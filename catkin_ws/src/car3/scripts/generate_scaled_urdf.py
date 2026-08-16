#!/usr/bin/env python3
"""Generate a uniformly scaled car3 URDF while preserving the reference file."""

import argparse
import pathlib
import xml.etree.ElementTree as ET


DEFAULT_SCALE = 0.54


def parse_values(text):
    return [float(value) for value in text.split()]


def format_values(values):
    return " ".join("{:.12g}".format(value) for value in values)


def scale_vector_attribute(element, attribute, factor):
    value = element.get(attribute)
    if value is None:
        return
    element.set(attribute, format_values(item * factor for item in parse_values(value)))


def indent(element, level=0):
    whitespace = "\n" + "  " * level
    child_whitespace = "\n" + "  " * (level + 1)
    if len(element):
        if not element.text or not element.text.strip():
            element.text = child_whitespace
        for child in element:
            indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = child_whitespace
        element[-1].tail = whitespace
    elif level and (not element.tail or not element.tail.strip()):
        element.tail = whitespace


def scale_urdf(source, destination, factor):
    if not 0.0 < factor <= 1.0:
        raise ValueError("scale must be in the interval (0, 1]")

    tree = ET.parse(source)
    robot = tree.getroot()
    robot.set("name", "car3_scaled_{:03d}".format(round(factor * 100)))

    for origin in robot.findall(".//origin"):
        scale_vector_attribute(origin, "xyz", factor)

    for mesh in robot.findall(".//mesh"):
        scale = parse_values(mesh.get("scale", "1 1 1"))
        if len(scale) != 3:
            raise ValueError("mesh scale must contain three values")
        mesh.set("scale", format_values(value * factor for value in scale))

    # Keep each link's mass unchanged for numerical stability.  With constant
    # mass, a uniform geometric scale changes rotational inertia by s^2.
    inertia_factor = factor * factor
    for inertia in robot.findall(".//inertia"):
        for attribute in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz"):
            inertia.set(attribute, "{:.12g}".format(float(inertia.get(attribute)) * inertia_factor))

    for pose in robot.findall(".//sensor/pose"):
        values = parse_values(pose.text or "")
        if len(values) != 6:
            raise ValueError("sensor pose must contain six values")
        pose.text = format_values(
            [values[0] * factor, values[1] * factor, values[2] * factor] + values[3:]
        )

    for minimum_depth in robot.findall(".//minDepth"):
        minimum_depth.text = "{:.12g}".format(float(minimum_depth.text) * factor)

    indent(robot)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def main():
    package_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE)
    parser.add_argument(
        "--source", type=pathlib.Path, default=package_root / "urdf" / "car3.urdf"
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=package_root / "urdf" / "car3_350mm.urdf",
    )
    arguments = parser.parse_args()
    scale_urdf(arguments.source, arguments.output, arguments.scale)
    print("generated {} at scale {:.6f}".format(arguments.output, arguments.scale))


if __name__ == "__main__":
    main()
