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

**前置**：场地铺好黑线；脚本已部署（首次执行下面的 scp）；容器 `ros-noetic` 运行中
（雷达桥 docker exec 依赖）。

```bash
# 部署（首次，宿主机）
scp robot-src/catkin_ws/src/robot_dog_follow_line/scripts/follow_line.py \
    robot-src/catkin_ws/src/robot_dog_follow_line/host/run_main_flow2.sh \
    robot-src/catkin_ws/src/robot_dog_follow_line/host/run_lidar_rear_bridge.sh \
    robot-src/catkin_ws/src/robot_dog_follow_line/host/lidar_rear_bridge_inner.sh \
    pi@192.168.137.157:/home/pi/oumax-xgo/

# 运行（机器端，由用户手动执行；AI 不得自动启动）——一条指令即可
bash /home/pi/oumax-xgo/run_main_flow2.sh
```

- 脚本自动：停 `raicom-original-main` + `oumax-camera` → **自动拉起雷达后方桥**
  （`run_lidar_rear_bridge.sh`：容器内 roscore+雷达+HTTP :8767，输出 bridge-ok 与
  rear_m）→ 前台跑 `follow_line.py`（带雷达后方第一个右转定位）；退出后不自动恢复服务。
- 雷达桥失败（容器未起等）→ 脚本中止（full exposure，不静默降级）。
- 覆盖环境变量：`RAICOM_XGO_PYTHON`（解释器，默认 `/home/pi/RaspberryPi-CM5/xgovenv/bin/python`）、
  `RAICOM_FOLLOW_LINE`（巡线脚本路径）、`RAICOM_REAR_BRIDGE`（雷达桥脚本路径，默认
  `/home/pi/oumax-xgo/run_lidar_rear_bridge.sh`）。

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
# 1) 先起雷达后方距离桥（容器内 /scan + HTTP :8767）
bash /home/pi/oumax-xgo/run_lidar_rear_bridge.sh
curl -s http://127.0.0.1:8767/rear   # 应有 rear_m

# 2) 运行巡线（机器端，用户手动执行；须宿主机 xgovenv）
/home/pi/RaspberryPi-CM5/xgovenv/bin/python /home/pi/oumax-xgo/follow_line.py
```

- 推流：`http://192.168.137.157:8090/`（带框原画面，含水印 `lw/raw/阈值`）、`:8091/`（阈值画面，同线宽）。
- 终端每 0.3s：`[线宽] …`；另有 `[雷达后方] rear=…m dip_done=… step=0/2 next_at=0.75m`。
- **弯道右转（默认）= 雷达后方第一个右转定位**：正后扇区中位距离**曾见 > 2.0 m
  后首次 < 1.0 m** → 判定第一个右转、开启功能；此后 rear **依次增大到 ≥ 0.75 m、
  ≥ 1.5 m** 各执行一次 IMU yaw 闭环 **右转 90° → 停 2 s → 左转 90° 回正 → 继续巡线**。
  **第1次触发前要求相对阶段1时刻 yaw 已转过 ≥ 80°**（`rear_yaw_min_deg`，防刚转角就
  触发；日志 `[雷达后方] 等 yaw`/`yaw 验证通过`）。参数
  （`rear_dip_from_m`/`rear_dip_to_m`/`rear_turn_at_steps_m`/`rear_yaw_min_deg`/`rear_turn_deg`/`rear_hold_s`）
  写入 follow_line_config.json 可调；线宽突变默认关闭。
- 按键：`p/o` P±1、`R/F` P±50、`i/u` D±0.1、`[`/`]` 直行速度±1、`-`/`=` 转向速度±1、`t` 转向方向、`m` 轮式/足式、`Q` 保存日志、B 键（板载）退出、Ctrl-C 退出。
- 板载按钮：A 巡线 / C color / D init / B 退出。

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
# 前置（宿主机）：切换串口服务（imu_bridge 需要 8765；raicom-original-main 会顶掉手动服务）
sudo systemctl stop raicom-original-main.service
sudo systemctl start oumax-manual-control.service
curl http://127.0.0.1:8765/health   # 确认 {"ok": true}

# 建图模式 - gmapping（odom_mode 默认 cmd_vel → slam_gmapping，遥控建图）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true \
        enable_mapping:=true local_master_ip:=192.168.137.157 \
        init_x:=0.0 init_y:=0.0 > /tmp/main_launch.log 2>&1"

# 建图模式 - Cartographer 纯激光（enable_mapping:=true odom_mode:=carto，从零建图）
# 节点集：cartographer_node + imu_bridge + carto_odom + 雷达 + 滤波 + TF + cmd_vel 桥，
# 无 map_server/lidar_loc/move_base（纯建图，不加载默认地图）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && roslaunch robot_dog_bringup robot_dog_main.launch enable_mapping:=true \
        odom_mode:=carto enable_motion:=true local_master_ip:=192.168.137.157 \
        init_x:=0.0 init_y:=0.0 init_yaw:=0.0 > /tmp/carto_map.log 2>&1"
# cartographer_node 默认不发布 /map 栅格，需另启 occupancy_grid_node 拼子图供 RViz 显示：
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && rosrun cartographer_ros cartographer_occupancy_grid_node \
        -resolution 0.05 -publish_period_sec 1.0 > /tmp/occ_grid.log 2>&1"

