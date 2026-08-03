# RICAM 仿真快速启动

本文档适用于 WSL `Ubuntu-20.04` 的 `car` 用户，独立工作空间为：

```text
/home/car/ricam_sim_ws
```

该工作空间与 `smartcar2026-simulation` 相互独立，不要在参考工程中构建或启动本仿真。

## 1. 日常启动

在 PowerShell 中进入指定 WSL：

```powershell
wsl.exe -d Ubuntu-20.04 -u car
```

然后在 WSL 终端完整执行：

```bash
source /opt/ros/noetic/setup.bash
source /home/car/ricam_sim_ws/devel/setup.bash

unset LIBGL_ALWAYS_SOFTWARE
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA

roslaunch ricam_arena_sim simulation.launch \
  gui:=true \
  rviz:=true \
  navigation:=true
```

正常结果：

- Gazebo 和 RViz 各打开一个窗口。
- Mini2 机器狗位于起点 `(-1.30, 1.00)`，头部沿世界坐标 `+X` 水平向右。
- RViz 的 Displays 面板启用 `Arena Map`、`Global Costmap` 和 `Local Costmap`。
- `move_base` 默认加载 `cym_planner/CymPlanner`，RViz 同时启用 CymPlanner 激光点和轨迹调试图层。
- 全局代价地图覆盖 3.0 m × 2.5 m 场地；局部代价地图为 2 m × 2 m 滚动窗口。
- Gazebo 目标实时因子约为 `0.3`。

不要发送 `2D Nav Goal`，车会保持在起点；发送目标后 `move_base` 会通过 `/cmd_vel` 驱动车辆。

## 2. 首次使用或源码更新后构建

仅在第一次使用，或 Windows 项目文件已同步到 WSL 工作空间后执行：

```bash
source /opt/ros/noetic/setup.bash
cd /home/car/ricam_sim_ws
catkin_make
source /home/car/ricam_sim_ws/devel/setup.bash
```

运行包级测试：

```bash
cd /home/car/ricam_sim_ws
catkin_make run_tests_ricam_arena_sim
catkin_make run_tests_mini2_description
catkin_make run_tests_cym_planner
catkin_test_results /home/car/ricam_sim_ws/build/test_results/ricam_arena_sim
catkin_test_results /home/car/ricam_sim_ws/build/test_results/mini2_description
catkin_test_results /home/car/ricam_sim_ws/build/test_results/cym_planner
```

预期 `ricam_arena_sim`、`mini2_description` 和 `cym_planner` 均汇总为 `0 errors, 0 failures`；`mini2_description` 的静态测试会验证原始模型未被改写、仿真模型根节点可移动、关节固定、碰撞简化和传感器接口。嵌套 gtest XML 在部分 catkin 版本中会把套件与用例重复计数，因此不要只按汇总测试数判断。

## 3. 快速检查

另开一个 `car` 用户的 WSL 终端，并加载环境：

```bash
source /opt/ros/noetic/setup.bash
source /home/car/ricam_sim_ws/devel/setup.bash
```

检查核心节点：

```bash
rosnode list | grep -E '^/(gazebo|gazebo_gui|move_base|rviz)$'
```

检查 Gazebo 已加载 Mini2 而不是旧车模：

```bash
gz model --list | grep -E '^(mini2|car3)$'
```

应只输出 `mini2`。

检查全局和局部代价地图：

```bash
rostopic type /move_base/global_costmap/costmap
rostopic type /move_base/local_costmap/costmap
```

两条命令都应返回：

```text
nav_msgs/OccupancyGrid
```

检查 CymPlanner 已被 move_base 加载：

```bash
rosparam get /move_base/base_local_planner
rostopic type /move_base/CymPlanner/laser_points
```

应分别返回 `cym_planner/CymPlanner` 和 `sensor_msgs/PointCloud2`。

检查机器狗导航与感知接口：

