# 自动对准夹球程序指令文档

本文档说明 `robot_dog_teleop` 包中 `ball_align_grab.py` 的自动流程：机器趴下 → 视觉
对准球心 → 放臂夹球。它复用已部署的 OUMAX 手控服务（`127.0.0.1:8765`）、Picamera2
MJPEG 流（`127.0.0.1:8090/stream.mjpg`）与 YOLOv8 ONNX 球检测模型
（`best.onnx`）。

## 一、流程概述

程序自动执行三个阶段，全程无需按键：

| 阶段 | 动作 | 说明 |
| --- | --- | --- |
| 1 趴下 | 只设置腿关节 `j1`–`j12` 到夹球姿态 | 机械臂 `j13`–`j15` **保持不动** |
| 2 对准 | 视觉检测球，同步调整四腿髋关节 `j3`/`j6`/`j9`/`j12` 把球水平对准画面中心 | 垂直偏差仅提示，不自动调整；对准完成条件为连续 `good_frames` 帧水平偏差 ≤ `tol_x` |
| 3 夹球 | 爪子张开到最大 → 机械臂到位 → 闭合爪子 | `j13=-65` 张开 → `j14=-72`/`j15=92` → `j13=56` 闭合 |

目标姿态（用户实测夹球姿态）：

```text
j1 -60, j2 40, j3 0, j4 -60, j5 40, j6 0, j7 21, j8 0, j9 0, j10 20, j11 0, j12 0,
j13 56, j14 -72, j15 92
```

## 二、安全前提

- 仅在原厂 UI 已由 `raicom-control-handover` 接管、OUMAX 手控服务健康时运行。
- 首次实机测试须：机器已充电、站稳、四周至少留出 1 m 净空、无人位于运动方向、实体
  急停或断电可达。
- 首次运行前先用 `raicom-launch-pose-keyboard` 手动回中（按 `m`）并目视核对关节方向，
  确认髋关节正负方向后再跑本程序。
- 禁止同时启动其他手柄、APP、raw-XGO、键盘控制或串口控制程序。
- 球须放在机器前方视野内（趴下后摄像头可见的位置），且机器与球的相对距离应使球落在
  画面垂直中心附近；垂直偏差过大时程序只提示、不自动移动，需人工调整位置。
- 髋关节对准有方向保护：连续 `max_worsen` 次步进偏差未减小时程序自动中止，提示检查
  `yaw_direction` 参数，不会越调越偏。

## 三、启动方式

部署后，在宿主机执行：

```bash
sudo /usr/local/sbin/raicom-launch-ball-align-grab
```

该启动器先接管串口（停止原厂 UI、启动 OUMAX 手控服务并检查健康），再进入 ROS 容器
运行 `roslaunch robot_dog_teleop ball_align_grab.launch enable_motion:=true`。退出时
自动恢复原厂 UI。Ctrl-C 可在任意阶段中止（节点退出即不再发送命令，舵机保持当前
角度）。

launch 参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_motion` | 无默认（必填） | 必须显式设为 `true` 才允许真实运动 |
| `model` | `/root/catkin_ws/src/ball_spotter/models/best.onnx` | 球检测 ONNX 模型路径 |
| `stream_url` | `http://127.0.0.1:8090/stream.mjpg` | 摄像头 MJPEG 流 |
| `conf` | `0.5` | 检测置信度阈值 |
| `iou` | `0.45` | NMS IoU 阈值 |
| `names` | `red_ball,blue_ball,green_ball` | 类别名（仅用于日志显示） |
| `classes` | 空 | 只对准指定类别索引（逗号分隔），空则任意球 |
| `tol_x` | `20.0` | 水平对准容差（像素） |
| `tol_y` | `20.0` | 垂直容差（像素），超出仅提示不自动调整 |
| `yaw_step` | `1.0` | 髋关节对准步长（度） |
| `yaw_direction` | `1.0` | 髋关节对准方向；实测方向反时改 `-1` |
| `max_yaw_offset` | `15.0` | 髋关节最大偏移（度），防止过度转向 |
| `joint_delay` | `0.5` | 关节命令间隔（秒） |
| `arm_delay` | `0.6` | 机械臂动作间隔（秒） |
| `align_timeout` | `120.0` | 对准超时（秒），超时中止 |
| `good_frames` | `3` | 连续多少帧水平对准视为完成 |
| `max_worsen` | `3` | 连续多少次步进偏差增大即中止 |

## 四、运行日志

每阶段与每次舵机命令都打印日志，例如：

```text
[INFO] stage 1/3: crouching with legs only (arm untouched)
[INFO] motor j1 -> -60.0 deg
...
[INFO] stage 2/3: aligning to ball center
[INFO] ball red_ball center=(412,178) dx=92 dy=-2 conf=0.87
[INFO] motor j3 -> -1.0 deg
...
[INFO] ball centered: dx=5.0 dy=-1.0
[INFO] stage 3/3: lowering arm and grabbing ball
[INFO] claw open to max (j13=-65.0)
[INFO] arm to grab pose (j14=-72.0, j15=92.0), claw stays open
[INFO] claw close (j13=56.0)
[INFO] ball grabbed: full pose j1=-60 ...
```

## 五、异常与中止

- 未检测到球（超过 `conf`）：每 5 秒警告一次，继续等待；需人工调整机器或球的位置。
- 垂直偏差超过 `tol_y`：警告提示调整机器与球的距离，不自动移动。
- 连续 `max_worsen` 次步进偏差增大：中止并提示检查 `yaw_direction`。
- 超过 `align_timeout` 仍未对准：中止。
- 舵机命令被服务拒绝（网络异常、超时、超范围）：立即中止退出。
- 任一中止后舵机保持最近一次目标角度，需人工干预。

## 六、首次使用清单

- [ ] 机器已充电、站稳，四周净空 ≥ 1 m，急停/断电可达。
- [ ] 已运行 `install_host_handover.sh --cutover`，启动器已安装。
- [ ] 已用姿态键盘程序回中并目视核对髋关节方向。
- [ ] 球已放在机器前方视野内、预期距离处。
- [ ] 执行 `sudo /usr/local/sbin/raicom-launch-ball-align-grab`，观察阶段 1 趴下动作
      无异常。
- [ ] 观察阶段 2 髋关节步进方向：球在画面中心右侧时日志 `dx>0`，若髋关节向错误方向
      调整且程序中止，把 `yaw_direction` 改为 `-1` 重跑。
- [ ] 观察阶段 3 爪子张开 → 臂到位 → 闭合 的完整序列与夹球结果。
- [ ] 完成后按 Ctrl-C 退出，确认原厂 UI 恢复。

## 七、相关文件

- `scripts/ball_align_grab.py`：自动对准夹球节点（不依赖 ROS 话题，仅 HTTP 调服务）。
- `launch/ball_align_grab.launch`：launch 文件与参数。
- `host/launch_ball_align_grab.sh`：宿主机启动器（注册为 `raicom-launch-ball-align-grab`）。
- 检测依赖：`wsl-simulation/src/ball_spotter/`（`letterbox`/`postprocess` 逻辑同源）与
  模型 `best.onnx`。
- `README.md`：包总览。
