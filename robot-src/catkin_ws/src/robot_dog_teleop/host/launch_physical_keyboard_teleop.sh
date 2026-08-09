#!/usr/bin/env bash
# Interactive host-side launcher.  It hands the serial port over before
# starting the ROS keyboard node, and always attempts to restore the original
# application once roslaunch exits.
set -euo pipefail

HANDOVER="/usr/local/sbin/raicom-control-handover"

if [[ ! -x "$HANDOVER" ]]; then
  echo "Handover helper is missing. Run install_host_handover.sh --cutover first." >&2
  exit 2
fi

sudo "$HANDOVER" acquire
cleanup() {
  local code=$?
  sudo "$HANDOVER" release || echo "WARNING: automatic restoration failed; run: sudo $HANDOVER release" >&2
  exit "$code"
}
trap cleanup EXIT HUP INT TERM

docker exec -it ros-noetic bash -lc '
  source /opt/ros/noetic/setup.bash
  source /root/catkin_ws/devel/setup.bash
  exec roslaunch robot_dog_teleop physical_keyboard_teleop.launch enable_motion:=true
'
