#!/usr/bin/env python3
'''
巡线代码
可视化相关的代码已经注释
需要根据光照调节掩码范围
'''
# encoding: utf-8
import json
import math
import urllib.error
import urllib.request
import select
import signal
import sys
import termios
import threading
import time
import tty
from collections import deque
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Condition
from urllib.parse import urlsplit
import cv2 as cv
import numpy as np
from picamera2 import Picamera2
from uiutils import *
from xgolib import XGO
from statistics import mode, StatisticsError
import logging
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image, ImageDraw, ImageFont
from uiutils import *
display = LCD_2inch.LCD_2inch()
display.clear()
splash = Image.new("RGB", (display.height, display.width), "black")
display.ShowImage(splash)
button = Button()

STREAM_PORT = 8090  # 带框原画面
MASK_PORT = 8091    # 阈值（二值掩码）画面
# 雷达后方第一个右转定位（替代线宽突变）：轮询后方距离 HTTP
REAR_RANGE_URL = "http://127.0.0.1:8767/rear"
DEFAULT_REAR_DIP_FROM_M = 2.0      # 阶段1：rear 曾 > 该值（起点后方开阔）
DEFAULT_REAR_DIP_TO_M = 1.0        # 阶段1：rear 首次 < 该值 = 第一个右转（开启功能）
DEFAULT_REAR_TURN_AT_STEPS_M = [0.75, 1.5]  # 阶段2触发距离列表（依次生效）：0.75 一次、1.5 一次（2026-09-01 改）
DEFAULT_REAR_YAW_MIN_DEG = 30.0   # 阶段2第1次触发前要求 |yaw 变化| ≥ 该值（80°实机达不到：弯道幅度仅~30°，2026-09-01 降）
DEFAULT_REAR_TURN_DEG = 90.0       # 右转/左转角度（度）
DEFAULT_REAR_TURN_SPEED = 16       # 转向速度绝对值（负=右转，正=左转）
DEFAULT_REAR_HOLD_S = 2.0          # 右转后停顿时长（秒）
DEFAULT_REAR_TURN_TIMEOUT = 10.0   # 每段 yaw 闭环超时（秒）
DEFAULT_USE_REAR_TRIGGER = True    # True=用雷达后方；False=回退线宽突变
DEFAULT_USE_LINE_SURGE = False     # 改用雷达后默认关闭线宽突变
DEFAULT_LOCK_WHEELS = True         # foot 巡线行进中锁 4 轮（wheel_control 128 抱死，防轮子自由滚动漂移）


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
                b"<html><body><img src='/stream.mjpg' "
                b"style='max-width:100%;height:auto'></body></html>"
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


FOLLOW_LINE_CONFIG = Path(__file__).resolve().parent / "follow_line_config.json"
DEFAULT_LOWER_BLACK = [0, 0, 0]
DEFAULT_UPPER_BLACK = [180, 255, 30]
DEFAULT_CROP = [0, 319]  # 左右裁剪 [left_x, right_x]（保留区间，0~319），默认全宽
DEFAULT_LINE_WIDTH = [5, 150]  # 线宽过滤 [min_px, max_px]：minAreaRect 短边；上限 150 给弯道粗块留余量（突变 raw>95 仍可跟踪）
# 运动控制默认（2026-08-31：全部可写入 follow_line_config.json，边走边调后按 s 保存即为下次启动默认）
DEFAULT_PID = [396.0, 0, 30.0]          # [P, I, D]
DEFAULT_STRAIGHT_SPEED = 6              # 直行 move_x 速度（2026-08-31 实机再降：8→6）
DEFAULT_TURN_MOVE_SPEED = 4             # 转向时前进速度（2026-08-31 实机再降：6→4）
DEFAULT_DIRECTION = 1                   # 转向方向：1=原厂方向，-1=反
DEFAULT_MODE = 'foot'                   # 运动方式：foot 足式 / wheel 轮式
DEFAULT_WHEEL_BASE = 145                # 轮式基础速度字节（>128 前进）


def load_follow_line_config(config_path=FOLLOW_LINE_CONFIG):
    """读取同目录 follow_line_config.json（HSV/裁剪/线宽 + 运动参数）。

    缺失文件或缺字段时用默认值；返回完整配置 dict，字段与 save_follow_line_config
    一致，供 LineDetect 启动时一次性应用。
    """
    defaults = {
        "lower": list(DEFAULT_LOWER_BLACK),
        "upper": list(DEFAULT_UPPER_BLACK),
        "crop": list(DEFAULT_CROP),
        "line_width": list(DEFAULT_LINE_WIDTH),
        "pid": list(DEFAULT_PID),
        "straight_speed": DEFAULT_STRAIGHT_SPEED,
        "turn_move_speed": DEFAULT_TURN_MOVE_SPEED,
        "direction": DEFAULT_DIRECTION,
        "mode": DEFAULT_MODE,
        "wheel_base": DEFAULT_WHEEL_BASE,
        "lock_wheels": DEFAULT_LOCK_WHEELS,
        "rear_dip_from_m": DEFAULT_REAR_DIP_FROM_M,
        "rear_dip_to_m": DEFAULT_REAR_DIP_TO_M,
        "rear_turn_at_steps_m": list(DEFAULT_REAR_TURN_AT_STEPS_M),
        "rear_yaw_min_deg": DEFAULT_REAR_YAW_MIN_DEG,
        "rear_turn_deg": DEFAULT_REAR_TURN_DEG,
        "rear_hold_s": DEFAULT_REAR_HOLD_S,
    }
    if not config_path.is_file():
        print(
            f"未找到 {config_path.name}，使用默认 "
            f"lower={defaults['lower']} upper={defaults['upper']} "
            f"crop={defaults['crop']} line_width={defaults['line_width']} "
            f"pid={defaults['pid']} spd={defaults['straight_speed']}/"
            f"{defaults['turn_move_speed']} dir={defaults['direction']} "
            f"mode={defaults['mode']}"
        )
        return defaults
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = dict(defaults)
    for key in cfg:
        if key in data:
            cfg[key] = data[key]
    print(
        f"已加载巡线配置 {config_path}: lower={cfg['lower']} upper={cfg['upper']} "
        f"crop={cfg['crop']} line_width={cfg['line_width']} pid={cfg['pid']} "
        f"spd={cfg['straight_speed']}/{cfg['turn_move_speed']} "
        f"dir={cfg['direction']} mode={cfg['mode']}"
    )
    return cfg


