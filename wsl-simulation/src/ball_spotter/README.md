# ball_spotter

实时检测红 / 蓝 / 绿球的位置，把检测结果打印到终端。基于 YOLOv8 导出的 ONNX 模型，运行时不依赖 ROS 和 PyTorch，只依赖 OpenCV + onnxruntime，适配树莓派 CM5 纯 CPU 环境（Python 3.8）。

## 依赖

```bash
pip install onnxruntime
# OpenCV 需已安装（Ubuntu: sudo apt install python3-opencv）
```

## 用法

```bash
python3 scripts/ball_detector.py --model path/to/model.onnx
```

实机（机器狗）默认从 `http://127.0.0.1:8090/stream.mjpg`（OUMAX Picamera2 MJPEG 流）读取画面。

### 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--model` | 必填 | ONNX 模型路径 |
| `--source` | `http://127.0.0.1:8090/stream.mjpg` | 视频源（MJPEG URL 或摄像头设备号，如 `0`） |
| `--conf` | `0.25` | 置信度阈值 |
| `--iou` | `0.45` | NMS IoU 阈值 |
| `--imgsz` | `416` | 推理输入尺寸（实机 CPU 建议 416） |
| `--names` | `red_ball,blue_ball,green_ball` | 类别名（与训练顺序一致） |
| `--classes` | 无 | 只输出指定类别索引，如 `--classes 0 2` |
| `--max-frames` | `0` | 跑 N 帧后退出（0 = 无限） |
| `--no-show` | 关 | 纯终端模式，不弹 cv2 窗口（实机无显示时使用） |

### 终端输出

```
[13:45:01.234] frame 42: 2 balls
  red_ball   center=(320,180)  size=45x38  conf=0.87
  blue_ball  center=(128,200)  size=30x28  conf=0.62
```

无检测时每 5 秒打印一次状态行。退出时打印统计（总帧数、有检测帧数、平均推理耗时）。

### 实机运行

```bash
# 机器狗上（容器内），有显示时：
python3 scripts/ball_detector.py --model models/best.onnx
# 无显示时：
python3 scripts/ball_detector.py --model models/best.onnx --no-show
```

按 `q` 或 `Esc` 退出；Ctrl-C 也可安全退出。

## 测试

```bash
python3 -m unittest discover -s test -v
```

纯 numpy 单测，不依赖 OpenCV / onnxruntime 即可运行。
