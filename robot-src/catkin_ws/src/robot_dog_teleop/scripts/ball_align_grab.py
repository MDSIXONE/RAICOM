#!/usr/bin/env python3
"""自动对准夹球程序：趴下姿态 → 视觉对准球心 → 放臂夹球。

三个阶段：
1. 姿态趴下：只把腿关节 j1-j12 设为目标夹球姿态，机械臂关节 j13-j15 保持不动。
2. 视觉对准：用 YOLOv8 ONNX 模型检测球，通过差速轮脉冲（转向修正水平偏差 dx、
   前后移动修正垂直偏差 dy）把球对准画面中心。
3. 放臂夹球：爪子张开到最大（j13=-65）→ 机械臂到位（j14=-72, j15=92，保持
   爪子张开）→ 爪子闭合（j13=56）。

安全：
- 仅在 enable_motion:=true 时发送真实命令（launch 无默认值）。
- 差速轮命令无看门狗：每次脉冲后立即发零速停止，退出/中止时也确保零速。
- 对准有方向保护：连续多次脉冲误差未减小时报错退出，防止方向参数错误时越调越偏。
"""

import json
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2
import numpy as np
import rospy

_MANUAL_BASE_URL = "http://127.0.0.1:8765"
_HEALTH_URL = _MANUAL_BASE_URL + "/health"
_COMMAND_URL = _MANUAL_BASE_URL + "/command"

# 关节表：(名称, 舵机 id, (范围下限, 范围上限))。
# 与 manual_control_server.py 的 MOTOR_RANGES 保持一致。
_JOINT_SPECS = (
    ("j1", 11, (-73.0, 57.0)),
    ("j2", 12, (-66.0, 93.0)),
    ("j3", 13, (-31.0, 31.0)),
    ("j4", 21, (-73.0, 57.0)),
    ("j5", 22, (-66.0, 93.0)),
    ("j6", 23, (-31.0, 31.0)),
    ("j7", 31, (-73.0, 57.0)),
    ("j8", 32, (-66.0, 93.0)),
    ("j9", 33, (-31.0, 31.0)),
    ("j10", 41, (-73.0, 57.0)),
    ("j11", 42, (-66.0, 93.0)),
    ("j12", 43, (-31.0, 31.0)),
    ("j13", 51, (-65.0, 65.0)),
    ("j14", 52, (-115.0, 70.0)),
    ("j15", 53, (-85.0, 100.0)),
)

_INDEX_BY_NAME = {spec[0]: index for index, spec in enumerate(_JOINT_SPECS)}

# 夹球目标姿态（j13=56 为闭合状态的数值，程序先张开再闭合）。
_GRAB_POSE = {
    "j1": -60.0, "j2": 40.0, "j3": 0.0, "j4": -60.0, "j5": 40.0, "j6": 0.0,
    "j7": 21.0, "j8": 0.0, "j9": 0.0, "j10": 20.0, "j11": 0.0, "j12": 0.0,
    "j13": 56.0, "j14": -72.0, "j15": 92.0,
}

# 爪子张开到最大的角度（正值为收紧，负值为张开）。
_CLAW_OPEN = -65.0


def letterbox(img, new_size, color=(114, 114, 114)):
    h, w = img.shape[:2]
    new_w, new_h = new_size
    scale = min(new_w / w, new_h / h)
    resized_w, resized_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(img, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_h, new_w, 3), color, dtype=np.uint8)
    pad_x = (new_w - resized_w) // 2
    pad_y = (new_h - resized_h) // 2
    canvas[pad_y : pad_y + resized_h, pad_x : pad_x + resized_w] = resized
    return canvas, scale, pad_x, pad_y


