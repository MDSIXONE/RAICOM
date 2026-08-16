#!/usr/bin/env python3
"""Augment ros_control joint states with the five passive gripper joints."""

import rospy
from sensor_msgs.msg import JointState


MIMIC_JOINTS = {
    "l_joint": -1.0,
    "r_in_joint": 1.0,
    "l_in_joint": -1.0,
    "r_out_joint": -1.0,
    "l_out_joint": 1.0,
}


class GripperJointStateAugmenter:
    def __init__(self):
        self.publisher = rospy.Publisher("/joint_states_full", JointState, queue_size=10)
        self.subscriber = rospy.Subscriber(
            "/joint_states", JointState, self.callback, queue_size=10
        )

    def callback(self, message):
        if "r_joint" not in message.name:
            rospy.logwarn_throttle(5.0, "r_joint is missing from /joint_states")
            self.publisher.publish(message)
            return

        source_index = message.name.index("r_joint")
        source_position = message.position[source_index]
        output = JointState()
        output.header = message.header
        output.name = list(message.name)
        output.position = list(message.position)
        output.velocity = list(message.velocity) if message.velocity else []
        output.effort = list(message.effort) if message.effort else []

        for name, multiplier in MIMIC_JOINTS.items():
            if name in output.name:
                continue
            output.name.append(name)
            output.position.append(source_position * multiplier)
            if output.velocity:
                velocity = message.velocity[source_index] if len(message.velocity) > source_index else 0.0
                output.velocity.append(velocity * multiplier)
            if output.effort:
                effort = message.effort[source_index] if len(message.effort) > source_index else 0.0
                output.effort.append(effort * multiplier)

        self.publisher.publish(output)


if __name__ == "__main__":
    rospy.init_node("gripper_mimic")
    GripperJointStateAugmenter()
    rospy.spin()
