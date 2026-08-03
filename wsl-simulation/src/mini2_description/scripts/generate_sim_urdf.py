#!/usr/bin/env python3
"""Generate the navigation-simulation URDF from the untouched Mini2 CAD URDF."""

import argparse
import io
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PACKAGE_DIR / "urdf" / "mini2_description.urdf"
DEFAULT_OUTPUT = PACKAGE_DIR / "urdf" / "mini2_sim.urdf"
FIXED_JOINT_CHILD_TAGS = (
    "axis",
    "calibration",
    "dynamics",
    "limit",
    "mimic",
    "safety_controller",
)


def parse_vector(text, default=(0.0, 0.0, 0.0)):
    if not text:
        return default
    return tuple(float(value) for value in text.split())


def rotation_matrix(rpy):
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def transform_point(point, origin_xyz, rotation):
    return tuple(
        origin_xyz[row]
        + sum(rotation[row][column] * point[column] for column in range(3))
        for row in range(3)
    )


def binary_stl_bounds(path):
    data = path.read_bytes()
    if len(data) < 84:
        raise RuntimeError(f"STL is too short: {path}")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(data) < expected_size:
        raise RuntimeError(
            f"STL triangle table is truncated: {path} "
            f"({len(data)} bytes, expected at least {expected_size})"
        )

    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    for record in struct.iter_unpack("<12fH", data[84:expected_size]):
        for offset in (3, 6, 9):
            for axis in range(3):
                value = float(record[offset + axis])
                minimum[axis] = min(minimum[axis], value)
                maximum[axis] = max(maximum[axis], value)
    return tuple(minimum), tuple(maximum)


def format_vector(values):
    return " ".join(f"{value:.9g}" for value in values)


def replace_mesh_collision_with_box(link, package_dir):
    visual = link.find("visual")
    if visual is None:
        return
    mesh = visual.find("geometry/mesh")
    if mesh is None:
        return
    mesh_path = package_dir / "meshes" / Path(mesh.get("filename")).name
    minimum, maximum = binary_stl_bounds(mesh_path)
    scale = parse_vector(mesh.get("scale"), (1.0, 1.0, 1.0))
    origin = visual.find("origin")
    origin_xyz = parse_vector(origin.get("xyz") if origin is not None else None)
    origin_rpy = parse_vector(origin.get("rpy") if origin is not None else None)
    rotation = rotation_matrix(origin_rpy)

    transformed = []
    for x_value in (minimum[0], maximum[0]):
        for y_value in (minimum[1], maximum[1]):
            for z_value in (minimum[2], maximum[2]):
                transformed.append(
                    transform_point(
                        (
                            x_value * scale[0],
                            y_value * scale[1],
                            z_value * scale[2],
                        ),
                        origin_xyz,
                        rotation,
                    )
                )
    box_minimum = tuple(min(point[axis] for point in transformed) for axis in range(3))
    box_maximum = tuple(max(point[axis] for point in transformed) for axis in range(3))
    size = tuple(box_maximum[axis] - box_minimum[axis] for axis in range(3))
    centre = tuple((box_maximum[axis] + box_minimum[axis]) / 2.0 for axis in range(3))

    collision = link.find("collision")
    if collision is None:
        collision = ET.SubElement(link, "collision")
    collision.clear()
    collision.set("name", f"{link.get('name')}_sim_collision")
    ET.SubElement(
        collision,
        "origin",
        {"xyz": format_vector(centre), "rpy": "0 0 0"},
    )
    geometry = ET.SubElement(collision, "geometry")
    ET.SubElement(geometry, "box", {"size": format_vector(size)})


def freeze_joint(joint):
    joint.set("type", "fixed")
    for tag_name in FIXED_JOINT_CHILD_TAGS:
        child = joint.find(tag_name)
        if child is not None:
            joint.remove(child)


def add_fixed_joint(root, name, parent, child, xyz="0 0 0", rpy="0 0 0"):
    joint = ET.SubElement(root, "joint", {"name": name, "type": "fixed"})
    ET.SubElement(joint, "origin", {"xyz": xyz, "rpy": rpy})
    ET.SubElement(joint, "parent", {"link": parent})
    ET.SubElement(joint, "child", {"link": child})


def add_base_footprint(root):
    link = ET.Element("link", {"name": "base_footprint"})
    inertial = ET.SubElement(link, "inertial")
    ET.SubElement(inertial, "origin", {"xyz": "0 0 0", "rpy": "0 0 0"})
    ET.SubElement(inertial, "mass", {"value": "0.001"})
    ET.SubElement(
        inertial,
        "inertia",
        {
            "ixx": "0.000001",
            "ixy": "0",
            "ixz": "0",
            "iyy": "0.000001",
            "iyz": "0",
            "izz": "0.000001",
        },
    )
    root.insert(0, link)


