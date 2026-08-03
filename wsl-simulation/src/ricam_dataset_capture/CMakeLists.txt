cmake_minimum_required(VERSION 3.0.2)
project(ricam_dataset_capture)

find_package(catkin REQUIRED COMPONENTS cv_bridge rospy sensor_msgs)
catkin_package()

catkin_install_python(PROGRAMS scripts/timed_image_capture.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch data
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