def save_follow_line_config(line_detect, config_path=FOLLOW_LINE_CONFIG):
    """把当前巡线参数（视觉 + 运动）写回 follow_line_config.json（s 键调用）。

    保存后下次启动 follow_line.py / follow_line_tune.py 即以这些值为默认。
    """
    payload = {
        "lower": [int(x) for x in line_detect.color.lower_black],
        "upper": [int(x) for x in line_detect.color.upper_black],
        "crop": [int(x) for x in line_detect.color.crop],
        "line_width": [int(x) for x in line_detect.color.line_width],
        "pid": [float(x) for x in line_detect.FollowLinePID],
        "straight_speed": int(line_detect.straight_speed),
        "turn_move_speed": int(line_detect.turn_move_speed),
        "direction": int(line_detect.direction),
        "mode": str(line_detect.mode),
        "wheel_base": int(line_detect.wheel_base),
        "lock_wheels": bool(line_detect.lock_wheels),
        "rear_dip_from_m": float(line_detect.rear_dip_from_m),
        "rear_dip_to_m": float(line_detect.rear_dip_to_m),
        "rear_turn_at_steps_m": [float(v) for v in line_detect.rear_turn_at_steps_m],
        "rear_yaw_min_deg": float(line_detect.rear_yaw_min_deg),
        "rear_turn_deg": float(line_detect.rear_turn_deg),
        "rear_hold_s": float(line_detect.rear_hold_s),
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"已保存巡线参数 {config_path}: {payload}", flush=True)


# 定义颜色跟踪类
class color_follow:
    def __init__(self):
        """
        初始化一些参数
        binary: 二值化图像
        Center_x: 检测到的圆形的中心x坐标
        Center_y: 检测到的圆形的中心y坐标
        Center_r: 检测到的圆形的半径
        """
        self.binary = None
        self.Center_x = 0
        self.Center_y = 0
        self.Center_r = 0
        self.best_area = 0  # 最大轮廓面积（弯道检测用）
        self.best_line_w = 0  # 过滤后最大轮廓的线宽（minAreaRect 短边）
        self.raw_line_w = 0  # 不过滤的全局最大轮廓短边（线宽突变检测用）
        self.lower_black = np.array(DEFAULT_LOWER_BLACK, dtype="uint8")
        self.upper_black = np.array(DEFAULT_UPPER_BLACK, dtype="uint8")
        self.crop = list(DEFAULT_CROP)
        self.line_width = list(DEFAULT_LINE_WIDTH)

    def line_follow(self, rgb_img, hsv_msg):
        """
        对输入的RGB图像进行跟踪
        :param rgb_img: 输入的RGB图像
        :param hsv_msg: HSV颜色范围的元组，格式为((H1, S1, V1), (H2, S2, V2))
        :return: 处理后的RGB图像、二值图像以及检测到的圆形的中心坐标和半径
        """
        height, width = rgb_img.shape[:2]
        img = rgb_img.copy()
        img[0:int(5*height / 8), 0:width] = 0  # 清空图像上半部分
        # 左右裁剪：只保留 crop=[left_x, right_x] 区间，避免多线场地误跟到旁边的线
        crop_left, crop_right = self.crop
        if crop_left > 0:
            img[:, :min(crop_left, width)] = 0
        if crop_right < width:
            img[:, max(crop_right, 0):] = 0
        hsv_img = cv.cvtColor(img, cv.COLOR_BGR2HSV)  # 将图像转换为HSV

        # 创建掩码，保留黑色；阈值来自实例属性（可由 follow_line_config.json 覆盖）
        mask = cv.inRange(hsv_img, self.lower_black, self.upper_black)


        color_mask = cv.bitwise_and(hsv_img, hsv_img, mask=mask)
        gray_img = cv.cvtColor(color_mask, cv.COLOR_RGB2GRAY)  
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5)) 
        gray_img = cv.morphologyEx(gray_img, cv.MORPH_CLOSE, kernel)
        ret, binary = cv.threshold(gray_img, 10, 255, cv.THRESH_BINARY) 
        find_contours = cv.findContours(
            binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)  # 获取轮廓点集(坐标)
        if len(find_contours) == 3:
            contours = find_contours[1]
        else:
            contours = find_contours[0]

        if len(contours) != 0:
            # 线宽过滤：minAreaRect 短边（线宽）须在 [line_width_min, line_width_max]
            # 内，排除其他线/杂物（防误跟旁边线）；过滤后取面积最大的
            w_min, w_max = self.line_width
            best = None
            best_area = 0
            best_line_w = 0
            raw_line_w = 0  # 不过滤的全局最大轮廓短边（线宽突变检测用）
            raw_area = 0
            for candidate in contours:
                rect = cv.minAreaRect(candidate)
                w, h = rect[1]
                line_w = min(w, h)
                area = cv.contourArea(candidate)
                if area > raw_area:
                    raw_area = area
                    raw_line_w = line_w
                if line_w < w_min or line_w > w_max:
                    continue
                if area > best_area:
                    best_area = area
                    best = candidate
                    best_line_w = line_w
            if best is None:
                self.raw_line_w = raw_line_w
                return rgb_img, binary, None
            self.best_line_w = best_line_w
            self.raw_line_w = raw_line_w
            max_rect = cv.minAreaRect(best)
            max_box = cv.boxPoints(max_rect)
            max_box = np.intp(max_box)

            box = cv.boxPoints(max_rect)  
            box = np.intp(box) 

            cv.drawContours(rgb_img, [box], 0, (255, 0, 0), 2)  # 绘制最小矩形

            (color_x, color_y), color_radius = cv.minEnclosingCircle(max_box)
            self.Center_x = int(color_x)  
            self.Center_y = int(color_y)
            self.Center_r = int(color_radius)
            self.best_area = best_area
            cv.circle(rgb_img, (self.Center_x, self.Center_y),
                      5, (255, 0, 255), -1)
            b, g, r1 = cv.split(rgb_img)
            image = cv.merge((r1, g, b))
            imgok = Image.fromarray(image)
            display.ShowImage(imgok)
        else:
            self.best_line_w = 0
            self.raw_line_w = 0
            self.best_area = 0
            return rgb_img, binary, None
        return rgb_img, binary, (self.Center_x, self.Center_y, self.Center_r)

# 定义简单PID控制器类
class simplePID:
    """
    非常简单的离散PID控制器
    """

    def __init__(self, target, P, I, D):
        """
        创建一个离散PID控制器

        :param target: 目标值，可以是标量或与P、I、D长度相同的向量
        :param P: 比例系数
        :param I: 积分系数
        :param D: 微分系数
        """
        # 检查参数形状是否兼容
        if (not (np.size(P) == np.size(I) == np.size(D)) or ((np.size(target) == 1) and np.size(P) != 1) or (
                np.size(target) != 1 and (np.size(P) != np.size(target) and (np.size(P) != 1)))):
            raise TypeError('input parameters shape is not compatable')

        self.Kp = np.array(P)
        self.Ki = np.array(I)
        self.Kd = np.array(D)
        self.last_error = 0
        self.integrator = 0
        self.timeOfLastCall = None
        self.setPoint = np.array(target)
        self.integrator_max = float('inf')
        

    def update(self, current_value):
        """
        更新PID控制器

        :param current_value: 当前值，可以是标量或与目标值长度相同的向量
        :return: 控制信号，与目标值长度相同的向量
        """
        current_value = np.array(current_value)
        if (np.size(current_value) != np.size(self.setPoint)):
            raise TypeError(
                'current_value and target do not have the same shape')
        currentTime = time.perf_counter()
        if (self.timeOfLastCall is None):
            # PID首次调用，还不知道时间间隔deltaT，不应用控制信号
            self.timeOfLastCall = currentTime
            return np.zeros(np.size(current_value))
        deltaT = (currentTime - self.timeOfLastCall)
        if deltaT > 0.5:
            # 长时间空档（丢线转圈期间 execute 不调用）后重置积分/微分状态，
            # 避免陈旧时间把 I/D 项污染成不可预测值，重见线即全新启动
            self.integrator = 0
            self.last_error = 0
            self.timeOfLastCall = currentTime
            return np.zeros(np.size(current_value))
        error = self.setPoint - current_value
        P = error
        # 误差的积分是当前误差乘以自上次更新以来的时间
        self.integrator = self.integrator + (error * deltaT)
        I = self.integrator
        # 导数是误差的差值除以自上次更新以来的时间
        D = (error - self.last_error) / deltaT
        self.last_error = error
        self.timeOfLastCall = currentTime
        # 返回控制信号
        return self.Kp * P + self.Ki * I + self.Kd * D


