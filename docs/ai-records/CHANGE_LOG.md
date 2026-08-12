# 代码改动记录

每个改动单元的状态只能使用“进行中”或“改动完成”。

## 2026-08-11｜四轮通道顺序校正

- 状态：进行中
- 目标：按实机观察修正轮控数据通道顺序，使左/右转分别让物理左侧和右侧的两个轮子同组反向运行。
- 影响文件：`robot-src/host-services/oumax-xgo/manual_control_server.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：待更新。
- 验证：待更新。
- 遗留风险：待更新。

## 2026-08-11｜四动力轮差速转向映射

- 状态：改动完成
- 目标：按实机确认的四个主动轮实现轮式左/右转：左转左侧两轮向后、右侧两轮向前；右转相反。
- 影响文件：`robot-src/host-services/oumax-xgo/manual_control_server.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`gamepad_wheel_speeds` 改为四轮差速混合，输出顺序为左前、右前、左后、右后；正 yaw 输出 `[-,+,-,+]`（左转），负 yaw 输出 `[+,-,+,-]`（右转），同时移除右侧为被动轮的错误假设。已备份并部署到机器 `/home/pi/oumax-xgo/manual_control_server.py`，备份为 `/home/pi/oumax-xgo/manual_control_server.py.20260811-wheel4-turn.bak`。
- 验证：本地及机器端 Python 编译通过；映射断言确认左转 `[-1.15,1.15,-1.15,1.15]`、右转 `[1.15,-1.15,1.15,-1.15]`、直行四轮同向；部署后原厂主服务为 active、手控服务为 inactive，因此未发送新的运动指令。
- 遗留风险：轮式转向的正负方向已按用户定义映射，首次在实际地面使用仍应短时观察机身朝向；手控服务将在下一次控制权交接后加载新代码。

## 2026-08-09｜实机部署：jie_ware 定位 + 键盘姿态控制

- 状态：改动完成
- 目标：把 jie_ware 激光定位集成（lidar_loc/initial_pose_publisher/scan filter 三 launch 改动）与键盘姿态控制（pose_keyboard_teleop + kind=motor 接口）传输到机器狗（192.168.137.157）部署并编译。
- 影响文件：机器 `/home/pi/ros_ws/src/{jie_ware,robot_dog_navigation,robot_dog_bringup,robot_dog_teleop}/`、`/home/pi/oumax-xgo/manual_control_server.py`、`/usr/local/sbin/raicom-launch-pose-keyboard`；仓库 `docs/ai-records/CHANGE_LOG.md`。备份：机器 `/home/pi/ros_ws/backups/deploy-20260809-jie-ware-pose/`。
- 实施记录：scp 上传 jie_ware 包、navigation/bringup/teleop 差异文件与 manual_control_server.py；机器上 `sed -i 's/\r$//'` 修复 Windows scp 引入的 CRLF 行尾（install_host_handover.sh、launch_pose_keyboard_teleop.sh）；`sudo bash install_host_handover.sh --install-only` 注册 `raicom-launch-pose-keyboard`；容器内 `catkin_make` 编译成功（jie_ware 三节点 + 脚本 wrapper）。顺带修复两个机器侧历史误传：工作空间根 `/home/pi/ros_ws/CMakeLists.txt`（2026-08-07 误放的 catkin 顶层模板，挡住 catkin_make，移至 backups/CMakeLists.txt.stray-20260807-root）与 WSL 专用包 `ball_spotter/`（无 CMakeLists.txt 导致 catkin 配置失败，移至 backups/ball_spotter-stray-wsl-pkg-20260809）。
- 验证：devel 空间 `jie_ware/{lidar_loc,costmap_cleaner,lidar_filter_node}` 可执行存在、`initial_pose_publisher.py` 已安装；`roslaunch robot_dog_bringup robot_dog_main.launch --nodes` 解析出 map_server/lidar_loc/initial_pose_publisher/move_base；`pose_keyboard_teleop.launch enable_motion:=false --nodes` 解析出 /robot_dog_pose_keyboard_teleop；两个新 Python 脚本容器内 py_compile 通过；宿主机 manual_control_server.py py_compile 通过且 `kind=motor`/`MOTOR_RANGES` 就位。未切换串口所有权（oumax-manual.service 保持 inactive，raicom-original-main.service 维持 active），新版 manual_control_server 将在下次 launch_pose_keyboard_teleop.sh acquire 时生效。
- 遗留风险：姿态键盘首次实机使用须先按 `m` 回中（本地跟踪角可能与舵机实际角漂移），并在站稳、净空 1 m 场地以最小细步（w/s 1°）逐关节验证方向；`kind=motor` 参数校验已静态验证，实际动关节行为待实机；lidar_loc 实机首次导航需确认 initialpose 落点与实际位置偏差在收敛域内（±1 栅格/±1° 迭代），不匹配时用 rviz 2D Pose Estimate 修正后再发目标点；lidar_loc 不可单独重启（会卡地图原点）。

## 2026-08-09｜定点导航接入激光定位（jie_ware lidar_loc）与局部代价地图

