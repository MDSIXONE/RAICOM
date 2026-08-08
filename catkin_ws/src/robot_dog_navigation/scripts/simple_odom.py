#!/usr/bin/env python3
import json
import math
import threading
import urllib.request

import rospy
import tf
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf.transformations import quaternion_from_euler


def wrap_pi(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class SimpleOdom:
    def __init__(self):
        self.init_x = rospy.get_param("~init_x", -0.70)
        self.init_y = rospy.get_param("~init_y", 1.00)
        self.init_yaw = rospy.get_param("~init_yaw", 0.0)
        self.frame_id = rospy.get_param("~frame_id", "odom")
        self.child_frame_id = rospy.get_param("~child_frame_id", "base_link")
        self.imu_url = rospy.get_param("~imu_url", "http://127.0.0.1:8765/imu")
        self.rate = rospy.Rate(rospy.get_param("~rate", 10.0))
        self.yaw_jump_limit = rospy.get_param("~yaw_jump_limit", 0.4)
        self.vx_eps = rospy.get_param("~vx_eps", 0.01)
        self.d_max = rospy.get_param("~d_max", 0.10)

        self.lock = threading.Lock()
        self.x = self.init_x
        self.y = self.init_y
        self.yaw = self.init_yaw
        self.vx = 0.0
        self.wz = 0.0
        self.last_time = None
        self._last_raw = None
        self._accum_yaw = None

        self.pub = rospy.Publisher(
            rospy.get_param("~odom_topic", "/odom"), Odometry, queue_size=10)
        self.br = tf.TransformBroadcaster()
        rospy.Subscriber(
            rospy.get_param("~cmd_vel_topic", "/cmd_vel"), Twist, self.cmd_cb, queue_size=1)
        rospy.loginfo(
            "simple_odom: init pose (%.2f, %.2f, %.2f), frame %s -> %s, imu_url=%s",
            self.init_x, self.init_y, self.init_yaw, self.frame_id,
            self.child_frame_id, self.imu_url)

    def cmd_cb(self, msg):
        with self.lock:
            self.vx = msg.linear.x
            self.wz = msg.angular.z

    def fetch_imu_yaw(self):
        if not self.imu_url:
            return None
        try:
            req = urllib.request.Request(self.imu_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=0.4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not data.get("ok"):
                raise ValueError(data.get("message", "imu read failed"))
            raw = math.radians(float(data["yaw"]))
        except Exception as exc:
            rospy.logwarn_throttle(10.0, "imu fetch failed: %s", exc)
            return None
        if self._last_raw is None:
            self._last_raw = raw
            self._accum_yaw = raw
        else:
            delta = raw - self._last_raw
            if delta > math.pi:
                delta -= 2.0 * math.pi
            elif delta < -math.pi:
                delta += 2.0 * math.pi
            if abs(delta) > self.yaw_jump_limit:
                rospy.logwarn_throttle(10.0,
                    "imu yaw jump %.2f rad dropped", delta)
                self._last_raw = raw
                return self._accum_yaw
            self._last_raw = raw
            self._accum_yaw += delta
        return self._accum_yaw

    def publish(self):
        now = rospy.Time.now()
        with self.lock:
            dt = 0.0 if self.last_time is None else (now - self.last_time).to_sec()
            self.last_time = now
            vx, wz = self.vx, self.wz
            x, y, yaw = self.x, self.y, self.yaw
        if dt > 0.5 or dt < 0.0:
            dt = 0.0

        heading = self.fetch_imu_yaw()
        if heading is not None:
            with self.lock:
                self.yaw = heading
        else:
            yaw += wz * dt
            with self.lock:
                self.yaw = yaw
            heading = yaw

        vx = 0.0 if abs(vx) < self.vx_eps else vx

        dx = vx * math.cos(heading) * dt
        dy = vx * math.sin(heading) * dt
        # Per-frame displacement clamp: 0.10 m @ 10 Hz == 1.0 m/s ceiling.
        # Tune up if the foot gait moves faster than that; too low silently
        # drops real motion (rviz robot stays put while the robot walks).
        if abs(dx) > self.d_max or abs(dy) > self.d_max:
            dx = dy = 0.0
        x += dx
        y += dy
        with self.lock:
            self.x, self.y = x, y

        q = quaternion_from_euler(0.0, 0.0, heading)
        stamp = rospy.Time.now()
        self.br.sendTransform(
            (x, y, 0.0), q, stamp, self.child_frame_id, self.frame_id)
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = wz
        self.pub.publish(odom)

    def run(self):
        while not rospy.is_shutdown():
            self.publish()
            self.rate.sleep()


if __name__ == "__main__":
    rospy.init_node("simple_odom")
    try:
        SimpleOdom().run()
    except rospy.ROSInterruptException:
        pass
