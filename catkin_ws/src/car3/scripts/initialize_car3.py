#!/usr/bin/env python3
"""Move car3 smoothly into the calibrated parked pose and keep it controlled."""

import time

import rospy
from controller_manager_msgs.srv import ListControllers
from std_msgs.msg import Float64
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


ARM_JOINTS = [
    "arm_joint1",
    "arm_joint2",
    "arm_joint3",
    "arm_joint4",
    "arm_joint5",
]
REFERENCE_PARKED_POSE = [-0.0001, -0.4999, 1.2800, 1.7000, 0.0000]


def parse_positions(value):
    if isinstance(value, str):
        value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, (list, tuple)) or len(value) != len(ARM_JOINTS):
        raise rospy.ROSException("arm_initial_positions must contain five angles")
    return [float(item) for item in value]


def controllers_are_running(list_controllers):
    states = {item.name: item.state for item in list_controllers().controller}
    required = ("joint_state_controller", "arm_controller", "gripper_controller")
    return all(states.get(name) == "running" for name in required)


def main():
    rospy.init_node("initialize_car3")
    arm_positions = parse_positions(
        rospy.get_param("~arm_initial_positions", REFERENCE_PARKED_POSE)
    )
    gripper_position = float(rospy.get_param("~gripper_initial_position", 1.0))
    duration = max(0.5, float(rospy.get_param("~duration", 6.0)))
    timeout = max(5.0, float(rospy.get_param("~controller_wait_timeout", 20.0)))

    rospy.wait_for_service("/controller_manager/list_controllers", timeout=timeout)
    list_controllers = rospy.ServiceProxy(
        "/controller_manager/list_controllers", ListControllers
    )
    deadline = time.monotonic() + timeout
    while not rospy.is_shutdown() and time.monotonic() < deadline:
        if controllers_are_running(list_controllers):
            break
        rospy.sleep(0.1)
    else:
        raise rospy.ROSException("car3 controllers did not reach running state")

    arm_pub = rospy.Publisher("/arm_controller/command", JointTrajectory, queue_size=1)
    gripper_pub = rospy.Publisher(
        "/gripper_controller/command", Float64, queue_size=1, latch=True
    )
    connection_deadline = time.monotonic() + 5.0
    while not rospy.is_shutdown() and time.monotonic() < connection_deadline:
        if arm_pub.get_num_connections() and gripper_pub.get_num_connections():
            break
        rospy.sleep(0.05)

    trajectory = JointTrajectory()
    trajectory.joint_names = list(ARM_JOINTS)
    for fraction in (0.5, 1.0):
        point = JointTrajectoryPoint()
        point.positions = [fraction * value for value in arm_positions]
        point.velocities = [0.0] * len(ARM_JOINTS)
        point.time_from_start = rospy.Duration(duration * fraction)
        trajectory.points.append(point)

    for _ in range(8):
        trajectory.header.stamp = rospy.Time.now()
        arm_pub.publish(trajectory)
        gripper_pub.publish(Float64(data=gripper_position))
        rospy.sleep(0.05)

    rospy.loginfo(
        "car3 initialization commanded: arm=%s, gripper=%.3f, duration=%.1fs; "
        "controllers remain active to hold the pose",
        arm_positions,
        gripper_position,
        duration,
    )


if __name__ == "__main__":
    main()
