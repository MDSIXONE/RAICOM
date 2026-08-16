#!/usr/bin/env python3
"""Contracts for the 10 cm vertex-numbered arena map."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


PACKAGE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PACKAGE_DIR / "scripts"
MAPS_DIR = PACKAGE_DIR / "maps"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_numbered_grid import (  # noqa: E402
    DEFAULT_OUTPUT_BASENAME,
    GRID_COLUMNS,
    GRID_ROWS,
    IMAGE_HEIGHT_PX,
    IMAGE_WIDTH_PX,
    SQUARE_COUNT,
    VERTEX_COLUMNS,
    VERTEX_COUNT,
    VERTEX_ROWS,
    build_grid_data,
    generate,
)


class NumberedGridTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_grid_data()

    def test_grid_dimensions_and_counts(self):
        self.assertEqual((GRID_COLUMNS, GRID_ROWS), (30, 25))
        self.assertEqual((VERTEX_COLUMNS, VERTEX_ROWS), (31, 26))
        self.assertEqual(SQUARE_COUNT, 750)
        self.assertEqual(VERTEX_COUNT, 806)
        self.assertEqual(len(self.data["points"]), 806)
        self.assertEqual(len(self.data["squares"]), 750)

    def test_corner_numbers_and_world_coordinates(self):
        mapping = self.data["number_to_coordinate_m"]
        self.assertEqual(mapping["1"], {"x_m": -1.5, "y_m": 1.25})
        self.assertEqual(mapping["31"], {"x_m": 1.5, "y_m": 1.25})
        self.assertEqual(mapping["776"], {"x_m": -1.5, "y_m": -1.25})
        self.assertEqual(mapping["806"], {"x_m": 1.5, "y_m": -1.25})

    def test_vertex_numbers_are_unique_and_row_major(self):
        points = self.data["points"]
        self.assertEqual([point["number"] for point in points], list(range(1, 807)))
        for point in points:
            expected = (
                point["row_boundary_from_top"] * VERTEX_COLUMNS
                + point["column_boundary_from_left"]
                + 1
            )
            self.assertEqual(point["number"], expected)

    def test_square_topology_uses_four_adjacent_vertices(self):
        for square in self.data["squares"]:
            vertices = square["vertex_numbers"]
            self.assertEqual(vertices["top_right"], vertices["top_left"] + 1)
            self.assertEqual(
                vertices["bottom_left"], vertices["top_left"] + VERTEX_COLUMNS
            )
            self.assertEqual(
                vertices["bottom_right"], vertices["bottom_left"] + 1
            )

    def test_committed_assets_are_reproducible_and_readable(self):
        committed_json = MAPS_DIR / f"{DEFAULT_OUTPUT_BASENAME}.json"
        committed_png = MAPS_DIR / f"{DEFAULT_OUTPUT_BASENAME}.png"
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            generated_json, generated_png = generate(
                Path(first_directory), MAPS_DIR / "ricam_arena.pgm"
            )
            repeated_json, repeated_png = generate(
                Path(second_directory), MAPS_DIR / "ricam_arena.pgm"
            )
            self.assertEqual(generated_json.read_bytes(), committed_json.read_bytes())
            self.assertEqual(generated_json.read_bytes(), repeated_json.read_bytes())
            self.assertEqual(generated_png.read_bytes(), repeated_png.read_bytes())

        with Image.open(committed_png) as image:
            self.assertEqual(image.size, (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX))
            self.assertEqual(image.mode, "RGB")
            self.assertIn((123, 63, 152), image.getdata())

        parsed = json.loads(committed_json.read_text(encoding="utf-8"))
        self.assertEqual(parsed["counts"], {"vertices": 806, "squares": 750})


if __name__ == "__main__":
    unittest.main()
