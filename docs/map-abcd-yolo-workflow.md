# 地图 A/B/C/D 字母检测：采集 → 标注 → 训练 → 部署

针对 2026 睿抗国赛物流配送足式组，机器狗需识别包裹识别区的 A/B/C/D 字母。
本流程用机器狗相机实拍地图，训练 YOLOv8 字母检测模型并导出 ONNX 部署回机器。

## 1. 采集（已就绪）

机器端相机流服务已启用（systemd `oumax-camera.service`，端口 8090，640x360）。

```powershell
python scripts/capture_map_photos.py --interval 1 --max-count 3000
```

- 输出目录：`datasets/yolo/abcd/images/`（默认）
- 每秒存一张 `map_XXXX.jpg`，实时打印已存张数
- 采集时让机器狗绕场地走，覆盖 A/B/C/D 四个字母区，近景/远景/斜视角度都要拍
- 拍够了在采集窗口按 `Ctrl+C` 停止

## 2. 标注

用 labelImg（本机已装 1.8.6）打开 `datasets/yolo/abcd/images/`：

```powershell
labelImg datasets/yolo/abcd/images datasets/yolo/abcd/classes.txt
```

`classes.txt` 内容（顺序必须与 data.yaml 的 names 一致）：

```
A
B
C
D
```

- 标注框选字母，标签分别为 A/B/C/D
- 保存格式选 YOLO（默认），生成的 `.txt` 与图片同名同目录
- 建议先标几百张，训练一版看效果，再补齐难样本

## 3. 切分 train/val

```powershell
python scripts/split_yolo_dataset.py --ratio 0.9
```

图片与标注按 9:1 随机移入 `images/train|val`、`labels/train|val`。

## 4. 训练

```powershell
python scripts/train_abcd_yolo.py --epochs 100
```

- 用 yolov8n.pt 预训练权重，RTX 4050 上约 20-40 分钟
- 输出：`runs/abcd/train/weights/best.pt`（PyTorch）与 `best.onnx`
- 首轮训练后看 `results.png` 与混淆矩阵，不足则补样本、加 epochs 重训

## 5. 部署到机器狗

```powershell
scp runs\abcd\train\weights\best.onnx pi@192.168.137.157:/home/pi/ros_ws/models/letters.onnx
```

机器端推理参考 `robot-src/host-services/oumax-xgo/ball_yolo_grab.py` 的
letterbox + onnxruntime 模式（模型输入 640x640，RGB888 不交换通道）。

## 数据与脚本位置

| 内容 | 位置 |
| --- | --- |
| 采集图片 | `datasets/yolo/abcd/images/`（不入库） |
| 标注 | `datasets/yolo/abcd/labels/`（不入库） |
| 数据配置 | `datasets/yolo/abcd/data.yaml`（不入库） |
| 采集脚本 | `scripts/capture_map_photos.py` |
| 切分脚本 | `scripts/split_yolo_dataset.py` |
| 训练脚本 | `scripts/train_abcd_yolo.py` |
| 训练输出 | `runs/abcd/`（不入库） |
