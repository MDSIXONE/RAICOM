# 本地 RViz 定点导航快速启动手册

本手册用于在 **本机 WSL** 中打开机器狗导航可视化：在 RViz 里设置目标点并查看
全局路径。离线模式的地图、雷达点云和代价地图均为本地模拟数据；实机模式连接机器狗
ROS Master 以显示实时雷达，二者都不会发送底盘速度指令。

## 1. 安全边界

启动前确认下面三点：

- 仅使用本机 WSL 的 `http://127.0.0.1:11311`。
- 不启动 `robot_dog_lidar`，不打开串口，不运行任何底盘控制节点。
- 即使设置了目标点，`/cmd_vel` 也没有硬件订阅者；它只会在本地生成规划结果。

不要在本手册的终端中设置远程 `ROS_MASTER_URI`。

## 2. 从零启动

打开第一个 WSL 终端，启动本地 ROS Master：

```bash
wsl -d Ubuntu-20.04
cd /mnt/d/WORK/ALLCODE/RAICOM
bash wsl-simulation/start_local_rosmaster.sh
```

看到 `Starting local-only ROS Master` 后保持此终端运行。

打开第二个 WSL 终端，构建并启动离线导航与 RViz：

```bash
wsl -d Ubuntu-20.04
cd /mnt/d/WORK/ALLCODE/RAICOM
bash wsl-simulation/start_offline_navigation.sh
```

首次启动会把构建产物放到 WSL 的 `~/raicom_ws`，源码仍保留在当前仓库。第二个命令
默认会打开 RViz；如果第一个终端已经有本地 Master，它不会另起一个。

## 3. 当前已经运行时

若 RViz、`/map` 和 `/move_base` 已由当前会话启动，不要重复运行 Master。直接在 RViz
中设置目标即可。可在任意 WSL 终端检查状态：

```bash
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://127.0.0.1:11311
export ROS_IP=127.0.0.1
rostopic list | grep -E '^/(map|scan|scan_filtered|lidar_points|move_base/(global|local)_costmap/costmap)$'
```

应看到 `/map`、`/scan`、`/scan_filtered`、`/lidar_points`、
`/move_base/global_costmap/costmap` 和 `/move_base/local_costmap/costmap`。
`/scan_filtered` 由 `scan_circle_filter` 生成，是局部代价地图的数据源。

## 4. 在 RViz 中定点并查看路线

1. 确认左侧 Displays 中 **Static Map**、**Global Costmap**、**Local Costmap (1m x 1m)**、
   **Lidar Point Cloud**、**Robot Body (0.27m x 0.16m)** 和 **Global Plan** 都已勾选。
   蓝色矩形仅代表长 0.27 m、宽 0.16 m 的机器狗视觉替身；局部代价地图显示的是
   以机器人为中心的 1 m × 1 m 滚动窗口，障碍物来自 `/scan_filtered`。
2. 确认 RViz 顶部的 Fixed Frame 是 `map`。
3. 点击工具栏的 **2D Nav Goal**。
4. 在最新版 RICAM 赛场地图的浅色可通行区域按住鼠标左键拖动：按下位置是目标点，拖动方向是目标朝向。当前离线起点为 `(-0.70, 1.00)`，这是为 0.27 m × 0.16 m 的矩形替身选择的安全位置。
5. 松开鼠标后，等待约一秒。蓝色线条会显示在 **Global Plan** 中；它就是官方
   `global_planner/GlobalPlanner` 计算的全局路线。

可在终端确认已经收到路线：

```bash
rostopic echo -n 1 /move_base/GlobalPlanner/plan
```

## 5. 常见问题

| 现象 | 处理方式 |
| --- | --- |
| RViz 没有窗口 | 在 WSL 中执行 `echo $DISPLAY`；正常应有值。关闭当前导航终端后重新执行启动命令。 |
| 提示已有 ROS Master | 不要重复启动 `start_local_rosmaster.sh`；保留原 Master，直接启动导航脚本。 |
| 没有地图或点云 | 在第二个终端按 `Ctrl+C` 后，重新运行 `bash wsl-simulation/setup_offline_navigation.sh`，再启动导航。 |
| 目标点没有蓝色路线 | 将目标放在白色可通行区域，避开黑色墙体和代价地图的障碍区；然后检查 `/move_base/GlobalPlanner/plan`。 |
| 担心机器狗会动 | 本演示不连接机器狗网络，且 `/cmd_vel` 没有订阅者。执行 `rostopic info /cmd_vel` 应显示 `Subscribers: None`。 |

## 6. 停止

先在第二个终端按 `Ctrl+C`，关闭导航节点和 RViz；再在第一个终端按 `Ctrl+C`，停止本地
Master。两者只影响本机 WSL，不会停止或修改机器狗容器。

## 7. 实机键盘建图（gmapping）

建图需要实机（192.168.137.157）、WSL 本地 master 与 rviz 同时在线。

### 7.1 准备

1. 实机通电，确认 `oumax-manual.service` 为 active（断电后需手动
   `sudo -n systemctl start oumax-manual.service`），`/health` 与 `/imu` 正常。
