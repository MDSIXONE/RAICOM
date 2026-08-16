#!/usr/bin/env python3

import importlib.util
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
GENERATOR_PATH = PACKAGE_ROOT / "scripts" / "generate_scaled_urdf.py"
SOURCE_PATH = PACKAGE_ROOT / "urdf" / "car3.urdf"
GENERATED_PATH = PACKAGE_ROOT / "urdf" / "car3_350mm.urdf"
SCALE = 0.54

spec = importlib.util.spec_from_file_location("generate_scaled_urdf", GENERATOR_PATH)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def values(text):
    return [float(item) for item in text.split()]


class ScaledUrdfTest(unittest.TestCase):
    def setUp(self):
        self.source = ET.parse(SOURCE_PATH).getroot()
        self.scaled = ET.parse(GENERATED_PATH).getroot()

    def test_generated_file_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "car3_scaled.urdf"
            generator.scale_urdf(SOURCE_PATH, output, SCALE)
            self.assertEqual(output.read_bytes(), GENERATED_PATH.read_bytes())

    def test_origins_and_meshes_are_uniformly_scaled(self):
        source_origins = self.source.findall(".//origin")
        scaled_origins = self.scaled.findall(".//origin")
        self.assertEqual(len(source_origins), len(scaled_origins))
        for source, scaled in zip(source_origins, scaled_origins):
            if source.get("xyz") is None:
                self.assertIsNone(scaled.get("xyz"))
                continue
            expected = [item * SCALE for item in values(source.get("xyz"))]
            for expected_value, actual_value in zip(expected, values(scaled.get("xyz"))):
                self.assertAlmostEqual(expected_value, actual_value, places=12)

        source_meshes = self.source.findall(".//mesh")
        scaled_meshes = self.scaled.findall(".//mesh")
        self.assertEqual(len(source_meshes), 44)
        for source, scaled in zip(source_meshes, scaled_meshes):
            expected = [item * SCALE for item in values(source.get("scale", "1 1 1"))]
            for expected_value, actual_value in zip(expected, values(scaled.get("scale"))):
                self.assertAlmostEqual(expected_value, actual_value, places=12)

    def test_mass_is_preserved_and_inertia_scales_with_length_squared(self):
        for source, scaled in zip(self.source.findall(".//mass"), self.scaled.findall(".//mass")):
            self.assertEqual(float(source.get("value")), float(scaled.get("value")))
        for source, scaled in zip(self.source.findall(".//inertia"), self.scaled.findall(".//inertia")):
            for attribute in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz"):
                self.assertAlmostEqual(
                    float(source.get(attribute)) * SCALE * SCALE,
                    float(scaled.get(attribute)),
                    places=12,
                )

    def test_sensor_translations_and_contact_depth_are_scaled(self):
        for source, scaled in zip(
            self.source.findall(".//sensor/pose"), self.scaled.findall(".//sensor/pose")
        ):
            source_values = values(source.text)
            scaled_values = values(scaled.text)
            for expected_value, actual_value in zip(
                [item * SCALE for item in source_values[:3]], scaled_values[:3]
            ):
                self.assertAlmostEqual(expected_value, actual_value, places=12)
            self.assertEqual(source_values[3:], scaled_values[3:])
        for source, scaled in zip(
            self.source.findall(".//minDepth"), self.scaled.findall(".//minDepth")
        ):
            self.assertAlmostEqual(float(source.text) * SCALE, float(scaled.text), places=12)


if __name__ == "__main__":
    unittest.main()
