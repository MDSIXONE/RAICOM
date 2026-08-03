#!/usr/bin/env bash
# Start a ROS Master that cannot advertise or query a machine/remote Master.
set -e

source /opt/ros/noetic/setup.bash
unset ROS_HOSTNAME
export ROS_MASTER_URI="http://127.0.0.1:11311"
export ROS_IP="127.0.0.1"
export ROS_LOCALHOST_ONLY=1

echo "Starting local-only ROS Master at ${ROS_MASTER_URI}"
echo "No smartcar or machine-dog ROS Master is contacted."
exec roscore -p 11311
