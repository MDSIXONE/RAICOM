# 睿抗机器人大赛智能配送项目

本项目用于开发睿抗机器人大赛智能配送赛道的参赛程序。机器人平台为机器狗，基准开发环境为 Ubuntu 20.04 + ROS Noetic。

## 项目目标

围绕智能配送任务，逐步实现机器狗的环境感知、自主定位、路径规划、运动控制、任务调度和异常处理。具体功能与目录会随着比赛方案和代码实现持续补充。

## 开发环境

- 操作系统：Ubuntu 20.04 LTS
- ROS 版本：ROS Noetic Ninjemys
- 硬件平台：机器狗
- 工作方式：优先在本地完成开发、调试和验证

新增依赖时，请同步记录安装方式、版本和必要配置，避免开发环境不一致。

## 当前内容


- `AGENTS.md`：仓库贡献规范及智能体协作要求。
- `.agents/skills/project-memory-records/`：随仓库同步的 AI 工作记录技能。
- `technical-reports/`：技术报告、阶段总结和赛后复盘。
- `docs/ai-records/`：跨对话的代码改动、犯错和失败方案记录。
- `competition-rules/`：赛事规则 PDF 及 [规则摘要](competition-rules/2026睿抗国赛规则-物流配送挑战赛-足式4.2-摘要.md)。
- `robot-information/`：机器狗统一平台约束、上位机/摄像头/下位机参考资料及下载清单。

## 目录结构

项目目录按开发、仿真、训练和资料分离。下方结构树由 GitHub Actions 自动生成：