- 状态：改动完成
- 目标：把 https://github.com/6-robot/jie_ware 的激光扫描匹配定位节点 `lidar_loc` 集成进定点导航任务（替代静态 map→odom TF），并让任务/本地 rviz 的局部代价地图具备 `/scan_filtered` 数据源与可视化。
- 影响文件：`catkin_ws/src/jie_ware/`（新增第三方包：`src/{lidar_loc,costmap_cleaner,lidar_filter_node}.cpp`、`CMakeLists.txt`、`package.xml`、`LICENSE`、`launch/`）、`catkin_ws/src/robot_dog_navigation/scripts/initial_pose_publisher.py`（新增）、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`catkin_ws/src/robot_dog_bringup/package.xml`、`catkin_ws/src/robot_dog_navigation/{launch/offline_navigation.launch,launch/robot_visualization.launch,CMakeLists.txt,package.xml}`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`lidar_loc` 订阅 `/map` 与 `/scan_filtered`，把激光点投影到地图障碍物渐变图做逐帧 15 变换（±1 栅格 × ±1°）迭代匹配，解出 map 系位姿并结合 `simple_odom` 的 odom→base 里程计发布 `map→odom` TF（30Hz）；收到 `/initialpose` 约 30 帧后自动调 `move_base/clear_costmaps`。导航模式用 `lidar_loc`（laser_topic=/scan_filtered）替换原静态 map_to_odom 并移除组外静态节点（顺带消除建图模式 gmapping 与静态 map_to_odom 双发布者冲突隐患）；新增 `initial_pose_publisher.py` 在 `/map` 到达后延时 1s 重复发布 5 次 `/initialpose`（init_x/init_y 默认 -0.70/1.00），覆盖 lidar_loc 收到地图时重置地图原点的竞争；本地 `offline_navigation.launch` 新增 `scan_circle_filter`（/scan→/scan_filtered，参数与实机一致）使局部代价地图有数据、rviz 的 Local Costmap 显示生效，并新增 `use_lidar_loc` arg（默认 false，true 时验证 lidar_loc 节点/TF 链路——mock 房间数据与 RICAM 地图不匹配，估计会漂移属预期）；`robot_visualization.launch` 同步加 filter 并把云点改订阅 `/scan_filtered`；`robot_dog_bringup/package.xml` 补齐运行依赖（gmapping/map_server/move_base/jie_ware/cym_planner 等）。
- 验证：jie_ware 三节点在 WSL Noetic 编译链接成功（需 cv_bridge/OpenCV，环境自带）；三个 launch 与两个 package.xml 均通过 XML 解析；离线默认模式端到端实测：`/scan_filtered` 有 360 点数据、`/move_base/local_costmap/costmap` 100×100@0.01 滚动窗口持续更新、`scan_circle_filter/move_base` 在线；`use_lidar_loc:=true` 实测：`lidar_loc/initial_pose_publisher` 在线，`tf map→odom` 持续发布且匹配结果随 mock 数据收敛（yaw ≈ -24°），`/initialpose` 发布窗口正常。
- 遗留风险：lidar_loc 收到 /map 会重置估计到地图原点，单独重启该节点会卡原点——须与 initial_pose_publisher 同启（已在 launch 注释与文档写明）；lidar_loc 匹配算法只在估计位姿附近 ±1 栅格/±1° 搜索，初始位姿误差需较小，实机开机后需确认 initialpose 落点与实际位置偏差在收敛域内；jie_ware 为 GPL-2.0 许可，与仓库其余 BSD-3-Clause 包隔离管理（进程间 topic 通信无链接传染）；实机导航闭环（lidar_loc 收敛后 2D Nav Goal 全程）待机器开机验证。

## 2026-08-08｜键盘姿态控制：j1-j15 关节步进调姿与姿态记录

- 状态：改动完成
- 目标：新增键盘程序控制车体姿态（机械爪、前腿、后腿共 15 个关节），终端实时显示当前姿态（如 `j1 1, j2 1`），支持一键记录姿态到文件。
- 影响文件：`catkin_ws/src/robot_dog_teleop/scripts/pose_keyboard_teleop.py`（新增）、`catkin_ws/src/robot_dog_teleop/launch/pose_keyboard_teleop.launch`（新增）、`catkin_ws/src/robot_dog_teleop/host/launch_pose_keyboard_teleop.sh`（新增）、`host-services/oumax-xgo/manual_control_server.py`（新增 `kind=motor` 单关节接口）、`catkin_ws/src/robot_dog_teleop/{CMakeLists.txt,host/install_host_handover.sh,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：关节映射 j1–j12 为四腿（j1/j2/j3 左前、j4/j5/j6 右前、j7/j8/j9 右后、j10/j11/j12 左后，分别为小腿/大腿/髋，舵机 id 11–43），j13 夹爪（51）、j14 小臂（52）、j15 大臂（53），范围按原厂 mcp 文档（小腿 [-73,57]、大腿 [-66,93]、髋 [-31,31]、爪 [-65,65]、小臂 [-115,70]、大臂 [-85,100]），默认姿态 0/0/-85/70；`manual_control_server.py` 新增 `MOTOR_RANGES` 表 + `handle_motor`（id/角度类型与范围校验、中文错误、`bot.motor(id, angle)`）+ dispatch 分支；`pose_keyboard_teleop.py` 沿用 u→y 双确认、`enable_motion:=true` 门禁、空格/x 锁定、Ctrl-C 双次退出模式，`[`/`]` 循环选关节、`w`/`s` 细步（默认 1°）、`q`/`e` 粗步（默认 10°）、`m` 回中、`r` 记录姿态（UTF-8 追加、失败仅报错）、`h` 帮助；终端底部 3 行 ANSI 实时重绘（状态行 + 姿态两行，每行 ≤80 字符，80 列终端不换行），姿态行格式 `j1 0, j2 0, ...` 便于抄录；未武装时按键只更新本地跟踪值不发送；`install_host_handover.sh` 注册 `raicom-launch-pose-keyboard`。
- 验证：py_compile 通过；launch XML 解析通过；两个 host 脚本在 WSL `bash -n` 通过；git 空白检查通过；独立测试脚本（mock `bot.motor`/rospy/termios）40+ 断言全部通过（15 关节范围端点 57/-73/93/-66/31/-31/65/-65/70/-115/100/-85 接受、越界拒绝、未知/缺失/非数字 id 拒绝、关节表名/id 映射、默认姿态行、钳制与边界 no-op、关节循环选择、记录文件内容、回中）；全部改动文件 LF 行尾。
- 遗留风险：本地跟踪角度与舵机真实角度可能漂移（若曾被其他程序移动），首次使用须先按 `m` 回中；单关节步进可能改变腿的姿态稳定性，须在站稳、净空 1 m 场地以最小细步逐关节验证方向；`kind=motor` 与 `raicom-launch-pose-keyboard` 需部署后实机验证；52/53 大臂舵机默认值按原厂文档，实机回中后需目视核对。

## 2026-08-08｜gmapping 键盘建图与实机地图切换

- 状态：改动完成
- 目标：在实机上用键盘控制机器狗行走，通过 gmapping 实时建图并保存地图，供导航模式加载使用；修复建图不出图与里程计位移不更新的问题。
- 影响文件：`catkin_ws/src/robot_dog_navigation/scripts/{laser_frame_tf.py,simple_odom.py,scan_circle_filter.py}`、`catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.{pgm,yaml}`（新增）、`catkin_ws/src/robot_dog_teleop/scripts/mapping_keyboard_teleop.py`（新增）、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`、`docs/local-rviz-navigation-quickstart.md`。
- 实施记录：容器安装 `ros-noetic-slam-gmapping`（可执行文件在 `gmapping` 包而非 `slam_gmapping` 空 wrapper，launch 必须 `pkg="gmapping" type="slam_gmapping"`）；`robot_dog_main.launch` 新增 `enable_mapping` arg（true 时停 map_server/move_base 并起 slam_gmapping，false 时原导航模式）；新增 `laser_frame_tf.py` 把 base_link→laser_frame 静态 TF 改为动态发布（gmapping 用 tf1 不读 /tf_static，这是实机“只有首图”的决定性根因）；新增 `mapping_keyboard_teleop.py` 键盘建图脚本（w/s 前后、a/d 转向、按住持续 10Hz 发布 /cmd_vel，走桥接→simple_odom 保证建图 odom 正确）；`simple_odom` 加固（yaw 毛刺限幅 0.4rad、静止冻结、位移限幅）并把初始位姿改为 launch 的 init_x/init_y arg（建图模式 0,0 对齐机器起点）；修复 `simple_odom` d_max 位移限幅 0.02→0.10（foot 步速 0.3~0.8m/s 时原限幅每帧清零导致 rviz 车体只转不走）。
- 验证：实机键盘建图成功，保存 `ricam_arena_mapped.pgm/yaml`（1408×1344 @ 0.02m/pix，origin [-13.66,-14.06]）；切回导航模式 `/map` 加载新建图、move_base 恢复、无 transform 超时；gmapping 本地对照实验全链路跑通（动态 TF + 0.2s scan 时间戳偏移后 /map 持续更新）；d_max 修复仅本地 py_compile 通过，实机验证待下次开机。
- 遗留风险：d_max=0.10 修复尚未实机验证（机器关机）；simple_odom 无真实里程计，重启后需对齐起点；建图地图原点按建图起点 (0,0) 对齐，导航模式下机器实际起点需用 init_x/init_y 与地图匹配；AMCL 闭环定位未实施（待装 ros-noetic-amcl）。

