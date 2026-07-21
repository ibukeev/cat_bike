#!/usr/bin/env python3
"""Generate the simplified two-part eight-whisker carrier in Blender."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PACKAGE_ROOT / "config/whisker-carrier-v0.json"
OUTPUT_DIR = PACKAGE_ROOT / "output"
CONFIG: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def activate(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def box(name: str, size: tuple[float, float, float], location: tuple[float, float, float]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def cylinder(
    name: str,
    diameter: float,
    depth: float,
    location: tuple[float, float, float],
    vertices: int = 48,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=diameter / 2.0,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    return obj


def boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    activate(target)
    modifier = target.modifiers.new(name=f"{operation}_{tool.name}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def clean_mesh(obj: bpy.types.Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0001)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.0001)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def subtract_box(
    target: bpy.types.Object,
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
) -> None:
    boolean(target, box(name, size, location), "DIFFERENCE")


def subtract_hole(
    target: bpy.types.Object,
    name: str,
    diameter: float,
    depth: float,
    location: tuple[float, float, float],
    vertices: int = 48,
) -> None:
    boolean(target, cylinder(name, diameter, depth, location, vertices), "DIFFERENCE")


def pixel_centers() -> list[tuple[float, float]]:
    strip = CONFIG["led_strip"]
    pitch = float(strip["pixel_pitch_mm"])
    row_pitch = float(strip["row_center_spacing_mm"])
    count = int(strip["pixels_per_row"])
    xs = [(index - (count - 1) / 2.0) * pitch for index in range(count)]
    return [(x, y) for y in (row_pitch / 2.0, -row_pitch / 2.0) for x in xs]


def assembly_holes() -> list[tuple[float, float]]:
    assembly = CONFIG["assembly"]
    x = float(assembly["hole_x_mm"])
    y = float(assembly["hole_y_mm"])
    return [(-x, -y), (-x, y), (x, -y), (x, y)]


def build_base() -> bpy.types.Object:
    base_cfg = CONFIG["base"]
    strip = CONFIG["led_strip"]
    assembly = CONFIG["assembly"]
    length = float(base_cfg["total_length_with_mounting_ears_mm"])
    width = float(base_cfg["width_mm"])
    thickness = float(base_cfg["thickness_mm"])
    base = box("whisker_carrier_base", (length, width, thickness), (0.0, 0.0, thickness / 2.0))

    pocket_length = float(strip["four_pixel_cut_length_mm"]) + float(base_cfg["strip_channel_clearance_mm"])
    pocket_width = float(strip["strip_width_mm"]) + float(base_cfg["strip_channel_clearance_mm"])
    pocket_depth = float(base_cfg["strip_channel_depth_mm"])
    row_pitch = float(strip["row_center_spacing_mm"])
    for index, y in enumerate((row_pitch / 2.0, -row_pitch / 2.0), start=1):
        subtract_box(
            base,
            f"strip_channel_{index}",
            (pocket_length, pocket_width, pocket_depth + 0.2),
            (0.0, y, thickness - pocket_depth / 2.0 + 0.1),
        )

    nut_diameter = float(assembly["m2p5_nut_trap_diameter_mm"])
    for index, (x, y) in enumerate(assembly_holes(), start=1):
        subtract_hole(
            base,
            f"m2p5_nut_trap_{index}",
            nut_diameter,
            thickness + 2.0,
            (x, y, thickness / 2.0),
            vertices=6,
        )

    head_hole_x = float(base_cfg["head_mount_hole_x_mm"])
    head_hole = float(assembly["head_mount_clearance_diameter_mm"])
    for index, x in enumerate((-head_hole_x, head_hole_x), start=1):
        subtract_hole(
            base,
            f"head_mount_m3_{index}",
            head_hole,
            thickness + 2.0,
            (x, 0.0, thickness / 2.0),
        )
    clean_mesh(base)
    return base


def build_top() -> bpy.types.Object:
    top_cfg = CONFIG["top"]
    assembly = CONFIG["assembly"]
    fiber = CONFIG["fiber"]
    thickness = float(top_cfg["thickness_mm"])
    top = box(
        "whisker_carrier_top",
        (float(top_cfg["length_mm"]), float(top_cfg["width_mm"]), thickness),
        (0.0, 0.0, thickness / 2.0),
    )

    collar_outer_diameter = float(fiber["guide_collar_outer_diameter_mm"])
    collar_height = float(fiber["guide_collar_height_mm"])
    for index, (x, y) in enumerate(pixel_centers(), start=1):
        collar = cylinder(
            f"fiber_guide_collar_{index}",
            collar_outer_diameter,
            collar_height,
            (x, y, thickness + collar_height / 2.0),
        )
        boolean(top, collar, "UNION")

    cavity_depth = float(top_cfg["cell_cavity_depth_mm"])
    for index, (x, y) in enumerate(pixel_centers(), start=1):
        subtract_box(
            top,
            f"light_cell_{index}",
            (
                float(top_cfg["cell_cavity_length_mm"]),
                float(top_cfg["cell_cavity_width_mm"]),
                cavity_depth + 0.2,
            ),
            (x, y, cavity_depth / 2.0 - 0.1),
        )
        subtract_hole(
            top,
            f"fiber_hole_{index}",
            float(fiber["top_hole_diameter_mm"]),
            thickness + 2.0,
            (x, y, thickness / 2.0),
        )

    relief_length = float(top_cfg["wire_relief_length_mm"])
    relief_width = float(top_cfg["wire_relief_width_mm"])
    relief_depth = float(top_cfg["wire_relief_depth_mm"])
    relief_x = float(top_cfg["length_mm"]) / 2.0 - relief_length / 2.0 + 0.1
    for index, side in enumerate((-1.0, 1.0), start=1):
        subtract_box(
            top,
            f"wire_relief_{index}",
            (relief_length + 0.2, relief_width, relief_depth + 0.2),
            (side * relief_x, 0.0, relief_depth / 2.0 - 0.1),
        )

    screw_diameter = float(assembly["m2p5_clearance_diameter_mm"])
    for index, (x, y) in enumerate(assembly_holes(), start=1):
        subtract_hole(
            top,
            f"top_m2p5_clearance_{index}",
            screw_diameter,
            thickness + 2.0,
            (x, y, thickness / 2.0),
        )
    clean_mesh(top)
    return top


def mesh_report(obj: bpy.types.Object) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(bm.calc_volume(signed=True)) if nonmanifold == 0 else None
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": round(volume, 2) if volume is not None else None,
        "dimensions_mm": [round(float(value), 3) for value in obj.dimensions],
    }
    bm.free()
    return result


def export_stl(obj: bpy.types.Object, filename: str) -> None:
    activate(obj)
    bpy.ops.wm.stl_export(
        filepath=str(OUTPUT_DIR / filename),
        export_selected_objects=True,
        ascii_format=False,
    )


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    return result


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_review(base: bpy.types.Object, top: bpy.types.Object) -> None:
    base_cfg = CONFIG["base"]
    top_cfg = CONFIG["top"]
    strip = CONFIG["led_strip"]
    black = material("Base_Black", (0.04, 0.05, 0.06, 1.0))
    grey = material("Top_Grey", (0.35, 0.38, 0.42, 1.0))
    copper = material("PCB_Copper", (0.45, 0.08, 0.02, 1.0))
    white = material("LED_White", (0.8, 0.82, 0.85, 1.0))
    cyan = material("Fiber_Cyan", (0.0, 0.75, 1.0, 1.0))
    base.data.materials.append(black)
    top.data.materials.append(grey)

    base_thickness = float(base_cfg["thickness_mm"])
    top.location.z = base_thickness + 8.0
    pcb_z = base_thickness - float(base_cfg["strip_channel_depth_mm"]) + 0.15
    row_pitch = float(strip["row_center_spacing_mm"])
    for row, y in enumerate((row_pitch / 2.0, -row_pitch / 2.0), start=1):
        pcb = box(
            f"review_pcb_{row}",
            (
                float(strip["four_pixel_cut_length_mm"]),
                float(strip["strip_width_mm"]),
                0.3,
            ),
            (0.0, y, pcb_z),
        )
        pcb.data.materials.append(copper)

    for index, (x, y) in enumerate(pixel_centers(), start=1):
        led = box(f"review_led_{index}", (5.0, 5.0, 1.6), (x, y, pcb_z + 0.95))
        led.data.materials.append(white)
        fiber = cylinder(
            f"review_fiber_{index}",
            float(CONFIG["fiber"]["nominal_diameter_mm"]),
            35.0,
            (x, y, 31.0),
            vertices=32,
        )
        fiber.data.materials.append(cyan)

    bpy.ops.object.camera_add(location=(125.0, -145.0, 105.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 125.0
    point_at(camera, (0.0, 0.0, 10.0))
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_object_outline = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.92, 0.93, 0.94)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT_DIR / "whisker-carrier-v0-review.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "whisker-carrier-v0-review.blend")
    )
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "whisker-carrier-v0-review.glb"),
        export_format="GLB",
        use_selection=False,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_scene()
    base = build_base()
    top = build_top()
    parts = [
        (base, "whisker-carrier-base.stl"),
        (
            top,
            f"whisker-carrier-top-{float(CONFIG['fiber']['top_hole_diameter_mm']):.2f}".replace(".", "p")
            + ".stl",
        ),
    ]

    report: dict[str, Any] = {
        "schema_version": 2,
        "pixel_centers_mm": pixel_centers(),
        "parts": {},
        "checks": {},
    }
    for obj, filename in parts:
        export_stl(obj, filename)
        report["parts"][filename] = mesh_report(obj)

    part_reports = list(report["parts"].values())
    report["checks"] = {
        "part_count_is_two": len(parts) == 2,
        "all_parts_closed_manifold": all(
            item["nonmanifold_edges"] == 0 for item in part_reports
        ),
        "all_parts_have_positive_volume": all(
            item["volume_mm3"] is not None and item["volume_mm3"] > 0
            for item in part_reports
        ),
        "eight_unique_pixel_centers": len(set(pixel_centers())) == 8,
        "pitch_matches_four_pixel_length": math.isclose(
            float(CONFIG["led_strip"]["pixel_pitch_mm"]) * 4.0,
            float(CONFIG["led_strip"]["four_pixel_cut_length_mm"]),
            abs_tol=0.05,
        ),
        "current_matches_eight_pixels": math.isclose(
            float(CONFIG["electrical_interface"]["maximum_whisker_carrier_current_a"]),
            8.0 * 0.06,
            abs_tol=0.001,
        ),
        "guide_collars_clear_adjacent_pixels": (
            float(CONFIG["fiber"]["guide_collar_outer_diameter_mm"])
            < min(
                float(CONFIG["led_strip"]["pixel_pitch_mm"]),
                float(CONFIG["led_strip"]["row_center_spacing_mm"]),
            )
        ),
    }
    report["checks"]["pass"] = all(report["checks"].values())
    (OUTPUT_DIR / "whisker-carrier-v0-validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    build_review(base, top)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
