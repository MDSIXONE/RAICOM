#!/usr/bin/env python3
"""Convert the hardware LaserScan stream to RViz points and publish a body marker.

This node is visualization-only: it neither opens a device nor publishes a
velocity command.  The laser driver remains the sole owner of the serial port.
"""

import math

import rospy
from sensor_msgs import point_cloud2
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker


class ScanToCloudAndBody:
    """Publish one PointCloud2 and the fixed visual body for every lidar scan."""

    def __init__(self):
        self._scan_topic = rospy.get_param("~scan_topic", "/scan")
        self._cloud_topic = rospy.get_param("~cloud_topic", "/lidar_points")
        self._body_length = float(rospy.get_param("~body_length", 0.27))
        self._body_width = float(rospy.get_param("~body_width", 0.16))
        self._body_height = float(rospy.get_param("~body_height", 0.10))
        self._cloud_publisher = rospy.Publisher(
            self._cloud_topic, point_cloud2.PointCloud2, queue_size=1
        )
        self._body_marker_publisher = rospy.Publisher(
            "/robot_body_marker", Marker, queue_size=1, latch=True
        )
        rospy.Subscriber(self._scan_topic, LaserScan, self._scan_callback, queue_size=1)

    def _publish_body_marker(self, stamp):
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

    def _scan_callback(self, scan):
        points = []
        for index, distance in enumerate(scan.ranges):
            if not math.isfinite(distance):
                continue
            if distance < scan.range_min or distance > scan.range_max:
                continue
            angle = scan.angle_min + index * scan.angle_increment
            points.append((distance * math.cos(angle), distance * math.sin(angle), 0.0))

        header = scan.header
        if header.stamp == rospy.Time():
            header.stamp = rospy.Time.now()
        self._cloud_publisher.publish(point_cloud2.create_cloud_xyz32(header, points))
        self._publish_body_marker(header.stamp)


def main():
    rospy.init_node("scan_to_cloud_and_body")
    ScanToCloudAndBody()
    rospy.spin()


if __name__ == "__main__":
    main()