## 2026-08-08｜主流程集成：球检测、里程计、运动桥接与雷达滤波

- 状态：改动完成
- 目标：把 2D Nav Goal 选点、cym_planner 导航、OUMAX 运动控制、球检测画面与雷达滤波整合为本地 rviz + 实机主流程的端到端闭环。
- 影响文件：`catkin_ws/src/robot_dog_navigation/scripts/{simple_odom.py,scan_circle_filter.py}`、`catkin_ws/src/robot_dog_teleop/scripts/oumax_cmd_vel_bridge.py`、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`wsl-simulation/src/ball_spotter/{scripts/ball_detector_node.py,launch/local_control.launch}`、`wsl-simulation/src/ricam_dataset_capture/scripts/mjpeg_bridge.py`、`host-services/oumax-xgo/manual_control_server.py`（新增 `/imu` 只读接口、Timer 看门狗运动语义、wheel4 差速混合）、`catkin_ws/src/cym_planner/config/cym_planner_params.json`、`wsl-simulation/start_local_control.sh`、WSL 侧 `/root/fix_shm.sh` 与 `/etc/wsl.conf`。
- 实施记录：本地球检测节点（YOLO 画框发布 `/ball_detector/image`）；`/cmd_vel`→OUMAX HTTP 桥接（yaw 优先、watchdog 急停、步进线性映射避开固件死区）；`simple_odom` 里程计（cmd_vel 积分 + IMU yaw 融合，替代原静态 odom→base_link TF）；雷达滤波（前方机械臂扇形 ±20°/1.0m 后改为圆心 (0,0) 半径 0.45m 全向滤除站立姿态自身遮挡）；OUMAX 手控服务增加 `/imu` 接口与 Timer 看门狗（turn/move_x 立即返回，runtime 后自动停）；WSLg 窗口修复（boot.command 预挂载 tmpfs 到 /mnt/shared_memory）；IP 迁移至 192.168.137.232。
- 验证：球检测 3 球全检出（red 0.92/blue 0.90/green 0.87）；/odom 10 Hz 且 yaw 随 IMU 变化；/imu 返回 `{"ok":true,"yaw":5.61,...}`；自身遮挡滤波后 <0.45m 点 = 0；WSL 发 goal 到容器 move_base 成功（需 export ROS_IP=192.168.137.232）；**导航闭环 SUCCEEDED：goal (-0.20,1.00) 10s 到达，最终 odom (-0.218,0.961) 误差 ~4cm**；foot 模式转向死区确认（yaw<12 不动，15→21°/s、30→36°/s）。
- 遗留风险：simple_odom 重启后重置 init (-0.70,1.00) 但机器物理位置可能已移动——odom 绝对位置不闭合（无闭环定位），比赛需重新对齐起点；XGO 固件 yaw 步进死区 <12，小误差角修正依赖 cym final_yaw 逻辑（tolerance 0.08rad）；机器仅左侧两轮有驱动（右侧无刷被动），foot 模式为唯一可靠运动模式，wheel 模式转向打滑不可用；机器人侧 C++ 节点 master 掉线后不自动重连。

## 2026-08-05｜接入独立发布版 CymPlanner 局部规划器

