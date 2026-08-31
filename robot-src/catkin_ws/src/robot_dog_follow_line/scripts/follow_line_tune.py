#!/home/pi/RaspberryPi-CM5/xgovenv/bin/python
"""巡线 HSV 阈值调参工具：8090 MJPEG 分屏推流（不用 LCD，避免与原厂 main.py 抢 SPI）。

调参时把狗摆成巡线同款低趴姿态（z=10/p=15，相机俯视近处地面），让看到的画面
与正式巡线一致；不做任何行走动作，退出时 dog.reset() 复位站立。
注意：不用 xgoscreen LCD——LCD 走 SPI，与原厂 main.py 并发会 spidev_ioctl 死锁
（2026-08-30 两次实机复现，kill 无效只能重启），推流画面在浏览器看即可。
须用厂商 xgovenv 运行（含 picamera2/xgolib）。也可：
  /home/pi/RaspberryPi-CM5/xgovenv/bin/python /home/pi/oumax-xgo/follow_line_tune.py
"""

from __future__ import annotations

import atexit
import json
import select
import signal
import socket
import subprocess
import sys
import termios
import threading
import time
import tty
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Condition
from urllib.parse import urlsplit

import cv2 as cv
import numpy as np
from PIL import Image
from picamera2 import Picamera2
from xgolib import XGO

CONFIG_PATH = Path(__file__).resolve().parent / "follow_line_config.json"
SAMPLE_LOG = Path(__file__).resolve().parent / "line_samples.log"
DEFAULT_LOWER = [0, 0, 0]
DEFAULT_UPPER = [180, 255, 30]
DEFAULT_CROP = [0, 319]  # 左右裁剪 [left_x, right_x]（保留区间，0~319），默认全宽
DEFAULT_LINE_WIDTH = [5, 100]  # 线宽过滤 [min_px, max_px]：minAreaRect 短边
PORT = 8090    # 带框原画面
MASK_PORT = 8091  # 阈值（二值）画面