2. 确认 WSL 当前 IP（`ip addr` 找 192.168.137.x，会变），master 由
   `wsl-simulation/start_local_control.sh` 拉起（内含 `ROS_MASTER_URI` 与 `ROS_IP`）。
3. 启动实机主流程（建图模式，机器起点对齐地图原点 0,0）：

```bash
docker exec -d ros-noetic bash -lc "source /opt/ros/noetic/setup.bash; source /root/catkin_ws/devel/setup.bash; export ROS_MASTER_URI=http://<WSL_IP>:11311; export ROS_IP=192.168.137.157; roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true enable_mapping:=true init_x:=0.0 init_y:=0.0 > /tmp/main_launch.log 2>&1"
```

确认 `/slam_gmapping`、`/laser_frame_tf` 在线，`/map` 有首图（latching 重放正常）。

### 7.2 键盘控制建图

在实机容器内交互终端逐行执行（**不要批量粘贴**，批量粘贴会导致 rosrun 提前退出）：

```bash
docker exec -it ros-noetic bash
source /opt/ros/noetic/setup.bash
source /root/catkin_ws/devel/setup.bash
export ROS_MASTER_URI=http://<WSL_IP>:11311
export ROS_IP=192.168.137.157
rosrun robot_dog_teleop mapping_keyboard_teleop.py
```

按住 `w/s` 前后、`a/d` 转向（松开 0.25s 自动停），`q` 退出。期间在 rviz 中观察
`/map` 实时增长（建图必须移动机器，gmapping 运动阈值才触发 scan 处理）。

### 7.3 保存地图

建图满意后退出键盘节点，在容器内执行（`map_saver` 属于 map_server 包）：

```bash
rosrun map_server map_saver -f /root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped
```

把生成的 `ricam_arena_mapped.pgm/yaml` 同步回仓库
`catkin_ws/src/robot_dog_navigation/maps/` 并提交。

### 7.4 切回导航模式

```bash
docker exec ros-noetic bash -lc "pkill -f 'roslaunch[ ]robot_dog_main' 2>/dev/null; sleep 2"
docker exec -d ros-noetic bash -lc "source /opt/ros/noetic/setup.bash; source /root/catkin_ws/devel/setup.bash; export ROS_MASTER_URI=http://<WSL_IP>:11311; export ROS_IP=192.168.137.157; roslaunch robot_dog_bringup robot_dog_main.launch enable_motion:=true map_file:=/root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.yaml > /tmp/main_launch.log 2>&1"
```

导航模式加载 `ricam_arena_mapped`，`/slam_gmapping` 消失、`/map_server` 与
`/move_base` 恢复；此时在 rviz 用 2D Nav Goal 选点即进入 cym_planner 导航。
注意：导航模式的 `init_x/init_y` 默认 (-0.70, 1.00)，若机器起点与建图原点不一致，
用 `init_x:=0.0 init_y:=0.0` 等参数对齐。

## 8. 定点导航的激光定位（jie_ware lidar_loc）

导航模式下，`map -> odom` 变换由第三方包 `jie_ware` 的 `lidar_loc` 节点发布
（源码位于 `catkin_ws/src/jie_ware`，来自 https://github.com/6-robot/jie_ware，
GPL-2.0 许可，与仓库其余包的 BSD-3-Clause 分开管理）：

1. `lidar_loc` 订阅 `/map` 与 `/scan_filtered`，把激光点与地图障碍物做逐帧扫描匹配，
   解出机器人在 `map` 系下的位姿，再结合 `simple_odom` 的 `odom -> base_link`
   里程计推算，发布带修正的 `map -> odom` TF。
2. 启动时由 `initial_pose_publisher` 在 `/map` 到达后自动发布 `/initialpose`
   （初始位姿取 `init_x/init_y`，默认 -0.70, 1.00）；也可在 rviz 用 **2D Pose Estimate**
   手动修正。收到初始位姿约 30 帧激光后，`lidar_loc` 会自动调用
   `move_base/clear_costmaps` 清掉启动期的陈旧障碍。
3. **约束**：`lidar_loc` 收到 `/map` 时会先把估计重置到地图原点，因此不要单独
   重启 `lidar_loc`，必须连同 `initial_pose_publisher` 一起重启，否则会一直卡在原点。
4. 编译 `jie_ware` 需要 `cv_bridge` 与 OpenCV（ROS Noetic 默认自带）；机器容器若提示
   缺少依赖，执行 `apt install ros-noetic-cv-bridge` 后重新 `catkin_make`。

本地离线模拟默认使用静态 TF（`use_lidar_loc:=false`），因为模拟激光是通用房间
数据、与 RICAM 地图不匹配，定位会发散；若要验证 `lidar_loc` 节点与 TF 链路本身，
可追加参数：

```bash
bash wsl-simulation/start_offline_navigation.sh use_lidar_loc:=true
```

此时 rviz 里机器人会随着错误匹配漂移，属正常现象（仅链路验证）。
