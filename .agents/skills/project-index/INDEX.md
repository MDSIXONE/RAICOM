# RAICOM 睿抗机器人大赛智能配送项目 结构索引

- 更新时间：2026-08-15

## 总体结构
```
RAICOM/
├── .agents/skills/            # 随仓库同步的 AI 技能（工作记录、提交规范、本索引）
├── .github/workflows/         # CI：update-project-tree.yml 自动更新 README 结构树
├── archive/                   # 设备源码快照与历史归档（只读参考）
│   ├── full-device-source/    # 完整设备源码快照（home-pi/oumax-xgo、RaspberryPi-CM5、systemd）
│   └── preliminary-code/      # 初赛代码（oumax-xgo、xgo-cm5 机器人系列）
├── blender-maps/              # 离线场地：Blender 可再生成源 + ROS 地图
│   ├── offline_navigation_arena.py   # 生成 .blend 场地的脚本
│   └── ricam_arena/           # blender/（.blend）、gazebo/（world+obj）、navigation/（pgm+yaml 地图）
├── competition-rules/         # 赛事规则（2026 睿抗国赛物流配送足式 4.2 PDF + 摘要）
├── datasets/                  # YOLO/OCR 数据集说明与小型样例（大数据默认不入库）
│   ├── ocr/
│   └── yolo/
├── docs/                      # 跨对话记录与技术文档
│   ├── ai-records/            # AI 工作记录（CHANGE_LOG、FAILED_APPROACHES、MISTAKE_INDEX、mistakes/）
│   └── technical/             # 技术文档（待补充）
├── robot-information/         # 机器狗平台资料与硬件参考
│   ├── camera/                # 树莓派摄像头 Module 3 资料
│   ├── compute/               # 树莓派 CM4 资料
│   ├── control/               # ESP32 资料
│   ├── course-resources/      # 课程资源
│   ├── private/               # 本机敏感资料（device-access.md，不入库）
│   └── actual-hardware-observations.md / download-manifest.md / README.md
├── robot-src/                 # ★ 机器端全部源码（唯一机器代码写入区）
│   ├── catkin_ws/src/         # 机器狗 ROS 包（Catkin 工作空间，容器内编译运行；本次比赛任务代码存放地）
│   └── host-services/<device>/ # 机器端非 ROS 常驻服务（如 oumax-xgo/manual_control_server.py）
├── scripts/                   # 仓库辅助脚本（update_readme_tree.py）
├── technical-reports/         # 技术报告、阶段总结、赛后复盘（空）
├── tmp/                       # 临时文件与实验脚本（不入库）
└── wsl-simulation/            # ★ WSL 离线仿真（独立工作区，不进 catkin_ws）
    ├── src/                   # 仿真 ROS 包
    └── *.sh                   # setup/start/verify 离线导航、rviz、本地 rosmaster 脚本
```

## 功能索引

