#!/usr/bin/env python3
"""Render consistent exterior and internal review views of the Gate 8 assembly."""

from pathlib import Path

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PACKAGE_ROOT / "output/gate8-full-size-structural-iteration"
BLEND_PATH = OUTPUT_DIR / "gate8-full-size-structural-review.blend"
RENDER_DIR = OUTPUT_DIR / "review-renders"


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location: tuple[float, float, float], energy: float) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = 240.0
    light = bpy.data.objects.new(name, data)
    light.location = location
    bpy.context.scene.collection.objects.link(light)
    point_at(light, Vector((0.0, 110.0, 160.0)))


def main() -> None:
    if Path(bpy.data.filepath).resolve() != BLEND_PATH.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.12, 0.14, 0.17)

    camera_data = bpy.data.cameras.new("Gate8_review_camera")
    camera_data.lens = 58.0
    camera = bpy.data.objects.new("Gate8_review_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    add_area_light("Gate8_key", (330.0, -300.0, 450.0), 1500.0)
    add_area_light("Gate8_fill", (-330.0, -180.0, 280.0), 1000.0)
    add_area_light("Gate8_rear", (0.0, 500.0, 360.0), 1300.0)

    views = {
        "gate8-front": (
            (0.0, -520.0, 170.0), False, (0.0, 112.0, 160.0), 58.0
        ),
        "gate8-front-right": (
            (430.0, -300.0, 240.0), False, (0.0, 112.0, 160.0), 58.0
        ),
        "gate8-rear": (
            (0.0, 660.0, 175.0), False, (0.0, 112.0, 160.0), 58.0
        ),
        "gate8-rear-internal": (
            (0.0, 600.0, 180.0), True, (0.0, 112.0, 160.0), 58.0
        ),
        "gate8-integral-sockets-internal": (
            (0.0, 48.0, 215.0), True, (0.0, 126.0, 203.0), 55.0
        ),
    }
    rear_base = bpy.data.objects.get("rear_base")
    for name, (location, hide_rear_base, target, lens) in views.items():
        if rear_base is not None:
            rear_base.hide_render = hide_rear_base
        camera.location = location
        camera.data.lens = lens
        point_at(camera, Vector(target))
        scene.render.filepath = str(RENDER_DIR / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    if rear_base is not None:
        rear_base.hide_render = False
    print(f"Wrote {RENDER_DIR}")


if __name__ == "__main__":
    main()
