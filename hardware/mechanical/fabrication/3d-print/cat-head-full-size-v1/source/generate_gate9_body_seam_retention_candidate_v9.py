#!/usr/bin/env python3
"""Generate Gate 9 V9 removable body-seam retention from accepted V8 shells."""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_body_seam_clearance_candidate_v8 as v8  # noqa: E402
import generate_gate9_m2_rear_interface_candidate_v7 as v7  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-body-seam-retention-candidate-v9.json"
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
        f"[gate9-v9 +{time.monotonic() - started_at:8.2f}s] {message}",
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


def intersection_volume(
    first: bpy.types.Object,
    second: bpy.types.Object,
    name: str,
) -> float:
    result = duplicate_object(first, name)
    tool = duplicate_object(second, f"{name}__tool")
    gate5.apply_boolean(result, tool, "INTERSECT", solver="MANIFOLD")
    volume = gate5.mesh_volume(result)
    bpy.data.objects.remove(result, do_unlink=True)
    return volume


def annular_ring(
    name: str,
    first: Vector,
    second: Vector,
    outer_diameter: float,
    inner_diameter: float,
) -> bpy.types.Object:
    ring = gate5.cylinder(
        name,
        first,
        second,
        outer_diameter,
        vertices=32,
    )
    direction = (second - first).normalized()
    bore = gate5.cylinder(
        f"{name}__bore",
        first - direction,
        second + direction,
        inner_diameter,
        vertices=24,
    )
    gate5.apply_boolean(ring, bore, "DIFFERENCE", solver="MANIFOLD")
    gate5.require_manifold(ring, f"{name} annular ring")
    return ring


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


