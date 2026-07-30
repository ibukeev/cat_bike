#!/usr/bin/env python3
"""Generate Gate 9 V8 complementary body seams from the accepted V7 shell."""

from __future__ import annotations

import json
import math
import sys
import time
from itertools import combinations
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

import generate_gate1_master as gate1  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402
import generate_mirror_facet_cap_prototypes as mirror  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-body-seam-clearance-candidate-v8.json"
)
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
SERVICE_PARTS = ("rear_bezel", "bottom_keel")
CAP_PARTS = ("left_socket_cap", "right_socket_cap")
PRODUCTION_PARTS = (*BODY_PARTS, *SERVICE_PARTS, *CAP_PARTS)


def stage(message: str, started_at: float) -> None:
    print(
        f"[gate9-v8 +{time.monotonic() - started_at:8.2f}s] {message}",
        flush=True,
    )


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


def world_points(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def bounds_record(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = world_points(obj)
    return {
        "minimum_head_mm": [
            round(min(point[axis] for point in points), 4)
            for axis in range(3)
        ],
        "maximum_head_mm": [
            round(max(point[axis] for point in points), 4)
            for axis in range(3)
        ],
    }


def topology_record(obj: bpy.types.Object) -> dict[str, float | int]:
    boundary, nonmanifold = gate5.topology_counts(obj)
    return {
        "components": len(gate5.components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "volume_mm3": round(gate5.mesh_volume(obj), 3),
    }


def require_single_manifold(
    obj: bpy.types.Object,
    operation: str,
) -> None:
    gate5.require_manifold(obj, operation)
    count = len(gate5.components(obj))
    if count != 1:
        raise ValueError(
            f"{operation}: {obj.name} has {count} connected components"
        )


def intersection_object(
    first: bpy.types.Object,
    second: bpy.types.Object,
    name: str,
) -> bpy.types.Object:
    result = duplicate_object(first, name)
    tool = duplicate_object(second, f"{name}__tool")
    gate5.apply_boolean(result, tool, "INTERSECT", solver="MANIFOLD")
    return result


def intersection_volume(
    first: bpy.types.Object,
    second: bpy.types.Object,
    name: str,
) -> float:
    result = intersection_object(first, second, name)
    volume = gate5.mesh_volume(result)
    bpy.data.objects.remove(result, do_unlink=True)
    return volume


def expanded_component_hull(
    component: bpy.types.Object,
    name: str,
    clearance_mm: float,
) -> bpy.types.Object:
    points = []
    for vertex in component.data.vertices:
        world = component.matrix_world @ vertex.co
        for offset_x in (-clearance_mm, clearance_mm):
            for offset_y in (-clearance_mm, clearance_mm):
                for offset_z in (-clearance_mm, clearance_mm):
                    points.append(
                        world + Vector((offset_x, offset_y, offset_z))
                    )
    hull = gate5.convex_hull_points(name, points)
    gate5.require_manifold(hull, f"{name} expanded local hull")
    return hull


def selected_landing_bvhs(
    config: dict[str, Any],
) -> dict[str, BVHTree]:
    mirror_config = json.loads(
        (REPO_ROOT / config["mirror_cap_config"]).read_text(
            encoding="utf-8"
        )
    )
    model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    source_bounds = gate1.bounds(model.vertices)
    scale, source_origin, _ = gate1.make_transform(
        source_bounds,
        float(mirror_config["source_head_height_mm"]),
    )
    grouped = mirror.raw_group_faces(model)
    selections = [
        *mirror_config["first_physical_trial"]["selected_facets"],
        *mirror_config["selected_facets"],
    ]
    output: dict[str, BVHTree] = {}
    for selection in selections:
        faces = [
            face
            for group_name in selection["source_face_groups"]
            for face in grouped[group_name]
        ]
        boundary = mirror.boundary_cycle(faces)
        selected_indices = {
            vertex_index
            for face in faces
            for vertex_index in face.indices
        }
        transformed = {
            vertex_index: Vector(
                gate1.transform_point(
                    model.vertices[vertex_index],
                    scale,
                    source_origin,
                )
            )
            for vertex_index in selected_indices
        }
        normal_sum = Vector()
        for face in faces:
            anchor = transformed[face.indices[0]]
            for index in range(1, len(face.indices) - 1):
                first = transformed[face.indices[index]]
                second = transformed[face.indices[index + 1]]
                normal_sum += (first - anchor).cross(second - anchor)
        normal = normal_sum.normalized()
        boundary_points = [transformed[index] for index in boundary]
        longest_edge_index = max(
            range(len(boundary_points)),
            key=lambda index: (
                boundary_points[(index + 1) % len(boundary_points)]
                - boundary_points[index]
            ).length,
        )
        x_axis = (
            boundary_points[
                (longest_edge_index + 1) % len(boundary_points)
            ]
            - boundary_points[longest_edge_index]
        ).normalized()
        y_axis = normal.cross(x_axis).normalized()
        plane_origin = sum(boundary_points, Vector()) / len(boundary_points)
        projected = [
            (
                float((point - plane_origin).dot(x_axis)),
                float((point - plane_origin).dot(y_axis)),
            )
            for point in boundary_points
        ]
        if mirror.signed_area(projected) < 0.0:
            projected.reverse()
        inset = mirror.inset_convex_polygon(
            projected,
            float(mirror_config["perimeter_inset_mm"]),
        )
        cap = mirror.chamfer_polygon(
            inset,
            float(mirror_config["corner_chamfer_mm"]),
        )
        cap_points = [
            plane_origin + x_axis * point[0] + y_axis * point[1]
            for point in cap
        ]
        output[selection["cap_id"]] = BVHTree.FromPolygons(
            cap_points,
            [tuple(range(len(cap_points)))],
            all_triangles=False,
        )
    return output


def landing_hits(
    cutter: bpy.types.Object,
    landings: dict[str, BVHTree],
) -> dict[str, int]:
    cutter_bvh = comparison.object_bvh(cutter)
    output = {}
    for cap_id, landing in landings.items():
        overlaps = cutter_bvh.overlap(landing)
        if overlaps:
            output[cap_id] = len(overlaps)
    return output


def apply_local_relief(
    owner: bpy.types.Object,
    relieved: bpy.types.Object,
    operation_name: str,
    clearance_mm: float,
    zero_tolerance_mm3: float,
    max_sliver_volume_mm3: float,
    landings: dict[str, BVHTree],
) -> dict[str, Any]:
    overlap = intersection_object(
        owner,
        relieved,
        f"gate9_v8__overlap__{operation_name}",
    )
    overlap_volume = gate5.mesh_volume(overlap)
    record: dict[str, Any] = {
        "operation": operation_name,
        "owner": owner.name,
        "relieved_part": relieved.name,
        "clearance_mm": clearance_mm,
        "overlap_before_mm3": round(overlap_volume, 6),
        "cutters": [],
    }
    if overlap_volume <= zero_tolerance_mm3:
        bpy.data.objects.remove(overlap, do_unlink=True)
        record.update(
            {
                "cutter_count": 0,
                "cleanup": {
                    "component_count_before_cleanup": 1,
                    "removed_component_count": 0,
                    "kept_component_volume_mm3": round(
                        gate5.mesh_volume(relieved), 3
                    ),
                    "removed_component_volume_mm3": 0.0,
                },
                "overlap_after_mm3": round(overlap_volume, 6),
                "topology_after": topology_record(relieved),
            }
        )
        return record

    components = gate8.split_closed_components(overlap)
    for component_index, component in enumerate(components):
        component_volume = gate5.mesh_volume(component)
        if component_volume <= zero_tolerance_mm3:
            bpy.data.objects.remove(component, do_unlink=True)
            continue
        cutter = expanded_component_hull(
            component,
            (
                f"gate9_v8__relief__{operation_name}"
                f"__{component_index:03d}"
            ),
            clearance_mm,
        )
        bpy.data.objects.remove(component, do_unlink=True)
        hits = landing_hits(cutter, landings)
        cutter_record = {
            "component_index": component_index,
            "source_overlap_volume_mm3": round(component_volume, 6),
            "bounds": bounds_record(cutter),
            "mirror_landing_triangle_overlap_pairs": hits,
        }
        record["cutters"].append(cutter_record)
        if hits:
            raise ValueError(
                f"{operation_name} relief reaches mirror landing(s): {hits}"
            )
        gate5.apply_boolean(
            relieved,
            cutter,
            "DIFFERENCE",
            solver="MANIFOLD",
        )
        gate5.require_manifold(
            relieved,
            f"{operation_name} localized clearance subtraction",
        )

    cleanup = gate5.keep_largest_component(relieved)
    if (
        float(cleanup["removed_component_volume_mm3"])
        > max_sliver_volume_mm3
    ):
        raise ValueError(
            f"{operation_name} detached "
            f"{cleanup['removed_component_volume_mm3']} mm3, over the "
            f"{max_sliver_volume_mm3} mm3 cleanup limit"
        )
    require_single_manifold(relieved, f"{operation_name} completed relief")
    residual_volume = intersection_volume(
        owner,
        relieved,
        f"gate9_v8__residual__{operation_name}",
    )
    record.update(
        {
            "cutter_count": len(record["cutters"]),
            "cleanup": cleanup,
            "overlap_after_mm3": round(residual_volume, 6),
            "topology_after": topology_record(relieved),
        }
    )
    return record


def pair_matrix(
    parts: dict[str, bpy.types.Object],
) -> dict[str, dict[str, Any]]:
    output = {}
    for first_name, second_name in combinations(parts, 2):
        first = parts[first_name]
        second = parts[second_name]
        collision = comparison.collision_record(first, second)
        volume = intersection_volume(
            first,
            second,
            f"gate9_v8__pair__{first_name}__{second_name}",
        )
        output[f"{first_name}__{second_name}"] = {
            **collision,
            "positive_overlap_volume_mm3": round(volume, 6),
        }
    return output


def object_center(obj: bpy.types.Object) -> Vector:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return sum(points, Vector()) / len(points)


def assembly_path(
    label: str,
    moving_names: tuple[str, ...],
    fixed_names: tuple[str, ...],
    parts: dict[str, bpy.types.Object],
    direction: Vector,
    offsets: list[float],
    zero_tolerance_mm3: float,
) -> dict[str, Any]:
    direction = direction.normalized()
    samples = []
    for offset in offsets:
        moving_objects = []
        for name in moving_names:
            duplicate = duplicate_object(
                parts[name],
                f"gate9_v8__path__{label}__{name}__{offset:g}",
            )
            duplicate.location += direction * offset
            moving_objects.append((name, duplicate))
        bpy.context.view_layer.update()
        collisions = []
        for moving_name, moving in moving_objects:
            for fixed_name in fixed_names:
                record = comparison.collision_record(
                    moving,
                    parts[fixed_name],
                )
                positive_volume = None
                if offset == 0.0 and record["intersects"]:
                    positive_volume = intersection_volume(
                        moving,
                        parts[fixed_name],
                        (
                            f"gate9_v8__path_volume__{label}"
                            f"__{moving_name}__{fixed_name}"
                        ),
                    )
                collisions.append(
                    {
                        "moving": moving_name,
                        "fixed": fixed_name,
                        "triangle_overlap_pair_count": record[
                            "triangle_overlap_pair_count"
                        ],
                        "intersects": record["intersects"],
                        "positive_overlap_volume_mm3": (
                            round(positive_volume, 6)
                            if positive_volume is not None
                            else None
                        ),
                    }
                )
        if offset == 0.0:
            clear = all(
                (
                    not record["intersects"]
                    or (
                        record["positive_overlap_volume_mm3"] is not None
                        and record["positive_overlap_volume_mm3"]
                        <= zero_tolerance_mm3
                    )
                )
                for record in collisions
            )
        else:
            clear = not any(record["intersects"] for record in collisions)
        samples.append(
            {
                "offset_mm": offset,
                "clear": clear,
                "collisions": [
                    record
                    for record in collisions
                    if record["intersects"]
                ],
            }
        )
        for _, moving in moving_objects:
            bpy.data.objects.remove(moving, do_unlink=True)
    return {
        "label": label,
        "direction_head": [
            round(float(value), 6) for value in direction
        ],
        "samples": samples,
        "all_samples_clear": all(sample["clear"] for sample in samples),
    }


def subtractive_only_record(
    current: bpy.types.Object,
    source: bpy.types.Object,
    zero_tolerance_mm3: float,
) -> dict[str, Any]:
    source_volume = gate5.mesh_volume(source)
    current_volume = gate5.mesh_volume(current)
    source_bounds = bounds_record(source)
    current_bounds = bounds_record(current)
    added = duplicate_object(
        current,
        f"gate9_v8__subtractive_audit__{current.name}",
    )
    source_tool = duplicate_object(
        source,
        f"gate9_v8__subtractive_source__{current.name}",
    )
    gate5.apply_boolean(
        added,
        source_tool,
        "DIFFERENCE",
        solver="MANIFOLD",
    )
    added_volume = gate5.mesh_volume(added)
    bpy.data.objects.remove(added, do_unlink=True)
    bounds_tolerance_mm = 0.001
    bounds_inside = all(
        current_bounds["minimum_head_mm"][axis]
        >= source_bounds["minimum_head_mm"][axis] - bounds_tolerance_mm
        and current_bounds["maximum_head_mm"][axis]
        <= source_bounds["maximum_head_mm"][axis] + bounds_tolerance_mm
        for axis in range(3)
    )
    return {
        "construction_history": (
            "V8 starts from a direct V7 mesh copy and permits only Boolean "
            "DIFFERENCE plus removal of reported detached slivers"
        ),
        "source_v7_volume_mm3": round(source_volume, 3),
        "v8_volume_mm3": round(current_volume, 3),
        "removed_volume_mm3": round(source_volume - current_volume, 3),
        "source_v7_bounds": source_bounds,
        "v8_bounds": current_bounds,
        "bounds_tolerance_mm": bounds_tolerance_mm,
        "bounds_inside_v7_extents": bounds_inside,
        "coplanar_boolean_residual_diagnostic_mm3": round(added_volume, 6),
        "coplanar_boolean_residual_is_acceptance_authority": False,
        "subtractive_only": (
            current_volume <= source_volume + zero_tolerance_mm3
            and bounds_inside
        ),
    }


def main() -> None:
    started_at = time.monotonic()
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = (REPO_ROOT / config["source_v7_blend"]).resolve()
    if not source_blend.exists():
        raise FileNotFoundError(
            f"Missing V7 source blend: {source_blend}"
        )
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    stage("V7 source review model loaded", started_at)

    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    if interface["interface_revision"] != config[
        "required_interface_revision"
    ]:
        raise ValueError("V8 loaded the wrong shell/aluminum interface revision")
    if interface["metal_handoff_record"]["revision"] != config[
        "required_metal_handoff_revision"
    ]:
        raise ValueError("V8 loaded the wrong M2 metal handoff")
    v7_validation = json.loads(
        (REPO_ROOT / config["source_v7_validation"]).read_text(
            encoding="utf-8"
        )
    )
    if not all(v7_validation["geometry_validation"].values()):
        raise ValueError("V7 rear correction validation is not fully passing")

    source_parts = {
        name: bpy.data.objects[source_name]
        for name, source_name in config["source_objects"].items()
    }
    parts = {
        name: duplicate_object(source, f"gate9_v8__{name}")
        for name, source in source_parts.items()
    }
    landings = selected_landing_bvhs(config)
    values = config["seam_relief"]
    clearance = float(values["clearance_mm"])
    zero_tolerance = float(values["zero_volume_tolerance_mm3"])
    max_sliver = float(
        values["maximum_single_operation_detached_sliver_volume_mm3"]
    )

    seam_records = []
    for operation in values["ownership_operations"]:
        seam_records.append(
            apply_local_relief(
                parts[operation["owner"]],
                parts[operation["relieved_part"]],
                operation["seam"],
                clearance,
                zero_tolerance,
                max_sliver,
                landings,
            )
        )
    stage("eight seated seam ownership reliefs complete", started_at)

    rear_normal = Vector(
        interface["rear_interface_plane"]["outward_normal_head"]
    ).normalized()
    service_values = config["rear_bezel_service_path"]
    service_cut_records = []
    for offset in service_values["relief_sample_offsets_mm"]:
        moving_bezel = duplicate_object(
            parts["rear_bezel"],
            f"gate9_v8__bezel_service_owner__{offset:g}",
        )
        moving_bezel.location += rear_normal * float(offset)
        bpy.context.view_layer.update()
        for body_name in BODY_PARTS:
            service_cut_records.append(
                {
                    "offset_mm": float(offset),
                    **apply_local_relief(
                        moving_bezel,
                        parts[body_name],
                        f"bezel_service_{offset:g}__{body_name}",
                        clearance,
                        zero_tolerance,
                        max_sliver,
                        landings,
                    ),
                }
            )
        bpy.data.objects.remove(moving_bezel, do_unlink=True)
    stage("rear-bezel service sweep relief complete", started_at)

    topology = {
        name: topology_record(obj) for name, obj in parts.items()
    }
    seated_matrix = pair_matrix(parts)
    stage("complete seated topology and pair matrix complete", started_at)

    same_side_offsets = [
        float(value)
        for value in config["assembly_paths"][
            "same_side_lower_from_upper_offsets_mm"
        ]
    ]
    module_offsets = [
        float(value)
        for value in config["assembly_paths"][
            "right_module_from_left_module_offsets_mm"
        ]
    ]
    keel_offsets = [
        float(value)
        for value in config["assembly_paths"][
            "bottom_keel_downward_offsets_mm"
        ]
    ]
    assembly_paths = {
        "left_lower_from_upper": assembly_path(
            "left_lower_from_upper",
            ("left_lower_face",),
            ("left_upper_head",),
            parts,
            (
                object_center(parts["left_lower_face"])
                - object_center(parts["left_upper_head"])
            ),
            same_side_offsets,
            zero_tolerance,
        ),
        "right_lower_from_upper": assembly_path(
            "right_lower_from_upper",
            ("right_lower_face",),
            ("right_upper_head",),
            parts,
            (
                object_center(parts["right_lower_face"])
                - object_center(parts["right_upper_head"])
            ),
            same_side_offsets,
            zero_tolerance,
        ),
        "right_module_from_left_module": assembly_path(
            "right_module_from_left_module",
            ("right_upper_head", "right_lower_face"),
            ("left_upper_head", "left_lower_face"),
            parts,
            Vector((1.0, 0.0, 0.0)),
            module_offsets,
            zero_tolerance,
        ),
        "rear_bezel_outward": assembly_path(
            "rear_bezel_outward",
            ("rear_bezel",),
            BODY_PARTS,
            parts,
            rear_normal,
            [
                float(value)
                for value in service_values["validation_offsets_mm"]
            ],
            zero_tolerance,
        ),
        "bottom_keel_downward": assembly_path(
            "bottom_keel_downward",
            ("bottom_keel",),
            (*BODY_PARTS, "rear_bezel"),
            parts,
            Vector((0.0, 0.0, -1.0)),
            keel_offsets,
            zero_tolerance,
        ),
    }
    stage("five complete assembly-path sweeps complete", started_at)

    subtractive_only = {
        name: subtractive_only_record(
            parts[name],
            source_parts[name],
            zero_tolerance,
        )
        for name in BODY_PARTS
    }
    all_cutters = [
        cutter
        for record in (*seam_records, *service_cut_records)
        for cutter in record["cutters"]
    ]
    mirror_landing_overlap_pairs = sum(
        sum(cutter["mirror_landing_triangle_overlap_pairs"].values())
        for cutter in all_cutters
    )

    required = config["validation"]
    topology_pass = all(
        record["components"] == required["required_component_count"]
        and record["boundary_edges"] == required["required_boundary_edges"]
        and record["nonmanifold_edges"]
        == required["required_nonmanifold_edges"]
        for record in topology.values()
    )
    seated_volume_pass = all(
        record["positive_overlap_volume_mm3"] <= zero_tolerance
        for record in seated_matrix.values()
    )
    seam_relief_pass = all(
        record["overlap_after_mm3"] <= zero_tolerance
        for record in seam_records
    )
    service_relief_pass = all(
        record["overlap_after_mm3"] <= zero_tolerance
        for record in service_cut_records
    )
    validation = {
        "v05_m2_interface_datums_unchanged": (
            interface["interface_revision"]
            == config["required_interface_revision"]
            and interface["metal_handoff_record"]["revision"]
            == config["required_metal_handoff_revision"]
        ),
        "all_eight_seated_ownership_overlaps_removed": seam_relief_pass,
        "complete_rear_bezel_service_sweep_relief_removed": (
            service_relief_pass
        ),
        "all_eight_printed_parts_single_closed_manifold": topology_pass,
        "all_twenty_eight_seated_part_pairs_have_zero_positive_volume": (
            seated_volume_pass
        ),
        "all_five_sampled_assembly_paths_clear": all(
            record["all_samples_clear"]
            for record in assembly_paths.values()
        ),
        "all_body_changes_are_subtractive_only": all(
            record["subtractive_only"]
            for record in subtractive_only.values()
        ),
        "all_selected_mirror_panel_landings_untouched": (
            mirror_landing_overlap_pairs
            == required["mirror_landing_cutter_overlap_pairs"]
        ),
    }
    validation["digital_v8_body_seam_candidate_pass"] = all(
        validation.values()
    )

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_dir = output_dir / "parts"
    for name, obj in parts.items():
        comparison.export_stl(obj, stl_dir / f"{name}.stl")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            visible = obj in parts.values()
            obj.hide_viewport = not visible
            obj.hide_render = not visible
    blend_path = output_dir / "gate9-body-seam-clearance-candidate-v8.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "schema_version": 8,
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "metal_handoff_revision": interface["metal_handoff_record"][
            "revision"
        ],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "source_v7_blend": config["source_v7_blend"],
        "seam_ownership_and_relief": seam_records,
        "rear_bezel_service_sweep_relief": service_cut_records,
        "topology": topology,
        "seated_pair_matrix": seated_matrix,
        "assembly_paths": assembly_paths,
        "subtractive_exterior_preservation": subtractive_only,
        "mirror_panel_landing_validation": {
            "selected_cap_ids": sorted(landings),
            "relief_cutter_count": len(all_cutters),
            "triangle_overlap_pair_count": mirror_landing_overlap_pairs,
            "perimeter_inset_mm": 0.9,
            "corner_chamfer_mm": 0.8,
        },
        "digital_validation": validation,
        "acceptance_holds": config["acceptance_holds"],
        "remaining_production_blockers": [
            "physical full-shell V8 fit and flange-meeting validation",
            "final seam fastener or internal bridge-plate retention",
            "ear connector and ear-to-head physical validation",
            "eye frame and eye socket integration",
            "glow-panel insert and landing integration",
            "lamp and steering portal revision for the accepted head angle",
            "support/brim-inclusive Prusa MK4 Generic ASA slice",
            "complete final ASA print authorization",
        ],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "stls": str(stl_dir.relative_to(REPO_ROOT)),
        },
    }
    report_path = output_dir / "gate9-body-seam-clearance-v8.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    review_path = (REPO_ROOT / config["review_summary_path"]).resolve()
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    stage("V8 blend, STLs, and review summary exported", started_at)
    print(
        json.dumps(
            {
                "validation": validation,
                "report": str(review_path.relative_to(REPO_ROOT)),
                "blend": str(blend_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not validation["digital_v8_body_seam_candidate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
