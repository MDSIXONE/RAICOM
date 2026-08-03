cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_teleop)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  rospy
)

catkin_package(CATKIN_DEPENDS geometry_msgs rospy)

catkin_install_python(PROGRAMS
  scripts/keyboard_pulse_teleop.py
  scripts/physical_keyboard_teleop.py
  scripts/physical_keyboard_continuous.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
