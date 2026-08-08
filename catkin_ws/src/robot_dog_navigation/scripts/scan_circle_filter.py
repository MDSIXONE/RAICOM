#!/usr/bin/env python3
"""Filter lidar points inside a circle and/or an angular sector.

Two masking regions can be applied to the raw scan:

1. A circle centered at (center_x, center_y) with a given radius (mask by
   Cartesian distance), useful for a robotic arm mounted near the lidar.
2. An angular sector around sector_center_deg (0 = directly in front of the
   lidar, positive = counter-clockwise) with half-width sector_half_width_deg;
   points inside the sector are masked only up to sector_max_range metres so
   distant walls are kept.  A sector_max_range of 0 or inf means no range
   limit.

Masked points are replaced by infinity, and their intensities by 0.0.
"""

import math

import rospy
from sensor_msgs.msg import LaserScan


def _wrap_pi(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class ScanCircleFilter:
    """Republish /scan with circular and sector regions masked out."""

    def __init__(self):
        self._scan_topic = rospy.get_param("~scan_topic", "/scan")
        self._filtered_topic = rospy.get_param("~filtered_topic", "/scan_filtered")

        self._center_x = float(rospy.get_param("~center_x", 0.15))
        self._center_y = float(rospy.get_param("~center_y", 0.0))
        self._radius = float(rospy.get_param("~radius", 0.15))
        if self._radius < 0.0:
            rospy.logerr("radius 不能为负：%.3f", self._radius)
            raise rospy.ROSException("radius must be non-negative")
        self._radius_squared = self._radius * self._radius

        self._sector_center = math.radians(
            float(rospy.get_param("~sector_center_deg", 0.0))
        )
        self._sector_half_width = math.radians(
            float(rospy.get_param("~sector_half_width_deg", 5.0))
        )
        if self._sector_half_width < 0.0:
            rospy.logerr("sector_half_width_deg 不能为负：%.3f", self._sector_half_width)
            raise rospy.ROSException("sector_half_width_deg must be non-negative")
        self._sector_max_range = float(
            rospy.get_param("~sector_max_range", 1.0)
        )
        if self._sector_max_range < 0.0:
            rospy.logerr("sector_max_range 不能为负：%.3f", self._sector_max_range)
            raise rospy.ROSException("sector_max_range must be non-negative")

        self._publisher = rospy.Publisher(
            self._filtered_topic, LaserScan, queue_size=1
        )
        rospy.Subscriber(self._scan_topic, LaserScan, self._scan_callback, queue_size=1)
        rospy.loginfo(
            "scan_circle_filter: 圆 (%.3f, %.3f, r=%.3f) 扇形 %+.1f° ± %.1f° (上限 %.3f m)，%s -> %s",
            self._center_x, self._center_y, self._radius,
            math.degrees(self._sector_center), math.degrees(self._sector_half_width),
            self._sector_max_range,
            self._scan_topic, self._filtered_topic,
        )

    def _inside_circle(self, angle, distance):
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)
        dx = x - self._center_x
        dy = y - self._center_y
        return dx * dx + dy * dy <= self._radius_squared

    def _inside_sector(self, angle, distance):
        if self._sector_half_width <= 0.0:
            return False
        if abs(_wrap_pi(angle - self._sector_center)) > self._sector_half_width:
            return False
        if self._sector_max_range > 0.0 and distance > self._sector_max_range:
            return False
        return True

    def _masked(self, angle, distance):
        return self._inside_circle(angle, distance) or self._inside_sector(
            angle, distance
        )

    def _scan_callback(self, scan):
        filtered = LaserScan()
        filtered.header = scan.header
        filtered.angle_min = scan.angle_min
        filtered.angle_max = scan.angle_max
        filtered.angle_increment = scan.angle_increment
        filtered.time_increment = scan.time_increment
        filtered.scan_time = scan.scan_time
        filtered.range_min = scan.range_min
        filtered.range_max = scan.range_max
        filtered.ranges = list(scan.ranges)
        filtered.intensities = list(scan.intensities)

        for index, distance in enumerate(filtered.ranges):
            if not math.isfinite(distance):
                continue
            if distance < scan.range_min or distance > scan.range_max:
                continue
            angle = scan.angle_min + index * scan.angle_increment
            if self._masked(angle, distance):
                filtered.ranges[index] = float("inf")
                if index < len(filtered.intensities):
                    filtered.intensities[index] = 0.0

        self._publisher.publish(filtered)


def main():
    rospy.init_node("scan_circle_filter")
    ScanCircleFilter()
    rospy.spin()


if __name__ == "__main__":
    main()
