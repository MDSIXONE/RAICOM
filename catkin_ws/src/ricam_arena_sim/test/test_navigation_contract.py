#!/usr/bin/env python3
"""Static contracts for the navigation costmaps and RViz displays."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]


class NavigationContractTest(unittest.TestCase):
    def test_launch_starts_move_base_by_default_without_duplicate_odom_tf(self):
        root = ET.parse(PACKAGE_DIR / "launch" / "simulation.launch").getroot()
        arguments = {
            element.attrib["name"]: element.attrib.get("default")
            for element in root.findall("arg")
        }
        self.assertEqual(arguments["navigation"], "true")
        self.assertEqual(arguments["local_planner"], "cym_planner/CymPlanner")
        self.assertEqual(arguments["cym_navigation_mode"], "main_legacy")

        nodes = {node.attrib["name"]: node for node in root.findall("node")}
        self.assertIn("spawn_mini2", nodes)
        self.assertNotIn("spawn_car3", nodes)
        self.assertNotIn("controller_spawner", nodes)
        self.assertNotIn("initialize_car3", nodes)
        self.assertNotIn("gripper_mimic", nodes)
        robot_description = next(
            parameter
            for parameter in root.findall("param")
            if parameter.attrib.get("name") == "robot_description"
        )
        self.assertIn("mini2_description", robot_description.attrib["textfile"])
        self.assertIn("mini2_sim.urdf", robot_description.attrib["textfile"])
        self.assertNotIn("odom_to_tf", nodes)
        self.assertEqual(nodes["map_to_odom"].attrib["pkg"], "tf2_ros")
        self.assertEqual(nodes["move_base"].attrib["pkg"], "move_base")
        self.assertEqual(nodes["move_base"].attrib.get("if"), "$(arg navigation)")
        move_base_parameters = "\n".join(
            element.attrib.get("file", "")
            for element in nodes["move_base"].findall("rosparam")
        )
        self.assertIn("cym_planner_params.json", move_base_parameters)
        self.assertIn("cym_planner_sim.yaml", move_base_parameters)

    def test_costmap_frames_plugins_and_scan_source_are_explicit(self):
        common = (PACKAGE_DIR / "config" / "costmap_common.yaml").read_text(
            encoding="utf-8"
        )
        global_map = (PACKAGE_DIR / "config" / "global_costmap.yaml").read_text(
            encoding="utf-8"
        )
        local_map = (PACKAGE_DIR / "config" / "local_costmap.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("topic: /scan", common)
        self.assertIn("- [0.20, 0.08]", common)
        self.assertIn("- [0.20, -0.08]", common)
        self.assertIn("robot_base_frame: base_footprint", global_map)
        self.assertIn("global_frame: map", global_map)
        self.assertIn('type: "costmap_2d::StaticLayer"', global_map)
        self.assertIn("global_frame: odom", local_map)
        self.assertIn("rolling_window: true", local_map)
        self.assertIn("width: 2", local_map)
        self.assertIn("height: 2", local_map)
        self.assertIn('type: "costmap_2d::ObstacleLayer"', local_map)

        move_base = (PACKAGE_DIR / "config" / "move_base.yaml").read_text(
            encoding="utf-8"
        )
        cym_sim = (PACKAGE_DIR / "config" / "cym_planner_sim.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("base_local_planner: cym_planner/CymPlanner", move_base)
        self.assertIn("main_legacy_max_vel_x: 0.40", cym_sim)
        self.assertIn("main_legacy_max_vel_theta: 1.00", cym_sim)

    def test_rviz_enables_both_costmap_topics(self):
        rviz = (PACKAGE_DIR / "rviz" / "arena.rviz").read_text(encoding="utf-8")
        self.assertIn("Name: Global Costmap", rviz)
        self.assertIn("Topic: /move_base/global_costmap/costmap", rviz)
        self.assertIn("Name: Local Costmap", rviz)
        self.assertIn("Topic: /move_base/local_costmap/costmap", rviz)
        self.assertIn("Topic: /move_base/CymPlanner/laser_points", rviz)

    def test_runtime_dependencies_are_declared(self):
        package = ET.parse(PACKAGE_DIR / "package.xml").getroot()
        dependencies = {element.text for element in package.findall("exec_depend")}
        for dependency in (
            "costmap_2d",
            "cym_planner",
            "dwa_local_planner",
            "mini2_description",
            "move_base",
            "navfn",
            "tf2_ros",
        ):
            self.assertIn(dependency, dependencies)


if __name__ == "__main__":
    unittest.main()