# 定义巡线检测类
class LineDetect:
    def __init__(self):
        self.img = None
        self.circle = None
        self.Roi_init = ()
        self.scale = 1000
        list_hsv = (0, 43, 46, 10, 255, 255)
        self.hsv_text = ((int(list_hsv[0]), int(list_hsv[1]), int(list_hsv[2])),
                         (int(list_hsv[3]), int(list_hsv[4]), int(list_hsv[5])))
        self.hsv_range = self.hsv_text
        self.dyn_update = True
        self.select_flags = False
        self.Track_state = 'tracking'
        self.windows_name = 'frame'
        self.color = color_follow()
        self.cols, self.rows = 0, 0
        # 默认值见文件顶部 DEFAULT_* 常量；启动时由 load_follow_line_config() 覆盖为
        # follow_line_config.json 中的保存值（边走边调按 s 保存）
        self.FollowLinePID = list(DEFAULT_PID)  # 实机标定（2026-08-30）：P=396/D=30 基本巡线；边走边调 p/o/i/u
        self.straight_speed = DEFAULT_STRAIGHT_SPEED  # 直行 move_x 速度（原厂 18 实机太快，边走边调 [ ] ±1）
        self.turn_move_speed = DEFAULT_TURN_MOVE_SPEED  # 转向时前进速度（原厂 15 实机太快，边走边调 - = ±1）
        self.direction = DEFAULT_DIRECTION  # 转向方向：1=原厂方向，-1=反（t 键切换，实机方向反时用）
        self.mode = DEFAULT_MODE  # 运动方式：foot 足式 / wheel 轮式（m 键切换）
        self.wheel_base = DEFAULT_WHEEL_BASE  # 轮式基础速度字节（>128 前进；直行 145 约 0.2m/s 量级）
        self.lock_wheels = DEFAULT_LOCK_WHEELS  # foot 行进中锁 4 轮（wheel_control 128 抱死）
        self._lost = False  # 丢线状态（日志：丢线开始/恢复 + 持续时长）
        self._lost_ts = 0.0
        self._lost_frame = 0  # 连续丢线帧数：≥5 帧（约 0.5s）才确认真丢线并启动探测，
                              # 线边缘闪烁的抖动丢线（1-2 帧恢复）不触发探测
        # 弯道探测：丢线后右转探测——每转一格抓帧检测，见到线即停交回 PID 巡线，
        # 限格内未见线则丢线即停。不依赖 cx/area 判据（宽线时 cx 全程 ≤177 失效）。
        self.probe_steps = 6        # 最多右转格数
        self.step_duration = 0.7 * 5 / 3  # 每格右转时长(秒)：0.7 加 2/3 = 1.167s，turn(-16)
        self._probe_active = False  # 探测进行中
        self._probe_step = 0        # 已转格数
        self._probe_cooldown = 0.0  # 探测完成后冷却：冷却期内再丢线不重复探测（防死循环）
        # 线宽突变检测（2026-08-31）：raw_line_w > 95px 且连续 3 帧 → 右转 90°
        # （2026-08-31 实机：正常段约 89px 误触发 75，改 95）
        self.surge_lw_thresh = 95   # 突变绝对阈值（px）：超过即弯道
        self.surge_frames = 3       # 连续突变帧数
        # 右转 90° 改 IMU yaw 闭环（2026-09-01）：不再盲转固定时长（turn(-16)×4.2s
        # 开环——转弯时摇晃看不到线也照转，转多转少无反馈）；读机载 IMU yaw 累积角
        # （0x66 单轴，度）做闭环，|yaw 变化| ≥ surge_turn_deg 即停转。speed 符号
        # = 转向方向（负=右转，同原盲转，实机标定）。
        self.surge_turn_deg = 90.0       # 目标转角（度）
        self.surge_turn_speed = -16      # 转向速度（同原盲转）
        self.surge_turn_timeout = 10.0   # 闭环超时(秒)：yaw 异常/转不动时停转保护
        self._lw_surge = 0          # 连续突变计数
        self._surge_active = False  # 线宽突变右转执行中
        # 雷达后方第一个右转定位（2026-09-01）：rear 首次 >2m→<1m = 第一个右转（开启
        # 功能）；此后 rear 增大到 ≥1.5m 时右转 90° → 停 2s → 左转 90° 回正 → 继续巡线
        self.use_rear_trigger = DEFAULT_USE_REAR_TRIGGER
        self.use_line_surge = DEFAULT_USE_LINE_SURGE
        self.rear_dip_from_m = DEFAULT_REAR_DIP_FROM_M
        self.rear_dip_to_m = DEFAULT_REAR_DIP_TO_M
        self.rear_turn_at_steps_m = list(DEFAULT_REAR_TURN_AT_STEPS_M)
        self.rear_yaw_min_deg = DEFAULT_REAR_YAW_MIN_DEG
        self.rear_turn_deg = DEFAULT_REAR_TURN_DEG
        self.rear_turn_speed = DEFAULT_REAR_TURN_SPEED
        self.rear_hold_s = DEFAULT_REAR_HOLD_S
        self.rear_turn_timeout = DEFAULT_REAR_TURN_TIMEOUT
        self.rear_range_url = REAR_RANGE_URL
        self._rear_dip_done = False     # 阶段1：已识别第一个右转（rear 曾 >from，首次 <to）
        self._rear_turn_step = 0        # 阶段2：已完成的转向序列次数（=下一个触发阈值索引）
        self._rear_seen_far = False     # 曾见 rear > dip_from（起点后方开阔），阶段1前提
        self._rear_yaw0 = None          # 阶段1触发时刻的 yaw 基准（第1次转向序列前验证转过 ≥rear_yaw_min_deg）
        self._last_rear_yaw_wait_log_ts = 0.0  # yaw 等待日志节流
        self._last_rear_m = float("nan")
        self._last_rear_log_ts = 0.0
        self._cx_hist = deque(maxlen=10)
        self._area_hist = deque(maxlen=10)
        self.PID_init()
        self.dog = XGO(port='/dev/ttyAMA0', version="xgolite")
        self.dog_type = 'L'
        self.dog_init()
        # 应用 follow_line_config.json（HSV/裁剪/线宽 + 运动参数；s 键保存后
        # 即为下次启动默认）；wheel 模式需启用轮控
        cfg = load_follow_line_config()
        self.color.lower_black = np.array(cfg["lower"], dtype="uint8")
        self.color.upper_black = np.array(cfg["upper"], dtype="uint8")
        self.color.crop = list(cfg["crop"])
        self.color.line_width = list(cfg["line_width"])
        self.FollowLinePID = [float(v) for v in cfg["pid"]]
        self.straight_speed = int(cfg["straight_speed"])
        self.turn_move_speed = int(cfg["turn_move_speed"])
        self.direction = int(cfg["direction"])
        self.mode = str(cfg["mode"])
        self.wheel_base = int(cfg["wheel_base"])
        self.lock_wheels = bool(cfg["lock_wheels"])
        self.rear_dip_from_m = float(cfg["rear_dip_from_m"])
        self.rear_dip_to_m = float(cfg["rear_dip_to_m"])
        self.rear_turn_at_steps_m = [float(v) for v in cfg["rear_turn_at_steps_m"]]
        self.rear_yaw_min_deg = float(cfg["rear_yaw_min_deg"])
        self.rear_turn_deg = float(cfg["rear_turn_deg"])
        self.rear_hold_s = float(cfg["rear_hold_s"])
        self.PID_init()
        if self.mode == 'wheel' and hasattr(self.dog, 'enable_wheel_control'):
            self.dog.enable_wheel_control(1)
        
    def execute(self, point_x, point_y, radius):
        """
        根据检测到的圆形信息，通过PID控制器控制机械狗转向
        :param point_x: 检测到的圆形的x坐标
        :param point_y: 检测到的圆形的y坐标
        :param radius: 检测到的圆形的半径
        """
        # PID 目标 = 裁剪窗中心（crop 不对称时不再是 160，否则恒有固定偏差，
        # P 越大越猛转向、怎么调都没用）；方向用 self.direction 切换（t 键）
        crop_center = (self.color.crop[0] + self.color.crop[1]) / 2.0
        [z_Pid, _] = self.PID_controller.update([(point_x - crop_center), 0])
        z_Pid = self.direction * z_Pid
        if self.mode == 'wheel':
            self.execute_wheel(z_Pid, point_x, crop_center)
            return
        if self.dog_type == 'L':
            # 转向窗口须 ≥ 固件步态周期（~0.5s，实测 0.35s 窗口被吞、转不动）；
            # 0.5s 起步、偏差大时多转一个周期（上限 0.9s）
            runtime_x = min(0.5 + 0.02 * abs(int(z_Pid)), 0.9)
            turn_speed = int(max(min(5 * abs(z_Pid), 48), 50))
        else:
            # 同上：M 型 0.5s 起步（0.35s 实测转不动），大偏差最多 0.8s；
            # 上限 18 每次全速转向单次转角过大（0.5s 窗口×18 造成蛇形过冲），
            # 降到 15；死区 12 是速度下限
            runtime_x = min(0.5 + 0.005 * abs(int(z_Pid)), 0.8)
            # 死区钳制：XGO 固件 yaw 动作死区 12，速度 <12 固件不转向
            turn_speed = int(max(12, min(0.8 * abs(z_Pid), 15)))
        if abs(z_Pid) < 8:  # 当转向角度较小时，前进
            self.dog.turn(0)
            # self.dog.gait_type(mode)
            self.dog.move_x(self.straight_speed)
            self.log_bias(point_x, crop_center, z_Pid, detail="直行")
        elif abs(z_Pid)>=8:
            fuhao = abs(z_Pid)/z_Pid
            turn_speed = fuhao * turn_speed
            run_speed = self.turn_move_speed
            logging.warning(f'转向角{z_Pid},转向速度{turn_speed},前进速度{run_speed},运动调整时间{runtime_x}')
            # 足式一次只能一个运动指令（xgolib 源码：move_x 发 VX、turn 发 VYAW，
            # 固件后发覆盖先发；原厂 turn+move_x 连发会被 move_x 吞掉转向，实机
            # 表现为只前进不转向）。改为：先纯转向 runtime_x，再停转、短前进。
            self.dog.turn(turn_speed)
            time.sleep(runtime_x)
            self.dog.turn(0)
            self.dog.move_x(run_speed)
            time.sleep(0.15)
            self.dog.stop()
            self.log_bias(point_x, crop_center, z_Pid, detail=f"turn={turn_speed}")
        else:
            self.dog.stop()

    def lock_wheels_now(self):
        """锁 4 轮（转向序列期间用）：enable_wheel_control(1) + wheel_control(128) 抱死，
        防转向时轮子滑动漂移。128=停，>128 前进，<128 后退。
        """
        if self.lock_wheels and self.mode == 'foot':
            if hasattr(self.dog, 'enable_wheel_control'):
                self.dog.enable_wheel_control(1)
            self.dog.wheel_control([128, 128, 128, 128])

    def unlock_wheels(self):
        """解锁轮子（转向序列完成后）：enable_wheel_control(0) 恢复默认腿模式。"""
        if self.lock_wheels and self.mode == 'foot':
            if hasattr(self.dog, 'enable_wheel_control'):
                self.dog.enable_wheel_control(0)

    def log_bias(self, point_x, crop_center, z_Pid, detail=""):
        """节流（0.5s）打印线相对画面的偏左/偏右 + 实际输出（轮式 L/R、足式 turn）。"""
        now = time.time()
        if now - getattr(self, '_last_log_ts', 0.0) < 0.5:
            return
        self._last_log_ts = now
        if point_x < crop_center - 1:
            bias = '偏左'
        elif point_x > crop_center + 1:
            bias = '偏右'
        else:
            bias = '居中'
        logging.warning(
            f'[线{bias}] cx={point_x:.0f}/中心{crop_center:.0f} '
            f'z_Pid={z_Pid:.1f} lw={self.color.best_line_w:.0f}'
            f'/raw={self.color.raw_line_w:.0f} mode={self.mode} {detail}'
        )

    def execute_wheel(self, z_Pid, point_x, crop_center):
        """轮式控制：4 通道差速。通道 [左前,右前,右后,左后]，128=停、>128 前进、
        <128 后退。差速范围放开到 0~255：转向时允许一侧后退（<128）另一侧前进，
        差速大时可接近原地转，转向更灵活。

        z_Pid>0（线偏左）→ 左轮快右轮慢 → 右转……实际方向由 self.direction
        决定（z_Pid 已乘方向），实机按 t 验证。
        """
        base = self.wheel_base
        diff = int(max(-127, min(127, round(z_Pid * 2.0))))
        left = max(0, min(255, base + diff))
        right = max(0, min(255, base - diff))
        self.dog.wheel_control([left, right, right, left])
        self.log_bias(point_x, crop_center, z_Pid, detail=f"L={left} R={right}")

    def switch_mode(self):
        """foot<->wheel 切换：wheel 需 enable_wheel_control(1)；foot 若 lock_wheels
        也保持 enable(1)（锁轮需要），否则恢复 0。"""
        if self.mode == 'foot':
            self.dog.stop()
            if hasattr(self.dog, 'enable_wheel_control'):
                self.dog.enable_wheel_control(1)
            self.mode = 'wheel'
            print('mode=wheel 轮式', flush=True)
        else:
            self.dog.stop()
            if hasattr(self.dog, 'enable_wheel_control'):
                self.dog.enable_wheel_control(0)
            self.mode = 'foot'
            print('mode=foot 足式', flush=True)

    def stop_motion(self):
        """按当前方式停止：foot 用 dog.stop，wheel 用 128 停轮。"""
        if self.mode == 'wheel':
            self.dog.wheel_control([128, 128, 128, 128])
        else:
            self.dog.stop()

    def cancel(self):
        """
        重置机械狗的状态
        """
        self.dog.reset()

    def dog_init(self):
        """
        初始化机械狗的状态，包括停止、设置速度、调整位置和角度等
        """
        fm = self.dog.read_firmware()
        print(fm)
        if fm[0] == 'M':
            print('XGO-MINI')
            self.dog = XGO(port='/dev/ttyAMA0', version="xgomini")
            self.dog_type = 'M'
        else:
            print('XGO-LITE')
            self.dog = XGO(port='/dev/ttyAMA0', version="xgolite")
            self.dog_type = 'L'
        self.dog.stop()
        self.dog.pace('normal')
        self.dog.gait_type("slow_trot")
        # 低趴且前后等高：z=0 再压低（原 z=10；xgomini z 约±19.5，0 更贴地）；p=0（不用抓球 p=15——俯仰会低头翘臀，
        # 后腿看起来比前腿高）。不单独改 31/41，四腿由固件按 translation 对称落地。过低影响步态则回调 z。
        self.dog.translation('z', 0)
        self.dog.attitude('p', 0)
        time.sleep(2)

    def start_probe(self):
        """丢线后启动右转探测：先转第一格（右转）。

        主循环在确认真丢线（连续丢线 ≥5 帧）后调用；探测期间每帧推进
        probe_step，看到线即停止转弯恢复巡线。
        """
        logging.warning('[探测] 丢线→右转探测开始（每格见线即停）')
        self._probe_active = True
        self._probe_step = 0
        self.dog.turn(-16)
        time.sleep(self.step_duration)
        self.dog.turn(0)
        time.sleep(0.5)  # 转一格后停 0.5s 再检测
        self._probe_step = 1
        logging.warning(f'[探测] 第{self._probe_step}/{self.probe_steps}格')

    def probe_step(self, rgb_img):
        """探测推进：检测当前帧是否看到线；未见线则再右转一格。

        看到线 → **立即停止转弯**，交回 PID 对准线继续巡线；
        未见线且转满限格数 → 丢线即停放弃。
        """
        _, binary, circle = self.color.line_follow(rgb_img, self.hsv_range)
        if circle is not None:
            logging.warning(
                f'[探测] 第{self._probe_step}格看到线，停止转弯，恢复巡线'
            )
            self._probe_active = False
            self._finish_turn()
            return
        if self._probe_step >= self.probe_steps:
            self._probe_active = False
            logging.warning(f'[探测] {self.probe_steps} 格未见线，放弃（丢线即停）')
            self._finish_turn(advance=False)
            return
        self.dog.turn(-16)
        time.sleep(self.step_duration)
        self.dog.turn(0)
        time.sleep(0.5)  # 转一格后停 0.5s 再检测
        self._probe_step += 1
        logging.warning(f'[探测] 第{self._probe_step}/{self.probe_steps}格未见线，继续')

    def _finish_turn(self, advance=True):
        """探测结束复位。见线恢复巡线：直接交回 PID（无额外停留）；
        限格未见线放弃：保持丢线即停。
        冷却 5s：期间再丢线不重复探测（防 丢线→探测→丢线 死循环）。
        """
        self._probe_active = False
        self._probe_step = 0
        self._probe_cooldown = time.time() + 5.0
        self._lost = False
        self._lost_frame = 0
        self._cx_hist.clear()
        self._area_hist.clear()
        self.PID_controller.timeOfLastCall = None
        if advance:
            logging.warning('[探测] 见线，恢复巡线')
        else:
            logging.warning('[丢线] 探测限格内未见线，停止')


    def fetch_rear_range_m(self):
        """读雷达正后方扇区距离（m）。服务未起/失败返回 None（暴露，不装死）。"""
        try:
            with urllib.request.urlopen(self.rear_range_url, timeout=0.2) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            now = time.time()
            if now - getattr(self, "_last_rear_err_ts", 0.0) >= 2.0:
                self._last_rear_err_ts = now
                logging.warning(f"[雷达后方] 读取失败: {exc}")
            return None
        if not data.get("ok"):
            return None
        val = data.get("rear_m")
        if val is None:
            return None
        return float(val)

    def check_rear_trigger(self):
        """雷达后方第一个右转定位（2026-09-01，替代旧 armed+rising）。

        阶段1（识别第一个右转）：曾见 rear > rear_dip_from_m（起点后方开阔）后，
        首次 rear < rear_dip_to_m → 判定为第一个右转，开启功能（只一次）。
        阶段2（转向序列，可多次）：功能开启后按 rear_turn_at_steps_m 依次触发——
        rear 增大到阈值时执行 右转 90° → 停 rear_hold_s → 左转 90° 回正 → 继续
        巡线；当前默认 [0.75, 1.5] 即 0.75 一次、1.5 一次，全部完成后不再触发。
        第1次触发前加 yaw 验证：相对阶段1时刻的 yaw 基准须已转过 ≥ rear_yaw_min_deg
        （默认 80°，防刚到转角就触发）；第2次起不要求（车已过弯）。
        服务不可用时不触发（打日志）。
        """
        if not self.use_rear_trigger or self._surge_active:
            return False
        # 全部转向序列已完成：直接短路（process() 内调用无 step 前置条件，
        # 不提前返回会走到日志行对 '--' 应用 :.2f 崩溃）
        if self._rear_turn_step >= len(self.rear_turn_at_steps_m):
            return False
        rear_m = self.fetch_rear_range_m()
        if rear_m is None:
            return False
        self._last_rear_m = rear_m
        now = time.time()
        if now - self._last_rear_log_ts >= 0.3:
            self._last_rear_log_ts = now
            logging.warning(
                f"[雷达后方] rear={rear_m:.3f}m dip_done={self._rear_dip_done} "
                f"step={self._rear_turn_step}/{len(self.rear_turn_at_steps_m)} "
                f"next_at={self.rear_turn_at_steps_m[self._rear_turn_step]:.2f}m"
            )
        if not self._rear_dip_done:
            # 阶段1：曾见 rear > from（起点后方开阔）后，首次 rear < to ＝ 第一个右转
            if rear_m > self.rear_dip_from_m:
                self._rear_seen_far = True
            if self._rear_seen_far and rear_m < self.rear_dip_to_m:
                self._rear_dip_done = True
                # 记录阶段1时刻的 yaw 基准（第1次转向序列前验证转过 ≥ rear_yaw_min_deg）
                try:
                    self._rear_yaw0 = float(self.dog.read_yaw())
                    yaw0_txt = f"yaw0={self._rear_yaw0:.1f}°"
                except Exception as exc:
                    self._rear_yaw0 = None
                    yaw0_txt = f"yaw0读取失败({exc})"
                steps = "/".join(f"{s:.2f}" for s in self.rear_turn_at_steps_m)
                logging.warning(
                    f"[雷达后方] 第一个右转：rear {rear_m:.2f}m "
                    f"(曾 >{self.rear_dip_from_m:.1f}m 现 <{self.rear_dip_to_m:.1f}m)，{yaw0_txt}，功能开启："
                    f"rear≥{steps}m 依次右转{self.rear_turn_deg:.0f}°→停"
                    f"{self.rear_hold_s}s→左转{self.rear_turn_deg:.0f}°（第1次须已转过"
                    f"≥{self.rear_yaw_min_deg:.0f}°）"
                )
            return False
        # 阶段2：按步骤依次触发（每个阈值执行一次转向序列）
        if self._rear_turn_step >= len(self.rear_turn_at_steps_m):
            return False
        target = self.rear_turn_at_steps_m[self._rear_turn_step]
        if rear_m < target:
            return False
        # yaw 验证：第1次触发前要求相对阶段1基准已转过 ≥ rear_yaw_min_deg
        # （防刚到转角就触发；第2次起车已过弯不再要求）
        if self._rear_turn_step == 0 and self.rear_yaw_min_deg > 0:
            if self._rear_yaw0 is None:
                now = time.time()
                if now - self._last_rear_yaw_wait_log_ts >= 2.0:
                    self._last_rear_yaw_wait_log_ts = now
                    logging.error("[雷达后方] yaw 基准缺失（阶段1读取失败），第1次转向不触发")
                return False
            try:
                yaw_now = float(self.dog.read_yaw())
            except Exception as exc:
                logging.error(f"[雷达后方] yaw 读取失败: {exc}，第1次转向不触发")
                return False
            yaw_delta = yaw_now - self._rear_yaw0
            if abs(yaw_delta) < self.rear_yaw_min_deg:
                now = time.time()
                if now - self._last_rear_yaw_wait_log_ts >= 0.5:
                    self._last_rear_yaw_wait_log_ts = now
                    logging.warning(
                        f"[雷达后方] 等 yaw：已转过 {abs(yaw_delta):.1f}° < "
                        f"{self.rear_yaw_min_deg:.0f}°（需转过后方可第1次转向）"
                    )
                return False
            logging.warning(
                f"[雷达后方] yaw 验证通过：已转过 {abs(yaw_delta):.1f}° "
                f"≥ {self.rear_yaw_min_deg:.0f}°，允许第1次转向"
            )
        logging.warning(
            f"[雷达后方] 第{self._rear_turn_step + 1}/{len(self.rear_turn_at_steps_m)}次："
            f"rear={rear_m:.3f}m ≥ {target:.2f}m，右转 {self.rear_turn_deg:.0f}° → "
            f"停 {self.rear_hold_s}s → 左转 {self.rear_turn_deg:.0f}° 回正"
        )
        self._rear_turn_step += 1
        self._surge_active = True
        self.start_rear_turn_seq()
        self._surge_active = False
        logging.warning(
            f"[雷达后方] 第{self._rear_turn_step}/{len(self.rear_turn_at_steps_m)}次转向序列完成，继续巡线"
        )
        return True

    def check_line_surge(self, raw_lw):
        """线宽突变检测（跟踪帧调用）：raw_line_w > surge_lw_thresh 连续 surge_frames 帧 → 右转 90°。

        触发后 start_surge_turn() 阻塞完成右转（不依赖主循环状态机）。
        """
        if self._surge_active or raw_lw <= 0:
            return False
        if raw_lw > self.surge_lw_thresh:
            self._lw_surge += 1
            if self._lw_surge >= self.surge_frames:
                logging.warning(
                    f'[线宽突变] 当前线宽 {raw_lw:.0f}px > {self.surge_lw_thresh}px '
                    f'（连续{self._lw_surge}帧），右转 90°'
                )
                self._lw_surge = 0
                self._surge_active = True
                self.start_surge_turn()
                self._surge_active = False
                return True
        else:
            self._lw_surge = 0
        return False

    def turn_closed_loop(self, target_deg, speed, timeout_sec):
        """IMU yaw 闭环转向（阻塞）：以当前 yaw 为基准，|yaw 变化| ≥ target_deg 即停。

        原盲转按固定时长转 90°（turn(-16)×4.2s）是开环——转弯时机器摇晃看不到线
        也照转，转多转少无法反馈；改为读机载 IMU yaw 累积角（0x66 单轴，度）：
        相对变化即转角（累积角无需 wrap），转够角度立即 turn(0) 停。
        speed 符号决定转向方向（负=右转，同原盲转）；用 |delta| 判断方向不敏感。
        yaw 读取失败 / 超时未转够 → 立即停转并返回 False（full exposure，不静默盲转）。
        """
        try:
            yaw0 = float(self.dog.read_yaw())
        except Exception as exc:
            logging.error(f'[闭环转向] 读取起始 yaw 失败: {exc}，停转')
            self.dog.turn(0)
            return False
        target_delta = abs(target_deg)
        self.dog.turn(speed)
        t0 = time.time()
        last_delta = 0.0
        while time.time() - t0 < timeout_sec:
            time.sleep(0.1)
            try:
                yaw = float(self.dog.read_yaw())
            except Exception as exc:
                logging.error(f'[闭环转向] yaw 读取失败: {exc}，立即停转')
                self.dog.turn(0)
                return False
            last_delta = yaw - yaw0
            if abs(last_delta) >= target_delta:
                self.dog.turn(0)
                logging.warning(
                    f'[闭环转向] yaw delta {last_delta:+.1f}° ≥ {target_deg}°，停转'
                )
                return True
        self.dog.turn(0)
        logging.error(
            f'[闭环转向] 超时 {timeout_sec:.0f}s 未转够 {target_deg}°'
            f'（yaw delta={last_delta:+.1f}°），停转'
        )
        return False

    def start_surge_turn(self):
        """线宽突变 → IMU yaw 闭环右转 90°（不再盲转固定时长）后恢复巡线。

        转完后短暂稳定，PID 重置；若转角偏差导致线不在视野，由丢线探测兜底。
        """
        ok = self.turn_closed_loop(
            self.surge_turn_deg, self.surge_turn_speed, self.surge_turn_timeout
        )
        time.sleep(0.3)
        self.PID_controller.timeOfLastCall = None
        self._cx_hist.clear()
        self._area_hist.clear()
        logging.warning(f'[线宽右转] 90° 闭环转弯完成（ok={ok}），继续巡线')

    def start_rear_turn_seq(self):
        """雷达后方第一个右转后的转向序列：右转 90° → 停 hold 秒 → 左转 90° 回正 → 继续巡线。

        锁轮时机（2026-09-01）：转向序列期间锁 4 轮（enable_wheel_control(1) +
        wheel_control 128 抱死）防转向时轮子滑动漂移；左转回正完成后解锁
        （enable_wheel_control(0) 恢复默认，平时行进不锁——全程锁轮会拖慢速度）。
        两段转向都用 IMU yaw 闭环（speed 负=右转、正=左转；|yaw delta| ≥ rear_turn_deg
        即停），每段独立超时，读取失败/超时停转打日志不静默。
        """
        self.lock_wheels_now()  # 右转前先锁轮
        ok_r = self.turn_closed_loop(
            self.rear_turn_deg, -abs(self.rear_turn_speed), self.rear_turn_timeout
        )
        logging.warning(
            f'[雷达后方] 右转 {self.rear_turn_deg:.0f}° 完成（ok={ok_r}），停 {self.rear_hold_s}s'
        )
        time.sleep(self.rear_hold_s)
        ok_l = self.turn_closed_loop(
            self.rear_turn_deg, abs(self.rear_turn_speed), self.rear_turn_timeout
        )
        self.unlock_wheels()  # 左转回正完成后解锁
        time.sleep(0.3)
        self.PID_controller.timeOfLastCall = None
        self._cx_hist.clear()
        self._area_hist.clear()
        logging.warning(
            f'[雷达后方] 左转 {self.rear_turn_deg:.0f}° 回正完成（ok={ok_l}），继续巡线'
        )

    def process(self, rgb_img, action):
        """
        处理输入的RGB图像，根据按键事件和跟踪状态进行相应操作

        :param rgb_img: 输入的RGB图像
        :param action: 动作值（当前未充分使用，可后续扩展）
        :return: 处理后的RGB图像和二值图像
        """
        binary = []
        rgb_img = cv.resize(rgb_img, (320, 240))
        if button.press_d():
            self.Track_state = 'init'
            print('state:init')
        if button.press_c():
            self.Track_state = 'color'
            print('state:color')
        if button.press_a():
            self.Track_state = 'tracking'
            print('state:tracking')

        if self.Track_state == 'tracking':
            # print(self.hsv_range)
            rgb_img, binary, self.circle = self.color.line_follow(rgb_img, self.hsv_range)
            if self.circle is not None:
                if self._lost:
                    # 状态恢复：丢线->看到线，打一次恢复日志（含丢线持续时长）
                    logging.warning(
                        f'[恢复寻线] 丢线持续 {time.time() - self._lost_ts:.1f}s'
                    )
                    self._lost = False
                    self._lost_frame = 0
                # 记录 cx 历史（丢线时用于弯道判定）
                self._cx_hist.append(self.circle[0])
                self._area_hist.append(self.color.best_area)
                # 雷达后方第一个右转定位（优先）；线宽突变可选（默认关）
                if self.check_rear_trigger():
                    pass
                elif self.use_line_surge:
                    self.check_line_surge(self.color.raw_line_w)
                #print('检测到线条，巡线运动')
                self.execute(self.circle[0], self.circle[1], self.circle[2])
            else:
                if not self._lost:
                    # 状态变化：只在丢线开始时打一次，避免每帧刷屏
                    self._lost = True
                    self._lost_ts = time.time()
                    self._cx_hist.clear()
                    self._area_hist.clear()
                    logging.warning(
                        f'[丢线开始] mode={self.mode} P={self.FollowLinePID[0]:.1f} '
                        f'D={self.FollowLinePID[2]:.1f} '
                        f'V={self.color.upper_black[2]} crop={self.color.crop} '
                        f'lw={self.color.line_width} spd={self.straight_speed}/{self.turn_move_speed} '
                        f'dir={"+" if self.direction > 0 else "-"}'
                    )
                # 连续丢线计数：≥5 帧才确认真丢线（主循环据此启动探测）；
                # 线边缘闪烁的抖动丢线（1-2 帧即恢复）不会触发探测右转
                self._lost_frame += 1
                # 丢线即停；主循环在确认丢线后启动右转探测（弯道确认）
                self.PID_controller.timeOfLastCall = None  # 重见线时 PID 全新启动
                self.stop_motion()
        return rgb_img, binary

    def Reset(self):
        """
        重置巡线检测的相关状态和参数，包括PID控制器、跟踪状态、HSV范围和机械狗状态等
        """
        self.PID_init()
        self.Track_state = 'init'
        self.hsv_range = ()
        self.dog_init()

    def PID_init(self):
        """
        初始化PID控制器的参数
        """
        self.PID_controller = simplePID(
            [0, 0],
            [self.FollowLinePID[0] / 1.0 / self.scale, 0],
            [self.FollowLinePID[1] / 1.0 / self.scale, 0],
            [self.FollowLinePID[2] / 1.0 / self.scale, 0])

