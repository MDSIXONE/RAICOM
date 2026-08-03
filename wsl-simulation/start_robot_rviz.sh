#!/usr/bin/env bash
# Open only local RViz against the robot's ROS Master.  It never starts a
# Master, base driver, or hardware node on this computer.
set -e

source /opt/ros/noetic/setup.bash
source "${RAICOM_WSL_WORKSPACE:-${HOME}/raicom_ws}/devel/setup.bash"

ROBOT_IP="${RAICOM_ROBOT_IP:-192.168.137.157}"
WSL_IP="${RAICOM_WSL_IP:-192.168.137.139}"
unset ROS_HOSTNAME
export ROS_MASTER_URI="http://${ROBOT_IP}:11311"
export ROS_IP="${WSL_IP}"
unset ROS_LOCALHOST_ONLY

echo "Opening local RViz via ${ROS_MASTER_URI}; callback address: ${ROS_IP}"
echo "This script does not start a local Master or publish a base command."
exec rviz -d "$(rospack find robot_dog_navigation)/rviz/offline_navigation.rviz"
