#!/usr/bin/env python3
"""Run the Gate 9 comparison with current configuration ownership/API fixes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


original_load_repo_json = comparison.load_repo_json


def load_repo_json_with_gate1_height(relative_path: str) -> dict:
    data = original_load_repo_json(relative_path)
    if relative_path == (
        "hardware/mechanical/fabrication/3d-print/"
        "cat-head-full-size-v1/config/gate2-section-layout.json"
    ):
        gate1_config = json.loads(
            gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
        )
        data["target_height_mm"] = float(
            gate1_config["target_height_mm"]
        )
    return data


def configure_render_for_installed_blender(output_dir: Path) -> None:
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1120
    scene.render.resolution_y = 840
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.018, 0.024, 0.036)

    camera_data = bpy.data.cameras.new("Gate9_Camera")
    camera = bpy.data.objects.new("Gate9_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.lens = 58

    for name, location, energy, size in (
        ("Gate9_Key", (350.0, -300.0, 480.0), 1500.0, 260.0),
        ("Gate9_Fill", (-360.0, 20.0, 300.0), 1100.0, 240.0),
        ("Gate9_Rear", (40.0, 560.0, 420.0), 1300.0, 220.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        comparison.point_camera(
            light, Vector((0.0, 175.0, 165.0))
        )


comparison.load_repo_json = load_repo_json_with_gate1_height
comparison.configure_render = configure_render_for_installed_blender


if __name__ == "__main__":
    comparison.main()
