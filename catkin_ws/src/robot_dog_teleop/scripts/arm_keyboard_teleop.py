#!/usr/bin/env python3
"""Explicitly armed keyboard control for the XGO arm through OUMAX's local API.

This process never opens a serial port.  It sends bounded, step-wise ``kind=arm``
requests only to the already-running local OUMAX manual service, which remains
the sole owner of ``/dev/ttyAMA0``.  The arm API accepts point targets (0..255
for x/z/claw), so a key press moves the arm by one bounded step and the arm
holds its last pose until the next step; there is no continuous motion.
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

    def arm_cartesian(self, x, z):
        return self._request(
            _COMMAND_URL,
            {"kind": "arm", "command": "cartesian", "x": x, "z": z},
        )

    def arm_claw(self, claw):
        return self._request(
            _COMMAND_URL,
            {"kind": "arm", "command": "claw", "claw": claw},
        )

    def arm_mid(self):
        return self._request(_COMMAND_URL, {"kind": "arm", "command": "mid"})


class ArmKeyboardTeleop:
    """Step-wise keyboard arm control with local confirmation."""

    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError(
                "real motion is disabled; use enable_motion:=true only after "
                "on-site safety confirmation"
            )
        self._arm_step = self._bounded_param("~arm_step", 10.0, 1.0, 20.0)
        self._claw_step = self._bounded_param("~claw_step", 10.0, 1.0, 40.0)
        self._home = (
            self._bounded_param("~home_x", 80.0, 0.0, 255.0),
            self._bounded_param("~home_z", 60.0, 0.0, 255.0),
        )
        self._x, self._z = self._home
        self._client = OumaxManualClient()
        self._client.verify_identity()
        self._armed = False
        self._arm_requested_until = 0.0
        self._ctrl_c_exit_armed = False
        self._lock = threading.RLock()
        rospy.on_shutdown(self._shutdown_stop)

    @staticmethod
    def _bounded_param(name, default, minimum, maximum):
        value = float(rospy.get_param(name, default))
        if not minimum <= value <= maximum:
            raise ValueError("{} must be within [{}, {}]".format(name, minimum, maximum))
        return value

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    def _send_arm_command(self, label, sender):
        if not self._armed:
            print("LOCKED: press u, then y before any arm command can be sent.")
            return False
        with self._lock:
            try:
                sender()
                rospy.logwarn("REAL OUMAX arm command accepted: %s", label)
                return True
            except (URLError, OSError, ValueError, RuntimeError) as error:
                self._lock_and_stop("arm command failed")
                print("ARM COMMAND REJECTED: {}".format(error))
                return False

    def _lock_and_stop(self, reason):
        with self._lock:
            self._armed = False
            self._arm_requested_until = 0.0
        rospy.logwarn("Arm keyboard teleop locked and stopped: %s", reason)

    def _shutdown_stop(self):
        self._lock_and_stop("ROS shutdown")

    def _request_arm(self):
        self._arm_requested_until = time.monotonic() + 5.0
        print(
            "ARM REQUESTED: real arm motion is possible. Confirm clear space, "
            "people away and emergency stop/power-off reachable. Press y within 5 seconds."
        )

    def _confirm_arm(self):
        if time.monotonic() > self._arm_requested_until:
            print("Arm request expired. Press u, then y within 5 seconds.")
            return
        self._armed = True
        self._arm_requested_until = 0.0
        print(
            "ARMED (REAL OUMAX ARM): w/s arm x +/-{:.0f}, a/d arm z +/-{:.0f}, "
            "q/e claw +/-{:.0f}, m move to home. Space or x locks without moving; "
            "Ctrl-C locks, twice to exit.".format(
                self._arm_step, self._arm_step, self._claw_step
            )
        )

    @staticmethod
    def _read_key():
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        return sys.stdin.read(1) if ready else ""

    def run(self):
        if not sys.stdin.isatty():
            raise RuntimeError("arm keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        print("ARM keyboard teleop is LOCKED. Press u, then y to arm; space/x lock; Ctrl-C stops, twice to exit.")
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if not key:
                    continue
                if key == "\x03":
                    self._lock_and_stop("emergency stop")
                    if self._ctrl_c_exit_armed:
                        print("Ctrl-C pressed twice: exiting arm keyboard teleop.")
                        break
                    self._ctrl_c_exit_armed = True
                    print("Emergency stop sent. Press Ctrl-C again to exit the program.")
                elif key in (" ", "x"):
                    self._lock_and_stop("emergency stop")
                elif key == "u":
                    self._request_arm()
                elif key == "y":
                    self._confirm_arm()
                elif key == "w":
                    self._step_cartesian("x", +self._arm_step)
                elif key == "s":
                    self._step_cartesian("x", -self._arm_step)
                elif key == "a":
                    self._step_cartesian("z", -self._arm_step)
                elif key == "d":
                    self._step_cartesian("z", +self._arm_step)
                elif key == "q":
                    self._step_claw(+self._claw_step)
                elif key == "e":
                    self._step_claw(-self._claw_step)
                elif key == "m":
                    self._move_mid()
                else:
                    print("Keys: u then y arm; w/s x steps; a/d z steps; q/e claw; m home; space/x lock; Ctrl-C stops, twice to exit.")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._lock_and_stop("node exit")

    def _step_cartesian(self, axis, delta):
        with self._lock:
            new_x = self._clamp(self._x + (delta if axis == "x" else 0.0), 0.0, 255.0)
            new_z = self._clamp(self._z + (delta if axis == "z" else 0.0), 0.0, 255.0)

        def send():
            self._client.arm_cartesian(new_x, new_z)
        if self._send_arm_command("cartesian {} {}".format(axis, delta), send):
            with self._lock:
                self._x, self._z = new_x, new_z

    def _step_claw(self, delta):
        target = self._clamp(128.0 + delta, 0.0, 255.0)

        def send():
            self._client.arm_claw(target)
        self._send_arm_command("claw {}".format(delta), send)

    def _move_mid(self):
        def send():
            self._client.arm_mid()
        if self._send_arm_command("move to mid", send):
            with self._lock:
                self._x, self._z = self._home


def main():
    rospy.init_node("robot_dog_arm_keyboard_teleop")
    try:
        ArmKeyboardTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("Arm keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
