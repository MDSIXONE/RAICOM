#!/usr/bin/env bash
# 雷达后方距离桥：确保容器内 roscore + 雷达 /scan + lidar_rear_range_http.py
# （HTTP :8767 /rear）就绪，供巡线 follow_line.py 轮询后方距离。
#
# 容器内逻辑独立为 lidar_rear_bridge_inner.sh（docker exec 调用），避免
# `bash -lc "长字符串"` 里 pkill -f 匹配自身 argv 导致脚本被杀（2026-09-01
# 实机复现并修复）。
#
# 用法（宿主机）：
#   bash run_lidar_rear_bridge.sh   # 幂等：已起则复用，输出 bridge-ok 与 rear_m
set -euo pipefail
CONTAINER="${RAICOM_ROS_CONTAINER:-ros-noetic}"
PORT="${RAICOM_REAR_PORT:-8767}"
INNER="${RAICOM_REAR_INNER:-/home/pi/oumax-xgo/lidar_rear_bridge_inner.sh}"

docker exec "$CONTAINER" bash "${INNER}"

curl -s -m 3 "http://127.0.0.1:${PORT}/rear"
echo
