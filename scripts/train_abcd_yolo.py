#!/usr/bin/env python3
"""训练地图 A/B/C/D 字母检测的 YOLOv8 模型，导出 ONNX 供机器端推理。

用法（在仓库根目录运行）：
    python scripts/train_abcd_yolo.py

前提：
    1. datasets/yolo/abcd/images/train、images/val 已放好标注过的图片
    2. 每张图有对应的 labels/train、labels/val 下同名 .txt（YOLO 格式）
    3. 本机已安装 ultralytics（pip install ultralytics）
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_YAML = REPO_ROOT / "datasets/yolo/abcd/data.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="yolov8n.pt", help="预训练权重或已有训练权重")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--project", default=str(REPO_ROOT / "runs/abcd"))
    parser.add_argument("--name", default="train")
    args = parser.parse_args()

    if not DATA_YAML.exists():
        raise FileNotFoundError(f"缺少数据集配置: {DATA_YAML}")

    model = YOLO(args.model)
    model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=0,
        cache="disk",
        workers=4,
    )
    best = Path(args.project) / args.name / "weights/best.pt"
    if best.exists():
        YOLO(str(best)).export(format="onnx", imgsz=args.imgsz, opset=12, dynamic=False)
        print(f"done: {best} -> {best.with_suffix('.onnx')}")


if __name__ == "__main__":
    main()
