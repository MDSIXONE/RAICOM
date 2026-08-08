#!/usr/bin/env bash
# Start the LOCAL ROS master and the local control station (ball detector +
# RViz).  The robot's bringup connects to this master and publishes map,
# lidar and camera data; RViz displays them all.
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export DISPLAY="${DISPLAY:-:0}"

# WSLg workaround: the shared Wayland runtime directory may belong to another
# UID, which breaks the RViz window.  Use a private runtime dir, X11 and
# software OpenGL for deterministic rendering (see smartcar2026 operations).
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg-runtime-$(id -u)}"
mkdir -p "${XDG_RUNTIME_DIR}"
chmod 0700 "${XDG_RUNTIME_DIR}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export DISABLE_ROS1_EOL_WARNINGS=1
export MESA_SHADER_CACHE_DIR="${MESA_SHADER_CACHE_DIR:-${HOME}/.cache/mesa_shader_cache}"
mkdir -p "${MESA_SHADER_CACHE_DIR}" 2>/dev/null || true

source /opt/ros/noetic/setup.bash
source "${RAICOM_WSL_WORKSPACE:-${HOME}/raicom_ws}/devel/setup.bash"
export ROS_PACKAGE_PATH="${SCRIPT_DIR}/src:${ROS_PACKAGE_PATH}"

LOCAL_IP="${RAICOM_LOCAL_IP:-192.168.137.232}"
ROBOT_IP="${RAICOM_ROBOT_IP:-192.168.137.157}"
unset ROS_HOSTNAME
export ROS_MASTER_URI="http://${LOCAL_IP}:11311"
export ROS_IP="${LOCAL_IP}"
unset ROS_LOCALHOST_ONLY

echo "Local control master: ${ROS_MASTER_URI} (WSL IP ${ROS_IP})"
echo "Robot expected at: ${ROBOT_IP} (set ROS_MASTER_URI on the robot side)"

STARTED_MASTER=0
MASTER_PID=""
cleanup() {
  if [ "${STARTED_MASTER}" -eq 1 ] && [ -n "${MASTER_PID}" ]; then
    kill "${MASTER_PID}" 2>/dev/null || true
    wait "${MASTER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if ! rostopic list >/dev/null 2>&1; then
  mkdir -p "${HOME}/.ros/log"
  roscore -p 11311 >"${HOME}/.ros/log/raicom_local_roscore.log" 2>&1 &
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

echo "Launching local control station (ball detector + RViz)..."
roslaunch ball_spotter local_control.launch "$@"
