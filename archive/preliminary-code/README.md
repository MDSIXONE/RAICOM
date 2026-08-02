# 机器狗上位机源码快照

本目录保存从当前机器狗 CM5 上位机拉取的非 ROS 源码快照，作为接口和行为研究的只读基线；不能直接视为本项目的 ROS Noetic 功能包。

## 目录来源

| 本地目录 | 远程来源 | 内容 |
| --- | --- | --- |
| `xgo-cm5/common/` | `/home/pi/RaspberryPi-CM5/common/` | CM5 公共程序与演示代码 |
| `xgo-cm5/robots/Dog_LM/` | `/home/pi/RaspberryPi-CM5/robots/Dog_LM/` | 当前机器狗对应的 Dog_LM 演示与控制代码 |
| `oumax-xgo/` | `/home/pi/oumax-xgo/` | 机器本地的 TCP、手动控制和 MJPEG 服务 |

## 导入范围

本次只导入文本源码、构建说明和不含凭据的配置。未导入 Python 虚拟环境、模型、音视频、日志、PID、缓存、构建产物、Git 元数据及含凭据配置。

初次导入与预推送复核共发现六份云语音示例内嵌 API 密钥、令牌或应用标识，已从快照剔除；请不要从设备再次复制这些原文件到仓库。需要使用该类服务时，应以本机私有环境变量或 Git 忽略的配置文件提供凭据。

## 后续接入

将功能迁移到比赛项目时，应先提炼接口与依赖，再在 `catkin_ws/src/` 中新建 ROS Noetic 包；不要把此目录直接放入 Catkin 工作区。
