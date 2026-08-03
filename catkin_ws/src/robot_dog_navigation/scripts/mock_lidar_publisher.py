#!/usr/bin/env python3
"""Publish deterministic offline lidar data for the local navigation demo.

This node has no device, serial, socket, or robot-control access.  It keeps the
same ``/scan`` and ``laser_frame`` convention as the hardware lidar package so
the offline source can later be replaced without changing visualization topics.
"""

import math

import rospy
from sensor_msgs import point_cloud2
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker


class MockLidarPublisher:
    """Emit a fixed indoor-obstacle pattern as both LaserScan and PointCloud2."""

    def __init__(self):
        self._frame_id = rospy.get_param("~frame_id", "laser_frame")
        self._scan_topic = rospy.get_param("~scan_topic", "/scan")
        self._cloud_topic = rospy.get_param("~cloud_topic", "/lidar_points")
        self._rate_hz = float(rospy.get_param("~rate", 8.0))
        self._body_length = float(rospy.get_param("~body_length", 0.27))
        self._body_width = float(rospy.get_param("~body_width", 0.16))
        self._body_height = float(rospy.get_param("~body_height", 0.10))
        self._range_min = 0.12
        self._range_max = 8.0
        self._sample_count = 360

        self._scan_publisher = rospy.Publisher(
            self._scan_topic, LaserScan, queue_size=1
        )
        self._cloud_publisher = rospy.Publisher(
            self._cloud_topic, point_cloud2.PointCloud2, queue_size=1
        )
        self._body_marker_publisher = rospy.Publisher(
            "/robot_body_marker", Marker, queue_size=1, latch=True
        )

    def _publish_body_marker(self, stamp):
        """Publish a local visual-only rectangular placeholder for the robot body."""

        marker = Marker()
        marker.header.stamp = stamp
        marker.header.frame_id = "base_link"
        marker.ns = "robot_body"
        marker.id = 0
        marker.type = Marker.CUBE
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.pose.position.z = self._body_height / 2.0
        marker.scale.x = self._body_length
        marker.scale.y = self._body_width
        marker.scale.z = self._body_height
        marker.color.r = 0.10
        marker.color.g = 0.45
        marker.color.b = 1.00
        marker.color.a = 0.85
        self._body_marker_publisher.publish(marker)

    def _range_for_angle(self, angle):
        """Return a repeatable room-like return distance for one beam.

        The pattern deliberately contains near walls and isolated obstacles so
        both the RViz point cloud and the global obstacle layer are visible.
        """

        distance = 4.8
        cosine = math.cos(angle)
        sine = math.sin(angle)

        # Nearer returns in the four room directions.
        if cosine > 0.93:
            distance = min(distance, 2.7 / cosine)
        elif cosine < -0.93:
            distance = min(distance, 1.1 / -cosine)
        if sine > 0.94:
            distance = min(distance, 2.2 / sine)
        elif sine < -0.94:
            distance = min(distance, 1.6 / -sine)

        # Small deterministic obstacles in front-left and front-right.
        if 0.34 < angle < 0.62:
            distance = min(distance, 1.35)
        if -0.82 < angle < -0.59:
            distance = min(distance, 1.8)

        return max(self._range_min, min(distance, self._range_max - 0.01))

    def publish_once(self):
        now = rospy.Time.now()
        angle_min = -math.pi
        angle_increment = 2.0 * math.pi / float(self._sample_count - 1)
        ranges = []
        points = []

        for index in range(self._sample_count):
            angle = angle_min + index * angle_increment
            distance = self._range_for_angle(angle)
            ranges.append(distance)
            points.append((distance * math.cos(angle), distance * math.sin(angle), 0.03))

        scan = LaserScan()
        scan.header.stamp = now
        scan.header.frame_id = self._frame_id
        scan.angle_min = angle_min
        scan.angle_max = math.pi
        scan.angle_increment = angle_increment
        scan.time_increment = 0.0
        scan.scan_time = 1.0 / self._rate_hz
        scan.range_min = self._range_min
        scan.range_max = self._range_max
        scan.ranges = ranges
        self._scan_publisher.publish(scan)

        cloud_header = scan.header
        cloud = point_cloud2.create_cloud_xyz32(cloud_header, points)
        self._cloud_publisher.publish(cloud)
        self._publish_body_marker(now)

    def spin(self):
        rate = rospy.Rate(self._rate_hz)
        while not rospy.is_shutdown():
            self.publish_once()
            rate.sleep()


def main():
    rospy.init_node("mock_lidar_publisher")
    MockLidarPublisher().spin()


if __name__ == "__main__":
    main()
