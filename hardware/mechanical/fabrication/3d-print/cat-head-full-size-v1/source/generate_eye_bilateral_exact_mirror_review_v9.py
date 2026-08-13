"""Build the V9 bilateral-eye visual review from validated FreeCAD owners.

This script is review-only. It hides the obsolete Gate 8 bucket/cap meshes,
imports the four validated V9 owner meshes, and renders opaque whole-head and
isolated bilateral context. It does not generate or alter production CAD.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> tuple[Path, Path, Path]:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 3:
        raise SystemExit("usage: script.py -- BASELINE_BLEND REVIEW_DIR OUTPUT_BLEND")
    return tuple(Path(value).resolve() for value in args)  # type: ignore[return-value]


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.58
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def import_obj(path: Path, name: str, mat: bpy.types.Material) -> bpy.types.Object:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    # FreeCAD OBJ export uses Y-up coordinates: (X, Y, Z) becomes
    # Blender (X, -Z, Y). Restore the repository Z-up world frame.
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, z, -y)
    assign_material(obj, mat)
    return obj


def look_at(camera: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def ensure_camera() -> bpy.types.Object:
    camera = bpy.data.objects.get("REVIEW_CAMERA_V9")
    if camera is None:
        camera_data = bpy.data.cameras.new("REVIEW_CAMERA_V9")
        camera = bpy.data.objects.new("REVIEW_CAMERA_V9", camera_data)
        bpy.context.scene.collection.objects.link(camera)
    camera.data.lens = 52
    bpy.context.scene.camera = camera
    return camera


def add_area_light(name: str, location: tuple[float, float, float], energy: float, size: float):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, (0.0, 90.0, 145.0))


def render(path: Path, camera_location: tuple[float, float, float], target, lens: float) -> None:
    camera = ensure_camera()
    camera.location = camera_location
    camera.data.lens = lens
    look_at(camera, target)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    baseline_blend, review_dir, output_blend = parse_args()
    review_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(baseline_blend))

    obsolete = {
        "left_eye_bucket",
        "left_eye_led_rear_cap",
        "right_eye_bucket",
        "right_eye_led_rear_cap",
    }
    context_mat = material("FROZEN_HEAD_CONTEXT_V9", (0.62, 0.66, 0.70, 1.0))
    right_bucket_mat = material("V9_RIGHT_BUCKET", (1.0, 0.24, 0.025, 1.0))
    right_cap_mat = material("V9_RIGHT_CAP", (0.64, 0.035, 0.012, 1.0))
    left_bucket_mat = material("V9_LEFT_BUCKET", (0.015, 0.55, 1.0, 1.0))
    left_cap_mat = material("V9_LEFT_CAP", (0.005, 0.18, 0.68, 1.0))

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        obj.hide_render = obj.name in obsolete
        obj.hide_set(obj.name in obsolete)
        if obj.name not in obsolete:
            assign_material(obj, context_mat)

    new_objects = {
        "right_bucket": import_obj(
            review_dir / "review_only_right_eye_bucket_v9.obj",
            "PROPOSED__RIGHT_EYE_BUCKET__V9",
            right_bucket_mat,
        ),
        "right_cap": import_obj(
            review_dir / "review_only_right_eye_rear_cap_v9.obj",
            "PROPOSED__RIGHT_EYE_REAR_CAP__V9",
            right_cap_mat,
        ),
        "left_bucket": import_obj(
            review_dir / "review_only_left_eye_bucket_v9.obj",
            "PROPOSED__LEFT_EYE_BUCKET__EXACT_X0_MIRROR_V9",
            left_bucket_mat,
        ),
        "left_cap": import_obj(
            review_dir / "review_only_left_eye_rear_cap_v9.obj",
            "PROPOSED__LEFT_EYE_REAR_CAP__EXACT_X0_MIRROR_V9",
            left_cap_mat,
        ),
    }

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.075, 0.085, 0.105, 1.0)
    background.inputs["Strength"].default_value = 0.8

    add_area_light("V9_KEY", (310.0, -340.0, 430.0), 2600.0, 250.0)
    add_area_light("V9_FILL", (-300.0, -120.0, 260.0), 1800.0, 220.0)
    add_area_light("V9_REAR", (0.0, 420.0, 300.0), 2200.0, 210.0)

    render(
        review_dir / "01-v9-whole-head-front.png",
        (0.0, -560.0, 175.0),
        (0.0, 118.0, 155.0),
        58.0,
    )
    render(
        review_dir / "02-v9-whole-head-rear-interior.png",
        (0.0, 510.0, 220.0),
        (0.0, 102.0, 152.0),
        58.0,
    )

    context_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj not in new_objects.values()
    ]
    for obj in context_objects:
        obj.hide_render = True
        obj.hide_set(True)

    render(
        review_dir / "03-v9-bilateral-owners-isolated-front.png",
        (0.0, -280.0, 155.0),
        (0.0, 78.0, 150.0),
        66.0,
    )
    render(
        review_dir / "04-v9-bilateral-owners-isolated-rear.png",
        (0.0, 325.0, 175.0),
        (0.0, 80.0, 150.0),
        70.0,
    )

    for obj in context_objects:
        obj.hide_render = False
        obj.hide_set(False)
    for name in obsolete:
        if bpy.data.objects.get(name):
            bpy.data.objects[name].hide_render = True
            bpy.data.objects[name].hide_set(True)

    scene["V9_REVIEW_ONLY"] = True
    scene["V9_MIRROR_PLANE"] = "X=0 / YZ"
    scene["V9_RIGHT_BUCKET_VOLUME_MM3"] = 6649.60
    scene["V9_LEFT_BUCKET_VOLUME_MM3"] = 6649.60
    scene["V9_RIGHT_CAP_VOLUME_MM3"] = 4212.35
    scene["V9_LEFT_CAP_VOLUME_MM3"] = 4212.35
    scene["V9_BUCKET_CROSS_CENTERLINE_CLEARANCE_MM"] = 54.9791
    scene["V9_CAP_CROSS_CENTERLINE_CLEARANCE_MM"] = 51.8270
    scene["V9_PRINT_RELEASE"] = False
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))


if __name__ == "__main__":
    main()
