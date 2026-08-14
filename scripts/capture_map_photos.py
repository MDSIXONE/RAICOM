#!/usr/bin/env python3
"""从机器狗 Picamera2 MJPEG 流按固定间隔抓帧，保存为 YOLO 训练图片。

运行在 Windows 本机，机器端无需登录：直接读取
http://<机器IP>:8090/stream.mjpg 的 multipart/x-mixed-replace 流，
把每个 JPEG 帧写入指定目录（默认 datasets/yolo/abcd/images/）。
"""

from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path

JPEG_START = b"\xff\xd8"
JPEG_END = b"\xff\xd9"
BOUNDARY = b"FRAME"
CHUNK = 64 * 1024


def iter_jpeg_frames(url: str):
    """从 MJPEG 流中逐个产出完整 JPEG 字节，不依赖 OpenCV。"""
    buffer = b""
    with urllib.request.urlopen(url, timeout=10) as response:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                return
            buffer += chunk
            while True:
                start = buffer.find(JPEG_START)
                if start < 0:
                    break
                end = buffer.find(JPEG_END, start)
                if end < 0:
                    break
                yield buffer[start : end + 2]
                buffer = buffer[end + 2 :]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="抓取机器狗相机流的 JPEG 帧用于 YOLO 标注"
    )
    parser.add_argument("--url", default="http://192.168.137.157:8090/stream.mjpg")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent.parent / "datasets/yolo/abcd/images"),
    )
    parser.add_argument("--interval", type=float, default=1.5, help="两次保存之间的秒数")
    parser.add_argument("--max-count", type=int, default=0, help="最多保存张数，0 表示不限")
    parser.add_argument("--probe", action="store_true", help="只保存一帧验证通路后退出")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    next_save = time.monotonic()
    for frame in iter_jpeg_frames(args.url):
        now = time.monotonic()
        if args.probe and saved == 0:
            path = output_dir / "probe.jpg"
            path.write_bytes(frame)
            print(f"probe: {path} ({len(frame)} bytes)")
            return
        if now < next_save:
            continue
        path = output_dir / f"map_{saved + 1:04d}.jpg"
        path.write_bytes(frame)
        saved += 1
        print(f"saved {saved}: {path.name}")
        next_save = now + args.interval
        if args.max_count and saved >= args.max_count:
            break

    print(f"done: {saved} frames in {output_dir}")


if __name__ == "__main__":
    main()
