#!/usr/bin/env python3
"""订阅 /scan，计算雷达正后方扇区距离，HTTP 暴露给巡线等非 ROS 进程。

默认：扇区中心 180°（正后）、半宽 15°，取扇区内有效 range 的中位数。
GET /rear  -> {"ok": true, "rear_m": 1.23, "n": 12, "stamp": ...}
GET /health -> {"ok": true}

用法（容器内，需已有 /scan）:
  rosrun robot_dog_navigation lidar_rear_range_http.py
  # 或
  python3 lidar_rear_range_http.py _port:=8767
"""
from __future__ import annotations

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import rospy
from sensor_msgs.msg import LaserScan


def _wrap_pi(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class RearRangeState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.rear_m = float("nan")
        self.n = 0
        self.stamp = 0.0
        self.ok = False


STATE = RearRangeState()


class RearHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: N802 — quiet access log
        rospy.logdebug("%s - " + fmt, self.address_string(), *args)

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/health", "/"):
            self._send_json(200, {"ok": True, "service": "lidar_rear_range"})
            return
        if path == "/rear":
            with STATE.lock:
                payload = {
                    "ok": STATE.ok,
                    "rear_m": None if math.isnan(STATE.rear_m) else round(STATE.rear_m, 4),
                    "n": STATE.n,
                    "stamp": STATE.stamp,
                }
            self._send_json(200, payload)
            return
        self._send_json(404, {"ok": False, "error": "not found"})


def rear_median_m(scan: LaserScan, center_rad: float, half_width_rad: float) -> tuple[float, int]:
    """扇区内有效 range 的中位数；无有效点返回 (nan, 0)。"""
    vals = []
    angle = scan.angle_min
    for r in scan.ranges:
        if scan.range_min < r < scan.range_max and math.isfinite(r):
            if abs(_wrap_pi(angle - center_rad)) <= half_width_rad:
                vals.append(float(r))
        angle += scan.angle_increment
    if not vals:
        return float("nan"), 0
    vals.sort()
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid], len(vals)
    return 0.5 * (vals[mid - 1] + vals[mid]), len(vals)


def main() -> None:
    rospy.init_node("lidar_rear_range_http")
    port = int(rospy.get_param("~port", 8767))
    scan_topic = rospy.get_param("~scan_topic", "/scan")
    center_deg = float(rospy.get_param("~rear_center_deg", 180.0))
    half_width_deg = float(rospy.get_param("~rear_half_width_deg", 15.0))
    center_rad = math.radians(center_deg)
    half_width_rad = math.radians(half_width_deg)

    def on_scan(msg: LaserScan) -> None:
        rear_m, n = rear_median_m(msg, center_rad, half_width_rad)
        with STATE.lock:
            STATE.rear_m = rear_m
            STATE.n = n
            STATE.stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.get_time()
            STATE.ok = n > 0 and math.isfinite(rear_m)

    rospy.Subscriber(scan_topic, LaserScan, on_scan, queue_size=1)

    server = HTTPServer(("0.0.0.0", port), RearHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rospy.loginfo(
        "lidar_rear_range_http: %s -> http://0.0.0.0:%d/rear  center=%.1f° ±%.1f°",
        scan_topic,
        port,
        center_deg,
        half_width_deg,
    )
    rospy.on_shutdown(server.shutdown)
    rospy.spin()


if __name__ == "__main__":
    main()
