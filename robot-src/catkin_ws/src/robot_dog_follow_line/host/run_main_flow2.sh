#!/usr/bin/env bash
# 主流程2（备选主流程）：开始任务后直接巡线（跳过定点巡航导航）。
# 与主流程1（robot_dog_navigation/host/run_main_flow_in_docker.sh：导航 5 点 →
# 抓球放球）互斥；主流程1 行不通时在机器端执行本脚本即可直接进入黑线巡线。
#
# 职责：停占串口/相机的服务（raicom-original-main 占 SPI/串口、oumax-camera 占
# Picamera2）→ 自动拉起雷达后方桥（run_lidar_rear_bridge.sh：容器内 roscore +
# 雷达驱动 + HTTP :8767）→ 用厂商 xgovenv 前台运行 follow_line.py（HSV 黑线 +
# PID，启动即 tracking 巡线；板载按钮 A 巡线 / C color / D init，B 退出）。
# 2026-09-01：合并雷达桥启动后，一条指令即可跑带雷达后方定位（第一个右转）的巡线。
#
# 运行环境：机器端宿主机（不是容器内；容器 ros-noetic 未直通 /dev/ttyAMA0，
# xgolib 需要宿主机串口权限，pi 用户在 dialout 组）。雷达桥需容器 ros-noetic
# 运行中（docker exec），容器未起/桥失败时脚本中止（full exposure，不静默降级）。
#
# 用法：
#   scp robot-src/catkin_ws/src/robot_dog_follow_line/host/run_main_flow2.sh \
#       pi@192.168.137.157:/home/pi/oumax-xgo/
#   bash /home/pi/oumax-xgo/run_main_flow2.sh
#
# 可用环境变量覆盖：
#   RAICOM_XGO_PYTHON  巡线解释器（默认宿主机 xgovenv 路径）
#   RAICOM_FOLLOW_LINE 巡线脚本路径（默认 /home/pi/oumax-xgo/follow_line.py）
#   RAICOM_REAR_BRIDGE 雷达桥脚本路径（默认 /home/pi/oumax-xgo/run_lidar_rear_bridge.sh）
set -euo pipefail

PYTHON="${RAICOM_XGO_PYTHON:-/home/pi/RaspberryPi-CM5/xgovenv/bin/python}"
FOLLOW_LINE="${RAICOM_FOLLOW_LINE:-/home/pi/oumax-xgo/follow_line.py}"
REAR_BRIDGE="${RAICOM_REAR_BRIDGE:-/home/pi/oumax-xgo/run_lidar_rear_bridge.sh}"

echo "[main_flow2] stopping services holding serial/camera..."
sudo systemctl stop raicom-original-main.service
sudo systemctl stop oumax-camera.service

echo "[main_flow2] starting rear lidar bridge: ${REAR_BRIDGE}"
bash "${REAR_BRIDGE}"
echo "[main_flow2] rear bridge ok（见上方 bridge-ok 与 rear_m）"

echo "[main_flow2] starting line following: ${PYTHON} ${FOLLOW_LINE}"
exec "${PYTHON}" "${FOLLOW_LINE}"
