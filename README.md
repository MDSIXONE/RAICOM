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

项目目前处于初始化阶段，ROS 工作空间、功能包、启动文件和测试目录尚未建立。后续建议采用标准 Catkin 工作空间结构，例如：

```text
catkin_ws/
├── src/
│   ├── perception/
│   ├── navigation/
│   ├── motion_control/
│   └── mission_manager/
└── README.md
```

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