def postprocess(output, conf_thres, iou_thres, img_shape, letterbox_scale, letterbox_pad):
    """把 YOLOv8 ONNX 原始输出转成检测列表（与 ball_spotter 的 ball_detector.py 一致）。

    output shape: [1, 4 + num_classes, num_anchors]。
    """
    orig_h, orig_w = img_shape[:2]
    scale, pad_x, pad_y = letterbox_scale, letterbox_pad[0], letterbox_pad[1]

    preds = output[0].T
    num_classes = preds.shape[1] - 4
    if num_classes < 1:
        raise ValueError("model output has no class scores")

    boxes_xywh = preds[:, :4]
    class_scores = preds[:, 4:]

    detections = []
    for c in range(num_classes):
        scores = class_scores[:, c]
        keep = np.where(scores >= conf_thres)[0]
        if keep.size == 0:
            continue
        cand_boxes = boxes_xywh[keep]
        cand_scores = scores[keep]
        xyxy = np.empty_like(cand_boxes)
        xyxy[:, 0] = cand_boxes[:, 0] - cand_boxes[:, 2] / 2.0
        xyxy[:, 1] = cand_boxes[:, 1] - cand_boxes[:, 3] / 2.0
        xyxy[:, 2] = cand_boxes[:, 0] + cand_boxes[:, 2] / 2.0
        xyxy[:, 3] = cand_boxes[:, 1] + cand_boxes[:, 3] / 2.0
        indices = cv2.dnn.NMSBoxes(
            xyxy.tolist(), cand_scores.tolist(), conf_thres, iou_thres
        )
        if isinstance(indices, tuple):
            indices = indices[0]
        if indices is None:
            continue
        for idx in np.asarray(indices).ravel():
            x1, y1, x2, y2 = xyxy[int(idx)]
            x1 = (x1 - pad_x) / scale
            y1 = (y1 - pad_y) / scale
            x2 = (x2 - pad_x) / scale
            y2 = (y2 - pad_y) / scale
            x1 = max(0.0, min(x1, orig_w - 1))
            y1 = max(0.0, min(y1, orig_h - 1))
            x2 = max(0.0, min(x2, orig_w - 1))
            y2 = max(0.0, min(y2, orig_h - 1))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(
                {
                    "cls": c,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "cx": (x1 + x2) / 2.0,
                    "cy": (y1 + y2) / 2.0,
                    "w": x2 - x1,
                    "h": y2 - y1,
                    "conf": float(cand_scores[int(idx)]),
                }
            )
    return detections


class OumaxManualClient:
    """调用已运行的本地 OUMAX 手控服务的客户端（与 pose_keyboard_teleop 一致）。"""

    @staticmethod
    def _request(url, payload=None, timeout=5.0):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
        with urlopen(request, timeout=timeout) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        if not decoded.get("ok", False):
            raise RuntimeError(decoded.get("message", "manual service rejected request"))
        return decoded

    def verify_identity(self):
        try:
            health = self._request(_HEALTH_URL)
        except (URLError, OSError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                "cannot reach local OUMAX manual service: {}".format(error)
            )
        if health.get("serial_port") != "/dev/ttyAMA0" or health.get("manual_port") != 8765:
            raise RuntimeError(
                "unexpected OUMAX manual-service identity: {}".format(health)
            )

    def motor_move(self, servo_id, angle):
        return self._request(
            _COMMAND_URL,
            {"kind": "motor", "id": servo_id, "angle": angle},
        )

    def wheel_move(self, speeds):
        """差速轮命令（持续生效，无看门狗；调用方必须随后发送零速停止）。"""
        return self._request(
            _COMMAND_URL,
            {"kind": "wheel", "enabled": True, "speeds": [float(s) for s in speeds]},
        )

    def gamepad(self, x, y, yaw, drive_mode="wheel4"):
        """gamepad 差速轮命令（实机验证：wheel4 需 10Hz 持续刷新才会动）。"""
        return self._request(
            _COMMAND_URL,
            {"kind": "gamepad", "x": x, "y": y, "yaw": yaw, "drive_mode": drive_mode},
        )

    def warmup(self):
        """触发 OUMAX 服务端懒初始化（打开串口并握手，实测可能耗时数十秒），
        期间阻塞；用长超时发一条安全的夹爪回中命令（j13=0，无副作用）。
        初始化完成后后续命令通常毫秒级返回。"""
        try:
            self._request(
                _COMMAND_URL,
                {"kind": "motor", "id": 51, "angle": 0.0},
                timeout=90.0,
            )
        except (URLError, OSError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                "warmup motor command failed (serial init): {}".format(error)
            )