def add_sensor_link(root, name, geometry_tag=None, geometry_attributes=None):
    link = ET.SubElement(root, "link", {"name": name})
    inertial = ET.SubElement(link, "inertial")
    ET.SubElement(inertial, "origin", {"xyz": "0 0 0", "rpy": "0 0 0"})
    ET.SubElement(inertial, "mass", {"value": "0.001"})
    ET.SubElement(
        inertial,
        "inertia",
        {
            "ixx": "0.000001",
            "ixy": "0",
            "ixz": "0",
            "iyy": "0.000001",
            "iyz": "0",
            "izz": "0.000001",
        },
    )
    if geometry_tag:
        visual = ET.SubElement(link, "visual")
        geometry = ET.SubElement(visual, "geometry")
        ET.SubElement(geometry, geometry_tag, geometry_attributes or {})
        material = ET.SubElement(visual, "material", {"name": "sensor_black"})
        ET.SubElement(material, "color", {"rgba": "0.05 0.05 0.05 1"})
    return link


def add_gazebo_extensions(root):
    model_gazebo = ET.SubElement(root, "gazebo")
    ET.SubElement(model_gazebo, "selfCollide").text = "false"
    planar = ET.SubElement(
        model_gazebo,
        "plugin",
        {"name": "planar_controller", "filename": "libgazebo_ros_planar_move.so"},
    )
    for tag_name, value in (
        ("commandTopic", "/cmd_vel"),
        ("odometryTopic", "/odom"),
        ("odometryFrame", "odom"),
        ("odometryRate", "30"),
        ("robotBaseFrame", "base_footprint"),
        ("bodyName", "base_link"),
        ("cmdTimeout", "0.5"),
    ):
        ET.SubElement(planar, tag_name).text = value

    for foot_link in ("11_Link", "21_Link", "31_Link", "41_Link"):
        gazebo = ET.SubElement(root, "gazebo", {"reference": foot_link})
        for tag_name, value in (
            ("mu1", "2.0"),
            ("mu2", "2.0"),
            ("kp", "100000"),
            ("kd", "100"),
            ("minDepth", "0.001"),
        ):
            ET.SubElement(gazebo, tag_name).text = value

    for planar_link in ("base_footprint", "base_link"):
        gazebo = ET.SubElement(root, "gazebo", {"reference": planar_link})
        ET.SubElement(gazebo, "gravity").text = "false"
        ET.SubElement(gazebo, "kinematic").text = "true"

    laser_gazebo = ET.SubElement(root, "gazebo", {"reference": "laser_link"})
    ET.SubElement(laser_gazebo, "material").text = "Gazebo/Black"
    laser = ET.SubElement(laser_gazebo, "sensor", {"type": "ray", "name": "mini2_laser"})
    ET.SubElement(laser, "pose").text = "0 0 0 0 0 0"
    ET.SubElement(laser, "visualize").text = "false"
    ET.SubElement(laser, "update_rate").text = "15"
    ray = ET.SubElement(laser, "ray")
    scan = ET.SubElement(ray, "scan")
    horizontal = ET.SubElement(scan, "horizontal")
    for tag_name, value in (
        ("samples", "720"),
        ("resolution", "1"),
        ("min_angle", "-1.57"),
        ("max_angle", "1.57"),
    ):
        ET.SubElement(horizontal, tag_name).text = value
    scan_range = ET.SubElement(ray, "range")
    for tag_name, value in (("min", "0.02"), ("max", "10.0"), ("resolution", "0.01")):
        ET.SubElement(scan_range, tag_name).text = value
    laser_plugin = ET.SubElement(
        laser,
        "plugin",
        {"name": "mini2_laser_plugin", "filename": "libgazebo_ros_laser.so"},
    )
    ET.SubElement(laser_plugin, "topicName").text = "/scan"
    ET.SubElement(laser_plugin, "frameName").text = "laser_link"

    imu_gazebo = ET.SubElement(root, "gazebo", {"reference": "imu_link"})
    imu = ET.SubElement(imu_gazebo, "sensor", {"name": "mini2_imu", "type": "imu"})
    ET.SubElement(imu, "always_on").text = "true"
    ET.SubElement(imu, "update_rate").text = "100"
    imu_plugin = ET.SubElement(
        imu,
        "plugin",
        {"name": "mini2_imu_plugin", "filename": "libgazebo_ros_imu_sensor.so"},
    )
    ET.SubElement(imu_plugin, "topicName").text = "/imu"
    ET.SubElement(imu_plugin, "bodyName").text = "imu_link"
    ET.SubElement(imu_plugin, "frameName").text = "imu_link"
    ET.SubElement(imu_plugin, "updateRateHZ").text = "100"
    ET.SubElement(imu_plugin, "gaussianNoise").text = "0"
    ET.SubElement(imu_plugin, "xyzOffset").text = "0 0 0"
    ET.SubElement(imu_plugin, "rpyOffset").text = "0 0 0"

    camera_gazebo = ET.SubElement(root, "gazebo", {"reference": "camera_link"})
    camera = ET.SubElement(camera_gazebo, "sensor", {"name": "mini2_rgb_camera", "type": "camera"})
    ET.SubElement(camera, "pose").text = "0 0 0 0 0 0"
    ET.SubElement(camera, "always_on").text = "true"
    ET.SubElement(camera, "update_rate").text = "20"
    ET.SubElement(camera, "visualize").text = "true"
    optics = ET.SubElement(camera, "camera")
    ET.SubElement(optics, "horizontal_fov").text = "1.288"
    image = ET.SubElement(optics, "image")
    ET.SubElement(image, "width").text = "640"
    ET.SubElement(image, "height").text = "480"
    ET.SubElement(image, "format").text = "R8G8B8"
    clip = ET.SubElement(optics, "clip")
    ET.SubElement(clip, "near").text = "0.02"
    ET.SubElement(clip, "far").text = "4.0"
    camera_plugin = ET.SubElement(
        camera,
        "plugin",
        {"name": "mini2_rgb_plugin", "filename": "libgazebo_ros_camera.so"},
    )
    for tag_name, value in (
        ("alwaysOn", "true"),
        ("updateRate", "20"),
        ("cameraName", "camera"),
        ("imageTopicName", "rgb/image_raw"),
        ("cameraInfoTopicName", "rgb/camera_info"),
        ("frameName", "camera_optical_frame"),
    ):
        ET.SubElement(camera_plugin, tag_name).text = value

    for fixed_joint in (
        "base_footprint_joint",
        "laser_joint",
        "camera_joint",
        "camera_optical_joint",
        "imu_joint",
    ):
        gazebo = ET.SubElement(root, "gazebo", {"reference": fixed_joint})
        ET.SubElement(gazebo, "preserveFixedJoint").text = "true"


