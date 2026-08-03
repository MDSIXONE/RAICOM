#!/usr/bin/env bash
# Start the offline map, simulated lidar, official global planner and RViz.
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bash "${SCRIPT_DIR}/setup_offline_navigation.sh"

source /opt/ros/noetic/setup.bash
source "${RAICOM_WSL_WORKSPACE:-${HOME}/raicom_ws}/devel/setup.bash"
unset ROS_HOSTNAME
export ROS_MASTER_URI="http://127.0.0.1:11311"
export ROS_IP="127.0.0.1"
export ROS_LOCALHOST_ONLY=1

STARTED_MASTER=0
MASTER_PID=""
cleanup() {
  if [ "${STARTED_MASTER}" -eq 1 ] && [ -n "${MASTER_PID}" ]; then
    kill "${MASTER_PID}" 2>/dev/null || true
    wait "${MASTER_PID}" 2>/dev/null || true
  fi
}

if ! rostopic list >/dev/null 2>&1; then
  mkdir -p "${HOME}/.ros/log"
  roscore -p 11311 >"${HOME}/.ros/log/raicom_offline_roscore.log" 2>&1 &
  MASTER_PID=$!
  STARTED_MASTER=1
  for _ in $(seq 1 30); do
    if rostopic list >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done
fi

if ! rostopic list >/dev/null 2>&1; then
  cleanup
  echo "The local ROS Master did not start at ${ROS_MASTER_URI}." >&2
  exit 1
fi

echo "Launching local-only offline navigation against ${ROS_MASTER_URI}"
echo "No robot hardware node is included."
trap cleanup EXIT INT TERM
roslaunch robot_dog_navigation offline_navigation.launch "$@"
