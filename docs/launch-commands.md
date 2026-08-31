# 启动命令速查（机器狗实机 + WSL 仿真）

主流程1（定点巡航 + 抓球放球）、主流程2（直接巡线）与各调试程序的启动/部署命令汇总。
命令以"复制即用"为目标；每条给出执行位置（宿主机 / 机器端 / 容器内 / WSL）与关键注意。

权威细节：`docs/lingo.md`（黑话）、`docs/local-rviz-navigation-quickstart.md`（导航联调）、
`docs/technical/2026-08-16-docker-runtime-unification.md`（容器化方案）。

---

## 0. 机器前置

| 项 | 值/命令 |
| --- | --- |
| 机器 IP / SSH | `192.168.137.157`，`ssh pi@192.168.137.157`（密码 `pi`） |
| 手控服务 HTTP | `http://192.168.137.157:8765`（`/health`、`/command`、`/imu`） |
| 导航容器 | `ros-noetic`（ROS Noetic，master 在机器本机 `127.0.0.1:11311`） |
| 球程序容器 | `ros-noetic-ball`（Debian Bookworm + ballenv） |

**服务互斥（跑巡线/球/调参工具前必须先停）：**

```bash
# 停（释放 SPI/串口 + 相机/8090）
sudo systemctl stop raicom-original-main.service oumax-camera.service
# 需要时也停手控服务（占串口）
sudo systemctl stop oumax-manual.service
# 恢复
sudo systemctl start raicom-original-main.service oumax-camera.service
```

---

## 1. 主流程1：定点巡航 5 点 → 抓球放球（一键）

**前置**：① 导航已以 AMCL 定点模式启动（见 §5）；② 球容器已配置（首次见 §4）；③ 机器在出发区与地图原点对齐。

```bash
# 机器端（推荐）：机器上已部署的一键入口
bash /home/pi/run_main_flow.sh

# 或仓库版（宿主机执行，等价）：
bash robot-src/catkin_ws/src/robot_dog_navigation/host/run_main_flow_in_docker.sh
```

- 流程：容器内导航 5 点 → ssh 停 oumax-camera/oumax-manual → 球容器跑 `ball_grab_release.py --enable-motion`。
- 参数：`--side-distances` 当前临时收缩为 `0.5,0.25,-0.575`；地图补扫右下角后恢复 `0.5,1.65,-0.575`。
- 不带 `--enable-motion` 时只导航不抓球。

---

## 2. 主流程2：直接巡线（跳过导航）

**前置**：场地铺好黑线；脚本已部署（首次执行下面的 scp）。

```bash
# 部署（首次，宿主机）
scp robot-src/catkin_ws/src/robot_dog_follow_line/scripts/follow_line.py \
    robot-src/catkin_ws/src/robot_dog_follow_line/host/run_main_flow2.sh \
    pi@192.168.137.157:/home/pi/oumax-xgo/

# 运行（机器端，由用户手动执行；AI 不得自动启动）
bash /home/pi/oumax-xgo/run_main_flow2.sh
```

- 脚本自动停 `raicom-original-main` + `oumax-camera` → 前台跑 `follow_line.py`；退出后不自动恢复服务。
- 覆盖环境变量：`RAICOM_XGO_PYTHON`（解释器，默认 `/home/pi/RaspberryPi-CM5/xgovenv/bin/python`）、`RAICOM_FOLLOW_LINE`（脚本路径）。

---

## 3. 巡线调试

> 跑前一律先停 `raicom-original-main` + `oumax-camera`；`follow_line_config.json` 由调参工具在机器上生成（同目录）。

### 3.1 调参工具 follow_line_tune.py（狗只摆姿态不走）

```bash
# 部署（首次，宿主机）
scp robot-src/catkin_ws/src/robot_dog_follow_line/scripts/follow_line_tune.py \
    pi@192.168.137.157:/home/pi/oumax-xgo/

# 运行（机器端，需 SSH 交互终端）
cd /home/pi/oumax-xgo && ./follow_line_tune.py
```

- 浏览器看画面：`http://192.168.137.157:8090/`。
- 按键：`w/s` V 上限±10、`1/2` V 上限±1、`a/d` V 下限±10、`z/x` 左裁剪±10、`c/v` 右裁剪±10、`q` 保存退出。
- 自动停/恢复 `raicom-original-main` + `oumax-camera`，摆低趴姿态（与巡线视角一致）。

### 3.2 巡线本体 follow_line.py（边走边调）

```bash
# 运行（机器端，用户手动执行；容器未直通 ttyAMA0，须宿主机 xgovenv）
/home/pi/RaspberryPi-CM5/xgovenv/bin/python /home/pi/oumax-xgo/follow_line.py
```

