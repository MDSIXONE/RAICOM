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

## 主流程（定点巡航 → 抓球放球）

`scripts/main_flow.py` 是上电后的全自动主流程：以当前位姿为起点（默认从
`map → base_link` 读取，可用 `--start-x/--start-y/--start-yaw` 覆盖），依次向
`/move_base` 发送 5 个带朝向的目标点，全部到达后运行抓球放球一键编排
`ball_grab_release.py`（抓球 → 掉头 180° → 放球）。

相对路径（以起点为原点、初始朝向为 0 基准，x 前 y 左，右转 yaw 为负）：

| 点 | 位置 | 朝向 |
| --- | --- | --- |
| P1 | 前方 2.3 m（`--forward-m`） | 初始右转 90°（`--turn-deg`） |
| P2 | 初始朝向右方 0.5 m | 与初始相差 180° |
| P3 | 右方累计 2.15 m（再 1.65 m） | 与初始相差 180° |
| P4 | 左方 0.575 m（自 P3 回撤，右方累计 1.575 m） | 与初始相差 180° |
| P5 | 沿 P4 朝向前进 1 m（`--final-forward-m`） | 与 P1 相同（右转 90°） |

距离参数（`--side-distances`，逗号分隔，正值=右方、负值=左方）均为实测标定值，
实机验证时可按场地调整；若某段方向相反，把对应参数取负即可。

运行（机器端 ROS 容器内，ROS master 在机器本机 127.0.0.1）：

```bash
rosrun robot_dog_navigation main_flow.py --enable-motion --grab-release-ssh pi@127.0.0.1
```

- 前置：`robot_dog_main.launch` 已用 AMCL 定点模式启动（`use_amcl:=true
  map_file:=ricam_arena_mapped.yaml init_x:=0.0 init_y:=0.0 init_yaw:=0.0`），
  起点与地图原点对齐摆放。
- 局部规划器切换（对比验证用）：`local_planner:=dwa` 使用标准
  `dwa_local_planner/DWAPlannerROS`（参数 `config/dwa_planner.yaml`），默认
  `local_planner:=cym` 为自定义 CymPlanner；全局规划器始终为
  `global_planner/GlobalPlanner`。
- 不带 `--enable-motion` 时 move_base 照常导航，但最后的抓球放球程序不运动
  （与 `ball_grab_release.py` 的门禁一致）。
- 抓球放球编排默认解析同工作区 catkin 包
  `robot_dog_ball_grab/scripts/ball_grab_release.py`，也可用
  `--grab-release-script` 显式指定。

**机器端一键执行（推荐，master 跑在机器上）**：导航在容器 `ros-noetic` 内、
球编排在球容器 `ros-noetic-ball` 内执行（程序均不走宿主机）；导航完成后经 ssh
到宿主机停 `oumax-camera`/`oumax-manual` 释放相机与串口，再经 ssh 在宿主机
`docker exec` 进球容器运行 catkin 包球编排。仓库提供等价一键脚本：

```bash
# 机器终端（或 ssh）：
bash robot-src/catkin_ws/src/robot_dog_navigation/host/run_main_flow_in_docker.sh
# 或机器端既有脚本（重新部署 main_flow.py 后行为一致）：
bash /home/pi/run_main_flow.sh
```

一键脚本调用的参数：`--enable-motion --grab-release-ssh pi@127.0.0.1
--side-distances 0.5,0.25,-0.575`（右侧距离已按实机地图已知区 y≥-0.75 临时收缩；
地图补扫右下角后恢复 `0.5,1.65,-0.575`）。`--grab-release-ssh` 模式会先
`ssh <host> sudo systemctl stop oumax-camera.service oumax-manual.service` 释放相机
与串口，再 `ssh <host> docker exec ros-noetic-ball
/root/catkin_ws/src/robot_dog_ball_grab/host/run_ball_in_container.sh --enable-motion`
在球容器内跑球编排（容器名/入口可用 `--grab-release-container`/
`--grab-release-runner` 覆盖；球容器环境由
`robot_dog_ball_grab/host/setup_ball_container.sh` 配置，详见该包 README）。
