# robot_dog_navigation

本包同时提供本机 WSL 离线演示和实机只读可视化。两种模式都使用 ROS Noetic
官方 `move_base` 和 `global_planner/GlobalPlanner`；局部规划器使用
`cym_planner/CymPlanner`（独立发布包 `cym_planner_standalone_20260713` 的源码，
位于同工作区 `catkin_ws/src/cym_planner`，参数由
`cym_planner/config/cym_planner_params.json` 加载）。

通过仓库根目录的 `wsl-simulation/setup_offline_navigation.sh` 构建，然后执行：

```bash
bash /mnt/d/WORK/ALLCODE/RAICOM/wsl-simulation/start_offline_navigation.sh
```

启动脚本固定使用 `http://127.0.0.1:11311`。在 RViz 中选择 **2D Nav Goal**
并在浅色静态地图的可通行区域点击，即可看到全局路径和全局代价地图；没有节点会
接收或执行 `/cmd_vel`。

离线话题：

- `/map`：最新版 RICAM 仿真导出的 3.0 m × 2.5 m 静态占据栅格地图。
- `/scan`、`/lidar_points`：模拟的 `laser_frame` 雷达数据。
- `/robot_body_marker`：跟随 `base_link` 的蓝色矩形替身，长 0.27 m、宽 0.16 m。
- `/move_base/global_costmap/costmap`：官方 `costmap_2d` 发布的全局代价地图。
- `/move_base/local_costmap/costmap`：1 m × 1 m 滚动局部代价地图。
- `/move_base/GlobalPlanner/plan`：收到目标点后由官方全局规划器发布的路径。
- `/cym_planner/map_image`：CymPlanner 发布的局部代价地图与路径叠加图。
- `/cym_planner/plan_image`：CymPlanner 发布的车体系路径俯视图。

默认初始位姿为 RICAM 地图中适合 0.27 m × 0.16 m 矩形替身的安全位置：`map` 坐标
`(-0.70, 1.00, 0 rad)`；默认地图
`maps/ricam_arena.pgm` 与 `wsl-simulation/src/ricam_arena_sim/maps/ricam_arena.pgm`
的 SHA-256 摘要必须一致。

## 实机只读可视化

机器狗容器使用 `robot_visualization.launch`：它加载同一张地图、发布固定起点和
矩形替身，启动只读 YDLIDAR `/scan`，并把每帧扫描转换为实时
`/lidar_points`。全局代价地图只使用静态赛场地图；局部代价地图独立使用 1 m ×
1 m 的实时扫描窗口。二者膨胀半径均为 0.10 m。

`move_base` 的 `cmd_vel` 被强制重映射到
`/robot_dog_navigation/disabled_cmd_vel`，因此本 launch 不会把任何速度消息送往
底盘。完成机器端部署后，在本机 WSL 使用：

```bash
bash wsl-simulation/start_robot_rviz.sh
```

该脚本只打开本机 RViz，并将 ROS 回连地址固定为当前 WSL 局域网地址
`192.168.137.139`；如地址改变，可通过 `RAICOM_WSL_IP` 覆盖。