#------------------主程序-------------------

def read_key(timeout=0.0):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return ""
    return sys.stdin.read(1)


class TeeLog:
    """stdout/stderr 双路 tee：原样输出 + 写入共享环形缓冲（Q 键保存用）。"""

    def __init__(self, target, shared):
        self.target = target
        self.shared = shared

    def write(self, s):
        self.shared.append(s)
        self.target.write(s)

    def flush(self):
        self.target.flush()


def save_logs(shared_buf):
    """Q 键：保存日志快照，滚动只保留 2 份（_1 最新，_2 次新，多的删除）。"""
    log_dir = Path(__file__).resolve().parent
    log1 = log_dir / "follow_line_log_1.log"
    log2 = log_dir / "follow_line_log_2.log"
    if log1.exists():
        if log2.exists():
            log2.unlink()
        log1.rename(log2)
    with open(log1, "w", encoding="utf-8") as f:
        f.write("".join(shared_buf))
    print(f"日志已保存: {log1}（滚动保留 2 份）", flush=True)


def print_params(line_detect):
    pid = line_detect.FollowLinePID
    sys.stdout.write(
        f"{time.strftime('%H:%M:%S')} "
        f"P={pid[0]:.1f} D={pid[2]:.1f} "
        f"V={line_detect.color.upper_black[2]} "
        f"crop={line_detect.color.crop} "
        f"lw={line_detect.color.line_width} "
        f"spd={line_detect.straight_speed}/{line_detect.turn_move_speed} "
        f"dir={'+' if line_detect.direction > 0 else '-'}\n"
    )
    sys.stdout.flush()


