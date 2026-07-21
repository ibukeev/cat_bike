#!/usr/bin/env python3
"""Export the accepted Gate 7 head as a complete 100 mm test-print package."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
GATE7_CONFIG = PACKAGE_ROOT / "config/gate7-glow-panel-inserts.json"
GATE7_BLEND = (
    PACKAGE_ROOT
    / "output/gate7-glow-panel-inserts/gate7-glow-panel-inserts-review.blend"
)
GATE6_VALIDATION = (
    PACKAGE_ROOT
    / "output/gate6-eye-modules/gate6-eye-module-validation.json"
)
OUTPUT_DIR = PACKAGE_ROOT / "output/gate7-small-test-print-100mm"
SHELL_DIR = OUTPUT_DIR / "shells"
INSERT_DIR = OUTPUT_DIR / "glow-inserts"
EYE_DIR = OUTPUT_DIR / "eye-modules"

EYE_PARTS = (
    "right_eye_bucket",
    "right_eye_diffuser",
    "right_eye_led_rear_cap",
    "left_eye_bucket",
    "left_eye_diffuser",
    "left_eye_led_rear_cap",
)


def merged_component_z_intervals(
    obj: bpy.types.Object, tolerance: float = 1e-5
) -> list[list[float]]:
    intervals = sorted(
        (
            min(
                (obj.matrix_world @ obj.data.vertices[index].co).z
                for index in component
            ),
            max(
                (obj.matrix_world @ obj.data.vertices[index].co).z
                for index in component
            ),
        )
        for component in gate5.components(obj)
    )
    merged: list[list[float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + tolerance:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [[round(start, 4), round(end, 4)] for start, end in merged]


def part_metrics(obj: bpy.types.Object) -> dict[str, Any]:
    boundary, nonmanifold = gate5.topology_counts(obj)
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "connected_components": len(gate5.components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "dimensions_mm_sorted": [
            round(float(value), 3) for value in sorted(obj.dimensions)
        ],
        "merged_component_z_intervals_mm": merged_component_z_intervals(obj),
    }


def scaled_copy(obj: bpy.types.Object, factor: float) -> bpy.types.Object:
    duplicate = gate6.duplicate_scaled(obj, f"small_{obj.name}", factor)
    duplicate.location = obj.location * factor
    return duplicate


def overall_dimensions(objects: list[bpy.types.Object]) -> list[float]:
    points = [
        obj.matrix_world @ vertex.co
        for obj in objects
        for vertex in obj.data.vertices
    ]
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return [round(maximum[axis] - minimum[axis], 3) for axis in range(3)]


def main() -> None:
    config = json.loads(GATE7_CONFIG.read_text(encoding="utf-8"))
    gate6_validation = json.loads(
        GATE6_VALIDATION.read_text(encoding="utf-8")
    )
    target_height = float(config["small_model_head_height_mm"])
    source_height = float(config["source_head_height_mm"])
    scale = target_height / source_height

    for directory in (OUTPUT_DIR, SHELL_DIR, INSERT_DIR, EYE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    for directory in (SHELL_DIR, INSERT_DIR, EYE_DIR):
        for stale in directory.glob("*.stl"):
            stale.unlink()

    bpy.ops.wm.open_mainfile(filepath=str(GATE7_BLEND))
    source_objects = {
        obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"
    }
    shell_names = tuple(gate2.SECTION_ORDER)
    insert_names = tuple(
        sorted(name for name in source_objects if name.startswith("glow_insert_"))
    )
    required = {*shell_names, *EYE_PARTS, *insert_names}
    missing = sorted(required - source_objects.keys())
    if missing:
        raise ValueError(f"Gate 7 review is missing test-print parts: {missing}")

    categories = {
        "shells": (shell_names, SHELL_DIR),
        "glow_inserts": (insert_names, INSERT_DIR),
        "eye_modules": (EYE_PARTS, EYE_DIR),
    }
    scaled_parts: list[bpy.types.Object] = []
    manifest_parts: dict[str, Any] = {}
    for category, (names, directory) in categories.items():
        category_parts = []
        for name in names:
            part = scaled_copy(source_objects[name], scale)
            gate5.export_stl(part, directory / f"{part.name}.stl")
            category_parts.append(part)
            scaled_parts.append(part)
        manifest_parts[category] = {
            part.name: part_metrics(part) for part in category_parts
        }

    gate6.export_selected(
        OUTPUT_DIR / "cat_head_100mm_visual_assembly.stl", scaled_parts
    )

    source_meshes = [
        obj for obj in list(bpy.context.scene.objects) if obj.type == "MESH"
        and obj not in scaled_parts
    ]
    for obj in source_meshes:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "cat_head_100mm_test_print_review.blend")
    )

    all_closed = all(
        value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
        for category in manifest_parts.values()
        for value in category.values()
    )
    overall = overall_dimensions(scaled_parts)
    height_is_target = abs(overall[2] - target_height) <= 0.05
    eye_head_mounts_valid = gate6_validation["acceptance"].get(
        "all_head_mount_tabs_intersect_their_printed_owners", False
    )
    no_vertically_isolated_shell_components = all(
        len(value["merged_component_z_intervals_mm"]) == 1
        for value in manifest_parts["shells"].values()
    )
    manifest = {
        "source": str(GATE7_BLEND.relative_to(PACKAGE_ROOT)),
        "target_head_height_mm": target_height,
        "uniform_scale": round(scale, 6),
        "overall_dimensions_xyz_mm": overall,
        "print_part_count": len(scaled_parts),
        "parts": manifest_parts,
        "acceptance": {
            "seven_shell_parts_exported": len(manifest_parts["shells"]) == 7,
            "seven_glow_inserts_exported": len(manifest_parts["glow_inserts"]) == 7,
            "six_eye_module_parts_exported": len(manifest_parts["eye_modules"]) == 6,
            "all_exported_parts_closed_manifold": all_closed,
            "eye_head_mounts_have_valid_attachment_paths": eye_head_mounts_valid,
            "no_vertically_isolated_shell_components": (
                no_vertically_isolated_shell_components
            ),
            "assembled_height_is_100mm": height_is_target,
            "review_blend_created": (
                OUTPUT_DIR / "cat_head_100mm_test_print_review.blend"
            ).exists(),
            "combined_visual_assembly_created": (
                OUTPUT_DIR / "cat_head_100mm_visual_assembly.stl"
            ).exists(),
        },
        "limitations": [
            "This uniform-scale model is for visual, fit, seam, and material testing.",
            "M3 and M2.5 holes are scaled to about 30.3 percent and do not accept the original hardware.",
            "Use glue, tape, or temporary pins for the 100 mm assembly; validate real fasteners on full-size coupons.",
            "Thin walls, ribs, roots, and retaining features are also uniformly scaled and may require a 0.25 mm nozzle or slicer thin-wall support.",
        ],
    }
    if not all(manifest["acceptance"].values()):
        failures = [
            name for name, passed in manifest["acceptance"].items() if not passed
        ]
        raise ValueError(f"100 mm test-print validation failed: {failures}")
    (OUTPUT_DIR / "test-print-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    print(f"Wrote {OUTPUT_DIR.relative_to(PACKAGE_ROOT)}")


if __name__ == "__main__":
    main()
