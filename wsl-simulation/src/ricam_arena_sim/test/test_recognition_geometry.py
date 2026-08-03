#!/usr/bin/env python3
"""Contract tests keeping Blender, Gazebo and RViz recognition boxes aligned."""

import importlib.util
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PACKAGE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from arena_geometry import (  # noqa: E402
    FIELD_WIDTH_M,
    PICKUP_ZONE_CENTER_Y_M,
    RECOGNITION_BOXES,
    RECOGNITION_BOX_SIZE_M,
    RECOGNITION_ZONE_GAP_M,
    RECOGNITION_ZONES,
    RECOGNITION_ZONE_SIZE_X_M,
    RECOGNITION_ZONE_SIZE_Y_M,
    SIDE_BOX_CENTER_M,
    SIDE_BOX_SIZE_M,
    WALL_THICKNESS_M,
)


class RecognitionGeometryTest(unittest.TestCase):
    def test_initial_heading_points_to_world_positive_x(self):
        launch_root = ET.parse(PACKAGE_DIR / "launch" / "simulation.launch").getroot()
        arguments = {
            element.attrib["name"]: element.attrib.get("default")
            for element in launch_root.findall("arg")
        }
        self.assertEqual(float(arguments["start_yaw"]), 0.0)

        spawn = next(
            node
            for node in launch_root.findall("node")
            if node.attrib.get("name") == "spawn_mini2"
        )
        self.assertIn("-Y $(arg start_yaw)", spawn.attrib["args"])

    def test_manual_box_positions_remain_inside_recognition_zones(self):
        half_zone = RECOGNITION_ZONE_SIZE_X_M / 2.0
        half_box = RECOGNITION_BOX_SIZE_M / 2.0
        for (zone_x, _zone_y, _letter, _item), (box_x, _box_y) in zip(
            RECOGNITION_ZONES, RECOGNITION_BOXES
        ):
            self.assertGreaterEqual(box_x - half_box, zone_x - half_zone)
            self.assertLessEqual(box_x + half_box, zone_x + half_zone)
        self.assertEqual(RECOGNITION_BOXES, ((0.694172, 0.40), (0.954366, -0.40)))

    def test_recognition_gap_is_30_cm(self):
        upper_y = RECOGNITION_ZONES[0][1]
        lower_y = RECOGNITION_ZONES[1][1]
        clear_gap = upper_y - lower_y - RECOGNITION_ZONE_SIZE_Y_M
        self.assertAlmostEqual(clear_gap, RECOGNITION_ZONE_GAP_M)
        self.assertAlmostEqual(clear_gap, 0.30)

    def test_pickup_centreline_matches_lower_recognition_zone(self):
        self.assertAlmostEqual(PICKUP_ZONE_CENTER_Y_M, RECOGNITION_ZONES[1][1])

    def test_right_side_gray_regions_remain(self):
        zone_right = RECOGNITION_ZONES[1][0] + RECOGNITION_ZONE_SIZE_X_M / 2.0
        east_wall_inner = FIELD_WIDTH_M / 2.0 - WALL_THICKNESS_M
        right_box_edge = RECOGNITION_BOXES[1][0] + RECOGNITION_BOX_SIZE_M / 2.0
        self.assertAlmostEqual(zone_right - right_box_edge, 0.018372)
        self.assertAlmostEqual(east_wall_inner - zone_right, 0.327262)

    def test_gazebo_collision_centres_match_shared_geometry(self):
        world = (PACKAGE_DIR / "worlds" / "arena.world").read_text(encoding="utf-8")
        poses = []
        for name in ("kt_box_1", "kt_box_2"):
            match = re.search(
                rf'<collision name="{name}">\s*<pose>([^<]+)</pose>', world
            )
            self.assertIsNotNone(match)
            values = tuple(float(value) for value in match.group(1).split())
            poses.append(values[:2])
        self.assertEqual(tuple(poses), RECOGNITION_BOXES)

    def test_gazebo_side_box_matches_recovered_blender_geometry(self):
        world = (PACKAGE_DIR / "worlds" / "arena.world").read_text(encoding="utf-8")
        match = re.search(
            r'<collision name="manual_side_box">\s*<pose>([^<]+)</pose>\s*'
            r'<geometry><box><size>([^<]+)</size>',
            world,
        )
        self.assertIsNotNone(match)
        pose = tuple(float(value) for value in match.group(1).split())
        size = tuple(float(value) for value in match.group(2).split())
        self.assertEqual(pose[:3], SIDE_BOX_CENTER_M)
        self.assertEqual(size, SIDE_BOX_SIZE_M)

    def test_rviz_generator_uses_shared_box_centres(self):
        spec = importlib.util.spec_from_file_location(
            "generate_rviz_map", SCRIPTS_DIR / "generate_rviz_map.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIs(module.RECOGNITION_BOXES, RECOGNITION_BOXES)

    def test_obj_box_bounds_match_shared_geometry(self):
        vertices = {"kt_box_1": [], "kt_box_2": [], "manual_side_box": []}
        current_object = None
        obj_path = PACKAGE_DIR / "meshes" / "ricam_arena.obj"
        for line in obj_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("o "):
                current_object = line[2:].strip()
            elif current_object in vertices and line.startswith("v "):
                vertices[current_object].append(
                    tuple(float(value) for value in line.split()[1:4])
                )

        for index, (x_m, y_m) in enumerate(RECOGNITION_BOXES, 1):
            points = vertices[f"kt_box_{index}"]
            self.assertTrue(points)
            minimum = tuple(min(point[axis] for point in points) for axis in range(3))
            maximum = tuple(max(point[axis] for point in points) for axis in range(3))
            centre = tuple((low + high) / 2.0 for low, high in zip(minimum, maximum))
            dimensions = tuple(high - low for low, high in zip(minimum, maximum))
            for actual, expected in zip(
                centre, (x_m, y_m, RECOGNITION_BOX_SIZE_M / 2.0)
            ):
                self.assertAlmostEqual(actual, expected)
            for dimension in dimensions:
                self.assertAlmostEqual(dimension, RECOGNITION_BOX_SIZE_M)

        points = vertices["manual_side_box"]
        self.assertTrue(points)
        minimum = tuple(min(point[axis] for point in points) for axis in range(3))
        maximum = tuple(max(point[axis] for point in points) for axis in range(3))
        centre = tuple((low + high) / 2.0 for low, high in zip(minimum, maximum))
        dimensions = tuple(high - low for low, high in zip(minimum, maximum))
        for actual, expected in zip(centre, SIDE_BOX_CENTER_M):
            self.assertAlmostEqual(actual, expected, places=5)
        for actual, expected in zip(dimensions, SIDE_BOX_SIZE_M):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_generated_grid_contains_new_centres_not_old_centres(self):
        pgm = (PACKAGE_DIR / "maps" / "ricam_arena.pgm").read_bytes()
        magic, dimensions, maximum, pixels = pgm.split(b"\n", 3)
        self.assertEqual(magic, b"P5")
        self.assertEqual(maximum, b"255")
        width_px, height_px = (int(value) for value in dimensions.split())

        def value_at(x_m, y_m):
            px = int(round((x_m + 1.5) / 0.01))
            py = int(round((1.25 - y_m) / 0.01))
            return pixels[py * width_px + px]

        for x_m, y_m in RECOGNITION_BOXES:
            self.assertEqual(value_at(x_m, y_m), 0)
        self.assertEqual(value_at(SIDE_BOX_CENTER_M[0], SIDE_BOX_CENTER_M[1]), 0)
        self.assertEqual(value_at(-1.05, 0.0), 254)
        self.assertEqual(value_at(0.90, 0.58), 254)
        self.assertEqual(value_at(0.90, -0.58), 254)


if __name__ == "__main__":
    unittest.main()