- 状态：改动完成
- 目标：把 `tmp/cym_planner_standalone_20260713.zip` 中的独立发布版 `cym_planner` 源码包接入本仓库源码，替换离线演示原有的 `TrajectoryPlannerROS` 局部规划器；规划器内部的 OpenCV 窗口改为把全部可视化图像发布为 ROS 话题，供 rosmaster 上的 RViz 直接订阅。
- 影响文件：`catkin_ws/src/cym_planner/`（新增包）、`catkin_ws/src/robot_dog_navigation/{config/move_base.yaml,launch/offline_navigation.launch,launch/robot_visualization.launch,rviz/offline_navigation.rviz,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：把独立包源码复制到 `catkin_ws/src/cym_planner`，`cym_planner_params.json` 由 GB18030 转为 UTF-8，插件描述乱码修正；`cym_planner.h/.cpp` 移除 `cv::namedWindow/imshow/resizeWindow/waitKey`，新增 `sensor_msgs/Image` 发布器（`/cym_planner/map_image` 为代价地图与路径叠加图、放大 5 倍；`/cym_planner/plan_image` 为车体系 600×600 路径俯视图，话题名可由 `~/map_image_topic`、`~/plan_image_topic` 覆盖）；`package.xml` 与 `CMakeLists.txt` 增加 `sensor_msgs` 依赖。`move_base.yaml` 的 `base_local_planner` 改为 `cym_planner/CymPlanner`，两个 launch 均加载 `cym_planner_params.json`，RViz 配置新增两张 `rviz/Image` 显示。
- 验证：package/plugin/launch XML 均通过 XML 解析；参数文件按 YAML 解析成功且顶层键为 `CymPlanner`；修改后的源码无 `namedWindow/imshow/waitKey/highgui` 残留；离线与实机 launch 均能找到并加载参数文件。已部署至机器狗 `ros-noetic` 容器；安装 OpenCV 4.2 后，`catkin_make --pkg cym_planner robot_dog_navigation robot_dog_yolo_dataset` 成功，CymPlanner 插件可被 `nav_core` 发现，导航 launch 静态解析通过；未启动 `move_base` 或底盘控制。
- 遗留风险：该插件参数为 SmartCar 车体标定值（如 `max_vel_x: 14.0`、`max_vel_theta: 20.5`），远超机器狗安全速度；离线演示无 `/cmd_vel` 订阅者且实机 launch 已把 `cmd_vel` 重映射到禁用话题，但在接入真实底盘前必须按机器狗重新标定速度与增益，并验证避障与终点对准行为。

## 2026-08-05｜雷达正前方圆形区域过滤节点

- 状态：改动完成
- 目标：新增只读过滤节点，把 `/scan` 中雷达正前方 15 cm 处、半径 15 cm 圆形区域内的点置为 `inf`，用于屏蔽安装在雷达前方的机械臂；不访问底盘或雷达串口。
- 影响文件：`catkin_ws/src/robot_dog_navigation/{scripts/scan_circle_filter.py,launch/scan_circle_filter.launch,CMakeLists.txt}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：新增 Python3 节点订阅 `/scan` 发布 `/scan_filtered`，逐点把笛卡尔坐标落入以 `(center_x=0.15, center_y=0.0)` 为圆心、`radius=0.15` 的圆内的点置为 `inf` 并清零强度，其余字段原样透传；圆心与半径均可由 launch 参数覆盖，半径拒绝负值。新增配套 launch 与 `catkin_install_python` 安装声明。
- 验证：Python 语法检查通过；圆形判定断言覆盖圆心点、圆内近/远端、圆外侧方/后方/紧邻雷达点，均符合预期；Git 空白检查通过。已随导航包部署至机器狗，在 Noetic 容器构建成功，`scan_circle_filter.launch --nodes` 静态解析通过；未启动过滤节点或雷达。
- 遗留风险：圆位置按雷达坐标系（`laser_frame`）定义，机械臂若不在雷达扫描平面内则无需过滤；costmap 需将 `scan` 的 `topic` 改为 `/scan_filtered` 才能生效。

## 2026-08-05｜YOLO 相机训练集采集功能包

- 状态：改动完成
- 目标：新增独立 ROS 功能包，通过 USB 相机每 0.5 秒采集一张图片，共采集 600 张，供后续 YOLO 训练标注使用。
- 影响文件：`catkin_ws/src/robot_dog_yolo_dataset/`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：新增 OpenCV 相机采集节点、默认参数 launch 文件和使用说明；默认以单调时钟每 0.5 秒保存一次，文件连续编号至 600 张。节点不订阅或发布底盘控制话题；中断时释放相机，连续 20 次读取失败时退出。
- 验证：独立审查确认默认采集数量与间隔、定时逻辑、Catkin 安装声明和 launch 参数；本地 Python 语法、launch/package XML、默认值/关键错误路径断言与 Git 空白检查均通过。已部署至机器狗 Noetic 容器，容器已安装 Python OpenCV 4.2 并映射 `/dev/video0`，Catkin 构建与 `yolo_image_collector.launch --nodes` 静态解析通过；未启动相机或写入训练图片。
- 遗留风险：目标机器尚未连接相机；OpenCV、相机设备号和 Linux 脚本执行权限需在部署时确认，采集结束后仍需人工完成 YOLO 标注。

## 2026-08-05｜机械臂键盘控制接入

- 状态：改动完成
- 目标：新增机械臂键盘控制节点，通过 OUMAX 手控服务 `kind=arm` 接口（`cartesian`、`claw`、`mid`）逐步控制 XGO 机械臂，并沿用运动键盘的 `u→y` 双确认与急停模式。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/arm_keyboard_teleop.py,launch/arm_keyboard_teleop.launch,host/launch_arm_keyboard_teleop.sh,CMakeLists.txt,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`w/s` 步进 x 前伸/收回、`a/d` 步进 z 降低/升高、`q/e` 夹爪开合、`m` 回中（默认 home x=80、z=60，与手控服务默认一致）；步长默认 10（范围 1–20）、夹爪步长 10（范围 1–40），客户端在 0–255 内钳制并本地跟踪姿态作为步进基准。`enable_motion:=true` 才允许真实运动；`verify_identity` 校验与运动键盘一致；空格/x 锁定、Ctrl-C 第一次锁定第二次退出。机械臂命令为点目标，无持续运动，无需看门狗。
- 验证：Python 语法检查通过；启动脚本与 launch XML 与既有物理键盘模式逐段比对一致；host 启动器沿用 `raicom-control-handover acquire/release` 包裹。未上传、未启动、未发送任何串口或 HTTP 命令。
- 遗留风险：本地跟踪姿态与机械臂真实姿态可能漂移（若曾被其他程序移动），首次使用须先按 `m` 回中；首次实机测试须净空 1 m 并仅验证一次回中行为；`raicom-launch-arm-keyboard` 需要安装后在机器端部署脚本。

## 2026-08-05｜键盘 Ctrl-C 双次退出修复

