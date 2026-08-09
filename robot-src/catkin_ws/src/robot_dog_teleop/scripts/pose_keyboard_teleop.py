#!/usr/bin/env python3
"""Explicitly armed keyboard pose control for the XGO dog through OUMAX's local API.

This process never opens a serial port.  It sends bounded, step-wise ``kind=motor``
requests (one servo id plus a clamped angle) only to the already-running local
OUMAX manual service, which remains the sole owner of ``/dev/ttyAMA0``.  The 15
joints j1..j15 are stepped with w/s (fine) and q/e (coarse), held within their
servo ranges, and the current pose can be appended to a file with r.  Requests
are sent only while armed (u then y), mirroring the arm keyboard flow.
"""

import json
import select
import sys
import termios
import threading
import time
import tty
from urllib.error import URLError
from urllib.request import Request, urlopen

import rospy


_MANUAL_BASE_URL = "http://127.0.0.1:8765"
_HEALTH_URL = _MANUAL_BASE_URL + "/health"
_COMMAND_URL = _MANUAL_BASE_URL + "/command"

_JOINT_SPECS = (
    ("j1", 11, -73.0, 57.0, 0.0),
    ("j2", 12, -66.0, 93.0, 0.0),
    ("j3", 13, -31.0, 31.0, 0.0),
    ("j4", 21, -73.0, 57.0, 0.0),
    ("j5", 22, -66.0, 93.0, 0.0),
    ("j6", 23, -31.0, 31.0, 0.0),
    ("j7", 31, -73.0, 57.0, 0.0),
    ("j8", 32, -66.0, 93.0, 0.0),
    ("j9", 33, -31.0, 31.0, 0.0),
    ("j10", 41, -73.0, 57.0, 0.0),
    ("j11", 42, -66.0, 93.0, 0.0),
    ("j12", 43, -31.0, 31.0, 0.0),
    ("j13", 51, -65.0, 65.0, 0.0),
    ("j14", 52, -115.0, 70.0, 70.0),
    ("j15", 53, -85.0, 100.0, -85.0),
)

_HELP_TEXT = (
    "按键说明：\n"
    "  [ / ]    循环选择当前关节（j1..j15）\n"
    "  w / s    细步调整当前关节角度（默认 1 度，可用 ~fine_step 覆盖）\n"
    "  q / e    粗步调整当前关节角度（默认 10 度，可用 ~coarse_step 覆盖）\n"
    "  m        所有关节回中（恢复默认姿态）\n"
    "  r        记录当前姿态到文件（追加一行，含时间戳）\n"
    "  u        请求武装；5 秒内按 y 确认后，按键才会发送真实舵机命令\n"
    "  空格/x   立即锁定并停止（不再发送任何命令）\n"
    "  Ctrl-C   第一次锁定并停止，第二次退出程序\n"
    "  h        显示本帮助"
)