def indent(element, level=0):
    whitespace = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = whitespace + "  "
        for child in element:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = whitespace
    if level and (not element.tail or not element.tail.strip()):
        element.tail = whitespace


def generate(source, output):
    tree = ET.parse(source)
    root = tree.getroot()
    root.set("name", "mini2_sim")
    world_link = root.find("link[@name='world']")
    world_joint = root.find("joint[@name='world_fixed']")
    if world_link is None or world_joint is None:
        raise RuntimeError("Official Mini2 URDF no longer has the expected world anchor")
    root.remove(world_link)
    root.remove(world_joint)

    for link in root.findall("link"):
        replace_mesh_collision_with_box(link, source.parent.parent)
    for joint in root.findall("joint"):
        freeze_joint(joint)

    add_base_footprint(root)
    add_fixed_joint(root, "base_footprint_joint", "base_footprint", "base_link", xyz="0 0 0.088")
    add_sensor_link(root, "laser_link", "cylinder", {"radius": "0.025", "length": "0.02"})
    add_fixed_joint(root, "laser_joint", "base_link", "laser_link", xyz="0 0 0.16")
    add_sensor_link(root, "camera_link", "box", {"size": "0.025 0.04 0.025"})
    add_fixed_joint(root, "camera_joint", "base_link", "camera_link", xyz="0.18 0 0.16")
    add_sensor_link(root, "camera_optical_frame")
    add_fixed_joint(
        root,
        "camera_optical_joint",
        "camera_link",
        "camera_optical_frame",
        rpy="-1.5708 0 -1.5708",
    )
    add_sensor_link(root, "imu_link")
    add_fixed_joint(root, "imu_joint", "base_link", "imu_link")
    add_gazebo_extensions(root)
    root.insert(
        0,
        ET.Comment(
            " Generated from the untouched mini2_description.urdf; "
            "joints are fixed because the supplied package has no actuator controller. "
        ),
    )
    indent(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    tree.write(
        buffer,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    )
    output.write_bytes(buffer.getvalue())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    generate(arguments.source.resolve(), arguments.output.resolve())
    print(f"Generated {arguments.output.resolve()}")


if __name__ == "__main__":
    main()
