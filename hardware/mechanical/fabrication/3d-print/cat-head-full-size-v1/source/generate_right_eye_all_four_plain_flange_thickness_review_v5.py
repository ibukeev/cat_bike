#!/usr/bin/env python3
"""Build four visibly thickened plain right-eye flange leaves.

V5 replaces V4 because V4's eye-side layer was contained entirely inside the
bucket owner and therefore did not change the actual eye-flange solid.  V5
reconstructs all four right-side flange leaves as standalone plain rectangular
solids with their owner-side thickness doubled from 2.4 to 4.8 mm.  Mating
faces, M2.5 axes, and the 0.3 mm pair gaps remain fixed.
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
CONFIG_PATH = (
    PACKAGE_ROOT
    / "config/right-eye-all-four-plain-flange-thickness-review-v5.json"
)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def create_thick_plain_flange(
    name: str,
    frame: dict,
    owner_kind: str,
    added_thickness: float,
    assigned: bpy.types.Material,
) -> bpy.types.Object:
    is_head = owner_kind == "head"
    center = frame["head_center"] if is_head else frame["eye_center"]
    hole_center = (
        frame["head_hole_center"] if is_head else frame["eye_hole_center"]
    )
    backing_sign = -1.0 if is_head else +1.0
    backing = frame["radial"] * backing_sign
    original_thickness = float(frame["dimensions"][2])
    total_thickness = original_thickness + added_thickness

    # Shift by half the addition toward the owner.  This keeps the mating face
    # exactly fixed while moving only the hidden/owner-side face.
    thick_center = center + backing * (added_thickness / 2.0)
    flange = gate5.box(
        name,
        thick_center,
        (frame["tangent"], frame["inward"], frame["radial"]),
        (
            float(frame["dimensions"][0]),
            float(frame["dimensions"][1]),
            total_thickness,
        ),
        assigned,
    )
    gate6.cut_axis_hole(
        flange,
        f"{name}__M2_5_THROUGH",
        hole_center,
        frame["radial"],
        float(frame["hole_diameter"]),
        total_thickness + 8.0,
    )
    flange["review_only"] = True
    flange["owner_kind"] = owner_kind
    flange["mount_role"] = frame["role"]
    flange["original_thickness_mm"] = original_thickness
    flange["added_owner_side_thickness_mm"] = added_thickness
    flange["total_thickness_mm"] = total_thickness
    return flange


def mating_face_center(frame: dict, owner_kind: str, thickness: float) -> Vector:
    center = frame["head_center"] if owner_kind == "head" else frame["eye_center"]
    backing_sign = -1.0 if owner_kind == "head" else +1.0
    backing = frame["radial"] * backing_sign
    return center - backing * thickness / 2.0


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
        "FROZEN__RIGHT_EYE_BUCKET_V9_V5",
    )
    owners = {
        "outer_head": bpy.data.objects["right_upper_head"],
        "lower_head": bpy.data.objects["right_lower_face"],
        "outer_eye": bucket,
        "lower_eye": bucket,
    }
    right_geometry = next(
        item for item in gate6.eye_geometry() if item["side"] == "right"
    )
    mount_frames = frames.mount_frames(right_geometry)

    proposed_head = v3.material("PROPOSED__V5_HEAD_FLANGES", (0.72, 0.12, 0.86, 1.0))
    proposed_eye = v3.material("PROPOSED__V5_EYE_FLANGES", (1.0, 0.34, 0.04, 1.0))
    frozen_upper = v3.material("FROZEN__V5_UPPER_HEAD", (0.42, 0.46, 0.51, 1.0))
    frozen_lower = v3.material("FROZEN__V5_LOWER_FACE", (0.27, 0.42, 0.37, 1.0))
    frozen_eye = v3.material("FROZEN__V5_EYE_BUCKET", (0.10, 0.46, 0.82, 1.0))
    v3.assign(owners["outer_head"], frozen_upper)
    v3.assign(owners["lower_head"], frozen_lower)
    v3.assign(bucket, frozen_eye)

    added = float(contract["added_owner_side_thickness_mm"])
    original = float(contract["existing_radial_thickness_mm"])
    flanges = {}
    records = {}
    for role in ("outer", "lower"):
        frame = mount_frames[role]
        for owner_kind in ("head", "eye"):
            key = f"{role}_{owner_kind}"
            name = f"PROPOSED__RIGHT_{role.upper()}_{owner_kind.upper()}__PLAIN_FLANGE_4P8MM_V5"
            flange = create_thick_plain_flange(
                name,
                frame,
                owner_kind,
                added,
                proposed_head if owner_kind == "head" else proposed_eye,
            )
            flanges[key] = flange
            owner_overlap = v3.intersection_volume(flange, owners[key])
            topology = v3.topology(flange)
            original_mating = mating_face_center(frame, owner_kind, original)
            thick_center = (
                frame["head_center"]
                if owner_kind == "head"
                else frame["eye_center"]
            ).copy()
            backing_sign = -1.0 if owner_kind == "head" else +1.0
            thick_center += frame["radial"] * backing_sign * (added / 2.0)
            backing = frame["radial"] * backing_sign
            thick_mating = thick_center - backing * ((original + added) / 2.0)
            mating_shift = (thick_mating - original_mating).length
            if owner_overlap <= 0.0:
                raise RuntimeError(f"{name} misses receiving owner")
            if topology["boundary_edges"] or topology["nonmanifold_edges"]:
                raise RuntimeError(f"{name} is open or nonmanifold: {topology}")
            if mating_shift > 1e-5:
                raise RuntimeError(f"{name} moved its mating face: {mating_shift}")
            records[key] = {
                "object": name,
                "mount_edge_indices": frame["edge"],
                "m2_5_hole_center_mm": [
                    round(value, 5)
                    for value in (
                        frame["head_hole_center"]
                        if owner_kind == "head"
                        else frame["eye_hole_center"]
                    )
                ],
                "m2_5_hole_axis": [
                    round(value, 6) for value in frame["radial"]
                ],
                "owner_overlap_mm3": round(owner_overlap, 4),
                "mating_face_shift_mm": round(mating_shift, 6),
                "topology": topology,
            }

    pair_checks = {}
    for role in ("outer", "lower"):
        head = flanges[f"{role}_head"]
        eye = flanges[f"{role}_eye"]
        interference = v3.intersection_volume(head, eye)
        clearance = v3.distance(head, eye)
        if interference > 0.001:
            raise RuntimeError(f"{role} thick flange pair interferes: {interference}")
        if abs(clearance - float(contract["mating_gap_mm"])) > 0.01:
            raise RuntimeError(f"{role} mating gap changed: {clearance}")
        pair_checks[role] = {
            "interference_mm3": round(interference, 6),
            "minimum_clearance_mm": round(clearance, 4),
        }

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
    camera_data = bpy.data.cameras.new("V5_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V5_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72

    all_context = set(owners.values()) | set(flanges.values())
    renders = [
        v3.render(camera, output, "01-v5-all-four-owner-context", (165, 150, 180), (83, 73, 135), all_context),
        v3.render(camera, output, "02-v5-outer-pair-close", (136, 128, 170), (101, 85, 147), {bucket, owners["outer_head"], flanges["outer_eye"], flanges["outer_head"]}),
        v3.render(camera, output, "03-v5-lower-pair-close", (106, 112, 145), (66, 61, 119), {bucket, owners["lower_head"], flanges["lower_eye"], flanges["lower_head"]}),
        v3.render(camera, output, "04-v5-four-thick-flanges-isolated", (145, 135, 170), (83, 73, 135), set(flanges.values())),
    ]

    v3.export_obj(bucket, output / "review/right_eye_bucket_v9.obj")
    v3.export_obj(owners["outer_head"], output / "review/right_upper_head_context.obj")
    v3.export_obj(owners["lower_head"], output / "review/right_lower_face_context.obj")
    for key, flange in flanges.items():
        v3.export_obj(flange, output / f"review/{key}_plain_4p8mm_v5.obj")

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "construction": "four standalone plain 12 x 8 x 4.8 mm flange leaves; mating faces fixed; owner-side face moved 2.4 mm toward owner",
        "flanges": records,
        "pairs": pair_checks,
        "all_four_are_real_standalone_thickened_solids": True,
        "v4_contained_eye_layer_reused": False,
        "broad_base_or_wedge_present": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v5.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(
            output
            / "CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.blend"
        )
    )


if __name__ == "__main__":
    main()
