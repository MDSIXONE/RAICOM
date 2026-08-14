# robot_dog_ball_grab

本次睿抗国赛抓球任务的代码存放包。`ball_yolo_grab.py` 是机器端独立 YOLO 抓球程序：
厂商硬件接口（`xgolib`/`uiutils`）+ 项目训练的 ONNX 球模型（YOLOv8 导出）。

## 运行环境

程序不在容器内运行，而是在机器端（OUMAX XGO mini3W，树莓派 CM5）宿主机直接运行，依赖：

- `picamera2`、`cv2`、`numpy`、`onnxruntime`（机器端已装）
- `uiutils` 的 `dog` 接口（厂商 `xgolib`，机器端 `/home/pi/RaspberryPi-CM5` 环境）
- ONNX 模型：默认 `/home/pi/ros_ws/models/best.onnx`

## 部署与运行

```bash
# 上传到机器
scp scripts/ball_yolo_grab.py pi@192.168.137.157:/home/pi/oumax-xgo/ball_yolo_grab.py

# 机器端运行（默认只检测，不动作）
python3 ball_yolo_grab.py

# 允许真实运动
python3 ball_yolo_grab.py --enable-motion
```

参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--model` | `/home/pi/ros_ws/models/best.onnx` | ONNX 球检测模型 |
| `--target-radius` | `28.0` | YOLO 框半径达到该像素值后抓取 |
| `--confidence` | `0.60` | 检测置信度阈值 |
| `--enable-motion` | 关 | 显式开启才允许真实运动 |
| `--frames` | `0` | 仅检测 N 帧后退出；0 持续运行 |

## 抓取流程

1. 设定 `slow_trot` 步态 → 低趴（`z=10`、`p=15`、`y=-6`）。
2. 检测球：水平偏差 >25px 转向；框半径小于目标时小步前进。
3. 框半径达标后：后肢抬高（`31=26°、41=25°`）→ 机械臂安全序列
   `51=-65 → 52=-50 → 53=90 → 52=-45 → 51=40 → 53=0 → 52=0` → 车体 yaw 复原。

关节方向标定、安全顺序与低趴姿态详见 `docs/lingo.md`（机械臂关节 / 低趴词条）。

## 相关文件

- `scripts/ball_yolo_grab.py`：机器端独立抓球程序（本包归档副本；历史部署路径
  `/home/pi/oumax-xgo/ball_yolo_grab.py`，仓库内另一副本在
  `robot-src/host-services/oumax-xgo/ball_yolo_grab.py`，两者内容一致）。
- `robot-src/catkin_ws/src/robot_dog_teleop/scripts/ball_align_grab.py`：另一条
  基于手控服务 HTTP 的自动对准夹球方案（ROS launch 方式）。
- 模型：`best.onnx`（项目 YOLO 训练导出，机器端 `/home/pi/ros_ws/models/`）。
