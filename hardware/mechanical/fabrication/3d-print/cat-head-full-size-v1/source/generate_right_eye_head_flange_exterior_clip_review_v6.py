#!/usr/bin/env python3
"""Clip both thick right-eye head flanges to the local shell exterior.

V6 preserves the approved V5 locations, mating planes, bolt axes, pair gaps,
and both eye-side flange solids.  Only material from the two head-side V5
flanges that crosses a frozen owner exterior plane is removed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_eye_all_eight_flange_broad_base_review_v3 as frames  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_right_eye_all_four_plain_flange_thickness_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-head-flange-exterior-clip-review-v6.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def owner_world_faces(owner: bpy.types.Object) -> list[dict]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = owner.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    world = evaluated.matrix_world
    vertices = [world @ vertex.co for vertex in mesh.vertices]
    records = []
    for polygon in mesh.polygons:
        indices = [
            mesh.loops[index].vertex_index for index in polygon.loop_indices
        ]
        center = sum((vertices[index] for index in indices), Vector()) / len(indices)
        normal = (world.to_3x3() @ polygon.normal).normalized()
        records.append(
            {
                "index": int(polygon.index),
                "center": center,
                "normal": normal,
                "area_mm2": float(polygon.area),
            }
        )
    evaluated.to_mesh_clear()
    return records


def exterior_plane(
    owner: bpy.types.Object,
    frame: dict,
    flange: bpy.types.Object,
) -> tuple[Vector, Vector, int, float, dict]:
    """Resolve the actual exterior owner skin, not the nearest mount facet."""
    world_vertices = [
        flange.matrix_world @ vertex.co for vertex in flange.data.vertices
    ]
    candidates = []
    for record in owner_world_faces(owner):
        point = record["center"]
        normal = record["normal"].copy()
        anchor_signed = (frame["anchor"] - point).dot(normal)
        center_signed = (frame["head_center"] - point).dot(normal)
        signed_vertices = [
            (vertex - point).dot(normal) for vertex in world_vertices
        ]
        minimum = min(signed_vertices)
        maximum = max(signed_vertices)
        if center_signed > 0.0:
            normal = -normal
            anchor_signed = -anchor_signed
            center_signed = -center_signed
            minimum, maximum = -maximum, -minimum
        if (
            record["area_mm2"] < 100.0
            or abs(anchor_signed) > 2.25
            or center_signed > -0.5
            or maximum < 0.05
            or maximum > 4.0
            or minimum > -0.5
        ):
            continue
        score = abs(anchor_signed) - min(record["area_mm2"], 2000.0) * 1e-6
        candidates.append(
            (
                score,
                point,
                normal,
                record,
                anchor_signed,
                center_signed,
                minimum,
                maximum,
            )
        )
    if not candidates:
        raise RuntimeError(f"no safe exterior owner-skin plane for {owner.name}")
    (
        _score,
        point,
        normal,
        record,
        anchor_signed,
        center_signed,
        minimum,
        maximum,
    ) = min(candidates, key=lambda item: item[0])
    diagnostics = {
        "source_face_area_mm2": round(record["area_mm2"], 4),
        "anchor_signed_distance_mm": round(anchor_signed, 6),
        "head_flange_center_signed_distance_mm": round(center_signed, 6),
        "pre_clip_signed_range_mm": [
            round(minimum, 6),
            round(maximum, 6),
        ],
        "selection_method": (
            "large exterior owner skin crossing only outward flange corner"
        ),
    }
    return (
        point,
        normal,
        int(record["index"]),
        abs(float(anchor_signed)),
        diagnostics,
    )


def create_thick_plain_flange_blank(
    name: str,
    frame: dict,
    added_thickness: float,
    assigned: bpy.types.Material,
) -> bpy.types.Object:
    """Build the head leaf without its bore so clipping precedes hole cutting."""
    original_thickness = float(frame["dimensions"][2])
    total_thickness = original_thickness + added_thickness
    backing = -frame["radial"]
    center = frame["head_center"] + backing * (added_thickness / 2.0)
    flange = gate5.box(
        name,
        center,
        (frame["tangent"], frame["inward"], frame["radial"]),
        (
            float(frame["dimensions"][0]),
            float(frame["dimensions"][1]),
            total_thickness,
        ),
        assigned,
    )
    flange["review_only"] = True
    flange["owner_kind"] = "head"
    flange["mount_role"] = frame["role"]
    flange["original_thickness_mm"] = original_thickness
    flange["added_owner_side_thickness_mm"] = added_thickness
    flange["total_thickness_mm"] = total_thickness
    return flange


def clip_to_interior_halfspace(
    flange: bpy.types.Object,
    frame: dict,
    plane_point: Vector,
    outward_normal: Vector,
    recess: float,
    clip_material: bpy.types.Material,
) -> tuple[Vector, float]:
    clip_point = plane_point - outward_normal * recess
    axis_u = frame["tangent"] - outward_normal * frame["tangent"].dot(
        outward_normal
    )
    if axis_u.length < 0.01:
        axis_u = frame["inward"] - outward_normal * frame["inward"].dot(
            outward_normal
        )
    axis_u.normalize()
    axis_v = outward_normal.cross(axis_u).normalized()
    half_depth = 120.0
    clipper = gate5.box(
        f"TOOL__{flange.name}__INTERIOR_HALFSPACE",
        clip_point - outward_normal * half_depth,
        (axis_u, axis_v, outward_normal),
        (300.0, 300.0, half_depth * 2.0),
        clip_material,
    )
    gate5.apply_boolean(flange, clipper, "INTERSECT")
    return clip_point, recess


def connected_components(obj: bpy.types.Object) -> int:
    mesh = obj.data
    adjacency = {vertex.index: set() for vertex in mesh.vertices}
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(adjacency)
    count = 0
    while unseen:
        count += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
    return count


def triangulate_for_exact_exchange(obj: bpy.types.Object) -> None:
    """Remove Boolean slivers and triangulate before OBJ-to-BRep exchange."""
    mesh = obj.data
    working = bmesh.new()
    working.from_mesh(mesh)
    bmesh.ops.remove_doubles(
        working, verts=list(working.verts), dist=1e-6
    )
    bmesh.ops.dissolve_degenerate(
        working, edges=list(working.edges), dist=1e-7
    )
    bmesh.ops.triangulate(working, faces=list(working.faces))
    working.normal_update()
    working.to_mesh(mesh)
    working.free()
    mesh.update()


def maximum_signed_distance(
    obj: bpy.types.Object,
    plane_point: Vector,
    outward_normal: Vector,
) -> float:
    return max(
        (
            (obj.matrix_world @ vertex.co) - plane_point
        ).dot(outward_normal)
        for vertex in obj.data.vertices
    )


def plane_marker(
    name: str,
    frame: dict,
    point: Vector,
    normal: Vector,
    assigned: bpy.types.Material,
) -> bpy.types.Object:
    axis_u = frame["tangent"] - normal * frame["tangent"].dot(normal)
    axis_u.normalize()
    axis_v = normal.cross(axis_u).normalized()
    marker = gate5.box(
        name,
        point - normal * 0.025,
        (axis_u, axis_v, normal),
        (16.0, 12.0, 0.05),
        assigned,
    )
    marker["review_only_anchor_plane"] = True
    return marker


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled source: {source}")
    output = repo_path(config["output_dir"])
    (output / "review").mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]

    bucket = v5.v3.import_freecad_obj(
        repo_path(config["current_right_bucket_obj"]),
        "FROZEN__RIGHT_EYE_BUCKET_V9_V6",
    )
    owners = {
        "outer_head": bpy.data.objects["right_upper_head"],
        "lower_head": bpy.data.objects["right_lower_face"],
        "outer_eye": bucket,
        "lower_eye": bucket,
    }
    geometry = next(item for item in gate6.eye_geometry() if item["side"] == "right")
    mount_frames = frames.mount_frames(geometry)

    proposed_head = v5.v3.material("PROPOSED__V6_CLIPPED_HEAD", (0.72, 0.12, 0.86, 1.0))
    proposed_eye = v5.v3.material("PROPOSED__V6_UNCHANGED_EYE", (1.0, 0.34, 0.04, 1.0))
    frozen_upper = v5.v3.material("FROZEN__V6_UPPER_HEAD", (0.42, 0.46, 0.51, 1.0))
    frozen_lower = v5.v3.material("FROZEN__V6_LOWER_FACE", (0.27, 0.42, 0.37, 1.0))
    frozen_eye = v5.v3.material("FROZEN__V6_EYE_BUCKET", (0.10, 0.46, 0.82, 1.0))
    clip_tool = v5.v3.material("TOOL__V6_INTERIOR_HALFSPACE", (0.2, 1.0, 0.2, 1.0))
    marker_material = v5.v3.material("REVIEW_ONLY__V6_CLIP_PLANES", (0.1, 1.0, 0.2, 1.0))
    v5.v3.assign(owners["outer_head"], frozen_upper)
    v5.v3.assign(owners["lower_head"], frozen_lower)
    v5.v3.assign(bucket, frozen_eye)

    added = float(contract["total_radial_thickness_mm"]) - float(
        gate6.CONFIG["head_mount"]["tab_thickness_mm"]
    )
    recess = float(contract["head_exterior_recess_mm"])
    flanges = {}
    records = {}
    anchor_records = {}
    markers = {}

    for role in ("outer", "lower"):
        frame = mount_frames[role]
        for owner_kind in ("head", "eye"):
            key = f"{role}_{owner_kind}"
            suffix = "EXTERIOR_CLIPPED" if owner_kind == "head" else "UNCHANGED"
            name = f"PROPOSED__RIGHT_{role.upper()}_{owner_kind.upper()}__PLAIN_FLANGE_4P8MM_{suffix}_V6"
            if owner_kind == "head":
                flange = create_thick_plain_flange_blank(
                    name, frame, added, proposed_head
                )
            else:
                flange = v5.create_thick_plain_flange(
                    name, frame, owner_kind, added, proposed_eye
                )
            pre_volume = v5.v3.topology(flange)["volume_mm3"]
            clip_point = None
            clip_normal = None
            clipped_blank_volume = None
            exterior_deviation = None
            edge_margin = None
            if owner_kind == "head":
                (
                    point,
                    normal,
                    polygon_index,
                    anchor_distance,
                    plane_diagnostics,
                ) = exterior_plane(owners[key], frame, flange)
                clip_point, _ = clip_to_interior_halfspace(
                    flange,
                    frame,
                    point,
                    normal,
                    recess,
                    clip_tool,
                )
                clip_normal = normal
                clipped_blank_volume = v5.v3.topology(flange)["volume_mm3"]
                total_thickness = float(contract["total_radial_thickness_mm"])
                gate6.cut_axis_hole(
                    flange,
                    f"{name}__M2_5_THROUGH",
                    frame["head_hole_center"],
                    frame["radial"],
                    float(frame["hole_diameter"]),
                    total_thickness + 8.0,
                )
                exterior_deviation = maximum_signed_distance(
                    flange, clip_point, normal
                )
                hole_center = frame["head_hole_center"]
                edge_margin = -(
                    hole_center - clip_point
                ).dot(normal) - float(frame["hole_diameter"]) / 2.0
                markers[role] = plane_marker(
                    f"REVIEW_ONLY__{role.upper()}_HEAD_EXTERIOR_CLIP_PLANE_V6",
                    frame,
                    clip_point,
                    normal,
                    marker_material,
                )
                anchor_records[key] = {
                    "owner": owners[key].name,
                    "source_polygon_index_zero_based": polygon_index,
                    "source_anchor_point_mm": [round(value, 6) for value in point],
                    "outward_normal": [round(value, 8) for value in normal],
                    "nearest_distance_from_mount_anchor_mm": round(anchor_distance, 6),
                    "clip_recess_mm": recess,
                    **plane_diagnostics,
                }
            flanges[key] = flange
            if owner_kind == "head":
                triangulate_for_exact_exchange(flange)
            topology = v5.v3.topology(flange)
            components = connected_components(flange)
            owner_overlap = v5.v3.intersection_volume(flange, owners[key])
            if topology["boundary_edges"] or topology["nonmanifold_edges"]:
                raise RuntimeError(f"{name} is open or nonmanifold: {topology}")
            if components != 1:
                raise RuntimeError(f"{name} has {components} components")
            if owner_overlap <= 0.0:
                raise RuntimeError(f"{name} misses receiving owner")
            if owner_kind == "head":
                if exterior_deviation > float(
                    contract["maximum_exterior_positive_deviation_mm"]
                ):
                    raise RuntimeError(
                        f"{name} breaches exterior by {exterior_deviation:.6f} mm"
                    )
            records[key] = {
                "object": name,
                "owner": owners[key].name,
                "owner_overlap_mm3": round(owner_overlap, 4),
                "owner_overlap_80mm3_gate": owner_overlap
                >= float(contract["minimum_direct_owner_overlap_mm3"]),
                "pre_clip_blank_volume_mm3": (
                    round(pre_volume, 4) if owner_kind == "head" else None
                ),
                "post_clip_pre_bore_volume_mm3": (
                    round(clipped_blank_volume, 4)
                    if clipped_blank_volume is not None
                    else None
                ),
                "final_post_bore_volume_mm3": round(
                    topology["volume_mm3"], 4
                ),
                "removed_exterior_volume_mm3": (
                    round(pre_volume - clipped_blank_volume, 4)
                    if clipped_blank_volume is not None
                    else 0.0
                ),
                "mating_face_shift_mm": 0.0,
                "hole_axis_shift_mm": 0.0,
                "maximum_exterior_positive_deviation_mm": (
                    round(exterior_deviation, 6)
                    if exterior_deviation is not None
                    else None
                ),
                "bore_to_clipped_edge_margin_mm": (
                    round(edge_margin, 4) if edge_margin is not None else None
                ),
                "bore_to_clipped_edge_3p5mm_gate": (
                    edge_margin
                    >= float(contract["minimum_bore_to_clipped_edge_mm"])
                    if edge_margin is not None
                    else None
                ),
                "connected_components": components,
                "topology": topology,
            }

    pair_checks = {}
    for role in ("outer", "lower"):
        head = flanges[f"{role}_head"]
        eye = flanges[f"{role}_eye"]
        interference = v5.v3.intersection_volume(head, eye)
        clearance = v5.v3.distance(head, eye)
        if interference > 0.001:
            raise RuntimeError(f"{role} pair interferes: {interference}")
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
    camera_data = bpy.data.cameras.new("V6_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V6_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72

    all_context = set(owners.values()) | set(flanges.values())
    renders = [
        v5.v3.render(camera, output, "01-v6-all-four-owner-context", (165, 150, 180), (83, 73, 135), all_context),
        v5.v3.render(camera, output, "02-v6-outer-head-exterior", (145, 45, 170), (103, 82, 147), {owners["outer_head"], bucket, flanges["outer_head"], flanges["outer_eye"]}),
        v5.v3.render(camera, output, "03-v6-lower-head-exterior", (112, 30, 100), (67, 61, 120), {owners["lower_head"], bucket, flanges["lower_head"], flanges["lower_eye"]}),
        v5.v3.render(camera, output, "04-v6-four-flanges-isolated", (145, 135, 170), (83, 73, 135), set(flanges.values())),
        v5.v3.render(camera, output, "05-v6-owner-clip-plane-anchors", (150, 115, 180), (83, 73, 135), all_context | set(markers.values())),
    ]

    v5.v3.export_obj(bucket, output / "review/right_eye_bucket_v9.obj")
    v5.v3.export_obj(owners["outer_head"], output / "review/right_upper_head_context.obj")
    v5.v3.export_obj(owners["lower_head"], output / "review/right_lower_face_context.obj")
    for key, flange in flanges.items():
        v5.v3.export_obj(flange, output / f"review/{key}_v6.obj")

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "anchors": anchor_records,
        "construction": "V5 flange locations and 4.8 mm thickness preserved; only exterior-breaching head-side corners clipped to geometrically classified large frozen-owner skin planes",
        "flanges": records,
        "pairs": pair_checks,
        "both_eye_side_v5_shapes_unchanged": True,
        "both_head_side_exterior_breaches_clipped": True,
        "structural_print_release_hold": "Any false bore-to-clipped-edge 3.5 mm gate remains an explicit hold; no hole or flange relocation was authorized.",
        "frozen_owner_geometry_modified": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v6.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    for marker in markers.values():
        marker.hide_render = True
        marker.hide_viewport = True
    bpy.ops.wm.save_as_mainfile(
        filepath=str(
            output
            / "CAT_HEAD_RIGHT_EYE_HEAD_FLANGE_EXTERIOR_CLIP_REVIEW_V6.blend"
        )
    )


if __name__ == "__main__":
    main()
