#!/usr/bin/env python3
"""Generate a 10 cm vertex-numbered arena map and coordinate JSON."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena_geometry import (  # noqa: E402
    DELIVERY_TARGETS,
    FIELD_HEIGHT_M,
    FIELD_WIDTH_M,
    PICKUP_BALL_X_M,
    PICKUP_ZONE_CENTER_X_M,
    PICKUP_ZONE_CENTER_Y_M,
    RECOGNITION_ZONES,
    RECOGNITION_ZONE_SIZE_X_M,
    RECOGNITION_ZONE_SIZE_Y_M,
)


GRID_SIDE_M = 0.10
PIXELS_PER_SQUARE = 160
LEFT_MARGIN_PX = 110
RIGHT_MARGIN_PX = 110
TOP_MARGIN_PX = 180
BOTTOM_MARGIN_PX = 110

GRID_COLUMNS = int(round(FIELD_WIDTH_M / GRID_SIDE_M))
GRID_ROWS = int(round(FIELD_HEIGHT_M / GRID_SIDE_M))
VERTEX_COLUMNS = GRID_COLUMNS + 1
VERTEX_ROWS = GRID_ROWS + 1
VERTEX_COUNT = VERTEX_COLUMNS * VERTEX_ROWS
SQUARE_COUNT = GRID_COLUMNS * GRID_ROWS

FIELD_WIDTH_PX = GRID_COLUMNS * PIXELS_PER_SQUARE
FIELD_HEIGHT_PX = GRID_ROWS * PIXELS_PER_SQUARE
IMAGE_WIDTH_PX = LEFT_MARGIN_PX + FIELD_WIDTH_PX + RIGHT_MARGIN_PX
IMAGE_HEIGHT_PX = TOP_MARGIN_PX + FIELD_HEIGHT_PX + BOTTOM_MARGIN_PX

DEFAULT_OUTPUT_BASENAME = "ricam_arena_10cm_full_grid_all_numbered"


def rounded_coordinate(value):
    """Return stable decimal metre coordinates without binary float tails."""
    rounded = round(value, 2)
    return 0.0 if rounded == -0.0 else rounded


def vertex_number(row_boundary_from_top, column_boundary_from_left):
    return row_boundary_from_top * VERTEX_COLUMNS + column_boundary_from_left + 1


def vertex_coordinate(row_boundary_from_top, column_boundary_from_left):
    x_m = -FIELD_WIDTH_M / 2.0 + column_boundary_from_left * GRID_SIDE_M
    y_m = FIELD_HEIGHT_M / 2.0 - row_boundary_from_top * GRID_SIDE_M
    return rounded_coordinate(x_m), rounded_coordinate(y_m)


def build_grid_data():
    points = []
    number_to_coordinate_m = {}
    for row in range(VERTEX_ROWS):
        for column in range(VERTEX_COLUMNS):
            number = vertex_number(row, column)
            x_m, y_m = vertex_coordinate(row, column)
            point = {
                "number": number,
                "type": "vertex",
                "row_boundary_from_top": row,
                "column_boundary_from_left": column,
                "x_m": x_m,
                "y_m": y_m,
            }
            points.append(point)
            number_to_coordinate_m[str(number)] = {"x_m": x_m, "y_m": y_m}

    squares = []
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            top_left = vertex_number(row, column)
            squares.append(
                {
                    "square_number": row * GRID_COLUMNS + column + 1,
                    "row_from_top": row + 1,
                    "column_from_left": column + 1,
                    "vertex_numbers": {
                        "top_left": top_left,
                        "top_right": top_left + 1,
                        "bottom_left": top_left + VERTEX_COLUMNS,
                        "bottom_right": top_left + VERTEX_COLUMNS + 1,
                    },
                }
            )

    return {
        "description": (
            "Full 0.10 m square grid covering the 3.0 m x 2.5 m RICAM arena. "
            "Every unique vertex has one numeric ID and a world-coordinate mapping."
        ),
        "coordinate_system": {
            "frame": "map",
            "origin_m": {"x": 0.0, "y": 0.0},
            "x_axis": "positive to the right",
            "y_axis": "positive upward",
            "numbering_order": "top to bottom, left to right within each row",
        },
        "map_bounds_m": {
            "x": [-FIELD_WIDTH_M / 2.0, FIELD_WIDTH_M / 2.0],
            "y": [-FIELD_HEIGHT_M / 2.0, FIELD_HEIGHT_M / 2.0],
        },
        "square_side_m": GRID_SIDE_M,
        "grid_dimensions": {
            "columns": GRID_COLUMNS,
            "rows": GRID_ROWS,
            "total_squares": SQUARE_COUNT,
        },
        "vertex_grid_dimensions": {
            "columns": VERTEX_COLUMNS,
            "rows": VERTEX_ROWS,
            "total_vertices": VERTEX_COUNT,
        },
        "numbering_scheme": {
            "vertices": [1, VERTEX_COUNT],
            "top_left_vertex": 1,
            "top_right_vertex": VERTEX_COLUMNS,
            "bottom_left_vertex": vertex_number(GRID_ROWS, 0),
            "bottom_right_vertex": VERTEX_COUNT,
        },
        "counts": {"vertices": VERTEX_COUNT, "squares": SQUARE_COUNT},
        "points": points,
        "grouped_points": {"vertices": points},
        "number_to_coordinate_m": number_to_coordinate_m,
        "squares": squares,
    }


def load_font(size, bold=False):
    names = (
        ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf")
    )
    candidates = []
    windows_fonts = Path("C:/Windows/Fonts")
    for name in names:
        candidates.append(windows_fonts / name)
        candidates.append(Path("/usr/share/fonts/truetype/dejavu") / name)
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def world_to_image(x_m, y_m):
    x_px = LEFT_MARGIN_PX + (x_m + FIELD_WIDTH_M / 2.0) * (
        FIELD_WIDTH_PX / FIELD_WIDTH_M
    )
    y_px = TOP_MARGIN_PX + (FIELD_HEIGHT_M / 2.0 - y_m) * (
        FIELD_HEIGHT_PX / FIELD_HEIGHT_M
    )
    return int(round(x_px)), int(round(y_px))


def metric_rectangle(draw, center_x, center_y, size_x, size_y, **kwargs):
    left, top = world_to_image(center_x - size_x / 2.0, center_y + size_y / 2.0)
    right, bottom = world_to_image(center_x + size_x / 2.0, center_y - size_y / 2.0)
    draw.rectangle((left, top, right, bottom), **kwargs)


def metric_circle(draw, center_x, center_y, radius_m, **kwargs):
    left, top = world_to_image(center_x - radius_m, center_y + radius_m)
    right, bottom = world_to_image(center_x + radius_m, center_y - radius_m)
    draw.ellipse((left, top, right, bottom), **kwargs)


def text_bounds(draw, text, font):
    """Measure text on both current Pillow and Ubuntu 20.04 Pillow."""
    if hasattr(draw, "textbbox"):
        return draw.textbbox((0, 0), text, font=font)
    width, height = draw.textsize(text, font=font)
    return 0, 0, width, height


def draw_rounded_box(draw, box, radius, fill):
    """Draw a filled rounded box using APIs available in old Pillow."""
    left, top, right, bottom = box
    diameter = radius * 2
    draw.rectangle((left + radius, top, right - radius, bottom), fill=fill)
    draw.rectangle((left, top + radius, right, bottom - radius), fill=fill)
    draw.ellipse((left, top, left + diameter, top + diameter), fill=fill)
    draw.ellipse((right - diameter, top, right, top + diameter), fill=fill)
    draw.ellipse((left, bottom - diameter, left + diameter, bottom), fill=fill)
    draw.ellipse((right - diameter, bottom - diameter, right, bottom), fill=fill)


def draw_centered_text(draw, xy, text, font, fill):
    box = text_bounds(draw, text, font)
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.text((xy[0] - width / 2.0, xy[1] - height / 2.0 - box[1]), text, font=font, fill=fill)


def render_numbered_map(source_map_path):
    image = Image.new("RGB", (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), "white")
    draw = ImageDraw.Draw(image)
    field_box = (
        LEFT_MARGIN_PX,
        TOP_MARGIN_PX,
        LEFT_MARGIN_PX + FIELD_WIDTH_PX,
        TOP_MARGIN_PX + FIELD_HEIGHT_PX,
    )
    draw.rectangle(field_box, fill="#fffbd1")

    # Draw non-occupied game regions first. The exact occupancy mask is overlaid
    # afterwards so walls and physical boxes remain authoritative.
    metric_rectangle(draw, -1.30, 1.075, 0.30, 0.25, fill="#e8eef5")
    for index in range(6):
        stripe_x = -1.435 + index * 0.054
        metric_rectangle(draw, stripe_x, 1.075, 0.018, 0.24, fill="#3978b8")

    region_font = load_font(58, bold=True)
    for letter, (x_m, y_m) in zip("ABCD", DELIVERY_TARGETS):
        metric_circle(draw, x_m, y_m, 0.135, fill="#c9ced3", outline="#666666", width=5)
        draw_centered_text(draw, world_to_image(x_m, y_m), letter, region_font, "#202020")

    metric_rectangle(
        draw,
        PICKUP_ZONE_CENTER_X_M,
        PICKUP_ZONE_CENTER_Y_M,
        0.72,
        0.32,
        fill="#c9ced3",
        outline="#666666",
        width=5,
    )
    for index, x_m in enumerate(PICKUP_BALL_X_M):
        color = "#d12e2e" if index < 2 else "#2878c8"
        metric_circle(draw, x_m, PICKUP_ZONE_CENTER_Y_M, 0.045, fill=color, outline="#202020", width=3)

    for zone_x, zone_y, _letter, _item in RECOGNITION_ZONES:
        metric_rectangle(
            draw,
            zone_x,
            zone_y,
            RECOGNITION_ZONE_SIZE_X_M,
            RECOGNITION_ZONE_SIZE_Y_M,
            fill="#c9ced3",
            outline="#666666",
            width=5,
        )

    source_map = Image.open(source_map_path).convert("L")
    expected_size = (int(round(FIELD_WIDTH_M / 0.01)), int(round(FIELD_HEIGHT_M / 0.01)))
    if source_map.size != expected_size:
        raise ValueError(
            f"Expected occupancy map size {expected_size}, got {source_map.size}"
        )
    occupied = source_map.resize((FIELD_WIDTH_PX, FIELD_HEIGHT_PX), Image.NEAREST).point(
        lambda value: 255 if value < 128 else 0
    )
    obstacle_layer = Image.new("RGB", (FIELD_WIDTH_PX, FIELD_HEIGHT_PX), "#292929")
    image.paste(obstacle_layer, (LEFT_MARGIN_PX, TOP_MARGIN_PX), occupied)
    draw = ImageDraw.Draw(image)

    for column in range(VERTEX_COLUMNS):
        x_px = LEFT_MARGIN_PX + column * PIXELS_PER_SQUARE
        draw.line(
            (x_px, TOP_MARGIN_PX, x_px, TOP_MARGIN_PX + FIELD_HEIGHT_PX),
            fill="#aeb3b7",
            width=2,
        )
    for row in range(VERTEX_ROWS):
        y_px = TOP_MARGIN_PX + row * PIXELS_PER_SQUARE
        draw.line(
            (LEFT_MARGIN_PX, y_px, LEFT_MARGIN_PX + FIELD_WIDTH_PX, y_px),
            fill="#aeb3b7",
            width=2,
        )
    draw.rectangle(field_box, outline="#111111", width=10)

    number_font = load_font(25, bold=True)
    for row in range(VERTEX_ROWS):
        for column in range(VERTEX_COLUMNS):
            number = vertex_number(row, column)
            center_x = LEFT_MARGIN_PX + column * PIXELS_PER_SQUARE
            center_y = TOP_MARGIN_PX + row * PIXELS_PER_SQUARE
            text = str(number)
            text_box = text_bounds(draw, text, number_font)
            text_width = text_box[2] - text_box[0]
            badge_width = max(48, text_width + 18)
            badge_height = 34
            badge_box = (
                center_x - badge_width // 2,
                center_y - badge_height // 2,
                center_x + badge_width // 2,
                center_y + badge_height // 2,
            )
            draw_rounded_box(draw, badge_box, 9, "white")
            inner_badge_box = (
                badge_box[0] + 2,
                badge_box[1] + 2,
                badge_box[2] - 2,
                badge_box[3] - 2,
            )
            draw_rounded_box(draw, inner_badge_box, 7, "#7b3f98")
            draw_centered_text(draw, (center_x, center_y), text, number_font, "white")

    title_font = load_font(54, bold=True)
    subtitle_font = load_font(28)
    draw_centered_text(
        draw,
        (IMAGE_WIDTH_PX // 2, 58),
        "RICAM 10 cm Vertex Grid",
        title_font,
        "#202020",
    )
    draw_centered_text(
        draw,
        (IMAGE_WIDTH_PX // 2, 118),
        "map frame: origin at centre, +X right, +Y up | vertices 1-806",
        subtitle_font,
        "#444444",
    )
    return image


def generate(output_dir, source_map_path, basename=DEFAULT_OUTPUT_BASENAME):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    png_path = output_dir / f"{basename}.png"

    grid_data = build_grid_data()
    with json_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(grid_data, ensure_ascii=False, indent=2) + "\n")
    image = render_numbered_map(source_map_path)
    image.save(png_path, format="PNG", optimize=True, dpi=(300, 300))
    print(f"Generated {json_path} and {png_path}")
    return json_path, png_path


def main():
    package_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=package_dir / "maps",
    )
    parser.add_argument(
        "--source-map",
        type=Path,
        default=package_dir / "maps" / "ricam_arena.pgm",
    )
    parser.add_argument("--basename", default=DEFAULT_OUTPUT_BASENAME)
    args = parser.parse_args()
    generate(args.output_dir.resolve(), args.source_map.resolve(), args.basename)


if __name__ == "__main__":
    main()
