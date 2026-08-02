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
│   └── preliminary-code/
├── blender-maps/
├── catkin_ws/
│   └── src/
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
│   │   ├── horizon-x3/
│   │   └── raspberry-pi-cm4/
│   ├── control/
│   │   └── esp32/
│   └── course-resources/
│       └── max/
├── scripts/
├── technical-reports/
├── tmp/
└── wsl-simulation/
```
<!-- PROJECT_STRUCTURE_TREE:END -->

Blender 地图必须使用本机的 `G:\Blender 5.1` 工具链创建或编辑。WSL 仿真文件位于 `wsl-simulation/`；在默认挂载配置下可通过 `/mnt/g/AICODE/01_PROJECTS/RICAM/wsl-simulation/` 访问。

原始 YOLO/OCR 数据集通常较大，已默认排除在 Git 提交之外；仅提交数据说明、清单或可公开的小型样例。`robot-information/private/` 用于本机敏感资料，也不会提交。

## 快速开始

安装 ROS Noetic 并配置 Catkin 后，在工作空间根目录执行：

```bash
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

当前尚无可启动的 ROS 节点。加入首个功能包后，请在本节补充构建、启动、仿真和硬件连接命令。

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