- 推流：`http://192.168.137.157:8090/`（带框原画面）、`:8091/`（阈值画面）。
- 按键：`p/o` P±1、`R/F` P±50、`i/u` D±0.1、`[`/`]` 直行速度±1、`-`/`=` 转向速度±1、`t` 转向方向、`m` 轮式/足式、`Q` 保存日志、B 键（板载）退出、Ctrl-C 退出。
- 板载按钮：A 巡线 / C color / D init / B 退出。
- 弯道右转 90° 为 IMU yaw 闭环（`surge_turn_deg/surge_turn_speed/surge_turn_timeout` 可调）。

---

## 4. 球任务调试（抓球/旋转/放球）

### 4.1 容器配置（首次或容器重建后，宿主机）

```bash
sudo bash robot-src/catkin_ws/src/robot_dog_ball_grab/host/setup_ball_container.sh
```

### 4.2 部署（宿主机）

```bash
scp robot-src/catkin_ws/src/robot_dog_ball_grab/scripts/*.py \
    pi@192.168.137.157:/home/pi/ros_ws/src/robot_dog_ball_grab/scripts/
scp robot-src/catkin_ws/src/robot_dog_ball_grab/host/*.sh \
    pi@192.168.137.157:/home/pi/ros_ws/src/robot_dog_ball_grab/host/
```

### 4.3 一键编排：抓球 → 掉头 180° → 放球

```bash
# 宿主机入口（--release-camera-serial 先停相机/手控服务释放设备；--enable-motion 才真运动）
bash robot-src/catkin_ws/src/robot_dog_ball_grab/host/run_ball_in_docker.sh \
    --release-camera-serial --enable-motion

# 或容器内直接跑
docker exec ros-noetic-ball \
    /root/catkin_ws/src/robot_dog_ball_grab/host/run_ball_in_container.sh --enable-motion
```

### 4.4 单独脚本（容器内 `/root/catkin_ws/src/robot_dog_ball_grab/scripts/`）

```bash
# 抓球（--frames N 检测 N 帧后退出，0=持续）
/opt/ballenv/bin/python ball_yolo_grab.py --enable-motion --frames 30
# 旋转 180°（--turn-speed / --turn-duration 可调）
/opt/ballenv/bin/python rotate.py --enable-motion --turn-duration 9.0
# 放球
/opt/ballenv/bin/python ball_release.py --enable-motion
```

### 4.5 YOLO 检查工具 yolo_view.py（画全部框，不动狗）

```bash
# 机器端（部署后）：默认 letters.onnx 识别 A/B/C/D，8090 推流
scp robot-src/catkin_ws/src/robot_dog_ball_grab/scripts/yolo_view.py \
    pi@192.168.137.157:/home/pi/ros_ws/src/robot_dog_ball_grab/scripts/
ssh pi@192.168.137.157
docker exec ros-noetic-ball /opt/ballenv/bin/python \
    /root/catkin_ws/src/robot_dog_ball_grab/scripts/yolo_view.py
```

---

## 5. 导航调试（容器 ros-noetic 内）

> 以下命令在机器端容器内执行；`docker exec` 交互或 `-d` 后台均可用。`ROS_MASTER_URI` 用机器本机 `127.0.0.1`（若用 WSL 跨机 master 则换成 WSL IP，见 `docs/local-rviz-navigation-quickstart.md`）。

```bash
# 建图模式（enable_mapping:=true，走 mapping_keyboard_teleop 遥控建图）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && export ROS_MASTER_URI=http://127.0.0.1:11311 && export ROS_IP=127.0.0.1 \
   && roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true \
        enable_mapping:=true init_x:=0.0 init_y:=0.0 > /tmp/main_launch.log 2>&1"

# AMCL 定点模式（主流程1 前置；init_x/y/yaw 与出发区摆放对齐）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && export ROS_MASTER_URI=http://127.0.0.1:11311 && export ROS_IP=127.0.0.1 \
   && roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true \
        use_amcl:=true map_file:=/root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.yaml \
        init_x:=0.0 init_y:=0.0 init_yaw:=0.0 > /tmp/main_launch.log 2>&1"

# 保存地图（建图完成后，容器内）
rosrun map_server map_saver -f /root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped

# 清理残留同名节点（多次 roslaunch 后必须清，否则新节点被挤掉）
docker exec ros-noetic bash -lc "pkill -9 -f 'roslaunch|move_base|amcl|lidar_loc'"
```

- 遥控建图：`docker exec -it ros-noetic bash` 后 `rosrun robot_dog_teleop mapping_keyboard_teleop.py`。
- RViz（WSL 侧连机器 master）：`bash wsl-simulation/start_robot_rviz.sh`（`RAICOM_ROBOT_IP`/`RAICOM_WSL_IP` 可覆盖）。

---

## 6. WSL 仿真（开发调试，无需机器）

```bash
bash wsl-simulation/setup_offline_navigation.sh        # 构建仿真工作区
bash wsl-simulation/start_offline_navigation.sh        # 启动离线导航（use_lidar_loc:=true 可选）
bash wsl-simulation/start_local_rosmaster.sh           # 本地 rosmaster
bash wsl-simulation/verify_offline_navigation.sh       # 验证导航
```

完整流程与排障：`docs/local-rviz-navigation-quickstart.md`。
