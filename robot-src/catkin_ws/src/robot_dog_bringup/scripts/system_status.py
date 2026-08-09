#!/usr/bin/env python3
"""Publish basic, read-only host status for the robot dog ROS workspace."""

import platform
import socket

import rospy
from std_msgs.msg import String


def make_status():
    """Return diagnostics without sending hardware-control commands."""
    return "hostname={}; kernel={}; ros_distro={}".format(
        socket.gethostname(),
        platform.release(),
        rospy.get_param("/rosdistro", "unknown"),
    )


def main():
    rospy.init_node("system_status")
    rate_hz = float(rospy.get_param("~rate", 1.0))
    if rate_hz <= 0.0:
        raise rospy.ROSInitException("~rate must be greater than zero")

    publisher = rospy.Publisher(
        "/robot_dog_bringup/status", String, queue_size=1, latch=True
    )
    rate = rospy.Rate(rate_hz)
    while not rospy.is_shutdown():
        publisher.publish(make_status())
        rate.sleep()


if __name__ == "__main__":
    main()
