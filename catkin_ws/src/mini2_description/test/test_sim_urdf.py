#!/usr/bin/env python3
"""Contracts for the Mini2 navigation-simulation derivative."""

import hashlib
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
OFFICIAL_URDF = PACKAGE_DIR / "urdf" / "mini2_description.urdf"
SIM_URDF = PACKAGE_DIR / "urdf" / "mini2_sim.urdf"
GENERATOR = PACKAGE_DIR / "scripts" / "generate_sim_urdf.py"
OFFICIAL_URDF_SHA256 = "750ef1cdc06d2a12a09bad3550827798603faf16daac31381cfd70a0be304e6e"


class Mini2SimulationUrdfTest(unittest.TestCase):
    def test_official_model_remains_intact_and_sim_derivative_is_free(self):
        official = ET.parse(OFFICIAL_URDF).getroot()
        simulation = ET.parse(SIM_URDF).getroot()
        self.assertEqual(
            hashlib.sha256(OFFICIAL_URDF.read_bytes()).hexdigest(),
            OFFICIAL_URDF_SHA256,
        )
        self.assertEqual(official.attrib["name"], "mini2_description")
        self.assertIsNotNone(official.find("link[@name='world']"))
        self.assertIsNotNone(official.find("joint[@name='world_fixed']"))
        self.assertEqual(len(official.findall("link")), 19)
        self.assertEqual(len(official.findall("joint")), 18)

        self.assertEqual(simulation.attrib["name"], "mini2_sim")
        self.assertIsNone(simulation.find("link[@name='world']"))
        self.assertIsNone(simulation.find("joint[@name='world_fixed']"))
        self.assertIsNotNone(
            simulation.find("link[@name='base_footprint']/inertial")
        )
        base_joint = simulation.find("joint[@name='base_footprint_joint']")
        self.assertEqual(base_joint.attrib["type"], "fixed")
        self.assertEqual(base_joint.find("parent").attrib["link"], "base_footprint")
        self.assertEqual(base_joint.find("child").attrib["link"], "base_link")
        self.assertEqual(base_joint.find("origin").attrib["xyz"], "0 0 0.088")

    def test_uncontrolled_joints_are_frozen_and_collisions_are_primitive(self):
        simulation = ET.parse(SIM_URDF).getroot()
        original_joint_names = {
            joint.attrib["name"]
            for joint in ET.parse(OFFICIAL_URDF).getroot().findall("joint")
            if joint.attrib["name"] != "world_fixed"
        }
        joints = {joint.attrib["name"]: joint for joint in simulation.findall("joint")}
        for name in original_joint_names:
            self.assertEqual(joints[name].attrib["type"], "fixed")
            self.assertIsNone(joints[name].find("axis"))
            self.assertIsNone(joints[name].find("limit"))

        for link in simulation.findall("link"):
            mesh = link.find("visual/geometry/mesh")
            if mesh is not None:
                self.assertTrue(
                    (PACKAGE_DIR / "meshes" / Path(mesh.attrib["filename"]).name).is_file()
                )
                self.assertIsNotNone(link.find("collision/geometry/box"))
                self.assertIsNone(link.find("collision/geometry/mesh"))

    def test_navigation_sensors_and_planar_plugin_are_present(self):
        simulation = ET.parse(SIM_URDF).getroot()
        for frame_name in (
            "laser_link",
            "camera_link",
            "camera_optical_frame",
            "imu_link",
        ):
            self.assertIsNotNone(
                simulation.find(f"link[@name='{frame_name}']/inertial")
            )
        plugins = {
            plugin.attrib["name"]: plugin
            for plugin in simulation.findall(".//plugin")
        }
        planar = plugins["planar_controller"]
        self.assertEqual(planar.find("commandTopic").text, "/cmd_vel")
        self.assertEqual(planar.find("odometryTopic").text, "/odom")
        self.assertEqual(planar.find("robotBaseFrame").text, "base_footprint")
        self.assertEqual(planar.find("cmdTimeout").text, "0.5")
        self.assertEqual(plugins["mini2_laser_plugin"].find("topicName").text, "/scan")
        self.assertEqual(
            plugins["mini2_rgb_plugin"].find("imageTopicName").text,
            "rgb/image_raw",
        )
        self.assertEqual(plugins["mini2_imu_plugin"].find("topicName").text, "/imu")
        camera_sensor = simulation.find("gazebo[@reference='camera_link']/sensor")
        self.assertEqual(camera_sensor.find("pose").text, "0 0 0 0 0 0")

        laser_joint = simulation.find("joint[@name='laser_joint']")
        camera_joint = simulation.find("joint[@name='camera_joint']")
        self.assertEqual(laser_joint.find("origin").attrib["xyz"], "0 0 0.16")
        self.assertEqual(
            camera_joint.find("origin").attrib["xyz"], "0.18 0 0.16"
        )
        for sensor_joint in (laser_joint, camera_joint):
            sensor_z = float(sensor_joint.find("origin").attrib["xyz"].split()[2])
            self.assertGreater(sensor_z, 0.145)

        for planar_link in ("base_footprint", "base_link"):
            gazebo = simulation.find(f"gazebo[@reference='{planar_link}']")
            self.assertEqual(gazebo.find("gravity").text, "false")
            self.assertEqual(gazebo.find("kinematic").text, "true")

    def test_generated_urdf_is_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            generated = Path(temporary_directory) / "mini2_sim.urdf"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--source",
                    str(OFFICIAL_URDF),
                    "--output",
                    str(generated),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(generated.read_bytes(), SIM_URDF.read_bytes())


if __name__ == "__main__":
    unittest.main()