| 功能/模块 | 位置 | 一句话说明 | 详情 |
| --- | --- | --- | --- |
| 赛事规则 | `competition-rules/` | 2026 睿抗国赛物流配送足式 4.2 规则 PDF 与摘要 | - |
| 机器狗 ROS 启动 | `robot-src/catkin_ws/src/robot_dog_bringup` | 整机 bringup 与主 launch、系统状态脚本（system_status.py） | - |
| 雷达驱动 | `robot-src/catkin_ws/src/robot_dog_lidar` | YDLIDAR 只读扫描发布节点（ydlidar_scan_node.cpp） | - |
| 导航 | `robot-src/catkin_ws/src/robot_dog_navigation` | 离线本地导航演示：move_base/costmap/maps/rviz，含 mock 雷达、简单里程计、TF 脚本；`scripts/main_flow.py` 为比赛主流程（定点巡航 5 点 → 抓球放球一键编排） | - |
| 自定义规划 | `robot-src/catkin_ws/src/cym_planner` | 自定义全局规划器（C++，plugin 化，参数 JSON） | - |
| 定位 | `robot-src/catkin_ws/src/jie_ware` | 激光定位 lidar_loc、雷达滤波、costmap 清理（C++ 节点 + launch） | - |
| 遥操作 | `robot-src/catkin_ws/src/robot_dog_teleop` | 键盘脉冲/物理键盘/pose/机械臂/球对齐抓取等多种遥操作模式 + 宿主机 systemd/handover 部署 | - |
| YOLO 数据采集 | `robot-src/catkin_ws/src/robot_dog_yolo_dataset` | 定时间隔抓图用于 YOLO 数据集（yolo_image_collector.py） | - |
| 地图字母采集训练 | `scripts/capture_map_photos.py` + `datasets/yolo/abcd/` | 从机器狗 8090 流抓帧采集地图照片，YOLO 训练 A/B/C/D（配套 split/train 脚本与工作流文档） | `docs/map-abcd-yolo-workflow.md` |
| 抓球/放球任务 | `robot-src/catkin_ws/src/robot_dog_ball_grab` | 本次抓球/放球任务代码包：ball_yolo_grab.py（YOLO 抓球）、ball_release.py（放球）、rotate.py（180° 旋转）、ball_grab_release.py（抓→转→放一键编排） | - |
| 机器端非 ROS 服务 | `robot-src/host-services/oumax-xgo/manual_control_server.py` | 机器上 /home/pi/oumax-xgo 的手动控制常驻服务（systemd 运行） | - |
| 离线场地地图 | `blender-maps/ricam_arena/navigation/` | 10cm 栅格地图（pgm/yaml/json/png，含编号网格） | - |
| 场地 Gazebo 模型 | `blender-maps/ricam_arena/gazebo/` | arena.world + obj/mtl 模型与预览图 | - |
| Blender 生成脚本 | `blender-maps/offline_navigation_arena.py` | 可再生成与栅格地图对应的 .blend 场地 | - |
| WSL 仿真-场地 | `wsl-simulation/src/ricam_arena_sim` | 仿真场地包（worlds/meshes/maps/launch/QUICK_START） | - |
| WSL 仿真-机器狗模型 | `wsl-simulation/src/mini2_description` | 机器狗 URDF/meshes 描述 | - |
| WSL 仿真-规划 | `wsl-simulation/src/cym_planner` | 仿真侧自定义规划器（含 plugin 声明与测试） | - |
| WSL 仿真-球识别 | `wsl-simulation/src/ball_spotter` | 球体识别模型与脚本 | - |
| WSL 仿真-数据采集 | `wsl-simulation/src/ricam_dataset_capture` | 仿真内数据集采集 | - |
| WSL 仿真-启动脚本 | `wsl-simulation/*.sh` | 离线导航 setup/start/verify、本地 rosmaster、rviz、机器人控制 | - |
| AI 工作记录 | `docs/ai-records/` | 变更日志、犯错索引、失败方案记录（mistakes/） | - |
| 硬件资料 | `robot-information/` | 摄像头/CM4/ESP32 数据手册、课程资源、实机观测、下载清单 | - |
| 历史归档 | `archive/` | 初赛代码与设备完整源码快照（只读） | - |
| 临时实验 | `tmp/` | 实验脚本、测试数据集、ONNX 模型（不入库） | - |

## 关键入口

- 项目说明：`README.md`（含目录职责边界：机器代码只允许写入 `robot-src/catkin_ws/src/` 或 `robot-src/host-services/<device>/`，仿真代码写入 `wsl-simulation/src/`）
- WSL 离线导航：`wsl-simulation/setup_offline_navigation.sh` → `wsl-simulation/start_offline_navigation.sh`
- 机器 ROS 入口：`robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`
- CI 结构树自动更新：`.github/workflows/update-project-tree.yml`（配合 `scripts/update_readme_tree.py`）