- 状态：改动完成
- 目标：修复 `tty.setraw()` 下 Ctrl-C 只停止运动、无法退出键盘控制进程的问题；第一次 Ctrl-C 保持紧急停止，第二次退出程序。
- 影响文件：`catkin_ws/src/robot_dog_teleop/scripts/{keyboard_pulse_teleop.py,physical_keyboard_teleop.py,physical_keyboard_continuous.py}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：raw 模式关闭 ISIG，Ctrl-C 以字节 `\x03` 到达；原处理分支只调用 `_lock_and_stop` 且循环不退出。三个脚本均新增 `_ctrl_c_exit_armed` 标志：第一次 `\x03` 紧急停止并提示，第二次 `\x03` 跳出循环，`finally` 恢复终端并发送停止。空格/x 行为不变。
- 验证：三个脚本 Python 语法检查通过；改动经逐一复核，break 位于 `try/finally` 内，终端设置必然恢复。
- 遗留风险：无；行为变更已在启动提示与帮助文本中说明。

## 模板：YYYY-MM-DD｜改动标题

- 状态：进行中
- 目标：
- 影响文件：
- 实施记录：
- 验证：
- 遗留风险：

读取与写入时机由 `project-memory-records` 技能定义。

## 2026-08-04｜带断链停止的连续键盘控制

- 状态：改动完成
- 目标：新增独立连续键盘模式：按住方向键持续刷新原厂幅值的前后/转向请求，停止刷新、节点异常或断链时自动停止；保留单点动模式。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_continuous.py,launch/physical_keyboard_continuous.launch,host/launch_physical_keyboard_continuous.sh,host/install_host_handover.sh,CMakeLists.txt,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：基于机器既有 `oumax-manual.service` UDP `gamepad` 接口（仅本机 `127.0.0.1:8766`）实现；该服务已提供 0.35 秒 UDP 看门狗。连续节点维持原厂默认前后 `17`、yaw `55`，以最多 10 Hz 的终端重复键刷新；本地无刷新 0.25 秒即连续发送三帧零命令，并保留 `u→y` 确认、空格/x/Ctrl-C 锁定停止和唯一串口服务切换。
- 验证：目标环境 Python 模拟验证前后归一化 `17/25=0.68`、yaw 归一化 `55/80=0.6875`、同方向 0.10 秒内限流、方向切换与三帧零停止；Python 语法、launch XML、宿主启动脚本语法、Git 空白检查、WSL `rospack find` 与 `roslaunch --nodes ... enable_motion:=false` 均通过。两次 WSL `catkin_make` 均卡在既有 CMake 构建系统检查并在 55 秒上限内超时，未进入本包编译；未连接、上传或启动机器狗。
- 遗留风险：普通 SSH 终端没有 key-up 事件；方向键释放后依赖客户端停止自动重复，少数终端可能在初始重复延迟期间动作不连续。若需要可靠“松键即停”，应另行采用宿主机 evdev 原始输入。连续控制会真实运动，部署后不得自动启动；首次必须在净空场地验证停止、本地超时、UDP 断链超时和实体急停。

## 2026-08-04｜键盘自动重复脉冲锁定

- 状态：改动完成
- 目标：防止终端键盘自动重复把单次 0.20 秒点动串联为连续运动；每次成功物理点动后自动重新锁定，下一次动作须再次 `u`、`y` 确认。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机日志显示按住 `w` 产生了多次约间隔 0.20 秒的 accepted pulse，现有计时器会被后续重复键取消，无法实现单次点动的预期边界。
- 验证：本地模拟覆盖 `u→y→w→重复 w`，确认仅一次运动请求和一次超时停止；模拟请求失败后确认程序锁定、发送停止且重复键不重试。Python 语法、WSL Catkin 构建和 Git 空白检查通过。用户要求部署后，机器端脚本已更新并在容器内重新构建、Python 语法和节点解析通过；上一版备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-single-pulse-lock`。未重启当时的旧键盘进程或发送新的运动命令。
- 遗留风险：当前运行中的旧键盘程序不具备自动重复锁定，须由用户 Ctrl-C 退出后才会加载新版本；重启后每次动作都需要 `u`、`y`、方向键，且首次强度为原厂默认幅值，必须在净空场地单次验证。

## 2026-08-04｜键盘原地转向独立标定

- 状态：改动完成
- 目标：将真实键盘控制的前后与原地转向强度分离，并复用原厂 Dog_LM 摇杆默认强度：前后 XGO 值 `17`、`a/d` XGO 值 `55`，参数上限保持在原厂摇杆范围（前后 `25`、yaw `70`），脉冲仍不超过 `0.20 s`。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,launch/physical_keyboard_teleop.launch,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：实机日志已确认 `a/d` 的 HTTP 请求正常到达 OUMAX 服务；随后按用户要求读取原厂 `dog_Joystick.py`：默认 `step_control=70`，前后映射为约 `17`，yaw 映射为约 `55`（上限 `100`）。原先的保守 yaw `16` 方案已弃用；新方案保留键盘程序的脉冲超时、急停和同进程确认保护。
- 验证：本地 Python 语法、launch XML、WSL Catkin 构建和物理 launch 节点解析通过；用户要求部署后，机器端脚本、launch 和说明已更新，上一版物理键盘脚本/launch 备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-original-values`，容器内 Catkin 构建、Python 语法和节点解析通过。未重启或改变当时运行中的旧实控进程，未发送新的运动命令。
- 遗留风险：新参数会使首次 `a/d` 实际转向更明显；当前运行中的旧实控进程不会热加载新参数，须由用户主动退出并重新启动。重启后必须在净空场地单次验证方向；前后/yaw 值只是复刻原厂默认幅值，不是完整复刻原厂持续摇杆的时间行为，也不是 m/s 或 rad/s。

## 2026-08-04｜手控服务就绪等待修复

- 状态：改动完成
- 目标：修复控制权接管脚本在 OUMAX 服务刚被 systemd 启动时立即探测健康接口、误判服务失败并回滚的问题；只增加有限就绪等待，不改变运动接口。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/raicom-control-handover`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机复现显示 `oumax-manual.service` 从启动到监听 `127.0.0.1:8765` 存在约 1 秒初始化窗口；当前脚本在 systemd active 后立即 `curl`，触发安全回滚。新增总时限约 5 秒、每 0.2 秒一次的只读 `/health` 重试，并校验 `ok`、串口和端口身份；超时/服务退出时先停止手控服务、等待串口释放，才恢复原厂 UI。回滚后原厂 UI 已恢复、OUMAX 服务已停止、未发送运动命令。
- 验证：Bash 语法与 Git 空白检查通过；mock `systemctl`、`fuser`、`curl` 验证前五次健康检查失败、第六次返回正确身份时仍能获得控制权，并在 release 后恢复原厂 UI。用户授权修复后，已上传至机器工作区和 `/usr/local/sbin/raicom-control-handover`，旧帮助程序备份为 `/usr/local/sbin/raicom-control-handover.20260804-readiness.bak`；实机只读回归成功完成“原厂 UI 停止 → OUMAX 服务监听并返回正确 `/health` → 原厂 UI 恢复”，两端服务状态均正确，未启动键盘节点、未调用 `/command` 或发送运动命令。
- 遗留风险：不得在修复验证时启动物理键盘节点或调用 `/command`；仅允许检查 `/health`。

