#!/usr/bin/env python3
"""Right-eye review: omit two floating bezel strips and extend main walls.

This emits four isolated replacement solids:

* exact retained bezel segments 2 and 3;
* main-wall segment 0 extended to the front plane;
* main-wall segment 1 extended to the front plane.

The accepted main baffle body is not emitted or modified here.  FreeCAD keeps
that source owner frozen and assembles these pieces around it for review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate6_eye_modules as gate6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = (
    PACKAGE_ROOT
    / "output/70-freecad-pilots/opposite-side-flange-pilot-v1"
    / "right-eye-delete-strips-extend-walls-review-v6"
)
OUTPUT_BLEND = OUTPUT_DIR / "right-eye-delete-strips-extend-walls-v6.blend"
OUTPUT_JSON = OUTPUT_DIR / "delete-strips-extend-walls-contract-v6.json"


def segment_prism(
    name: str,
    outer: list[Vector],
    inner: list[Vector],
    edge_index: int,
    inward: Vector,
    start_depth: float,
    end_depth: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    following = (edge_index + 1) % len(outer)
    section = [outer[edge_index], outer[following], inner[following], inner[edge_index]]
    return gate6.polygon_prism(
        name, section, inward, start_depth, end_depth, material
    )


def export_selected(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path), export_selected_objects=True, ascii_format=False
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    geometry = gate6.eye_geometry()[0]
    if geometry["side"] != "right":
        raise ValueError("Expected right eye first in Gate 6 geometry")

    values = gate6.CONFIG["module"]
    inward = geometry["inward"]
    aperture = geometry["aperture"]
    outer_fit = gate6.radial_offset_loop(
        geometry["outer"], -float(values["opening_clearance_mm"])
    )
    diffuser_loop = gate6.radial_offset_loop(
        aperture, float(values["diffuser_perimeter_overlap_mm"])
    )
    pocket_loop = gate6.radial_offset_loop(
        diffuser_loop, float(values["diffuser_pocket_clearance_mm"])
    )
    baffle_outer = gate6.radial_offset_loop(
        pocket_loop, float(values["baffle_wall_thickness_mm"])
    )

    bezel_depth = float(values["front_bezel_thickness_mm"])
    main_wall_front = max(0.0, bezel_depth - 0.3)
    extension_overlap = 0.15
    extension_end = main_wall_front + extension_overlap

    retained_material = gate6.gate5.material(
        "Retained exact bezel", (0.64, 0.67, 0.70, 1.0)
    )
    extension_material = gate6.gate5.material(
        "Main wall extensions", (0.10, 0.72, 0.20, 1.0)
    )

    outputs: list[bpy.types.Object] = []
    for edge_index in (2, 3):
        outputs.append(
            segment_prism(
                f"FROZEN_EQUIVALENT__RIGHT_EYE__RETAINED_BEZEL_SEGMENT_{edge_index}_V6",
                outer_fit,
                aperture,
                edge_index,
                inward,
                0.0,
                bezel_depth,
                retained_material,
            )
        )

    for edge_index, anchor in ((0, "FACE682"), (1, "FACE679")):
        outputs.append(
            segment_prism(
                f"PROPOSED__RIGHT_EYE__EXTEND_{anchor}_TO_FACE55_PLANE_V6",
                baffle_outer,
                pocket_loop,
                edge_index,
                inward,
                0.0,
                extension_end,
                extension_material,
            )
        )

    for obj in outputs:
        gate6.gate5.require_manifold(obj, obj.name)
        export_selected(obj, OUTPUT_DIR / f"{obj.name}.stl")

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))

    contract = {
        "status": "REVIEW_ONLY",
        "operation": "delete_two_floating_front_strips_and_extend_two_main_walls",
        "selected_main_faces": [679, 682],
        "termination_plane_face": 55,
        "omitted_original_bezel_segments": [0, 1],
        "retained_exact_bezel_segments": [2, 3],
        "main_wall_extension_segments": [0, 1],
        "termination_depth_mm": 0.0,
        "main_wall_original_front_depth_mm": main_wall_front,
        "extension_end_depth_mm": extension_end,
        "owner_overlap_mm": extension_overlap,
        "main_wall_thickness_mm": float(values["baffle_wall_thickness_mm"]),
        "production_generator_modified": False,
        "holds": [
            "left_mirror",
            "production_integration",
            "STL_print_release",
            "slicing",
            "ASA_printing",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
