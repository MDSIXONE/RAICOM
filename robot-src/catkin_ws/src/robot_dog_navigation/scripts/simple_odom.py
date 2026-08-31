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
        # IMU 单帧跳变过滤。注意阈值不能太小：XGO 转向是脉冲式（cmd_vel 桥把
        # wz 映射为 turn 步长突发），单帧（10Hz）IMU 变化可能达到数十度；0.4 rad
        # 会把真实转向当作跳变丢弃，且丢弃后以新 raw 为基准，该段航向被永久
        # 抹掉 → odom 朝向系统性落后 → 平移积分方向错误 → odom 路径漂移
        # （2026-08-17 实机：odom (4.88,2.49) vs 实际 (2.03,-0.19)）。
        # 1.5 rad 只过滤 ±π 环绕之外的真正异常跳变（±π 环绕已在上方处理）。
        self.yaw_jump_limit = rospy.get_param("~yaw_jump_limit", 1.5)
        self.vx_eps = rospy.get_param("~vx_eps", 0.01)
        self.d_max = rospy.get_param("~d_max", 0.10)
        # 位移标定系数：cmd_vel 的 vx（m/s）经 oumax_cmd_vel_bridge 转成 XGO
        # 步长是非线性映射，实际速度 ≠ cmd_vel 值。odom 按 cmd_vel 积分会虚高，
        # 使 move_base 提前判定到达（实机"移动距离太短"）。标定方法：发已知
        # 距离 goal，量狗实际位移，scale = 实际/名义；实测后写入 launch。
        self.odom_scale = rospy.get_param("~odom_scale", 1.0)
        # Stale /cmd_vel must decay to zero: the last Twist would otherwise
        # keep integrating forever after the publisher stops (e.g. a test
        # rostopic pub), making odom drift kilometres while the robot stands
        # still and breaking lidar_loc / move_base feedback.
        self.cmd_timeout = rospy.get_param("~cmd_timeout", 0.5)
        self._cmd_stamp = None
        # 位置模式：integrate（默认，cmd_vel 积分，foot 打滑不可靠，仅兜底）；
        # yaw_only（给 Cartographer 用）：位置不积分（保持 init 位姿，位置全交给
        # 激光匹配），只发布 IMU 朝向（yaw + IMU 差分角速度 wz），vx 恒 0。
        self.position_mode = rospy.get_param("~position_mode", "integrate")
        self.publish_tf = rospy.get_param("~publish_tf", True)

        self.lock = threading.Lock()
        self.x = self.init_x
        self.y = self.init_y
        self.yaw = self.init_yaw
        self.vx = 0.0
        self.wz = 0.0
        self.last_time = None
        self._last_raw = None
        self._accum_yaw = None
        self._last_heading = None  # yaw_only：上一帧 heading，用于 IMU 差分角速度

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
            self._cmd_stamp = rospy.Time.now()

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
            # Baseline the accumulated yaw at init_yaw so the robot starts
            # facing the map +X axis (mapping mode) instead of the IMU's
            # absolute magnetic heading (e.g. ~25 deg), which made the robot
            # appear tilted in RViz.
            self._accum_yaw = self.init_yaw
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
            if self._cmd_stamp is not None and (now - self._cmd_stamp).to_sec() > self.cmd_timeout:
                vx = wz = 0.0
                self.vx = self.wz = 0.0
            x, y, yaw = self.x, self.y, self.yaw
        if dt > 0.5 or dt < 0.0:
            dt = 0.0

        heading = self.fetch_imu_yaw()
        if heading is not None:
            with self.lock:
                self.yaw = heading
                if self.position_mode == "yaw_only":
                    # IMU 差分角速度（wz）：作为 Cartographer 的旋转先验，
                    # 替代不可靠的 cmd_vel angular.z
                    if self._last_heading is not None and dt > 0:
                        self.wz = wrap_pi(heading - self._last_heading) / dt
                    self._last_heading = heading
        else:
            yaw += wz * dt
            with self.lock:
                self.yaw = yaw
            heading = yaw

        vx = 0.0 if abs(vx) < self.vx_eps else vx

        if self.position_mode == "yaw_only":
            # yaw_only：位置不积分（保持 init 位姿），位置全交给激光匹配；
            # vx 置 0 表示无平移先验
            vx = 0.0
            x, y = self.init_x, self.init_y
        else:
            dx = vx * math.cos(heading) * dt * self.odom_scale
            dy = vx * math.sin(heading) * dt * self.odom_scale
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
        if self.publish_tf:
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