class StreamingOutput:
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def set_frame(self, jpeg_bytes: bytes):
        with self.condition:
            self.frame = jpeg_bytes
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        output = self.server.output
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            body = (
                b"<html><head><title>follow_line_tune</title></head>"
                b"<body><h1>follow_line_tune (NOT oumax-camera)</h1>"
                b"<p>8090=boxed camera + line width / 8091=binary mask</p>"
                b"<img src='/stream.mjpg' style='max-width:100%;height:auto'>"
                b"</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path != "/stream.mjpg":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        try:
            while True:
                with output.condition:
                    output.condition.wait(timeout=1.0)
                    frame = output.frame
                if frame is None:
                    continue
                self.wfile.write(b"--FRAME\r\n")
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return


class StreamingServer(ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, output):
        self.output = output
        super().__init__(address, handler)


SERVICES = ("raicom-original-main.service", "oumax-camera.service")
_service_was_active = {}


def _is_active(name):
    completed = subprocess.run(
        ["systemctl", "is-active", name],
        capture_output=True, text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "active"


def _wait_inactive(name, timeout=15.0):
    """轮询等待服务真正 inactive；防 Restart=on-failure 竞态（停完又被拉起）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _is_active(name):
            return True
        time.sleep(0.2)
    return False


def stop_services():
    """停原厂主服务（占串口）与相机推流（oumax-camera）。

    本工具不用 LCD（避免 SPI 死锁），但低趴姿态需串口（被原厂 main.py 占用），
    相机需释放 8090，故两个服务都停；停后轮询确认 inactive，防止
    raicom-original-main 的 Restart=on-failure 停完自动拉起（2026-08-30 实机
    复现：服务停失败/超时被 systemd 判 failed 后自动重启，与原厂 main.py 并发
    抢 SPI 死锁，kill 无效只能重启机器）。
    """
    for name in SERVICES:
        _service_was_active[name] = _is_active(name)
        print(f"Stopping {name} ...", flush=True)
        subprocess.run(["sudo", "systemctl", "stop", name], check=True)
        if not _wait_inactive(name):
            raise RuntimeError(
                f"{name} still active after stop (Restart=on-failure race?); "
                f"check: systemctl status {name}"
            )
    # 给端口释放留一点时间，避免仍连上原厂 8090 流
    time.sleep(0.5)


def assert_port_free(port: int):
    """8090 仍被占用时直接失败，避免浏览器悄悄连上原厂纯画面流。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"port {port} still in use after stopping services; "
                f"check: ss -ltnp | grep {port} ; "
                f"systemctl is-active oumax-camera"
            )
    finally:
        sock.close()


def restore_services():
    """按启动前状态恢复服务（仅恢复原本 active 的）。"""
    for name in SERVICES:
        if _service_was_active.get(name, True):
            print(f"Restoring {name} ...", flush=True)
            completed = subprocess.run(
                ["sudo", "systemctl", "start", name],
                check=False,
            )
            if completed.returncode != 0:
                print(
                    f"ERROR: failed to start {name} "
                    f"(exit={completed.returncode})",
                    flush=True,
                )


def load_hsv(path: Path):
    """返回 (lower, upper, crop, line_width)；无配置/缺字段时用默认。"""
    if not path.is_file():
        return (
            list(DEFAULT_LOWER), list(DEFAULT_UPPER),
            list(DEFAULT_CROP), list(DEFAULT_LINE_WIDTH),
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return (
        list(data["lower"]),
        list(data["upper"]),
        list(data.get("crop", DEFAULT_CROP)),
        list(data.get("line_width", DEFAULT_LINE_WIDTH)),
    )


def save_hsv(path: Path, lower, upper, crop, line_width):
    payload = {
        "lower": [int(x) for x in lower],
        "upper": [int(x) for x in upper],
        "crop": [int(x) for x in crop],
        "line_width": [int(x) for x in line_width],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"Saved {path}: {payload}", flush=True)


def print_hsv(lower, upper, crop, line_width):
    # raw TTY 下需 \r\n，否则光标不回行首
    sys.stdout.write(
        f"H=[{lower[0]},{upper[0]}] S=[{lower[1]},{upper[1]}] "
        f"V=[{lower[2]},{upper[2]}] CROP=[{crop[0]},{crop[1]}] "
        f"LW=[{line_width[0]},{line_width[1]}]\r\n"
    )
    sys.stdout.flush()


def clamp_v(lower, upper):
    lower[2] = max(0, min(255, int(lower[2])))
    upper[2] = max(0, min(255, int(upper[2])))
    if lower[2] > upper[2]:
        lower[2] = upper[2]


def clamp_crop(crop):
    """裁剪边界钳制：0 <= left < right <= 319，且最小保留 10px。"""
    crop[0] = max(0, min(319, int(crop[0])))
    crop[1] = max(0, min(319, int(crop[1])))
    if crop[1] - crop[0] < 10:
        if crop[1] > crop[0]:
            crop[0] = max(0, crop[1] - 10)
        else:
            crop[1] = min(319, crop[0] + 10)


def make_mask(rgb_img, lower, upper, crop):
    """与 follow_line.color_follow.line_follow 视觉处理一致（含左右裁剪，不含画框）。"""
    height, width = rgb_img.shape[:2]
    img = rgb_img.copy()
    img[0:int(5 * height / 8), 0:width] = 0
    # 左右裁剪：只保留 crop=[left_x, right_x] 区间，避免多线场地误跟到旁边的线
    crop_left, crop_right = crop
    if crop_left > 0:
        img[:, :min(crop_left, width)] = 0
    if crop_right < width:
        img[:, max(crop_right, 0):] = 0
    hsv_img = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    mask = cv.inRange(
        hsv_img,
        np.array(lower, dtype="uint8"),
        np.array(upper, dtype="uint8"),
    )
    color_mask = cv.bitwise_and(hsv_img, hsv_img, mask=mask)
    gray_img = cv.cvtColor(color_mask, cv.COLOR_RGB2GRAY)
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5))
    gray_img = cv.morphologyEx(gray_img, cv.MORPH_CLOSE, kernel)
    _ret, binary = cv.threshold(gray_img, 10, 255, cv.THRESH_BINARY)
    return binary


def detect_contour(binary, line_width):
    """从二值图找线（线宽过滤），返回 (box_points, center_x, width_px) 或 None。

    与 follow_line.line_follow 的过滤逻辑一致：minAreaRect 短边在
    [min,max] 内才接受，过滤后取面积最大。
    """
    find_contours = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    if len(find_contours) == 3:
        contours = find_contours[1]
    else:
        contours = find_contours[0]
    w_min, w_max = line_width
    best = None
    best_area = 0
    best_width = 0
    for candidate in contours:
        rect = cv.minAreaRect(candidate)
        w, h = rect[1]
        line_w = min(w, h)
        if line_w < w_min or line_w > w_max:
            continue
        area = cv.contourArea(candidate)
        if area > best_area:
            best_area = area
            best = candidate
            best_width = line_w
    if best is None:
        return None
    box = cv.boxPoints(cv.minAreaRect(best))
    box = np.intp(box)
    cx = int(np.mean(box[:, 0]))
    return box, cx, int(best_width)


