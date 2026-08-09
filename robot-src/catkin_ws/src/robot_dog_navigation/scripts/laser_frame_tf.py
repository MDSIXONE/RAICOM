#!/usr/bin/env python3
import rospy
import tf2_ros
from geometry_msgs.msg import TransformStamped


def main():
    rospy.init_node("laser_frame_tf")
    parent = rospy.get_param("~parent_frame", "base_link")
    child = rospy.get_param("~child_frame", "laser_frame")
    x = rospy.get_param("~x", 0.16)
    y = rospy.get_param("~y", 0.0)
    z = rospy.get_param("~z", 0.15)
    rate = rospy.Rate(rospy.get_param("~rate", 10.0))

    br = tf2_ros.TransformBroadcaster()
    while not rospy.is_shutdown():
        t = TransformStamped()
        t.header.stamp = rospy.Time.now()
        t.header.frame_id = parent
        t.child_frame_id = child
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.w = 1.0
        br.sendTransform(t)
        rate.sleep()


if __name__ == "__main__":
    main()
