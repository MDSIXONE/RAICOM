#!/usr/bin/env python3
"""Direct, explicitly armed keyboard point control through OUMAX's local API.

This process never opens a serial port and never accepts ROS velocity topics.
It sends bounded, single-axis requests only to the already-running local OUMAX
manual service, which remains the sole owner of ``/dev/ttyAMA0``.
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

    def motion(self, axis, value, runtime):
        return self._request(
            _COMMAND_URL,
            {
                "kind": "motion",
                "axis": axis,
                "value": value,
                "runtime": runtime,
                "drive_mode": "dog",
            },
        )

    def stop(self):
        return self._request(_COMMAND_URL, {"kind": "motion", "axis": "stop"})


class PhysicalKeyboardTeleop:
    """Keyboard point control with local confirmation and a stop watchdog."""

    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError(
                "real motion is disabled; use enable_motion:=true only after "
                "on-site safety confirmation"
            )
        self._pulse_duration = self._bounded_param(
            "~pulse_duration_sec", 0.20, 0.05, 0.20
        )
        # XGO units, not metres per second.  Defaults reproduce the supplied
        # Dog_LM joystick's normal step setting (x≈17, yaw≈55), while keeping
        # this keyboard controller's independent <=0.20s pulse watchdog.
        self._linear_motion_value = self._bounded_param(
            "~linear_motion_value", 17.0, 1.0, 25.0
        )
        self._yaw_motion_value = self._bounded_param(
            "~yaw_motion_value", 55.0, 1.0, 70.0
        )
        self._client = OumaxManualClient()
        self._client.verify_identity()
        self._armed = False
        self._arm_requested_until = 0.0
        self._ctrl_c_exit_armed = False
        self._stop_timer = None
        self._pulse_id = 0
        self._pulse_active = False
        self._lock = threading.RLock()
        rospy.on_shutdown(self._shutdown_stop)

    @staticmethod
    def _bounded_param(name, default, minimum, maximum):
        value = float(rospy.get_param(name, default))
        if not minimum <= value <= maximum:
            raise ValueError("{} must be within [{}, {}]".format(name, minimum, maximum))
        return value

    def _send_stop_locked(self, reason):
        self._pulse_id += 1
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None
        try:
            self._client.stop()
        except (URLError, OSError, ValueError, RuntimeError) as error:
            rospy.logerr("OUMAX stop request failed (%s): %s", reason, error)
        rospy.logwarn("OUMAX stop requested: %s", reason)

    def _lock_and_stop(self, reason):
        with self._lock:
            self._armed = False
            self._arm_requested_until = 0.0
            self._pulse_active = False
            self._send_stop_locked(reason)

    def _stop_after_pulse(self, pulse_id):
        with self._lock:
            if pulse_id != self._pulse_id:
                return
            self._pulse_active = False
            self._send_stop_locked("pulse timeout")

    def _request_arm(self):
        if self._pulse_active:
            print("WAIT: the previous point command has not completed its stop cycle.")
            return
        self._arm_requested_until = time.monotonic() + 5.0
        print(
            "ARM REQUESTED: real motion is possible. Confirm 1 m clear space, "
            "people away and emergency stop/physical power-off reachable. "
            "Press y within 5 seconds."
        )

    def _confirm_arm(self):
        if self._pulse_active:
            print("WAIT: the previous point command has not completed its stop cycle.")
            return
        if time.monotonic() > self._arm_requested_until:
            print("Arm request expired. Press u, then y within 5 seconds.")
            return
        self._armed = True
        self._arm_requested_until = 0.0
        print(
            "ARMED (REAL OUMAX CONTROL): w/s intended forward/reverse, a/d intended "
            "left/right turn. Each action is one <= {:.2f}s uncalibrated XGO pulse. "
            "Space or x stops and locks.".format(self._pulse_duration)
        )

    def _pulse(self, label, axis, direction, magnitude):
        if not self._armed:
            print("LOCKED: press u, then y before any physical command can be sent.")
            return
        with self._lock:
            try:
                self._pulse_id += 1
                pulse_id = self._pulse_id
                if self._stop_timer is not None:
                    self._stop_timer.cancel()
                    self._stop_timer = None
                # Start the local watchdog only after the manual service has
                # accepted the motion request, avoiding a late-motion race.
                self._client.motion(axis, direction * magnitude, self._pulse_duration)
                # Raw terminals auto-repeat held keys.  Consume this arm before
                # starting the timer so repeated w/s/a/d events cannot extend a
                # single physical point command.
                self._armed = False
                self._arm_requested_until = 0.0
                self._pulse_active = True
                self._stop_timer = threading.Timer(
                    self._pulse_duration, self._stop_after_pulse, args=(pulse_id,)
                )
                self._stop_timer.daemon = True
                self._stop_timer.start()
                rospy.logwarn("REAL OUMAX pulse accepted: %s for %.2fs", label, self._pulse_duration)
                print("REAL MOTION PULSE: {} for <= {:.2f}s (XGO value {:.1f}; direction is uncalibrated).".format(
                    label, self._pulse_duration, direction * magnitude
                ))
                print("LOCKED AFTER PULSE: press u, then y before the next physical point command.")
            except (URLError, OSError, ValueError, RuntimeError) as error:
                self._lock_and_stop("motion request failed")
                print("MOTION REJECTED: {}".format(error))

    @staticmethod
    def _read_key():
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        return sys.stdin.read(1) if ready else ""

    def _shutdown_stop(self):
        with self._lock:
            self._send_stop_locked("ROS shutdown")

    def run(self):
        bindings = {
            "w": ("intended forward", "x", 1.0, self._linear_motion_value),
            "s": ("intended reverse", "x", -1.0, self._linear_motion_value),
            "a": ("intended left turn", "yaw", 1.0, self._yaw_motion_value),
            "d": ("intended right turn", "yaw", -1.0, self._yaw_motion_value),
        }
        if not sys.stdin.isatty():
            raise RuntimeError("physical keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        print("REAL keyboard teleop is LOCKED. Press u, then y to arm; space/x stop and lock; Ctrl-C stops, twice to exit.")
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if not key:
                    continue
                if key == "\x03":
                    self._lock_and_stop("emergency stop")
                    if self._ctrl_c_exit_armed:
                        print("Ctrl-C pressed twice: exiting keyboard teleop.")
                        break
                    self._ctrl_c_exit_armed = True
                    print("Emergency stop sent. Press Ctrl-C again to exit the program.")
                elif key in (" ", "x"):
                    self._lock_and_stop("emergency stop")
                elif key == "u":
                    self._request_arm()
                elif key == "y":
                    self._confirm_arm()
                elif key in bindings:
                    self._pulse(*bindings[key])
                else:
                    print("Keys: u then y arm; w/s forward/reverse; a/d turn; space/x stop and lock; Ctrl-C stops, twice to exit.")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._lock_and_stop("node exit")


def main():
    rospy.init_node("robot_dog_keyboard_teleop")
    try:
        PhysicalKeyboardTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("Physical keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
