#!/usr/bin/env python3
"""carto_odom.py

Cartographer 模式（odom_mode:=carto）的 /odom 消息桥：把 cartographer_node
发布的 odom -> base_link TF 转成 nav_msgs/Odometry（含差分 twist），供
move_base 与局部规划器消费。只发消息、不发 TF（TF 由 cartographer 独占，
避免双发布者打架）。

背景：cartographer_node 的 provide_odom_frame 只发布 TF 不发布 /odom 消息，
而 move_base 默认订阅 /odom；本节点补齐该消息。
"""

import math
import threading

import rospy
import tf2_ros
from nav_msgs.msg import Odometry
from tf.transformations import quaternion_from_euler


class CartoOdom:
    def __init__(self):
        self.frame_id = rospy.get_param("~frame_id", "odom")
        self.child_frame_id = rospy.get_param("~child_frame_id", "base_link")
        self.rate = rospy.Rate(rospy.get_param("~rate", 30.0))
        self.pub = rospy.Publisher(
            rospy.get_param("~odom_topic", "/odom"), Odometry, queue_size=10
        )
        self.tf_buffer = tf2_ros.Buffer(cache_time=rospy.Duration(5.0))
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        self.lock = threading.Lock()
        self._last = None
        self._vx = 0.0
        self._wz = 0.0
        rospy.loginfo(
            "carto_odom: TF %s -> %s -> %s", self.frame_id, self.child_frame_id,
            rospy.get_param("~odom_topic", "/odom"))

    def publish(self):
        now = rospy.Time.now()
        try:
            t = self.tf_buffer.lookup_transform(
                self.frame_id, self.child_frame_id, rospy.Time(0))
        except (tf2_ros.LookupException, tf2_ros.ExtrapolationException) as exc:
            return
        q = t.transform.rotation
        x = t.transform.translation.x
        y = t.transform.translation.y
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        stamp = t.header.stamp

        with self.lock:
            if self._last is None:
                self._last = (x, y, yaw, stamp)
                self._vx = self._wz = 0.0
            else:
                lx, ly, lyaw, ltime = self._last
                dt = (stamp - ltime).to_sec()
                if dt > 1e-6:
                    dx = x - lx
                    dy = y - ly
                    dyaw = yaw - lyaw
                    while dyaw > math.pi:
                        dyaw -= 2.0 * math.pi
                    while dyaw < -math.pi:
                        dyaw += 2.0 * math.pi
                    dist = math.hypot(dx, dy)
                    if dist > 0.05 or abs(dyaw) > 0.1:
                        self._vx = self._wz = 0.0
                    else:
                        self._vx = dist / dt
                        self._wz = dyaw / dt
                self._last = (x, y, yaw, stamp)

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation = q
        with self.lock:
            odom.twist.twist.linear.x = self._vx
            odom.twist.twist.angular.z = self._wz
        self.pub.publish(odom)

    def run(self):
        while not rospy.is_shutdown():
            self.publish()
            self.rate.sleep()


if __name__ == "__main__":
    rospy.init_node("carto_odom")
    try:
        CartoOdom().run()
    except rospy.ROSInterruptException:
        pass
