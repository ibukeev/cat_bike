#!/usr/bin/env python3
"""Build two additive right-eye wall continuations for isolated review.

The accepted six-source eye bucket is frozen.  This script does not rebuild,
replace, trim, or cut it.  It emits only two short pieces that continue the
existing baffle-wall cross-section toward the front bezel at the user-approved
face pairs 67/246 and 45/338.

Outputs are review inputs, not fabrication exports.
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
    / "right-eye-additive-wall-continuation-review-v5"
)
OUTPUT_BLEND = OUTPUT_DIR / "right-eye-additive-wall-continuations-v5.blend"
OUTPUT_JSON = OUTPUT_DIR / "additive-wall-continuation-contract-v5.json"


def wall_segment(
    name: str,
    outer: list[Vector],
    inner: list[Vector],
    edge_index: int,
    inward: Vector,
    start_depth: float,
    end_depth: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Continue one existing main-wall cross-section toward the front plank."""
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
        filepath=str(path),
        export_selected_objects=True,
        ascii_format=False,
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
    diffuser_loop = gate6.radial_offset_loop(
        aperture, float(values["diffuser_perimeter_overlap_mm"])
    )
    pocket_loop = gate6.radial_offset_loop(
        diffuser_loop, float(values["diffuser_pocket_clearance_mm"])
    )
    baffle_outer = gate6.radial_offset_loop(
        pocket_loop, float(values["baffle_wall_thickness_mm"])
    )

    bezel_back = float(values["front_bezel_thickness_mm"])
    baffle_front = max(0.0, bezel_back - 0.3)
    continuation_start_depth = 0.0
    continuation_end_depth = 2.0
    main_wall_overlap_mm = continuation_end_depth - baffle_front

    material_a = gate6.gate5.material(
        "Review bridge Face67 to Face246", (0.10, 0.72, 0.20, 1.0)
    )
    material_b = gate6.gate5.material(
        "Review bridge Face45 to Face338", (0.98, 0.55, 0.05, 1.0)
    )

    bridge_a = wall_segment(
        "PROPOSED__RIGHT_EYE__ADDITIVE_WALL_CONTINUATION_FACE67_TO_FACE246_V5",
        baffle_outer,
        pocket_loop,
        0,
        inward,
        continuation_start_depth,
        continuation_end_depth,
        material_a,
    )
    bridge_b = wall_segment(
        "PROPOSED__RIGHT_EYE__ADDITIVE_WALL_CONTINUATION_FACE45_TO_FACE338_V5",
        baffle_outer,
        pocket_loop,
        1,
        inward,
        continuation_start_depth,
        continuation_end_depth,
        material_b,
    )

    for bridge in (bridge_a, bridge_b):
        gate6.gate5.require_manifold(bridge, bridge.name)
        export_selected(bridge, OUTPUT_DIR / f"{bridge.name}.stl")

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))

    contract = {
        "status": "REVIEW_ONLY",
        "problem": "Continue the untouched main eye body to the two disconnected front-plank wall segments.",
        "frozen_owner": "PROPOSED__RIGHT_EYE_BUCKET__SIX_SOURCE_POST_CLEARANCE_V1",
        "frozen_rear_cap": "PROPOSED__RIGHT_EYE_REAR_CAP__ONE_BODY_V1_ref",
        "approved_face_pairs": [[67, 246], [45, 338]],
        "operation": "additive_only_wall_continuations",
        "wall_thickness_mm": float(values["baffle_wall_thickness_mm"]),
        "depth_range_mm": [continuation_start_depth, continuation_end_depth],
        "main_wall_overlap_mm": main_wall_overlap_mm,
        "plane_rule": "continue the untouched main-wall cross-section through the front overlap zone",
        "baseline_cut_or_replaced": False,
        "production_gate6_modified": False,
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
