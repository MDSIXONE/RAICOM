#!/usr/bin/env python3
"""Generate the RViz occupancy grid from the shared arena dimensions."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena_geometry import (  # noqa: E402
    FIELD_HEIGHT_M,
    FIELD_WIDTH_M,
    RECOGNITION_BOX_SIZE_M,
    RECOGNITION_BOXES,
    SIDE_BOX_CENTER_M,
    SIDE_BOX_SIZE_M,
    WALL_THICKNESS_M,
)

RESOLUTION_M = 0.01


def world_to_pixel(x_m, y_m, width_px, height_px):
    px = int(round((x_m + FIELD_WIDTH_M / 2.0) / RESOLUTION_M))
    py = int(round((FIELD_HEIGHT_M / 2.0 - y_m) / RESOLUTION_M))
    return px, py


def fill_rect(pixels, width_px, height_px, x_min, x_max, y_min, y_max, value):
    left, top = world_to_pixel(x_min, y_max, width_px, height_px)
    right, bottom = world_to_pixel(x_max, y_min, width_px, height_px)
    left = max(0, min(width_px - 1, left))
    right = max(0, min(width_px - 1, right))
    top = max(0, min(height_px - 1, top))
    bottom = max(0, min(height_px - 1, bottom))
    for row in range(top, bottom + 1):
        offset = row * width_px
        for col in range(left, right + 1):
            pixels[offset + col] = value


def generate(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    width_px = int(round(FIELD_WIDTH_M / RESOLUTION_M))
    height_px = int(round(FIELD_HEIGHT_M / RESOLUTION_M))
    pixels = bytearray([254] * (width_px * height_px))

    wall = WALL_THICKNESS_M
    fill_rect(pixels, width_px, height_px, -1.5, 1.5, 1.25 - wall, 1.25, 0)
    fill_rect(pixels, width_px, height_px, -1.5, 1.5, -1.25, -1.25 + wall, 0)
    fill_rect(pixels, width_px, height_px, -1.5, -1.5 + wall, -1.25, 1.25, 0)
    fill_rect(pixels, width_px, height_px, 1.5 - wall, 1.5, -1.25, 1.25, 0)

    half_box = RECOGNITION_BOX_SIZE_M / 2.0
    for x_m, y_m in RECOGNITION_BOXES:
        fill_rect(
            pixels,
            width_px,
            height_px,
            x_m - half_box,
            x_m + half_box,
            y_m - half_box,
            y_m + half_box,
            0,
        )

    side_x, side_y, _side_z = SIDE_BOX_CENTER_M
    side_size_x, side_size_y, _side_size_z = SIDE_BOX_SIZE_M
    fill_rect(
        pixels,
        width_px,
        height_px,
        side_x - side_size_x / 2.0,
        side_x + side_size_x / 2.0,
        side_y - side_size_y / 2.0,
        side_y + side_size_y / 2.0,
        0,
    )

    pgm_path = output_dir / "ricam_arena.pgm"
    with pgm_path.open("wb") as stream:
        stream.write(f"P5\n{width_px} {height_px}\n255\n".encode("ascii"))
        stream.write(pixels)

    yaml_path = output_dir / "ricam_arena.yaml"
    yaml_path.write_text(
        "image: ricam_arena.pgm\n"
        f"resolution: {RESOLUTION_M:.2f}\n"
        "origin: [-1.500, -1.250, 0.000]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n",
        encoding="utf-8",
    )
    print(f"Generated {pgm_path} and {yaml_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "maps",
    )
    args = parser.parse_args()
    generate(args.output_dir.resolve())


if __name__ == "__main__":
    main()
