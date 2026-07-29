#!/usr/bin/env python3
"""Generate Gate 9 V6 frozen-axis socket and portal geometry."""

from __future__ import annotations

import json
import sys
from math import acos, degrees
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
INTERFACE_MODULE_DIR = REPO_ROOT / "hardware/mechanical/interfaces"
if str(INTERFACE_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(INTERFACE_MODULE_DIR))

from cat_head_interface import load_interface  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_gate9_complementary_service_parts_candidate_v5 as v5  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-socket-portals-candidate-v6.json"
)
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
MODIFIED_PARTS = (*BODY_PARTS, "rear_bezel", "bottom_keel")


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def load_repo_json(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    )


def duplicate_object(
    source: bpy.types.Object,
    name: str,
) -> bpy.types.Object:
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    duplicate.name = name
    bpy.context.collection.objects.link(duplicate)
    return duplicate


def require_single_manifold(
    obj: bpy.types.Object,
    operation: str,
) -> None:
    gate5.require_manifold(obj, operation)
    if len(gate5.components(obj)) != 1:
        raise ValueError(f"{operation}: {obj.name} is not one component")


def true_union(
    owner: bpy.types.Object,
    feature: bpy.types.Object,
    operation: str,
) -> None:
    gate5.apply_boolean(owner, feature, "UNION", solver="MANIFOLD")
    require_single_manifold(owner, operation)


def world_polygon(
    obj: bpy.types.Object,
    target: Vector,
) -> tuple[
    bpy.types.MeshPolygon,
    Vector,
    Vector,
    list[Vector],
]:
    polygon = min(
        obj.data.polygons,
        key=lambda value: (
            (obj.matrix_world @ value.center) - target
        ).length,
    )
    center = obj.matrix_world @ polygon.center
    normal = (
        obj.matrix_world.to_3x3() @ polygon.normal
    ).normalized()
    vertices = [
        obj.matrix_world @ obj.data.vertices[index].co
        for index in polygon.vertices
    ]
    return polygon, center, normal, vertices


def socket_basis(axis: Vector) -> tuple[Vector, Vector]:
    horizontal = Vector((1.0, 0.0, 0.0))
    across = (
        horizontal - axis * horizontal.dot(axis)
    ).normalized()
    outward = axis.cross(across).normalized()
    return across, outward


def triangle_overlap_count(
    first: bpy.types.Object,
    second: bpy.types.Object,
) -> int:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return len(
        BVHTree.FromObject(first, depsgraph).overlap(
            BVHTree.FromObject(second, depsgraph)
        )
    )


def feature_plane_report(
    feature: bpy.types.Object,
    center: Vector,
    outward: Vector,
) -> dict[str, Any]:
    distances = [
        (
            (feature.matrix_world @ vertex.co) - center
        ).dot(outward)
        for vertex in feature.data.vertices
    ]
    return {
        "maximum_exterior_plane_signed_distance_mm": round(
            max(distances), 4
        ),
        "minimum_exterior_recess_mm": round(-max(distances), 4),
        "outside_exterior_plane_vertex_count": sum(
            value > 1e-5 for value in distances
        ),
    }