# 定位模式 - Cartographer（odom_mode:=carto，加载已有地图看定位效果，不运动）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && roslaunch robot_dog_bringup robot_dog_main.launch odom_mode:=carto \
        enable_motion:=false local_master_ip:=192.168.137.157 \
        map_file:=/root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.yaml \
        init_x:=0.0 init_y:=0.0 init_yaw:=0.0 > /tmp/carto_launch.log 2>&1"

# AMCL 定点模式（主流程1 前置；init_x/y/yaw 与出发区摆放对齐）
docker exec -d ros-noetic bash -lc \
  "source /opt/ros/noetic/setup.bash && source /root/catkin_ws/devel/setup.bash \
   && roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true \
        use_amcl:=true local_master_ip:=192.168.137.157 \
        map_file:=/root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.yaml \
        init_x:=0.0 init_y:=0.0 init_yaw:=0.0 > /tmp/main_launch.log 2>&1"

# 保存地图（建图完成后，容器内）
rosrun map_server map_saver -f /root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped

# 清理残留同名节点（多次 roslaunch 后必须清，否则新节点被挤掉）
docker exec ros-noetic bash -lc "pkill -9 -f 'rosl[a]unch|move_b[a]se|amc[l]|lidar_l[o]c|cartograph[e]r|imu_bridg[e]'"
```

- 遥控建图：`docker exec -it ros-noetic bash` 后 `rosrun robot_dog_teleop mapping_keyboard_teleop.py`
  （carto 建图/遥控需 enable_motion:=true，场地净空、急停可达）。
- RViz（WSL 侧连机器 master）：`bash wsl-simulation/start_robot_rviz.sh`（`RAICOM_ROBOT_IP`/`RAICOM_WSL_IP` 可覆盖）。
- 若 RViz 看不到地图：地图色带中空闲为黑色，黑背景上不明显——把 RViz 背景调亮
  （Global Options → Background Color）或增大地图 Alpha；`/map` 数据可用
  `rosrun map_server map_saver -f /tmp/x` 存图后用图片工具确认内容。
- Cartographer 纯激光建图注意事项：
  ①`num_subdivisions_per_laser_scan=1`（config/cartographer_2d.lua）——ydlidar
     scan 无 per-point 时间偏移，>1 会报 subdivision 时间恒等并忽略大部分 scan
     （建图停滞），=0 会让 1.0.0 CHECK 崩溃；②use_imu_data=false（纯雷达，
     固件无原始 accel/gyro）；③/scan_filtered 已由 scan_circle_filter 屏蔽
     近处前方扇区（半径 0.25m、前方 30° 内 1m）。

---

## 6. WSL 仿真（开发调试，无需机器）

```bash
bash wsl-simulation/setup_offline_navigation.sh        # 构建仿真工作区
bash wsl-simulation/start_offline_navigation.sh        # 启动离线导航（use_lidar_loc:=true 可选）
bash wsl-simulation/start_local_rosmaster.sh           # 本地 rosmaster
bash wsl-simulation/verify_offline_navigation.sh       # 验证导航
```

完整流程与排障：`docs/local-rviz-navigation-quickstart.md`。

---

## 7. 轮控诊断（四轮依次转）

**前置**：机器开机、场地净空可随时断电；手控服务占串口（`oumax-manual.service` active，`raicom-original-main` 一般 inactive）；`/health` 正常。

通道顺序：`[左前, 右前, 右后, 左后]`。脚本 10Hz 刷新 wheel 命令，每轮结束与全局结束发零速。**ACK ≠ 实际转动，须现场目视**（左后通道 3 曾持续不转，见 `docs/ai-records/mistakes/2026-08-13.md`、`2026-08-31.md`）。

```bash
# ---------- 机器端（推荐，SSH 登录后）----------
# 首次部署（在开发机仓库根目录执行）
scp tmp/drive_wheels_sequential.py pi@192.168.137.157:/home/pi/oumax-xgo/

# 运行（pi@pi 家目录下不要写 tmp/…，脚本在 oumax-xgo）
python3 /home/pi/oumax-xgo/drive_wheels_sequential.py
# 或
cd /home/pi/oumax-xgo && python3 drive_wheels_sequential.py 7 1.2

# ---------- 开发机（仓库根目录 → 机器 8765）----------
python3 tmp/drive_wheels_sequential.py
python3 tmp/drive_wheels_sequential.py 7 1.2
# 主机覆盖：RAICOM_MANUAL_HOST=192.168.137.157 python3 tmp/drive_wheels_sequential.py

# 仅左后轮（对照/单轮，开发机）
python3 tmp/drive_left_rear_wheel.py 7 1.2

# 健康检查
curl -s http://192.168.137.157:8765/health          # 开发机
curl -s http://127.0.0.1:8765/health                # 机器端
```

- 顺序：左前 → 右前 → 右后 → 左后。
- 脚本按主机名自动选手控地址：机器上 `127.0.0.1`，开发机 `192.168.137.157`（`RAICOM_MANUAL_HOST` 可覆盖）。
- 手控未起时先切换（机器端）：`sudo systemctl stop raicom-original-main.service && sudo systemctl start oumax-manual.service`。
- 单轮扭动机体可能位移，勿依赖四轮差速/同驱（左后可能失效时）。