<!-- PROJECT_STRUCTURE_TREE:START -->
```text
项目根目录/
├── archive/
│   ├── full-device-source/
│   │   ├── home-pi/
│   │   │   ├── oumax-xgo/
│   │   │   └── RaspberryPi-CM5/
│   │   │       ├── common/
│   │   │       │   ├── demos/
│   │   │       │   │   ├── AI_gym/
│   │   │       │   │   ├── mcp_server/
│   │   │       │   │   ├── realtime_dialog/
│   │   │       │   │   ├── sample/
│   │   │       │   │   ├── src/
│   │   │       │   │   └── WIFI/
│   │   │       │   ├── language/
│   │   │       │   └── volume/
│   │   │       ├── robots/
│   │   │       │   ├── Dog_LM/
│   │   │       │   │   ├── demos/
│   │   │       │   │   │   ├── face_classification/
│   │   │       │   │   │   │   └── src/
│   │   │       │   │   │   │       ├── utils/
│   │   │       │   │   │   │       └── web/
│   │   │       │   │   │   ├── follow_person/
│   │   │       │   │   │   ├── speech/
│   │   │       │   │   │   │   └── volcengine_binary_demo/
│   │   │       │   │   │   │       └── protocols/
│   │   │       │   │   │   ├── xiaozhi_test/
│   │   │       │   │   │   │   ├── config/
│   │   │       │   │   │   │   └── src/
│   │   │       │   │   │   │       ├── audio_codecs/
│   │   │       │   │   │   │       ├── audio_processing/
│   │   │       │   │   │   │       ├── constants/
│   │   │       │   │   │   │       ├── iot/
│   │   │       │   │   │   │       │   └── things/
│   │   │       │   │   │   │       ├── network/
│   │   │       │   │   │   │       └── utils/
│   │   │       │   │   │   └── YDLidar-SDK/
│   │   │       │   │   │       ├── core/
│   │   │       │   │   │       │   ├── base/
│   │   │       │   │   │       │   ├── common/
│   │   │       │   │   │       │   ├── json/
│   │   │       │   │   │       │   ├── math/
│   │   │       │   │   │       │   ├── network/
│   │   │       │   │   │       │   └── serial/
│   │   │       │   │   │       │       └── impl/
│   │   │       │   │   │       │           ├── unix/
│   │   │       │   │   │       │           └── windows/
│   │   │       │   │   │       ├── csharp/
│   │   │       │   │   │       │   └── examples/
│   │   │       │   │   │       ├── doc/
│   │   │       │   │   │       │   ├── FAQs/
│   │   │       │   │   │       │   ├── howto/
│   │   │       │   │   │       │   ├── quickstart/
│   │   │       │   │   │       │   └── tutorials/
│   │   │       │   │   │       ├── examples/
│   │   │       │   │   │       ├── python/
│   │   │       │   │   │       │   ├── examples/
│   │   │       │   │   │       │   └── test/
│   │   │       │   │   │       ├── src/
│   │   │       │   │   │       │   └── filters/
│   │   │       │   │   │       ├── startup/
│   │   │       │   │   │       └── test/
│   │   │       │   │   └── flacksocket/
│   │   │       │   │       ├── static/
│   │   │       │   │       └── templates/
│   │   │       │   ├── Mini3W_W/
│   │   │       │   │   ├── demos/
│   │   │       │   │   │   ├── face_classification/
│   │   │       │   │   │   │   └── src/
│   │   │       │   │   │   │       ├── utils/
│   │   │       │   │   │   │       └── web/
│   │   │       │   │   │   ├── follow_person/
│   │   │       │   │   │   ├── speech/
│   │   │       │   │   │   │   └── volcengine_binary_demo/
│   │   │       │   │   │   │       └── protocols/
│   │   │       │   │   │   ├── xiaozhi_test/
│   │   │       │   │   │   │   ├── config/
│   │   │       │   │   │   │   └── src/
│   │   │       │   │   │   │       ├── audio_codecs/
│   │   │       │   │   │   │       ├── audio_processing/
│   │   │       │   │   │   │       ├── constants/
│   │   │       │   │   │   │       ├── iot/
│   │   │       │   │   │   │       │   └── things/
│   │   │       │   │   │   │       ├── network/
│   │   │       │   │   │   │       └── utils/
│   │   │       │   │   │   └── YDLidar-SDK/
│   │   │       │   │   │       ├── core/
│   │   │       │   │   │       │   ├── base/
│   │   │       │   │   │       │   ├── common/
│   │   │       │   │   │       │   ├── json/
│   │   │       │   │   │       │   ├── math/
│   │   │       │   │   │       │   ├── network/
│   │   │       │   │   │       │   └── serial/
│   │   │       │   │   │       │       └── impl/
│   │   │       │   │   │       │           ├── unix/
│   │   │       │   │   │       │           └── windows/
│   │   │       │   │   │       ├── csharp/
│   │   │       │   │   │       │   └── examples/
│   │   │       │   │   │       ├── doc/
│   │   │       │   │   │       │   ├── FAQs/
│   │   │       │   │   │       │   ├── howto/
│   │   │       │   │   │       │   ├── quickstart/
│   │   │       │   │   │       │   └── tutorials/
│   │   │       │   │   │       ├── examples/
│   │   │       │   │   │       ├── python/
│   │   │       │   │   │       │   ├── examples/
│   │   │       │   │   │       │   └── test/
│   │   │       │   │   │       ├── src/
│   │   │       │   │   │       │   └── filters/
│   │   │       │   │   │       ├── startup/
│   │   │       │   │   │       └── test/
│   │   │       │   │   └── flacksocket/
│   │   │       │   │       ├── static/
│   │   │       │   │       └── templates/
│   │   │       │   └── Rider_R/
│   │   │       │       ├── demos/
│   │   │       │       │   ├── face_classification/
│   │   │       │       │   │   └── src/
│   │   │       │       │   │       ├── utils/
│   │   │       │       │   │       └── web/
│   │   │       │       │   ├── follow_person/
│   │   │       │       │   ├── sample/
│   │   │       │       │   ├── speech/
│   │   │       │       │   │   └── volcengine_binary_demo/
│   │   │       │       │   │       └── protocols/
│   │   │       │       │   └── xiaozhi_test/
│   │   │       │       │       ├── config/
│   │   │       │       │       └── src/
│   │   │       │       │           ├── audio_codecs/
│   │   │       │       │           ├── audio_processing/
│   │   │       │       │           ├── constants/
│   │   │       │       │           ├── iot/
│   │   │       │       │           │   └── things/
│   │   │       │       │           ├── network/
│   │   │       │       │           └── utils/
│   │   │       │       └── flacksocket/
│   │   │       │           ├── static/
│   │   │       │           └── templates/
│   │   │       └── uiutils/
│   │   │           └── src/
│   │   │               └── uiutils/
│   │   └── systemd/
│   └── preliminary-code/
│       ├── oumax-xgo/
│       └── xgo-cm5/
│           ├── common/
│           │   ├── demos/
│           │   │   ├── AI_gym/
│           │   │   ├── mcp_server/
│           │   │   ├── realtime_dialog/
│           │   │   ├── sample/
│           │   │   ├── src/
│           │   │   └── WIFI/
│           │   ├── language/
│           │   └── volume/
│           └── robots/
│               └── Dog_LM/
│                   ├── demos/
│                   │   ├── face_classification/
│                   │   │   └── src/
│                   │   │       ├── utils/
│                   │   │       └── web/
│                   │   ├── follow_person/
│                   │   ├── speech/
│                   │   │   └── volcengine_binary_demo/
│                   │   │       └── protocols/
│                   │   ├── xiaozhi_test/
│                   │   │   ├── config/
│                   │   │   └── src/
│                   │   │       ├── audio_codecs/
│                   │   │       ├── audio_processing/
│                   │   │       ├── constants/
│                   │   │       ├── iot/
│                   │   │       │   └── things/
│                   │   │       ├── network/
│                   │   │       └── utils/
│                   │   └── YDLidar-SDK/
│                   │       ├── core/
│                   │       │   ├── base/
│                   │       │   ├── common/
│                   │       │   ├── json/
│                   │       │   ├── math/
│                   │       │   ├── network/
│                   │       │   └── serial/
│                   │       │       └── impl/
│                   │       │           ├── unix/
│                   │       │           └── windows/
│                   │       ├── csharp/
│                   │       │   └── examples/
│                   │       ├── doc/
│                   │       │   ├── FAQs/
│                   │       │   ├── howto/
│                   │       │   ├── quickstart/
│                   │       │   └── tutorials/
│                   │       ├── examples/
│                   │       ├── python/
│                   │       │   ├── examples/
│                   │       │   └── test/
│                   │       ├── src/
│                   │       │   └── filters/
│                   │       ├── startup/
│                   │       └── test/
│                   └── flacksocket/
│                       ├── static/
│                       └── templates/
├── blender-maps/
│   └── ricam_arena/
│       ├── blender/
│       ├── gazebo/
│       └── navigation/
├── competition-rules/
├── datasets/
│   ├── ocr/
│   └── yolo/
├── docs/
│   ├── ai-records/
│   └── technical/
├── robot-information/
│   ├── camera/
│   │   └── raspberry-pi-camera-module-3/
│   ├── compute/
│   │   └── raspberry-pi-cm4/
│   ├── control/
│   │   └── esp32/
│   └── course-resources/
│       └── max/
├── robot-src/
│   ├── catkin_ws/
│   │   └── src/
│   │       ├── cym_planner/
│   │       │   ├── config/
│   │       │   ├── include/
│   │       │   └── src/
│   │       ├── jie_ware/
│   │       │   ├── launch/
│   │       │   └── src/
│   │       ├── robot_dog_bringup/
│   │       │   ├── launch/
│   │       │   └── scripts/
│   │       ├── robot_dog_lidar/
│   │       │   ├── launch/
│   │       │   └── src/
│   │       ├── robot_dog_navigation/
│   │       │   ├── config/
│   │       │   ├── launch/
│   │       │   ├── maps/
│   │       │   ├── rviz/
│   │       │   └── scripts/
│   │       ├── robot_dog_teleop/
│   │       │   ├── host/
│   │       │   ├── launch/
│   │       │   └── scripts/
│   │       └── robot_dog_yolo_dataset/
│   │           ├── launch/
│   │           └── scripts/
│   └── host-services/
│       └── oumax-xgo/
├── scripts/
├── technical-reports/
├── tmp/
└── wsl-simulation/
    └── src/
        ├── ball_spotter/
        │   ├── launch/
        │   ├── models/
        │   ├── scripts/
        │   └── test/
        ├── cym_planner/
        │   ├── config/
        │   ├── include/
        │   │   └── cym_planner/
        │   ├── src/
        │   └── test/
        ├── mini2_description/
        │   ├── config/
        │   ├── launch/
        │   ├── meshes/
        │   ├── scripts/
        │   ├── test/
        │   └── urdf/
        ├── ricam_arena_sim/
        │   ├── config/
        │   ├── launch/
        │   ├── maps/
        │   ├── meshes/
        │   ├── rviz/
        │   ├── scripts/
        │   ├── test/
        │   └── worlds/
        └── ricam_dataset_capture/
            ├── launch/
            ├── scripts/
            └── test/
```
<!-- PROJECT_STRUCTURE_TREE:END -->