def sample_line(binary):
    """采样当前帧（p 键）：crop 全区/左右条带黑占比 + 最大轮廓几何。

    返回一行文本追加到 SAMPLE_LOG，供弯道判定标定分析。
    """
    h, w = binary.shape[:2]
    strip_w = 25
    ratio_full = float(np.count_nonzero(binary)) / (h * w)
    left_strip = binary[:, :strip_w]
    right_strip = binary[:, -strip_w:]
    ratio_l = float(np.count_nonzero(left_strip)) / left_strip.size
    ratio_r = float(np.count_nonzero(right_strip)) / right_strip.size

    find_contours = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contours = find_contours[1] if len(find_contours) == 3 else find_contours[0]
    ncont = len(contours)
    if ncont:
        areas = np.array([cv.contourArea(c) for c in contours], dtype=float)
        best = contours[int(np.argmax(areas))]
        (cx, cy), (bw, bh), angle = cv.minAreaRect(best)
        lw = min(bw, bh)
        ln = cv.arcLength(best, True)
        area = float(np.max(areas))
    else:
        cx = cy = lw = ln = area = -1.0
        angle = 0.0
    return (
        f"SAMPLE|t={time.strftime('%H:%M:%S')}|ratio_full={ratio_full:.2f}|"
        f"stripL={ratio_l:.2f}|stripR={ratio_r:.2f}|area={area:.0f}|"
        f"lw={lw:.0f}|len={ln:.0f}|cx={cx:.0f}|cy={cy:.0f}|angle={angle:.1f}|ncont={ncont}"
    )


def compose_orig(rgb_img, det, lower, upper, crop, line_width):
    """8090 画面：带框原图 + 线宽标注 + TUNE 参数水印。RGB 语义。"""
    canvas = rgb_img.copy()
    if det is not None:
        box, cx, width = det
        cv.polylines(canvas, [box], True, (255, 0, 0), 2)  # 蓝框（RGB）
        cv.circle(canvas, (cx, 120), 4, (255, 0, 255), -1)  # 圆心紫点
        cv.putText(
            canvas, f"LW={width}px  cx={cx}",
            (4, 40), cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv.LINE_AA,
        )
    cv.putText(
        canvas, "TUNE", (4, 24),
        cv.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2, cv.LINE_AA,
    )
    text = (
        f"H[{lower[0]},{upper[0]}] S[{lower[1]},{upper[1]}] "
        f"V[{lower[2]},{upper[2]}] CROP={crop} LW={line_width}"
    )
    cv.putText(
        canvas, text, (4, 60),
        cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2, cv.LINE_AA,
    )
    # 裁剪边界竖线
    cv.line(canvas, (int(crop[0]), 0), (int(crop[0]), 239), (255, 0, 255), 1)
    cv.line(canvas, (int(crop[1]), 0), (int(crop[1]), 239), (255, 0, 255), 1)
    return canvas


def compose_mask(binary, line_width):
    """8091 画面：红白二值掩码 + MASK 水印。"""
    h, w = binary.shape[:2]
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[binary > 0] = (0, 0, 255)  # RGB：掩码区纯红
    cv.putText(
        canvas, "MASK", (4, 24),
        cv.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2, cv.LINE_AA,
    )
    cv.putText(
        canvas, f"LW filter={line_width}",
        (4, 48), cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2, cv.LINE_AA,
    )
    return canvas


def read_key(timeout=0.0):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return ""
    return sys.stdin.read(1)


def init_low_pose():
    """摆成巡线同款低趴姿态（z=10/p=15），不做行走动作。

    调参画面与正式巡线视角一致（相机俯视近处地面）。自动识别机型后
    设置步态/姿态；退出时由调用方 dog.reset() 复位站立。
    """
    print("Setting low crouch pose (z=10, p=15) ...", flush=True)
    dog = XGO(port='/dev/ttyAMA0', version="xgolite")
    fm = dog.read_firmware()
    if fm and len(fm) > 0 and fm[0] == 'M':
        dog = XGO(port='/dev/ttyAMA0', version="xgomini")
    dog.stop()
    dog.pace('normal')
    dog.gait_type("slow_trot")
    dog.translation('z', 10)
    dog.attitude('p', 15)
    time.sleep(2)
    print("Low pose ready", flush=True)
    return dog


