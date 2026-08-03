#!/usr/bin/env python3
"""Explicitly armed continuous keyboard control with dual stop watchdogs.

Direction keys rely on terminal auto-repeat while held. Each repeat refreshes
the command. When those refreshes stop, this node sends zero gamepad frames
after <=0.25 s; the host OUMAX UDP service independently stops after its
existing 0.35 s watchdog if this node or terminal fails.
"""

import json
import select
import socket
import sys
import termios
import threading
import time
import tty
from urllib.error import URLError
from urllib.request import urlopen

import rospy


_HEALTH_URL = "http://127.0.0.1:8765/health"
_GAMEPAD_ADDRESS = ("127.0.0.1", 8766)
_REFRESH_PERIOD_SEC = 0.10


class LocalOumaxGamepad:
    """Loopback-only UDP transport for OUMAX's watchdog-protected gamepad API."""

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect(_GAMEPAD_ADDRESS)

    def verify_identity(self):
        try:
            with urlopen(_HEALTH_URL, timeout=0.25) as response:
                health = json.loads(response.read().decode("utf-8"))
        except (URLError, OSError, ValueError) as error:
            raise RuntimeError("cannot reach local OUMAX manual service: {}".format(error))
        if (
            not health.get("ok")
            or health.get("serial_port") != "/dev/ttyAMA0"
            or health.get("manual_port") != 8765
            or health.get("gamepad_udp_port") != 8766
        ):
            raise RuntimeError("unexpected OUMAX manual-service identity: {}".format(health))

    def send(self, x=0.0, yaw=0.0):
        payload = {
            "kind": "gamepad",
            "x": max(-1.0, min(1.0, x)),
            "y": 0.0,
            "yaw": max(-1.0, min(1.0, yaw)),
            "drive_mode": "dog",
            "name": "raicom-continuous-keyboard",
        }
        self._socket.send(json.dumps(payload).encode("utf-8"))

    def close(self):
        self._socket.close()


class ContinuousKeyboardTeleop:
    """Held-key teleoperation guarded by local and host-side watchdogs."""

    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError("real motion is disabled; use enable_motion:=true after safety confirmation")
        self._linear_value = self._bounded_param("~linear_motion_value", 17.0, 1.0, 25.0)
        self._yaw_value = self._bounded_param("~yaw_motion_value", 55.0, 1.0, 70.0)
        self._hold_timeout = self._bounded_param("~hold_timeout_sec", 0.25, 0.10, 0.25)
        self._gamepad = LocalOumaxGamepad()
        self._gamepad.verify_identity()
        self._armed = False
        self._arm_requested_until = 0.0
        self._command_id = 0
        self._stop_timer = None
        self._last_refresh_at = 0.0
        self._active_label = ""
        self._lock = threading.RLock()
        rospy.on_shutdown(self._lock_and_stop)

    @staticmethod
    def _bounded_param(name, default, minimum, maximum):
        value = float(rospy.get_param(name, default))
        if not minimum <= value <= maximum:
            raise ValueError("{} must be within [{}, {}]".format(name, minimum, maximum))
        return value

    def _send_stop_locked(self, reason):
        self._command_id += 1
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None
        self._active_label = ""
        self._last_refresh_at = 0.0
        for _ in range(3):
            try:
                self._gamepad.send()
            except OSError as error:
                rospy.logerr("OUMAX UDP stop failed (%s): %s", reason, error)
                break
        rospy.logwarn("OUMAX continuous stop requested: %s", reason)

    def _lock_and_stop(self, reason="ROS shutdown"):
        with self._lock:
            self._armed = False
            self._arm_requested_until = 0.0
            self._send_stop_locked(reason)

    def _stop_after_hold(self, command_id):
        with self._lock:
            if command_id != self._command_id:
                return
            self._send_stop_locked("key refresh timeout")

    def _request_arm(self):
        self._arm_requested_until = time.monotonic() + 5.0
        print(
            "ARM REQUESTED: continuous real motion is possible. Confirm clear space, "
            "people away and emergency stop/power-off reachable. Press y within 5 seconds."
        )

    def _confirm_arm(self):
        if time.monotonic() > self._arm_requested_until:
            print("Arm request expired. Press u, then y within 5 seconds.")
            return
        self._armed = True
        self._arm_requested_until = 0.0
        print(
            "ARMED (CONTINUOUS): w/s refresh XGO ±{:.0f}, a/d refresh yaw ±{:.0f}. "
            "Terminal repeats are limited to 10 Hz; stopping repeats sends zero within {:.2f}s locally / 0.35s host watchdog. "
            "Space/x/Ctrl-C locks and stops.".format(
                self._linear_value, self._yaw_value, self._hold_timeout
            )
        )

    def _refresh_command(self, label, x, yaw):
        if not self._armed:
            print("LOCKED: press u, then y before continuous motion.")
            return
        with self._lock:
            now = time.monotonic()
            if (
                label == self._active_label
                and now - self._last_refresh_at < _REFRESH_PERIOD_SEC
            ):
                return
            self._command_id += 1
            command_id = self._command_id
            if self._stop_timer is not None:
                self._stop_timer.cancel()
            try:
                self._gamepad.send(x=x, yaw=yaw)
            except OSError as error:
                self._lock_and_stop("UDP motion refresh failed")
                print("MOTION REJECTED: {}".format(error))
                return
            self._last_refresh_at = now
            self._active_label = label
            self._stop_timer = threading.Timer(
                self._hold_timeout, self._stop_after_hold, args=(command_id,)
            )
            self._stop_timer.daemon = True
            self._stop_timer.start()
        rospy.logwarn_throttle(1.0, "CONTINUOUS OUMAX refresh: %s", label)

    @staticmethod
    def _read_key():
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        return sys.stdin.read(1) if ready else ""

    def run(self):
        bindings = {
            "w": ("intended forward", self._linear_value / 25.0, 0.0),
            "s": ("intended reverse", -self._linear_value / 25.0, 0.0),
            "a": ("intended left turn", 0.0, self._yaw_value / 80.0),
            "d": ("intended right turn", 0.0, -self._yaw_value / 80.0),
        }
        if not sys.stdin.isatty():
            raise RuntimeError("continuous keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        print(
            "CONTINUOUS keyboard teleop is LOCKED. Press u, then y; "
            "hold w/s/a/d so terminal repeats refresh motion; stopping repeats stops it."
        )
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if not key:
                    continue
                if key in ("\x03", " ", "x"):
                    self._lock_and_stop("emergency stop")
                elif key == "u":
                    self._request_arm()
                elif key == "y":
                    self._confirm_arm()
                elif key in bindings:
                    self._refresh_command(*bindings[key])
                else:
                    print(
                        "Keys: u then y arm; hold w/s/a/d for terminal repeat refresh; "
                        "stop repeats to stop; space/x/Ctrl-C stop and lock."
                    )
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._lock_and_stop("node exit")
            self._gamepad.close()


def main():
    rospy.init_node("robot_dog_keyboard_continuous")
    try:
        ContinuousKeyboardTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("Continuous keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
