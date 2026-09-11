#!/usr/bin/env python3
"""Render deterministic front and isometric evidence images for Rev112."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


def find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


ROOT = find_repo_root()
CONTRACT = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-final-user-cutter-holes-rev112.json"
)


def import_stl(path: Path, name: str):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path))
    created = [obj for obj in bpy.data.objects if obj not in before]
    if len(created) != 1:
        raise RuntimeError(f"Expected one imported object for {path.name}")
    obj = created[0]
    obj.name = name
    return obj


def material(name: str, color, metallic: float, roughness: float):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return result


def look_at(camera, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location, energy: float, size: float, target: Vector):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def render(path: Path, camera_location, target: Vector, ortho_scale: float) -> None:
    camera = bpy.data.objects["EvidenceCamera"]
    camera.location = camera_location
    look_at(camera, target)
    camera.data.ortho_scale = ortho_scale
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"Evidence render failed: {path.name}")


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    output = contract["output"]
    candidate = ROOT / output["candidate_directory"]
    bpy.ops.wm.read_factory_settings(use_empty=True)

    head = import_stl(ROOT / output["head_stl"], "Rev112FinalHead")
    pane_paths = (
        output["right_eye_stl"],
        output["left_eye_stl"],
        output["mouth_tri005_stl"],
        output["mouth_tri006_stl"],
    )
    panes = [
        import_stl(ROOT / relative, f"Rev112Pane{index}")
        for index, relative in enumerate(pane_paths, start=1)
    ]
    head.data.materials.append(material("Opaque structural head", (0.52, 0.58, 0.66), 0.05, 0.62))
    pane_material = material("Translucent panel evidence", (0.06, 0.73, 0.92), 0.05, 0.25)
    for pane in panes:
        pane.data.materials.append(pane_material)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("EvidenceWorld")
    scene.world.color = (0.018, 0.025, 0.038)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.6
    scene.display.shading.curvature_valley_factor = 1.2
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.055, 0.070, 0.095)

    camera_data = bpy.data.cameras.new("EvidenceCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("EvidenceCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    target = Vector((0.0, 62.0, 96.0))
    add_area_light("Key", (-180.0, -220.0, 300.0), 1650.0, 150.0, target)
    add_area_light("Fill", (190.0, -90.0, 155.0), 950.0, 120.0, target)
    add_area_light("Rim", (0.0, 260.0, 250.0), 1300.0, 110.0, target)

    for pane in panes:
        pane.hide_render = True
    render(
        candidate / "rev112-front-final-head-cut-holes.png",
        Vector((0.0, -420.0, 96.0)),
        target,
        235.0,
    )

    for pane in panes:
        pane.hide_render = False
    render(
        candidate / "rev112-isometric-final-head-and-panes.png",
        Vector((265.0, -360.0, 245.0)),
        target,
        250.0,
    )


if __name__ == "__main__":
    main()
