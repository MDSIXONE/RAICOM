#!/usr/bin/env python3
"""Static contracts for numbered waypoint navigation."""

import json
import math
import unittest
import xml.etree.ElementTree as ET
import importlib.util
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]


class WaypointRouteTest(unittest.TestCase):
    def test_default_route_coordinates_match_numbered_grid(self):
        grid = json.loads(
            (
                PACKAGE_DIR
                / "maps"
                / "ricam_arena_10cm_full_grid_all_numbered.json"
            ).read_text(encoding="utf-8")
        )
        mapping = grid["number_to_coordinate_m"]
        self.assertEqual(mapping["91"], {"x_m": 1.3, "y_m": 1.05})
        self.assertEqual(mapping["711"], {"x_m": 1.3, "y_m": -0.95})
        self.assertEqual(mapping["694"], {"x_m": -0.4, "y_m": -0.95})
        self.assertEqual(mapping["400"], {"x_m": 1.2, "y_m": 0.05})
        self.assertEqual(mapping["392"], {"x_m": 0.4, "y_m": 0.05})
        self.assertEqual(mapping["640"], {"x_m": 0.4, "y_m": -0.75})
        self.assertEqual(mapping["741"], {"x_m": 1.2, "y_m": -1.05})
        self.assertEqual(mapping["708"], {"x_m": 1.0, "y_m": -0.95})
        self.assertEqual(mapping["702"], {"x_m": 0.4, "y_m": -0.95})

    def test_launch_requires_navfn_and_cymplanner(self):
        root = ET.parse(
            PACKAGE_DIR / "launch" / "numbered_waypoint_route.launch"
        ).getroot()
        arguments = {
            element.attrib["name"]: element.attrib.get("default")
            for element in root.findall("arg")
        }
        self.assertEqual(arguments["point_numbers"], "[91, 711, 694]")
        node = root.find("node")
        self.assertEqual(node.attrib["type"], "navigate_numbered_waypoints.py")
        parameters = {
            element.attrib["name"]: element.attrib.get("value")
            for element in node.findall("param")
        }
        self.assertEqual(parameters["expected_global_planner"], "navfn/NavfnROS")
        self.assertEqual(
            parameters["expected_local_planner"], "cym_planner/CymPlanner"
        )
        self.assertEqual(parameters["require_expected_planners"], "true")
        via_points = next(
            element
            for element in node.findall("rosparam")
            if element.attrib.get("param") == "via_point_numbers"
        )
        self.assertIn("[400, 392, 640]", via_points.text)
        self.assertIn("[741, 708, 702]", via_points.text)
        self.assertEqual(parameters["pass_through_intermediate"], "true")
        self.assertEqual(parameters["waypoint_position_tolerance_m"], "0.12")
        self.assertEqual(parameters["via_position_tolerance_m"], "0.06")
        tolerance_overrides = next(
            element
            for element in node.findall("rosparam")
            if element.attrib.get("param") == "position_tolerance_overrides"
        )
        self.assertIn('"741": 0.11', tolerance_overrides.text)

    def test_node_preflights_and_sends_sequential_move_base_goals(self):
        source = (
            PACKAGE_DIR / "scripts" / "navigate_numbered_waypoints.py"
        ).read_text(encoding="utf-8")
        self.assertIn('ServiceProxy("/move_base/make_plan", GetPlan)', source)
        self.assertIn("start = response.plan.poses[-1]", source)
        self.assertIn('SimpleActionClient(\n            "/move_base", MoveBaseAction', source)
        self.assertIn("for index, (number, (x_m, y_m), yaw) in enumerate", source)
        self.assertIn("state == GoalStatus.SUCCEEDED", source)
        self.assertIn("terminal_failure_states", source)
        self.assertIn("math.atan2", source)
        self.assertIn("incoming_yaw", source)
        self.assertIn("outgoing_yaw", source)
        self.assertIn("first_goal_distance <= self.plan_tolerance_m", source)
        self.assertIn("number in self.primary_point_numbers", source)
        self.assertIn("quaternion_yaw", source)
        self.assertIn("expand_point_numbers", source)
        self.assertIn('"91->711": [400, 392, 640]', source)
        self.assertIn('"711->694": [741, 708, 702]', source)
        self.assertIn("wait_for_waypoint", source)
        self.assertIn("cancel_goal", source)
        self.assertIn("position_tolerance_overrides", source)

    def test_runtime_route_expansion_and_primary_yaws(self):
        try:
            import rospy  # noqa: F401
        except ImportError:
            self.skipTest("ROS Python modules are not installed in this environment")

        script = PACKAGE_DIR / "scripts" / "navigate_numbered_waypoints.py"
        specification = importlib.util.spec_from_file_location(
            "navigate_numbered_waypoints", str(script)
        )
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)

        navigator = module.NumberedWaypointNavigator.__new__(
            module.NumberedWaypointNavigator
        )
        navigator.primary_point_numbers = [91, 711, 694]
        navigator.via_point_numbers = {
            "91->711": [400, 392, 640],
            "711->694": [741, 708, 702],
        }
        navigator.plan_tolerance_m = 0.05
        navigator.position_tolerance_overrides = {741: 0.11}
        navigator.point_numbers = navigator.expand_point_numbers()
        navigator.points = [
            (1.30, 1.05),
            (1.20, 0.05),
            (0.40, 0.05),
            (0.40, -0.75),
            (1.30, -0.95),
            (1.20, -1.05),
            (1.00, -0.95),
            (0.40, -0.95),
            (-0.40, -0.95),
        ]

        yaws = navigator.compute_goal_yaws(-1.30, 1.05, 0.0)

        self.assertEqual(
            navigator.point_numbers,
            [91, 400, 392, 640, 711, 741, 708, 702, 694],
        )
        self.assertEqual(len(yaws), 9)
        self.assertAlmostEqual(yaws[0], 0.0, places=6)
        self.assertAlmostEqual(yaws[4], math.atan2(-0.20, 0.90), places=6)
        self.assertAlmostEqual(abs(yaws[8]), math.pi, places=6)

    def test_rviz_displays_numbered_route_markers(self):
        rviz = (PACKAGE_DIR / "rviz" / "arena.rviz").read_text(encoding="utf-8")
        self.assertIn("Name: Numbered Waypoint Route", rviz)
        self.assertIn(
            "Marker Topic: /numbered_waypoint_navigation/route_markers", rviz
        )


if __name__ == "__main__":
    unittest.main()
