#!/usr/bin/env python3
"""Replace the wrong lower-face eye flange with an upper-head-owned pair.

V8 keeps the approved outer eye-mount pair and creates the second pair at the
measured inner-upper eye edge position where both the V9 eye bucket and the
right upper-head shell provide direct owner engagement. Both head-side leaves
are plain rectangles rooted directly into right_upper_head. The lower face is
frozen context only and owns no eye-mount geometry.
"""

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

import generate_eye_all_eight_flange_broad_base_review_v3 as frames
import generate_gate6_eye_modules as gate6
import generate_right_eye_all_four_plain_flange_thickness_review_v5 as v5
import generate_right_eye_all_four_flange_local_skin_clip_review_v7 as v7
import generate_right_eye_head_flange_exterior_clip_review_v6 as v6

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-upper-head-only-dual-pair-review-v8.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def inner_upper_mount_frame(
    geometry: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    settings = gate6.CONFIG["head_mount"]
    outer = geometry["outer"]
    aperture = geometry["aperture"]
    inward = geometry["inward"]
    edge = tuple(contract["replacement_inner_upper_edge_indices"])
    first, second = edge
    edge_vector = outer[second] - outer[first]
    anchor = (outer[first] + outer[second]) / 2.0
    aperture_midpoint = (aperture[first] + aperture[second]) / 2.0
    tangent = edge_vector.copy()
    tangent -= inward * tangent.dot(inward)
    if tangent.length < 0.01:
        raise RuntimeError("right inner-upper eye-mount edge has no stable tangent")
    tangent.normalize()
    anchor += tangent * edge_vector.length * float(
        contract["replacement_edge_fraction_from_midpoint"]
    )
    radial = inward.cross(tangent).normalized()
    if radial.dot(aperture_midpoint - anchor) < 0.0:
        radial = -radial
    length, depth, _total_thickness = (
        float(value) for value in contract["replacement_plain_flange_dimensions_mm"]
    )
    thickness = float(settings["tab_thickness_mm"])
    gap = float(settings["tab_face_gap_mm"])
    overlap = float(settings["shell_overlap_mm"])
    front_recess = float(settings["front_recess_mm"])
    hole_depth = float(settings["bolt_depth_from_eye_plane_mm"])
    head_center = anchor + radial * (thickness / 2.0 - overlap) + inward * (front_recess + depth / 2.0)
    eye_center = anchor + radial * (thickness - overlap + gap + thickness / 2.0) + inward * (front_recess + depth / 2.0)
    return {
        "role": "inner_upper",
        "edge": list(edge),
        "anchor": anchor,
        "tangent": tangent,
        "inward": inward,
        "radial": radial,
        "dimensions": (length, depth, thickness),
        "head_center": head_center,
        "eye_center": eye_center,
        "head_hole_center": head_center + inward * (hole_depth - depth / 2.0),
        "eye_hole_center": eye_center + inward * (hole_depth - depth / 2.0),
        "hole_diameter": float(settings["m2_5_clearance_diameter_mm"]),
        "front_recess": front_recess,
        "mating_gap": gap,
    }


def crossing_planes(owner, frame, role_flanges, contract, reference_point=None, reference_normal=None):
    if reference_point is not None and reference_normal is not None:
        return v7.local_skin_planes(
            owner, frame, role_flanges, reference_point, reference_normal, contract
        )
    records = []
    for face in v7.evaluated_world_faces(owner):
        point = face["point"]
        normal = face["normal"].copy()
        if (frame["head_center"] - point).dot(normal) > 0.0:
            normal = -normal
        anchor_distance = v7.distance_to_polygon(frame["anchor"], face["vertices"])
        ranges = [v7.signed_range(flange, point, normal) for flange in role_flanges]
        minimum = min(value[0] for value in ranges)
        maximum = max(value[1] for value in ranges)
        if (
            face["area_mm2"] < float(contract["minimum_face_area_mm2"])
            or anchor_distance > float(contract["maximum_face_distance_from_role_anchor_mm"])
            or (frame["head_center"] - point).dot(normal) > -0.25
            or maximum <= float(contract["maximum_exterior_positive_deviation_mm"])
            or minimum >= -0.05
        ):
            continue
        records.append({
            "index": face["index"],
            "point": point,
            "normal": normal,
            "area_mm2": face["area_mm2"],
            "anchor_distance_mm": anchor_distance,
        })
    records.sort(key=lambda item: (item["anchor_distance_mm"], -item["area_mm2"]))
    if not records:
        raise RuntimeError("no upper-head exterior skin facet crosses upper pair")
    return records


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_v7_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled V7 source: {source}")
    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]

    upper_head = bpy.data.objects["right_upper_head"]
    lower_face = bpy.data.objects["right_lower_face"]
    bucket = bpy.data.objects["FROZEN__RIGHT_EYE_BUCKET_V9_V6"]
    geometry_record = next(item for item in gate6.eye_geometry() if item["side"] == "right")
    outer_frame = frames.mount_frames(geometry_record)["outer"]
    inner_frame = inner_upper_mount_frame(geometry_record, contract)
    mount_frames = {"outer": outer_frame, "inner_upper": inner_frame}
    if outer_frame["edge"] != contract["retained_outer_edge_indices"]:
        raise RuntimeError(f"outer edge changed: {outer_frame['edge']}")
    if inner_frame["edge"] != contract["replacement_inner_upper_edge_indices"]:
        raise RuntimeError(f"inner-upper edge changed: {inner_frame['edge']}")

    head_material = v5.v3.material("PROPOSED__V8_UPPER_HEAD_OWNED", (0.72, 0.12, 0.86, 1.0))
    eye_material = v5.v3.material("PROPOSED__V8_V9_EYE_OWNED", (1.0, 0.34, 0.04, 1.0))
    clip_material = v5.v3.material("TOOL__V8_LOCAL_INTERIOR_HALFSPACE", (0.2, 1.0, 0.2, 1.0))
    v5.v3.assign(upper_head, v5.v3.material("FROZEN__V8_UPPER_HEAD", (0.42, 0.46, 0.51, 1.0)))
    v5.v3.assign(lower_face, v5.v3.material("FROZEN__V8_LOWER_FACE_CONTEXT_ONLY", (0.27, 0.42, 0.37, 1.0)))
    v5.v3.assign(bucket, v5.v3.material("FROZEN__V8_V9_EYE_BUCKET", (0.10, 0.46, 0.82, 1.0)))

    original_thickness = float(inner_frame["dimensions"][2])
    added = (
        float(contract["replacement_plain_flange_dimensions_mm"][2])
        - original_thickness
    )
    flanges = {}
    for owner_kind in ("head", "eye"):
        key = f"outer_{owner_kind}"
        source_name = (
            f"PROPOSED__RIGHT_OUTER_{owner_kind.upper()}__"
            "PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7"
        )
        flanges[key] = v7.duplicate_mesh(
            bpy.data.objects[source_name],
            f"PROPOSED__RIGHT_OUTER_{owner_kind.upper()}__UPPER_HEAD_ONLY_V8",
            head_material if owner_kind == "head" else eye_material,
        )
    retained = set(flanges.values())
    for obj in list(bpy.data.objects):
        if (
            obj.type == "MESH"
            and obj.name.startswith("PROPOSED__RIGHT_")
            and "FLANGE" in obj.name
            and obj not in retained
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    flanges["inner_upper_head"] = v6.create_thick_plain_flange_blank(
        "PROPOSED__RIGHT_INNER_UPPER_HEAD__UPPER_HEAD_ONLY_V8",
        inner_frame,
        added,
        head_material,
    )
    flanges["inner_upper_eye"] = v5.create_thick_plain_flange(
        "PROPOSED__RIGHT_INNER_UPPER_EYE__UPPER_HEAD_ONLY_V8",
        inner_frame,
        "eye",
        added,
        eye_material,
    )

    clipping_records = {
        "outer": [{"source": "validated V7 local-skin-clipped outer pair reused unchanged"}]
    }
    recess = float(contract["exterior_recess_mm"])
    head_blank = flanges["inner_upper_head"]
    pre_clip_volume = v5.v3.topology(head_blank)["volume_mm3"]
    point, normal, face_index, anchor_distance, diagnostics = v6.exterior_plane(
        upper_head, inner_frame, head_blank
    )
    clip_point, _ = v6.clip_to_interior_halfspace(
        head_blank, inner_frame, point, normal, recess, clip_material
    )
    post_clip_volume = v5.v3.topology(head_blank)["volume_mm3"]
    total_thickness = float(contract["replacement_plain_flange_dimensions_mm"][2])
    gate6.cut_axis_hole(
        head_blank,
        f"{head_blank.name}__M2_5_THROUGH",
        inner_frame["head_hole_center"],
        inner_frame["radial"],
        float(inner_frame["hole_diameter"]),
        total_thickness + 8.0,
    )
    exterior_deviation = v6.maximum_signed_distance(head_blank, clip_point, normal)
    if exterior_deviation > float(contract["maximum_exterior_positive_deviation_mm"]):
        raise RuntimeError(
            f"inner-upper head leaf breaches exterior by {exterior_deviation:.6f} mm"
        )
    clipping_records["inner_upper"] = [{
        "owner_face_zero_based": face_index,
        "point_mm": [round(value, 6) for value in point],
        "outward_normal": [round(value, 8) for value in normal],
        "anchor_distance_mm": round(anchor_distance, 6),
        "removed_mm3": round(pre_clip_volume - post_clip_volume, 6),
        "post_clip_exterior_deviation_mm": round(exterior_deviation, 6),
        **diagnostics,
    }]

    print("V8_CLIPPING_RECORDS=" + json.dumps(clipping_records, default=str))

    records = {}
    for key, flange in flanges.items():
        v6.triangulate_for_exact_exchange(flange)
        topology = v5.v3.topology(flange)
        components = v6.connected_components(flange)
        role, owner_kind = key.rsplit("_", 1)
        owner = upper_head if owner_kind == "head" else bucket
        overlap = v5.v3.intersection_volume(flange, owner)
        if topology["boundary_edges"] or topology["nonmanifold_edges"] or components != 1:
            raise RuntimeError(f"{key} is not one closed manifold component: {topology}")
        if overlap < float(contract["minimum_direct_owner_overlap_mm3"]):
            raise RuntimeError(f"{key} owner overlap {overlap:.4f} is below contract")
        records[key] = {
            "object": flange.name,
            "owner": owner.name,
            "owner_overlap_mm3": round(overlap, 4),
            "topology": topology,
            "connected_components": components,
            "mount_edge_indices": mount_frames[role]["edge"],
            "hole_center_mm": [
                round(value, 5)
                for value in (
                    mount_frames[role]["head_hole_center"]
                    if owner_kind == "head"
                    else mount_frames[role]["eye_hole_center"]
                )
            ],
            "hole_axis": [round(value, 7) for value in mount_frames[role]["radial"]],
        }

    pair_records = {}
    for role in ("outer", "inner_upper"):
        head = flanges[f"{role}_head"]
        eye = flanges[f"{role}_eye"]
        interference = v5.v3.intersection_volume(head, eye)
        clearance = v5.v3.distance(head, eye)
        if interference > 0.001:
            raise RuntimeError(f"{role} pair interferes: {interference}")
        if abs(clearance - float(contract["mating_gap_mm"])) > 0.01:
            raise RuntimeError(f"{role} pair gap changed: {clearance}")
        pair_records[role] = {
            "interference_mm3": round(interference, 6),
            "minimum_clearance_mm": round(clearance, 4),
        }
    separation = (outer_frame["anchor"] - inner_frame["anchor"]).length
    if separation < float(contract["minimum_pair_center_separation_mm"]):
        raise RuntimeError(f"pair separation {separation:.4f} is below contract")

    v5.v3.export_obj(bucket, review / "right_eye_bucket_v9.obj")
    v5.v3.export_obj(upper_head, review / "right_upper_head_context.obj")
    v5.v3.export_obj(lower_face, review / "right_lower_face_context_only.obj")
    for key, flange in flanges.items():
        v5.v3.export_obj(flange, review / f"{key}_v8.obj")

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
    camera_data = bpy.data.cameras.new("V8_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V8_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72
    contexts = {upper_head, lower_face, bucket, *flanges.values()}
    renders = [
        v5.v3.render(camera, output, "01-v8-upper-head-only-owner-context", (165, 150, 190), (82, 77, 147), contexts),
        v5.v3.render(camera, output, "02-v8-two-head-leaves-with-upper-head", (145, 130, 180), (76, 73, 153), {upper_head, flanges["outer_head"], flanges["inner_upper_head"]}),
        v5.v3.render(camera, output, "03-v8-two-pairs-with-v9-eye", (137, 126, 180), (86, 81, 155), {upper_head, bucket, *flanges.values()}),
        v5.v3.render(camera, output, "04-v8-lower-face-zero-flanges", (125, 110, 135), (70, 65, 120), {lower_face, upper_head, bucket, *flanges.values()}),
        v5.v3.render(camera, output, "05-v8-four-leaves-isolated", (145, 135, 180), (86, 81, 155), set(flanges.values())),
    ]

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "construction": "retained outer pair plus measured inner-upper plain rectangular pair; both head leaves owned only by right_upper_head",
        "flanges": records,
        "pairs": pair_records,
        "pair_anchor_separation_mm": round(separation, 4),
        "clipping": clipping_records,
        "head_owner_set": sorted({record["owner"] for key, record in records.items() if key.endswith("_head")}),
        "lower_face_flange_count": 0,
        "pole_neck_bridge_count": 0,
        "legacy_lower_pair_present": False,
        "frozen_owner_geometry_modified": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v8.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output / "CAT_HEAD_RIGHT_EYE_UPPER_HEAD_ONLY_DUAL_PAIR_REVIEW_V8.blend")
    )


if __name__ == "__main__":
    main()