if __name__ == '__main__':
    # 日志 tee：print/logging 都进环形缓冲，Q 键保存
    shared_buf = deque(maxlen=8000)
    sys.stdout = TeeLog(sys.__stdout__, shared_buf)
    sys.stderr = TeeLog(sys.__stderr__, shared_buf)
    # 带时间戳（毫秒）输出，日志可直接读时序/丢线时长
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s.%(msecs)03d %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    # 初始化Picamera2
    picam2 = Picamera2()
    picam2.configure(
        picam2.create_preview_configuration(main={"format": "RGB888", "size": (320, 240)})
    )
    picam2.start()
    print("摄像头初始化完毕")
    line_detect = LineDetect()

    # 双推流：8090 带框原画面 + 8091 阈值（二值）画面，浏览器两个窗口同时看
    output_orig = StreamingOutput()
    output_mask = StreamingOutput()
    try:
        httpd_orig = StreamingServer(("0.0.0.0", STREAM_PORT), StreamingHandler, output_orig)
        httpd_mask = StreamingServer(("0.0.0.0", MASK_PORT), StreamingHandler, output_mask)
    except OSError as exc:
        raise RuntimeError(
            f"cannot bind {STREAM_PORT}/{MASK_PORT} (still oumax-camera?). {exc}"
        ) from exc
    threading.Thread(target=httpd_orig.serve_forever, daemon=True).start()
    threading.Thread(target=httpd_mask.serve_forever, daemon=True).start()
    print(
        f"原画面推流: http://192.168.137.157:{STREAM_PORT}/stream.mjpg\n"
        f"阈值画面推流: http://192.168.137.157:{MASK_PORT}/stream.mjpg",
        flush=True,
    )

    settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        print("边走边调：p/o P±1  R/F P±50  i/u D±0.1  [ ] 直行±1  - = 转向±1  t 方向  m 轮/足式  s 保存参数(下次默认)  Q 保存日志  Ctrl-C退出")
        print_params(line_detect)
        _fps_cnt = 0
        _fps_t0 = time.time()
        _stream_cnt = 0
        while True:
            start = time.time()
            # 从Picamera2获取图像
            frame = picam2.capture_array()
            # FPS 统计（每 3s 报一次）
            _fps_cnt += 1
            now = time.time()
            if now - _fps_t0 >= 3.0:
                fps = _fps_cnt / (now - _fps_t0)
                logging.warning(f'[FPS] {fps:.1f} 帧/秒（含推流）')
                _fps_cnt = 0
                _fps_t0 = now
            # 丢线后右转探测（弯道确认）：连续丢线 ≥5 帧（约 0.5s，确认真丢线）
            # 才启动；每格转后抓帧检测，见线即确认；线边缘闪烁的抖动丢线
            # （1-2 帧恢复）不触发；冷却期内再丢线不重复探测
            if (
                line_detect._lost
                and line_detect._lost_frame >= 5
                and not line_detect._probe_active
                and time.time() > line_detect._probe_cooldown
            ):
                line_detect.start_probe()
                continue
            if line_detect._probe_active:
                line_detect.probe_step(frame)
                continue
            # 雷达后方第一个右转：每帧检查（不依赖是否见线），阶段2按 rear_turn_at_steps_m
            # 依次执行 右转90°→停2s→左转90° 转向序列（默认 0.75 一次、1.5 一次）
            if (
                line_detect.use_rear_trigger
                and line_detect._rear_turn_step < len(line_detect.rear_turn_at_steps_m)
            ):
                line_detect.check_rear_trigger()
            action = 32
            frame, binary = line_detect.process(frame, action)

            # 推流降频：每 2 帧推一次（浏览器 15fps 足够，省 imencode 开销提主循环帧率）
            _stream_cnt += 1
            if _stream_cnt % 2:
                continue

            # 实时线宽：过滤后 best / 突变用 raw / 阈值 thresh（8090+8091 水印 + 终端节流）
            lw = float(line_detect.color.best_line_w)
            raw_lw = float(line_detect.color.raw_line_w)
            lw_th = float(line_detect.surge_lw_thresh)
            lw_txt = f"lw={lw:.0f} raw={raw_lw:.0f}/{lw_th:.0f}"
            now_lw = time.time()
            if now_lw - getattr(line_detect, "_last_lw_log_ts", 0.0) >= 0.3:
                line_detect._last_lw_log_ts = now_lw
                logging.warning(f"[线宽] {lw_txt} crop={line_detect.color.crop}")

            # 推流 8090：画框后的 RGB 帧，加水印区分原始流 + 实时线宽
            cv.putText(
                frame, "FOLLOW " + line_detect.mode + " " + lw_txt,
                (4, 18), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv.LINE_AA,
            )
            ok, jpeg = cv.imencode(
                ".jpg", cv.cvtColor(frame, cv.COLOR_RGB2BGR),
                [int(cv.IMWRITE_JPEG_QUALITY), 80],
            )
            if ok:
                output_orig.set_frame(jpeg.tobytes())

            # 推流 8091：阈值（二值掩码）画面 + 参数/线宽水印
            if isinstance(binary, np.ndarray):
                mask_bgr = cv.cvtColor(binary, cv.COLOR_GRAY2BGR)
                cv.putText(
                    mask_bgr,
                    f"MASK V={line_detect.color.upper_black[2]} "
                    f"crop={line_detect.color.crop} {lw_txt}",
                    (4, 18), cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv.LINE_AA,
                )
                ok2, jpeg2 = cv.imencode(
                    ".jpg", mask_bgr,
                    [int(cv.IMWRITE_JPEG_QUALITY), 80],
                )
                if ok2:
                    output_mask.set_frame(jpeg2.tobytes())

            if button.press_b():
                line_detect.cancel()
                break

            key = read_key(0.0)
            if key == "\x03":
                break
            if key == "p":
                line_detect.FollowLinePID[0] += 1
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "o":
                line_detect.FollowLinePID[0] = max(0, line_detect.FollowLinePID[0] - 1)
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "R":
                line_detect.FollowLinePID[0] += 50
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "F":
                line_detect.FollowLinePID[0] = max(0, line_detect.FollowLinePID[0] - 50)
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "i":
                line_detect.FollowLinePID[2] += 0.1
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "u":
                line_detect.FollowLinePID[2] = max(0, round(line_detect.FollowLinePID[2] - 0.1, 1))
                line_detect.PID_init()
                print_params(line_detect)
            elif key == "[":
                line_detect.straight_speed = min(30, line_detect.straight_speed + 1)
                print_params(line_detect)
            elif key == "]":
                line_detect.straight_speed = max(0, line_detect.straight_speed - 1)
                print_params(line_detect)
            elif key == "-":
                line_detect.turn_move_speed = min(30, line_detect.turn_move_speed + 1)
                print_params(line_detect)
            elif key == "=":
                line_detect.turn_move_speed = max(0, line_detect.turn_move_speed - 1)
                print_params(line_detect)
            elif key == "t":
                line_detect.direction = -line_detect.direction
                print_params(line_detect)
            elif key == "m":
                line_detect.switch_mode()
                print_params(line_detect)
            elif key == "s":
                # 保存当前参数（视觉 + 运动）到 follow_line_config.json，下次启动即默认
                save_follow_line_config(line_detect)
            elif key == "Q":
                save_logs(shared_buf)

    except KeyboardInterrupt:
        print("程序被手动终止")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        # 先停运动：move_x/turn/wheel_control 是持续指令，不显式停摄像头停了狗还在走
        line_detect.stop_motion()
        print("dog stopped", flush=True)
        # 退出自动保存日志（Q 键可手动保存；Ctrl-C 退出不再丢日志）
        try:
            save_logs(shared_buf)
        except Exception as exc:
            print(f"save_logs failed: {exc}", flush=True)
        try:
            httpd_orig.shutdown()
            httpd_mask.shutdown()
        except Exception:
            pass
        # 恢复固件默认：wheel 使能状态不残留（2026-08-16 教训：锁轮/wheel 模式残留
        # 导致后续主流程 move_x 失效）；wheel 模式退出也一并恢复 0
        if hasattr(line_detect.dog, 'enable_wheel_control'):
            try:
                line_detect.dog.enable_wheel_control(0)
            except Exception as exc:
                print(f"enable_wheel_control(0) 恢复失败: {exc}", flush=True)
        # SIGINT 免疫且不恢复：解释器退出时 picamera2 的 atexit close() 会 join
        # 预览线程，此时 Ctrl-C 会打断它导致 "Exception ignored in atexit callback"
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        picam2.stop()
        print("摄像头已停止")