class BallAlignGrab:
    """趴下 → 视觉对准球心 → 放臂夹球 的自动流程。"""

    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError(
                "real motion is disabled; use enable_motion:=true only after "
                "on-site safety confirmation"
            )
        model_path = rospy.get_param("~model", "")
        if not model_path:
            raise RuntimeError("~model parameter is required (path to best.onnx)")
        self._model_path = model_path
        self._stream_url = rospy.get_param("~stream_url", "http://127.0.0.1:8090/stream.mjpg")
        self._conf = float(rospy.get_param("~conf", 0.4))
        self._iou = float(rospy.get_param("~iou", 0.45))
        names = rospy.get_param("~names", "red_ball,blue_ball,green_ball")
        self._class_names = [n.strip() for n in names.split(",") if n.strip()]
        classes = rospy.get_param("~classes", "")
        self._allowed_classes = None
        if classes:
            try:
                self._allowed_classes = {int(x) for x in str(classes).split(",") if x.strip()}
            except ValueError as error:
                raise RuntimeError("~classes must be comma-separated ints: {}".format(error))
        self._tol_x = float(rospy.get_param("~tol_x", 20.0))
        self._tol_y = float(rospy.get_param("~tol_y", 20.0))
        # 差速轮对准参数（wheel 无看门狗，脉冲后必须零速停止）。
        # 实机标定：前两轮（左前/右前）有驱动，后两轮无驱动电机；
        # 速度 0.8 以下轮子几乎不动，1.5 满速有明显转动。
        self._wheel_turn_speed = float(rospy.get_param("~wheel_turn_speed", 1.5))
        self._wheel_move_speed = float(rospy.get_param("~wheel_move_speed", 1.5))
        self._wheel_pulse_time = float(rospy.get_param("~wheel_pulse_time", 0.6))
        self._wheel_delay = float(rospy.get_param("~wheel_delay", 1.0))
        self._yaw_direction = float(rospy.get_param("~yaw_direction", 1.0))
        if self._yaw_direction not in (-1.0, 1.0):
            raise ValueError("~yaw_direction must be -1 or 1")
        self._x_direction = float(rospy.get_param("~x_direction", 1.0))
        if self._x_direction not in (-1.0, 1.0):
            raise ValueError("~x_direction must be -1 or 1")
        self._joint_delay = float(rospy.get_param("~joint_delay", 0.5))
        self._arm_delay = float(rospy.get_param("~arm_delay", 0.6))
        self._align_timeout = float(rospy.get_param("~align_timeout", 180.0))
        self._good_frames = int(rospy.get_param("~good_frames", 3))
        self._max_worsen = int(rospy.get_param("~max_worsen", 3))
        self._client = OumaxManualClient()
        self._client.verify_identity()
        self._client.warmup()
        rospy.on_shutdown(self._shutdown_stop)

    # ---------- 底层工具 ----------

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    def _send_joint(self, name, angle):
        spec = _JOINT_SPECS[_INDEX_BY_NAME[name]]
        clamped = self._clamp(angle, spec[2][0], spec[2][1])
        try:
            self._client.motor_move(spec[1], clamped)
        except (URLError, OSError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                "motor command for {}={} failed: {}".format(name, clamped, error)
            )
        rospy.loginfo("motor %s -> %.1f deg", name, clamped)

    def _set_pose(self, pose, delay):
        """逐关节发送目标姿态，关节间留 delay 秒让舵机跟上。"""
        for name, angle in pose.items():
            self._send_joint(name, angle)
            if delay > 0.0:
                time.sleep(delay)

    # ---------- 阶段 1：趴下 ----------

    def _crouch(self):
        """只把腿关节 j1-j12 设为目标姿态，机械臂 j13-j15 保持不动。"""
        rospy.loginfo("stage 1/3: crouching with legs only (arm untouched)")
        crouch_pose = {spec[0]: _GRAB_POSE[spec[0]] for spec in _JOINT_SPECS[:12]}
        self._set_pose(crouch_pose, self._joint_delay)

    # ---------- 阶段 2：视觉对准 ----------

    def _pick_ball(self, detections):
        if self._allowed_classes is not None:
            detections = [d for d in detections if d["cls"] in self._allowed_classes]
        if not detections:
            return None
        return max(detections, key=lambda d: d["conf"])

    def _wheel_hold(self, speeds, duration):
        """差速轮持续刷新：10Hz 连发 duration 秒后发零速停止。

        实机验证：wheel 命令单发不驱动轮子，必须像定点巡航那样 10Hz
        持续刷新才会动。四个轮子全部给值，不出现不受控轮。"""
        try:
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                self._client.wheel_move(speeds)
                time.sleep(0.1)
        except (URLError, OSError, ValueError, RuntimeError) as error:
            raise RuntimeError("wheel command failed: {}".format(error))
        finally:
            try:
                self._client.wheel_move([0.0, 0.0, 0.0, 0.0])
            except (URLError, OSError, ValueError, RuntimeError) as error:
                raise RuntimeError("wheel stop failed: {}".format(error))

    def _wheel_yaw_speeds(self, dx):
        """前轮差速转向（实测映射：字节0=左前、字节1=右前、后轮无驱动电机）：
        球偏右（dx>0）→ 右转：左前向前、右前向后；
        球偏左（dx<0）→ 左转：左前向后、右前向前。
        方向由 yaw_direction 参数反转。"""
        speed = self._wheel_turn_speed * self._yaw_direction
        if dx > 0:
            return [speed, -speed, 0.0, 0.0]
        if dx < 0:
            return [-speed, speed, 0.0, 0.0]
        return [0.0, 0.0, 0.0, 0.0]

    def _wheel_move_speeds(self, dy):
        """前后移动，前两轮同向（后轮无驱动，置 0）：
        球偏上（dy<0，画面顶部=远处）→ 前进；偏下（dy>0，近处）→ 后退。
        方向由 x_direction 参数反转。"""
        speed = self._wheel_move_speed * self._x_direction
        if dy < 0:
            return [speed, speed, 0.0, 0.0]
        if dy > 0:
            return [-speed, -speed, 0.0, 0.0]
        return [0.0, 0.0, 0.0, 0.0]

    def _align(self, session, input_name, expected_size):
        rospy.loginfo("stage 2/3: aligning to ball center via differential wheels")
        cap = cv2.VideoCapture(self._stream_url)
        if not cap.isOpened():
            raise RuntimeError("cannot open camera stream: {}".format(self._stream_url))
        try:
            deadline = time.monotonic() + self._align_timeout
            good_count = 0
            worsen_count = 0
            last_error = None
            no_ball_count = 0
            scan_phase = 0  # 0=右转, 1=左转，交替扫描
            while not rospy.is_shutdown():
                if time.monotonic() > deadline:
                    raise RuntimeError("align timeout: ball not centered in time")
                ok, frame = cap.read()
                if not ok or frame is None:
                    rospy.logwarn_throttle(5.0, "failed to read frame; retrying")
                    time.sleep(0.1)
                    continue

                height, width = frame.shape[:2]
                boxed, scale, pad_x, pad_y = letterbox(frame, expected_size)
                blob = cv2.dnn.blobFromImage(
                    boxed, scalefactor=1.0 / 255.0, size=expected_size, swapRB=True
                )
                outputs = session.run(None, {input_name: blob})
                detections = postprocess(
                    outputs[0], self._conf, self._iou, frame.shape, scale, (pad_x, pad_y)
                )
                ball = self._pick_ball(detections)
                if ball is None:
                    no_ball_count += 1
                    rospy.logwarn_throttle(
                        5.0,
                        "no ball detected (conf>%.2f); scanning with wheel turns",
                        self._conf,
                    )
                    if no_ball_count % 3 == 0:
                        # 交替左右转向扫描，直到球进入视野
                        dx_probe = 1.0 if scan_phase == 0 else -1.0
                        scan_phase = 1 - scan_phase
                        rospy.loginfo("scan wheel yaw pulse (phase %d)", scan_phase)
                        self._wheel_hold(
                            self._wheel_yaw_speeds(dx_probe), self._wheel_pulse_time
                        )
                        time.sleep(self._wheel_delay)
                    continue

                dx = ball["cx"] - width / 2.0
                dy = ball["cy"] - height / 2.0
                rospy.loginfo_throttle(
                    2.0,
                    "ball %s center=(%.0f,%.0f) dx=%.0f dy=%.0f conf=%.2f",
                    self._class_names[ball["cls"]]
                    if ball["cls"] < len(self._class_names)
                    else "cls{}".format(ball["cls"]),
                    ball["cx"],
                    ball["cy"],
                    dx,
                    dy,
                    ball["conf"],
                )

                if abs(dx) <= self._tol_x and abs(dy) <= self._tol_y:
                    good_count += 1
                    if good_count >= self._good_frames:
                        rospy.loginfo("ball centered: dx=%.1f dy=%.1f", dx, dy)
                        return True
                    continue

                good_count = 0
                error = abs(dx) + abs(dy)
                if last_error is not None and error > last_error + 5.0:
                    worsen_count += 1
                    if worsen_count >= self._max_worsen:
                        raise RuntimeError(
                            "alignment is worsening after {} pulses: wheel direction "
                            "may be inverted; stop and fix ~yaw_direction/~x_direction".format(
                                self._max_worsen
                            )
                        )
                else:
                    worsen_count = 0
                last_error = error

                if abs(dx) > self._tol_x:
                    rospy.loginfo("wheel yaw pulse: dx=%.0f", dx)
                    self._wheel_hold(
                        self._wheel_yaw_speeds(dx), self._wheel_pulse_time
                    )
                elif abs(dy) > self._tol_y:
                    rospy.loginfo("wheel move pulse: dy=%.0f", dy)
                    self._wheel_hold(
                        self._wheel_move_speeds(dy), self._wheel_pulse_time
                    )
                time.sleep(self._wheel_delay)
            raise RuntimeError("ROS shutdown during alignment")
        finally:
            cap.release()

    def _shutdown_stop(self):
        """退出/中止时确保轮子零速（wheel 无看门狗）。"""
        try:
            self._client.wheel_move([0.0, 0.0, 0.0, 0.0])
        except (URLError, OSError, ValueError, RuntimeError):
            pass

    # ---------- 阶段 3：放臂夹球 ----------

    def _grab(self):
        """爪子张开到最大 → 臂到位（保持张开）→ 闭合。"""
        rospy.loginfo("stage 3/3: lowering arm and grabbing ball")
        rospy.loginfo("claw open to max (j13=%.1f)", _CLAW_OPEN)
        self._send_joint("j13", _CLAW_OPEN)
        time.sleep(self._arm_delay)
        rospy.loginfo("arm to grab pose (j14=%.1f, j15=%.1f), claw stays open", -72.0, 92.0)
        self._send_joint("j14", -72.0)
        time.sleep(self._arm_delay)
        self._send_joint("j15", 92.0)
        time.sleep(self._arm_delay)
        rospy.loginfo("claw close (j13=%.1f)", _GRAB_POSE["j13"])
        self._send_joint("j13", _GRAB_POSE["j13"])
        time.sleep(self._arm_delay)
        rospy.loginfo("ball grabbed: full pose %s", " ".join(
            "{}={:g}".format(name, value) for name, value in _GRAB_POSE.items()
        ))

    # ---------- 主流程 ----------

    def run(self):
        rospy.loginfo("loading ball model from %s", self._model_path)
        session = self._load_session()
        input_name = session.get_inputs()[0].name
        expected_size = tuple(session.get_inputs()[0].shape[2:4])
        rospy.loginfo("model input size %s", expected_size)

        try:
            self._crouch()
            self._align(session, input_name, expected_size)
            self._grab()
        except RuntimeError as error:
            rospy.logerr("ball align-grab aborted: %s", error)
            raise SystemExit(2)

    def _load_session(self):
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime is required: pip install onnxruntime"
            ) from exc
        session = ort.InferenceSession(self._model_path, providers=["CPUExecutionProvider"])
        return session


def main():
    rospy.init_node("robot_dog_ball_align_grab")
    try:
        BallAlignGrab().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("ball align-grab refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
