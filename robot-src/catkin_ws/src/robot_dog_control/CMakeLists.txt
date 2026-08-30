cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_control)

find_package(catkin REQUIRED COMPONENTS
  rospy
  geometry_msgs
  std_msgs
)

catkin_package(CATKIN_DEPENDS rospy geometry_msgs std_msgs)

catkin_install_python(PROGRAMS
  scripts/oumax_cmd_vel_bridge.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)