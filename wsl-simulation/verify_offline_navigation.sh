#!/usr/bin/env bash
# Reproducible headless check for the local-only navigation demo.
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bash "${SCRIPT_DIR}/setup_offline_navigation.sh"

source /opt/ros/noetic/setup.bash
source "${RAICOM_WSL_WORKSPACE:-${HOME}/raicom_ws}/devel/setup.bash"
unset ROS_HOSTNAME
export ROS_MASTER_URI="http://127.0.0.1:11311"
export ROS_IP="127.0.0.1"
export ROS_LOCALHOST_ONLY=1

LOG_DIRECTORY="$(mktemp -d)"
MASTER_PID=""
NAVIGATION_PID=""
OPEN_RVIZ="false"
if [ "${RAICOM_VERIFY_RVIZ:-0}" = "1" ]; then
  OPEN_RVIZ="true"
fi
cleanup() {
  if [ -n "${NAVIGATION_PID}" ]; then
    kill "${NAVIGATION_PID}" 2>/dev/null || true
    wait "${NAVIGATION_PID}" 2>/dev/null || true
  fi
  if [ -n "${MASTER_PID}" ]; then
    kill "${MASTER_PID}" 2>/dev/null || true
    wait "${MASTER_PID}" 2>/dev/null || true
  fi
  rm -f "${LOG_DIRECTORY}/roscore.log" "${LOG_DIRECTORY}/navigation.log"
  rmdir "${LOG_DIRECTORY}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

roscore -p 11311 >"${LOG_DIRECTORY}/roscore.log" 2>&1 &
MASTER_PID=$!
sleep 2
roslaunch robot_dog_navigation offline_navigation.launch "open_rviz:=${OPEN_RVIZ}" \
  >"${LOG_DIRECTORY}/navigation.log" 2>&1 &
NAVIGATION_PID=$!

for _ in $(seq 1 30); do
  if rostopic list 2>/dev/null | grep -qx "/move_base/global_costmap/costmap"; then
    break
  fi
  sleep 0.5
done

for topic in /map /scan /lidar_points /robot_body_marker \
  /move_base/global_costmap/costmap /move_base/local_costmap/costmap; do
  rostopic list | grep -qx "${topic}"
done
if [ "${OPEN_RVIZ}" = "true" ]; then
  rosnode list | grep -qx "/rviz"
fi

test "$(rosparam get /move_base/base_global_planner)" = "global_planner/GlobalPlanner"
timeout 5 rostopic echo -n 1 /map >/dev/null
timeout 5 rostopic echo -n 1 /scan >/dev/null
timeout 5 rostopic echo -n 1 /lidar_points >/dev/null
marker_message="$(timeout 5 rostopic echo -n 1 /robot_body_marker)"
printf '%s\n' "${marker_message}" | grep -A 4 '^scale:' | grep -qx '  x: 0.27'
printf '%s\n' "${marker_message}" | grep -A 4 '^scale:' | grep -qx '  y: 0.16'
timeout 5 rostopic echo -n 1 /move_base/global_costmap/costmap >/dev/null
timeout 5 rostopic echo -n 1 /move_base/local_costmap/costmap >/dev/null

# Ask RViz's normal goal topic for a route within the centre room, then require
# the actual official GlobalPlanner output rather than only checking its config.
rostopic pub -1 /move_base_simple/goal geometry_msgs/PoseStamped \
  '{header: {frame_id: "map"}, pose: {position: {x: 0.40, y: -0.75, z: 0.0}, orientation: {w: 1.0}}}' \
  >/dev/null
timeout 5 rostopic echo -n 1 /move_base/GlobalPlanner/plan >/dev/null

echo "Offline navigation verification passed: local map, lidar point cloud, global/local costmaps and GlobalPlanner path are available."
