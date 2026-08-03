# WSL 仿真工作区

此目录是独立的 ROS Noetic Catkin 工作区，包含 Gazebo、RViz、导航和图像采集所需的功能包：

- `ricam_arena_sim`：赛场 world、运行时地图、Gazebo/RViz 启动文件与代价地图配置。
- `mini2_description`：Mini Pupper/机器狗仿真模型。
- `cym_planner`：CymPlanner 局部规划器。
- `ricam_dataset_capture`：每 0.5 秒一次、最多 600 张的采集功能包。

## WSL 启动

```bash
cd ~/RAICOM/wsl-simulation
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
roslaunch ricam_arena_sim simulation.launch
```

默认会启动 Gazebo、RViz、地图服务器和 `move_base`。机器人初始朝向为水平向右（`start_yaw:=0.0`）。如需关闭导航或 RViz，可在启动时传入 `navigation:=false` 或 `rviz:=false`。

## 地图资产

`ricam_arena_sim` 中保留了一份运行时导出的 world、网格和导航地图，以便此工作区在 WSL 中单独克隆、构建与启动。可编辑的 Blender 原文件、地图归档和顶点编号数据统一位于仓库根目录的 `blender-maps/ricam_arena/`。

## 本地离线 RViz 定点规划

仓库根目录的 `catkin_ws/src/robot_dog_navigation` 是另一套轻量离线演示，使用模拟雷达、
地图和官方 `global_planner/GlobalPlanner`。它固定使用回环地址
`http://127.0.0.1:11311`，不连接机器狗，也没有 `/cmd_vel` 硬件订阅者。

不要将本节与上面的 `simulation.launch` 混用：后者会启动 Gazebo 完整仿真；仅需 RViz
看路线时，在仓库根目录执行：

```bash
bash wsl-simulation/start_local_rosmaster.sh
# 另开一个 WSL 终端：
bash wsl-simulation/start_offline_navigation.sh
```

完整人工操作步骤见 [`docs/local-rviz-navigation-quickstart.md`](../docs/local-rviz-navigation-quickstart.md)。
