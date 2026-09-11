#!/usr/bin/env python3
"""Render deterministic review evidence for the Rev113 merged mouth pane."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


def find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


ROOT = find_repo_root()
CONTRACT_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-merged-mouth-pane-rev113.json"
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


def material(name: str, color):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Metallic"].default_value = 0.04
    shader.inputs["Roughness"].default_value = 0.48
    return result


def look_at(camera, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


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
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    output = contract["output"]
    candidate = ROOT / output["candidate_directory"]
    bpy.ops.wm.read_factory_settings(use_empty=True)

    head = import_stl(ROOT / output["head_stl"], "Rev113FrozenHead")
    right_eye = import_stl(ROOT / output["right_eye_stl"], "Rev113RightEye")
    left_eye = import_stl(ROOT / output["left_eye_stl"], "Rev113LeftEye")
    merged_mouth = import_stl(ROOT / output["merged_mouth_stl"], "Rev113MergedMouth")
    bridge = import_stl(ROOT / output["bridge_review_stl"], "Rev113ReviewOnlyBridge")
    old_tri005 = import_stl(
        ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/head-rev112/CAT_HEAD_MEDIUM_MOUTH_TRI005_TRANSLUCENT_PANE_REV112.stl",
        "Rev112MouthTri005",
    )
    old_tri006 = import_stl(
        ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/head-rev112/CAT_HEAD_MEDIUM_MOUTH_TRI006_TRANSLUCENT_PANE_REV112.stl",
        "Rev112MouthTri006",
    )

    head.data.materials.append(material("Frozen structural head", (0.52, 0.58, 0.66)))
    pane_material = material("Final translucent pane evidence", (0.05, 0.72, 0.94))
    for pane in (right_eye, left_eye, merged_mouth):
        pane.data.materials.append(pane_material)
    old_tri005.data.materials.append(material("Original right mouth half", (0.06, 0.52, 0.94)))
    old_tri006.data.materials.append(material("Original left mouth half", (0.08, 0.78, 0.88)))
    bridge.data.materials.append(material("Seam-only bridge", (0.45, 1.0, 0.18)))

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
    for obj in (bridge, old_tri005, old_tri006):
        obj.hide_render = True
    render(
        candidate / "rev113-front-final-head-and-one-piece-mouth.png",
        Vector((0.0, -420.0, 96.0)),
        target,
        235.0,
    )
    render(
        candidate / "rev113-isometric-final-four-part-package.png",
        Vector((265.0, -360.0, 245.0)),
        target,
        250.0,
    )

    for obj in (head, right_eye, left_eye, merged_mouth):
        obj.hide_render = True
    for obj in (bridge, old_tri005, old_tri006):
        obj.hide_render = False
    mouth_target = Vector((0.0, 7.0, 20.0))
    render(
        candidate / "rev113-isolated-mouth-halves-and-seam-only-bridge.png",
        Vector((72.0, -120.0, 68.0)),
        mouth_target,
        62.0,
    )

    operation = contract["operation"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">
  <rect width="1200" height="700" fill="#0e1622"/>
  <text x="60" y="72" fill="#f6f8fb" font-family="sans-serif" font-size="34">Rev113 mouth merge — numeric seam contract</text>
  <polygon points="90,210 500,150 500,540 90,480" fill="#0f85ef" stroke="#8ec9ff" stroke-width="5"/>
  <polygon points="700,150 1110,210 1110,480 700,540" fill="#15bfcf" stroke="#9af7ff" stroke-width="5"/>
  <polygon points="500,150 700,150 700,540 500,540" fill="#73ff2e" stroke="#d3ffbd" stroke-width="5"/>
  <line x1="500" y1="610" x2="700" y2="610" stroke="#ffffff" stroke-width="4"/>
  <path d="M500 590 L500 630 M700 590 L700 630" stroke="#ffffff" stroke-width="4"/>
  <text x="420" y="665" fill="#ffffff" font-family="monospace" font-size="30">measured gap: {operation['measured_minimum_seam_gap_mm']:.6f} mm</text>
  <text x="430" y="115" fill="#d3ffbd" font-family="monospace" font-size="28">seam-only ruled bridge: {operation['expected_bridge_volume_mm3']:.4f} mm³</text>
  <text x="90" y="575" fill="#b8dcff" font-family="sans-serif" font-size="24">Rev112 TRI005 preserved</text>
  <text x="810" y="575" fill="#b8fbff" font-family="sans-serif" font-size="24">Rev112 TRI006 preserved</text>
</svg>'''
    (candidate / "rev113-dimensioned-seam-contract.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
