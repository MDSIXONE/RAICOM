#!/usr/bin/env python3

import pathlib
import unittest


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCH_TEXT = (
    PACKAGE_ROOT.parent / "ricam_arena_sim" / "launch" / "simulation.launch"
).read_text(encoding="utf-8")


class InitializationContractTest(unittest.TestCase):
    def test_real_controllers_replace_fake_joint_publisher(self):
        self.assertIn("joint_state_controller arm_controller gripper_controller", LAUNCH_TEXT)
        self.assertNotIn('pkg="joint_state_publisher"', LAUNCH_TEXT)

    def test_calibrated_initialization_is_started(self):
        self.assertIn('type="initialize_car3.py"', LAUNCH_TEXT)
        self.assertIn('default="-0.0001,-0.4999,1.2800,1.7000,0.0000"', LAUNCH_TEXT)
        self.assertIn('-J r_joint $(arg gripper_initial_position)', LAUNCH_TEXT)

    def test_rviz_does_not_force_software_rendering(self):
        self.assertNotIn("LIBGL_ALWAYS_SOFTWARE", LAUNCH_TEXT)

    def test_reference_physics_startup_is_used(self):
        self.assertIn('name="start_z" default="0.0054"', LAUNCH_TEXT)
        self.assertNotIn("simulation_pid_gains.yaml", LAUNCH_TEXT)

    def test_scaled_robot_description_is_used(self):
        self.assertIn("car3_350mm.urdf", LAUNCH_TEXT)


if __name__ == "__main__":
    unittest.main()
