#!/usr/bin/env python3
"""Render clean assembled and under-ear review views from the V11 blend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


FULL_SHELL_OBJECTS = {
    "gate9_v11__left_upper_head",
    "gate9_v11__right_upper_head",
    "gate9_v11__left_ear",
    "gate9_v11__right_ear",
    "gate9_v11__rear_bezel",
    "gate9_v11__left_under_ear_insert",
    "gate9_v11__right_under_ear_insert",
    "gate9_v9__left_lower_face",
    "gate9_v9__right_lower_face",
    "gate9_v9__bottom_keel",
    "gate9_v9__left_socket_cap",
    "gate9_v9__right_socket_cap",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = (
        sys.argv[sys.argv.index("--") + 1 :]
        if "--" in sys.argv
        else sys.argv[1:]
    )
    return parser.parse_args(args)


def set_visible(names: set[str]) -> None:
    for obj in bpy.context.scene.objects:
        show = obj.name in names
        obj.hide_viewport = False
        obj.hide_render = not show
        obj.hide_set(not show)
    bpy.context.view_layer.update()


def render_view(
    camera: bpy.types.Object,
    output_path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    ortho_scale: float,
) -> None:
    camera.location = Vector(location)
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = ortho_scale
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.025, 0.025)

    camera_data = bpy.data.cameras.new("gate9_v11_review_camera")
    camera = bpy.data.objects.new("gate9_v11_review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    scene.camera = camera

    set_visible(FULL_SHELL_OBJECTS)
    render_view(
        camera,
        output_dir / "gate9-v11-full-three-quarter.png",
        (-390.0, -255.0, 285.0),
        (0.0, 165.0, 165.0),
        405.0,
    )

    for side, x_sign in (("left", -1.0), ("right", 1.0)):
        names = {
            f"gate9_v11__{side}_upper_head",
            f"gate9_v11__{side}_ear",
            f"gate9_v11__{side}_under_ear_insert",
            "gate9_v11__rear_bezel",
        }
        set_visible(names)
        render_view(
            camera,
            output_dir / f"gate9-v11-{side}-under-ear-detail.png",
            (285.0 * x_sign, 86.0, 245.0),
            (82.0 * x_sign, 173.0, 227.0),
            190.0,
        )


if __name__ == "__main__":
    main()
