# 睿抗机器人大赛智能配送项目

本项目用于开发睿抗机器人大赛智能配送赛道的参赛程序。机器人平台为机器狗，开发与运行环境以本机 Ubuntu 20.04 和 ROS Noetic 为准。

## 项目目标

围绕智能配送任务，逐步实现机器狗的环境感知、自主定位、路径规划、运动控制、任务调度和异常处理。具体功能与目录会随着比赛方案和代码实现持续补充。

## 开发环境

- 操作系统：Ubuntu 20.04 LTS
- ROS 版本：ROS Noetic Ninjemys
- 硬件平台：机器狗
- 工作方式：优先在本机完成开发、调试和验证

新增依赖时，请同步记录安装方式、版本和必要配置，避免开发环境不一致。

## 当前内容

- `MODEL_ROUTING.md`：GPT-5.6 子模型路由、风险分级和任务执行规范。
- `AGENTS.md`：仓库贡献规范及智能体协作要求。
- `.agents/skills/project-memory-records/`：随仓库同步的 AI 工作记录技能。
- `technical-reports/`：技术报告、阶段总结和赛后复盘。
- `docs/ai-records/`：跨对话的代码改动、犯错和失败方案记录。
- `competition-rules/`：赛事规则 PDF 及 [规则摘要](competition-rules/2026睿抗国赛规则-物流配送挑战赛-足式4.2-摘要.md)。
- `robot-information/`：机器狗统一平台约束、上位机/摄像头/下位机参考资料及下载清单。
- `README.md`：项目简介和快速入口。

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
├── catkin_ws/
│   └── src/
│       ├── robot_dog_bringup/
│       │   ├── launch/
│       │   └── scripts/
│       ├── robot_dog_lidar/
│       │   ├── launch/
│       │   └── src/
│       ├── robot_dog_navigation/
│       │   ├── config/
│       │   ├── launch/
│       │   ├── maps/
│       │   ├── rviz/
│       │   └── scripts/
│       └── robot_dog_teleop/
│           ├── host/
│           ├── launch/
│           └── scripts/
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
├── scripts/
├── technical-reports/
├── tmp/
└── wsl-simulation/
    └── src/
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

Blender 离线场地的可再生成源位于 `blender-maps/offline_navigation_arena.py`；它会生成
与 ROS 占据栅格地图对应的 `.blend` 场景。当前未在本机找到原先约定的 Blender 工具链，
因此不提交二进制 `.blend`；安装或找回 Blender 后可按该目录的说明生成。WSL 离线导航
文件位于 `wsl-simulation/`，当前仓库在 WSL 中的默认路径为
`/mnt/d/WORK/ALLCODE/RAICOM/`。

原始 YOLO/OCR 数据集通常较大，已默认排除在 Git 提交之外；仅提交数据说明、清单或可公开的小型样例。`robot-information/private/` 用于本机敏感资料，也不会提交。

## 本地离线导航（WSL）

本机 WSL 已配置 Ubuntu 20.04 + ROS Noetic。下面的流程会在 WSL 自己的 ext4 工作区
`~/raicom_ws` 构建，源码保持在本仓库；实机雷达包因依赖机器狗容器内的供应商 SDK 而被
明确排除。

```bash
cd /mnt/d/WORK/ALLCODE/RAICOM
bash wsl-simulation/setup_offline_navigation.sh
bash wsl-simulation/start_offline_navigation.sh
```

启动入口强制使用 `ROS_MASTER_URI=http://127.0.0.1:11311`、`ROS_IP=127.0.0.1` 和
`ROS_LOCALHOST_ONLY=1`；它只启动静态地图、模拟 `/scan` 与 `/lidar_points`、官方
`move_base + global_planner/GlobalPlanner` 和 RViz，绝不连接或改动 smartcar / 机器狗
的 ROS Master。RViz 默认显示雷达点云、静态地图和
`/move_base/global_costmap/costmap`。详情和无界面验收命令见 `wsl-simulation/README.md`。

## 提交规范

提交标题统一使用“Emoji + 范围 + 中文动作”：

```text
🤖 ROS：新增机器狗底盘控制包
🧭 导航：优化目标点路径规划
👁️ 视觉：补充 YOLO 标注说明
🗺️ 地图：更新 Blender 比赛场地
🐛 修复：处理相机启动失败
📚 文档：补充赛事规则解读
```

每个提交只处理一组相关改动。GitHub 会在文件或文件夹右侧显示其最近相关提交的标题，因此这些中文 Emoji 会自然呈现在仓库列表中。已推送的历史不应仅为美化而重写。

## 协作说明

开始开发前请阅读 `AGENTS.md`。编写或修改代码时必须使用子智能体协作，并由主智能体负责整合结果、检查实际差异和验证测试。AI 工作记录统一由项目技能 `project-memory-records` 管理。
