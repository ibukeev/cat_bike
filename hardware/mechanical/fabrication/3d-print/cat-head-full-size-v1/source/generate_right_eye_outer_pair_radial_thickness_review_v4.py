#!/usr/bin/env python3
"""Build the right outer eye/head pair with plain radial thickness additions.

V4 rejects the V2 broad bases and V3 depth extensions.  It preserves the
existing eye-bucket flange and reconstructs the matching head member as the
original plain 12 x 8 x 2.4 mm bar.  Each member gains 2.4 mm only on its
shell-interior radial side, with the original M2.5 channel continued through
the added material.
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

import generate_eye_all_eight_flange_broad_base_review_v3 as frames  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_right_eye_outer_pair_face879_depth_extension_review_v3 as v3  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-outer-pair-radial-thickness-review-v4.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def create_radial_layer(
    name: str,
    center: Vector,
    hole_center: Vector,
    frame: dict,
    backing_sign: float,
    added_thickness: float,
    overlap: float,
    assigned: bpy.types.Material,
) -> bpy.types.Object:
    backing = frame["radial"] * backing_sign
    existing_thickness = float(frame["dimensions"][2])
    owner_face = center + backing * existing_thickness / 2.0
    start = owner_face - backing * overlap
    end = owner_face + backing * added_thickness
    layer = gate5.box(
        name,
        (start + end) / 2.0,
        (frame["tangent"], frame["inward"], backing),
        (
            float(frame["dimensions"][0]),
            float(frame["dimensions"][1]),
            added_thickness + overlap,
        ),
        assigned,
    )
    gate6.cut_axis_hole(
        layer,
        f"{name}__M2_5_CONTINUATION",
        hole_center,
        frame["radial"],
        float(frame["hole_diameter"]),
        existing_thickness + added_thickness + overlap + 6.0,
    )
    return layer


def create_plain_head_flange(
    frame: dict,
    assigned: bpy.types.Material,
) -> bpy.types.Object:
    flange = gate5.box(
        "PROPOSED__RIGHT_OUTER_HEAD__PLAIN_FLANGE_BAR_V4",
        frame["head_center"],
        (frame["tangent"], frame["inward"], frame["radial"]),
        frame["dimensions"],
        assigned,
    )
    gate6.cut_axis_hole(
        flange,
        "PROPOSED__RIGHT_OUTER_HEAD__PLAIN_FLANGE_BAR_V4__M2_5",
        frame["head_hole_center"],
        frame["radial"],
        float(frame["hole_diameter"]),
        float(frame["dimensions"][2]) + 8.0,
    )
    return flange


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled source: {source}")
    output = repo_path(config["output_dir"])
    (output / "review").mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]

    bucket = v3.import_freecad_obj(
        repo_path(config["current_right_bucket_obj"]),
        "FROZEN__RIGHT_EYE_BUCKET_V9_V4",
    )
    head_owner = bpy.data.objects["right_upper_head"]
    frame = frames.mount_frames(
        next(item for item in gate6.eye_geometry() if item["side"] == "right")
    )["outer"]

    proposed = v3.material("PROPOSED__V4_RADIAL_THICKNESS", (0.72, 0.1, 0.82, 1.0))
    frozen = v3.material("FROZEN__V4_CONTEXT", (0.32, 0.36, 0.4, 1.0))
    v3.assign(bucket, frozen)
    v3.assign(head_owner, frozen)

    plain_head = create_plain_head_flange(frame, proposed)
    eye_layer = create_radial_layer(
        "PROPOSED__RIGHT_OUTER_EYE__SHELL_INTERIOR_THICKNESS_V4",
        frame["eye_center"],
        frame["eye_hole_center"],
        frame,
        +1.0,
        float(contract["added_shell_interior_thickness_mm"]),
        float(contract["hidden_union_overlap_mm"]),
        proposed,
    )
    head_layer = create_radial_layer(
        "PROPOSED__RIGHT_OUTER_HEAD__SHELL_INTERIOR_THICKNESS_V4",
        frame["head_center"],
        frame["head_hole_center"],
        frame,
        -1.0,
        float(contract["added_shell_interior_thickness_mm"]),
        float(contract["hidden_union_overlap_mm"]),
        proposed,
    )

    eye_owner_overlap = v3.intersection_volume(eye_layer, bucket)
    head_owner_overlap = v3.intersection_volume(head_layer, head_owner)
    pair_overlap = v3.intersection_volume(eye_layer, head_layer)
    mating_gap = v3.distance(plain_head, bucket)
    if eye_owner_overlap <= 0.0 or head_owner_overlap <= 0.0:
        raise RuntimeError(
            f"radial layers miss owners: eye={eye_owner_overlap}, head={head_owner_overlap}"
        )
    if pair_overlap > 0.001:
        raise RuntimeError(f"radial layers collide: {pair_overlap} mm3")
    if abs(mating_gap - float(contract["mating_gap_mm"])) > 0.01:
        raise RuntimeError(f"mating gap changed: {mating_gap} mm")

    topology = {
        "plain_head": v3.topology(plain_head),
        "eye_layer": v3.topology(eye_layer),
        "head_layer": v3.topology(head_layer),
    }
    if any(
        record["boundary_edges"] or record["nonmanifold_edges"]
        for record in topology.values()
    ):
        raise RuntimeError("V4 proposal contains open/nonmanifold geometry")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("V4_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V4_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72

    context = {bucket, head_owner, plain_head, eye_layer, head_layer}
    renders = [
        v3.render(camera, output, "01-v4-owner-context", (155, 175, 185), (101, 85, 147), context),
        v3.render(camera, output, "02-v4-plain-pair-close", (136, 128, 170), (101, 85, 147), {bucket, plain_head, eye_layer, head_layer}),
        v3.render(camera, output, "03-v4-added-thickness-isolated", (135, 125, 165), (101, 85, 147), {eye_layer, head_layer}),
    ]

    v3.export_obj(bucket, output / "review/right_eye_bucket_v9.obj")
    v3.export_obj(head_owner, output / "review/right_upper_head_context.obj")
    v3.export_obj(plain_head, output / "review/plain_outer_head_flange_v4.obj")
    v3.export_obj(eye_layer, output / "review/eye_shell_interior_thickness_v4.obj")
    v3.export_obj(head_layer, output / "review/head_shell_interior_thickness_v4.obj")

    prior = json.loads(repo_path(config["prior_v3_validation"]).read_text(encoding="utf-8"))
    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "construction_axis": "radial shell-interior thickness; not flange-depth/inward axis",
        "broad_base_objects_created": False,
        "v2_rectangular_base_present": False,
        "v3_depth_extensions_present": False,
        "eye_layer_owner_overlap_mm3": round(eye_owner_overlap, 4),
        "head_layer_owner_overlap_mm3": round(head_owner_overlap, 4),
        "layer_pair_overlap_mm3": round(pair_overlap, 4),
        "mating_clearance_mm": round(mating_gap, 4),
        "topology": topology,
        "lower_eye_flange_fingerprint_unchanged": prior["lower_eye_flange_fingerprint_unchanged"],
        "lower_head_flange_fingerprint_unchanged": prior["lower_head_flange_fingerprint_unchanged"],
        "lower_pair_modified": False,
        "mirror_performed": False,
        "owner_boolean_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v4.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output / "CAT_HEAD_RIGHT_EYE_OUTER_PAIR_RADIAL_THICKNESS_REVIEW_V4.blend")
    )


if __name__ == "__main__":
    main()
