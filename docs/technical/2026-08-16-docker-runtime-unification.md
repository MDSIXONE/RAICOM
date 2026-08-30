# 运行环境统一容器化方案（2026-08-16）

> 目标：把厂商示例程序与抓球程序统一进 `ros-noetic` Docker 容器运行，消除"导航在容器、厂商程序在宿主机"的割裂形态。本文档是方案与实施清单；机器离线，实机验证点全部标注【待实机】。

## 1. 现状运行矩阵（问题）

| 程序 | 当前位置 | 运行方式 | 依赖 |
| --- | --- | --- | --- |
| ROS 导航/雷达/桥/simple_odom | 容器 ros-noetic | `docker exec -d ros-noetic bash -lc "... roslaunch robot_dog_main.launch"` | ROS Noetic |
| 主流程 main_flow.py | 容器内 | 同上（actionlib 发 goal） | ROS |
| 厂商示例（ball.py、follow_line.py、color.py…） | 宿主机 `/home/pi/RaspberryPi-CM5/robots/*/demos/` | 宿主机 `xgovenv/bin/python` | picamera2、uiutils、xgolib、xgoscreen、OpenCV |
| 抓球四脚本（ball_yolo_grab / ball_release / rotate / ball_grab_release） | 宿主机 `/home/pi/oumax-xgo/` | 宿主机 `xgovenv/bin/python`（main_flow 经 ssh 触发） | picamera2、onnxruntime、uiutils(xgolib) |

**割裂点**：ROS 侧在容器、厂商视觉/控制侧在宿主机 xgovenv；主流程在容器内通过 `ssh` 跳回宿主机停服务、再跑抓球程序。串口（/dev/ttyAMA0）由宿主机 oumax-manual 服务持有，相机由宿主机 oumax-camera 服务持有。

## 2. 统一方案（推荐）：容器挂载厂商环境 + 设备映射

核心思路：**容器与宿主机共享 `/home/pi` 挂载 + 硬件设备直通**，厂商 venv（xgovenv）按原路径挂载进容器后可直接复用（venv 内部引用的是绝对路径 `/home/pi/RaspberryPi-CM5/xgovenv/bin/python`，bind mount 同路径即可用），所有厂商示例与抓球程序改由容器内执行。

### 2.1 容器启动参数（机器上线后重建或 docker update 生效【待实机】）

```bash
docker run -d --name ros-noetic \
  --network host --privileged \
  -v /home/pi/ros_ws:/root/catkin_ws \
  -v /home/pi:/home/pi \            # 厂商环境 + xgovenv + oumax-xgo 同路径挂载
  -v /dev:/dev \                    # 或逐设备：--device /dev/ttyAMA0:/dev/ttyAMA0 --device /dev/video0:/dev/video0
  <镜像> 
```

注意：
- `-v /dev:/dev` 是给容器内直接访问串口（ttyAMA0）与相机（video0）的最小做法；`--privileged` 可进一步覆盖 SPI 屏等（xgoscreen 依赖 /dev/spidev、/dev/fb0）。
- 若现有容器无法重建，可评估 `docker update --device`（部分 Docker 版本支持运行时加设备；不支持的需重建容器）【待实机】。
- 挂载后容器内路径与宿主机一致，厂商 venv 的 shebang/activate 脚本无需任何改动。

### 2.2 容器内运行示例/抓球（统一入口）

```bash
# 厂商示例（容器内，复用 xgovenv）
docker exec ros-noetic /home/pi/RaspberryPi-CM5/xgovenv/bin/python \
  /home/pi/RaspberryPi-CM5/robots/Mini3W_W/demos/follow_line.py

# 抓球（容器内）
docker exec ros-noetic /home/pi/RaspberryPi-CM5/xgovenv/bin/python \
  /home/pi/oumax-xgo/ball_grab_release.py --enable-motion
```

封装为仓库内脚本（随各包 host/ 提供）：
- `robot_dog_ball_grab/host/run_ball_in_docker.sh`：抓球一键容器内运行（含手控服务停/恢复可选参数）。
- demos 包 host 脚本：`run_demo_in_docker.sh <demo名>` 通用封装【待 demos 包完成后补】。

### 2.3 依赖与硬件检查清单（容器内【待实机】）

