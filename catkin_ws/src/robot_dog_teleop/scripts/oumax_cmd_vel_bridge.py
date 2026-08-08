#!/usr/bin/env python3
"""Bridge ROS cmd_vel (geometry_msgs/Twist) to the local OUMAX manual service.

Reference: physical_keyboard_teleop.py's OumaxManualClient (127.0.0.1:8765).
This node runs on the robot (inside the ROS container), subscribes to the
navigation stack's /cmd_vel output and drives the physical dog through the
already-running OUMAX manual service, the sole owner of /dev/ttyAMA0.

Motion mapping (XGO units, not m/s):
  |angular.z| above dead_zone_wz -> yaw pulse (default 55)
  else |linear.x| above dead_zone_vx -> x pulse (default 17)
  zero velocity / watchdog timeout -> stop
A refresh loop re-sends the current command while it stays nonzero, so the
physical motion continues for as long as the planner demands it.
"""

import json
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


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

    def gamepad(self, x, y, yaw, drive_mode):
        return self._request(
            _COMMAND_URL,
            {"kind": "gamepad", "x": x, "y": y, "yaw": yaw, "drive_mode": drive_mode},
        )

    def stop(self):
        return self._request(_COMMAND_URL, {"kind": "motion", "axis": "stop"})


class OumaxCmdVelBridge:
    def __init__(self):
        if rospy.get_param("~enable_motion", False) is not True:
            raise RuntimeError(
                "real motion is disabled; use enable_motion:=true only after "
                "on-site safety confirmation"
            )
        self._cmd_vel_topic = rospy.get_param("~cmd_vel_topic", "/cmd_vel")
        self._drive_mode = rospy.get_param("~drive_mode", "dog")
        if self._drive_mode not in ("dog", "wheel4"):
            raise ValueError("~drive_mode must be 'dog' or 'wheel4', got: {}".format(self._drive_mode))
        self._linear_value = self._bounded_param("~linear_motion_value", 17.0, 1.0, 25.0)
        self._yaw_value = self._bounded_param("~yaw_motion_value", 55.0, 1.0, 70.0)
        self._yaw_scale_ref = rospy.get_param("~yaw_scale_ref", 2.0)
        self._x_scale_ref = rospy.get_param("~x_scale_ref", 4.0)
        self._yaw_min_step = self._bounded_param("~yaw_min_step", 10.0, 1.0, 70.0)
        self._x_min_step = self._bounded_param("~x_min_step", 5.0, 1.0, 25.0)
        self._dead_zone_vx = rospy.get_param("~dead_zone_vx", 0.02)
        self._dead_zone_wz = rospy.get_param("~dead_zone_wz", 0.05)
        self._runtime = rospy.get_param("~pulse_duration_sec", 0.25)
        self._watchdog_sec = rospy.get_param("~watchdog_sec", 0.35)
        self._rate_hz = rospy.get_param("~rate_hz", 10.0)

        self._client = OumaxManualClient()
        self._client.verify_identity()

        self._lock = threading.RLock()
        self._latest = None
        self._latest_stamp = 0.0
        self._paused = False
        self._last_axis = None

        self._cmd_sub = rospy.Subscriber(
            self._cmd_vel_topic, Twist, self._on_cmd_vel, queue_size=1
        )
        self._stop_sub = rospy.Subscriber(
            "~stop_cmd", Bool, self._on_stop_cmd, queue_size=1
        )
        rospy.on_shutdown(self._shutdown_stop)
        rospy.loginfo(
            "oumax_cmd_vel_bridge ready on %s (drive_mode=%s, x=%s, yaw=%s, runtime=%.2fs, watchdog=%.2fs)",
            self._cmd_vel_topic,
            self._drive_mode,
            self._linear_value,
            self._yaw_value,
            self._runtime,
            self._watchdog_sec,
        )

    @staticmethod
    def _bounded_param(name, default, minimum, maximum):
        value = float(rospy.get_param(name, default))
        if not minimum <= value <= maximum:
            raise ValueError("{} must be within [{}, {}]".format(name, minimum, maximum))
        return value

    @staticmethod
    def _scale_step(magnitude, scale_ref, min_step, max_step):
        # Linear mapping from |cmd| into [min_step, max_step]. The min bound
        # avoids the XGO firmware dead zone (step < ~12 barely moves).
        ratio = min(1.0, magnitude / scale_ref)
        step = min_step + ratio * (max_step - min_step)
        return max(min_step, min(float(max_step), float(step)))

    def _on_cmd_vel(self, msg):
        with self._lock:
            self._latest = msg
            self._latest_stamp = time.monotonic()

    def _on_stop_cmd(self, msg):
        with self._lock:
            self._paused = bool(msg.data)
            if self._paused:
                self._latest = None
                rospy.logwarn("oumax_cmd_vel_bridge PAUSED by /stop_cmd")
                self._send_stop("stop command")
            else:
                rospy.logwarn("oumax_cmd_vel_bridge resumed")

    def _send_stop(self, reason):
        try:
            self._client.stop()
        except (URLError, OSError, ValueError, RuntimeError) as error:
            rospy.logerr("OUMAX stop request failed (%s): %s", reason, error)
            return False
        self._last_axis = None
        return True

    def _send_motion(self, axis, value):
        # runtime acts as a watchdog on the service side: the service sends
        # the velocity command immediately and stops the axis `runtime`
        # seconds after the last command arrives (re-armed on refresh), so
        # this 10 Hz loop sustains continuous motion without blocking.
        try:
            self._client.motion(axis, value, self._runtime)
        except (URLError, OSError, ValueError, RuntimeError) as error:
            rospy.logerr("OUMAX motion request failed: %s", error)
            self._send_stop("motion request failed")
            return False
        if axis != self._last_axis:
            rospy.logwarn("OUMAX pulse: axis=%s value=%.1f for %.2fs", axis, value, self._runtime)
            self._last_axis = axis
        return True

    def _send_gamepad(self, x, y, yaw):
        try:
            self._client.gamepad(x, y, yaw, "wheel4")
        except (URLError, OSError, ValueError, RuntimeError) as error:
            rospy.logerr("OUMAX gamepad request failed: %s", error)
            self._send_stop("gamepad request failed")
            return False
        self._last_axis = "gamepad"
        return True

    @staticmethod
    def _clamp_unit(value):
        return max(-1.0, min(1.0, value))

    def _control_tick(self):
        with self._lock:
            if self._paused:
                return
            if self._latest is None:
                return
            if time.monotonic() - self._latest_stamp > self._watchdog_sec:
                self._latest = None
                self._send_stop("watchdog timeout")
                return
            cmd = self._latest
            if self._drive_mode == "wheel4":
                if abs(cmd.angular.z) > self._dead_zone_wz or abs(cmd.linear.x) > self._dead_zone_vx:
                    x = -self._clamp_unit(cmd.linear.x / self._x_scale_ref)
                    yaw = self._clamp_unit(cmd.angular.z / self._yaw_scale_ref)
                    self._send_gamepad(x, 0.0, yaw)
                else:
                    self._send_gamepad(0.0, 0.0, 0.0)
                return
            if abs(cmd.angular.z) > self._dead_zone_wz:
                step = self._scale_step(
                    abs(cmd.angular.z), self._yaw_scale_ref, self._yaw_min_step, self._yaw_value
                )
                self._send_motion("yaw", step * (1.0 if cmd.angular.z > 0 else -1.0))
            elif abs(cmd.linear.x) > self._dead_zone_vx:
                step = self._scale_step(
                    abs(cmd.linear.x), self._x_scale_ref, self._x_min_step, self._linear_value
                )
                self._send_motion("x", step * (1.0 if cmd.linear.x > 0 else -1.0))
            else:
                self._send_stop("zero velocity")

    def _shutdown_stop(self):
        with self._lock:
            self._latest = None
            self._send_stop("ROS shutdown")

    def run(self):
        rate = rospy.Rate(self._rate_hz)
        while not rospy.is_shutdown():
            self._control_tick()
            rate.sleep()


def main():
    rospy.init_node("oumax_cmd_vel_bridge")
    try:
        OumaxCmdVelBridge().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("OumaxCmdVelBridge refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
