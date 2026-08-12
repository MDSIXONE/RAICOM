#!/usr/bin/env bash
# 自动对准夹球启动器：先由 handover 帮助程序接管串口（停原厂 UI、起 OUMAX
# 手控服务），再进入 ROS 容器运行对准夹球节点，退出时自动恢复原厂 UI。
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
  exec roslaunch robot_dog_teleop ball_align_grab.launch enable_motion:=true
'
