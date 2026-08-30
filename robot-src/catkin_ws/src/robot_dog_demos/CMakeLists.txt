cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_demos)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/ball.py
  scripts/color.py
  scripts/dog_Joystick.py
  scripts/dog_show.py
  scripts/face_decetion.py
  scripts/face_mask.py
  scripts/group.py
  scripts/hands.py
  scripts/hp.py
  scripts/pose_dog.py
  scripts/shijiao_UDP.py
  scripts/shijiao.py
  scripts/common/device.py
  scripts/common/face.py
  scripts/common/face_mask.py
  scripts/common/fru.py
  scripts/common/group.py
  scripts/common/language.py
  scripts/common/LLM.py
  scripts/common/network_app.py
  scripts/common/qrcode.py
  scripts/common/receiver_workflow.py
  scripts/common/run_blockly.py
  scripts/common/volume.py
  scripts/common/wifi_set.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
