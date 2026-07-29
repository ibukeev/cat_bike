#!/usr/bin/env python3
"""Generate the Gate 9 V4 complementary service-seam review candidate."""

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

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_aperture_frame_and_keel_candidate_v3 as v3  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/gate9-service-seams-candidate-v4.json"
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
LOWER_PARTS = ("left_lower_face", "right_lower_face")
METAL_NAMES = (
    "backplate",
    "rail_left",
    "rail_right",
    "shoe_envelope_left",
    "shoe_envelope_right",
    "shoe_tool_envelope_left",
    "shoe_tool_envelope_right",
    "adapter_hardware_n22_n20",
    "adapter_hardware_n22_p20",
    "adapter_hardware_p22_n20",
    "adapter_hardware_p22_p20",
)


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def mesh_volume(obj: bpy.types.Object) -> float:
    mesh = obj.evaluated_get(
        bpy.context.evaluated_depsgraph_get()
    ).to_mesh()
    try:
        return abs(sum(polygon.area * polygon.center.dot(polygon.normal) for polygon in mesh.polygons) / 3.0)
    finally:
        obj.evaluated_get(
            bpy.context.evaluated_depsgraph_get()
        ).to_mesh_clear()


def union(
    owner: bpy.types.Object,
    feature: bpy.types.Object,
    operation: str,
) -> None:
    gate5.join_closed_overlapping_mesh(owner, feature)
    gate5.require_manifold(owner, operation)
    if len(gate5.components(owner)) != 1:
        raise ValueError(f"{operation}: union split {owner.name}")


def difference(
    owner: bpy.types.Object,
    cutter: bpy.types.Object,
    operation: str,
    solver: str,
) -> None:
    gate5.apply_boolean(owner, cutter, "DIFFERENCE", solver=solver)
    gate5.require_manifold(owner, operation)
    if len(gate5.components(owner)) != 1:
        raise ValueError(f"{operation}: cut split {owner.name}")