def collision_matrix(
    moving: bpy.types.Object,
    fixed: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    return {
        name: comparison.collision_record(moving, obj)
        for name, obj in fixed.items()
    }


def all_clear(matrix: dict[str, Any]) -> bool:
    return all(not record["intersects"] for record in matrix.values())


def sweep_records(
    source: bpy.types.Object,
    direction: Vector,
    offsets: list[float],
    fixed: dict[str, bpy.types.Object],
) -> list[dict[str, Any]]:
    records = []
    for index, offset in enumerate(offsets):
        moving = duplicate_object(
            source,
            f"{source.name}__sweep_{index:02d}",
        )
        moving.location += direction.normalized() * float(offset)
        bpy.context.view_layer.update()
        collisions = collision_matrix(moving, fixed)
        records.append(
            {
                "withdrawal_offset_mm": float(offset),
                "collisions": collisions,
                "clear": all_clear(collisions),
            }
        )
        bpy.data.objects.remove(moving, do_unlink=True)
    return records


def radial_reference(
    name: str,
    center: Vector,
    axis: Vector,
    diameter: float,
    length: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    half = axis.normalized() * (length / 2.0)
    return gate5.cylinder(
        name,
        center - half,
        center + half,
        diameter,
        material,
        vertices=24,
    )


def add_portal(
    side: str,
    shell: bpy.types.Object,
    all_printed_parts: dict[str, bpy.types.Object],
    interface: dict[str, Any],
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
) -> tuple[dict[str, Any], dict[str, bpy.types.Object]]:
    portal = config["portal"]
    hardware = config["hardware_review"]
    rails = interface["rail_system"]
    socket_contract = rails["socket"]
    target = Vector(
        rails["upper_shell_search_targets_head_mm"][side]
    )
    lower = Vector(rails["lower_targets_head_mm"][side])
    axis = Vector(rails["accepted_axes_head"][side]).normalized()
    across, outward = socket_basis(axis)
    polygon, surface, surface_normal, face_vertices = world_polygon(
        shell, target
    )
    # The Boolean unions below replace the shell mesh and invalidate Blender's
    # live polygon handle. Capture the stable source index before that happens.
    source_face_index = polygon.index
    original_shell = duplicate_object(
        shell, f"gate9_v6__{side}_upper_original"
    )
    original_shell.hide_render = True
    original_shell.hide_viewport = True

    opening = float(socket_contract["printed_opening_width_mm"])
    insertion_depth = float(socket_contract["insertion_depth_mm"])
    end_overlap = float(portal["socket_end_overlap_mm"])
    rail_reference_length = float(
        rails["modeled_installed_reference_length_mm"]
    )
    stop_distance_from_open = insertion_depth - end_overlap
    open_center = lower + axis * (
        rail_reference_length - stop_distance_from_open
    )
    socket_center = open_center + axis * (insertion_depth / 2.0)
    socket_values = {
        "tube_outer_width_mm": float(
            rails["profile"]["outside_width_mm"]
        ),
        "tube_design_clearance_mm": (
            opening - float(rails["profile"]["outside_width_mm"])
        ),
        "clamp_wall_mm": float(portal["socket_wall_mm"]),
        "clamp_length_mm": insertion_depth,
        "socket_end_overlap_mm": end_overlap,
        "m4_clearance_diameter_mm": float(
            socket_contract["cross_bolt_clearance_diameter_mm"]
        ),
        "bolt_offset_from_open_end_mm": float(
            socket_contract["cross_bolt_offset_from_open_end_mm"]
        ),
    }
    socket, socket_report = gate8.integrated_tube_socket(
        f"gate9_v6__{side}_tube_socket",
        socket_center,
        axis,
        across,
        outward,
        socket_values,
        materials["portal"],
    )
    socket_reference = duplicate_object(
        socket, f"gate9_v6__{side}_socket_reference"
    )
    socket_reference.data.materials.clear()
    socket_reference.data.materials.append(materials["reference"])

    pad_scale = float(portal["mount_pad_face_scale"])
    shell_wall = float(portal["shell_wall_thickness_mm"])
    pad_overlap = float(portal["mount_pad_shell_overlap_mm"])
    pad_front = [
        surface
        + (point - surface) * pad_scale
        - surface_normal * (shell_wall - pad_overlap)
        for point in face_vertices
    ]
    pad = gate7.finish_surface_insert(
        f"gate9_v6__{side}_portal_pad",
        pad_front,
        [tuple(range(len(pad_front)))],
        materials["portal"],
        float(portal["mount_pad_thickness_mm"]),
    )
    pad_reference = duplicate_object(
        pad, f"gate9_v6__{side}_pad_reference"
    )
    pad_reference.data.materials.clear()
    pad_reference.data.materials.append(materials["reference"])

    pre_union = {
        "pad_to_original_shell_triangle_overlap_pairs": (
            triangle_overlap_count(pad, shell)
        ),
        "socket_to_original_shell_triangle_overlap_pairs": (
            triangle_overlap_count(socket, shell)
        ),
        "pad_to_socket_triangle_overlap_pairs": (
            triangle_overlap_count(pad, socket)
        ),
    }
    shell_volume_before = gate5.mesh_volume(shell)
    true_union(shell, pad, f"{side} portal pad true union")
    true_union(shell, socket, f"{side} socket true union")
    shell_volume_after = gate5.mesh_volume(shell)

    outer_width = opening + 2.0 * float(portal["socket_wall_mm"])
    seated_end_clearance = float(
        portal["rail_seated_end_clearance_mm"]
    )
    rail_length = rail_reference_length - seated_end_clearance
    rail = gate5.box(
        f"gate9_v6__{side}_rail_fit_envelope",
        lower + axis * (rail_length / 2.0),
        (across, outward, axis),
        (
            float(rails["profile"]["outside_width_mm"]),
            float(rails["profile"]["outside_height_mm"]),
            rail_length,
        ),
        materials["rail"],
    )
    bolt_center = Vector(socket_report["bolt_center_mm"])
    bolt = radial_reference(
        f"gate9_v6__{side}_m4_bolt_body",
        bolt_center,
        across,
        float(hardware["m4_bolt_body_diameter_mm"]),
        outer_width + 12.0,
        materials["hardware"],
    )

    center_side = -1.0 if side == "right" else 1.0
    center_face = (
        bolt_center + across * center_side * (outer_width / 2.0)
    )
    outer_face = (
        bolt_center - across * center_side * (outer_width / 2.0)
    )
    head_stack = (
        float(hardware["m4_head_envelope_thickness_mm"])
        + float(hardware["m4_washer_envelope_thickness_mm"])
    )
    nut_stack = (
        float(hardware["m4_nut_envelope_thickness_mm"])
        + float(hardware["m4_washer_envelope_thickness_mm"])
    )
    head = radial_reference(
        f"gate9_v6__{side}_m4_head_washer_envelope",
        center_face + across * center_side * (head_stack / 2.0),
        across,
        float(hardware["m4_washer_envelope_diameter_mm"]),
        head_stack,
        materials["hardware"],
    )
    nut = radial_reference(
        f"gate9_v6__{side}_m4_nut_washer_envelope",
        outer_face - across * center_side * (nut_stack / 2.0),
        across,
        max(
            float(hardware["m4_nut_envelope_diameter_mm"]),
            float(hardware["m4_washer_envelope_diameter_mm"]),
        ),
        nut_stack,
        materials["hardware"],
    )
    tool_length = float(hardware["tool_approach_length_mm"])
    head_tool = radial_reference(
        f"gate9_v6__{side}_m4_head_tool_approach",
        center_face
        + across * center_side * (head_stack + tool_length / 2.0),
        across,
        float(hardware["tool_approach_diameter_mm"]),
        tool_length,
        materials["tool"],
    )
    nut_tool = radial_reference(
        f"gate9_v6__{side}_m4_nut_tool_approach",
        outer_face
        - across * center_side * (nut_stack + tool_length / 2.0),
        across,
        float(hardware["tool_approach_diameter_mm"]),
        tool_length,
        materials["tool"],
    )

    other_printed = {
        name: obj
        for name, obj in all_printed_parts.items()
        if obj is not shell
    }
    portal_feature_collisions = {
        "socket_to_other_printed_parts": collision_matrix(
            socket_reference, other_printed
        ),
        "pad_to_other_printed_parts": collision_matrix(
            pad_reference, other_printed
        ),
    }
    rail_fixed = {
        name: obj
        for name, obj in all_printed_parts.items()
        if name != "rear_bezel"
    }
    rail_seated = collision_matrix(rail, rail_fixed)
    rail_to_installed_service_parts = collision_matrix(
        rail,
        {
            "rear_bezel": all_printed_parts["rear_bezel"],
            "bottom_keel": all_printed_parts["bottom_keel"],
        },
    )
    rail_sweep = sweep_records(
        rail,
        -axis,
        [
            float(value)
            for value in portal["rail_withdrawal_test_offsets_mm"]
        ],
        rail_fixed,
    )
    hardware_clearances = {
        "bolt_body": comparison.collision_record(bolt, shell),
        "head_and_washer_to_original_shell_skin": (
            comparison.collision_record(head, original_shell)
        ),
        "nut_and_washer_to_original_shell_skin": (
            comparison.collision_record(nut, original_shell)
        ),
        "head_tool_approach": comparison.collision_record(
            head_tool, shell
        ),
        "nut_tool_approach": comparison.collision_record(
            nut_tool, shell
        ),
    }
    hardware_bearing_contacts = {
        "head_and_washer_to_portal_body": (
            comparison.collision_record(head, shell)
        ),
        "nut_and_washer_to_portal_body": (
            comparison.collision_record(nut, shell)
        ),
        "interpretation": (
            "contact with the unioned socket face is intentional bearing; "
            "the hardware clearance gate checks the original shell skin"
        ),
    }

    report = {
        "shell": f"{side}_upper_head",
        "source_face_index": source_face_index,
        "surface_anchor_mm": [
            round(float(value), 3) for value in surface
        ],
        "surface_normal": [
            round(float(value), 5) for value in surface_normal
        ],
        "lower_target_mm": [
            round(float(value), 3) for value in lower
        ],
        "accepted_axis": [
            round(float(value), 5) for value in axis
        ],
        "open_center_mm": [
            round(float(value), 3) for value in open_center
        ],
        "socket_roll_reference": socket_contract["roll_reference"],
        "cross_bolt_angle_from_head_x_deg": round(
            degrees(
                acos(
                    min(
                        1.0,
                        abs(across.dot(Vector((1.0, 0.0, 0.0)))),
                    )
                )
            ),
            3,
        ),
        "rail_reference_length_mm": rail_reference_length,
        "rail_modeled_length_with_end_clearance_mm": rail_length,
        "socket_opening_mm": [opening, opening],
        "socket_outer_width_mm": outer_width,
        "socket_length_mm": insertion_depth,
        "socket_wall_mm": float(portal["socket_wall_mm"]),
        "bolt_center_mm": socket_report["bolt_center_mm"],
        "bolt_axis": socket_report["bolt_axis"],
        "pre_union_overlap": pre_union,
        "socket_exterior_plane": feature_plane_report(
            socket_reference, surface, surface_normal
        ),
        "pad_exterior_plane": feature_plane_report(
            pad_reference, surface, surface_normal
        ),
        "shell_volume_before_mm3": round(shell_volume_before, 3),
        "shell_volume_after_mm3": round(shell_volume_after, 3),
        "shell_volume_added_mm3": round(
            shell_volume_after - shell_volume_before, 3
        ),
        "portal_feature_collisions": portal_feature_collisions,
        "rail_seated_collisions_without_rear_bezel": rail_seated,
        "rail_to_installed_service_parts": (
            rail_to_installed_service_parts
        ),
        "rail_withdrawal_sweep_without_rear_bezel": rail_sweep,
        "hardware_clearances": hardware_clearances,
        "hardware_bearing_contacts": hardware_bearing_contacts,
    }
    references = {
        "socket": socket_reference,
        "pad": pad_reference,
        "rail": rail,
        "bolt": bolt,
        "head": head,
        "nut": nut,
        "head_tool": head_tool,
        "nut_tool": nut_tool,
        "original_shell": original_shell,
    }
    return report, references


def add_fit_coupon(
    interface: dict[str, Any],
    config: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    portal = config["portal"]
    rails = interface["rail_system"]
    socket = rails["socket"]
    axis = Vector((0.0, 0.0, 1.0))
    across = Vector((1.0, 0.0, 0.0))
    outward = Vector((0.0, 1.0, 0.0))
    values = {
        "tube_outer_width_mm": float(
            rails["profile"]["outside_width_mm"]
        ),
        "tube_design_clearance_mm": (
            float(socket["printed_opening_width_mm"])
            - float(rails["profile"]["outside_width_mm"])
        ),
        "clamp_wall_mm": float(portal["socket_wall_mm"]),
        "clamp_length_mm": float(portal["fit_coupon_length_mm"]),
        "socket_end_overlap_mm": float(
            portal["socket_end_overlap_mm"]
        ),
        "m4_clearance_diameter_mm": float(
            socket["cross_bolt_clearance_diameter_mm"]
        ),
        "bolt_offset_from_open_end_mm": float(
            socket["cross_bolt_offset_from_open_end_mm"]
        ),
    }
    coupon, report = gate8.integrated_tube_socket(
        "gate9_v6__socket_fit_coupon",
        Vector((0.0, 0.0, 0.0)),
        axis,
        across,
        outward,
        values,
        material,
        length=float(portal["fit_coupon_length_mm"]),
    )
    bpy.ops.object.select_all(action="DESELECT")
    coupon.select_set(True)
    bpy.context.view_layer.objects.active = coupon
    coupon.rotation_euler.x = 1.5707963267948966
    bpy.ops.object.transform_apply(
        location=False, rotation=True, scale=True
    )
    coupon.select_set(False)
    require_single_manifold(coupon, "V6 socket fit coupon")
    report["stl_orientation"] = "one outer socket wall flat on print bed"
    report["physical_gate"] = (
        "print in the intended ASA process; verify hand insertion, "
        "seating, removal, and M4 drilling/bolt fit with actual tube"
    )
    return coupon, report


def main() -> None:
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface_path = (
        REPO_ROOT / config["shared_interface_path"]
    ).resolve()
    interface, interface_report = load_interface(
        interface_path,
        config["required_interface_revision"],
    )
    v5_config_path = (
        REPO_ROOT / config["source_v5_config"]
    ).resolve()
    original_v5_requested_config_path = v5.requested_config_path
    v5.requested_config_path = lambda: v5_config_path
    try:
        v5.main()
    finally:
        v5.requested_config_path = original_v5_requested_config_path

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    architecture_config = load_repo_json(
        config["source_architecture_config"]
    )
    printed_parts = {
        part: bpy.data.objects[
            (
                f"gate9_frame_candidate__{part}"
                if part in BODY_PARTS
                else f"gate9_v5__{part}"
            )
        ]
        for part in MODIFIED_PARTS
    }
    materials = {
        "portal": comparison.create_material(
            "gate9_v6_portal", "#2E80A1"
        ),
        "reference": comparison.create_material(
            "gate9_v6_portal_reference", "#45BFD3", alpha=0.32
        ),
        "rail": comparison.create_material(
            "gate9_v6_rail_reference", "#B8C1CA", alpha=0.5
        ),
        "hardware": comparison.create_material(
            "gate9_v6_m4_hardware", "#C78638", alpha=0.62
        ),
        "tool": comparison.create_material(
            "gate9_v6_tool_envelope", "#D14B45", alpha=0.28
        ),
    }
    portal_reports = {}
    references: dict[str, bpy.types.Object] = {}
    for side in ("left", "right"):
        report, side_references = add_portal(
            side,
            printed_parts[f"{side}_upper_head"],
            printed_parts,
            interface,
            config,
            materials,
        )
        portal_reports[side] = report
        references.update(
            {
                f"{side}_{name}": value
                for name, value in side_references.items()
            }
        )

    coupon, coupon_report = add_fit_coupon(
        interface, config, materials["portal"]
    )
    modified_stats = {
        part: v5.object_stats(obj, architecture_config)
        for part, obj in printed_parts.items()
    }
    coupon_stats = v5.object_stats(coupon, architecture_config)
    topology_pass = all(
        value["connected_components"] == 1
        and value["boundary_edges"] == 0
        and value["nonmanifold_edges"] == 0
        for value in modified_stats.values()
    ) and (
        coupon_stats["connected_components"] == 1
        and coupon_stats["boundary_edges"] == 0
        and coupon_stats["nonmanifold_edges"] == 0
    )
    axes_pass = all(
        max(
            abs(
                portal_reports[side]["accepted_axis"][index]
                - float(
                    interface["rail_system"]["accepted_axes_head"][
                        side
                    ][index]
                )
            )
            for index in range(3)
        )
        <= float(
            interface["validation_tolerances"][
                "rail_axis_angular_error_deg_max"
            ]
        )
        for side in ("left", "right")
    )
    cross_bolt_angle_pass = all(
        abs(
            portal_reports[side][
                "cross_bolt_angle_from_head_x_deg"
            ]
            - float(
                interface["rail_system"]["socket"][
                    "expected_cross_bolt_angle_from_head_x_deg"
                ]
            )
        )
        <= 0.01
        for side in ("left", "right")
    )
    opening_pass = all(
        portal_reports[side]["socket_opening_mm"]
        == [
            float(
                interface["rail_system"]["socket"][
                    "printed_opening_width_mm"
                ]
            ),
            float(
                interface["rail_system"]["socket"][
                    "printed_opening_height_mm"
                ]
            ),
        ]
        for side in ("left", "right")
    )
    true_union_pass = all(
        report["pre_union_overlap"][
            "pad_to_original_shell_triangle_overlap_pairs"
        ]
        > 0
        and report["pre_union_overlap"][
            "pad_to_socket_triangle_overlap_pairs"
        ]
        > 0
        and report["shell_volume_added_mm3"] > 0.0
        for report in portal_reports.values()
    )
    exterior_pass = all(
        report["socket_exterior_plane"][
            "minimum_exterior_recess_mm"
        ]
        >= float(config["portal"]["minimum_socket_exterior_recess_mm"])
        and report["socket_exterior_plane"][
            "outside_exterior_plane_vertex_count"
        ]
        == 0
        and report["pad_exterior_plane"][
            "outside_exterior_plane_vertex_count"
        ]
        == 0
        for report in portal_reports.values()
    )
    portal_features_clear = all(
        all_clear(
            report["portal_feature_collisions"][
                "socket_to_other_printed_parts"
            ]
        )
        and all_clear(
            report["portal_feature_collisions"][
                "pad_to_other_printed_parts"
            ]
        )
        for report in portal_reports.values()
    )
    rail_paths_clear = all(
        all_clear(
            report["rail_seated_collisions_without_rear_bezel"]
        )
        and all_clear(report["rail_to_installed_service_parts"])
        and all(
            value["clear"]
            for value in report[
                "rail_withdrawal_sweep_without_rear_bezel"
            ]
        )
        for report in portal_reports.values()
    )
    hardware_clear = all(
        all(not value["intersects"] for value in report[
            "hardware_clearances"
        ].values())
        for report in portal_reports.values()
    )

    validation = {
        "shared_v03_interface_contract_passes": (
            interface_report["status"].startswith("PASS")
        ),
        "all_six_modified_parts_and_coupon_one_closed_manifold_component": (
            topology_pass
        ),
        "portal_pads_and_sockets_have_true_overlapping_union_roots": (
            true_union_pass
        ),
        "socket_openings_match_frozen_20p5_mm_contract": opening_pass,
        "rail_axes_and_head_x_projected_roll_match_frozen_v03": (
            axes_pass and cross_bolt_angle_pass
        ),
        "socket_and_pad_features_stay_behind_exterior_planes": (
            exterior_pass
        ),
        "portal_features_clear_other_printed_parts": (
            portal_features_clear
        ),
        "seated_rails_and_sampled_straight_insertion_paths_clear": (
            rail_paths_clear
        ),
        "m4_hardware_and_straight_tool_approach_envelopes_clear": (
            hardware_clear
        ),
    }
    validation["digital_v6_socket_portal_candidate_pass"] = all(
        validation.values()
    )

    shells_dir = output_dir / "shells"
    for name, obj in printed_parts.items():
        comparison.export_stl(obj, shells_dir / f"{name}.stl")
    coupon_dir = output_dir / "test-coupons"
    comparison.export_stl(
        coupon,
        coupon_dir / "gate9_v6_socket_fit_coupon.stl",
    )

    all_review_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name.startswith(
            (
                "gate9_frame_candidate__",
                "gate9_v5__",
                "gate9_v6__",
                "review_frame__",
            )
        )
    ]
    camera = bpy.data.objects.get("Bridge_Audit_Camera")
    if camera is None:
        camera = v5.v3.base.audit.configure_workbench_render()
    for render_name, selected in (
        (
            "v6_socket_portals__assembled",
            [
                *printed_parts.values(),
                references["left_rail"],
                references["right_rail"],
            ],
        ),
        (
            "v6_socket_portals__internal_detail",
            [
                printed_parts["left_upper_head"],
                printed_parts["right_upper_head"],
                *[
                    value
                    for name, value in references.items()
                    if not name.endswith("original_shell")
                ],
            ],
        ),
        ("v6_socket_fit_coupon", [coupon]),
    ):
        v5.v3.base.audit.render_part(
            render_name,
            selected,
            all_review_objects,
            output_dir,
            camera,
        )
    for original in (
        references["left_original_shell"],
        references["right_original_shell"],
    ):
        original.hide_render = True
        original.hide_viewport = True

    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = output_dir / "gate9-socket-portals-candidate-v6.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "portal_construction": config["portal"]["construction"],
        "portals": portal_reports,
        "fit_coupon": coupon_report,
        "parts": modified_stats,
        "fit_coupon_stats": coupon_stats,
        "validation": validation,
        "acceptance_holds": config["acceptance_holds"],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "shell_stls": str(shells_dir.relative_to(REPO_ROOT)),
            "fit_coupon_stl": str(
                (
                    coupon_dir / "gate9_v6_socket_fit_coupon.stl"
                ).relative_to(REPO_ROOT)
            ),
            "renders": str(
                (output_dir / "renders").relative_to(REPO_ROOT)
            ),
        },
    }
    report_path = output_dir / "gate9-socket-portals-candidate-v6.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "portals": {
                    side: {
                        "axis": value["accepted_axis"],
                        "opening_mm": value["socket_opening_mm"],
                        "minimum_socket_exterior_recess_mm": (
                            value["socket_exterior_plane"][
                                "minimum_exterior_recess_mm"
                            ]
                        ),
                        "hardware_clearances": (
                            value["hardware_clearances"]
                        ),
                    }
                    for side, value in portal_reports.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not validation["digital_v6_socket_portal_candidate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
