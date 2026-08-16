#!/usr/bin/env python3

import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


class CaptureContractTest(unittest.TestCase):
    def test_launch_defaults(self):
        launch_path = Path(__file__).resolve().parents[1] / "launch" / "capture_600.launch"
        root = ET.parse(str(launch_path)).getroot()
        defaults = {node.attrib["name"]: node.attrib["default"] for node in root.findall("arg")}
        self.assertEqual(defaults["interval"], "0.5")
        self.assertEqual(defaults["max_images"], "600")
        self.assertEqual(defaults["image_topic"], "/camera/rgb/image_raw")
        self.assertIn("data/images", defaults["output_dir"])


if __name__ == "__main__":
    unittest.main()