| 项 | 检查命令（容器内） | 备注 |
| --- | --- | --- |
| venv 可用 | `/home/pi/RaspberryPi-CM5/xgovenv/bin/python -c "import uiutils, xgolib"` | bind mount 同路径后应直接可用 |
| 相机 | `python -c "from picamera2 import Picamera2"` + 实拍一帧 | 需 video0 直通 |
| 串口 | `ls -l /dev/ttyAMA0` | 需 ttyAMA0 直通；容器内访问前须停宿主机 oumax-manual 服务 |
| OpenCV/onnxruntime | `python -c "import cv2, onnxruntime"` | xgovenv 自带 |
| 屏幕 | xgoscreen.LCD_2inch（SPI） | 若 /dev/spidev 未直通，示例可能显示失败——评估是否可容忍/禁用显示分支 |

### 2.4 主流程改造（已实施，2026-08-17 实机落地为双容器形态）

原方案设想"球程序与导航同一 focal 容器"，实机验证发现**不可行**：导航容器
`ros-noetic` 基于 Ubuntu Focal，宿主机 xgovenv 是 Python 3.11 + libcamera 0.3
（Raspberry Pi OS Bookworm 基线），Focal 内无对应 Python/libcamera，且 libcamera
相机枚举依赖 udevd（/run/udev/data 数据库）。最终落地为**双容器**：

- **导航容器 `ros-noetic`**（focal，重建补 `-v /home/pi` 与 `--device /dev/ttyAMA0`）：
  跑 ROS 导航 + `main_flow.py`。
- **球容器 `ros-noetic-ball`**（debian:bookworm-slim，与宿主机同基线）：跑球程序
  （ball_yolo_grab / ball_release / rotate / ball_grab_release）。环境由
  `robot_dog_ball_grab/host/setup_ball_container.sh` 配置：容器内 ballenv（pip 装
  numpy/opencv/onnxruntime 对齐宿主版本）+ `.pth` 兜底宿主 dist-packages 与
  xgovenv site-packages + `LD_LIBRARY_PATH` 兜底宿主系统库 + 挂载 libcamera IPA /
  libpisp / libcamera tuning 数据 + `-v /dev:/dev` + `--privileged` + 容器内跑
  udevd + `RPI_LGPIO_REVISION` 环境变量绕过 rpi-lgpio 检测。
- **触发链**：`main_flow.py`（导航容器内）导航完成后 → ssh 宿主机停
  oumax-camera/oumax-manual（释放相机与串口）→ ssh 宿主机
  `docker exec ros-noetic-ball run_ball_in_container.sh --enable-motion`。
  参数 `--grab-release-container`/`--grab-release-runner` 可覆盖容器与入口。

实机验证（2026-08-17）：球容器内 xgolib 串口固件识别（xgomini）、SPI 屏初始化、
cv2/numpy/onnxruntime import、Picamera2 实拍（480×640×3）全部通过。
主流程全链路（导航 5 点 + 容器内抓球放球）实机待跑。

## 3. 备选方案（若设备直通受阻）

- **方案 B：仅容器内 pip 安装依赖**：容器内 `pip install opencv-python-headless onnxruntime` + 复制 uiutils/xgolib 源码进容器。缺点：picamera2 在 Ubuntu Focal（ros-noetic 镜像）上无官方 wheel（需编译 libcamera），xgoscreen 依赖 SPI 屏，风险高、收益低，不推荐。
- **方案 C：宿主机不动、只统一入口脚本**：维持宿主机运行，仅把启动方式收敛到 docker exec 包装脚本（容器只做入口转发）。无法满足"统一环境"目标，仅作过渡。

## 4. 实施步骤（机器上线后按序执行）

1. 【待实机】机器开机，先执行 `restore_mode.py` 恢复狗默认腿模式（08-16 遗留第一优先项）。
2. 【待实机】确认/重建容器挂载与设备直通（§2.1），容器内跑 §2.3 全检查项。
3. 【待实机】容器内试跑 1~2 个厂商示例（follow_line、color）验证串口+相机链路。
4. 【待实机】容器内试跑抓球编排（`run_ball_in_docker.sh`），对比宿主机行为无差异。
5. 【待实机】改造 main_flow 抓球触发方式（§2.4），重跑主流程全链路。
6. 更新 CHANGE_LOG / lingo / 各包 README 的运行说明。

## 5. 相关文件

- 本方案：`docs/technical/2026-08-16-docker-runtime-unification.md`
- 抓球容器化封装：`robot-src/catkin_ws/src/robot_dog_ball_grab/host/run_ball_in_docker.sh`（实施时随本方案交付）
- 部署形态参考：`docs/technical/2026-08-16-main-flow-debug.md` §1/§5、`robot_dog_teleop/host/launch_*.sh`（handover + docker exec 模式）
