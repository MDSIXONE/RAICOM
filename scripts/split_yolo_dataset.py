#!/usr/bin/env python3
"""把采集并标注完的图片按比例随机切分为 train/val。

用法（在仓库根目录运行）：
    python scripts/split_yolo_dataset.py

前提：
    1. datasets/yolo/abcd/images/ 下是全部采集图片
    2. 每张图旁边已有同名 .txt（labelImg 保存的 YOLO 标注）
    3. 运行后图片与标注按比例移入 images/train、labels/train 与 images/val、labels/val
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets/yolo/abcd"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratio", type=float, default=0.9, help="train 占比")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    images = sorted((DATASET / "images").glob("*.jpg"))
    if not images:
        raise FileNotFoundError(f"{DATASET / 'images'} 下没有图片")

    random.Random(args.seed).shuffle(images)
    split_at = int(len(images) * args.ratio)
    for subset in ("train", "val"):
        (DATASET / "images" / subset).mkdir(parents=True, exist_ok=True)
        (DATASET / "labels" / subset).mkdir(parents=True, exist_ok=True)

    for index, image in enumerate(images):
        label = image.with_suffix(".txt")
        if not label.exists():
            raise FileNotFoundError(f"缺少标注: {label}（请先用 labelImg 标注再切分）")
        subset = "train" if index < split_at else "val"
        image.rename(DATASET / "images" / subset / image.name)
        label.rename(DATASET / "labels" / subset / label.name)

    print(
        f"done: {len(images)} 张 -> train {split_at} / val {len(images) - split_at}，"
        f"data.yaml 已指向 images/train 与 images/val"
    )


if __name__ == "__main__":
    main()
