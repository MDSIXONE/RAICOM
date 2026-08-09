#!/usr/bin/env python3
"""Publish an initial pose to /initialpose after the static map is available.

lidar_loc (jie_ware) resets its estimate to the map origin when it first
receives /map, so an /initialpose published before that callback runs would be
lost.  This node waits for the first /map message, then re-publishes the
configured pose a few times so it reliably lands after lidar_loc's own reset.
"""

import math
import time

import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid


class InitialPosePublisher:
    def __init__(self):
        self._init_x = float(rospy.get_param("~init_x", -0.70))
        self._init_y = float(rospy.get_param("~init_y", 1.00))
        self._init_yaw = float(rospy.get_param("~init_yaw", 0.0))
        self._map_topic = rospy.get_param("~map_topic", "/map")
        self._initialpose_topic = rospy.get_param("~initialpose_topic", "/initialpose")
        self._delay_after_map = float(rospy.get_param("~delay_after_map", 1.0))
        # A handful of repeats is enough to survive lidar_loc's startup
        # ordering without postponing its costmap clear too long (every
        # /initialpose resets lidar_loc's 30-scan clear countdown).
        self._publish_count = int(rospy.get_param("~publish_count", 5))
        self._publish_interval = float(rospy.get_param("~publish_interval", 0.5))

        if self._publish_count < 1:
            rospy.logerr("publish_count 不能小于 1：%d", self._publish_count)
            raise rospy.ROSException("publish_count must be >= 1")
        if self._delay_after_map < 0.0 or self._publish_interval <= 0.0:
            rospy.logerr("delay_after_map / publish_interval 非法：%.3f / %.3f",
                         self._delay_after_map, self._publish_interval)
            raise rospy.ROSException("invalid timing parameters")

        self._publisher = rospy.Publisher(
            self._initialpose_topic, PoseWithCovarianceStamped, queue_size=1
        )
        self._map_received = False
        rospy.Subscriber(self._map_topic, OccupancyGrid, self._map_callback, queue_size=1)
        rospy.loginfo(
            "initial_pose_publisher: 等待 %s，之后发布 %.3f %.3f yaw=%.1f° 到 %s",
            self._map_topic, self._init_x, self._init_y,
            math.degrees(self._init_yaw), self._initialpose_topic,
        )

    def _map_callback(self, _map):
        if self._map_received:
            return
        self._map_received = True
        rospy.sleep(self._delay_after_map)
        for _ in range(self._publish_count):
            self._publish_pose()
            rospy.sleep(self._publish_interval)
        rospy.loginfo(
            "initial_pose_publisher: 已发布 %d 次初始位姿 (%.3f, %.3f, yaw=%.1f°)",
            self._publish_count, self._init_x, self._init_y,
            math.degrees(self._init_yaw),
        )

    def _publish_pose(self):
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = rospy.Time.now()
        pose.pose.pose.position.x = self._init_x
        pose.pose.pose.position.y = self._init_y
        pose.pose.pose.position.z = 0.0
        pose.pose.pose.orientation.z = math.sin(self._init_yaw / 2.0)
        pose.pose.pose.orientation.w = math.cos(self._init_yaw / 2.0)
        self._publisher.publish(pose)


def main():
    rospy.init_node("initial_pose_publisher")
    InitialPosePublisher()
    rospy.spin()


if __name__ == "__main__":
    main()
