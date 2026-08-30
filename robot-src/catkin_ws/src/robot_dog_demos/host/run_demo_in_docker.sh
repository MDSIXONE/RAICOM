#!/usr/bin/env bash
# 厂商示例容器化运行启动器：在 ros-noetic 容器内用厂商 xgovenv 运行 demos 包脚本，
# 与导航同一容器环境，避免宿主机/容器割裂。
#
# 前置：容器需挂载 /home/pi 且直通 /dev/ttyAMA0、/dev/video0（见
# docs/technical/2026-08-16-docker-runtime-unification.md §2.1）。
#
# 用法：
#   run_demo_in_docker.sh <脚本名或相对路径> [参数...]
# 示例：
#   run_demo_in_docker.sh ball.py
#   run_demo_in_docker.sh follow_person/follow_person.py
#   run_demo_in_docker.sh common/face.py
#   run_demo_in_docker.sh --release-camera-serial -- color.py
#
# 注意：多数示例在容器内通过 /home/pi 挂载直接运行厂商原版脚本；本包 scripts/
# 是同一批文件的入库副本，容器运行推荐直接指向 /home/pi/RaspberryPi-CM5 下的
# 厂商目录（机器上已存在且 xgolib 等库相对路径依赖原目录结构）。
set -euo pipefail

CONTAINER="${RAICOM_CONTAINER:-ros-noetic}"
XGO_PY="${XGO_PY:-/home/pi/RaspberryPi-CM5/xgovenv/bin/python}"
# 机器上厂商 demos 根目录（三机型 + common 均在此）
VENDOR_DEMOS_ROOT="${VENDOR_DEMOS_ROOT:-/home/pi/RaspberryPi-CM5/robots/Mini3W_W/demos}"

RELEASE_SERVICES=0
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-camera-serial)
      RELEASE_SERVICES=1
      shift
      ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
      ;;
    *)
      EXTRA_ARGS=("$@")
      break
      ;;
  esac
done

if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
  echo "用法: run_demo_in_docker.sh [--release-camera-serial] [--] <脚本名> [参数...]" >&2
  exit 2
fi

DEMO="${EXTRA_ARGS[0]}"
DEMO_ARGS=("${EXTRA_ARGS[@]:1}")

if [[ "$RELEASE_SERVICES" -eq 1 ]]; then
  echo "Stopping oumax-camera + oumax-manual on host (release camera & serial)..."
  sudo systemctl stop oumax-camera.service
  sudo systemctl stop oumax-manual.service
fi

SCRIPT_PATH="${VENDOR_DEMOS_ROOT}/${DEMO}"
echo "Running ${DEMO} inside ${CONTAINER}: ${XGO_PY} ${SCRIPT_PATH} ${DEMO_ARGS[*]}"
docker exec "$CONTAINER" bash -lc \
  "cd ${VENDOR_DEMOS_ROOT} && exec ${XGO_PY} ${SCRIPT_PATH} ${DEMO_ARGS[*]}"
