#!/usr/bin/env python3
"""Fail fast when Mini2 sensors are publishing only self-occluded data."""

import math
import statistics
import sys

import rospy
from sensor_msgs.msg import Image, LaserScan


def scan_health(message):
    finite = [value for value in message.ranges if math.isfinite(value)]
    if not finite:
        return 0.0, 0.0, 1.0
    finite_ratio = len(finite) / float(len(message.ranges))
    median_range = statistics.median(finite)
    near_ratio = sum(value <= 0.10 for value in finite) / float(len(finite))
    return finite_ratio, median_range, near_ratio


def camera_health(message):
    encoding = message.encoding.lower()
    if encoding not in ("rgb8", "bgr8") or message.width == 0 or message.height == 0:
        return 0.0, 0
    data = memoryview(message.data)
    intensities = []
    colors = set()
    pixel_stride = max(1, (message.width * message.height) // 20000)
    for pixel in range(0, message.width * message.height, pixel_stride):
        row, column = divmod(pixel, message.width)
        offset = row * message.step + column * 3
        color = tuple(data[offset : offset + 3])
        if len(color) != 3:
            continue
        colors.add(color)
        intensities.append(sum(color) / 3.0)
    contrast = statistics.pstdev(intensities) if intensities else 0.0
    return contrast, len(colors)


def main():
    rospy.init_node("mini2_sensor_health_check", anonymous=True)
    scan = rospy.wait_for_message("/scan", LaserScan, timeout=15.0)
    image = rospy.wait_for_message("/camera/rgb/image_raw", Image, timeout=15.0)
    finite_ratio, median_range, near_ratio = scan_health(scan)
    contrast, unique_colors = camera_health(image)
    print(
        "scan finite={:.1%}, median={:.3f}m, <=0.10m={:.1%}; "
        "camera contrast={:.1f}, sampled colors={}".format(
            finite_ratio,
            median_range,
            near_ratio,
            contrast,
            unique_colors,
        )
    )
    healthy = (
        finite_ratio >= 0.20
        and median_range > 0.10
        and near_ratio < 0.25
        and contrast > 5.0
        and unique_colors >= 8
    )
    if not healthy:
        print("Mini2 sensor health check failed: likely self-occlusion or invalid data", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
