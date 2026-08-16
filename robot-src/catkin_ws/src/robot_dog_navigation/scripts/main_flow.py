#!/usr/bin/env python3
"""主流程：上电 → 定点巡航 → 抓球放球 一键编排。

顺序执行：
1. 以当前位姿为起点（默认从 map→base_link 读取，可用 --start-* 覆盖），
   按相对路径依次向 /move_base 发送 5 个带朝向的目标点并等待逐一到达：
     P1  前方 2.3 m，到达后右转 90°（朝向 = 初始 - 90°，--turn-deg）
     P2  初始朝向的右方 0.5 m 处，朝向与初始相差 180°
     P3  右方再 1.65 m（累计 2.15 m），朝向 180°
     P4  左方 0.575 m（自 P3 回撤，累计右方 1.575 m），朝向 180°
     P5  沿 P4 朝向前进 1 m（--final-forward-m），朝向与 P1 相同（右转 90°）
2. 全部到达后运行抓球放球程序 ball_grab_release.py（抓球 → 掉头 180° → 放球），
   --enable-motion 门禁透传。

坐标系约定：相对路径以起点为原点、初始朝向为 0 基准；x = 前方、y = 左方、
yaw 逆时针为正。因此"右转 90°" = yaw -π/2，"右方" = -y 方向，"朝向 180°" = yaw π。
地图绝对位姿 = 起点 + 旋转(初始 yaw) × 相对位姿；无论实机建图方向如何，只要
上电摆放起点与地图原点对齐（实机验证参数 use_amcl:=true init_x:=0 init_y:=0
init_yaw:=0），路径方向均与初始朝向解耦。

运行方式（机器端 ROS 容器内，ROS master 指向控制 PC）：
    rosrun robot_dog_navigation main_flow.py --enable-motion
或直接：
    python3 main_flow.py --enable-motion
（不带 --enable-motion 时 move_base 照常导航，但最后的抓球放球程序不运动；
 路径参数 --forward-m / --side-distances / --final-forward-m / --turn-deg
 可在实机标定时调整，例如方向相反时把 --side-distances 取负。）
"""

import argparse
import math
import os
import subprocess
import sys

import actionlib
import rospy
import tf2_ros
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal


