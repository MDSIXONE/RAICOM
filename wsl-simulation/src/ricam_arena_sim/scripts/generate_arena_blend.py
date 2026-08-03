#!/usr/bin/env python3
"""Build the competition arena in Blender and export an OBJ for Gazebo."""

import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena_geometry import (  # noqa: E402
    DELIVERY_TARGETS,
    FIELD_HEIGHT_M,
    FIELD_WIDTH_M,
    PICKUP_BALL_X_M,
    PICKUP_ZONE_CENTER_X_M,
    PICKUP_ZONE_CENTER_Y_M,
    RECOGNITION_BOXES,
    RECOGNITION_BOX_SIZE_M,
    RECOGNITION_ZONES,
    RECOGNITION_ZONE_SIZE_X_M,
    RECOGNITION_ZONE_SIZE_Y_M,
    SIDE_BOX_CENTER_M,
    SIDE_BOX_SIZE_M,
)

WALL_HEIGHT = 0.30
WALL_THICKNESS = 0.05


def material(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = rgba
        principled.inputs["Roughness"].default_value = 0.72
    return mat


def add_box(name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new(name="soft_edges", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def add_disc(name, location, radius, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=0.012, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_text(name, text, location, size, mat, rotation=(0.0, 0.0, 0.0), font_path=None):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.002
    if font_path and font_path.exists():
        obj.data.font = bpy.data.fonts.load(str(font_path))
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return obj


def build_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    yellow = material("arena_yellow", (0.90, 0.88, 0.32, 1.0))
    grey = material("zone_grey", (0.52, 0.55, 0.58, 1.0))
    dark = material("wall_dark", (0.13, 0.15, 0.17, 1.0))
    white = material("white", (0.95, 0.95, 0.95, 1.0))
    black = material("black", (0.02, 0.02, 0.02, 1.0))
    blue = material("route_blue", (0.20, 0.43, 0.88, 1.0))
    red = material("pickup_red", (0.85, 0.05, 0.05, 1.0))

    add_box("field_floor", (0.0, 0.0, -0.012), (FIELD_WIDTH_M, FIELD_HEIGHT_M, 0.024), yellow)
    add_box("wall_north", (0.0, 1.225, WALL_HEIGHT / 2.0), (3.0, WALL_THICKNESS, WALL_HEIGHT), dark)
    add_box("wall_south", (0.0, -1.225, WALL_HEIGHT / 2.0), (3.0, WALL_THICKNESS, WALL_HEIGHT), dark)
    add_box("wall_west", (-1.475, 0.0, WALL_HEIGHT / 2.0), (WALL_THICKNESS, 2.5, WALL_HEIGHT), dark)
    add_box("wall_east", (1.475, 0.0, WALL_HEIGHT / 2.0), (WALL_THICKNESS, 2.5, WALL_HEIGHT), dark)

    # User-added edit-mode cube, recovered and separated from kt_label_2.
    add_box("manual_side_box", SIDE_BOX_CENTER_M, SIDE_BOX_SIZE_M, black)

    # Rule figures 4-2 and 4-3: 0.3 m striped start zone in the upper-left.
    add_box("start_zone", (-1.30, 1.075, 0.008), (0.30, 0.25, 0.016), white)
    for index in range(6):
        x = -1.435 + index * 0.054
        add_box(f"start_stripe_{index}", (x, 1.075, 0.018), (0.018, 0.24, 0.008), blue)

    # Four lettered delivery targets below/right of the start zone.
    arial = Path("C:/Windows/Fonts/arial.ttf")
    for letter, (x, y) in zip("ABCD", DELIVERY_TARGETS):
        add_disc(f"delivery_{letter}", (x, y, 0.012), 0.135, grey)
        add_text(f"label_{letter}", letter, (x, y, 0.023), 0.18, black, font_path=arial)

    # Pickup zone and four colour-coded foam-ball placeholders.
    add_box(
        "pickup_zone",
        (PICKUP_ZONE_CENTER_X_M, PICKUP_ZONE_CENTER_Y_M, 0.008),
        (0.72, 0.32, 0.016),
        grey,
    )
    pickup_materials = (red, red, blue, blue)
    for index, (x, mat) in enumerate(zip(PICKUP_BALL_X_M, pickup_materials)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=32,
            ring_count=16,
            radius=0.045,
            location=(x, PICKUP_ZONE_CENTER_Y_M, 0.055),
        )
        ball = bpy.context.object
        ball.name = f"pickup_ball_{index}"
        ball.data.materials.append(mat)

    # Each 0.5 m by 0.8 m recognition region contains one 0.3 m KT-board box.
    for index, ((zone_x, zone_y, letter, item), (box_x, box_y)) in enumerate(
        zip(RECOGNITION_ZONES, RECOGNITION_BOXES), 1
    ):
        label_size = 0.0875 if item == "CLOTHES" else 0.095
        add_box(
            f"recognition_zone_{index}",
            (zone_x, zone_y, 0.008),
            (RECOGNITION_ZONE_SIZE_X_M, RECOGNITION_ZONE_SIZE_Y_M, 0.016),
            grey,
            bevel=0.04,
        )
        add_box(
            f"kt_box_{index}",
            (box_x, box_y, RECOGNITION_BOX_SIZE_M / 2.0),
            (RECOGNITION_BOX_SIZE_M,) * 3,
            white,
        )
        add_text(
            f"kt_label_{index}",
            f"{letter}\n{item}",
            (box_x - RECOGNITION_BOX_SIZE_M / 2.0 - 0.006, box_y, 0.17),
            label_size,
            black,
            rotation=(0.0, -math.pi / 2.0, 0.0),
            font_path=arial,
        )

    add_text("arena_title", "RICAM 2026", (0.25, 1.08, 0.02), 0.10, dark, font_path=arial)


def export_assets(blend_path, obj_path, preview_path):
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.camera_add(location=(0.0, 0.0, 4.5))
    camera = bpy.context.object
    camera.name = "arena_overview_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 3.4
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(preview_path)
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    bpy.ops.wm.obj_export(
        filepath=str(obj_path),
        export_selected_objects=True,
        export_materials=True,
        path_mode="RELATIVE",
        forward_axis="Y",
        up_axis="Z",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--obj", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    build_scene()
    export_assets(args.blend.resolve(), args.obj.resolve(), args.preview.resolve())
    print(f"Saved {args.blend.resolve()}, {args.obj.resolve()} and {args.preview.resolve()}")


if __name__ == "__main__":
    main()