## 2026-08-03｜机器狗键盘控制权自动切换

- 状态：改动完成
- 目标：在宿主机上将原厂 `common/main.py` 迁移为可控服务；真实键盘控制启动时临时停止原厂程序并启用 OUMAX 手动服务，退出时恢复原厂程序。当前只在本地编写，不上传、不运行。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/`、`catkin_ws/src/robot_dog_teleop/README.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：开始前已确认现机原厂程序由 `/etc/rc.local` 启动且持有 `/dev/ttyAMA0`；OUMAX 服务已收紧为仅本机监听。新增可控的原厂 UI systemd 单元、控制权 acquire/release 帮助程序、交互键盘启动包装器和显式 `--cutover` 安装脚本。它只替换经精确核验的 `rc.local` 原厂启动行并保留备份，拒绝 raw/其他手控服务并在任一接管失败时恢复原厂 UI；不会重新执行包含网络清理逻辑的整个 `rc.local`。
- 验证：三个 Bash 脚本的 `bash -n` 通过；在 WSL 以 mock `systemctl`、`fuser`、`curl` 验证 acquire 后原厂服务变为停止且 OUMAX 服务变为运行、release 后顺序反转；Git 空白检查通过。用户要求上传后，新包已同步到机器 `/home/pi/ros_ws/src/robot_dog_teleop`，旧版已备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-control-handover`；容器内 Catkin 构建、两个键盘 launch 节点解析、Python/launch XML 和三个宿主机脚本语法检查通过。未执行安装脚本、未停止原厂程序、未启动实控节点或发送运动命令。
- 遗留风险：部署前必须复核 `rc.local` 启动行仍与安装脚本一致，并确认没有外部路径重启 `common/main.py`。真实串口接管与首次点动仍须在用户确认电量、急停和场地条件后进行。

## 2026-08-03｜机器狗官方手动控制桥接

- 状态：改动完成
- 目标：在不抢占底盘串口的前提下，将已确认的键盘请求话题受控转发给机器现有的 OUMAX 手动控制服务，实现真实键盘点动的可部署实现；默认禁止实际运动。
- 影响文件：`catkin_ws/src/robot_dog_teleop/`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `ros-noetic` 容器与既有 `oumax-manual.service`。
- 实施记录：开始前确认宿主机 `oumax-manual.service` 正在独占 `/dev/ttyAMA0`，并在 `127.0.0.1:8765` 提供 `/health` 与 `/command` 接口；容器可访问健康接口。最终实现为同一进程内的 `physical_keyboard_teleop.py`：它不打开串口、也不订阅 ROS 速度话题，仅在键盘本地 `u`、`y` 双确认后调用该唯一服务。仅允许前后和原地转向，XGO 指令值硬限为 `1..8`、脉冲硬限为 `0.05..0.20 s`；零命令、超时、异常和退出均请求停止。取消了会被 ROS 话题绕过的独立 bridge，并以脉冲 ID 消除旧定时器对新命令的竞态。
- 验证：本地 WSL Catkin 构建、Python 语法、launch XML 和物理 launch 节点解析通过；机器容器内 `catkin_make`、包解析、物理 launch 节点解析、Python 语法和 XML 解析通过。新包已上传，上一版保留在 `/home/pi/ros_ws/backups/robot_dog_teleop-20260803-physical-keyboard`；在用户授权后，机器端手动服务源码已备份为 `/home/pi/oumax-xgo/manual_control_server.py.20260803-localhost.bak`，并收紧为仅监听 `127.0.0.1:8765/8766`，LAN 地址探测失败、容器健康探测成功；未启动物理控制 launch、未发送 HTTP 控制请求、未发送底盘命令。
- 遗留风险：首次真实运动尚未获现场安全确认。`/etc/rc.local` 自动启动的原厂 `common/main.py` 当前仍持有 `/dev/ttyAMA0`，不能与 OUMAX 手动服务并行使用；且应用日志显示电量为 9，须先充电。未经用户明确同意停止/替换原厂主程序、确认唯一串口持有者、急停/断电可达、站稳姿态，以及在 1 m 净空内验证首次单脉冲方向与停止行为，不得启动物理控制。

## 2026-08-03｜机器狗投影尺寸与键盘点动控制

- 状态：改动完成
- 目标：将 RViz 矩形替身及规划足迹调整为长 0.27 m、宽 0.16 m；新增默认锁定、明确确认后才可发出短时速度脉冲的键盘控制程序。实现阶段不部署或移动；后续已在机器开机后完成上传与静态核验。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`catkin_ws/src/robot_dog_teleop/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：矩形 Marker 与 footprint 已同步为长 0.27 m、宽 0.16 m；新增独立 `robot_dog_teleop` 包，默认只发布 `/robot_dog_teleop/requested_cmd`，不发布 `/cmd_vel`、不访问串口。程序默认锁定，按 `u` 后 5 秒内按 `y` 才解锁；`w/s/a/d` 每次仅请求 0.20 秒脉冲，空格、`x`、Ctrl-C 和退出均归零并锁定。
- 验证：WSL Catkin 构建通过并识别 `robot_dog_teleop`；Python、launch XML、Bash 和 Git 空白检查通过；本地离线节点实测 Marker 是 `base_link` 下的 CUBE，`scale.x=0.27`、`scale.y=0.16`，局部 costmap 已发布；从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 的全局路径服务仍能到达目标点。机器开机后已同步到 `/home/pi/ros_ws/src/`，容器内 Catkin 编译、包解析、launch 节点解析、Python 语法和 0.27×0.16 足迹/隔离话题检查通过；未启动节点、未解锁、未发送任何硬件命令。
- 遗留风险：当前没有经确认的 ROS 底盘 bridge；键盘程序仅完成干运行请求链路。实机底盘速度接口及安全现场条件尚未验证；不得在未经用户再次确认、机器固定检查和紧急停止准备前部署或解锁运动。

