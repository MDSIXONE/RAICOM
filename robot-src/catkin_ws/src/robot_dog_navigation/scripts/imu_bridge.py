#!/usr/bin/env python3
"""ROS IMU bridge: polls the OUMAX manual control server /imu endpoint and
publishes sensor_msgs/Imu on /imu.

The M-7.0.0b8 firmware exposes only single-axis attitude reads
(0x66/0x67/0x68): yaw is an accumulated angle, pitch/roll are body angles.
There is NO raw accelerometer/gyroscope stream, so:
  - orientation: built from the euler angles (roll, pitch, yaw in rad)
  - angular_velocity.z: finite-difference of the accumulated yaw
  - linear_acceleration: zero (unknown), covariance left empty
Cartographer is therefore configured with use_imu_data=false (laser-only
2D SLAM); this bridge keeps /imu available for yaw consumers (simple_odom
etc.) and for a future firmware/library upgrade.
"""
import json
import math
import urllib.request

import rospy
from sensor_msgs.msg import Imu
from tf.transformations import quaternion_from_euler

DEG2RAD = math.pi / 180.0


def wrap_pi(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class ImuBridge:
    def __init__(self):
        self.imu_url = rospy.get_param("~imu_url", "http://127.0.0.1:8765/imu")
        self.rate_hz = rospy.get_param("~rate", 30.0)
        self.frame_id = rospy.get_param("~frame_id", "base_link")
        self.http_timeout = rospy.get_param("~http_timeout", 0.3)
        self.topic = rospy.get_param("~imu_topic", "/imu")
        self.pub = rospy.Publisher(self.topic, Imu, queue_size=10)
        self._last_yaw = None
        self._last_stamp = None
        rospy.loginfo(
            "imu_bridge: %s -> %s @ %.0f Hz, frame=%s (yaw-diff gyro, no accel)",
            self.imu_url, self.topic, self.rate_hz, self.frame_id)

    def fetch(self):
        req = urllib.request.Request(self.imu_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def spin(self):
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            try:
                data = self.fetch()
                if not data.get("ok"):
                    raise ValueError(data.get("message", "imu read failed"))
                stamp = rospy.Time.now()
                euler = [math.radians(float(data["yaw"])), 0.0, 0.0] if "euler" not in data \
                    else [float(v) for v in data["euler"]]
                msg = Imu()
                msg.header.stamp = stamp
                msg.header.frame_id = self.frame_id
                q = quaternion_from_euler(euler[0], euler[1], euler[2])
                msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = q
                yaw_rad = euler[2]
                if self._last_yaw is not None:
                    dt = (stamp - self._last_stamp).to_sec()
                    if 0.0 < dt < 2.0:
                        delta = wrap_pi(yaw_rad - self._last_yaw)
                        msg.angular_velocity.z = delta / dt
                self._last_yaw = yaw_rad
                self._last_stamp = stamp
                self.pub.publish(msg)
            except Exception as exc:
                rospy.logwarn_throttle(10.0, "imu_bridge fetch failed: %s", exc)
            rate.sleep()


if __name__ == "__main__":
    rospy.init_node("imu_bridge")
    ImuBridge().spin()