class OumaxManualClient:
    """Minimal client for the pre-existing, local, serial-owning service."""

    @staticmethod
    def _request(url, payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
        with urlopen(request, timeout=0.25) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        if not decoded.get("ok", False):
            raise RuntimeError(decoded.get("message", "manual service rejected request"))
        return decoded

    def verify_identity(self):
        try:
            health = self._request(_HEALTH_URL)
        except (URLError, OSError, ValueError, RuntimeError) as error:
            raise RuntimeError("cannot reach local OUMAX manual service: {}".format(error))
        if health.get("serial_port") != "/dev/ttyAMA0" or health.get("manual_port") != 8765:
            raise RuntimeError("unexpected OUMAX manual-service identity: {}".format(health))

    def motor_move(self, servo_id, angle):
        return self._request(
            _COMMAND_URL,
            {"kind": "motor", "id": servo_id, "angle": angle},
        )


class PoseKeyboardTeleop:
    """Step-wise keyboard pose control with local confirmation."""

    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError(
                "real motion is disabled; use enable_motion:=true only after "
                "on-site safety confirmation"
            )
        self._fine_step = self._positive_param("~fine_step", 1.0)
        self._coarse_step = self._positive_param("~coarse_step", 10.0)
        self._record_file = rospy.get_param("~record_file", "/tmp/xgo_poses.log")
        self._angles = [spec[4] for spec in _JOINT_SPECS]
        self._selected = 0
        self._client = OumaxManualClient()
        self._client.verify_identity()
        self._armed = False
        self._arm_requested_until = 0.0
        self._ctrl_c_exit_armed = False
        self._lock = threading.RLock()
        rospy.on_shutdown(self._shutdown_stop)

    @staticmethod
    def _positive_param(name, default):
        value = float(rospy.get_param(name, default))
        if value <= 0.0:
            raise ValueError("{} must be positive".format(name))
        return value

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    @staticmethod
    def _format_angle(value):
        return "{:g}".format(value)

    def _pose_line(self):
        return ", ".join(
            "{} {}".format(name, self._format_angle(self._angles[index]))
            for index, (name, _, _, _, _) in enumerate(_JOINT_SPECS)
        )

    def _pose_lines(self):
        first = ", ".join(
            "{} {}".format(_JOINT_SPECS[index][0], self._format_angle(self._angles[index]))
            for index in range(0, 8)
        )
        second = ", ".join(
            "{} {}".format(_JOINT_SPECS[index][0], self._format_angle(self._angles[index]))
            for index in range(8, len(_JOINT_SPECS))
        )
        return first, second

    def _status_line(self):
        return "关节 {} 角度 {} 细步 {} 粗步 {} {}".format(
            _JOINT_SPECS[self._selected][0],
            self._format_angle(self._angles[self._selected]),
            self._format_angle(self._fine_step),
            self._format_angle(self._coarse_step),
            "已武装" if self._armed else "已锁定",
        )

    def _redraw(self):
        first, second = self._pose_lines()
        sys.stdout.write(
            "\r\x1b[K{}\n\x1b[K{}\n\x1b[K{}\x1b[2A".format(
                self._status_line(), first, second
            )
        )
        sys.stdout.flush()

    def _apply_joint(self, index, value):
        if not self._armed:
            with self._lock:
                self._angles[index] = value
            return True

        def send():
            self._client.motor_move(_JOINT_SPECS[index][1], value)
        try:
            with self._lock:
                send()
        except (URLError, OSError, ValueError, RuntimeError) as error:
            self._lock_and_stop("motor command failed")
            print("MOTOR COMMAND REJECTED: {}".format(error))
            return False
        with self._lock:
            self._angles[index] = value
        rospy.logwarn("REAL OUMAX motor command accepted: %s %.1f", _JOINT_SPECS[index][0], value)
        return True

    def _step_selected(self, delta):
        index = self._selected
        current = self._angles[index]
        target = self._clamp(current + delta, _JOINT_SPECS[index][2], _JOINT_SPECS[index][3])
        if target == current:
            return False
        return self._apply_joint(index, target)

    def _select_joint(self, offset):
        self._selected = (self._selected + offset) % len(_JOINT_SPECS)
        return True

    def _center_all(self):
        changed = False
        for index, spec in enumerate(_JOINT_SPECS):
            if self._angles[index] == spec[4]:
                continue
            if not self._apply_joint(index, spec[4]):
                return False
            changed = True
        return changed

    def _record_pose(self):
        line = "[{}] {}".format(
            time.strftime("%Y-%m-%d %H:%M:%S"), self._pose_line()
        )
        try:
            with open(self._record_file, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as error:
            print("RECORD FAILED: {}".format(error))
            return
        print("RECORDED: {}".format(line))
        self._redraw()

    def _lock_and_stop(self, reason):
        with self._lock:
            self._armed = False
            self._arm_requested_until = 0.0
        rospy.logwarn("Pose keyboard teleop locked and stopped: %s", reason)

    def _shutdown_stop(self):
        self._lock_and_stop("ROS shutdown")

    def _request_arm(self):
        self._arm_requested_until = time.monotonic() + 5.0
        print(
            "ARM REQUESTED: real servo motion is possible. Confirm clear space, "
            "people away and emergency stop/power-off reachable. Press y within 5 seconds."
        )
        self._redraw()

    def _confirm_arm(self):
        if time.monotonic() > self._arm_requested_until:
            print("Arm request expired. Press u, then y within 5 seconds.")
            return
        self._armed = True
        self._arm_requested_until = 0.0
        print(
            "ARMED (REAL OUMAX MOTORS): w/s fine +/-{} deg, q/e coarse +/-{} deg, "
            "[/] select joint, m center all, r record. Space or x locks without "
            "moving; Ctrl-C locks, twice to exit.".format(
                self._format_angle(self._fine_step),
                self._format_angle(self._coarse_step),
            )
        )
        self._redraw()

    @staticmethod
    def _read_key():
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        return sys.stdin.read(1) if ready else ""

    def run(self):
        if not sys.stdin.isatty():
            raise RuntimeError("pose keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        print(
            "POSE keyboard teleop is LOCKED. Press u, then y to arm; space/x lock; "
            "Ctrl-C stops, twice to exit. Press h for help."
        )
        self._redraw()
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if not key:
                    continue
                if key == "\x03":
                    self._lock_and_stop("emergency stop")
                    if self._ctrl_c_exit_armed:
                        print("Ctrl-C pressed twice: exiting pose keyboard teleop.")
                        break
                    self._ctrl_c_exit_armed = True
                    print("Emergency stop sent. Press Ctrl-C again to exit the program.")
                    self._redraw()
                elif key in (" ", "x"):
                    self._lock_and_stop("emergency stop")
                    self._redraw()
                elif key == "u":
                    self._request_arm()
                elif key == "y":
                    self._confirm_arm()
                elif key == "[":
                    if self._select_joint(-1):
                        self._redraw()
                elif key == "]":
                    if self._select_joint(1):
                        self._redraw()
                elif key == "w":
                    if self._step_selected(self._fine_step):
                        self._redraw()
                elif key == "s":
                    if self._step_selected(-self._fine_step):
                        self._redraw()
                elif key == "q":
                    if self._step_selected(self._coarse_step):
                        self._redraw()
                elif key == "e":
                    if self._step_selected(-self._coarse_step):
                        self._redraw()
                elif key == "m":
                    if self._center_all():
                        self._redraw()
                elif key == "r":
                    self._record_pose()
                elif key == "h":
                    print(_HELP_TEXT)
                    self._redraw()
                else:
                    print("未知按键：按 h 查看帮助。")
                    self._redraw()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._lock_and_stop("node exit")


def main():
    rospy.init_node("robot_dog_pose_keyboard_teleop")
    try:
        PoseKeyboardTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("Pose keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
