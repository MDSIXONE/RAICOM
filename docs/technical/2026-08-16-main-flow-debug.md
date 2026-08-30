# 主流程实机调试总结（2026-08-16）

> 会话背景：实机跑通比赛主流程（定点巡航 5 点 → 抓球放球）。本文件记录 08-16 全天调试的时间线、根因、标定数据与遗留事项，供后续会话直接续接。

## 1. 当前系统架构（机器来电后按此重建）

- **ROS master 跑在机器上**（容器 ros-noetic 内 roscore，host 网络，127.0.0.1:11311 / 192.168.137.157:11311），不依赖 WSL 动态 IP。
- **启动顺序**：`sudo raicom-control-handover acquire`（停厂商起手控 8765）→ 容器内 `roscore` → `roslaunch robot_dog_bringup robot_dog_main.launch`（参数见下）。全部用 `docker exec -d`（detach 模式，进程常驻）。
- **主流程一键执行**：`bash /home/pi/run_main_flow.sh`（容器内跑导航 → ssh 本机停 oumax-camera+oumax-manual 释放相机/串口 → xgovenv python 跑 ball_grab_release.py --enable-motion）。
- **launch 关键参数**（robot_dog_main.launch）：
  - `use_amcl:=true map_file:=/root/catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.yaml init_x:=0.0 init_y:=0.0 init_yaw:=0.0 enable_motion:=true local_master_ip:=192.168.137.157`
  - 桥（oumax_cmd_vel_bridge）：`x_scale_ref=0.2`（0.2 m/s 即满步长）、`linear_motion_value=25`、`x_min_step=15`、`dead_zone_wz=0.10`
  - simple_odom：`odom_scale=0.23`（位移标定，见 §3）
  - scan_circle_filter：`radius=0.25`（原 0.45 导致 AMCL 特征稀疏静止漂移）
  - cym_planner：`lookahead_distance=1.0`、`heading_tolerance=0.6`、`final_yaw_tolerance=0.15`（追线放宽）
- **主流程路径参数**（run_main_flow.sh）：`--side-distances 0.5,0.25,-0.575`（右侧距离按地图已知区 y≥-0.75 临时收缩；地图补扫后恢复 `0.5,1.65,-0.575`）。

## 2. 调试时间线（问题 → 根因 → 修复）

| # | 问题 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 主流程首跑"只能左右转、无法前进" | 桥 x 映射 x_scale_ref=4.0 使步长 12~13 压死区边缘（实测 13 不动）；桥 yaw 优先分支在 vx/wz 同非零时吃掉 x | x_scale_ref=0.2 + linear_motion_value=25 + x_min_step=15 + dead_zone_wz=0.10 → 单点测试 x=25 满步长、狗实际前进 |
| 2 | waypoint 3/4 规划失败（Failed to get a plan） | 实机地图 `ricam_arena_mapped`（8-15 建图）右下角 y≤-1.2 全未知（navfn 把 unknown 当 lethal）；且 y=-0.85~-1.1 有实时障碍膨胀高代价带 | 路径缩到已知区（--side-distances 0.5,0.25,-0.575）；最终需补建图扫右下角后恢复原参数 |
| 3 | simple_odom 在 roslaunch 里启动即死（exit 127） | **CRLF 污染**：scp 部署的 simple_odom.py shebang 变 `python3\r`；手动 `python3` 显式调用绕过 shebang 掩盖问题（浪费大量排查时间） | 容器内 `sed -i 's/\r$//'` + 重启 launch（mistake 已记录 2026-08-16.md） |
| 4 | 整机重启后 simple_odom 等节点起不来 / master 混乱 | 孤儿进程残留 + 同名节点注册冲突 + roslaunch 连不上 master | docker restart 容器（彻底清进程）→ 重建 roscore+launch；pkill 模式用 `[r]` 技巧防自杀 |
| 5 | AMCL 静止漂移（reset 后 3s 漂到 0.96m） | scan_circle_filter 过滤半径 0.45 过大，空旷场地有效点仅 96/410，激光匹配歧义大 | radius 0.45→0.25 → reset 后静止 5 次采样全 (0,0,0) 稳定 |
| 6 | "移动距离太短"（名义 1.0m 实际 2cm~146cm 随机） | **XGO mini3W 是轮足**：move_x 步态轮子自由滚动+打滑，位移不可重复（±20%）；odom 按 cmd_vel 积分虚高 | simple_odom 加 odom_scale 标定参数；多次实测取近似 0.23（见 §3） |
| 7 | wheel 模式（enable_wheel_control(1)+wheel_control）完全不动 | 固件 wheel 控制不可用/需持续刷新（单发、10Hz 刷新均无效）；wheel_byte 编码 0-255、128=停 | 放弃 wheel 模式路线；锁轮（128）+move_x 能走（F1=50cm F2=61cm，仍差 22%） |
| 8 | ⚠️ **F 测试后狗留在 wheel 模式**（flag=1+轮 128），主流程/抓球 move_x 全部失效 → 原地转圈无法前进 | 测试脚本改了固件模式未恢复 | **机器来电后第一件事**：跑 `/home/pi/oumax-xgo/restore_mode.py`（enable_wheel_control(0)）恢复默认腿模式 |