## 2026-08-03｜实机 ROS 导航可视化部署

- 状态：进行中
- 目标：将 RICAM 地图与导航可视化包部署至机器狗 ROS Noetic 容器，使本地 RViz 可显示正确起点、0.30 m × 0.25 m 矩形、全局/1 m × 1 m 局部代价地图和实时雷达点云；不发送底盘速度指令。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/start_robot_rviz.sh`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `/home/pi/ros_ws/src/robot_dog_navigation/` 与 `ros-noetic` 容器。
- 实施记录：全局和局部 costmap 参数已独立，膨胀半径均为 0.10 m；局部窗口改为 1 m × 1 m、0.01 m。新增从真实 `/scan` 实时转换 `/lidar_points` 和矩形 Marker 的只读节点、实机 launch 及本地 RViz 连接脚本；`move_base` 的速度输出重映射到无订阅者的隔离话题。机器端旧导航包已备份至 `/home/pi/ros_ws/backups/robot_dog_navigation-20260803-ricam-visualization`，新包已上传并在容器内构建；容器 Ubuntu 源切换至阿里云 ports 镜像，已安装 navigation、map-server 和 tf2-ros。
- 验证：机器端实测 RICAM 地图为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`；起点 TF 为 `(-0.70, 1.00)`；Marker 为 `0.30 m × 0.25 m`；全局/局部膨胀均为 0.1，局部宽高均为 1.0；真实 `/scan` 与 `/lidar_points` 均约 10 Hz，两个 costmap 话题均已发布，隔离速度话题没有订阅者。机器端已看见本机 RViz 注册为地图、点云和两张代价地图的订阅者。
- 遗留风险：已确认机器狗无法连接本机 WSL 的 RViz 动态 TCPROS/XMLRPC 端口，当前无法完成实际数据传输与目标点回传；Windows 防火墙规则创建需要管理员权限。绝不启动底盘控制节点。

## 2026-08-03｜离线定点任务切换至 RICAM 场地地图

- 状态：改动完成
- 目标：将最新版仿真 `ricam_arena` 的 3.0 m × 2.5 m 栅格地图作为本地 `robot_dog_navigation` 定点任务的默认地图；暂不上传机器狗。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/{setup_offline_navigation,start_local_rosmaster,start_offline_navigation,verify_offline_navigation}.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：将 `ricam_arena.pgm` 复制到导航包内并新增配套 YAML，默认 launch 切换至该地图；规划 footprint 统一为长 0.30 m、宽 0.25 m，附加 0.01 m 边界；安全起点设为 `(-0.70, 1.00)`，模拟雷达保留给 RViz 显示但不参与障碍层。
- 验证：地图源与导航包副本 SHA-256 均为 `F0336D936FA407548130CC6E3EBE253D7B10AD91438DEF02D57B171C6BB31488`；本地 launch 实测 `/map` 为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`，全局代价地图分辨率为 0.01 m、障碍层为 `false`；`move_base/make_plan` 从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 成功生成并精确结束于目标点；YAML、launch XML、Python 和全部 WSL Bash 脚本语法检查，以及 Git 空白检查均通过。
- 遗留风险：场地地图仅用于当前离线定点验证，尚未与真实雷达、机器人坐标系或实际安全边界标定；本次没有连接或上传机器狗。

## 2026-08-03｜RViz 矩形机器狗替身

- 状态：改动完成
- 目标：在本地离线 RViz 中以长 0.30 m、宽 0.25 m 的矩形可视化标记代替缺失的机器狗 URDF 模型。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：模拟雷达节点新增本地 `visualization_msgs/Marker` 发布器，在 `base_link` 下发布蓝色 `CUBE` 作为机器人矩形替身；默认长 0.30 m、宽 0.25 m、高 0.10 m，均可由 launch 参数调整。RViz 默认配置新增 Marker 显示，自动验证增加 Marker 话题与长宽断言；全程未修改或访问机器狗硬件。
- 验证：本机 Noetic 已解析 `visualization_msgs`；节点语法、Bash 语法与 Git 空白检查通过。已重启本地离线 launch，实测 `/robot_body_marker` 为 `visualization_msgs/Marker`，`base_link`、`CUBE`、`scale.x=0.3`、`scale.y=0.25`、`scale.z=0.1` 均正确，且 `/rviz` 已订阅该话题。
- 遗留风险：尺寸按用户给出的长 30、宽 25 解释为常用机器人单位厘米，即 0.30 m × 0.25 m；当前规划 `footprint` 比视觉矩形宽，后续接入真实机器人前应单独依据实测尺寸统一规划碰撞边界。

## 2026-08-03｜本地离线全局规划与 RViz 场景

- 状态：改动完成
- 目标：在本机 WSL 的独立 ROS Noetic Master 中接入官方 `global_planner/GlobalPlanner`，提供离线地图、模拟雷达点云、全局代价地图和 RViz 默认视图；不连接或改动机器狗的 ROS Master。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`blender-maps/`、`wsl-simulation/`、`README.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：新增离线导航功能包，使用官方 `move_base + global_planner/GlobalPlanner`、`map_server`、模拟 `/scan` 与 `/lidar_points`、静态 `map → odom → base_link → laser_frame` TF 和默认 RViz 配置；新增匹配的 `PGM + YAML` 栅格地图及可再生成的 Blender 场景脚本。WSL 脚本在 `~/raicom_ws` 的 ext4 文件系统构建，并固定 `ROS_MASTER_URI`、`ROS_IP` 和 `ROS_LOCALHOST_ONLY` 为回环地址；实机 `robot_dog_lidar` 包在本地构建中被黑名单排除。
- 验证：`catkin_make -DCATKIN_BLACKLIST_PACKAGES=robot_dog_lidar` 构建成功；无界面验证确认 `/map`、`/scan`、`/lidar_points`、`/move_base/global_costmap/costmap` 和官方全局路径均可收到；`RAICOM_VERIFY_RVIZ=1 bash wsl-simulation/verify_offline_navigation.sh` 进一步确认 WSLg RViz 配置可随离线 launch 启动。
- 遗留风险：D 盘剩余空间约 9.8 GiB；当前未找到 Blender 可执行文件，仓库保存的是可生成 `.blend` 的脚本而非二进制场景。地图、TF 和雷达数据均为离线模拟，接入真实传感器、定位或底盘前仍需单独设计安全边界与验证。