def oriented_box(
    name: str,
    center: Vector,
    axes: tuple[Vector, Vector, Vector],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    return comparison.create_oriented_box(
        name,
        center,
        tuple(axis.normalized() for axis in axes),
        dimensions,
        material,
    )


def oriented_cylinder(
    name: str,
    center: Vector,
    axis: Vector,
    diameter: float,
    length: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    return comparison.create_oriented_cylinder(
        name,
        center,
        axis.normalized(),
        diameter,
        length,
        material,
        vertices=32,
    )


def make_capsule_cutter(
    name: str,
    center: Vector,
    long_axis: Vector,
    across_axis: Vector,
    cut_axis: Vector,
    total_length: float,
    diameter: float,
    depth: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    straight = max(total_length - diameter, 0.1)
    cutter = oriented_box(
        f"{name}__center",
        center,
        (long_axis, across_axis, cut_axis),
        (straight, diameter, depth),
        material,
    )
    for label, sign in (("a", -1.0), ("b", 1.0)):
        cap = oriented_cylinder(
            f"{name}__cap_{label}",
            center + long_axis.normalized() * sign * straight / 2.0,
            cut_axis,
            diameter,
            depth,
            material,
        )
        union(cutter, cap, f"{name} capsule {label}")
    cutter.name = name
    return cutter


def make_hole_cutter(
    name: str,
    hole_type: str,
    center: Vector,
    seam_axis: Vector,
    across_axis: Vector,
    cut_axis: Vector,
    config: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    fasteners = config["fastener_system"]
    diameter = float(fasteners["keel_clearance_hole_diameter_mm"])
    depth = 9.0
    if hole_type == "round_primary_datum":
        return oriented_cylinder(
            name, center, cut_axis, diameter, depth, material
        )
    if hole_type == "longitudinal_slot":
        long_axis = seam_axis
        short_axis = across_axis
    elif hole_type == "lateral_slot_secondary_datum":
        long_axis = across_axis
        short_axis = seam_axis
    else:
        raise ValueError(f"Unknown V4 hole type: {hole_type}")
    return make_capsule_cutter(
        name,
        center,
        long_axis,
        short_axis,
        cut_axis,
        float(fasteners["slot_total_length_mm"]),
        diameter,
        depth,
        material,
    )


def add_lower_seal_and_pads(
    part: str,
    owner: bpy.types.Object,
    keel: bpy.types.Object,
    config: dict[str, Any],
    material: bpy.types.Material,
    cutter_material: bpy.types.Material,
) -> list[dict[str, Any]]:
    seam = config["seam_geometry"]["lower_seams"][part]
    start = Vector(seam["start_head_mm"])
    end = Vector(seam["end_head_mm"])
    along = (end - start).normalized()
    length = (end - start).length
    toward_owner = Vector(seam["toward_owner_head"]).normalized()
    inward = Vector(
        config["seam_geometry"]["bottom_inward_normal_head"]
    ).normalized()
    seal = config["seal_system"]
    fasteners = config["fastener_system"]
    pad = fasteners["lower_pad"]
    wall = float(config["seam_geometry"]["wall_thickness_mm"])
    gap = float(seal["seated_gap_mm"])
    lip_bottom = wall + gap
    lip_thickness = float(seal["lip_thickness_mm"])
    root_bottom = float(seal["root_bottom_inward_mm"])
    root_top = float(seal["root_top_inward_mm"])
    front_break = float(seal["lower_front_drainage_break_mm"])
    rear_break = float(seal["lower_rear_corner_break_mm"])
    rail_length = length - front_break - rear_break
    rail_mid = start + along * (front_break + rail_length / 2.0)

    root_width = float(seal["root_width_mm"])
    root = oriented_box(
        f"v4__{part}__seal_root",
        rail_mid
        + toward_owner * root_width / 2.0
        + inward * (root_bottom + root_top) / 2.0,
        (along, toward_owner, inward),
        (rail_length, root_width, root_top - root_bottom),
        material,
    )
    union(owner, root, f"{part} continuous seal root")
    lip_width = float(seal["lip_overhang_mm"])
    lip = oriented_box(
        f"v4__{part}__seal_lip",
        rail_mid
        - toward_owner * (lip_width / 2.0 - 0.5)
        + inward * (lip_bottom + lip_thickness / 2.0),
        (along, toward_owner, inward),
        (rail_length, lip_width + 1.0, lip_thickness),
        material,
    )
    union(owner, lip, f"{part} continuous hidden gasket lip")

    records = []
    pad_length = float(pad["length_mm"])
    root_owner_width = float(pad["root_width_owner_side_mm"])
    tongue_width = float(pad["tongue_width_keel_side_mm"])
    bolt_offset = float(pad["bolt_center_into_keel_mm"])
    pad_bottom = float(pad["bottom_inward_mm"])
    pad_top = float(pad["top_inward_mm"])
    pocket_depth = float(fasteners["heat_set_insert_pocket_depth_mm"])
    pocket_diameter = float(
        fasteners["heat_set_insert_pocket_diameter_mm"]
    )
    hole_types = fasteners["lower_hole_types"][part]
    for index, (fraction, hole_type) in enumerate(
        zip(pad["fractions_along_seam"], hole_types), start=1
    ):
        seam_point = start + (end - start) * float(fraction)
        root_pad = oriented_box(
            f"v4__{part}__pad_{index}__root",
            seam_point
            + toward_owner * root_owner_width / 2.0
            + inward * (root_bottom + pad_top) / 2.0,
            (along, toward_owner, inward),
            (
                pad_length,
                root_owner_width,
                pad_top - root_bottom,
            ),
            material,
        )
        union(owner, root_pad, f"{part} flange pad {index} root")
        tongue = oriented_box(
            f"v4__{part}__pad_{index}__tongue",
            seam_point
            - toward_owner * (tongue_width / 2.0 - 0.5)
            + inward * (pad_bottom + pad_top) / 2.0,
            (along, toward_owner, inward),
            (pad_length, tongue_width + 1.0, pad_top - pad_bottom),
            material,
        )
        union(owner, tongue, f"{part} flange pad {index} tongue")
        bolt_center = seam_point - toward_owner * bolt_offset
        pocket = oriented_cylinder(
            f"v4__{part}__insert_pocket_{index}",
            bolt_center
            + inward * (pad_bottom + pocket_depth / 2.0),
            inward,
            pocket_diameter,
            pocket_depth + 0.15,
            cutter_material,
        )
        difference(
            owner,
            pocket,
            f"{part} heat-set pocket {index}",
            config["frame"]["boolean_solver"],
        )
        hole = make_hole_cutter(
            f"v4__keel__{part}__hole_{index}",
            hole_type,
            bolt_center + inward * wall / 2.0,
            along,
            toward_owner,
            inward,
            config,
            cutter_material,
        )
        difference(
            keel,
            hole,
            f"keel {part} fastener hole {index}",
            config["frame"]["boolean_solver"],
        )
        records.append(
            {
                "owner": part,
                "index": index,
                "fraction_along_seam": float(fraction),
                "hole_type": hole_type,
                "bolt_center_head_mm": [
                    round(value, 4) for value in bolt_center
                ],
                "pad_length_mm": pad_length,
                "insert_pocket_diameter_mm": pocket_diameter,
                "insert_pocket_depth_mm": pocket_depth,
            }
        )
    return records


def add_rear_seal_and_pads(
    cassette: bpy.types.Object,
    keel: bpy.types.Object,
    config: dict[str, Any],
    material: bpy.types.Material,
    cutter_material: bpy.types.Material,
) -> list[dict[str, Any]]:
    seam = config["seam_geometry"]
    seal = config["seal_system"]
    fasteners = config["fastener_system"]
    pad = fasteners["rear_pad"]
    center = Vector(seam["rear_edge_center_head_mm"])
    across = Vector(seam["rear_edge_across_head"]).normalized()
    toward_keel = Vector(
        seam["rear_edge_toward_keel_head"]
    ).normalized()
    toward_cassette = -toward_keel
    inward = Vector(seam["bottom_inward_normal_head"]).normalized()
    wall = float(seam["wall_thickness_mm"])
    gap = float(seal["seated_gap_mm"])
    lip_bottom = wall + gap
    lip_thickness = float(seal["lip_thickness_mm"])
    root_bottom = float(seal["root_bottom_inward_mm"])
    root_top = float(seal["root_top_inward_mm"])
    half_span = float(seal["rear_span_half_width_mm"])
    exit_half = float(seal["rear_wire_exit_half_width_mm"])
    root_width = float(seal["root_width_mm"])
    lip_width = float(seal["lip_overhang_mm"])

    for side, low, high in (
        ("left", -half_span, -exit_half),
        ("right", exit_half, half_span),
    ):
        segment_length = high - low
        segment_center = center + across * ((low + high) / 2.0)
        root = oriented_box(
            f"v4__cassette__rear_seal_root_{side}",
            segment_center
            + toward_cassette * root_width / 2.0
            + inward * (root_bottom + root_top) / 2.0,
            (across, toward_cassette, inward),
            (
                segment_length,
                root_width,
                root_top - root_bottom,
            ),
            material,
        )
        union(cassette, root, f"cassette rear seal root {side}")
        lip = oriented_box(
            f"v4__cassette__rear_seal_lip_{side}",
            segment_center
            + toward_keel * (lip_width / 2.0 - 0.5)
            + inward * (lip_bottom + lip_thickness / 2.0),
            (across, toward_keel, inward),
            (segment_length, lip_width + 1.0, lip_thickness),
            material,
        )
        union(cassette, lip, f"cassette rear gasket lip {side}")

    pad_length = float(pad["length_across_mm"])
    root_owner_width = float(pad["root_width_cassette_side_mm"])
    tongue_width = float(pad["tongue_width_keel_side_mm"])
    bolt_offset = float(pad["bolt_center_into_keel_mm"])
    pad_bottom = float(pad["bottom_inward_mm"])
    pad_top = float(pad["top_inward_mm"])
    pocket_depth = float(fasteners["heat_set_insert_pocket_depth_mm"])
    pocket_diameter = float(
        fasteners["heat_set_insert_pocket_diameter_mm"]
    )
    records = []
    for index, (x_value, hole_type) in enumerate(
        zip(pad["x_head_mm"], fasteners["rear_hole_types"]), start=1
    ):
        seam_point = center + across * float(x_value)
        root_pad = oriented_box(
            f"v4__cassette__pad_{index}__root",
            seam_point
            + toward_cassette * root_owner_width / 2.0
            + inward * (root_bottom + pad_top) / 2.0,
            (across, toward_cassette, inward),
            (
                pad_length,
                root_owner_width,
                pad_top - root_bottom,
            ),
            material,
        )
        union(cassette, root_pad, f"cassette pad {index} root")
        tongue = oriented_box(
            f"v4__cassette__pad_{index}__tongue",
            seam_point
            + toward_keel * (tongue_width / 2.0 - 0.5)
            + inward * (pad_bottom + pad_top) / 2.0,
            (across, toward_keel, inward),
            (pad_length, tongue_width + 1.0, pad_top - pad_bottom),
            material,
        )
        union(cassette, tongue, f"cassette pad {index} tongue")
        bolt_center = seam_point + toward_keel * bolt_offset
        pocket = oriented_cylinder(
            f"v4__cassette__insert_pocket_{index}",
            bolt_center
            + inward * (pad_bottom + pocket_depth / 2.0),
            inward,
            pocket_diameter,
            pocket_depth + 0.15,
            cutter_material,
        )
        difference(
            cassette,
            pocket,
            f"cassette heat-set pocket {index}",
            config["frame"]["boolean_solver"],
        )
        hole = make_hole_cutter(
            f"v4__keel__cassette_hole_{index}",
            hole_type,
            bolt_center + inward * wall / 2.0,
            across,
            toward_keel,
            inward,
            config,
            cutter_material,
        )
        difference(
            keel,
            hole,
            f"keel cassette fastener hole {index}",
            config["frame"]["boolean_solver"],
        )
        records.append(
            {
                "owner": "rear_cassette",
                "index": index,
                "x_head_mm": float(x_value),
                "hole_type": hole_type,
                "bolt_center_head_mm": [
                    round(value, 4) for value in bolt_center
                ],
                "insert_pocket_diameter_mm": pocket_diameter,
                "insert_pocket_depth_mm": pocket_depth,
            }
        )
    return records


def add_wire_channel(
    keel: bpy.types.Object,
    config: dict[str, Any],
    material: bpy.types.Material,
) -> dict[str, Any]:
    seam = config["seam_geometry"]
    channel = config["wire_channel"]
    rear = Vector(seam["rear_edge_center_head_mm"])
    forward = Vector(seam["rear_edge_toward_keel_head"]).normalized()
    across = Vector(seam["rear_edge_across_head"]).normalized()
    inward = Vector(seam["bottom_inward_normal_head"]).normalized()
    start = float(channel["start_from_rear_edge_mm"])
    end = float(channel["end_from_rear_edge_mm"])
    length = end - start
    centerline = rear + forward * (start + length / 2.0)
    rail_width = float(channel["rail_width_mm"])
    rail_height = float(channel["rail_height_mm"])
    rail_bottom = float(channel["rail_bottom_inward_mm"])
    for index, x_value in enumerate(channel["rail_center_x_head_mm"], start=1):
        rail = oriented_box(
            f"v4__keel__wire_guard_{index}",
            centerline
            + across * float(x_value)
            + inward * (rail_bottom + rail_height / 2.0),
            (forward, across, inward),
            (length, rail_width, rail_height),
            material,
        )
        union(keel, rail, f"keel wire guard {index}")
    actual_clear = (
        abs(
            float(channel["rail_center_x_head_mm"][1])
            - float(channel["rail_center_x_head_mm"][0])
        )
        - rail_width
    )
    return {
        "start_from_rear_edge_mm": start,
        "end_from_rear_edge_mm": end,
        "actual_clear_width_mm": round(actual_clear, 3),
        "minimum_clear_width_mm": float(
            channel["minimum_clear_width_mm"]
        ),
        "rear_exit_gap_width_mm": float(
            channel["rear_exit_gap_width_mm"]
        ),
        "provisional_bundle_envelope_mm": channel[
            "provisional_bundle_envelope_mm"
        ],
    }


def cut_drains(
    keel: bpy.types.Object,
    config: dict[str, Any],
    material: bpy.types.Material,
) -> dict[str, Any]:
    drainage = config["drainage"]
    inward = Vector(
        config["seam_geometry"]["bottom_inward_normal_head"]
    ).normalized()
    before = mesh_volume(keel)
    records = []
    for index, values in enumerate(drainage["centers_head_mm"], start=1):
        center = Vector(values)
        cutter = oriented_cylinder(
            f"v4__keel__drain_{index}",
            center + inward * 1.0,
            inward,
            float(drainage["hole_diameter_mm"]),
            8.0,
            material,
        )
        difference(
            keel,
            cutter,
            f"keel drain {index}",
            config["frame"]["boolean_solver"],
        )
        records.append(
            {
                "index": index,
                "center_head_mm": values,
                "diameter_mm": float(drainage["hole_diameter_mm"]),
            }
        )
    after = mesh_volume(keel)
    return {
        "holes": records,
        "removed_volume_mm3": round(before - after, 3),
        "minimum_target_removed_volume_mm3": float(
            drainage["minimum_target_removed_volume_mm3"]
        ),
    }


def collision_matrix(
    first: bpy.types.Object,
    others: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    return {
        name: comparison.collision_record(first, other)
        for name, other in others.items()
    }


def sweep_records(
    moving: bpy.types.Object,
    direction: Vector,
    outward_offsets: list[float],
    fixed: dict[str, bpy.types.Object],
) -> list[dict[str, Any]]:
    records = []
    original = moving.location.copy()
    for offset in outward_offsets:
        moving.location = original + direction.normalized() * float(offset)
        bpy.context.view_layer.update()
        collisions = collision_matrix(moving, fixed)
        records.append(
            {
                "outward_offset_mm": float(offset),
                "collisions": collisions,
                "clear": all(
                    not value["intersects"]
                    for value in collisions.values()
                ),
            }
        )
    moving.location = original
    bpy.context.view_layer.update()
    return records


def object_stats(
    obj: bpy.types.Object, architecture_config: dict[str, Any]
) -> dict[str, Any]:
    return v3.object_stats(obj, architecture_config)


def main() -> None:
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    v3.main()
    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    v3_report_path = (
        output_dir / "gate9-aperture-frame-and-keel-candidate-v3.json"
    )
    v3_report = json.loads(v3_report_path.read_text(encoding="utf-8"))
    architecture_config = json.loads(
        (REPO_ROOT / config["source_architecture_config"]).read_text(
            encoding="utf-8"
        )
    )
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    objects = {
        part: bpy.data.objects[f"gate9_frame_candidate__{part}"]
        for part in BODY_PARTS
    }
    keel = bpy.data.objects["gate9_v3_partition_source__bottom_keel"]
    cassette = bpy.data.objects["gate9_frame_candidate__rear_cassette"]
    metal = {
        name: bpy.data.objects[f"gate9_frame_candidate__{name}"]
        for name in METAL_NAMES
    }
    material = comparison.create_material(
        "gate9_v4_service_seam", "#8E5AC8"
    )
    cutter_material = comparison.create_material(
        "gate9_v4_cutter", "#D74949", alpha=0.3
    )
    solver = config["frame"]["boolean_solver"]
    clearance = float(config["seam_geometry"]["seated_clearance_mm"])

    collision_before = {
        "keel_to_lower_shells": collision_matrix(
            keel, {part: objects[part] for part in LOWER_PARTS}
        ),
        "cassette_to_body_shells": collision_matrix(
            cassette, objects
        ),
    }
    for part in LOWER_PARTS:
        cutter = v3.expanded_cutter(
            objects[part],
            f"v4__expanded_{part}_keel_clearance",
            clearance,
        )
        difference(
            keel,
            cutter,
            f"keel clearance from {part}",
            solver,
        )
    for part in BODY_PARTS:
        cutter = v3.expanded_cutter(
            objects[part],
            f"v4__expanded_{part}_cassette_clearance",
            clearance,
        )
        difference(
            cassette,
            cutter,
            f"cassette clearance from {part}",
            solver,
        )

    fastener_records = []
    for part in LOWER_PARTS:
        fastener_records.extend(
            add_lower_seal_and_pads(
                part,
                objects[part],
                keel,
                config,
                material,
                cutter_material,
            )
        )
    fastener_records.extend(
        add_rear_seal_and_pads(
            cassette,
            keel,
            config,
            material,
            cutter_material,
        )
    )
    wire_report = add_wire_channel(keel, config, material)
    drain_report = cut_drains(keel, config, cutter_material)

    modified = {
        **objects,
        "rear_cassette": cassette,
        "bottom_keel": keel,
    }
    stats = {
        name: object_stats(obj, architecture_config)
        for name, obj in modified.items()
    }
    topology_pass = all(
        value["connected_components"] == 1
        and value["boundary_edges"] == 0
        and value["nonmanifold_edges"] == 0
        for value in stats.values()
    )
    seated = {
        "keel_to_lower_shells": collision_matrix(
            keel, {part: objects[part] for part in LOWER_PARTS}
        ),
        "keel_to_cassette": comparison.collision_record(
            keel, cassette
        ),
        "cassette_to_body_shells": collision_matrix(
            cassette, objects
        ),
    }
    seated_clear = (
        all(
            not value["intersects"]
            for value in seated["keel_to_lower_shells"].values()
        )
        and not seated["keel_to_cassette"]["intersects"]
        and all(
            not value["intersects"]
            for value in seated["cassette_to_body_shells"].values()
        )
    )
    printed_to_metal = {
        name: collision_matrix(obj, metal)
        for name, obj in (
            ("bottom_keel", keel),
            ("rear_cassette", cassette),
            *[(part, objects[part]) for part in LOWER_PARTS],
        )
    }
    metal_clear = all(
        not record["intersects"]
        for matrix in printed_to_metal.values()
        for record in matrix.values()
    )

    service = config["service_sweeps"]
    inward = Vector(
        config["seam_geometry"]["bottom_inward_normal_head"]
    ).normalized()
    keel_sweep = sweep_records(
        keel,
        -inward,
        service["keel_outward_test_offsets_mm"],
        {part: objects[part] for part in LOWER_PARTS},
    )
    rear_outward = Vector(
        interface["rear_interface_plane"]["outward_normal_head"]
    ).normalized()
    cassette_sweep = sweep_records(
        cassette,
        rear_outward,
        service["cassette_outward_test_offsets_mm"],
        {
            **objects,
            "bottom_keel": keel,
        },
    )
    sweeps_clear = all(record["clear"] for record in keel_sweep) and all(
        record["clear"] for record in cassette_sweep
    )
    drains_pass = (
        drain_report["removed_volume_mm3"]
        >= drain_report["minimum_target_removed_volume_mm3"]
    )
    wire_pass = (
        wire_report["actual_clear_width_mm"]
        >= wire_report["minimum_clear_width_mm"]
        and wire_report["rear_exit_gap_width_mm"]
        >= wire_report["provisional_bundle_envelope_mm"][0]
    )

    shells_dir = output_dir / "shells"
    for name, obj in modified.items():
        comparison.export_stl(obj, shells_dir / f"{name}.stl")
    for ear in ("left_ear", "right_ear"):
        source = (
            REPO_ROOT
            / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/variants/rear_cassette_full_scale"
            / f"{ear}.stl"
        )
        if not source.exists():
            raise FileNotFoundError(source)

    all_review_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name.startswith(
            (
                "gate9_frame_candidate__",
                "gate9_v3_partition_source__",
                "review_frame__",
                "v4__",
            )
        )
    ]
    camera = bpy.data.objects.get("Bridge_Audit_Camera")
    if camera is None:
        camera = v3.base.audit.configure_workbench_render()
    for render_name, selected_objects in (
        (
            "v4_service_seams__assembled",
            [*objects.values(), cassette, keel],
        ),
        (
            "v4_lower_seams__inside",
            [objects["left_lower_face"], objects["right_lower_face"], keel],
        ),
        ("v4_cassette_keel_seam", [cassette, keel]),
        ("v4_bottom_keel_wire_and_drains", [keel]),
    ):
        v3.base.audit.render_part(
            render_name,
            selected_objects,
            all_review_objects,
            output_dir,
            camera,
        )
    for obj in all_review_objects:
        obj.hide_render = False
        obj.hide_viewport = False

    validation = {
        "all_six_modified_printed_parts_one_closed_manifold_component": topology_pass,
        "all_preexisting_keel_and_cassette_body_collisions_removed": seated_clear,
        "all_modified_seam_parts_clear_frozen_metal_envelopes": metal_clear,
        "sampled_keel_bottom_install_and_cassette_rear_install_sweeps_clear": sweeps_clear,
        "two_forward_drains_remove_expected_opening_volume": drains_pass,
        "protected_wire_channel_and_rear_exit_meet_configured_envelope": wire_pass,
    }
    validation["digital_v4_service_seam_candidate_pass"] = all(
        validation.values()
    )
    report = {
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "source_v3_report": str(v3_report_path.relative_to(REPO_ROOT)),
        "source_v3_validation": v3_report["validation"],
        "seam_ownership": {
            "lower_side_seams": "left/right lower shells own gasket lips, broad pads, and heat-set inserts; keel owns clearance/slot holes only",
            "rear_keel_seam": "rear cassette owns split gasket lip, broad pads, and heat-set inserts; keel owns clearance/slot holes only",
            "primary_bike_mount_load_path": "unchanged metal-only V0.3 path; V4 M3 seam hardware is cosmetic shell retention",
        },
        "collision_before_v4_clearance": collision_before,
        "seated_collision_after_v4": seated,
        "printed_to_frozen_metal_collisions": printed_to_metal,
        "fastener_manifest": fastener_records,
        "fastener_count": len(fastener_records),
        "seal_system": config["seal_system"],
        "drainage": drain_report,
        "wire_channel": wire_report,
        "service_sweeps": {
            "keel_from_bottom": keel_sweep,
            "cassette_from_rear": cassette_sweep,
        },
        "parts": stats,
        "validation": validation,
        "acceptance_holds": config["acceptance_holds"],
    }
    blend_path = output_dir / "gate9-service-seams-candidate-v4.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report["generated_review_files"] = {
        "blend": str(blend_path.relative_to(REPO_ROOT)),
        "shell_stls": str(shells_dir.relative_to(REPO_ROOT)),
        "renders": str((output_dir / "renders").relative_to(REPO_ROOT)),
    }
    report_path = output_dir / "gate9-service-seams-candidate-v4.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "fastener_count": len(fastener_records),
                "drainage": drain_report,
                "wire_channel": wire_report,
                "topology": {
                    name: {
                        "components": value["connected_components"],
                        "boundary_edges": value["boundary_edges"],
                        "nonmanifold_edges": value["nonmanifold_edges"],
                    }
                    for name, value in stats.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not validation["digital_v4_service_seam_candidate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
