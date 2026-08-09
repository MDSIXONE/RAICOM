cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_navigation)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  rospy
  sensor_msgs
  tf2_ros
  visualization_msgs
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs nav_msgs rospy sensor_msgs tf2_ros visualization_msgs
)

catkin_install_python(PROGRAMS
  scripts/initial_pose_publisher.py
  scripts/mock_lidar_publisher.py
  scripts/scan_circle_filter.py
  scripts/scan_to_cloud_and_body.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY config launch maps rviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