class MainFlow:
    def __init__(self, args):
        self.args = args
        self.frame_id = "map"
        self.base_frame = "base_link"
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.move_base_client = actionlib.SimpleActionClient(
            "/move_base", MoveBaseAction
        )

    def current_pose(self):
        transform = self.tf_buffer.lookup_transform(
            self.frame_id,
            self.base_frame,
            rospy.Time(0),
            rospy.Duration(self.args.server_timeout_sec),
        )
        orientation = transform.transform.rotation
        yaw = math.atan2(
            2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
            1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z),
        )
        return (
            transform.transform.translation.x,
            transform.transform.translation.y,
            yaw,
        )

    def resolve_start(self):
        if (
            self.args.start_x is not None
            and self.args.start_y is not None
            and self.args.start_yaw is not None
        ):
            start = (self.args.start_x, self.args.start_y, math.radians(self.args.start_yaw))
            rospy.loginfo(
                "Start from args: (%.3f, %.3f, yaw=%.3f rad)", *start
            )
            return start
        start = self.current_pose()
        rospy.loginfo(
            "Start from tf %s->%s: (%.3f, %.3f, yaw=%.3f rad)",
            self.frame_id,
            self.base_frame,
            *start,
        )
        return start

    def build_waypoints(self):
        """相对路径点列表：[(x_m, y_m, yaw_rad)]，x 前、y 左、右转 yaw 为负。"""
        turn = -math.radians(self.args.turn_deg)
        yaw_opposite = math.pi
        waypoints = [(self.args.forward_m, 0.0, turn)]
        side_accum = 0.0
        for distance in self.args.side_distances:
            side_accum += distance
            waypoints.append((self.args.forward_m, -side_accum, yaw_opposite))
        last_x, last_y, _ = waypoints[-1]
        waypoints.append((last_x - self.args.final_forward_m, last_y, turn))
        return waypoints

    @staticmethod
    def to_map(waypoint, start):
        """相对位姿 → 地图绝对位姿。"""
        rel_x, rel_y, rel_yaw = waypoint
        start_x, start_y, start_yaw = start
        cos_yaw = math.cos(start_yaw)
        sin_yaw = math.sin(start_yaw)
        return (
            start_x + cos_yaw * rel_x - sin_yaw * rel_y,
            start_y + sin_yaw * rel_x + cos_yaw * rel_y,
            start_yaw + rel_yaw,
        )

    def pose_stamped(self, x_m, y_m, yaw):
        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = rospy.Time.now()
        pose.pose.position.x = x_m
        pose.pose.position.y = y_m
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def wait_for_goal(self, index, x_m, y_m, yaw):
        start_time = rospy.Time.now()
        terminal_failure_states = {
            GoalStatus.PREEMPTED,
            GoalStatus.ABORTED,
            GoalStatus.REJECTED,
            GoalStatus.RECALLED,
            GoalStatus.LOST,
        }
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            state = self.move_base_client.get_state()
            if state == GoalStatus.SUCCEEDED:
                return
            if state in terminal_failure_states:
                raise RuntimeError(
                    f"Navigation to waypoint {index} failed with action state {state}"
                )
            if (rospy.Time.now() - start_time).to_sec() >= self.args.goal_timeout_sec:
                self.move_base_client.cancel_goal()
                raise RuntimeError(
                    f"Timed out after {self.args.goal_timeout_sec:.0f}s navigating to waypoint {index}"
                )
            rate.sleep()
        raise rospy.ROSInterruptException()

    def run_navigation(self, start):
        waypoints = self.build_waypoints()
        total = len(waypoints)
        if not self.move_base_client.wait_for_server(
            rospy.Duration(self.args.server_timeout_sec)
        ):
            raise RuntimeError("Timed out waiting for /move_base action server")
        for index, waypoint in enumerate(waypoints, 1):
            x_m, y_m, yaw = self.to_map(waypoint, start)
            rospy.loginfo(
                "Navigating %d/%d to (%.3f, %.3f), yaw=%.3f rad",
                index,
                total,
                x_m,
                y_m,
                yaw,
            )
            goal = MoveBaseGoal()
            goal.target_pose = self.pose_stamped(x_m, y_m, yaw)
            self.move_base_client.send_goal(goal)
            self.wait_for_goal(index, x_m, y_m, yaw)
            rospy.loginfo("Reached waypoint %d/%d", index, total)

    def run_grab_release(self):
        if self.args.grab_release_ssh:
            host = self.args.grab_release_ssh
            rospy.loginfo("Stopping oumax-manual on %s to release serial", host)
            subprocess.run(
                ["ssh", host, "sudo systemctl stop oumax-manual.service"], check=True
            )
            python = self.args.grab_release_python
            command = "cd /home/pi/oumax-xgo && {} ball_grab_release.py".format(python)
            if self.args.enable_motion:
                command += " --enable-motion"
            rospy.loginfo("Running grab-and-release on %s: %s", host, command)
            subprocess.run(["ssh", host, command], check=True)
            rospy.loginfo("action=grabrelease-complete")
            return
        here = os.path.dirname(os.path.abspath(__file__))
        script = self.args.grab_release_script or os.path.join(
            here, "ball_grab_release.py"
        )
        command = [sys.executable, script]
        if self.args.enable_motion:
            command.append("--enable-motion")
        rospy.loginfo("Running grab-and-release: %s", " ".join(command))
        subprocess.run(command, check=True)
        rospy.loginfo("action=grabrelease-complete")

    def run(self):
        start = self.resolve_start()
        self.run_navigation(start)
        self.run_grab_release()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--forward-m",
        type=float,
        default=2.3,
        help="第 1 点：起点前方距离（米）",
    )
    parser.add_argument(
        "--side-distances",
        type=str,
        default="0.5,1.65,-0.575",
        help="右方三点依次间距（米，逗号分隔，沿初始朝向右侧累计；正值=右方，负值=左方）",
    )
    parser.add_argument(
        "--final-forward-m",
        type=float,
        default=1.0,
        help="最后一段沿 P4 朝向前进距离（米）",
    )
    parser.add_argument(
        "--turn-deg",
        type=float,
        default=90.0,
        help="P1/P5 相对初始朝向的右转角度（度，正值右转）",
    )
    parser.add_argument("--start-x", type=float, help="起点地图 x（默认从 tf 读取）")
    parser.add_argument("--start-y", type=float, help="起点地图 y（默认从 tf 读取）")
    parser.add_argument("--start-yaw", type=float, help="起点地图 yaw（度，默认从 tf 读取）")
    parser.add_argument("--goal-timeout-sec", type=float, default=180.0)
    parser.add_argument("--server-timeout-sec", type=float, default=20.0)
    parser.add_argument(
        "--grab-release-script",
        help="抓球放球编排脚本路径（默认与本脚本同目录的 ball_grab_release.py；"
        "仅本机执行模式使用）",
    )
    parser.add_argument(
        "--grab-release-ssh",
        help="球程序远程执行主机（如 pi@192.168.137.157）：提供后导航完成时经 ssh "
        "在该机执行抓球放球（先停 oumax-manual.service 释放串口，再用 "
        "--grab-release-python 跑 /home/pi/oumax-xgo/ball_grab_release.py）",
    )
    parser.add_argument(
        "--grab-release-python",
        default="/home/pi/RaspberryPi-CM5/xgovenv/bin/python",
        help="远程抓球放球使用的机器端 python（默认机器端 xgovenv）",
    )
    parser.add_argument(
        "--enable-motion",
        action="store_true",
        help="显式开启才允许真实运动（透传给 ball_grab_release.py）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    args.side_distances = [
        float(value) for value in args.side_distances.split(",") if value.strip()
    ]
    rospy.init_node("main_flow")
    try:
        MainFlow(args).run()
    except (RuntimeError, OSError, ValueError, KeyError, rospy.ROSException) as error:
        rospy.logfatal(str(error))
        raise SystemExit(1)
    except rospy.ROSInterruptException:
        pass


if __name__ == "__main__":
    main()
