#!/usr/bin/env python3
"""odom_from_amcl.py

把 AMCL 激光定位位姿（/amcl_pose）平滑后直接作为 odom → base_link 与
/odom 发布，替代基于 cmd_vel 积分的 simple_odom。

背景：XGO mini3W 是 foot 步态轮足，无轮式编码器，cmd_vel 积分 odom 不可信
（打滑 ±20%、步态随机、桥非线性映射，2026-08-17 实机 odom 漂移到 (4.88,2.49)
而实际 (2.03,-0.19)）。比赛场景激光始终可用、无激光退化，定位由 AMCL 激光
匹配全权负责。本节点只把 AMCL 结果转换成 odom 帧下的平滑运动估计，供 AMCL
运动模型与 move_base 局部规划器使用。

原理：AMCL 发布 map→odom = (map→base) × (odom→base)⁻¹。本节点把平滑后的
AMCL 位姿直接发布为 odom→base，则 map→odom 自动趋于恒等（差一个平滑延迟），
odom 增量即平滑后的真实运动。EMA 低通 + 静止死区抑制 AMCL 位姿噪声。

注意：本节点只在 use_amcl:=true 模式下使用（launch 中与 simple_odom 互斥）；
无 /amcl_pose 时不发布任何 odom。
"""

import math
import threading

import rospy
import tf
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from tf.transformations import quaternion_from_euler


def yaw_of(msg):
    q = msg.pose.pose.orientation
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


class OdomFromAmcl:
    def __init__(self):
        self.alpha = rospy.get_param("~alpha", 0.4)
        self.motion_eps = rospy.get_param("~motion_eps", 0.005)
        self.yaw_eps = rospy.get_param("~yaw_eps", 0.005)
        # 初始位姿：AMCL 首帧 amcl_pose 到来前也发布该位姿 TF，否则
        # AMCL 的 scan 处理等 laser->odom TF、本节点等 amcl_pose，互相死锁。
        self.init_x = rospy.get_param("~init_x", 0.0)
        self.init_y = rospy.get_param("~init_y", 0.0)
        self.init_yaw = rospy.get_param("~init_yaw", 0.0)
        self.frame_id = rospy.get_param("~frame_id", "odom")
        self.child_frame_id = rospy.get_param("~child_frame_id", "base_link")
        self.rate = rospy.Rate(rospy.get_param("~rate", 10.0))

        self.lock = threading.Lock()
        self._smooth = None
        self._last_pub = None
        self._vx = 0.0
        self._wz = 0.0

        self.pub = rospy.Publisher(
            rospy.get_param("~odom_topic", "/odom"), Odometry, queue_size=10
        )
        self.br = tf.TransformBroadcaster()
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self.pose_cb)
        rospy.loginfo(
            "odom_from_amcl: /amcl_pose -> %s -> %s (alpha=%.2f)",
            self.frame_id,
            self.child_frame_id,
            self.alpha,
        )

    def pose_cb(self, msg):
        yaw = yaw_of(msg)
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        with self.lock:
            if self._smooth is None:
                self._smooth = (x, y, yaw)
                return
            sx, sy, syaw = self._smooth
            dyaw = yaw - syaw
            while dyaw > math.pi:
                dyaw -= 2.0 * math.pi
            while dyaw < -math.pi:
                dyaw += 2.0 * math.pi
            if (
                abs(x - sx) < self.motion_eps
                and abs(y - sy) < self.motion_eps
                and abs(dyaw) < self.yaw_eps
            ):
                return
            self._smooth = (
                sx + self.alpha * (x - sx),
                sy + self.alpha * (y - sy),
                syaw + self.alpha * dyaw,
            )

    def publish(self):
        with self.lock:
            smooth = self._smooth
        if smooth is None:
            x, y, yaw = self.init_x, self.init_y, self.init_yaw
        else:
            x, y, yaw = smooth
        now = rospy.Time.now()

        with self.lock:
            if self._last_pub is None:
                self._last_pub = (x, y, yaw, now)
                self._vx = self._wz = 0.0
            else:
                lx, ly, lyaw, ltime = self._last_pub
                dt = (now - ltime).to_sec()
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
                        # 大跳（AMCL 修正/假定位突变）不计速度，只更新基准
                        self._vx = self._wz = 0.0
                    else:
                        self._vx = dist / dt
                        self._wz = dyaw / dt
                self._last_pub = (x, y, yaw, now)

        q = quaternion_from_euler(0.0, 0.0, yaw)
        self.br.sendTransform(
            (x, y, 0.0), q, now, self.child_frame_id, self.frame_id
        )
        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        with self.lock:
            odom.twist.twist.linear.x = self._vx
            odom.twist.twist.angular.z = self._wz
        self.pub.publish(odom)

    def run(self):
        while not rospy.is_shutdown():
            self.publish()
            self.rate.sleep()


if __name__ == "__main__":
    rospy.init_node("odom_from_amcl")
    try:
        OdomFromAmcl().run()
    except rospy.ROSInterruptException:
        pass
