#!/usr/bin/env python3
"""Generate Gate 9 V11 under-ear inserts and separated anti-flap ties."""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate9_body_seam_clearance_candidate_v8 as v8  # noqa: E402
import generate_gate9_ear_primary_interface_candidate_v10 as v10  # noqa: E402
import generate_gate9_m2_rear_interface_candidate_v7 as v7  # noqa: E402
import generate_gate9_rear_architecture_comparison as review  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "config/gate9-under-ear-insert-antiflap-candidate-v11.json"
)
SIDES = ("left", "right")


def stage(message: str, started_at: float) -> None:
    print(
        f"[gate9-v11-under-ear +{time.monotonic() - started_at:7.2f}s] "
        f"{message}",
        flush=True,
    )


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def selected_edge_record(
    boundary: list[dict[str, Any]],
    edge: list[int],
    fraction: float,
    transformed: list[Vector],
) -> dict[str, Any]:
    record = next(
        (
            candidate
            for candidate in boundary
            if set(candidate["edge"]) == set(int(value) for value in edge)
        ),
        None,
    )
    if record is None:
        raise ValueError(f"Missing configured insert boundary edge {edge}")
    output = dict(record)
    first = transformed[record["edge"][0]]
    second = transformed[record["edge"][1]]
    output["midpoint"] = first.lerp(second, float(fraction))
    output["station_fraction"] = float(fraction)
    return output


def require_single_manifold(obj: bpy.types.Object, label: str) -> None:
    gate5.require_manifold(obj, label)
    components = len(gate5.components(obj))
    if components != 1:
        raise ValueError(f"{label}: {obj.name} has {components} components")


def repair_single_boolean_seam(obj: bpy.types.Object) -> None:
    """Weld a sub-micron duplicate seam left by Blender exact Boolean."""
    boundary, nonmanifold = gate5.topology_counts(obj)
    if boundary != 0 or nonmanifold != 1:
        return
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.0e-5)
    bmesh.ops.dissolve_degenerate(
        bm,
        edges=list(bm.edges),
        dist=1.0e-7,
    )
    tiny_faces = [face for face in bm.faces if face.calc_area() < 1.0e-6]
    if tiny_faces:
        tiny_vertices = list({vertex for face in tiny_faces for vertex in face.verts})
        bmesh.ops.remove_doubles(bm, verts=tiny_vertices, dist=0.02)
        bmesh.ops.dissolve_degenerate(
            bm,
            edges=list(bm.edges),
            dist=1.0e-7,
        )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)
    boundary, nonmanifold = gate5.topology_counts(obj)
    if boundary or nonmanifold:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for edge in bm.edges:
            if edge.is_manifold:
                continue
            print(
                "[gate9-v11-nonmanifold-edge]",
                obj.name,
                [tuple(round(value, 9) for value in vertex.co) for vertex in edge.verts],
                "faces",
                len(edge.link_faces),
                "areas",
                [round(face.calc_area(), 12) for face in edge.link_faces],
                flush=True,
            )
        bm.free()


def replace_geometry_with_x_mirror(
    target: bpy.types.Object,
    source: bpy.types.Object,
) -> None:
    """Replace target mesh with an exact, outward-normal X mirror of source."""
    mirrored = source.data.copy()
    for vertex in mirrored.vertices:
        vertex.co.x *= -1.0
    target.data = mirrored
    bm = bmesh.new()
    bm.from_mesh(target.data)
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(target.data)
    bm.free()
    target.data.update(calc_edges=True)
    require_single_manifold(target, f"{target.name} mirrored finished geometry")


def mirrored_duplicate(
    source: bpy.types.Object,
    name: str,
) -> bpy.types.Object:
    duplicate = v10.duplicate_object(source, name)
    replace_geometry_with_x_mirror(duplicate, source)
    duplicate.location.x = -source.location.x
    return duplicate


def mirrored_interface_record(
    source: dict[str, Any],
    source_edge: list[int],
) -> dict[str, Any]:
    output = copy.deepcopy(source)
    output["source_edge"] = list(source_edge)
    output["center_head_mm"][0] *= -1.0
    output["axis_head"][0] *= -1.0
    return output


def cut_opening(
    obj: bpy.types.Object,
    name: str,
    center: Vector,
    axis: Vector,
    tangent: Vector,
    station: str,
    round_diameter: float,
    slot_width: float,
    slot_length: float,
) -> None:
    centers = [center]
    diameter = round_diameter
    if station == "slot":
        diameter = slot_width
        half_extension = (slot_length - slot_width) / 2.0
        centers = [
            center - tangent * half_extension,
            center + tangent * half_extension,
        ]
    for index, opening_center in enumerate(centers):
        cutter = gate5.cylinder(
            f"{name}__opening_{index}",
            opening_center - axis * 12.0,
            opening_center + axis * 12.0,
            diameter,
            vertices=32,
        )
        gate5.apply_boolean(obj, cutter, "DIFFERENCE", solver="MANIFOLD")
    require_single_manifold(obj, f"{name} {station} opening")


def cut_captive_nyloc_pocket(
    obj: bpy.types.Object,
    name: str,
    axis_first_to_second: Vector,
    first_center: Vector,
    tab_thickness: float,
    washer_thickness: float,
    nut_across_flats: float,
    nut_height: float,
    clearance: float,
) -> None:
    axis = axis_first_to_second.normalized()
    first_outer_face = first_center - axis * (tab_thickness / 2.0)
    depth = washer_thickness + nut_height + 0.3
    cutter = gate5.cylinder(
        f"{name}__captive_nyloc_pocket",
        first_outer_face - axis * 0.3,
        first_outer_face + axis * depth,
        (nut_across_flats + clearance) / 0.8660254038,
        vertices=6,
    )
    gate5.apply_boolean(obj, cutter, "DIFFERENCE", solver="MANIFOLD")
    require_single_manifold(obj, f"{name} captive nyloc pocket")


