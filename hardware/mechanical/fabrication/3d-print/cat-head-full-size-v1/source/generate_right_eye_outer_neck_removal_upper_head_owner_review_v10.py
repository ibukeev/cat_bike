#!/usr/bin/env python3
"""Correct V9: remove the actual long lower-face neck touching the outer pair."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_eye_second_pair_neck_removal_review_v9 as v9

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-outer-neck-removal-upper-head-owner-review-v10.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def component_faces(obj: bpy.types.Object, indices: set[int]) -> list[bpy.types.MeshPolygon]:
    return [
        polygon
        for polygon in obj.data.polygons
        if all(index in indices for index in polygon.vertices)
    ]


def component_matching_bbox(
    obj: bpy.types.Object,
    vertex_count: int,
    face_count: int,
    bbox_min: list[float],
    bbox_max: list[float],
    tolerance: float,
) -> tuple[set[int], dict[str, Any]]:
    expected_low = Vector(bbox_min)
    expected_high = Vector(bbox_max)
    matches: list[tuple[set[int], dict[str, Any]]] = []
    for indices in v9.components(obj):
        faces = component_faces(obj, indices)
        low, high = v9.world_bbox(obj, indices)
        if (
            len(indices) == vertex_count
            and len(faces) == face_count
            and all(abs(low[i] - expected_low[i]) <= tolerance for i in range(3))
            and all(abs(high[i] - expected_high[i]) <= tolerance for i in range(3))
        ):
            matches.append(
                (
                    indices,
                    {
                        "vertex_count": len(indices),
                        "face_count": len(faces),
                        "bbox_min_mm": [round(value, 5) for value in low],
                        "bbox_max_mm": [round(value, 5) for value in high],
                    },
                )
            )
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one locked component; found {len(matches)}")
    return matches[0]


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_v7_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled V7 source: {source}")
    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]

    source_lower = bpy.data.objects[v9.LOWER_FACE]
    upper = bpy.data.objects[v9.UPPER_HEAD]
    bucket = bpy.data.objects[v9.EYE_BUCKET]
    source_flanges = {key: bpy.data.objects[name] for key, name in v9.FLANGE_NAMES.items()}

    revised_lower = v9.v3.duplicate(
        source_lower,
        "PROPOSED__RIGHT_LOWER_FACE__ACTUAL_OUTER_NECK_REMOVED_V10",
    )
    retained_flanges = {
        key: v9.v3.duplicate(obj, f"RETAINED__V10__{key.upper()}__UNCHANGED")
        for key, obj in source_flanges.items()
    }

    before_topology = v9.v3.topology(revised_lower)
    before_component_count = len(v9.components(revised_lower))
    target, removed_record = component_matching_bbox(
        revised_lower,
        int(contract["removed_component_vertex_count"]),
        int(contract["removed_component_face_count"]),
        contract["removed_component_bbox_min_mm"],
        contract["removed_component_bbox_max_mm"],
        float(contract["bbox_tolerance_mm"]),
    )
    target_distance = v9.minimum_vertex_distance(
        revised_lower,
        target,
        retained_flanges["outer_head"],
    )
    if target_distance > float(contract["maximum_component_distance_to_outer_head_flange_mm"]):
        raise RuntimeError(f"locked neck does not touch selected outer head flange: {target_distance}")
    removed_record["minimum_vertex_distance_to_selected_outer_head_flange_mm"] = round(
        target_distance, 6
    )
    v9.delete_vertices(revised_lower, target)

    after_topology = v9.v3.topology(revised_lower)
    after_component_count = len(v9.components(revised_lower))
    if before_topology["vertices"] - after_topology["vertices"] != int(
        contract["removed_component_vertex_count"]
    ):
        raise RuntimeError("unexpected lower-face vertex deletion count")
    if before_topology["faces"] - after_topology["faces"] != int(
        contract["removed_component_face_count"]
    ):
        raise RuntimeError("unexpected lower-face face deletion count")
    if before_component_count - after_component_count != 1:
        raise RuntimeError("lower-face component count did not decrease by exactly one")

    _, restored_record = component_matching_bbox(
        revised_lower,
        int(contract["restored_v9_wrongly_deleted_component_vertex_count"]),
        int(contract["restored_v9_wrongly_deleted_component_face_count"]),
        contract["restored_v9_wrongly_deleted_component_bbox_min_mm"],
        contract["restored_v9_wrongly_deleted_component_bbox_max_mm"],
        float(contract["bbox_tolerance_mm"]),
    )
    restored_record["status"] = "restored_from_frozen_v7_source"

    flange_records: dict[str, Any] = {}
    for key, retained_obj in retained_flanges.items():
        source_fingerprint = v9.v3.fingerprint(source_flanges[key])
        retained_fingerprint = v9.v3.fingerprint(retained_obj)
        if retained_fingerprint != source_fingerprint:
            raise RuntimeError(f"{key} flange changed")
        flange_records[key] = {
            "source_object": source_flanges[key].name,
            "review_object": retained_obj.name,
            "fingerprint": retained_fingerprint,
            "topology": v9.v3.topology(retained_obj),
        }

    pair_records: dict[str, Any] = {}
    for role in ("outer", "second"):
        head = retained_flanges[f"{role}_head"]
        eye = retained_flanges[f"{role}_eye"]
        interference = v9.v3.intersection_volume(head, eye)
        gap = v9.v3.distance(head, eye)
        if interference > 0.001:
            raise RuntimeError(f"retained {role} pair interferes: {interference}")
        if abs(gap - float(contract["mating_gap_mm"])) > float(
            contract["maximum_pair_gap_error_mm"]
        ):
            raise RuntimeError(f"retained {role} pair gap changed: {gap}")
        pair_records[role] = {
            "minimum_clearance_mm": round(gap, 4),
            "interference_mm3": round(interference, 6),
        }

    outer_head = retained_flanges["outer_head"]
    upper_overlap = v9.v3.intersection_volume(outer_head, upper)
    revised_lower_overlap = v9.v3.intersection_volume(outer_head, revised_lower)
    if upper_overlap < float(contract["minimum_outer_head_flange_upper_head_overlap_mm3"]):
        raise RuntimeError(f"outer head flange lacks direct upper-head root: {upper_overlap}")

    frozen_material = v9.v3.material("FROZEN__V10_CONTEXT", (0.36, 0.40, 0.45, 1.0))
    revised_material = v9.v3.material("PROPOSED__V10_ACTUAL_NECK_REMOVED", (0.12, 0.64, 0.32, 1.0))
    retained_material = v9.v3.material("RETAINED__V10_FLANGES", (0.95, 0.55, 0.10, 1.0))
    v9.v3.assign(source_lower, frozen_material)
    v9.v3.assign(upper, frozen_material)
    v9.v3.assign(bucket, frozen_material)
    v9.v3.assign(revised_lower, revised_material)
    for obj in retained_flanges.values():
        v9.v3.assign(obj, retained_material)

    v9.v3.export_obj(revised_lower, review / "right_lower_face_actual_outer_neck_removed_v10.obj")
    v9.v3.export_obj(upper, review / "right_upper_head_context_v10.obj")
    v9.v3.export_obj(bucket, review / "right_eye_bucket_context_v10.obj")
    for key, obj in retained_flanges.items():
        v9.v3.export_obj(obj, review / f"{key}_unchanged_v10.obj")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    camera_data = bpy.data.cameras.new("V10_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V10_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58
    outer_pair = {retained_flanges["outer_head"], retained_flanges["outer_eye"]}
    renders = [
        v9.v3.render(camera, output, "01-v10-before-actual-neck-removal", (145, 45, 170), (103, 82, 147), {source_lower, upper, *outer_pair}),
        v9.v3.render(camera, output, "02-v10-after-actual-neck-removal", (145, 45, 170), (103, 82, 147), {revised_lower, upper, *outer_pair}),
        v9.v3.render(camera, output, "03-v10-after-full-owner-context", (150, 90, 175), (96, 78, 142), {revised_lower, upper, bucket, *retained_flanges.values()}),
    ]

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "removed_actual_neck_component": removed_record,
        "restored_v9_wrongly_deleted_component": restored_record,
        "lower_face_before": {
            "topology": before_topology,
            "component_count": before_component_count,
        },
        "lower_face_after": {
            "topology": after_topology,
            "component_count": after_component_count,
        },
        "flanges": flange_records,
        "retained_pairs": pair_records,
        "outer_head_flange_owner": {
            "upper_head_overlap_mm3": round(upper_overlap, 4),
            "revised_lower_face_overlap_mm3": round(revised_lower_overlap, 4),
            "assigned_owner": "right_upper_head",
            "spatial_relocation_performed": False,
        },
        "geometry_changed": [revised_lower.name],
        "flange_geometry_changed": False,
        "flange_location_changed": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v10.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output / "CAT_HEAD_RIGHT_EYE_OUTER_NECK_REMOVAL_UPPER_HEAD_OWNER_REVIEW_V10.blend")
    )


if __name__ == "__main__":
    main()
