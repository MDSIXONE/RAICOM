#!/usr/bin/env bash
# Build the local-only demo in WSL's ext4 filesystem.  Source files stay in the
# checked-out Windows repository; build artifacts stay under ~/raicom_ws.
set -e

if [ ! -f /opt/ros/noetic/setup.bash ]; then
  echo "ROS Noetic was not found at /opt/ros/noetic." >&2
  exit 1
fi

# Do not enable `set -u` before sourcing ROS Noetic's setup script.
source /opt/ros/noetic/setup.bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
SOURCE_DIRECTORY="${REPOSITORY_ROOT}/robot-src/catkin_ws/src"
WORKSPACE="${RAICOM_WSL_WORKSPACE:-${HOME}/raicom_ws}"

if [ ! -f "${SOURCE_DIRECTORY}/CMakeLists.txt" ]; then
  echo "Catkin sources were not found: ${SOURCE_DIRECTORY}" >&2
  exit 1
fi

mkdir -p "${WORKSPACE}"
if [ -e "${WORKSPACE}/src" ] && [ ! -L "${WORKSPACE}/src" ]; then
  echo "Refusing to replace existing non-symlink workspace source directory: ${WORKSPACE}/src" >&2
  exit 1
fi

ln -sfn "${SOURCE_DIRECTORY}" "${WORKSPACE}/src"
cd "${WORKSPACE}"

# robot_dog_lidar is a hardware package whose vendor SDK is mounted only in the
# robot Docker container.  Excluding it keeps this WSL build fully offline.
catkin_make -DCATKIN_BLACKLIST_PACKAGES=robot_dog_lidar

echo "Offline workspace built: ${WORKSPACE}"
echo "Source it with: source ${WORKSPACE}/devel/setup.bash"
