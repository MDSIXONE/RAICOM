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
rostopic list | grep -E '^/(map|scan|lidar_points|move_base/global_costmap/costmap)$'
```

应看到 `/map`、`/scan`、`/lidar_points` 和
`/move_base/global_costmap/costmap`。

## 4. 在 RViz 中定点并查看路线

1. 确认左侧 Displays 中 **Static Map**、**Global Costmap**、**Lidar Point Cloud**、
   **Robot Body (0.27m x 0.16m)** 和 **Global Plan** 都已勾选。蓝色矩形仅代表
   长 0.27 m、宽 0.16 m 的机器狗视觉替身。
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