def add_insert_root_pad(
    insert: bpy.types.Object,
    name: str,
    record: dict[str, Any],
    values: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[Vector, float]:
    pad_length = float(values["insert_root_pad_length_mm"])
    if "_body_slot__" in name:
        pad_length += float(values["slot_root_pad_extra_length_mm"])
    pad_center = (
        record["midpoint"]
        - record["radial"]
        * float(values["insert_root_pad_outward_radial_center_mm"])
        + record["inward"]
        * float(values["insert_root_pad_inward_center_mm"])
    )
    pad = gate5.box(
        name,
        pad_center,
        (record["tangent"], record["inward"], record["radial"]),
        (
            pad_length,
            float(values["insert_root_pad_inward_depth_mm"]),
            float(values["insert_root_pad_radial_width_mm"]),
        ),
        material,
    )
    root = v10.intersection_volume(
        insert,
        pad,
        f"{name}__root_intersection",
    )
    print(f"[gate9-v11-root] {name}: {root:.6f} mm3", flush=True)
    if root < float(values["minimum_insert_root_intersection_mm3"]):
        pad_center = sum(
            (pad.matrix_world @ Vector(corner) for corner in pad.bound_box),
            Vector(),
        ) / 8.0
        nearest = BVHTree.FromObject(
            insert,
            bpy.context.evaluated_depsgraph_get(),
        ).find_nearest(pad_center)
        if nearest is not None:
            delta = nearest[0] - pad_center
            print(
                "[gate9-v11-root-nearest]",
                name,
                "distance",
                round(float(nearest[3]), 6),
                "axis projections",
                [
                    round(delta.dot(axis.normalized()), 6)
                    for axis in (
                        record["tangent"],
                        record["inward"],
                        record["radial"],
                    )
                ],
                flush=True,
            )
    gate5.apply_boolean(insert, pad, "UNION", solver="EXACT")
    repair_single_boolean_seam(insert)
    require_single_manifold(insert, f"{name} insert root-pad union")
    return pad_center, root


def add_hardware_stack(
    name: str,
    first_name: str,
    second_name: str,
    center: Vector,
    axis_first_to_second: Vector,
    first_center: Vector,
    second_center: Vector,
    tab_thickness: float,
    screw_length: float,
    washer_diameter: float,
    washer_thickness: float,
    nut_diameter: float,
    nut_height: float,
    tools_config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    hardware: dict[str, bpy.types.Object],
    hardware_owners: dict[str, set[str]],
    tools: dict[str, bpy.types.Object],
    tool_owners: dict[str, set[str]],
) -> None:
    """Model a shell-side screw into a captive insert-side nyloc pocket."""
    axis = axis_first_to_second.normalized()
    first_outer_face = first_center - axis * (tab_thickness / 2.0)
    second_outer_face = second_center + axis * (tab_thickness / 2.0)
    screw = gate5.cylinder(
        f"{name}__screw",
        second_outer_face - axis * screw_length,
        second_outer_face,
        2.5,
        materials["hardware"],
        vertices=24,
    )
    head_start = second_outer_face + axis * washer_thickness
    head = gate5.cylinder(
        f"{name}__socket_cap_head",
        head_start,
        head_start + axis * float(tools_config["socket_cap_head_height_mm"]),
        float(tools_config["socket_cap_head_diameter_mm"]),
        materials["hardware"],
        vertices=24,
    )
    captive_washer = gate5.cylinder(
        f"{name}__captive_washer",
        first_outer_face,
        first_outer_face + axis * washer_thickness,
        washer_diameter,
        materials["hardware"],
        vertices=24,
    )
    head_washer = gate5.cylinder(
        f"{name}__head_washer",
        second_outer_face,
        head_start,
        washer_diameter,
        materials["hardware"],
        vertices=24,
    )
    nut = gate5.cylinder(
        f"{name}__captive_nyloc_envelope",
        first_outer_face + axis * washer_thickness,
        first_outer_face + axis * (washer_thickness + nut_height),
        nut_diameter / 0.8660254038,
        materials["hardware"],
        vertices=6,
    )
    for item in (screw, head, captive_washer, head_washer, nut):
        hardware[item.name] = item
        hardware_owners[item.name] = {first_name, second_name}
    driver_start = (
        head_start
        + axis
        * (
            float(tools_config["socket_cap_head_height_mm"])
            + float(tools_config["tool_start_clearance_mm"])
        )
    )
    driver = gate5.cylinder(
        f"{name}__driver_tool",
        driver_start,
        driver_start + axis * float(tools_config["tool_envelope_length_mm"]),
        float(tools_config["driver_envelope_diameter_mm"]),
        materials["driver"],
        vertices=32,
    )
    tools[driver.name] = driver
    tool_owners[driver.name] = {first_name, second_name}


def add_body_retainer(
    side: str,
    station: str,
    record: dict[str, Any],
    insert: bpy.types.Object,
    upper: bpy.types.Object,
    values: dict[str, Any],
    tools_config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    hardware: dict[str, bpy.types.Object],
    hardware_owners: dict[str, set[str]],
    tools: dict[str, bpy.types.Object],
    tool_owners: dict[str, set[str]],
) -> dict[str, Any]:
    prefix = f"gate9_v11__{side}_body_{station}"
    root_center, pad_root = add_insert_root_pad(
        insert,
        f"{prefix}__insert_root_pad",
        record,
        values,
        materials["insert_structure"],
    )
    upper_bvh = BVHTree.FromObject(
        upper,
        bpy.context.evaluated_depsgraph_get(),
    )
    nearest = upper_bvh.find_nearest(root_center)
    if nearest is None:
        raise ValueError(f"{side} {station} retainer has no upper landing")
    print(
        f"[gate9-v11-body-span] {side} {station}: "
        f"{float(nearest[3]):.6f} mm",
        flush=True,
    )
    upper_point = nearest[0]
    bolt_axis = (upper_point - root_center).normalized()
    tangent = record["tangent"] - bolt_axis * record["tangent"].dot(
        bolt_axis
    )
    if tangent.length < 0.01:
        raise ValueError(f"{side} {station} retainer tangent is degenerate")
    tangent.normalize()
    depth_axis = bolt_axis.cross(tangent).normalized()
    if depth_axis.dot(record["inward"]) < 0.0:
        depth_axis.negate()
    thickness = float(values["tab_thickness_mm"])
    gap = float(values["tab_face_clearance_mm"])
    depth = float(values["tab_depth_mm"])
    pair_center = (root_center + upper_point) / 2.0
    insert_center = pair_center - bolt_axis * (thickness / 2.0 + gap / 2.0)
    upper_center = pair_center + bolt_axis * (thickness / 2.0 + gap / 2.0)
    axes = (tangent, depth_axis, bolt_axis)
    dimensions = (
        float(values["tab_length_mm"]),
        depth,
        thickness,
    )
    insert_tab = gate5.box(
        f"{prefix}__insert_tab",
        insert_center,
        axes,
        dimensions,
        materials["insert_structure"],
    )
    upper_tab = gate5.box(
        f"{prefix}__upper_tab",
        upper_center,
        axes,
        dimensions,
        materials["shell_structure"],
    )
    insert_root = v10.intersection_volume(
        insert,
        insert_tab,
        f"{prefix}__insert_tab_root",
    )
    upper_root = v10.intersection_volume(
        upper,
        upper_tab,
        f"{prefix}__upper_tab_root",
    )
    print(
        f"[gate9-v11-tab-roots] {side} {station}: "
        f"insert={insert_root:.6f} upper={upper_root:.6f}",
        flush=True,
    )
    gate5.apply_boolean(insert, insert_tab, "UNION", solver="EXACT")
    repair_single_boolean_seam(insert)
    gate5.apply_boolean(upper, upper_tab, "UNION", solver="EXACT")
    repair_single_boolean_seam(upper)
    require_single_manifold(insert, f"{prefix} insert-tab union")
    require_single_manifold(upper, f"{prefix} upper-tab union")
    center = pair_center
    cut_opening(
        insert,
        f"{prefix}__insert",
        center,
        bolt_axis,
        tangent,
        "round",
        float(values["round_clearance_diameter_mm"]),
        float(values["slot_width_mm"]),
        float(values["slot_overall_length_mm"]),
    )
    cut_opening(
        upper,
        f"{prefix}__upper",
        center,
        bolt_axis,
        tangent,
        station,
        float(values["round_clearance_diameter_mm"]),
        float(values["slot_width_mm"]),
        float(values["slot_overall_length_mm"]),
    )
    cut_captive_nyloc_pocket(
        insert,
        f"{prefix}__insert",
        bolt_axis,
        insert_center,
        thickness,
        float(values["washer_thickness_mm"]),
        float(values["m2_5_nyloc_across_flats_mm"]),
        float(values["m2_5_nyloc_height_mm"]),
        float(tools_config["captive_nut_pocket_clearance_mm"]),
    )
    insert_name = f"{side}_under_ear_insert"
    upper_name = f"{side}_upper_head"
    add_hardware_stack(
        prefix,
        insert_name,
        upper_name,
        center,
        bolt_axis,
        insert_center,
        upper_center,
        thickness,
        float(values["m2_5_socket_cap_screw_length_mm"]),
        float(values["washer_outer_diameter_mm"]),
        float(values["washer_thickness_mm"]),
        float(values["m2_5_nyloc_across_flats_mm"]),
        float(values["m2_5_nyloc_height_mm"]),
        tools_config,
        materials,
        hardware,
        hardware_owners,
        tools,
        tool_owners,
    )
    tool_owners[f"{prefix}__driver_tool"].add(f"{side}_ear")
    return {
        "station": station,
        "source_edge": list(record["edge"]),
        "station_fraction": record["station_fraction"],
        "center_head_mm": [round(value, 4) for value in center],
        "axis_head": [round(value, 6) for value in bolt_axis],
        "nominal_opening_mm": (
            [float(values["round_clearance_diameter_mm"])]
            if station == "round"
            else [
                float(values["slot_width_mm"]),
                float(values["slot_overall_length_mm"]),
            ]
        ),
        "insert_root_pad_intersection_mm3": round(pad_root, 3),
        "insert_tab_root_intersection_mm3": round(insert_root, 3),
        "upper_tab_root_intersection_mm3": round(upper_root, 3),
        "initial_insert_pad_to_upper_distance_mm": round(
            float(nearest[3]),
            3,
        ),
    }


def add_anti_flap_tie(
    side: str,
    record: dict[str, Any],
    insert: bpy.types.Object,
    ear: bpy.types.Object,
    primary_centers: list[Vector],
    values: dict[str, Any],
    tools_config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    hardware: dict[str, bpy.types.Object],
    hardware_owners: dict[str, set[str]],
    tools: dict[str, bpy.types.Object],
    tool_owners: dict[str, set[str]],
    ear_geometry_prebuilt: bool = False,
) -> dict[str, Any]:
    prefix = f"gate9_v11__{side}_outer_antiflap"
    root_center, pad_root = add_insert_root_pad(
        insert,
        f"{prefix}__insert_root_pad",
        record,
        values,
        materials["insert_structure"],
    )
    ear_bvh = BVHTree.FromObject(
        ear,
        bpy.context.evaluated_depsgraph_get(),
    )
    nearest = ear_bvh.find_nearest(root_center)
    if nearest is None:
        raise ValueError(f"{side} anti-flap pad has no ear landing")
    ear_point = nearest[0]
    bolt_axis = (ear_point - root_center).normalized()
    tangent = record["tangent"] - bolt_axis * record["tangent"].dot(
        bolt_axis
    )
    if tangent.length < 0.01:
        raise ValueError(f"{side} anti-flap tangent is degenerate")
    tangent.normalize()
    depth_axis = bolt_axis.cross(tangent).normalized()
    if depth_axis.dot(record["inward"]) < 0.0:
        depth_axis.negate()
    thickness = float(values["lug_thickness_mm"])
    gap = float(values["lug_face_clearance_mm"])
    pair_center = (root_center + ear_point) / 2.0
    insert_center = pair_center - bolt_axis * (thickness / 2.0 + gap / 2.0)
    ear_center = pair_center + bolt_axis * (thickness / 2.0 + gap / 2.0)
    dimensions = (
        float(values["lug_length_mm"]),
        float(values["lug_depth_mm"]),
        thickness,
    )
    axes = (tangent, depth_axis, bolt_axis)
    insert_lug = gate5.box(
        f"{prefix}__insert_lug",
        insert_center,
        axes,
        dimensions,
        materials["insert_structure"],
    )
    ear_tab = gate5.box(
        f"{prefix}__ear_tab",
        ear_center,
        axes,
        dimensions,
        materials["shell_structure"],
    )
    insert_root = v10.intersection_volume(
        insert,
        insert_lug,
        f"{prefix}__insert_lug_root",
    )
    ear_root = v10.intersection_volume(
        ear,
        ear_tab,
        f"{prefix}__ear_tab_root",
    )
    print(
        f"[gate9-v11-antiflap-roots] {side}: "
        f"insert={insert_root:.6f} ear={ear_root:.6f}",
        flush=True,
    )
    gate5.apply_boolean(insert, insert_lug, "UNION", solver="EXACT")
    repair_single_boolean_seam(insert)
    if ear_geometry_prebuilt:
        bpy.data.objects.remove(ear_tab, do_unlink=True)
    else:
        gate5.apply_boolean(ear, ear_tab, "UNION", solver="MANIFOLD")
    require_single_manifold(insert, f"{prefix} insert-lug union")
    require_single_manifold(ear, f"{prefix} ear-tab union")
    cut_opening(
        insert,
        f"{prefix}__insert",
        pair_center,
        bolt_axis,
        tangent,
        "round",
        float(values["clearance_diameter_mm"]),
        float(values["clearance_diameter_mm"]),
        float(values["clearance_diameter_mm"]),
    )
    if not ear_geometry_prebuilt:
        cut_opening(
            ear,
            f"{prefix}__ear",
            pair_center,
            bolt_axis,
            tangent,
            "round",
            float(values["clearance_diameter_mm"]),
            float(values["clearance_diameter_mm"]),
            float(values["clearance_diameter_mm"]),
        )
    cut_captive_nyloc_pocket(
        insert,
        f"{prefix}__insert",
        bolt_axis,
        insert_center,
        thickness,
        float(values["washer_thickness_mm"]),
        float(values["m2_5_nyloc_across_flats_mm"]),
        float(values["m2_5_nyloc_height_mm"]),
        float(tools_config["captive_nut_pocket_clearance_mm"]),
    )
    add_hardware_stack(
        prefix,
        f"{side}_under_ear_insert",
        f"{side}_ear",
        pair_center,
        bolt_axis,
        insert_center,
        ear_center,
        thickness,
        float(values["m2_5_socket_cap_screw_length_mm"]),
        float(values["washer_outer_diameter_mm"]),
        float(values["washer_thickness_mm"]),
        float(values["m2_5_nyloc_across_flats_mm"]),
        float(values["m2_5_nyloc_height_mm"]),
        tools_config,
        materials,
        hardware,
        hardware_owners,
        tools,
        tool_owners,
    )
    primary_distance = min(
        (pair_center - center).length for center in primary_centers
    )
    return {
        "source_edge": list(record["edge"]),
        "station_fraction": record["station_fraction"],
        "center_head_mm": [round(value, 4) for value in pair_center],
        "axis_head": [round(value, 6) for value in bolt_axis],
        "nearest_primary_m3_center_distance_mm": round(
            primary_distance,
            3,
        ),
        "initial_insert_pad_to_ear_distance_mm": round(
            float(nearest[3]),
            3,
        ),
        "insert_root_pad_intersection_mm3": round(pad_root, 3),
        "insert_lug_root_intersection_mm3": round(insert_root, 3),
        "ear_tab_root_intersection_mm3": round(ear_root, 3),
        "primary_load_path": False,
    }


def relief_against_owner(
    owner: bpy.types.Object,
    insert: bpy.types.Object,
    label: str,
    values: dict[str, Any],
    clearance_direction: Vector,
) -> dict[str, Any]:
    overlap_before = v10.intersection_volume(
        owner,
        insert,
        f"gate9_v11__overlap_before__{label}",
    )
    cutter = v10.duplicate_object(
        owner,
        f"gate9_v11__shifted_owner_cutter__{label}",
    )
    cutter.location += clearance_direction.normalized() * float(
        values["final_shell_local_relief_clearance_mm"]
    )
    before_volume = gate5.mesh_volume(insert)
    gate5.apply_boolean(insert, cutter, "DIFFERENCE", solver="MANIFOLD")
    cleanup = gate5.keep_largest_component(insert)
    require_single_manifold(insert, f"{label} shifted-owner relief")
    residual_records = []
    for pass_index in range(1, 3):
        record = v8.apply_local_relief(
            owner,
            insert,
            f"{label}_residual_{pass_index}",
            0.10,
            float(values["zero_volume_tolerance_mm3"]),
            float(values["maximum_detached_cleanup_mm3"]),
            {},
        )
        residual_records.append(record)
        if float(record["overlap_after_mm3"]) <= float(
            values["zero_volume_tolerance_mm3"]
        ):
            break
    return {
        "clearance_mm": float(
            values["final_shell_local_relief_clearance_mm"]
        ),
        "clearance_direction_head": [
            round(value, 6) for value in clearance_direction.normalized()
        ],
        "overlap_before_mm3": round(overlap_before, 6),
        "removed_insert_volume_mm3": round(
            before_volume - gate5.mesh_volume(insert),
            3,
        ),
        "detached_component_cleanup": cleanup,
        "residual_cleanup": residual_records,
        "topology_after": v10.topology_record(insert),
    }

def all_collision_records_clear(records: dict[str, Any]) -> bool:
    return all(
        collision["clear"]
        for record in records.values()
        for collision in record.values()
    )


def main() -> None:
    started_at = time.monotonic()
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    v10_summary = json.loads(
        (REPO_ROOT / config["source_v10_validation"]).read_text(
            encoding="utf-8"
        )
    )
    if not all(v10_summary["digital_validation"].values()):
        raise ValueError("V11 source V10 validation is not fully passing")
    source_blend = (REPO_ROOT / config["source_v10_blend"]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    stage("accepted V10 primary ear source loaded", started_at)

    parts = {
        f"{side}_upper_head": v10.duplicate_object(
            bpy.data.objects[f"gate9_v10__{side}_upper_head"],
            f"gate9_v11__{side}_upper_head",
        )
        for side in SIDES
    }
    parts.update(
        {
            f"{side}_ear": v10.duplicate_object(
                bpy.data.objects[f"gate9_v10__{side}_ear"],
                f"gate9_v11__{side}_ear",
            )
            for side in SIDES
        }
    )
    parts["rear_bezel"] = v10.duplicate_object(
        bpy.data.objects["gate9_v9__rear_bezel"],
        "gate9_v11__rear_bezel",
    )
    source_bounds = {name: v10.bounds(obj) for name, obj in parts.items()}
    source_volumes = {
        name: gate5.mesh_volume(obj) for name, obj in parts.items()
    }
    materials = {
        "insert": review.create_material(
            "gate9_v11_frosted_insert",
            "#B762D4",
            alpha=0.68,
        ),
        "insert_structure": review.create_material(
            "gate9_v11_insert_hidden_structure",
            "#8D45AC",
            alpha=0.82,
        ),
        "shell_structure": review.create_material(
            "gate9_v11_shell_hidden_structure",
            "#E6A438",
        ),
        "driver": review.create_material(
            "gate9_v11_driver_envelope",
            "#D34C47",
            alpha=0.25,
        ),
        "nut_tool": review.create_material(
            "gate9_v11_nut_tool_envelope",
            "#AE4CCC",
            alpha=0.25,
        ),
        "hardware": review.create_material(
            "gate9_v11_m2_5_hardware",
            "#C6CCD4",
        ),
    }

    gate7_config = copy.deepcopy(
        json.loads(
            (REPO_ROOT / config["source_gate7_config"]).read_text(
                encoding="utf-8"
            )
        )
    )
    insert_values = config["insert"]
    gate7_config["insert"].update(
        {
            "visible_thickness_mm": float(
                insert_values["visible_thickness_mm"]
            ),
            "surface_setback_mm": float(
                insert_values["deep_body_surface_setback_mm"]
            ),
            "perimeter_clearance_mm": float(
                insert_values["deep_body_perimeter_clearance_mm"]
            ),
        }
    )
    gate7_config["visible_seam_cap"].update(
        {
            "perimeter_clearance_mm": float(
                insert_values["visible_cap_perimeter_clearance_mm"]
            ),
            "surface_setback_mm": float(
                insert_values["visible_cap_surface_setback_mm"]
            ),
            "thickness_mm": float(
                insert_values["visible_cap_thickness_mm"]
            ),
        }
    )
    gate7.CONFIG = gate7_config
    context = gate7.source_context()
    groups = {
        group["name"]: group
        for group in gate7.connected_panel_groups(context)
    }
    transformed = context["transformed"]
    inserts: dict[str, bpy.types.Object] = {}
    boundaries: dict[str, list[dict[str, Any]]] = {}
    visible_cap_records = {}
    baseline_topology = {}
    relief_records = {}
    for side in SIDES:
        group = groups[f"{side}_ear_root_cluster"]
        boundary = gate7.group_boundary(group, context)
        boundaries[side] = boundary
        insert = gate7.create_insert(
            group,
            boundary,
            [],
            context,
            materials["insert"],
        )
        insert.name = f"gate9_v11__{side}_under_ear_insert"
        visible_cap_records[side] = gate7.add_visual_seam_cap(
            group,
            insert,
            boundary,
            context,
            materials["insert"],
        )
        baseline_topology[side] = v10.topology_record(insert)
        average_inward = sum(
            (record["inward"] for record in boundary),
            Vector(),
        ).normalized()
        relief_records[side] = {
            "upper_head": relief_against_owner(
                parts[f"{side}_upper_head"],
                insert,
                f"{side}_insert_to_upper",
                insert_values,
                average_inward,
            ),
            "ear": relief_against_owner(
                parts[f"{side}_ear"],
                insert,
                f"{side}_insert_to_ear",
                insert_values,
                (
                    v8.object_center(insert)
                    - v8.object_center(parts[f"{side}_ear"])
                ).normalized(),
            ),
        }
        require_single_manifold(insert, f"{side} relieved under-ear insert")
        inserts[f"{side}_under_ear_insert"] = insert
    stage("two final-shell-relieved three-plane inserts generated", started_at)

    hardware: dict[str, bpy.types.Object] = {}
    hardware_owners: dict[str, set[str]] = {}
    tools: dict[str, bpy.types.Object] = {}
    tool_owners: dict[str, set[str]] = {}
    side_records = {}
    body_values = config["body_retention"]
    anti_values = config["anti_flap"]
    for side in SIDES:
        if side == "right":
            replace_geometry_with_x_mirror(
                parts["right_upper_head"],
                parts["left_upper_head"],
            )
            replace_geometry_with_x_mirror(
                parts["right_ear"],
                parts["left_ear"],
            )
            replace_geometry_with_x_mirror(
                inserts["right_under_ear_insert"],
                inserts["left_under_ear_insert"],
            )
            right_body_records = [
                mirrored_interface_record(record, edge)
                for record, edge in zip(
                    side_records["left"]["body_retainers"],
                    body_values["station_edges"]["right"],
                    strict=True,
                )
            ]
            right_antiflap = mirrored_interface_record(
                side_records["left"]["outer_anti_flap"],
                anti_values["station_edge"]["right"],
            )
            for registry, owners in (
                (hardware, hardware_owners),
                (tools, tool_owners),
            ):
                for left_name, left_object in list(registry.items()):
                    if "__left_" not in left_name:
                        continue
                    right_name = left_name.replace("__left_", "__right_", 1)
                    registry[right_name] = mirrored_duplicate(
                        left_object,
                        right_name,
                    )
                    owners[right_name] = {
                        owner.replace("left_", "right_", 1)
                        for owner in owners[left_name]
                    }
            side_records["right"] = {
                "body_retainers": right_body_records,
                "outer_anti_flap": right_antiflap,
            }
            continue
        body_records = []
        for index, (edge, fraction) in enumerate(
            zip(
                body_values["station_edges"][side],
                body_values["station_fractions"],
                strict=True,
            )
        ):
            station = "round" if index == 0 else "slot"
            station_fraction = float(fraction)
            record = selected_edge_record(
                boundaries[side],
                edge,
                station_fraction,
                transformed,
            )
            body_records.append(
                add_body_retainer(
                    side,
                    station,
                    record,
                    inserts[f"{side}_under_ear_insert"],
                    parts[f"{side}_upper_head"],
                    body_values,
                    config["tools"],
                    materials,
                    hardware,
                    hardware_owners,
                    tools,
                    tool_owners,
                )
            )
        anti_record = selected_edge_record(
            boundaries[side],
            anti_values["station_edge"][side],
            float(anti_values["station_fraction"]),
            transformed,
        )
        primary_centers = [
            Vector(record["center_head_mm"])
            for record in v10_summary["side_interfaces"][side]["screws"]
        ]
        ear_geometry_prebuilt = side == "right"
        if ear_geometry_prebuilt:
            replace_geometry_with_x_mirror(
                parts["right_ear"],
                parts["left_ear"],
            )
        anti_record_output = add_anti_flap_tie(
            side,
            anti_record,
            inserts[f"{side}_under_ear_insert"],
            parts[f"{side}_ear"],
            primary_centers,
            anti_values,
            config["tools"],
            materials,
            hardware,
            hardware_owners,
            tools,
            tool_owners,
            ear_geometry_prebuilt,
        )
        side_records[side] = {
            "body_retainers": body_records,
            "outer_anti_flap": anti_record_output,
        }
    stage("discrete body retainers and outer anti-flap ties added", started_at)

    clearance_values = config["final_clearance"]
    final_part_clearance = {}
    for side in SIDES:
        insert = inserts[f"{side}_under_ear_insert"]
        upper = parts[f"{side}_upper_head"]
        ear = parts[f"{side}_ear"]
        for label, owner, relieved in (
            (f"{side}_upper_to_insert", upper, insert),
            (f"{side}_ear_to_insert", ear, insert),
            (f"{side}_ear_to_upper", ear, upper),
            (f"{side}_insert_to_rear", insert, parts["rear_bezel"]),
            (f"{side}_ear_to_rear", ear, parts["rear_bezel"]),
        ):
            final_part_clearance[label] = v8.apply_local_relief(
                owner,
                relieved,
                f"gate9_v11__{label}",
                float(clearance_values["constructed_part_clearance_mm"]),
                float(clearance_values["zero_volume_tolerance_mm3"]),
                float(clearance_values["maximum_detached_cleanup_mm3"]),
                {},
            )
    hardware_pocket_clearance = {}
    for name, item in list(hardware.items()):
        side = "left" if "__left_" in name else "right"
        targets = []
        if "_body_" in name:
            targets.append((f"{side}_ear", parts[f"{side}_ear"]))
            if "_body_round__" in name:
                targets.append(("rear_bezel", parts["rear_bezel"]))
        elif "_outer_antiflap__" in name:
            targets.append((f"{side}_upper_head", parts[f"{side}_upper_head"]))
        for target_name, target in targets:
            label = f"{name}__to__{target_name}"
            hardware_pocket_clearance[label] = v8.apply_local_relief(
                item,
                target,
                f"gate9_v11__hardware_pocket__{label}",
                float(clearance_values["hardware_pocket_clearance_mm"]),
                float(clearance_values["zero_volume_tolerance_mm3"]),
                float(clearance_values["maximum_detached_cleanup_mm3"]),
                {},
            )
    insert_service_sweep_clearance = {}
    left_service_direction = Vector(
        config["assembly_paths"]["insert_outward_removal_direction_left_head"]
    ).normalized()
    for side in SIDES:
        direction = left_service_direction.copy()
        if side == "right":
            direction.x *= -1.0
        for offset in config["assembly_paths"]["insert_lead_in_sweep_offsets_mm"]:
            moved = v10.duplicate_object(
                inserts[f"{side}_under_ear_insert"],
                f"gate9_v11__{side}_insert_sweep_{float(offset):g}",
            )
            moved.location += direction * float(offset)
            label = f"{side}_insert_sweep_{float(offset):g}_to_upper"
            insert_service_sweep_clearance[label] = v8.apply_local_relief(
                moved,
                parts[f"{side}_upper_head"],
                f"gate9_v11__{label}",
                float(
                    config["assembly_paths"]["insert_lead_in_sweep_clearance_mm"]
                ),
                float(clearance_values["zero_volume_tolerance_mm3"]),
                float(clearance_values["maximum_detached_cleanup_mm3"]),
                {},
            )
            bpy.data.objects.remove(moved, do_unlink=True)
    stage("final seated, hardware-pocket, and service-sweep clearances applied", started_at)

    fixed_parts = {
        **parts,
        **inserts,
        "left_lower_face": bpy.data.objects["gate9_v9__left_lower_face"],
        "right_lower_face": bpy.data.objects["gate9_v9__right_lower_face"],
        "rear_bezel": parts["rear_bezel"],
        "bottom_keel": bpy.data.objects["gate9_v9__bottom_keel"],
        "left_socket_cap": bpy.data.objects["gate9_v9__left_socket_cap"],
        "right_socket_cap": bpy.data.objects["gate9_v9__right_socket_cap"],
    }
    for obj in bpy.data.objects:
        if obj.name.startswith("body_seam_bridge__"):
            fixed_parts[obj.name] = obj

    seated_pairs = {}
    for side in SIDES:
        insert = inserts[f"{side}_under_ear_insert"]
        for owner_name in (f"{side}_upper_head", f"{side}_ear"):
            seated_pairs[f"{side}_under_ear_insert__{owner_name}"] = round(
                v10.intersection_volume(
                    insert,
                    parts[owner_name],
                    f"gate9_v11__seated__{side}__{owner_name}",
                ),
                6,
            )
        seated_pairs[f"{side}_ear__{side}_upper_head"] = round(
            v10.intersection_volume(
                parts[f"{side}_ear"],
                parts[f"{side}_upper_head"],
                f"gate9_v11__seated__{side}_ear_upper",
            ),
            6,
        )

    assembly_paths = {}
    for side in SIDES:
        body_records = side_records[side]["body_retainers"]
        average_inward = sum(
            (
                selected_edge_record(
                    boundaries[side],
                    record["source_edge"],
                    record["station_fraction"],
                    transformed,
                )["inward"]
                for record in body_records
            ),
            Vector(),
        ).normalized()
        insert_name = f"{side}_under_ear_insert"
        insert_fixed = {
            name: obj
            for name, obj in fixed_parts.items()
            if name not in {insert_name, f"{side}_ear"}
        }
        insert_removal_direction = left_service_direction.copy()
        if side == "right":
            insert_removal_direction.x *= -1.0
        assembly_paths[f"{insert_name}_before_ear"] = v10.assembly_path(
            inserts[insert_name],
            insert_fixed,
            insert_removal_direction,
            [
                float(value)
                for value in config["assembly_paths"][
                    "insert_inward_removal_offsets_mm"
                ]
            ],
            f"gate9_v11__{side}_insert_path",
        )
        ear_name = f"{side}_ear"
        ear_fixed = {
            name: obj for name, obj in fixed_parts.items() if name != ear_name
        }
        outward = Vector(
            v10_summary["side_interfaces"][side][
                "outward_removal_direction_head"
            ]
        )
        assembly_paths[f"{ear_name}_after_insert"] = v10.assembly_path(
            parts[ear_name],
            ear_fixed,
            outward,
            [
                float(value)
                for value in config["assembly_paths"][
                    "ear_outward_removal_offsets_mm"
                ]
            ],
            f"gate9_v11__{side}_ear_path",
        )

    tool_collisions = {}
    for name, tool in tools.items():
        targets = {
            part_name: obj
            for part_name, obj in fixed_parts.items()
            if part_name not in tool_owners[name]
        }
        tool_collisions[name] = v10.collision_group(
            tool,
            targets,
            "gate9_v11__tool_collision",
        )
    hardware_collisions = {}
    for name, item in hardware.items():
        targets = {
            part_name: obj
            for part_name, obj in fixed_parts.items()
            if part_name not in hardware_owners[name]
        }
        hardware_collisions[name] = v10.collision_group(
            item,
            targets,
            "gate9_v11__hardware_collision",
        )
    metal_objects = {
        obj.name: obj
        for obj in bpy.data.objects
        if obj.name.startswith("metal_v05__")
    }
    updated_part_metal_collisions = {
        name: v7.collision_summary(obj, metal_objects)
        for name, obj in {**parts, **inserts}.items()
    }
    tool_metal_collisions = {
        name: v7.collision_summary(obj, metal_objects)
        for name, obj in tools.items()
    }
    stage("service, hardware, and complete-metal collisions evaluated", started_at)

    topology = {
        name: v10.topology_record(obj)
        for name, obj in {**parts, **inserts}.items()
    }
    exterior_preservation = {}
    for name, obj in parts.items():
        reference_bounds = source_bounds[name]
        if name.startswith("right_"):
            left_name = name.replace("right_", "left_", 1)
            left_bounds = source_bounds[left_name]
            reference_bounds = (
                [-left_bounds[1][0], left_bounds[0][1], left_bounds[0][2]],
                [-left_bounds[0][0], left_bounds[1][1], left_bounds[1][2]],
            )
        candidate_bounds = v10.bounds(obj)
        tolerance = 0.01
        inside_symmetric_source = all(
            candidate_bounds[0][axis] >= reference_bounds[0][axis] - tolerance
            and candidate_bounds[1][axis] <= reference_bounds[1][axis] + tolerance
            for axis in range(3)
        )
        hidden_ear_root_extension = max(
            0.0,
            reference_bounds[0][2] - candidate_bounds[0][2],
        )
        external_skin_safe = inside_symmetric_source
        if name.endswith("_ear"):
            external_skin_safe = (
                candidate_bounds[0][0] >= reference_bounds[0][0] - tolerance
                and candidate_bounds[1][0] <= reference_bounds[1][0] + tolerance
                and candidate_bounds[0][1] >= reference_bounds[0][1] - tolerance
                and candidate_bounds[1][1] <= reference_bounds[1][1] + tolerance
                and candidate_bounds[1][2] <= reference_bounds[1][2] + tolerance
                and hidden_ear_root_extension
                <= float(
                    config["validation"]["maximum_hidden_ear_root_extension_mm"]
                )
            )
        exterior_preservation[name] = {
            "bounds_inside_original_side_v10_source_extents": v10.bounds_inside(
                obj,
                source_bounds[name],
            ),
            "bounds_inside_symmetric_v10_source_extents": inside_symmetric_source,
            "external_skin_bounds_safe": external_skin_safe,
            "hidden_ear_root_extension_mm": round(hidden_ear_root_extension, 4),
            "symmetric_reference_bounds_mm": reference_bounds,
            "candidate_v11_bounds_mm": candidate_bounds,
            "source_v10_volume_mm3": round(source_volumes[name], 3),
            "candidate_v11_volume_mm3": round(gate5.mesh_volume(obj), 3),
        }
    mirror_errors = []
    for category in ("body_retainers",):
        for left, right in zip(
            side_records["left"][category],
            side_records["right"][category],
            strict=True,
        ):
            lp = left["center_head_mm"]
            rp = right["center_head_mm"]
            mirror_errors.append(
                max(
                    abs(lp[0] + rp[0]),
                    abs(lp[1] - rp[1]),
                    abs(lp[2] - rp[2]),
                )
            )
    lp = side_records["left"]["outer_anti_flap"]["center_head_mm"]
    rp = side_records["right"]["outer_anti_flap"]["center_head_mm"]
    mirror_errors.append(
        max(abs(lp[0] + rp[0]), abs(lp[1] - rp[1]), abs(lp[2] - rp[2]))
    )
    maximum_mirror_error = max(mirror_errors)
    zero_tolerance = float(insert_values["zero_volume_tolerance_mm3"])
    validation = {
        "both_inserts_use_three_original_visible_planes": all(
            baseline_topology[side]["components"] == 1 for side in SIDES
        ),
        "deep_body_and_visible_cap_clearances_are_separated": (
            float(insert_values["deep_body_perimeter_clearance_mm"])
            > float(insert_values["visible_cap_perimeter_clearance_mm"])
        ),
        "both_inserts_have_two_short_round_slot_body_retainers": all(
            [record["station"] for record in side_records[side]["body_retainers"]]
            == ["round", "slot"]
            for side in SIDES
        ),
        "all_body_retainer_roots_exceed_minimum": all(
            record["insert_root_pad_intersection_mm3"]
            >= float(body_values["minimum_insert_root_intersection_mm3"])
            and record["insert_tab_root_intersection_mm3"]
            >= float(body_values["minimum_insert_root_intersection_mm3"])
            and record["upper_tab_root_intersection_mm3"]
            >= float(body_values["minimum_shell_root_intersection_mm3"])
            for side in SIDES
            for record in side_records[side]["body_retainers"]
        ),
        "anti_flap_is_spatially_separated_and_non_primary": all(
            side_records[side]["outer_anti_flap"][
                "nearest_primary_m3_center_distance_mm"
            ]
            >= float(anti_values["minimum_center_distance_from_primary_m3_mm"])
            and not side_records[side]["outer_anti_flap"]["primary_load_path"]
            for side in SIDES
        ),
        "all_anti_flap_roots_exceed_minimum": all(
            side_records[side]["outer_anti_flap"][
                "insert_root_pad_intersection_mm3"
            ]
            >= float(anti_values["minimum_insert_root_intersection_mm3"])
            and side_records[side]["outer_anti_flap"][
                "insert_lug_root_intersection_mm3"
            ]
            >= float(anti_values["minimum_insert_root_intersection_mm3"])
            and side_records[side]["outer_anti_flap"][
                "ear_tab_root_intersection_mm3"
            ]
            >= float(anti_values["minimum_ear_root_intersection_mm3"])
            for side in SIDES
        ),
        "all_seven_updated_parts_are_single_closed_manifolds": all(
            record["components"] == 1
            and record["boundary_edges"] == 0
            and record["nonmanifold_edges"] == 0
            for record in topology.values()
        ),
        "all_seated_insert_ear_head_pairs_have_zero_positive_overlap": all(
            volume <= zero_tolerance for volume in seated_pairs.values()
        ),
        "insert_then_ear_service_paths_are_clear": all(
            record["all_samples_clear"] for record in assembly_paths.values()
        ),
        "all_m2_5_tools_clear_non_owned_printed_parts": (
            all_collision_records_clear(tool_collisions)
        ),
        "all_m2_5_hardware_clears_non_owned_printed_parts": (
            all_collision_records_clear(hardware_collisions)
        ),
        "updated_parts_and_tools_clear_complete_m2_metal": (
            all(
                record["clear"]
                for record in updated_part_metal_collisions.values()
            )
            and all(record["clear"] for record in tool_metal_collisions.values())
        ),
        "external_skin_bounds_are_preserved_and_ear_root_growth_is_hidden": all(
            record["external_skin_bounds_safe"]
            for record in exterior_preservation.values()
        ),
        "left_and_right_v11_fastener_centers_are_mirrored": (
            maximum_mirror_error
            <= float(
                config["validation"][
                    "maximum_mirror_fastener_center_error_mm"
                ]
            )
        ),
    }
    validation["digital_v11_under_ear_antiflap_geometry_candidate_pass"] = all(
        validation.values()
    )
    failures = [name for name, passed in validation.items() if not passed]
    if failures:
        print(f"V11 validation failures: {failures}", flush=True)

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for name, obj in {**parts, **inserts}.items():
        # Export through a temporary root-scene object so inherited hidden
        # collections and view-layer state cannot silently produce an empty
        # selected-object STL.
        export_obj = obj.copy()
        export_obj.parent = None
        export_obj.matrix_world = obj.matrix_world.copy()
        export_obj.name = f"gate9_v11__export__{name}"
        bpy.context.scene.collection.objects.link(export_obj)
        export_obj.hide_viewport = False
        export_obj.hide_render = False
        export_obj.hide_set(False)
        bpy.context.view_layer.update()
        if not export_obj.visible_get():
            raise ValueError(f"temporary STL export object is hidden: {name}")
        v10.export_stl(export_obj, parts_dir / f"{name}.stl")
        bpy.data.objects.remove(export_obj, do_unlink=True)
        exported_stl = parts_dir / f"{name}.stl"
        if exported_stl.stat().st_size <= 84:
            raise ValueError(f"empty STL export for {name}: {exported_stl}")
    output_blend = output_dir / "gate9-under-ear-insert-antiflap-v11.blend"
    for obj in {**parts, **inserts, **hardware, **tools}.values():
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))

    summary = {
        "gate": "Gate 9 V11 under-ear inserts and separated anti-flap ties",
        "status": config["status"],
        "interface_revision": v10_summary["interface_revision"],
        "metal_handoff_revision": v10_summary["metal_handoff_revision"],
        "source_v10_blend": config["source_v10_blend"],
        "output_blend": str(output_blend.relative_to(REPO_ROOT)),
        "architecture": {
            "insert": (
                "original three-plane illuminated surface with a shallow visual "
                "cap, enlarged deep-body tolerance, quantified final-shell "
                "relief, and no continuous perimeter connector"
            ),
            "body_retention": body_values["architecture"],
            "anti_flap": anti_values["architecture"],
            "service_order": (
                "seat and retain the under-ear insert before installing the ear; "
                "install the primary M3 ear pair next; install the separate outer "
                "M2.5 anti-flap locator last; remove in reverse order"
            ),
        },
        "insert_dimensions": {
            key: insert_values[key]
            for key in (
                "material",
                "visible_thickness_mm",
                "deep_body_perimeter_clearance_mm",
                "deep_body_surface_setback_mm",
                "visible_cap_perimeter_clearance_mm",
                "visible_cap_surface_setback_mm",
                "visible_cap_thickness_mm",
                "final_shell_local_relief_clearance_mm",
            )
        },
        "body_retention_hardware": {
            key: body_values[key]
            for key in (
                "fastener_nominal",
                "fastener_count_per_insert",
                "round_clearance_diameter_mm",
                "slot_width_mm",
                "slot_overall_length_mm",
                "m2_5_socket_cap_screw_length_mm",
                "washer_outer_diameter_mm",
                "washer_thickness_mm",
                "m2_5_nyloc_across_flats_mm",
                "m2_5_nyloc_height_mm",
                "tab_length_mm",
                "tab_depth_mm",
                "tab_thickness_mm",
                "tab_face_clearance_mm",
            )
        },
        "anti_flap_hardware": {
            key: anti_values[key]
            for key in (
                "fastener_nominal",
                "fastener_count_per_ear",
                "clearance_diameter_mm",
                "m2_5_socket_cap_screw_length_mm",
                "washer_outer_diameter_mm",
                "washer_thickness_mm",
                "m2_5_nyloc_across_flats_mm",
                "m2_5_nyloc_height_mm",
                "lug_length_mm",
                "lug_depth_mm",
                "lug_thickness_mm",
                "lug_face_clearance_mm",
                "minimum_center_distance_from_primary_m3_mm",
                "primary_load_path",
            )
        },
        "side_interfaces": side_records,
        "visible_cap_records": visible_cap_records,
        "baseline_insert_topology": baseline_topology,
        "final_shell_local_relief": relief_records,
        "final_constructed_part_clearance": final_part_clearance,
        "captive_hardware_pocket_clearance": hardware_pocket_clearance,
        "insert_service_sweep_clearance": insert_service_sweep_clearance,
        "topology": topology,
        "seated_positive_overlap_mm3": seated_pairs,
        "service_paths": assembly_paths,
        "tool_to_non_owned_printed_part_collisions": tool_collisions,
        "hardware_to_non_owned_printed_part_collisions": hardware_collisions,
        "updated_parts_to_m2_metal_collisions": updated_part_metal_collisions,
        "tool_to_m2_metal_collisions": tool_metal_collisions,
        "exterior_preservation": exterior_preservation,
        "mirror_fastener_center_max_error_mm": round(maximum_mirror_error, 4),
        "digital_validation": validation,
        "resolved_physical_findings": [
            "F-07 under-ear upper-corner collisions",
            "F-08 under-ear lower-center collision",
            "F-09 globally too-snug under-ear fit",
            "F-10 plane mismatch and clamping-induced lateral slide",
            "F-11 long over-constraining insert connector",
            "F-13 unsupported outer ear flapping",
            "F-14 requested outer grounding point through the under-ear insert",
            "A-07 through A-11 digital geometry portions",
        ],
        "remaining_release_holds": [
            "A-07 through A-11 still require physical PETG/ASA hand-fit, flush-plane, tightening, discrete-retention, and anti-flap checks.",
            "A-12 requires a complete physical install/removal sequence with actual M2.5 and M3 hardware.",
            "Real support/brim-inclusive Prusa MK4 PETG/ASA slicing must pass for all seven updated V11 parts.",
            "The complete-head findings outside the under-ear/ear scope remain governed by the authoritative physical-fit review.",
        ],
        "acceptance_holds": config["acceptance_holds"],
    }
    review_path = (REPO_ROOT / config["review_summary_path"]).resolve()
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    stage(f"summary written to {review_path}", started_at)
    if failures:
        raise ValueError(f"V11 validation failed: {failures}")


if __name__ == "__main__":
    main()