def main():
    stop_services()
    atexit.register(restore_services)
    assert_port_free(PORT)

    dog = init_low_pose()

    lower, upper, crop, line_width = load_hsv(CONFIG_PATH)
    print_hsv(lower, upper, crop, line_width)
    print(
        "Keys: w/s Vmax+/-10, 1/2 Vmax+/-1, a/d Vmin+/-10, "
        "z/x cropL+/-10, c/v cropR+/-10, n/b LW上限+/-5, "
        "p 采样当前帧(弯道标定), q save+exit, Q/Ctrl-C exit without save",
        flush=True,
    )
    print(
        f"带框原画面: http://192.168.137.157:{PORT}/stream.mjpg\n"
        f"阈值画面:   http://192.168.137.157:{MASK_PORT}/stream.mjpg",
        flush=True,
    )

    output_orig = StreamingOutput()
    output_mask = StreamingOutput()
    try:
        httpd_orig = StreamingServer(("0.0.0.0", PORT), StreamingHandler, output_orig)
        httpd_mask = StreamingServer(("0.0.0.0", MASK_PORT), StreamingHandler, output_mask)
    except OSError as exc:
        raise RuntimeError(
            f"cannot bind {PORT}/{MASK_PORT} (still oumax-camera?). {exc}"
        ) from exc
    threading.Thread(target=httpd_orig.serve_forever, daemon=True).start()
    threading.Thread(target=httpd_mask.serve_forever, daemon=True).start()
    print(f"bound {PORT}+{MASK_PORT} as follow_line_tune", flush=True)

    picam2 = Picamera2()
    picam2.configure(
        picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (320, 240)}
        )
    )
    picam2.start()

    if not sys.stdin.isatty():
        raise RuntimeError("follow_line_tune requires an interactive SSH/TTY stdin")
    settings = termios.tcgetattr(sys.stdin)
    save_on_exit = False
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            frame = picam2.capture_array()
            binary = make_mask(frame, lower, upper, crop)
            det = detect_contour(binary, line_width)

            # 8090：带框原画面（含线宽标注）
            view_orig = compose_orig(frame, det, lower, upper, crop, line_width)
            ok, jpeg = cv.imencode(
                ".jpg", cv.cvtColor(view_orig, cv.COLOR_RGB2BGR),
                [int(cv.IMWRITE_JPEG_QUALITY), 80],
            )
            if not ok:
                raise RuntimeError("cv2.imencode failed")
            output_orig.set_frame(jpeg.tobytes())

            # 8091：阈值二值画面
            view_mask = compose_mask(binary, line_width)
            ok2, jpeg2 = cv.imencode(
                ".jpg", cv.cvtColor(view_mask, cv.COLOR_RGB2BGR),
                [int(cv.IMWRITE_JPEG_QUALITY), 80],
            )
            if not ok2:
                raise RuntimeError("cv2.imencode failed")
            output_mask.set_frame(jpeg2.tobytes())

            key = read_key(0.01)
            if not key:
                continue
            if key in ("\x03", "Q"):
                save_on_exit = False
                break
            if key == "q":
                save_on_exit = True
                break
            if key == "p":
                # 采样当前帧（弯道判定标定用），追加写 line_samples.log
                sample_text = sample_line(binary)
                sys.stdout.write(sample_text + "\r\n")
                sys.stdout.flush()
                with open(SAMPLE_LOG, "a", encoding="utf-8") as f:
                    f.write(sample_text + "\n")
                sys.stdout.write(f"已采样 -> {SAMPLE_LOG}\r\n")
                sys.stdout.flush()
                continue
            changed = False
            if key == "w":
                upper[2] += 10
                changed = True
            elif key == "s":
                upper[2] -= 10
                changed = True
            elif key == "1":
                upper[2] += 1
                changed = True
            elif key == "2":
                upper[2] -= 1
                changed = True
            elif key == "a":
                lower[2] -= 10
                changed = True
            elif key == "d":
                lower[2] += 10
                changed = True
            elif key == "z":
                crop[0] -= 10
                changed = True
            elif key == "x":
                crop[0] += 10
                changed = True
            elif key == "c":
                crop[1] -= 10
                changed = True
            elif key == "v":
                crop[1] += 10
                changed = True
            elif key == "n":
                line_width[1] = min(300, line_width[1] + 5)
                changed = True
            elif key == "b":
                line_width[1] = max(line_width[0] + 5, line_width[1] - 5)
                changed = True
            if changed:
                clamp_v(lower, upper)
                clamp_crop(crop)
                print_hsv(lower, upper, crop, line_width)
    finally:
        # 清理期间忽略 SIGINT：否则二次 Ctrl-C 会打断 dog.reset/httpd.shutdown，
        # 导致清理不完整 + traceback（2026-08-30 实机复现）
        old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            dog.reset()
            print("dog reset to standing pose", flush=True)
            picam2.stop()
            httpd_orig.shutdown()
            httpd_mask.shutdown()
            if save_on_exit:
                save_hsv(CONFIG_PATH, lower, upper, crop, line_width)
            else:
                print("Exit without saving", flush=True)
        finally:
            signal.signal(signal.SIGINT, old_handler)


if __name__ == "__main__":
    main()