## 2026-07-30｜GitHub Actions 自动更新项目结构树

- 状态：改动完成
- 目标：在目录结构变化后自动更新 README 中的项目结构树。
- 影响文件：`.github/workflows/`、`scripts/`、`README.md`、`.gitignore`
- 实施记录：新增 README 结构树生成脚本和 GitHub Actions 工作流；以唯一标记限定更新范围。
- 验证：脚本通过 Python 编译、重复运行幂等性、唯一标记、排除内部目录和 Git 差异检查；GitHub Actions 首次运行成功。
- 遗留风险：仓库 Actions 设置必须持续允许 `GITHUB_TOKEN` 具有内容写入权限，自动提交才可在结构变化后推送。

## 2026-08-02｜导入机器狗上位机源码

- 状态：改动完成
- 目标：从机器狗上位机识别并导入可公开保存的源码到本仓库对应目录。
- 影响文件：`archive/preliminary-code/xgo-cm5/`、`archive/preliminary-code/oumax-xgo/`、`archive/preliminary-code/README.md`。
- 实施记录：从 `/home/pi/RaspberryPi-CM5/common/`、`robots/Dog_LM/` 与 `/home/pi/oumax-xgo/` 导入并复核；未导入 ROS 工作区，因为设备未安装 ROS 且远程不存在 ROS 包。初次筛选与预推送复核共剔除六份含硬编码云服务凭据的语音示例，并移除 IDE、打包和模型产物；最终快照为 274 个文件、约 2.9 MiB。
- 验证：逐文件大小校验和 Python 语法检查完成；二次凭据扫描无命中；未保留虚拟环境、构建目录、模型、密钥文件或长凭据字面量。
- 遗留风险：快照依赖设备上的专有运行时、模型与硬件接口，不能在当前 Windows 环境或未安装 ROS 的设备上直接构建运行。

## 2026-08-02｜创建机器狗全量源码快照

- 状态：改动完成
- 目标：在独立目录中保存机器狗的全部非系统用户/厂商/服务源码。
- 影响文件：`archive/full-device-source/`、`archive/full-device-source/SHA256SUMS.tsv`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：从 `/home/pi/` 导入所有可识别的应用与厂商源码，并导入 7 份引用这些程序的自定义 systemd 服务定义；经预推送复核后，完整筛选快照为 590 文件、6,529,017 字节。
- 验证：590 个清单条目的文件大小和 SHA-256 摘要全部一致；二次凭据字面量与敏感文件名扫描无命中；Python 源码语法解析通过。
- 遗留风险：自动剔除了 27 份含凭据的源码/配置、8 个超过 5 MiB 的文件、3,699 个非源码运行文件，以及打包元数据和模型文件。该目录不是整个 Debian 根文件系统，且依赖专有运行时、模型与硬件，不能在当前 Windows 环境直接运行。

## 2026-08-02｜创建机器狗 ROS 功能包

- 状态：改动完成
- 目标：在机器狗的 ROS Noetic Docker 工作区创建可构建的最小功能包，并同步至本仓库。
- 影响文件：`catkin_ws/src/CMakeLists.txt`、`catkin_ws/src/robot_dog_bringup/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：在机器狗的 `ros-noetic` 容器工作区创建 `robot_dog_bringup`，实现只读系统状态发布节点、launch 文件、构建规则、许可证与使用说明；将 6 个包源码文件按 SHA-256 一致性校验同步到本仓库。为本地检出提供可用的 Catkin 顶层 `CMakeLists.txt`，避免复制只能在容器内解析的绝对符号链接；同时更新部署后的存储、Docker、ROS 和功能包实机信息。
- 验证：容器内 `catkin_make` 构建成功；功能包依赖可解析；`roslaunch robot_dog_bringup robot_dog_bringup.launch` 已启动节点并在 `/robot_dog_bringup/status` 收到主机名、内核与 ROS 发行版状态消息；同步前后 6 个包源码文件的 SHA-256 摘要一致。
- 遗留风险：ROS Noetic 已结束常规支持，镜像基于 Ubuntu Focal；容器使用宿主网络与 IPC，后续接入不受信任的 ROS 节点前应限制 ROS 网络边界。功能包当前不含任何硬件控制逻辑。

## 2026-08-02｜机器狗雷达启动探测

- 状态：改动完成
- 目标：在不发送底盘、舵机或串口控制命令的前提下，为已确认的雷达驱动提供 ROS 启动与 `/scan` 数据验证入口。
- 影响文件：`catkin_ws/src/robot_dog_lidar/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：通过机器随附 SDK、CP2102 的 USB ID、厂商程序配置和设备返回信息确认 YDLIDAR Tmini Plus；新增 `robot_dog_lidar` C++ 节点，使用随附 SDK 的 Unix 源码在 Noetic 容器内构建，发布 `/scan`。容器仅映射当前雷达节点为 `/dev/ydlidar`，并只读挂载 SDK 源码；节点硬编码该容器路径，未映射或访问底盘 `ttyAMA0`，默认以墙钟限时 10 秒且退出时关闭雷达。
- 验证：容器内 `catkin_make` 成功构建供应商 SDK 静态库和节点；独立代码复核确认端口不可被 launch 覆盖、限时不受仿真时间影响；实机启动后收到有效 `sensor_msgs/LaserScan`，设备返回 Tmini Plus、230400、10 Hz，并在限时结束后记录“scanning has stopped”；测试结束后未发现残留 ROS 或雷达进程。
- 遗留风险：容器设备映射的宿主来源是当前 `/dev/ttyUSB0`；如 USB 枚举变化，节点会安全失败，但需在重新启动前重新确认稳定枚举名与映射。供应商 SDK 编译存在既有格式和宏重定义警告，当前构建与实测不受影响。
