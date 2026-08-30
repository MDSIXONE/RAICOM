# robot_dog_demos

厂商 XGO 示例程序集合包：Mini3W_W 机型 demos + common 通用示例。脚本为厂商原版
（仅复制入库，零代码改动），非 ROS 节点，统一在机器端 `ros-noetic` Docker 容器内
运行（与导航同一容器，不再宿主机/容器割裂）。

## 包内容清单

**scripts/ 顶层（Mini3W_W 机型 demos，12 个）**

| 程序 | 说明 |
| --- | --- |
| `ball.py` | 球类演示 |
| `color.py` | 颜色识别演示 |
| `dog_Joystick.py` | 手柄操控 |
| `dog_show.py` | 动作展示 |
| `face_decetion.py` | 人脸检测 |
| `face_mask.py` | 口罩检测 |
| `group.py` | 编队演示 |
| `hands.py` | 手势识别 |
| `hp.py` | 挥手检测 |
| `pose_dog.py` | 姿态检测 |
| `shijiao_UDP.py` | 视角/遥控 UDP 版 |
| `shijiao.py` | 视角/遥控 |

**scripts/common/（common 通用示例，13 个）**

`device.py`、`face.py`、`face_mask.py`、`fru.py`、`group.py`、`language.py`、
`LLM.py`、`network_app.py`、`qrcode.py`、`receiver_workflow.py`、
`run_blockly.py`、`volume.py`、`wifi_set.py`

**scripts/ 子目录（保持厂商目录结构）**

| 目录 | 内容 |
| --- | --- |
| `follow_person/` | `follow_person.py`、`track.py`（跟随行人） |
| `speech/` | 语音相关 8 个 py + `volcengine_binary_demo/`（火山引擎二进制协议：`protocols/`、`setup.py`、`pyproject.toml`） |
| `face_classification/` | 开源人脸分类项目（含 `src/` 完整结构 + Dockerfile/LICENSE/README.md/REQUIREMENTS.txt） |

## 来源与剔除策略

- 来源：`archive/full-device-source/home-pi/RaspberryPi-CM5/robots/Mini3W_W/demos/`
  与 `archive/full-device-source/home-pi/RaspberryPi-CM5/common/demos/`
  （08-02 全量设备源码快照），逐文件 SHA-256 校验与源一致。
- `follow_line.py`：**不入本包**，已在 `robot_dog_follow_line` 独立包中。
- `YDLidar-SDK/`：C++ 雷达 SDK 工程，**不入本包**，已由 `robot_dog_lidar` 包使用。
- `xiaozhi_test/`：小智语音测试子项目（体积大、与比赛无关），**不入本包**。
- common 下的 `mcp_server/`、`realtime_dialog/`、`WIFI/`、`AI_gym/`、`sample/`、
  `src/`：云服务/重依赖子项目，**不入本包**。
- 说明：任务清单中的 Mini3W_W `sample/` 目录在快照中实际不存在
  （`sample/` 仅见于 Rider_R 机型 demos），故无文件可复制。

## 运行环境

统一在机器端 `ros-noetic` Docker 容器内运行（容器挂载 `/home/pi` 后厂商
`xgovenv` 同路径可用），依赖：

- `picamera2`、`cv2`、`numpy`
- `uiutils`、`xgolib`、`xgoscreen`（厂商库）

容器需挂载 `/home/pi` 并直通 `/dev/ttyAMA0`（串口）与 `/dev/video0`（相机），
详见 `docs/technical/2026-08-16-docker-runtime-unification.md`。厂商 `xgovenv`
为唯一可用运行时；系统 Python 缺少 `uiutils`/`xgolib`，不可用。

## 部署与运行

```bash
# 上传到机器（脚本为机器端独立程序，非 ROS 节点；子目录用 -r）
scp -r scripts/* pi@192.168.137.157:/home/pi/oumax-xgo/

# 容器内运行（推荐封装脚本，默认指向机器上厂商 demos 原版目录）
bash robot-src/catkin_ws/src/robot_dog_demos/host/run_demo_in_docker.sh \
  --release-camera-serial -- ball.py

# 等价手动命令
docker exec ros-noetic /home/pi/RaspberryPi-CM5/xgovenv/bin/python \
  /home/pi/RaspberryPi-CM5/robots/Mini3W_W/demos/ball.py
```

注意：多数示例对相机/串口/屏幕有硬依赖（Picamera2、ttyAMA0、SPI 屏），
容器内运行时部分显示功能可能因设备未直通而不可用（见方案文档 §2.3 检查清单）。

运行前注意：先停占用串口/相机的服务（`raicom-original-main.service` 与
`oumax-camera.service`），避免 xgolib 挂死或 Picamera2 打不开。

## 凭据扫描结论

入库前对所有 56 个 py（含 speech/、LLM.py、network_app.py 及子目录）及
`pyproject.toml`/`setup.py` 执行凭据模式扫描（`sk-`、`api_key`/`secret`/
`token`/`access_key`/`AKID`/`bearer` 后跟长字面量），**零命中**；入库后复跑
同样零命中。shebang 检查：仅 3 个文件带 shebang（`dog_Joystick.py`、
`run_blockly.py` 为 `#!/usr/bin/env python3`，`speech/ringbuffer.py` 为
`#!/usr/bin/python3`），且均已在第 1 行，无需调整；其余文件保持原样。
