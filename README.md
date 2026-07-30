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
- `docs/ai-records/`：跨对话的代码改动、犯错和失败方案记录。
- `README.md`：项目简介和快速入口。

## 目录结构

项目目录按开发、仿真、训练和资料分离：

```text
RAICOM/
├── catkin_ws/src/              # 机器狗 ROS 源码包（后续放 perception、navigation 等）
├── wsl-simulation/             # WSL Ubuntu 20.04 中运行的仿真工程与配置
├── blender-maps/               # 比赛场地地图的 Blender 源文件
├── datasets/
│   ├── yolo/                   # YOLO 视觉训练数据集
│   └── ocr/                    # OCR 训练数据集
├── tmp/                        # 用户本机临时文件，不提交 Git
├── competition-rules/           # 赛事规则、任务书和官方补充说明
├── docs/
│   ├── technical/              # 技术方案、接口、调试和部署文档
│   └── ai-records/             # AI 跨对话工作记录
├── archive/preliminary-code/   # 已结束的预选赛代码，只读归档
└── robot-information/          # 机器狗型号、接口、标定和设备资料
```

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

## 协作说明

开始开发前请阅读 `AGENTS.md`。编写或修改代码时必须使用子智能体协作，并由主智能体负责整合结果、检查实际差异和验证测试。每次新对话还必须读取 `docs/ai-records/` 中规定的记录；具体写入规则由 `project-memory-records` 技能定义。
