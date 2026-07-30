#!/usr/bin/env python3
"""Generate Gate 9 V7 shell integration for the aluminum V0.5-M2 handoff."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


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
import generate_gate9_complementary_service_parts_candidate_v5 as v5  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402
import generate_gate9_socket_portals_candidate_v6 as v6  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-m2-rear-interface-candidate-v7.json"
)
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
SERVICE_PARTS = ("rear_bezel", "bottom_keel")
PRINTED_PARTS = (*BODY_PARTS, *SERVICE_PARTS)
_STATIC_COLLISION_CACHE: dict[
    int, tuple[Any, tuple[Vector, Vector]]
] = {}


def stage(message: str, started_at: float) -> float:
    now = time.monotonic()
    print(
        f"[gate9-v7 +{now - started_at:8.2f}s] {message}",
        flush=True,
    )
    return now


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


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
    component_count = len(gate5.components(obj))
    if component_count != 1:
        raise ValueError(
            f"{operation}: {obj.name} has {component_count} components"
        )


def true_union(
    owner: bpy.types.Object,
    feature: bpy.types.Object,
    operation: str,
) -> None:
    gate5.apply_boolean(owner, feature, "UNION", solver="MANIFOLD")
    require_single_manifold(owner, operation)


def rear_basis(
    interface: dict[str, Any],
) -> tuple[Vector, Vector, Vector, Vector]:
    center = Vector(
        interface["rear_interface_plane"]["center_head_mm"]
    )
    normal = Vector(
        interface["rear_interface_plane"]["outward_normal_head"]
    ).normalized()
    across = Vector((1.0, 0.0, 0.0))
    vertical = across.cross(normal).normalized()
    return center, normal, across, vertical


def plane_point(
    center: Vector,
    normal: Vector,
    across: Vector,
    vertical: Vector,
    local_x: float,
    local_v: float,
    local_t: float,
) -> Vector:
    return (
        center
        + across * local_x
        + vertical * local_v
        + normal * local_t
    )


def beam_between(
    name: str,
    start: Vector,
    end: Vector,
    width: float,
    depth: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    axis = (end - start).normalized()
    transverse = Vector((1.0, 0.0, 0.0))
    transverse -= axis * transverse.dot(axis)
    if transverse.length < 0.1:
        transverse = Vector((0.0, 0.0, 1.0))
        transverse -= axis * transverse.dot(axis)
    transverse.normalize()
    second = axis.cross(transverse).normalized()
    overlap = 2.0
    return gate5.box(
        name,
        (start + end) / 2.0,
        (transverse, second, axis),
        (width, depth, (end - start).length + 2.0 * overlap),
        material,
    )


def root_box(
    name: str,
    surface_center: Vector,
    cavity_normal: Vector,
    tangent_width: float,
    tangent_height: float,
    penetration: float,
    overlap_into_shell: float,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, Vector, dict[str, Any]]:
    cavity_normal = cavity_normal.normalized()
    inward = -cavity_normal
    tangent = Vector((1.0, 0.0, 0.0))
    tangent -= inward * tangent.dot(inward)
    if tangent.length < 0.1:
        tangent = Vector((0.0, 0.0, 1.0))
        tangent -= inward * tangent.dot(inward)
    tangent.normalize()
    second = inward.cross(tangent).normalized()
    center = (
        surface_center
        + cavity_normal * (penetration / 2.0 - overlap_into_shell)
    )
    root = gate5.box(
        name,
        center,
        (tangent, second, inward),
        (tangent_width, tangent_height, penetration),
        material,
    )
    signed_distances = [
        (
            (root.matrix_world @ vertex.co) - surface_center
        ).dot(cavity_normal)
        for vertex in root.data.vertices
    ]
    minimum_distance = min(signed_distances)
    maximum_distance = max(signed_distances)
    return root, center, {
        "cavity_reach_from_shell_skin_mm": round(maximum_distance, 5),
        "shell_overlap_depth_mm": round(-minimum_distance, 5),
        "root_total_span_mm": round(
            maximum_distance - minimum_distance, 5
        ),
        "root_face_area_mm2": round(
            tangent_width * tangent_height, 3
        ),
        "overlap_into_shell_mm": overlap_into_shell,
        "center_head_mm": [
            round(float(value), 3) for value in center
        ],
    }


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


def expanded_cylinder_copy(
    source: bpy.types.Object,
    name: str,
    clearance_mm: float,
    translation: Vector,
) -> bpy.types.Object:
    """Expand a cylindrical hardware envelope radially and axially."""
    expanded = duplicate_object(source, name)
    world_matrix = expanded.matrix_world.copy()
    inverse_world = world_matrix.inverted()
    world_vertices = [
        world_matrix @ vertex.co for vertex in expanded.data.vertices
    ]
    center = sum(world_vertices, Vector()) / len(world_vertices)
    cap_face = max(
        expanded.data.polygons,
        key=lambda polygon: len(polygon.vertices),
    )
    axis = (world_matrix.to_3x3() @ cap_face.normal).normalized()
    for vertex, world in zip(expanded.data.vertices, world_vertices):
        delta = world - center
        axial = delta.dot(axis)
        radial = delta - axis * axial
        if abs(axial) > 1e-6:
            axial += clearance_mm if axial > 0.0 else -clearance_mm
        if radial.length > 1e-6:
            radial *= (radial.length + clearance_mm) / radial.length
        vertex.co = inverse_world @ (center + axis * axial + radial)
    expanded.location += translation
    expanded.data.update()
    return expanded


def crossbolt_service_tunnel(
    name: str,
    hardware: bpy.types.Object,
    common_withdrawal: Vector,
    travel_mm: float,
    clearance_mm: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    start = expanded_cylinder_copy(
        hardware,
        f"{name}_start",
        clearance_mm,
        Vector(),
    )
    end = expanded_cylinder_copy(
        hardware,
        f"{name}_end",
        clearance_mm,
        common_withdrawal * travel_mm,
    )
    return gate5.convex_hull_objects(name, [start, end], material)


def collision_summary(
    moving: bpy.types.Object,
    fixed: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    moving_bvh = comparison.object_bvh(moving)
    moving_bounds = object_bounds(moving)
    records = {}
    for name, obj in fixed.items():
        cache_key = obj.as_pointer()
        if cache_key not in _STATIC_COLLISION_CACHE:
            _STATIC_COLLISION_CACHE[cache_key] = (
                comparison.object_bvh(obj),
                object_bounds(obj),
            )
        fixed_bvh, fixed_bounds = _STATIC_COLLISION_CACHE[cache_key]
        broad_phase_clear = any(
            moving_bounds[1][axis] < fixed_bounds[0][axis]
            or fixed_bounds[1][axis] < moving_bounds[0][axis]
            for axis in range(3)
        )
        overlaps = (
            []
            if broad_phase_clear
            else moving_bvh.overlap(fixed_bvh)
        )
        records[name] = {
            "first": moving.name,
            "second": obj.name,
            "triangle_overlap_pair_count": len(overlaps),
            "minimum_sampled_vertex_to_surface_distance_mm": None,
            "intersects": bool(overlaps),
            "audit_mode": "aabb_then_exact_triangle_bvh_overlap",
        }
    return {
        "clear": all(
            not record["intersects"] for record in records.values()
        ),
        "collisions": {
            name: record
            for name, record in records.items()
            if record["intersects"]
        },
    }


def append_m2_objects(
    blend_path: Path,
) -> dict[str, bpy.types.Object]:
    with bpy.data.libraries.load(
        str(blend_path), link=False
    ) as (data_from, data_to):
        data_to.objects = [
            name
            for name in data_from.objects
            if name.startswith("metal_v05__")
        ]
    objects = {}
    for obj in data_to.objects:
        if obj is None:
            continue
        if obj.name not in bpy.context.scene.collection.objects:
            bpy.context.collection.objects.link(obj)
        objects[obj.name] = obj
    if "metal_v05__backplate" not in objects:
        raise ValueError("M2 review blend did not provide the backplate")
    return objects


def joined_feature(
    name: str,
    objects: list[bpy.types.Object],
) -> bpy.types.Object:
    if not objects:
        raise ValueError(f"{name}: no feature objects")
    material = objects[0].data.materials[0]
    feature = gate5.convex_hull_objects(name, objects, material)
    require_single_manifold(feature, f"{name} closed structural hull")
    return feature


def voxel_fused_feature(
    name: str,
    objects: list[bpy.types.Object],
    material: bpy.types.Material,
    voxel_size_mm: float = 0.5,
) -> bpy.types.Object:
    if not objects:
        raise ValueError(f"{name}: no feature objects")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    feature = bpy.context.object
    feature.name = name
    feature.data.remesh_voxel_size = voxel_size_mm
    feature.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
    feature.data.materials.clear()
    feature.data.materials.append(material)
    feature.select_set(False)
    require_single_manifold(feature, f"{name} routed voxel fuse")
    return feature


def attachment_specs(
    interface: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    owners = config["rear_structure"]["owner_by_local_x_v"]
    centers = interface["aluminum_backplate"][
        "shell_attachment_hole_pattern"
    ]["local_x_v_centers_mm"]
    specs = []
    for local_x, local_v in centers:
        key = f"{float(local_x):g},{float(local_v):g}"
        specs.append(
            {
                "key": key,
                "local_x_mm": float(local_x),
                "local_v_mm": float(local_v),
                "owner": owners[key],
            }
        )
    return specs


def add_structural_attachments(
    printed_parts: dict[str, bpy.types.Object],
    metal_objects: dict[str, bpy.types.Object],
    interface: dict[str, Any],
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
) -> tuple[
    dict[str, Any],
    dict[str, bpy.types.Object],
    dict[str, dict[str, bpy.types.Object]],
]:
    values = config["rear_structure"]
    plate = interface["aluminum_backplate"]
    plate_thickness = float(plate["thickness_mm"])
    center, normal, across, vertical = rear_basis(interface)
    outer_face_t = (
        -plate_thickness / 2.0
        - float(values["plate_to_pad_nominal_gap_mm"])
    )
    pad_depth = float(values["pad_depth_mm"])
    pad_center_t = outer_face_t - pad_depth / 2.0
    pad_inner_t = outer_face_t - pad_depth
    specs = attachment_specs(interface, config)

    originals = {
        name: duplicate_object(
            printed_parts[name],
            f"gate9_v7__{name}_pre_rear_structure",
        )
        for name in BODY_PARTS
    }
    for obj in originals.values():
        obj.hide_render = True
        obj.hide_viewport = True

    owner_features: dict[str, list[bpy.types.Object]] = {
        name: [] for name in BODY_PARTS
    }
    boss_records: dict[str, Any] = {}
    boss_objects: dict[str, bpy.types.Object] = {}

    for spec in specs:
        local_x = spec["local_x_mm"]
        local_v = spec["local_v_mm"]
        if local_v == 30.0:
            width = float(values["top_pad_width_mm"])
            height = float(values["top_pad_height_mm"])
            geometry = "rectangular_pad"
            boss = gate5.box(
                f"gate9_v7__m5_boss_{spec['key'].replace(',', '_')}",
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_center_t,
                ),
                (across, vertical, normal),
                (width, height, pad_depth),
                materials["structure"],
            )
        elif local_v == -30.0:
            width = float(values["bottom_pad_width_mm"])
            height = float(values["bottom_pad_height_mm"])
            geometry = "rectangular_pad"
            boss = gate5.box(
                f"gate9_v7__m5_boss_{spec['key'].replace(',', '_')}",
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_center_t,
                ),
                (across, vertical, normal),
                (width, height, pad_depth),
                materials["structure"],
            )
        else:
            width = height = float(values["middle_pad_diameter_mm"])
            geometry = "circular_boss"
            boss = radial_reference(
                f"gate9_v7__m5_boss_{spec['key'].replace(',', '_')}",
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_center_t,
                ),
                normal,
                width,
                pad_depth,
                materials["structure"],
            )
        owner_features[spec["owner"]].append(boss)
        boss_objects[spec["key"]] = duplicate_object(
            boss,
            f"{boss.name}_pair_clearance_reference",
        )
        boss_records[spec["key"]] = {
            **spec,
            "geometry": geometry,
            "dimensions_mm": [width, height, pad_depth],
            "washer_bearing_edge_mm": round(
                min(width, height) / 2.0
                - float(values["washer_outer_diameter_mm"]) / 2.0,
                3,
            ),
            "tool_envelope_edge_mm": round(
                min(width, height) / 2.0
                - float(values["tool_approach_diameter_mm"]) / 2.0,
                3,
            ),
            "captive_nut_pocket_min_wall_mm": round(
                min(width, height) / 2.0
                - float(
                    values[
                        "captive_nyloc_pocket_across_corners_mm"
                    ]
                )
                / 2.0,
                3,
            ),
            "captive_nut_flat_clearance_each_side_mm": round(
                (
                    float(
                        values[
                            "captive_nyloc_pocket_across_flats_mm"
                        ]
                    )
                    - float(values["nyloc_envelope_across_flats_mm"])
                )
                / 2.0,
                3,
            ),
            "solid_pad_depth_beyond_nut_pocket_mm": round(
                pad_depth
                - float(values["captive_nyloc_pocket_depth_mm"]),
                3,
            ),
        }

    root_records: dict[str, Any] = {}
    for side in ("left", "right"):
        sign = -1.0 if side == "left" else 1.0
        owner = f"{side}_upper_head"
        web = gate5.box(
            f"gate9_v7__{side}_upper_pair_web",
            plane_point(
                center,
                normal,
                across,
                vertical,
                sign * float(values["upper_pair_web_center_x_abs_mm"]),
                float(values["upper_pair_web_center_v_mm"]),
                pad_center_t,
            ),
            (across, vertical, normal),
            (
                float(values["upper_pair_web_width_mm"]),
                float(values["upper_pair_web_height_mm"]),
                pad_depth,
            ),
            materials["structure"],
        )
        owner_features[owner].append(web)
        root_spec = values["upper_root_facets"][side]
        root_surface = Vector(root_spec["center_head_mm"])
        cavity_normal = Vector(root_spec["cavity_normal_head"])
        root, root_center, record = root_box(
            f"gate9_v7__{side}_upper_root",
            root_surface,
            cavity_normal,
            float(values["root_tangent_width_mm"]),
            float(values["root_tangent_height_mm"]),
            float(values["root_penetration_mm"]),
            float(values["root_overlap_into_shell_mm"]),
            materials["structure"],
        )
        owner_features[owner].append(root)
        source = plane_point(
            center,
            normal,
            across,
            vertical,
            sign * float(values["upper_pair_web_center_x_abs_mm"]),
            float(values["upper_truss_source_v_mm"]),
            pad_center_t - pad_depth / 4.0,
        )
        waypoint = plane_point(
            center,
            normal,
            across,
            vertical,
            sign * float(values["upper_pair_web_center_x_abs_mm"]),
            float(values["upper_truss_waypoint_v_mm"]),
            float(values["upper_truss_waypoint_t_mm"]),
        )
        tangent = Vector((1.0, 0.0, 0.0))
        tangent -= cavity_normal * tangent.dot(cavity_normal)
        tangent.normalize()
        beam_offset = float(values["truss_beam_offset_mm"])
        for beam_index, offset in enumerate((-beam_offset, beam_offset)):
            first = waypoint + across * offset
            owner_features[owner].append(
                beam_between(
                    f"gate9_v7__{side}_upper_truss_a_{beam_index:02d}",
                    source + across * offset,
                    first,
                    float(values["truss_beam_width_mm"]),
                    float(values["truss_beam_depth_mm"]),
                    materials["structure"],
                )
            )
            owner_features[owner].append(
                beam_between(
                    f"gate9_v7__{side}_upper_truss_b_{beam_index:02d}",
                    first,
                    root_center + tangent * offset,
                    float(values["truss_beam_width_mm"]),
                    float(values["truss_beam_depth_mm"]),
                    materials["structure"],
                )
            )
        root_records[f"{side}_upper"] = {
            **root_spec,
            **record,
        }

        owner = f"{side}_lower_face"
        root_spec = values["lower_root_facets"][side]
        root_surface = Vector(root_spec["center_head_mm"])
        cavity_normal = Vector(root_spec["cavity_normal_head"])
        root, root_center, record = root_box(
            f"gate9_v7__{side}_lower_root",
            root_surface,
            cavity_normal,
            float(values["root_tangent_width_mm"]),
            float(values["root_tangent_height_mm"]),
            float(values["root_penetration_mm"]),
            float(values["root_overlap_into_shell_mm"]),
            materials["structure"],
        )
        owner_features[owner].append(root)
        source = plane_point(
            center,
            normal,
            across,
            vertical,
            sign * float(values["lower_truss_source_x_abs_mm"]),
            float(values["lower_truss_source_v_mm"]),
            pad_center_t - pad_depth / 4.0,
        )
        waypoint = plane_point(
            center,
            normal,
            across,
            vertical,
            sign * float(values["lower_truss_waypoint_x_abs_mm"]),
            float(values["lower_truss_waypoint_v_mm"]),
            float(values["lower_truss_waypoint_t_mm"]),
        )
        tangent = Vector((1.0, 0.0, 0.0))
        tangent -= cavity_normal * tangent.dot(cavity_normal)
        tangent.normalize()
        beam_offset = float(values["lower_truss_beam_offset_mm"])
        for beam_index, offset in enumerate((-beam_offset, beam_offset)):
            first = waypoint + across * offset
            owner_features[owner].append(
                beam_between(
                    f"gate9_v7__{side}_lower_truss_a_{beam_index:02d}",
                    source + across * offset,
                    first,
                    float(values["lower_truss_beam_width_mm"]),
                    float(values["lower_truss_beam_depth_mm"]),
                    materials["structure"],
                )
            )
            owner_features[owner].append(
                beam_between(
                    f"gate9_v7__{side}_lower_truss_b_{beam_index:02d}",
                    first,
                    root_center + tangent * offset,
                    float(values["lower_truss_beam_width_mm"]),
                    float(values["lower_truss_beam_depth_mm"]),
                    materials["structure"],
                )
            )
        root_records[f"{side}_lower"] = {
            **root_spec,
            **record,
        }

    feature_references: dict[str, bpy.types.Object] = {}
    pre_union_overlap: dict[str, int] = {}
    service_tunnel_records: dict[str, Any] = {}
    axes = interface["rail_system"]["accepted_axes_head"]
    common_withdrawal = (
        -Vector(axes["left"]).normalized()
        - Vector(axes["right"]).normalized()
    ).normalized()
    travel_mm = max(
        float(value)
        for value in config["serviceable_socket"][
            "rigid_common_withdrawal_offsets_mm"
        ]
    )
    tunnel_clearance = float(
        values["crossbolt_service_tunnel_clearance_mm"]
    )
    for owner, features in owner_features.items():
        feature = voxel_fused_feature(
            f"gate9_v7__{owner}_rear_structure",
            features,
            materials["structure"],
            float(values["truss_voxel_fuse_resolution_mm"]),
        )
        if owner.endswith("_upper_head"):
            side = owner.split("_", 1)[0]
            before_volume = gate5.mesh_volume(feature)
            removed_by_hardware = {}
            for role in ("crossbolt", "crossbolt_head", "crossbolt_nut"):
                for index in (0, 1):
                    hardware_name = (
                        f"metal_v05__{role}_{side}_{index:02d}"
                    )
                    tunnel = crossbolt_service_tunnel(
                        f"gate9_v7__{side}_{role}_{index:02d}_service_tunnel",
                        metal_objects[hardware_name],
                        common_withdrawal,
                        travel_mm,
                        tunnel_clearance,
                        materials["cutter"],
                    )
                    overlap = comparison.collision_record(tunnel, feature)
                    preexisting_shell_overlap = comparison.collision_record(
                        tunnel, originals[owner]
                    )
                    gate5.apply_boolean(
                        feature,
                        tunnel,
                        "DIFFERENCE",
                        solver="MANIFOLD",
                    )
                    require_single_manifold(
                        feature,
                        f"{owner} {hardware_name} service relief",
                    )
                    removed_by_hardware[hardware_name] = {
                        "intersected_new_structure": overlap["intersects"],
                        "triangle_overlap_pair_count": overlap[
                            "triangle_overlap_pair_count"
                        ],
                        "intersects_preexisting_v6_shell": (
                            preexisting_shell_overlap["intersects"]
                        ),
                    }
            after_volume = gate5.mesh_volume(feature)
            service_tunnel_records[side] = {
                "travel_mm": travel_mm,
                "radial_and_axial_clearance_mm": tunnel_clearance,
                "new_structure_volume_before_mm3": round(before_volume, 3),
                "new_structure_volume_after_mm3": round(after_volume, 3),
                "new_structure_volume_removed_mm3": round(
                    before_volume - after_volume, 3
                ),
                "hardware_sweeps": removed_by_hardware,
            }
        reference = duplicate_object(
            feature,
            f"gate9_v7__{owner}_rear_structure_reference",
        )
        reference.data.materials.clear()
        reference.data.materials.append(materials["reference"])
        feature_references[owner] = reference
        pre_union_overlap[owner] = v6.triangle_overlap_count(
            feature, printed_parts[owner]
        )
        true_union(
            printed_parts[owner],
            feature,
            f"{owner} V7 rear structure true union",
        )

    hardware: dict[str, dict[str, bpy.types.Object]] = {}
    for spec in specs:
        local_x = spec["local_x_mm"]
        local_v = spec["local_v_mm"]
        owner = printed_parts[spec["owner"]]
        hole_center = plane_point(
            center,
            normal,
            across,
            vertical,
            local_x,
            local_v,
            0.0,
        )
        bore = gate5.cylinder(
            f"gate9_v7__m5_bore_{spec['key'].replace(',', '_')}",
            hole_center + normal * (plate_thickness + 2.0),
            hole_center
            - normal
            * (
                plate_thickness
                + pad_depth
                + 2.0
            ),
            float(values["m5_clearance_diameter_mm"]),
            vertices=32,
        )
        gate5.apply_boolean(
            owner, bore, "DIFFERENCE", solver="MANIFOLD"
        )
        require_single_manifold(owner, f"{spec['key']} M5 bore")
        captive_depth = float(values["captive_nyloc_pocket_depth_mm"])
        pocket_entry = plane_point(
            center,
            normal,
            across,
            vertical,
            local_x,
            local_v,
            pad_inner_t
            - float(values["captive_nyloc_pocket_entry_overlap_mm"]),
        )
        pocket_end = plane_point(
            center,
            normal,
            across,
            vertical,
            local_x,
            local_v,
            pad_inner_t + captive_depth,
        )
        captive_pocket = gate5.cylinder(
            f"gate9_v7__m5_captive_nyloc_pocket_{spec['key'].replace(',', '_')}",
            pocket_entry,
            pocket_end,
            float(
                values["captive_nyloc_pocket_across_corners_mm"]
            ),
            materials["cutter"],
            vertices=6,
        )
        gate5.apply_boolean(
            owner,
            captive_pocket,
            "DIFFERENCE",
            solver="MANIFOLD",
        )
        require_single_manifold(
            owner, f"{spec['key']} captive M5 nyloc pocket"
        )

        head_stack = (
            float(values["bolt_head_envelope_thickness_mm"])
            + float(values["washer_thickness_mm"])
        )
        nut_stack = float(values["captive_nyloc_thickness_mm"])
        hardware[spec["key"]] = {
            "bolt_body": radial_reference(
                f"gate9_v7__m5_bolt_{spec['key'].replace(',', '_')}",
                hole_center
                + normal
                * (
                    plate_thickness / 2.0
                    - float(values["bolt_thread_length_mm"]) / 2.0
                ),
                normal,
                float(values["m5_clearance_diameter_mm"]) - 0.3,
                float(values["bolt_thread_length_mm"]),
                materials["hardware"],
            ),
            "head_washer": radial_reference(
                f"gate9_v7__m5_head_{spec['key'].replace(',', '_')}",
                hole_center
                + normal * (plate_thickness / 2.0 + head_stack / 2.0),
                normal,
                float(values["bolt_head_envelope_diameter_mm"]),
                head_stack,
                materials["hardware"],
            ),
            "captive_nut": gate5.cylinder(
                f"gate9_v7__m5_nut_{spec['key'].replace(',', '_')}",
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_inner_t,
                ),
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_inner_t + nut_stack,
                ),
                float(values["nyloc_envelope_across_corners_mm"]),
                materials["hardware"],
                vertices=6,
            ),
            "rear_tool": radial_reference(
                f"gate9_v7__m5_rear_tool_{spec['key'].replace(',', '_')}",
                hole_center
                + normal
                * (
                    plate_thickness / 2.0
                    + head_stack
                    + float(values["tool_approach_length_mm"]) / 2.0
                ),
                normal,
                float(values["tool_approach_diameter_mm"]),
                float(values["tool_approach_length_mm"]),
                materials["tool"],
            ),
            "captive_nut_install_tool": radial_reference(
                f"gate9_v7__m5_captive_nut_install_tool_{spec['key'].replace(',', '_')}",
                plane_point(
                    center,
                    normal,
                    across,
                    vertical,
                    local_x,
                    local_v,
                    pad_inner_t
                    - float(values["tool_approach_length_mm"]) / 2.0,
                ),
                normal,
                float(values["tool_approach_diameter_mm"]),
                float(values["tool_approach_length_mm"]),
                materials["tool"],
            ),
        }

    pair_records = {}
    for left_key, right_key in (
        ("-10,30", "10,30"),
        ("-20,0", "20,0"),
        ("-7.4,-30", "7.4,-30"),
    ):
        left = boss_objects[left_key]
        right = boss_objects[right_key]
        pair_records[f"{left_key}__{right_key}"] = (
            comparison.collision_record(left, right)
        )
    for reference in boss_objects.values():
        bpy.data.objects.remove(reference, do_unlink=True)

    return (
        {
            "bosses": boss_records,
            "roots": root_records,
            "crossbolt_service_tunnels": service_tunnel_records,
            "pre_union_shell_overlap_pairs": pre_union_overlap,
            "opposing_boss_collisions": pair_records,
        },
        feature_references,
        hardware,
    )


def cut_serviceable_socket_and_add_cap(
    side: str,
    shell: bpy.types.Object,
    interface: dict[str, Any],
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
) -> tuple[bpy.types.Object, dict[str, Any], dict[str, bpy.types.Object]]:
    socket_values = config["serviceable_socket"]
    portal_values = json.loads(
        (
            REPO_ROOT / config["source_v6_config"]
        ).read_text(encoding="utf-8")
    )["portal"]
    rails = interface["rail_system"]
    socket = rails["socket"]
    lower = Vector(rails["lower_targets_head_mm"][side])
    axis = Vector(rails["accepted_axes_head"][side]).normalized()
    across, outward = v6.socket_basis(axis)
    outer_sign = -1.0 if side == "left" else 1.0
    opening = float(socket["printed_opening_width_mm"])
    depth = float(socket["insertion_depth_mm"])
    wall = float(portal_values["socket_wall_mm"])
    outer_width = opening + 2.0 * wall
    reference_length = float(
        rails["modeled_installed_reference_length_mm"]
    )
    end_overlap = float(portal_values["socket_end_overlap_mm"])
    open_center = lower + axis * (
        reference_length - (depth - end_overlap)
    )
    socket_center = open_center + axis * (depth / 2.0)
    original_shell = bpy.data.objects[
        f"gate9_v6__{side}_upper_original"
    ]

    wall_clearance = float(
        socket_values["removed_outer_wall_clearance_mm"]
    )
    cutter = gate5.box(
        f"gate9_v7__{side}_socket_outer_wall_cutter",
        socket_center
        + across
        * outer_sign
        * (opening / 2.0 + wall / 2.0),
        (across, outward, axis),
        (
            wall + 2.0 * wall_clearance,
            opening + 2.0 * wall_clearance,
            depth + 2.0 * wall_clearance,
        ),
        materials["cutter"],
    )
    cutter_to_original = comparison.collision_record(
        cutter, original_shell
    )
    gate5.apply_boolean(
        shell, cutter, "DIFFERENCE", solver="MANIFOLD"
    )
    require_single_manifold(shell, f"{side} U-cradle wall removal")

    cap_clearance = float(socket_values["cap_tongue_clearance_mm"])
    end_clearance = float(
        socket_values["cap_axis_end_clearance_mm"]
    )
    cover_thickness = float(
        socket_values["cap_cover_thickness_mm"]
    )
    tongue_inner = opening / 2.0
    tongue_outer = outer_width / 2.0 + 0.6
    tongue = gate5.box(
        f"gate9_v7__{side}_socket_cap_tongue",
        socket_center
        + across
        * outer_sign
        * ((tongue_inner + tongue_outer) / 2.0),
        (across, outward, axis),
        (
            tongue_outer - tongue_inner,
            opening - cap_clearance,
            depth - end_clearance,
        ),
        materials["cap"],
    )
    cover = gate5.box(
        f"gate9_v7__{side}_socket_cap_cover",
        socket_center
        + across
        * outer_sign
        * (outer_width / 2.0 + cover_thickness / 2.0),
        (across, outward, axis),
        (
            cover_thickness,
            outer_width,
            depth - end_clearance,
        ),
        materials["cap"],
    )
    cap = joined_feature(
        f"gate9_v7__{side}_socket_cap",
        [tongue, cover],
    )

    receiver_clearance = float(
        socket_values["cap_receiver_clearance_mm"]
    )
    receiver_inner = tongue_inner - receiver_clearance
    receiver_outer = (
        outer_width / 2.0
        + cover_thickness
        + receiver_clearance
    )
    receiver_relief = gate5.box(
        f"gate9_v7__{side}_socket_cap_receiver_relief",
        socket_center
        + across
        * outer_sign
        * ((receiver_inner + receiver_outer) / 2.0),
        (across, outward, axis),
        (
            receiver_outer - receiver_inner,
            outer_width + 2.0 * receiver_clearance,
            depth - end_clearance + 2.0 * receiver_clearance,
        ),
        materials["cutter"],
    )
    receiver_relief_to_original = comparison.collision_record(
        receiver_relief, original_shell
    )
    gate5.apply_boolean(
        shell,
        receiver_relief,
        "DIFFERENCE",
        solver="MANIFOLD",
    )
    require_single_manifold(
        shell, f"{side} cap receiver clearance relief"
    )

    bolt_center = open_center + axis * float(
        socket["cross_bolt_offset_from_open_end_mm"]
    )
    m4_bore = radial_reference(
        f"gate9_v7__{side}_cap_m4_bore",
        bolt_center,
        across,
        float(socket["cross_bolt_clearance_diameter_mm"]),
        outer_width + 2.0 * cover_thickness + 4.0,
        materials["cutter"],
    )
    gate5.apply_boolean(
        cap, m4_bore, "DIFFERENCE", solver="MANIFOLD"
    )
    require_single_manifold(cap, f"{side} cap M4 bore")

    cap_hardware: dict[str, bpy.types.Object] = {}
    insert_pocket_records = []
    for axis_index, station in enumerate(
        socket_values["cap_m3_axis_stations_from_mouth_mm"]
    ):
        for cross_index, cross_station in enumerate(
            socket_values["cap_m3_cross_section_stations_mm"]
        ):
            key = f"{axis_index}_{cross_index}"
            center = (
                open_center
                + axis * float(station)
                + outward * float(cross_station)
            )
            cap_hole = radial_reference(
                f"gate9_v7__{side}_cap_m3_bore_{key}",
                center
                + across
                * outer_sign
                * (outer_width / 2.0 + cover_thickness / 2.0),
                across,
                float(socket_values["cap_m3_clearance_diameter_mm"]),
                cover_thickness + 3.0,
                materials["cutter"],
            )
            gate5.apply_boolean(
                cap, cap_hole, "DIFFERENCE", solver="MANIFOLD"
            )
            require_single_manifold(
                cap, f"{side} cap M3 bore {key}"
            )
            pocket_depth = float(
                socket_values["cap_m3_insert_pocket_depth_mm"]
            )
            pocket = radial_reference(
                f"gate9_v7__{side}_cap_m3_insert_{key}",
                center
                + across
                * outer_sign
                * (outer_width / 2.0 - pocket_depth / 2.0),
                across,
                float(
                    socket_values[
                        "cap_m3_insert_pocket_diameter_mm"
                    ]
                ),
                pocket_depth + 0.5,
                materials["cutter"],
            )
            pocket_to_original = comparison.collision_record(
                pocket, original_shell
            )
            gate5.apply_boolean(
                shell, pocket, "DIFFERENCE", solver="MANIFOLD"
            )
            require_single_manifold(
                shell, f"{side} cap M3 insert pocket {key}"
            )
            insert_pocket_records.append(
                {
                    "key": key,
                    "center_head_mm": [
                        round(float(value), 3) for value in center
                    ],
                    "pocket_intersects_original_shell_skin": (
                        pocket_to_original["intersects"]
                    ),
                }
            )
            head_stack = float(
                socket_values["cap_m3_head_envelope_thickness_mm"]
            )
            tool_length = float(
                socket_values["cap_m3_tool_approach_length_mm"]
            )
            cap_hardware[f"m3_head_{key}"] = radial_reference(
                f"gate9_v7__{side}_cap_m3_head_{key}",
                center
                + across
                * outer_sign
                * (
                    outer_width / 2.0
                    + cover_thickness
                    + head_stack / 2.0
                ),
                across,
                float(
                    socket_values[
                        "cap_m3_head_envelope_diameter_mm"
                    ]
                ),
                head_stack,
                materials["hardware"],
            )
            cap_hardware[f"m3_tool_{key}"] = radial_reference(
                f"gate9_v7__{side}_cap_m3_tool_{key}",
                center
                + across
                * outer_sign
                * (
                    outer_width / 2.0
                    + cover_thickness
                    + head_stack
                    + tool_length / 2.0
                ),
                across,
                float(
                    socket_values[
                        "cap_m3_tool_approach_diameter_mm"
                    ]
                ),
                tool_length,
                materials["tool"],
            )

    require_single_manifold(cap, f"{side} completed socket cap")
    cap_report = {
        "side": side,
        "open_center_mm": [
            round(float(value), 3) for value in open_center
        ],
        "axis": [round(float(value), 5) for value in axis],
        "outer_side": (
            "negative socket-across"
            if outer_sign < 0.0
            else "positive socket-across"
        ),
        "restored_cavity_width_mm": opening,
        "restored_cavity_height_mm": opening,
        "socket_depth_mm": depth,
        "cap_m4_center_mm": [
            round(float(value), 3) for value in bolt_center
        ],
        "wall_cutter_intersects_original_shell_skin": (
            cutter_to_original["intersects"]
        ),
        "receiver_clearance_mm": receiver_clearance,
        "receiver_relief_intersects_original_shell_skin": (
            receiver_relief_to_original["intersects"]
        ),
        "insert_pockets": insert_pocket_records,
    }
    return cap, cap_report, cap_hardware


def rigid_metal_sweep(
    metal_objects: dict[str, bpy.types.Object],
    fixed_parts: dict[str, bpy.types.Object],
    interface: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    axes = interface["rail_system"]["accepted_axes_head"]
    common = (
        -Vector(axes["left"]).normalized()
        - Vector(axes["right"]).normalized()
    ).normalized()
    rear_normal = Vector(
        interface["rear_interface_plane"]["outward_normal_head"]
    ).normalized()
    socket_offsets = [
        float(value)
        for value in config["serviceable_socket"][
            "rigid_common_withdrawal_offsets_mm"
        ]
    ]
    rear_offsets = [
        float(value)
        for value in config["serviceable_socket"][
            "rear_clearance_offsets_after_socket_release_mm"
        ]
    ]
    paths = [
        {
            "phase": "socket_withdrawal",
            "socket_offset_mm": value,
            "rear_offset_mm": 0.0,
            "translation": common * value,
        }
        for value in socket_offsets
    ]
    release_offset = max(socket_offsets)
    paths.extend(
        {
            "phase": "rear_clearance",
            "socket_offset_mm": release_offset,
            "rear_offset_mm": value,
            "translation": common * release_offset + rear_normal * value,
        }
        for value in rear_offsets
    )

    records = []
    for sample_index, sample in enumerate(paths):
        observed = []
        for metal_name, metal in metal_objects.items():
            moving = duplicate_object(
                metal,
                f"{metal_name}__v7_sweep_{sample_index:02d}",
            )
            moving.location += sample["translation"]
            bpy.context.view_layer.update()
            summary = collision_summary(moving, fixed_parts)
            if not summary["clear"]:
                observed.append(
                    {
                        "metal": metal_name,
                        "fixed": summary["collisions"],
                    }
                )
            bpy.data.objects.remove(moving, do_unlink=True)
        records.append(
            {
                "phase": sample["phase"],
                "socket_offset_mm": sample["socket_offset_mm"],
                "rear_offset_mm": sample["rear_offset_mm"],
                "translation_head_mm": [
                    round(float(value), 3)
                    for value in sample["translation"]
                ],
                "clear": not observed,
                "observed_collisions": observed,
            }
        )
    axis_divergence_drift = (
        abs(
            Vector(axes["left"]).normalized().x
            - Vector(axes["right"]).normalized().x
        )
        / 2.0
        * float(
            interface["rail_system"]["socket"]["insertion_depth_mm"]
        )
    )
    existing_clearance = float(
        interface["rail_system"]["socket"][
            "nominal_clearance_each_side_mm"
        ]
    )
    return {
        "common_withdrawal_direction_head": [
            round(float(value), 6) for value in common
        ],
        "blind_socket_lateral_drift_over_30mm_mm": round(
            axis_divergence_drift, 4
        ),
        "blind_socket_available_lateral_clearance_mm": (
            existing_clearance
        ),
        "blind_socket_common_motion_limit_mm": round(
            existing_clearance
            / abs(Vector(axes["left"]).normalized().x),
            4,
        ),
        "blind_socket_rigid_pair_pass": (
            axis_divergence_drift <= existing_clearance
        ),
        "serviceable_socket_path_samples": records,
        "serviceable_socket_path_clear": all(
            record["clear"] for record in records
        ),
        "insertion_is_exact_reverse_of_sampled_removal": True,
    }


def object_bounds(
    obj: bpy.types.Object,
) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for corner in obj.bound_box
    ]
    return (
        Vector(
            (
                min(point.x for point in points),
                min(point.y for point in points),
                min(point.z for point in points),
            )
        ),
        Vector(
            (
                max(point.x for point in points),
                max(point.y for point in points),
                max(point.z for point in points),
            )
        ),
    )


def interface_object_stats(obj: bpy.types.Object) -> dict[str, Any]:
    minimum, maximum = object_bounds(obj)
    boundary_edges, nonmanifold_edges = gate5.topology_counts(obj)
    volume = gate5.mesh_volume(obj)
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "connected_components": len(gate5.components(obj)),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "dimensions_mm": [
            round(float(maximum[axis] - minimum[axis]), 3)
            for axis in range(3)
        ],
        "volume_mm3": round(volume, 3),
        "estimated_asa_mass_g": round(volume / 1000.0 * 1.07, 2),
        "orientation_search": "deferred_to_prusa_slicer_validation",
    }


def main() -> None:
    started_at = time.monotonic()
    stage("start", started_at)
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface_path = (
        REPO_ROOT / config["shared_interface_path"]
    ).resolve()
    interface, interface_report = load_interface(
        interface_path,
        config["required_interface_revision"],
    )
    metal_summary = json.loads(
        (REPO_ROOT / config["source_m2_summary"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        interface["metal_handoff_record"]["revision"]
        != config["required_metal_handoff_revision"]
    ):
        raise ValueError("shared interface does not carry the required M2 handoff")

    v6_config_path = (REPO_ROOT / config["source_v6_config"]).resolve()
    original_v6_requested_config_path = v6.requested_config_path
    v6.requested_config_path = lambda: v6_config_path
    try:
        v6.main()
    finally:
        v6.requested_config_path = original_v6_requested_config_path

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    printed_parts = {
        part: bpy.data.objects[
            (
                f"gate9_frame_candidate__{part}"
                if part in BODY_PARTS
                else f"gate9_v5__{part}"
            )
        ]
        for part in PRINTED_PARTS
    }
    materials = {
        "structure": comparison.create_material(
            "gate9_v7_rear_structure", "#2E80A1"
        ),
        "reference": comparison.create_material(
            "gate9_v7_structure_reference", "#45BFD3", alpha=0.28
        ),
        "cap": comparison.create_material(
            "gate9_v7_socket_cap", "#F0A13A"
        ),
        "hardware": comparison.create_material(
            "gate9_v7_hardware", "#C78638", alpha=0.62
        ),
        "tool": comparison.create_material(
            "gate9_v7_tool", "#D14B45", alpha=0.25
        ),
        "cutter": comparison.create_material(
            "gate9_v7_cutter", "#F05A5A", alpha=0.2
        ),
    }
    m2_blend_path = (REPO_ROOT / config["source_m2_review_blend"]).resolve()
    metal_objects = append_m2_objects(m2_blend_path)
    stage("source shells and complete M2 metal loaded", started_at)

    structure_report, structure_references, m5_hardware = (
        add_structural_attachments(
            printed_parts,
            metal_objects,
            interface,
            config,
            materials,
        )
    )
    stage("four routed structures fused into owner shells", started_at)

    caps = {}
    cap_reports = {}
    cap_hardware = {}
    for side in ("left", "right"):
        cap, report, hardware = cut_serviceable_socket_and_add_cap(
            side,
            printed_parts[f"{side}_upper_head"],
            interface,
            config,
            materials,
        )
        caps[side] = cap
        cap_reports[side] = report
        cap_hardware[side] = hardware
    stage("serviceable upper-socket cuts and caps complete", started_at)

    fixed_for_metal_path = {
        name: printed_parts[name] for name in BODY_PARTS
    }
    sweep_report = rigid_metal_sweep(
        metal_objects,
        fixed_for_metal_path,
        interface,
        config,
    )
    stage("rigid M2 removal/insertion sweep complete", started_at)

    seated_metal_collisions = {
        metal_name: collision_summary(metal, fixed_for_metal_path)
        for metal_name, metal in metal_objects.items()
    }
    cap_seated_collisions = {
        side: {
            "rail": comparison.collision_record(
                caps[side],
                metal_objects[f"metal_v05__rail_{side}"],
            ),
            "shell": comparison.collision_record(
                caps[side],
                printed_parts[f"{side}_upper_head"],
            ),
        }
        for side in ("left", "right")
    }
    stage("seated metal and cap collision audit complete", started_at)

    m5_clearance_report = {}
    metal_without_plate = {
        name: obj
        for name, obj in metal_objects.items()
        if name != "metal_v05__backplate"
    }
    for key, hardware in m5_hardware.items():
        other_printed = {
            name: obj
            for name, obj in printed_parts.items()
            if name != structure_report["bosses"][key]["owner"]
        }
        m5_clearance_report[key] = {
            "bolt_body_to_nonplate_metal": collision_summary(
                hardware["bolt_body"], metal_without_plate
            ),
            "bolt_body_to_other_printed_parts": collision_summary(
                hardware["bolt_body"], other_printed
            ),
            "head_and_washer_to_nonplate_metal": collision_summary(
                hardware["head_washer"], metal_without_plate
            ),
            "captive_nut_to_all_metal": collision_summary(
                hardware["captive_nut"], metal_objects
            ),
            "captive_nut_to_other_printed_parts": collision_summary(
                hardware["captive_nut"], other_printed
            ),
            "rear_tool_to_nonplate_metal": collision_summary(
                hardware["rear_tool"], metal_without_plate
            ),
            "premetal_nut_install_tool_to_other_printed_parts": (
                collision_summary(
                    hardware["captive_nut_install_tool"],
                    other_printed,
                )
            ),
            "assembly_sequence": (
                "press captive nyloc before M2 insertion; insert complete "
                "preassembled M2 module; install rear M5 bolt and washer"
            ),
        }
    stage("six M5 hardware/tool clearance audits complete", started_at)

    cap_hardware_clearance = {}
    for side, hardware in cap_hardware.items():
        other_printed = {
            name: obj
            for name, obj in printed_parts.items()
            if name != f"{side}_upper_head"
        }
        cap_hardware_clearance[side] = {
            name: {
                "metal": collision_summary(obj, metal_objects),
                "other_printed": collision_summary(
                    obj, other_printed
                ),
            }
            for name, obj in hardware.items()
            if name.startswith("m3_tool")
        }
    stage("socket-cap M3 tool clearance audits complete", started_at)

    part_stats = {
        name: interface_object_stats(obj)
        for name, obj in printed_parts.items()
    }
    cap_stats = {
        side: interface_object_stats(cap)
        for side, cap in caps.items()
    }
    stage("printed-part topology statistics complete", started_at)
    topology_pass = all(
        stats["connected_components"] == 1
        and stats["boundary_edges"] == 0
        and stats["nonmanifold_edges"] == 0
        for stats in (*part_stats.values(), *cap_stats.values())
    )
    structure_overlap_pass = all(
        value > 0
        for value in structure_report[
            "pre_union_shell_overlap_pairs"
        ].values()
    )
    expected_root_overlap = float(
        config["rear_structure"]["root_overlap_into_shell_mm"]
    )
    expected_cavity_reach = (
        float(config["rear_structure"]["root_penetration_mm"])
        - expected_root_overlap
    )
    root_pass = all(
        value["root_face_area_mm2"]
        >= float(config["validation"]["minimum_root_area_mm2"])
        and abs(
            value["shell_overlap_depth_mm"] - expected_root_overlap
        )
        <= 1e-4
        and abs(
            value["cavity_reach_from_shell_skin_mm"]
            - expected_cavity_reach
        )
        <= 1e-4
        for value in structure_report["roots"].values()
    )
    pad_bearing_pass = all(
        value["washer_bearing_edge_mm"]
        >= float(
            config["validation"][
                "minimum_shell_attachment_pad_bearing_edge_mm"
            ]
        )
        and value["tool_envelope_edge_mm"] >= 0.0
        and value["captive_nut_pocket_min_wall_mm"] >= 2.0
        and value["captive_nut_flat_clearance_each_side_mm"] >= 0.09
        and value["solid_pad_depth_beyond_nut_pocket_mm"] >= 6.0
        for value in structure_report["bosses"].values()
    )
    opposing_clear = all(
        not record["intersects"]
        for record in structure_report[
            "opposing_boss_collisions"
        ].values()
    )
    m5_access_clear = all(
        all(
            value[name]["clear"]
            for name in (
                "bolt_body_to_nonplate_metal",
                "bolt_body_to_other_printed_parts",
                "head_and_washer_to_nonplate_metal",
                "captive_nut_to_all_metal",
                "captive_nut_to_other_printed_parts",
                "rear_tool_to_nonplate_metal",
                "premetal_nut_install_tool_to_other_printed_parts",
            )
        )
        for value in m5_clearance_report.values()
    )
    service_tunnels_preserve_v6_shell = all(
        not sweep["intersects_preexisting_v6_shell"]
        for side in structure_report["crossbolt_service_tunnels"].values()
        for sweep in side["hardware_sweeps"].values()
    )
    seated_metal_clear = all(
        value["clear"] for value in seated_metal_collisions.values()
    )
    cap_seated_clear = all(
        not record["intersects"]
        for value in cap_seated_collisions.values()
        for record in value.values()
    )
    socket_skin_preserved = all(
        not report["wall_cutter_intersects_original_shell_skin"]
        and not report[
            "receiver_relief_intersects_original_shell_skin"
        ]
        and all(
            not pocket["pocket_intersects_original_shell_skin"]
            for pocket in report["insert_pockets"]
        )
        for report in cap_reports.values()
    )
    cap_tool_access_clear = all(
        value["metal"]["clear"]
        and value["other_printed"]["clear"]
        for side in cap_hardware_clearance.values()
        for value in side.values()
    )
    locked_datums_pass = (
        interface["interface_revision"]
        == config["required_interface_revision"]
        and interface["metal_handoff_record"]["revision"]
        == config["required_metal_handoff_revision"]
        and metal_summary["checks"]["accepted_axes_unchanged"]
        and metal_summary["checks"]["accepted_lower_targets_unchanged"]
        and metal_summary["checks"][
            "only_bottom_shell_centers_use_coordinated_v05_positions"
        ]
        and metal_summary["checks"]["locked_socket_opening_remains_21_mm"]
    )

    validation = {
        "shared_v05_m2_interface_contract_passes": (
            interface_report["status"].startswith("PASS")
            and locked_datums_pass
        ),
        "all_six_pad_bosses_meet_washer_bearing_and_contain_14mm_tool": (
            pad_bearing_pass
        ),
        "all_four_structural_roots_are_broad_with_controlled_shell_overlap": (
            root_pass
        ),
        "all_four_rear_structures_true_overlap_their_owner_shells": (
            structure_overlap_pass
        ),
        "opposing_left_right_pad_bosses_are_disjoint": (
            opposing_clear
        ),
        "all_six_m5_fastened_envelopes_and_staged_tools_clear": (
            m5_access_clear
        ),
        "crossbolt_service_tunnels_preserve_preexisting_v6_shell": (
            service_tunnels_preserve_v6_shell
        ),
        "seated_complete_m2_metal_clears_fixed_printed_shells": (
            seated_metal_clear
        ),
        "blind_socket_rigid_pair_is_correctly_rejected": (
            not sweep_report["blind_socket_rigid_pair_pass"]
        ),
        "cap_off_complete_m2_removal_and_reverse_insertion_path_clear": (
            sweep_report["serviceable_socket_path_clear"]
        ),
        "cap_on_rails_and_upper_shells_clear": cap_seated_clear,
        "socket_wall_and_insert_cuts_preserve_original_shell_skin": (
            socket_skin_preserved
        ),
        "all_cap_m3_tool_approaches_clear": cap_tool_access_clear,
        "all_six_shells_and_two_caps_one_closed_manifold_component": (
            topology_pass
        ),
    }
    validation["digital_v7_m2_rear_interface_candidate_pass"] = all(
        validation.values()
    )

    for obj in (*printed_parts.values(), *caps.values()):
        obj.hide_viewport = False
        obj.hide_render = False

    shells_dir = output_dir / "shells"
    for name, obj in printed_parts.items():
        comparison.export_stl(obj, shells_dir / f"{name}.stl")
    caps_dir = output_dir / "socket-caps"
    for side, cap in caps.items():
        comparison.export_stl(
            cap, caps_dir / f"{side}_socket_outer_cap.stl"
        )

    all_review_objects = [
        obj for obj in bpy.data.objects if obj.type == "MESH"
    ]
    camera = bpy.data.objects.get("Bridge_Audit_Camera")
    if camera is None:
        camera = v5.v3.base.audit.configure_workbench_render()
    render_sets = (
        (
            "v7_m2_rear_interface__seated_caps_on",
            [
                *printed_parts.values(),
                *caps.values(),
                *metal_objects.values(),
            ],
        ),
        (
            "v7_m2_rear_interface__structure_only",
            [
                *printed_parts.values(),
                *structure_references.values(),
            ],
        ),
        (
            "v7_m2_rear_interface__hardware_tools",
            [
                *printed_parts.values(),
                *caps.values(),
                *[
                    obj
                    for values in m5_hardware.values()
                    for obj in values.values()
                ],
                *[
                    obj
                    for values in cap_hardware.values()
                    for obj in values.values()
                ],
            ],
        ),
    )
    for render_name, selected in render_sets:
        v5.v3.base.audit.render_part(
            render_name,
            selected,
            all_review_objects,
            output_dir,
            camera,
        )
    stage("review renders complete", started_at)

    for obj in (
        *structure_references.values(),
        *[
            obj
            for values in m5_hardware.values()
            for obj in values.values()
        ],
        *[
            obj
            for values in cap_hardware.values()
            for obj in values.values()
        ],
    ):
        obj.hide_render = True
        obj.hide_viewport = True

    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = (
        output_dir / "gate9-m2-rear-interface-candidate-v7.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "metal_handoff_revision": (
            interface["metal_handoff_record"]["revision"]
        ),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "m2_source_blend": str(m2_blend_path.relative_to(REPO_ROOT)),
        "m2_object_names": sorted(metal_objects),
        "rear_structure": structure_report,
        "socket_caps": cap_reports,
        "rigid_m2_service_path": sweep_report,
        "seated_metal_collisions": seated_metal_collisions,
        "cap_seated_collisions": cap_seated_collisions,
        "m5_hardware_and_tool_clearance": m5_clearance_report,
        "cap_hardware_tool_clearance": cap_hardware_clearance,
        "parts": part_stats,
        "socket_cap_parts": cap_stats,
        "validation": validation,
        "acceptance_holds": config["acceptance_holds"],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "shell_stls": str(shells_dir.relative_to(REPO_ROOT)),
            "socket_cap_stls": str(caps_dir.relative_to(REPO_ROOT)),
            "renders": str(
                (output_dir / "renders").relative_to(REPO_ROOT)
            ),
        },
    }
    report_path = (
        output_dir / "gate9-m2-rear-interface-candidate-v7.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    stage("STLs, blend, and validation report exported", started_at)
    print(
        json.dumps(
            {
                "validation": validation,
                "blind_socket_kinematics": {
                    "lateral_drift_mm": sweep_report[
                        "blind_socket_lateral_drift_over_30mm_mm"
                    ],
                    "available_clearance_mm": sweep_report[
                        "blind_socket_available_lateral_clearance_mm"
                    ],
                    "common_motion_limit_mm": sweep_report[
                        "blind_socket_common_motion_limit_mm"
                    ],
                },
                "service_path_clear": sweep_report[
                    "serviceable_socket_path_clear"
                ],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not validation[
        "digital_v7_m2_rear_interface_candidate_pass"
    ]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
