#!/usr/bin/env python3
"""用 EasyOCR 对采集图片自动标注 A/B/C/D 字母，生成 YOLO 格式 txt。

仅保留单字符识别结果为 A/B/C/D 的框；低于置信度的丢弃。
输出 YOLO 归一化格式：class x_center y_center width height。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import easyocr
import numpy as np

ALLOWED = {"A", "B", "C", "D"}
MIN_CONF = 0.5


def imread_unicode(path: Path) -> np.ndarray:
    """cv2.imread 无法处理非 ASCII 路径（如 D:\\睿抗），改用字节读取后解码。"""
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="*", help="图片目录或图片列表")
    parser.add_argument("--conf", type=float, default=MIN_CONF)
    parser.add_argument("--no-cuda", action="store_true")
    args = parser.parse_args()

    paths = [Path(p) for p in args.images]
    if len(paths) == 1 and paths[0].is_dir():
        paths = sorted(paths[0].glob("*.jpg"))
    if not paths:
        sys.exit("no images")

    reader = easyocr.Reader(
        ["en"],
        gpu=not args.no_cuda,
        model_storage_directory=str(Path.home() / ".easyocr" / "model"),
        download_enabled=True,
    )

    labeled = 0
    for path in paths:
        image = imread_unicode(path)
        if image is None:
            raise FileNotFoundError(f"cannot read image: {path}")
        height, width = image.shape[:2]
        results = reader.readtext(
            image, detail=1, paragraph=False, batch_size=8, allowlist="ABCD"
        )
        boxes = []
        for bbox, text, conf in results:
            if text not in ALLOWED or conf < args.conf:
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            boxes.append((text, x_min, y_min, x_max, y_max))
        if boxes:
            lines = []
            for text, x1, y1, x2, y2 in boxes:
                cx = ((x1 + x2) / 2) / width
                cy = ((y1 + y2) / 2) / height
                w = (x2 - x1) / width
                h = (y2 - y1) / height
                lines.append(f"{'ABCD'.index(text)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            path.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            labeled += 1
        print(f"{path.name}: {len(boxes)} boxes", flush=True)

    print(f"done: {labeled}/{len(paths)} images labeled")


if __name__ == "__main__":
    main()
