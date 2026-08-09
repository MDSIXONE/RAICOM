# cym_planner

ROS 1 `nav_core::BaseLocalPlanner` 插件源码包（来源于 `cym_planner_standalone_20260713`）。
本包只包含规划器本身，不包含车模、机械臂、地图、Gazebo 世界或任务脚本。

## 兼容环境

- Ubuntu 20.04
- ROS Noetic
- `navigation` / `nav_core` / `pluginlib` / `sensor_msgs` / OpenCV

## 构建与接入

```bash
source /opt/ros/noetic/setup.bash
cd ~/your_catkin_ws/src
cp -a /path/to/cym_planner .
cd ..
catkin_make
source devel/setup.bash
```

在 `move_base` 节点中设置：

```xml
<param name="base_local_planner" value="cym_planner/CymPlanner"/>
<rosparam file="$(find cym_planner)/config/cym_planner_params.json" command="load"/>
```

参数加载在 `move_base` 节点自身的命名空间，而不是 `global_costmap` 或 `local_costmap` 下。

## RViz 可视化

规划器不再弹出本地 OpenCV 窗口，而是把两张可视化图发布为 ROS 图像话题，
可在 rosmaster 上的 RViz 中直接订阅（`rviz/Image` 显示，raw 传输）：

| 话题 | 内容 | frame_id |
| --- | --- | --- |
| `/cym_planner/map_image` | 局部代价地图与全局路径叠加图（放大 5 倍，便于观察） | costmap 全局 frame（如 `odom`） |
| `/cym_planner/plan_image` | 车体系下全局路径俯视图（600×600，100 px/m） | `base_link` |

话题名可用参数 `~/map_image_topic`、`~/plan_image_topic` 覆盖，默认即上表值。

## 搬运降速

规划器订阅 `std_msgs/Bool` 话题 `/sim_task3/carry_mode`。收到 `true` 后，
前进、转向及终点微调速度均按 `carry_speed_scale` 缩放；当前配置为 `0.80`（保留原速度 4/5）。
独立使用时，不发布该话题即保持正常速度。

## 配置

`config/cym_planner_params.json` 中的 `base_link_frame`、`odom_frame` 必须与目标机器人
TF 名称一致。插件导出定义位于 `cym_planner_plugin.xml`。
