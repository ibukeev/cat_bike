#!/usr/bin/env python3
"""Trim all four right-eye flange leaves to the adjacent head exterior skins.

V7 starts from the preserved V6 review.  It does not move a flange, mating
face, or bore.  It intersects each leaf only with the local interior
half-spaces defined by frozen owner-skin facets adjacent to the role anchor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector, geometry


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_eye_all_eight_flange_broad_base_review_v3 as frames  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_right_eye_all_four_plain_flange_thickness_review_v5 as v5  # noqa: E402
import generate_right_eye_head_flange_exterior_clip_review_v6 as v6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-all-four-flange-local-skin-clip-review-v7.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def duplicate_mesh(source: bpy.types.Object, name: str, material: bpy.types.Material) -> bpy.types.Object:
    copied = source.copy()
    copied.data = source.data.copy()
    copied.name = name
    bpy.context.scene.collection.objects.link(copied)
    v5.v3.assign(copied, material)
    copied.hide_viewport = False
    copied.hide_render = False
    copied["review_only"] = True
    copied["source_object"] = source.name
    return copied


def evaluated_world_faces(owner: bpy.types.Object) -> list[dict]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = owner.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    world = evaluated.matrix_world
    vertices = [world @ vertex.co for vertex in mesh.vertices]
    records = []
    for polygon in mesh.polygons:
        indices = [mesh.loops[index].vertex_index for index in polygon.loop_indices]
        polygon_vertices = [vertices[index] for index in indices]
        records.append(
            {
                "index": int(polygon.index),
                "point": sum(polygon_vertices, Vector()) / len(polygon_vertices),
                "normal": (world.to_3x3() @ polygon.normal).normalized(),
                "vertices": polygon_vertices,
                "area_mm2": float(polygon.area),
            }
        )
    evaluated.to_mesh_clear()
    return records


def distance_to_polygon(point: Vector, vertices: list[Vector]) -> float:
    if len(vertices) < 3:
        return float("inf")
    closest = float("inf")
    for index in range(1, len(vertices) - 1):
        candidate = geometry.closest_point_on_tri(
            point, vertices[0], vertices[index], vertices[index + 1]
        )
        closest = min(closest, (point - candidate).length)
    return closest


def world_vertices(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def signed_range(obj: bpy.types.Object, point: Vector, normal: Vector) -> tuple[float, float]:
    values = [(vertex - point).dot(normal) for vertex in world_vertices(obj)]
    return min(values), max(values)


def local_skin_planes(
    owner: bpy.types.Object,
    frame: dict,
    role_flanges: list[bpy.types.Object],
    reference_point: Vector,
    reference_normal: Vector,
    contract: dict,
) -> list[dict]:
    records = []
    for face in evaluated_world_faces(owner):
        point = face["point"]
        normal = face["normal"].copy()
        if (frame["head_center"] - point).dot(normal) > 0.0:
            normal = -normal
        center_signed = (frame["head_center"] - point).dot(normal)
        normal_dot = normal.dot(reference_normal)
        reference_plane_offset = (point - reference_point).dot(reference_normal)
        anchor_distance = distance_to_polygon(frame["anchor"], face["vertices"])
        ranges = [signed_range(flange, point, normal) for flange in role_flanges]
        maximum = max(item[1] for item in ranges)
        minimum = min(item[0] for item in ranges)
        if (
            face["area_mm2"] < float(contract["minimum_face_area_mm2"])
            or anchor_distance > float(contract["maximum_face_distance_from_role_anchor_mm"])
            or normal_dot < float(contract["minimum_reference_normal_dot"])
            or (normal_dot > 0.95 and reference_plane_offset < -0.10)
            or center_signed > -0.25
            or maximum <= float(contract["maximum_exterior_positive_deviation_mm"])
            or minimum >= -0.05
        ):
            continue
        records.append(
            {
                "index": face["index"],
                "point": point,
                "normal": normal,
                "area_mm2": face["area_mm2"],
                "anchor_distance_mm": anchor_distance,
                "normal_dot_reference": normal_dot,
                "reference_plane_offset_mm": reference_plane_offset,
                "center_signed_mm": center_signed,
                "pre_clip_pair_signed_range_mm": [minimum, maximum],
            }
        )
    records.sort(key=lambda item: (item["anchor_distance_mm"], -item["area_mm2"]))
    if not records:
        raise RuntimeError(f"no adjacent exterior facets cross {owner.name} flange pair")
    return records


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_v6_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled V6 source: {source}")
    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]
    v6_validation = json.loads(
        repo_path(config["source_v6_validation"]).read_text(encoding="utf-8")
    )

    owners = {
        "outer": bpy.data.objects["right_upper_head"],
        "lower": bpy.data.objects["right_lower_face"],
    }
    bucket = bpy.data.objects["FROZEN__RIGHT_EYE_BUCKET_V9_V6"]
    geometry_record = next(item for item in gate6.eye_geometry() if item["side"] == "right")
    mount_frames = frames.mount_frames(geometry_record)

    proposed_head = v5.v3.material("PROPOSED__V7_LOCAL_SKIN_CLIPPED_HEAD", (0.72, 0.12, 0.86, 1.0))
    proposed_eye = v5.v3.material("PROPOSED__V7_LOCAL_SKIN_CLIPPED_EYE", (1.0, 0.34, 0.04, 1.0))
    clip_material = v5.v3.material("TOOL__V7_LOCAL_INTERIOR_HALFSPACE", (0.2, 1.0, 0.2, 1.0))
    frozen_upper = v5.v3.material("FROZEN__V7_UPPER_HEAD", (0.42, 0.46, 0.51, 1.0))
    frozen_lower = v5.v3.material("FROZEN__V7_LOWER_FACE", (0.27, 0.42, 0.37, 1.0))
    frozen_eye = v5.v3.material("FROZEN__V7_EYE_BUCKET", (0.10, 0.46, 0.82, 1.0))
    v5.v3.assign(owners["outer"], frozen_upper)
    v5.v3.assign(owners["lower"], frozen_lower)
    v5.v3.assign(bucket, frozen_eye)

    flanges = {}
    for role in ("outer", "lower"):
        for owner_kind in ("head", "eye"):
            source_name = (
                f"PROPOSED__RIGHT_{role.upper()}_{owner_kind.upper()}__"
                f"PLAIN_FLANGE_4P8MM_{'EXTERIOR_CLIPPED' if owner_kind == 'head' else 'UNCHANGED'}_V6"
            )
            name = (
                f"PROPOSED__RIGHT_{role.upper()}_{owner_kind.upper()}__"
                "PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7"
            )
            flanges[f"{role}_{owner_kind}"] = duplicate_mesh(
                bpy.data.objects[source_name],
                name,
                proposed_head if owner_kind == "head" else proposed_eye,
            )

    role_records = {}
    recess = float(contract["exterior_recess_mm"])
    for role in ("outer", "lower"):
        frame = mount_frames[role]
        role_flanges = [flanges[f"{role}_head"], flanges[f"{role}_eye"]]
        reference_normal = Vector(v6_validation["anchors"][f"{role}_head"]["outward_normal"]).normalized()
        reference_point = Vector(
            v6_validation["anchors"][f"{role}_head"]["source_anchor_point_mm"]
        )
        planes = local_skin_planes(
            owners[role], frame, role_flanges, reference_point, reference_normal, contract
        )
        applied = []
        for plane in planes:
            changed = []
            clip_point = plane["point"] - plane["normal"] * recess
            for flange in role_flanges:
                before = v5.v3.topology(flange)["volume_mm3"]
                _minimum, maximum = signed_range(flange, clip_point, plane["normal"])
                if maximum <= float(contract["maximum_exterior_positive_deviation_mm"]):
                    continue
                v6.clip_to_interior_halfspace(
                    flange,
                    frame,
                    plane["point"],
                    plane["normal"],
                    recess,
                    clip_material,
                )
                after = v5.v3.topology(flange)["volume_mm3"]
                changed.append(
                    {
                        "flange": flange.name,
                        "removed_mm3": round(before - after, 6),
                    }
                )
            if changed:
                applied.append(
                    {
                        "owner_face_zero_based": plane["index"],
                        "point_mm": [round(value, 6) for value in plane["point"]],
                        "outward_normal": [round(value, 8) for value in plane["normal"]],
                        "face_area_mm2": round(plane["area_mm2"], 4),
                        "anchor_distance_mm": round(plane["anchor_distance_mm"], 4),
                        "normal_dot_reference": round(plane["normal_dot_reference"], 6),
                        "reference_plane_offset_mm": round(plane["reference_plane_offset_mm"], 6),
                        "changed": changed,
                    }
                )
        role_records[role] = {"candidate_count": len(planes), "applied_planes": applied}

    flange_records = {}
    for key, flange in flanges.items():
        v6.triangulate_for_exact_exchange(flange)
        topology = v5.v3.topology(flange)
        components = v6.connected_components(flange)
        if topology["boundary_edges"] or topology["nonmanifold_edges"]:
            raise RuntimeError(f"{flange.name} is open or nonmanifold: {topology}")
        if components != 1:
            raise RuntimeError(f"{flange.name} has {components} components")
        role, owner_kind = key.split("_")
        receiving_owner = owners[role] if owner_kind == "head" else bucket
        overlap = v5.v3.intersection_volume(flange, receiving_owner)
        flange_records[key] = {
            "object": flange.name,
            "topology": topology,
            "connected_components": components,
            "direct_owner_overlap_mm3": round(overlap, 4),
            "direct_owner_overlap_positive": overlap >= float(contract["minimum_direct_owner_overlap_mm3"]),
        }

    pair_records = {}
    for role in ("outer", "lower"):
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

    v5.v3.export_obj(bucket, review / "right_eye_bucket_v9.obj")
    v5.v3.export_obj(owners["outer"], review / "right_upper_head_context.obj")
    v5.v3.export_obj(owners["lower"], review / "right_lower_face_context.obj")
    for key, flange in flanges.items():
        v5.v3.export_obj(flange, review / f"{key}_v7.obj")

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
    camera_data = bpy.data.cameras.new("V7_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V7_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72
    contexts = set(owners.values()) | {bucket} | set(flanges.values())
    renders = [
        v5.v3.render(camera, output, "01-v7-all-four-owner-context", (165, 150, 180), (83, 73, 135), contexts),
        v5.v3.render(camera, output, "02-v7-outer-pair-exterior", (145, 45, 170), (103, 82, 147), {owners["outer"], bucket, flanges["outer_head"], flanges["outer_eye"]}),
        v5.v3.render(camera, output, "03-v7-lower-pair-exterior", (112, 30, 100), (67, 61, 120), {owners["lower"], bucket, flanges["lower_head"], flanges["lower_eye"]}),
        v5.v3.render(camera, output, "04-v7-four-flanges-isolated", (145, 135, 170), (83, 73, 135), set(flanges.values())),
    ]

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "construction": "V6 four-leaf geometry clipped only by adjacent frozen head-skin interior half-spaces",
        "roles": role_records,
        "flanges": flange_records,
        "pairs": pair_records,
        "mating_face_shift_mm": 0.0,
        "hole_axis_shift_mm": 0.0,
        "frozen_owner_geometry_modified": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v7.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output / "CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend")
    )


if __name__ == "__main__":
    main()
