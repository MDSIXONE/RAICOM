#!/usr/bin/env bash
# 主流程一键入口（宿主机）：容器内跑导航 5 点 → 容器内跑抓球放球编排。
# 与机器端 /home/pi/run_main_flow.sh 等价；导航完成后 main_flow.py 经 ssh 停
# oumax-camera/oumax-manual 释放相机与串口（容器→宿主 ssh 免密），随后在同一
# 容器内用厂商 xgovenv 运行 catkin 包 robot_dog_ball_grab 的球编排。
#
# 前置：容器 ros-noetic 已挂载 /home/pi 且直通 /dev/ttyAMA0、/dev/video0
# （docs/technical/2026-08-16-docker-runtime-unification.md §2.1）；
# robot_dog_main.launch 已用 AMCL 定点模式启动且机器与地图原点对齐。
#
# --side-distances 当前按实机地图已知区临时收缩（0.5,0.25,-0.575）；
# 地图补扫右下角后恢复 0.5,1.65,-0.575。
set -euo pipefail

CONTAINER="${RAICOM_CONTAINER:-ros-noetic}"
MAIN_FLOW="/root/catkin_ws/src/robot_dog_navigation/scripts/main_flow.py"

docker exec "$CONTAINER" bash -lc \
  "source /opt/ros/noetic/setup.bash \
   && source /root/catkin_ws/devel/setup.bash \
   && exec python3 '${MAIN_FLOW}' --enable-motion --grab-release-ssh pi@127.0.0.1 \
        --side-distances 0.5,0.25,-0.575"