def bounds_record(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [
        obj.matrix_world @ vertex.co for vertex in obj.data.vertices
    ]
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


def reconstructed_body_modules(
    gate8_config: dict[str, Any],
) -> tuple[
    Any,
    list[Vector],
    list[dict[str, Any]],
]:
    model, assignments, scale, origin = gate5.transformed_source()
    points, segments = gate5.seam_segments(
        model,
        assignments,
        scale,
        origin,
    )
    minimum = float(
        gate8_config["joint_system"]["minimum_usable_seam_edge_mm"]
    )
    excluded = {
        tuple(value)
        for value in gate8_config.get("excluded_joint_face_pairs", [])
    }
    usable = [
        segment
        for segment in segments
        if segment["length_mm"] >= minimum
        and tuple(segment["face_groups"]) not in excluded
    ]
    allocations = gate5.distribute_modules(
        usable,
        float(
            gate8_config["joint_system"]["module_max_spacing_mm"]
        ),
        int(
            gate8_config["joint_system"].get(
                "ear_minimum_module_count",
                1,
            )
        ),
    )
    allocations = [
        item
        for item in allocations
        if set(item[0]["sections"]).issubset(BODY_PARTS)
    ]
    counts: defaultdict[str, int] = defaultdict(int)
    records = []
    for segment, fraction, allocation_count in allocations:
        pair = "__".join(segment["sections"])
        counts[pair] += 1
        records.append(
            {
                "name": f"{pair}_{counts[pair]:02d}",
                "segment": segment,
                "fraction": fraction,
                "allocation_count": allocation_count,
            }
        )
    return model, points, records


def body_pair_matrix(
    parts: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    output = {}
    for first_name, second_name in combinations(BODY_PARTS, 2):
        collision = comparison.collision_record(
            parts[first_name],
            parts[second_name],
        )
        volume = intersection_volume(
            parts[first_name],
            parts[second_name],
            f"gate9_v9__body_pair__{first_name}__{second_name}",
        )
        output[f"{first_name}__{second_name}"] = {
            **collision,
            "positive_overlap_volume_mm3": round(volume, 6),
        }
    return output


def object_pair_matrix(
    first_objects: dict[str, bpy.types.Object],
    second_objects: dict[str, bpy.types.Object],
    prefix: str,
) -> dict[str, Any]:
    output = {}
    for first_name, first in first_objects.items():
        for second_name, second in second_objects.items():
            collision = comparison.collision_record(first, second)
            volume = intersection_volume(
                first,
                second,
                f"{prefix}__{first_name}__{second_name}",
            )
            output[f"{first_name}__{second_name}"] = {
                **collision,
                "positive_overlap_volume_mm3": round(volume, 6),
            }
    return output


def bridge_pair_matrix(
    bridges: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    output = {}
    for first_name, second_name in combinations(bridges, 2):
        collision = comparison.collision_record(
            bridges[first_name],
            bridges[second_name],
        )
        volume = intersection_volume(
            bridges[first_name],
            bridges[second_name],
            f"gate9_v9__bridge_pair__{first_name}__{second_name}",
        )
        output[f"{first_name}__{second_name}"] = {
            **collision,
            "positive_overlap_volume_mm3": round(volume, 6),
        }
    return output


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path),
        export_selected_objects=True,
    )
    obj.select_set(False)


def main() -> None:
    started_at = time.monotonic()
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    if interface["interface_revision"] != config[
        "required_interface_revision"
    ]:
        raise ValueError("V9 loaded the wrong shell/aluminum interface")
    if interface["metal_handoff_record"]["revision"] != config[
        "required_metal_handoff_revision"
    ]:
        raise ValueError("V9 loaded the wrong metal handoff")
    v8_summary = json.loads(
        (REPO_ROOT / config["source_v8_validation"]).read_text(
            encoding="utf-8"
        )
    )
    if not all(v8_summary["digital_validation"].values()):
        raise ValueError("V8 source validation is not fully passing")
    gate8_config = json.loads(
        (REPO_ROOT / config["source_gate8_config"]).read_text(
            encoding="utf-8"
        )
    )
    source_blend = (REPO_ROOT / config["source_v8_blend"]).resolve()
    if not source_blend.exists():
        raise FileNotFoundError(source_blend)
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    stage("accepted V8 source loaded", started_at)

    source_parts = {
        name: bpy.data.objects[source_name]
        for name, source_name in config["source_objects"].items()
    }
    parts = {
        name: duplicate_object(source, f"gate9_v9__{name}")
        for name, source in source_parts.items()
    }
    metal_objects = {
        obj.name: obj
        for obj in bpy.data.objects
        if obj.name.startswith("metal_v05__")
    }
    if "metal_v05__backplate" not in metal_objects:
        raise ValueError("V9 source blend is missing complete M2 metal")

    values = config["retention_system"]
    validation_values = config["validation"]
    selected_names = set(values["selected_source_modules"])
    zero_tolerance = float(
        validation_values["zero_volume_tolerance_mm3"]
    )
    model, points, module_inputs = reconstructed_body_modules(
        gate8_config
    )
    input_names = {record["name"] for record in module_inputs}
    if selected_names - input_names:
        raise ValueError(
            "Unknown selected retention modules: "
            f"{sorted(selected_names - input_names)}"
        )

    materials = {
        "pad": comparison.create_material(
            "gate9_v9_insert_pad",
            "#D98235",
        ),
        "bridge": comparison.create_material(
            "gate9_v9_bridge",
            "#E9B83B",
        ),
        "tool": comparison.create_material(
            "gate9_v9_tool",
            "#D74842",
            alpha=0.25,
        ),
    }
    landings = v8.selected_landing_bvhs(config)
    wall = float(gate8_config["shell_wall_thickness_mm"])
    pad_outer_depth = wall - float(values["pad_shell_overlap_mm"])
    if (
        abs(
            pad_outer_depth
            - float(values["minimum_analytic_pad_exterior_recess_mm"])
        )
        > 1e-6
    ):
        raise ValueError("Configured pad exterior recess is inconsistent")

    bridges: dict[str, bpy.types.Object] = {}
    tool_envelopes: dict[str, bpy.types.Object] = {}
    tool_owner_bridges: dict[str, str] = {}
    selected_records = []
    rejected_records = []
    module_directions: dict[str, Vector] = {}
    pad_landing_overlap_pairs = 0

    for module_input in module_inputs:
        name = module_input["name"]
        segment = module_input["segment"]
        fraction = float(module_input["fraction"])
        p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
        tangent = (p1 - p0).normalized()
        seam_point = p0.lerp(p1, fraction)
        side_data = {}
        pad_candidates = {}
        for section in segment["sections"]:
            geometry = gate5.side_geometry(
                name,
                segment,
                section,
                seam_point,
                tangent,
                model,
                points,
            )
            surface_center = (
                seam_point
                + geometry["toward_face"]
                * (
                    float(values["pad_seam_setback_mm"])
                    + float(values["pad_diameter_mm"]) / 2.0
                )
            )
            pad = gate5.cylinder(
                f"gate9_v9__pad__{name}__{section}",
                surface_center
                - geometry["normal"] * pad_outer_depth,
                surface_center
                - geometry["normal"]
                * (
                    pad_outer_depth
                    + float(values["pad_depth_mm"])
                ),
                float(values["pad_diameter_mm"]),
                materials["pad"],
                vertices=32,
            )
            root_volume = intersection_volume(
                pad,
                parts[section],
                f"gate9_v9__root_check__{name}__{section}",
            )
            pad_candidates[section] = pad
            side_data[section] = {
                "normal": geometry["normal"],
                "toward_face": geometry["toward_face"],
                "surface_center": surface_center,
                "root_intersection_mm3": root_volume,
                "face_depth_mm": geometry["face_depth_mm"],
            }

        if name not in selected_names:
            for pad in pad_candidates.values():
                bpy.data.objects.remove(pad, do_unlink=True)
            rejected_records.append(
                {
                    "module": name,
                    "source_face_groups": segment["face_groups"],
                    "reason": "not selected: no broad root on both final V8 shells",
                    "root_intersection_mm3": {
                        section: round(
                            record["root_intersection_mm3"],
                            3,
                        )
                        for section, record in side_data.items()
                    },
                }
            )
            continue

        minimum_root = float(values["minimum_root_intersection_mm3"])
        if any(
            record["root_intersection_mm3"] < minimum_root
            for record in side_data.values()
        ):
            raise ValueError(
                f"{name}: selected module lacks a broad V8 shell root"
            )

        contacts = []
        screws = []
        module_pad_records = []
        for section in segment["sections"]:
            record = side_data[section]
            normal = record["normal"]
            pad = pad_candidates[section]
            pad_hits = v8.landing_hits(pad, landings)
            pad_landing_overlap_pairs += sum(pad_hits.values())
            gate5.apply_boolean(
                parts[section],
                pad,
                "UNION",
                solver="MANIFOLD",
            )
            require_single_manifold(
                parts[section],
                f"{name} {section} pad union",
            )
            seat = (
                record["surface_center"]
                - normal
                * (
                    pad_outer_depth
                    + float(values["pad_depth_mm"])
                )
            )
            pilot = gate5.cylinder(
                f"gate9_v9__insert_pilot__{name}__{section}",
                seat - normal * 0.8,
                seat
                + normal * float(values["insert_pilot_depth_mm"]),
                float(values["insert_pilot_diameter_mm"]),
                vertices=24,
            )
            gate5.apply_boolean(
                parts[section],
                pilot,
                "DIFFERENCE",
                solver="MANIFOLD",
            )
            require_single_manifold(
                parts[section],
                f"{name} {section} insert pilot",
            )
            pilot_probe = gate5.cylinder(
                f"gate9_v9__pilot_probe__{name}__{section}",
                seat - normal * 0.3,
                seat
                + normal
                * (float(values["insert_pilot_depth_mm"]) - 0.2),
                float(values["insert_pilot_diameter_mm"]) - 0.1,
                vertices=24,
            )
            pilot_residual = intersection_volume(
                pilot_probe,
                parts[section],
                f"gate9_v9__pilot_residual__{name}__{section}",
            )
            bpy.data.objects.remove(pilot_probe, do_unlink=True)
            bearing = annular_ring(
                f"gate9_v9__insert_bearing__{name}__{section}",
                seat + normal * 0.3,
                seat + normal * 1.3,
                float(values["pad_diameter_mm"]) - 2.0,
                float(values["insert_pilot_diameter_mm"]) + 0.2,
            )
            bearing_volume = gate5.mesh_volume(bearing)
            bearing_support = intersection_volume(
                bearing,
                parts[section],
                f"gate9_v9__insert_bearing_support__{name}__{section}",
            )
            bpy.data.objects.remove(bearing, do_unlink=True)

            contact_center = (
                seat
                - normal
                * (
                    float(values["bridge_contact_face_clearance_mm"])
                    + float(values["bridge_end_thickness_mm"]) / 2.0
                )
            )
            deep_center = (
                seat
                - normal
                * (
                    float(values["bridge_contact_face_clearance_mm"])
                    + float(values["bridge_end_thickness_mm"])
                    + float(values["bridge_spine_inward_arch_mm"])
                )
            )
            contact = gate5.cylinder(
                f"gate9_v9__bridge_end__{name}__{section}",
                seat
                - normal
                * float(values["bridge_contact_face_clearance_mm"]),
                seat
                - normal
                * (
                    float(values["bridge_contact_face_clearance_mm"])
                    + float(values["bridge_end_thickness_mm"])
                ),
                float(values["bridge_end_diameter_mm"]),
                materials["bridge"],
                vertices=32,
            )
            contacts.append(contact)
            screws.append(
                {
                    "section": section,
                    "seat": seat,
                    "normal": normal,
                    "contact_center": contact_center,
                    "deep_center": deep_center,
                }
            )
            module_pad_records.append(
                {
                    "section": section,
                    "source_face_group": (
                        segment["face_groups"][
                            segment["sections"].index(section)
                        ]
                    ),
                    "pad_center_head_mm": [
                        round(float(value), 4)
                        for value in record["surface_center"]
                    ],
                    "pad_axis_outward_head": [
                        round(float(value), 6) for value in normal
                    ],
                    "root_intersection_mm3": round(
                        record["root_intersection_mm3"],
                        3,
                    ),
                    "pilot_residual_mm3": round(pilot_residual, 6),
                    "insert_bearing_support_ratio": round(
                        bearing_support / bearing_volume,
                        5,
                    ),
                }
            )

        link_direction = (
            screws[1]["deep_center"] - screws[0]["deep_center"]
        ).normalized()
        link = gate5.cylinder(
            f"gate9_v9__bridge_spine__{name}",
            screws[0]["deep_center"]
            - link_direction
            * float(values["bridge_spine_end_overlap_mm"]),
            screws[1]["deep_center"]
            + link_direction
            * float(values["bridge_spine_end_overlap_mm"]),
            float(values["bridge_spine_diameter_mm"]),
            materials["bridge"],
            vertices=32,
        )
        legs = [
            gate5.cylinder(
                f"gate9_v9__bridge_leg__{name}__{screw['section']}",
                screw["contact_center"],
                screw["deep_center"],
                float(values["bridge_spine_diameter_mm"]),
                materials["bridge"],
                vertices=32,
            )
            for screw in screws
        ]
        bridge_name = f"body_seam_bridge__{name}"
        bridge = contacts[0]
        bridge.name = bridge_name
        for component in (contacts[1], *legs, link):
            gate5.apply_boolean(
                bridge,
                component,
                "UNION",
                solver="MANIFOLD",
            )
        require_single_manifold(bridge, f"{name} arched bridge union")

        bridge_bearings = []
        for screw in screws:
            normal = screw["normal"]
            seat = screw["seat"]
            clearance = gate5.cylinder(
                f"gate9_v9__bridge_clearance__{name}"
                f"__{screw['section']}",
                seat + normal * 3.0,
                seat
                - normal
                * (
                    float(values["bridge_contact_face_clearance_mm"])
                    + float(values["bridge_end_thickness_mm"])
                    + float(values["bridge_spine_inward_arch_mm"])
                    + 4.0
                ),
                float(values["bridge_clearance_diameter_mm"]),
                vertices=24,
            )
            gate5.apply_boolean(
                bridge,
                clearance,
                "DIFFERENCE",
                solver="MANIFOLD",
            )
            require_single_manifold(
                bridge,
                f"{name} {screw['section']} bridge clearance",
            )
            bridge_ring = annular_ring(
                f"gate9_v9__bridge_bearing__{name}"
                f"__{screw['section']}",
                screw["contact_center"] + normal * 0.5,
                screw["contact_center"] - normal * 0.5,
                float(values["bridge_end_diameter_mm"]) - 0.4,
                float(values["bridge_clearance_diameter_mm"]) + 0.2,
            )
            ring_volume = gate5.mesh_volume(bridge_ring)
            ring_support = intersection_volume(
                bridge_ring,
                bridge,
                f"gate9_v9__bridge_bearing_support__{name}"
                f"__{screw['section']}",
            )
            bpy.data.objects.remove(bridge_ring, do_unlink=True)
            bridge_bearings.append(
                {
                    "section": screw["section"],
                    "support_ratio": round(
                        ring_support / ring_volume,
                        5,
                    ),
                }
            )

            tool_start = (
                seat
                - normal
                * (
                    float(values["bridge_contact_face_clearance_mm"])
                    + float(values["bridge_end_thickness_mm"])
                    + 0.2
                )
            )
            tool = gate5.cylinder(
                f"tool__{name}__{screw['section']}",
                tool_start,
                tool_start
                - normal * float(values["tool_envelope_length_mm"]),
                float(values["tool_envelope_diameter_mm"]),
                materials["tool"],
                vertices=24,
            )
            tool_envelopes[tool.name] = tool
            tool_owner_bridges[tool.name] = bridge_name

        require_single_manifold(bridge, f"{name} final bridge")
        bridges[bridge_name] = bridge
        module_inward = (
            -screws[0]["normal"] - screws[1]["normal"]
        ).normalized()
        module_directions[bridge_name] = module_inward
        selected_records.append(
            {
                "module": name,
                "bridge": bridge_name,
                "sections": segment["sections"],
                "source_face_groups": segment["face_groups"],
                "seam_point_head_mm": [
                    round(float(value), 4) for value in seam_point
                ],
                "analytic_pad_exterior_recess_mm": round(
                    pad_outer_depth,
                    3,
                ),
                "pads": module_pad_records,
                "bridge_bearing": bridge_bearings,
                "bridge_topology_before_local_relief": topology_record(
                    bridge
                ),
                "bridge_inward_approach_direction_head": [
                    round(float(value), 6)
                    for value in module_inward
                ],
            }
        )
    stage("five broad insert-pad and bridge modules built", started_at)

    if len(bridges) != int(values["selected_module_count"]):
        raise ValueError("V9 did not build the configured five bridges")

    body_pair_before_relief = body_pair_matrix(parts)
    pre_relief_bridge_body = object_pair_matrix(
        bridges,
        {name: parts[name] for name in BODY_PARTS},
        "gate9_v9__bridge_body_pre_relief",
    )
    local_relief_records = []
    allowlist = {
        bridge: set(sections)
        for bridge, sections in values[
            "local_relief_allowlist"
        ].items()
    }
    for pair_name, collision in pre_relief_bridge_body.items():
        bridge_name, section = pair_name.rsplit("__", 1)
        overlap = float(collision["positive_overlap_volume_mm3"])
        if overlap <= zero_tolerance:
            continue
        if (
            bridge_name not in allowlist
            or section not in allowlist[bridge_name]
        ):
            raise ValueError(
                f"Unapproved bridge/body overlap: {pair_name}={overlap}"
            )
        if overlap > float(
            values["maximum_allowed_pre_relief_bridge_overlap_mm3"]
        ):
            raise ValueError(
                f"{pair_name} overlap {overlap} exceeds relief limit"
            )
        local_relief_records.append(
            {
                "bridge": bridge_name,
                "section": section,
                **v8.apply_local_relief(
                    bridges[bridge_name],
                    parts[section],
                    f"{bridge_name}__{section}",
                    float(values["local_bridge_clearance_mm"]),
                    zero_tolerance,
                    float(
                        validation_values[
                            "maximum_relief_detached_sliver_volume_mm3"
                        ]
                    ),
                    landings,
                ),
            }
        )
    if {
        (record["bridge"], record["section"])
        for record in local_relief_records
    } != {
        (bridge_name, section)
        for bridge_name, sections in allowlist.items()
        for section in sections
    }:
        raise ValueError("V9 did not use exactly the approved local reliefs")
    stage("allowlisted lower-center local relief complete", started_at)

    bridge_body_matrix = object_pair_matrix(
        bridges,
        {name: parts[name] for name in PRODUCTION_PARTS},
        "gate9_v9__bridge_body_final",
    )
    bridge_bridge_matrix = bridge_pair_matrix(bridges)
    seated_pair_matrix = v8.pair_matrix(parts)
    body_pair_after_relief = body_pair_matrix(parts)
    topology = {
        name: topology_record(obj) for name, obj in parts.items()
    }
    bridge_topology = {
        name: topology_record(obj) for name, obj in bridges.items()
    }
    stage("final seated collision and topology matrices complete", started_at)

    assembly_values = config["assembly_paths"]
    assembly_paths = {
        "left_lower_from_upper": v8.assembly_path(
            "v9_left_lower_from_upper",
            ("left_lower_face",),
            ("left_upper_head",),
            parts,
            (
                v8.object_center(parts["left_lower_face"])
                - v8.object_center(parts["left_upper_head"])
            ),
            [
                float(value)
                for value in assembly_values[
                    "same_side_lower_from_upper_offsets_mm"
                ]
            ],
            zero_tolerance,
        ),
        "right_lower_from_upper": v8.assembly_path(
            "v9_right_lower_from_upper",
            ("right_lower_face",),
            ("right_upper_head",),
            parts,
            (
                v8.object_center(parts["right_lower_face"])
                - v8.object_center(parts["right_upper_head"])
            ),
            [
                float(value)
                for value in assembly_values[
                    "same_side_lower_from_upper_offsets_mm"
                ]
            ],
            zero_tolerance,
        ),
        "right_module_from_left_module": v8.assembly_path(
            "v9_right_module_from_left_module",
            ("right_upper_head", "right_lower_face"),
            ("left_upper_head", "left_lower_face"),
            parts,
            Vector((1.0, 0.0, 0.0)),
            [
                float(value)
                for value in assembly_values[
                    "right_module_from_left_module_offsets_mm"
                ]
            ],
            zero_tolerance,
        ),
        "rear_bezel_outward": v8.assembly_path(
            "v9_rear_bezel_outward",
            ("rear_bezel",),
            BODY_PARTS,
            parts,
            Vector(
                interface["rear_interface_plane"][
                    "outward_normal_head"
                ]
            ),
            [
                float(value)
                for value in assembly_values[
                    "rear_bezel_outward_offsets_mm"
                ]
            ],
            zero_tolerance,
        ),
        "bottom_keel_downward": v8.assembly_path(
            "v9_bottom_keel_downward",
            ("bottom_keel",),
            (*BODY_PARTS, "rear_bezel"),
            parts,
            Vector((0.0, 0.0, -1.0)),
            [
                float(value)
                for value in assembly_values[
                    "bottom_keel_downward_offsets_mm"
                ]
            ],
            zero_tolerance,
        ),
    }

    combined_parts = {**parts, **bridges}
    bridge_paths = {}
    fixed_for_bridge = PRODUCTION_PARTS
    for bridge_name in bridges:
        bridge_paths[bridge_name] = v8.assembly_path(
            f"v9_{bridge_name}_inward_approach",
            (bridge_name,),
            fixed_for_bridge,
            combined_parts,
            module_directions[bridge_name],
            [
                float(value)
                for value in assembly_values[
                    "bridge_inward_approach_offsets_mm"
                ]
            ],
            zero_tolerance,
        )
    stage("body and five bridge assembly paths complete", started_at)

    tool_body_collisions = {
        name: v7.collision_summary(
            tool,
            {
                part_name: obj
                for part_name, obj in {
                    **parts,
                    **bridges,
                }.items()
                if part_name not in name
                and part_name != tool_owner_bridges[name]
            },
        )
        for name, tool in tool_envelopes.items()
    }
    source_metal_collisions = {
        name: v7.collision_summary(source_parts[name], metal_objects)
        for name in PRODUCTION_PARTS
    }
    v9_metal_collisions = {
        name: v7.collision_summary(parts[name], metal_objects)
        for name in PRODUCTION_PARTS
    }
    bridge_metal_collisions = {
        name: v7.collision_summary(bridge, metal_objects)
        for name, bridge in bridges.items()
    }
    tool_metal_collisions = {
        name: v7.collision_summary(tool, metal_objects)
        for name, tool in tool_envelopes.items()
    }
    stage("driver and complete M2 metal collision audits complete", started_at)

    exterior_preservation = {}
    bounds_tolerance = 0.001
    for name in BODY_PARTS:
        source_bounds = bounds_record(source_parts[name])
        current_bounds = bounds_record(parts[name])
        exterior_preservation[name] = {
            "construction": (
                "only 12 mm cylindrical pads whose outer faces are "
                "analytically recessed 0.5 mm behind their source facet, "
                "blind pilot subtraction, and allowlisted internal relief"
            ),
            "source_v8_bounds": source_bounds,
            "v9_bounds": current_bounds,
            "bounds_inside_v8_extents": all(
                current_bounds["minimum_head_mm"][axis]
                >= source_bounds["minimum_head_mm"][axis]
                - bounds_tolerance
                and current_bounds["maximum_head_mm"][axis]
                <= source_bounds["maximum_head_mm"][axis]
                + bounds_tolerance
                for axis in range(3)
            ),
            "minimum_analytic_added_pad_exterior_recess_mm": round(
                pad_outer_depth,
                3,
            ),
        }

    minimum_insert_support = float(
        values["minimum_insert_bearing_support_ratio"]
    )
    minimum_bridge_support = float(
        values["minimum_bridge_bearing_support_ratio"]
    )
    selected_pad_records = [
        pad
        for module in selected_records
        for pad in module["pads"]
    ]
    selected_bridge_bearings = [
        bearing
        for module in selected_records
        for bearing in module["bridge_bearing"]
    ]
    topology_pass = all(
        record["components"]
        == int(validation_values["required_component_count"])
        and record["boundary_edges"]
        == int(validation_values["required_boundary_edges"])
        and record["nonmanifold_edges"]
        == int(validation_values["required_nonmanifold_edges"])
        for record in (*topology.values(), *bridge_topology.values())
    )
    zero_matrix_pass = all(
        float(record["positive_overlap_volume_mm3"])
        <= zero_tolerance
        for matrix in (
            seated_pair_matrix,
            body_pair_before_relief,
            body_pair_after_relief,
            bridge_body_matrix,
            bridge_bridge_matrix,
        )
        for record in matrix.values()
    )
    source_metal_state = {
        name: record["clear"]
        for name, record in source_metal_collisions.items()
    }
    v9_metal_state = {
        name: record["clear"]
        for name, record in v9_metal_collisions.items()
    }
    validation = {
        "v05_m2_interface_datums_unchanged": (
            interface["interface_revision"]
            == config["required_interface_revision"]
            and interface["metal_handoff_record"]["revision"]
            == config["required_metal_handoff_revision"]
        ),
        "exactly_five_removable_bridges_and_ten_m3_stations": (
            len(bridges) == int(values["selected_module_count"])
            and len(tool_envelopes) == int(values["m3_screw_total"])
        ),
        "all_selected_pads_have_broad_final_v8_roots": all(
            float(pad["root_intersection_mm3"])
            >= float(values["minimum_root_intersection_mm3"])
            for pad in selected_pad_records
        ),
        "all_insert_pilots_are_open_and_well_supported": all(
            float(pad["pilot_residual_mm3"]) <= zero_tolerance
            and float(pad["insert_bearing_support_ratio"])
            >= minimum_insert_support
            for pad in selected_pad_records
        ),
        "all_bridge_screw_bearings_are_supported": all(
            float(bearing["support_ratio"]) >= minimum_bridge_support
            for bearing in selected_bridge_bearings
        ),
        "only_allowlisted_lower_center_local_reliefs_used": (
            len(local_relief_records) == 2
            and all(
                float(record["overlap_before_mm3"])
                <= float(
                    values[
                        "maximum_allowed_pre_relief_bridge_overlap_mm3"
                    ]
                )
                and float(record["overlap_after_mm3"])
                <= zero_tolerance
                for record in local_relief_records
            )
        ),
        "all_thirteen_printed_parts_are_single_closed_manifolds": (
            topology_pass
        ),
        "all_seated_printed_part_pairs_have_zero_positive_overlap": (
            zero_matrix_pass
        ),
        "all_five_body_and_service_assembly_paths_clear": all(
            record["all_samples_clear"]
            for record in assembly_paths.values()
        ),
        "all_five_bridges_have_clear_inward_seating_paths": all(
            record["all_samples_clear"]
            for record in bridge_paths.values()
        ),
        "all_ten_driver_envelopes_clear_printed_parts": all(
            record["clear"] for record in tool_body_collisions.values()
        ),
        "v9_introduces_no_new_complete_m2_metal_collision": (
            source_metal_state == v9_metal_state
        ),
        "all_five_bridges_clear_complete_m2_metal": all(
            record["clear"] for record in bridge_metal_collisions.values()
        ),
        "all_ten_driver_envelopes_clear_complete_m2_metal": all(
            record["clear"] for record in tool_metal_collisions.values()
        ),
        "clean_exterior_bounds_and_half_mm_pad_recess_preserved": (
            all(
                record["bounds_inside_v8_extents"]
                and float(
                    record[
                        "minimum_analytic_added_pad_exterior_recess_mm"
                    ]
                )
                >= float(
                    values[
                        "minimum_analytic_pad_exterior_recess_mm"
                    ]
                )
                for record in exterior_preservation.values()
            )
        ),
        "mirror_panel_landings_untouched": (
            pad_landing_overlap_pairs
            == int(
                validation_values[
                    "mirror_landing_triangle_overlap_pairs"
                ]
            )
            and all(
                sum(
                    sum(
                        cutter[
                            "mirror_landing_triangle_overlap_pairs"
                        ].values()
                    )
                    for cutter in record["cutters"]
                )
                == 0
                for record in local_relief_records
            )
        ),
    }
    stage("V9 digital validation evaluated", started_at)

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for name in PRODUCTION_PARTS:
        export_stl(parts[name], parts_dir / f"{name}.stl")
    for name, bridge in bridges.items():
        export_stl(bridge, parts_dir / f"{name}.stl")

    for obj in bpy.data.objects:
        if obj not in (*parts.values(), *bridges.values()):
            obj.hide_viewport = True
            obj.hide_render = True
    for obj in (*parts.values(), *bridges.values()):
        obj.hide_viewport = False
        obj.hide_render = False
    blend_path = output_dir / "gate9-body-seam-retention-candidate-v9.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    review = {
        "gate": "Gate 9 V9 removable body-seam retention",
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "metal_handoff_revision": interface["metal_handoff_record"][
            "revision"
        ],
        "source_v8_blend": str(source_blend.relative_to(REPO_ROOT)),
        "output_blend": str(blend_path.relative_to(REPO_ROOT)),
        "retention_architecture": values["architecture"],
        "hardware": {
            key: values[key]
            for key in (
                "m3_screws_per_bridge",
                "m3_screw_total",
                "m3_heat_set_insert_total",
                "m3_socket_cap_screw_length_mm",
                "heat_set_insert_nominal_outer_diameter_mm",
                "heat_set_insert_nominal_length_mm",
                "insert_pilot_diameter_mm",
                "insert_pilot_depth_mm",
                "bridge_clearance_diameter_mm",
            )
        },
        "dimensions": {
            key: values[key]
            for key in (
                "pad_seam_setback_mm",
                "pad_diameter_mm",
                "pad_depth_mm",
                "pad_shell_overlap_mm",
                "minimum_analytic_pad_exterior_recess_mm",
                "bridge_contact_face_clearance_mm",
                "bridge_end_diameter_mm",
                "bridge_end_thickness_mm",
                "bridge_spine_diameter_mm",
                "bridge_spine_inward_arch_mm",
                "tool_envelope_diameter_mm",
                "tool_envelope_length_mm",
            )
        },
        "selected_modules": selected_records,
        "rejected_legacy_modules": rejected_records,
        "local_bridge_clearance_relief": local_relief_records,
        "topology": topology,
        "bridge_topology": bridge_topology,
        "body_pair_matrix_before_local_relief": body_pair_before_relief,
        "body_pair_matrix_after_local_relief": body_pair_after_relief,
        "seated_production_pair_matrix": seated_pair_matrix,
        "bridge_body_pair_matrix_before_local_relief": (
            pre_relief_bridge_body
        ),
        "bridge_body_pair_matrix": bridge_body_matrix,
        "bridge_bridge_pair_matrix": bridge_bridge_matrix,
        "assembly_paths": assembly_paths,
        "bridge_inward_assembly_paths": bridge_paths,
        "tool_to_printed_part_collisions": tool_body_collisions,
        "source_v8_to_m2_metal_collisions": source_metal_collisions,
        "v9_to_m2_metal_collisions": v9_metal_collisions,
        "bridge_to_m2_metal_collisions": bridge_metal_collisions,
        "tool_to_m2_metal_collisions": tool_metal_collisions,
        "exterior_preservation": exterior_preservation,
        "mirror_panel_landing_validation": {
            "pad_triangle_overlap_pair_count": (
                pad_landing_overlap_pairs
            ),
            "relief_cutter_triangle_overlap_pair_count": sum(
                sum(
                    sum(
                        cutter[
                            "mirror_landing_triangle_overlap_pairs"
                        ].values()
                    )
                    for cutter in record["cutters"]
                )
                for record in local_relief_records
            ),
        },
        "digital_validation": {
            **validation,
            "digital_v9_body_retention_candidate_pass": all(
                validation.values()
            ),
        },
        "remaining_production_blockers": [
            "Print one ASA heat-set insert and bridge-end coupon with the actual purchased M3 insert; confirm insertion, M3 x 8 engagement, torque, and removal before any body-shell print.",
            "Physically assemble the retained V9 shell interfaces and verify seam closure without cutting, melting, bending, or force fitting.",
            "Finish and validate ear interfaces, eye assemblies, glow-module skirts and retention, lamp portal, and steering portal against the final reinforced V9 shell.",
            "Rerun final complete-system collision, wiring, drainage, vibration, and service validation before authorizing the final black ASA print.",
        ],
        "acceptance_holds": config["acceptance_holds"],
    }
    review_path = (
        REPO_ROOT / config["review_summary_path"]
    ).resolve()
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(review, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "selected_bridge_count": len(bridges),
                "local_relief_count": len(local_relief_records),
                "review": str(review_path.relative_to(REPO_ROOT)),
                "blend": str(blend_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not all(validation.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
