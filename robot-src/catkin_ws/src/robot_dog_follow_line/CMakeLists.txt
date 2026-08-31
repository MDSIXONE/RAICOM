cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_follow_line)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/follow_line.py
  scripts/follow_line_tune.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
