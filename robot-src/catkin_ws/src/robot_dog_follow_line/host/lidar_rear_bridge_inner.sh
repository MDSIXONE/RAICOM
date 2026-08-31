#!/usr/bin/env bash
# 容器内执行：确保 roscore + 雷达 /scan + lidar_rear_range_http.py(:8767) 就绪。
# 由宿主机 run_lidar_rear_bridge.sh 通过 docker exec 调用。
#
# 为何独立成脚本：原实现把整段逻辑塞进 `docker exec bash -lc "长字符串"`，
# bash -lc 的 argv 含展开后的 `lidar_rear_range_http.py` 完整路径，执行
# `pkill -f lidar_rear_range_http.py` 时把 bash -lc 自身杀掉（2026-09-01 实机
# 复现：roscore/雷达已起、8767 未起、脚本中止）。独立脚本的进程 argv 只有
# 脚本路径，脚本内容不进 argv，pkill -f 不会自匹配。
set -uo pipefail

# source ROS 环境时临时关 -u：catkin profile 脚本会引用尚未定义的
# ROS_MASTER_URI（如 10.roslaunch.sh line 3），nounset 下 source 直接报错
set +u
source /opt/ros/noetic/setup.bash
source /root/catkin_ws/devel/setup.bash 2>/dev/null || true
set -u
export ROS_MASTER_URI=http://127.0.0.1:11311
export ROS_IP=127.0.0.1

PORT="${RAICOM_REAR_PORT:-8767}"
SCRIPT_CT="/root/catkin_ws/src/robot_dog_navigation/scripts/lidar_rear_range_http.py"

if ! rostopic list >/dev/null 2>&1; then
  nohup roscore >/tmp/roscore_rear.log 2>&1 &
  sleep 2
fi
if ! timeout 2 rostopic echo -n 1 /scan >/dev/null 2>&1; then
  nohup roslaunch robot_dog_lidar lidar.launch test_duration_sec:=0 >/tmp/lidar_rear.log 2>&1 &
  for _ in $(seq 1 30); do
    timeout 1 rostopic echo -n 1 /scan >/dev/null 2>&1 && break
    sleep 0.3
  done
fi
if ! curl -s -m 1 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  # 清残留 http 进程后重启（独立脚本 argv 无该模式，安全）
  pkill -f lidar_rear_range_http.py 2>/dev/null || true
  sleep 0.3
  nohup python3 "${SCRIPT_CT}" _port:="${PORT}" >/tmp/lidar_rear_http.log 2>&1 &
  sleep 0.8
fi
echo bridge-ok
