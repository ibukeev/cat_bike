#!/usr/bin/env python3
"""Build an evidence-only Blender review of the approved right A/B C001 orientation.

Run with Blender, passing an STL exported from the frozen FreeCAD owner object.
This script intentionally does not export an STL, 3MF, or G-code.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-stl", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def material(name, rgba, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    metallic_input = bsdf.inputs.get("Metallic IOR Level") or bsdf.inputs.get("Metallic")
    if metallic_input is not None:
        metallic_input.default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_box(name, location, scale, mat):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def look_at(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, path, location, target):
    camera.location = location
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    review_dir = output_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.stl_import(filepath=str(Path(args.input_stl).resolve()))
    part = bpy.context.selected_objects[0]
    part.name = "REVIEW__RIGHT_UPPER_HEAD_C001__A_B__PRINT_ORIENTATION_V1"

    quaternion = config["numeric_contract"]["selected_rotation_quaternion_wxyz"]
    part.rotation_mode = "QUATERNION"
    part.rotation_quaternion = quaternion
    bpy.context.view_layer.update()

    rotated = [part.matrix_world @ vertex.co for vertex in part.data.vertices]
    min_corner = Vector((min(v.x for v in rotated), min(v.y for v in rotated), min(v.z for v in rotated)))
    max_corner = Vector((max(v.x for v in rotated), max(v.y for v in rotated), max(v.z for v in rotated)))
    part.location = (-(min_corner.x + max_corner.x) * 0.5, -(min_corner.y + max_corner.y) * 0.5, -min_corner.z)
    bpy.context.view_layer.update()

    part_mat = material("Approved C001", (0.20, 0.52, 0.92, 1.0), metallic=0.02, roughness=0.42)
    bed_mat = material("MK4S conservative bed", (0.15, 0.17, 0.20, 1.0), metallic=0.05, roughness=0.72)
    reserve_mat = material("10 mm reserve boundary", (0.95, 0.52, 0.05, 1.0), metallic=0.0, roughness=0.4)
    part.data.materials.append(part_mat)

    bed_x, bed_y, _ = config["numeric_contract"]["conservative_printer_envelope_mm"]
    reserve = config["numeric_contract"]["required_xy_reserve_each_side_mm"]
    add_box("CONTEXT__CONSERVATIVE_BED", (0, 0, -0.55), (bed_x / 2, bed_y / 2, 0.5), bed_mat)
    inner_x = bed_x - 2 * reserve
    inner_y = bed_y - 2 * reserve
    rail = 0.65
    z = 0.12
    add_box("CONTEXT__RESERVE_FRONT", (0, -inner_y / 2, z), (inner_x / 2, rail, 0.35), reserve_mat)
    add_box("CONTEXT__RESERVE_REAR", (0, inner_y / 2, z), (inner_x / 2, rail, 0.35), reserve_mat)
    add_box("CONTEXT__RESERVE_LEFT", (-inner_x / 2, 0, z), (rail, inner_y / 2, 0.35), reserve_mat)
    add_box("CONTEXT__RESERVE_RIGHT", (inner_x / 2, 0, z), (rail, inner_y / 2, 0.35), reserve_mat)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.25
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.12, 0.14, 1.0)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7

    bpy.ops.object.light_add(type="AREA", location=(100, -130, 250))
    bpy.context.object.data.energy = 3200
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 160
    bpy.ops.object.light_add(type="AREA", location=(-150, 80, 130))
    bpy.context.object.data.energy = 2200
    bpy.context.object.data.size = 120
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.lens = 56
    scene.camera = camera

    target = (0, 0, 72)
    render(scene, camera, review_dir / "01-selected-orientation-isometric.png", (300, -320, 275), target)
    render(scene, camera, review_dir / "02-selected-orientation-opposite.png", (-300, 320, 245), target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 270
    render(scene, camera, review_dir / "03-selected-orientation-top.png", (0, 0, 420), (0, 0, 0))
    camera.data.ortho_scale = 230
    render(scene, camera, review_dir / "04-selected-orientation-side.png", (380, 0, 95), (0, 0, 80))

    final_vertices = [part.matrix_world @ vertex.co for vertex in part.data.vertices]
    dimensions = [
        max(v.x for v in final_vertices) - min(v.x for v in final_vertices),
        max(v.y for v in final_vertices) - min(v.y for v in final_vertices),
        max(v.z for v in final_vertices) - min(v.z for v in final_vertices),
    ]
    expected = config["audit_results"]["oriented_xyz_mm"]
    if any(abs(actual - target_value) > 0.01 for actual, target_value in zip(dimensions, expected)):
        raise RuntimeError(f"Oriented dimensions changed: {dimensions} != {expected}")

    metrics = {
        "review_id": config["review_id"],
        "geometry_change_mm": 0.0,
        "actual_oriented_xyz_mm": [round(value, 4) for value in dimensions],
        "expected_oriented_xyz_mm": expected,
        "dimension_check_tolerance_mm": 0.01,
        "dimension_check": "PASS",
        "production_export_created": False,
    }
    (output_dir / "orientation-validation-v1.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "right-ab-print-orientation-review-v1.blend"))


if __name__ == "__main__":
    main()