```bash
rostopic type /odom
rostopic type /scan
rostopic type /camera/rgb/image_raw
rostopic type /imu
rosrun tf tf_echo base_footprint base_link
```

当前 Mini2 使用 kinematic 固定站姿和平面运动代理进行地图/导航验证，四条腿不会执行真实步态，墙体接触也不会产生真实翻滚动力学。这是随包模型缺少执行器、步态控制器和可信动力学参数时的安全仿真配置。

检查激光和相机不是只看到机器狗自身外壳：

```bash
rosrun mini2_description check_mini2_sensors.py
```

命令应返回成功；激光中位距离应大于 0.10 m、近距离回波比例低于 25%，相机画面对比度应大于 5 且包含足够多的颜色层次。仅有话题类型并不能证明传感器安装位置有效。

检查硬件渲染：

```bash
grep -m1 GL_RENDERER ~/.gazebo/ogre.log
```

RTX 4060 环境应包含：

```text
D3D12 (NVIDIA GeForce RTX 4060)
```

如果显示 `llvmpipe`，说明正在使用软件渲染；停止仿真后，重新执行第 1 节的三个图形环境设置再启动。

检查实时因子：

```bash
gz stats -p
```

第一列应稳定在约 `0.30`，按 `Ctrl+C` 结束检查命令。

## 4. 停止仿真

在运行 `roslaunch` 的终端按：

```text
Ctrl+C
```

等待 Gazebo、RViz 和 `move_base` 正常退出。随后可检查是否仍有相关进程：

```bash
pgrep -af 'roslaunch ricam_arena_sim simulation.launch|gzserver|gzclient|rviz'
```

正常情况下不应输出仿真进程。若窗口已经关闭但 ROS 节点仍残留，可执行：

```bash
rosnode kill /rviz /move_base /gazebo_gui /gazebo
```

## 5. 常用启动变体

只启动 Gazebo，不打开 RViz：

```bash
roslaunch ricam_arena_sim simulation.launch rviz:=false navigation:=true
```

不启动导航代价地图：

```bash
roslaunch ricam_arena_sim simulation.launch navigation:=false
```

无界面启动，用于自动测试：

```bash
roslaunch ricam_arena_sim simulation.launch gui:=false rviz:=false navigation:=true
```

显式选择 CymPlanner 的参考兼容模式（也是默认值）：

```bash
roslaunch ricam_arena_sim simulation.launch \
  local_planner:=cym_planner/CymPlanner \
  cym_navigation_mode:=main_legacy
```

临时回退到 DWA，不改配置文件：

```bash
roslaunch ricam_arena_sim simulation.launch \
  local_planner:=dwa_local_planner/DWAPlannerROS
```

不要再同时启动参考工程 `cym_planner` 附带的整套导航 launch；本仿真已经提供唯一的 `map_server`、`map -> odom`、`move_base` 和两张 costmap，重复启动会造成节点、TF 与 `/cmd_vel` 冲突。

在仿真已经运行时，另开一个 `car` 用户 WSL 终端执行默认编号路线 `91 → 711 → 694`：

```bash
source /opt/ros/noetic/setup.bash
source /home/car/ricam_sim_ws/devel/setup.bash
roslaunch ricam_arena_sim numbered_waypoint_route.launch
```

航点任务会先确认 `navfn/NavfnROS + cym_planner/CymPlanner`，再预规划并顺序执行。主点仍为 `91 → 711 → 694`，实际安全路径为 `91 → 400 → 392 → 640 → 711 → 741 → 708 → 702 → 694`：前半段绕开下方识别箱东侧窄通道，后半段避开底墙膨胀区。除最终点外均按位置容差连续通过；普通引导点为 0.06 m，Mini2 在墙角转身点 741 单独使用 0.11 m。最终 694 必须由 move_base action 完整成功；任一段规划失败、控制失败或超时都会终止任务。RViz 的 `Numbered Waypoint Route` 图层会显示蓝色主点、橙色引导点和完整路线。