## 3. odom_scale 标定数据

| scale | 实测（1.0m goal 或 3s move_x） | 备注 |
| --- | --- | --- |
| 1.0 | 1.6s 到，实际 2cm | odom 虚高 ~50 倍（转向段 x 被吃 + 打滑） |
| 0.17 | 7.6s 到，实际 146cm | 过冲 46% |
| 0.24 | 5.4s 到，实际 85cm | 欠冲 15% |
| 0.22 | 6.0s 到，实际 91cm | 欠冲 9% |
| 0.19 | 两次：138cm（AMCL 漂移期，无效）/ 91cm | 漂移污染 |
| 0.23（当前） | 锁轮 F 段：move_x(25) 3s = 50/61cm → 0.185 m/s → scale=0.185/0.8 | 物理打滑 ±20% 无法消除，取近似 |

**结论**：轮子打滑 + 步态随机性是物理现实，完美标定不可能。odom_scale=0.23 为近似值，导航残余误差靠 AMCL（近处特征修正）+ 抓球/放球视觉闭环兜底。

## 4. 遗留事项（按优先级）

1. **恢复狗默认模式**：机器来电后执行 `restore_mode.py`（enable_wheel_control(0)），验证 move_x 恢复前进（否则一切 move_x 驱动失效）。
2. **跑完整主流程**（导航 5 点 + 抓球放球）：当前 5 点导航已跑通过一次（缩点路径），全链路（含抓球放球）待完整验证；注意观察每点实际到达位置误差。
3. **地图补建图**：扫右下角（y≤-1.2），完成后恢复 `--side-distances 0.5,1.65,-0.575` 原路径。
4. **DWA 对比**（可选）：`local_planner:=dwa` 已写好（config/dwa_planner.yaml + launch arg），机器来电后部署三个文件（launch/move_base.yaml/dwa_planner.yaml）可对比验证追线行为。
5. 手控服务 06:24 曾卡死、07:05 被 systemd 重启（原因未查，待观察）。
6. 部署提醒：向容器/机器 scp 脚本后必须 `chmod +x` + **检查 CRLF**（shebang 行无 \r）。

## 5. 关键文件清单（仓库 ↔ 部署）

| 文件 | 说明 |
| --- | --- |
| `robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch` | 主 launch（桥/simple_odom/scan_filter/cym 参数、local_planner arg、AMCL） |
| `robot-src/catkin_ws/src/robot_dog_navigation/scripts/main_flow.py` | 主流程（--grab-release-ssh 远程球程序模式） |
| `robot-src/catkin_ws/src/robot_dog_navigation/scripts/simple_odom.py` | odom（odom_scale 参数） |
| `robot-src/catkin_ws/src/robot_dog_navigation/config/dwa_planner.yaml` | DWA 对比参数（待部署） |
| `robot-src/catkin_ws/src/cym_planner/config/cym_planner_params.json` | 局部规划器参数（放宽版） |
| `/home/pi/run_main_flow.sh`（机器） | 一键执行脚本 |
| `/home/pi/oumax-xgo/restore_mode.py`（机器，已传） | 恢复默认腿模式（来电后第一件事） |