Blender 离线场地的可再生成源位于 `blender-maps/offline_navigation_arena.py`，可生成与 ROS 占据栅格地图对应的 `.blend` 场景；二进制 `.blend` 不纳入版本控制，详见该目录说明。WSL 离线导航见 `wsl-simulation/README.md`。

原始 YOLO/OCR 数据集通常较大，已默认排除在 Git 提交之外；仅提交数据说明、清单或可公开的小型样例。`robot-information/private/` 用于本机敏感资料，也不会提交。

### 目录职责边界

`robot-src/` 是机器源码包裹层，包含机器狗上运行的全部代码：

- `robot-src/catkin_ws/src/`：机器狗 ROS 容器内编译运行的源码包（Catkin 工作空间）。
- `robot-src/host-services/<device>/`：机器端非 ROS 服务源码（如 `oumax-xgo/manual_control_server.py`，对应机器上 `/home/pi/oumax-xgo/`，systemd 服务直接运行）。此类源码独立于 ROS 容器，不属于 `catkin_ws`；修改后需同步部署到机器对应路径。
- `robot-src/catkin_ws/src/<pkg>/host/`：随 ROS 包部署的宿主机 shell 脚本与服务单元（部署到 `/usr/local/sbin/` 或 systemd），是包的部署配套，与 `host-services/` 的机器常驻服务源码区分。
- `wsl-simulation/src/`：WSL 离线仿真的 ROS 源码包，构建在 WSL ext4 工作区，不进 `catkin_ws`。

AI 生成新源码时按上述边界落位：机器相关代码只允许写入 `robot-src/catkin_ws/src/` 或 `robot-src/host-services/<device>/`，仿真代码写入 `wsl-simulation/src/`，禁止在本仓库根目录或其他位置新建源码目录。

## 离线导航仿真（WSL）

离线仿真流程会在 WSL 自己的 ext4 工作区构建，源码保持在本仓库；实机雷达包因依赖机器狗容器内的供应商 SDK 而被排除。在仓库根目录执行：

```bash
bash wsl-simulation/setup_offline_navigation.sh
bash wsl-simulation/start_offline_navigation.sh
```

启动入口强制使用 `ROS_MASTER_URI=http://127.0.0.1:11311`、`ROS_IP=127.0.0.1` 和
`ROS_LOCALHOST_ONLY=1`；它只启动静态地图、模拟 `/scan` 与 `/lidar_points`、官方
`move_base + global_planner/GlobalPlanner` 和 RViz，不连接或改动实机 ROS Master。
RViz 默认显示雷达点云、静态地图和
`/move_base/global_costmap/costmap`。详情和无界面验收命令见 `wsl-simulation/README.md`。


