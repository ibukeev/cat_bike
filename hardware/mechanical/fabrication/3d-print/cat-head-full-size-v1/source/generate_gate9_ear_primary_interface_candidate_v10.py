#!/usr/bin/env python3
"""Generate complementary, broadly rooted Gate 9 V10 primary ear interfaces."""

from __future__ import annotations

import copy
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

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_body_seam_clearance_candidate_v8 as v8  # noqa: E402
import generate_gate9_m2_rear_interface_candidate_v7 as v7  # noqa: E402
import generate_gate9_rear_architecture_comparison as review  # noqa: E402


DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-ear-primary-interface-candidate-v10.json"
)
SIDES = ("left", "right")
UPDATED_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_ear",
    "right_ear",
)


def stage(message: str, started_at: float) -> None:
    print(
        f"[gate9-v10-ear +{time.monotonic() - started_at:7.2f}s] "
        f"{message}",
        flush=True,
    )


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def duplicate_object(source: bpy.types.Object, name: str) -> bpy.types.Object:
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    duplicate.name = name
    bpy.context.collection.objects.link(duplicate)
    return duplicate


def import_stl(path: Path, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.stl_import(filepath=str(path))
    imported = list(bpy.context.selected_objects)
    if len(imported) != 1:
        raise ValueError(f"{path} imported {len(imported)} objects")
    imported[0].name = name
    return imported[0]


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


def require_single_manifold(obj: bpy.types.Object, operation: str) -> None:
    gate5.require_manifold(obj, operation)
    components = len(gate5.components(obj))
    if components != 1:
        raise ValueError(
            f"{operation}: {obj.name} has {components} components"
        )


def bounds(obj: bpy.types.Object) -> tuple[list[float], list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def bounds_inside(
    candidate: bpy.types.Object,
    source_bounds: tuple[list[float], list[float]],
    tolerance: float = 0.01,
) -> bool:
    candidate_bounds = bounds(candidate)
    return all(
        candidate_bounds[0][axis] >= source_bounds[0][axis] - tolerance
        and candidate_bounds[1][axis]
        <= source_bounds[1][axis] + tolerance
        for axis in range(3)
    )


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


def reconstructed_ear_modules(
    gate8_config: dict[str, Any],
) -> tuple[Any, list[Vector], dict[str, tuple[dict[str, Any], float, int]]]:
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
    usable = [
        segment
        for segment in segments
        if segment["length_mm"] >= minimum
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
    output = {}
    for segment, fraction, allocation_count in allocations:
        ear_sections = [
            section
            for section in segment["sections"]
            if section.endswith("_ear")
        ]
        if not ear_sections:
            continue
        side = ear_sections[0].split("_", 1)[0]
        if side in output:
            raise ValueError(f"Multiple {side} ear interface modules")
        output[side] = (segment, fraction, allocation_count)
    if set(output) != set(SIDES):
        raise ValueError(f"Missing ear modules: {set(SIDES) - set(output)}")
    return model, points, output


def interface_frame(
    name: str,
    segment: dict[str, Any],
    fraction: float,
    allocation_count: int,
    model: Any,
    points: list[Vector],
    config: dict[str, Any],
) -> dict[str, Any]:
    joint = config["joint_system"]
    owner, receiver = gate5.joint_roles(segment, config)
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    seam_point = p0.lerp(p1, fraction)
    module_length = gate5.joint_module_length(
        segment,
        allocation_count,
        config,
    )
    owner_local = gate5.side_geometry(
        name,
        segment,
        owner,
        seam_point,
        tangent,
        model,
        points,
    )
    receiver_local = gate5.side_geometry(
        name,
        segment,
        receiver,
        seam_point,
        tangent,
        model,
        points,
    )
    tab_thickness = float(joint["ear_flange_tab_thickness_mm"])
    tab_depth = float(joint["ear_flange_tab_depth_mm"])
    clearance = float(joint["flange_face_clearance_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    root_overlap = float(joint["ear_flange_shell_overlap_mm"])
    inward = (
        -owner_local["normal"] - receiver_local["normal"]
    ).normalized()
    bolt_axis = inward.cross(tangent).normalized()
    if bolt_axis.dot(owner_local["toward_face"]) < 0.0:
        bolt_axis.negate()
    tab_depth_center = wall + tab_depth / 2.0 - root_overlap
    face_offset = tab_thickness / 2.0 + clearance / 2.0
    owner_center = (
        seam_point
        + inward * tab_depth_center
        + bolt_axis * face_offset
    )
    receiver_center = (
        seam_point
        + inward * tab_depth_center
        - bolt_axis * face_offset
    )
    requested_recess = float(
        joint["ear_minimum_tab_exterior_recess_mm"]
    )
    half_dimensions = (
        module_length / 2.0,
        tab_thickness / 2.0,
        tab_depth / 2.0,
    )

    def maximum_outward_projection(
        center: Vector,
        normal: Vector,
    ) -> float:
        return (
            (center - seam_point).dot(normal)
            + half_dimensions[0] * abs(tangent.dot(normal))
            + half_dimensions[1] * abs(bolt_axis.dot(normal))
            + half_dimensions[2] * abs(inward.dot(normal))
        )

    required_shift = 0.0
    normals = (owner_local["normal"], receiver_local["normal"])
    for center in (owner_center, receiver_center):
        for normal in normals:
            inward_projection = -inward.dot(normal)
            required_shift = max(
                required_shift,
                (
                    maximum_outward_projection(center, normal)
                    + requested_recess
                )
                / inward_projection,
            )
    if required_shift > 0.0:
        required_shift += 0.02
        owner_center += inward * required_shift
        receiver_center += inward * required_shift
    fastener_center = (
        (owner_center + receiver_center) / 2.0
        + inward * (tab_depth * 0.20)
    )
    half_span = module_length * 0.28
    screw_points = [
        fastener_center - tangent * half_span,
        fastener_center + tangent * half_span,
    ]
    return {
        "owner": owner,
        "receiver": receiver,
        "tangent": tangent,
        "inward": inward,
        "bolt_axis": bolt_axis,
        "seam_point": seam_point,
        "owner_center": owner_center,
        "receiver_center": receiver_center,
        "screw_points": screw_points,
        "module_length_mm": module_length,
        "tab_thickness_mm": tab_thickness,
        "tab_depth_mm": tab_depth,
        "required_inward_shift_mm": required_shift,
    }


def add_slot(
    tab: bpy.types.Object,
    name: str,
    screw_point: Vector,
    frame: dict[str, Any],
    values: dict[str, Any],
) -> None:
    half_extension = (
        float(values["slot_overall_length_mm"])
        - float(values["slot_width_mm"])
    ) / 2.0
    cut_extension = 2.0
    for direction in (-1.0, 1.0):
        point = (
            screw_point
            + frame["tangent"] * (direction * half_extension)
        )
        cutter = gate5.cylinder(
            f"{name}__slot_end_{'n' if direction < 0 else 'p'}",
            point
            - frame["bolt_axis"]
            * (frame["tab_thickness_mm"] + cut_extension),
            point
            + frame["bolt_axis"]
            * (frame["tab_thickness_mm"] + cut_extension),
            float(values["slot_width_mm"]),
            vertices=32,
        )
        gate5.apply_boolean(
            tab,
            cutter,
            "DIFFERENCE",
            solver="MANIFOLD",
        )
    require_single_manifold(tab, f"{name} tolerance slot")


def collision_group(
    probe: bpy.types.Object,
    objects: dict[str, bpy.types.Object],
    prefix: str,
) -> dict[str, Any]:
    output = {}
    for object_name, obj in objects.items():
        volume = intersection_volume(
            probe,
            obj,
            f"{prefix}__{probe.name}__{object_name}",
        )
        output[object_name] = {
            "positive_overlap_volume_mm3": round(volume, 6),
            "clear": volume <= 0.001,
        }
    return output


def assembly_path(
    ear: bpy.types.Object,
    fixed: dict[str, bpy.types.Object],
    outward: Vector,
    offsets: list[float],
    prefix: str,
) -> dict[str, Any]:
    samples = []
    for offset in offsets:
        moved = duplicate_object(ear, f"{prefix}__offset_{offset:g}")
        moved.location += outward * float(offset)
        collisions = collision_group(
            moved,
            fixed,
            f"{prefix}__collision_{offset:g}",
        )
        samples.append(
            {
                "offset_mm": float(offset),
                "collisions": collisions,
                "clear": all(
                    record["clear"] for record in collisions.values()
                ),
            }
        )
        bpy.data.objects.remove(moved, do_unlink=True)
    return {
        "outward_direction_head": [
            round(value, 6) for value in outward
        ],
        "samples": samples,
        "all_samples_clear": all(sample["clear"] for sample in samples),
    }


def main() -> None:
    started_at = time.monotonic()
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    values = config["primary_interface"]
    v9_summary = json.loads(
        (REPO_ROOT / config["source_v9_validation"]).read_text(
            encoding="utf-8"
        )
    )
    if not all(v9_summary["digital_validation"].values()):
        raise ValueError("V10 source V9 validation is not fully passing")
    gate8_config = json.loads(
        (REPO_ROOT / config["source_gate8_config"]).read_text(
            encoding="utf-8"
        )
    )
    source_blend = (REPO_ROOT / config["source_v9_blend"]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    stage("accepted V9 body source loaded", started_at)
    parts = {
        name: duplicate_object(
            bpy.data.objects[source_name],
            f"gate9_v10__{name}",
        )
        for name, source_name in config["source_head_objects"].items()
    }
    for ear_name, relative_path in config["source_ear_stls"].items():
        parts[ear_name] = import_stl(
            (REPO_ROOT / relative_path).resolve(),
            f"gate9_v10__{ear_name}",
        )
    source_bounds = {
        name: bounds(obj) for name, obj in parts.items()
    }
    source_volumes = {
        name: gate5.mesh_volume(obj) for name, obj in parts.items()
    }
    materials = {
        "legacy": review.create_material(
            "gate9_v10_legacy_removal",
            "#C84A45",
            alpha=0.3,
        ),
        "flange": review.create_material(
            "gate9_v10_primary_ear_flange",
            "#E6A438",
        ),
        "driver": review.create_material(
            "gate9_v10_driver_envelope",
            "#D34C47",
            alpha=0.25,
        ),
        "nut_tool": review.create_material(
            "gate9_v10_nut_tool_envelope",
            "#AE4CCC",
            alpha=0.25,
        ),
        "hardware": review.create_material(
            "gate9_v10_m3_hardware",
            "#C6CCD4",
        ),
    }
    model, points, modules = reconstructed_ear_modules(gate8_config)
    candidate_config = copy.deepcopy(gate8_config)
    candidate_joint = candidate_config["joint_system"]
    candidate_joint.update(
        {
            "ear_fastener_count_per_module": int(
                values["fastener_count_per_ear"]
            ),
            "m3_clearance_diameter_mm": float(
                values["round_clearance_diameter_mm"]
            ),
            "ear_flange_tab_thickness_mm": float(
                values["flange_tab_thickness_mm"]
            ),
            "ear_flange_tab_depth_mm": float(
                values["flange_tab_depth_mm"]
            ),
            "ear_flange_shell_overlap_mm": float(
                values["flange_shell_overlap_mm"]
            ),
            "flange_face_clearance_mm": float(
                values["flange_face_clearance_mm"]
            ),
            "ear_minimum_tab_exterior_recess_mm": float(
                values["minimum_tab_exterior_recess_mm"]
            ),
            "ear_flange_root_web_length_mm": float(
                values["root_web_length_mm"]
            ),
            "ear_flange_root_web_thickness_mm": float(
                values["root_web_thickness_mm"]
            ),
            "ear_flange_root_web_end_margin_mm": float(
                values["root_web_end_margin_mm"]
            ),
            "ear_flange_root_web_boolean_overlap_mm": float(
                values["root_web_boolean_overlap_mm"]
            ),
            "solid_ear_flange_root_base": True,
        }
    )
    candidate_config["validation"].update(
        {
            "minimum_flange_retained_volume_ratio": 0.55,
            "maximum_flange_retained_volume_ratio": 1.25,
            "maximum_solid_base_flange_retained_volume_ratio": 1.75,
            "minimum_flange_projected_length_ratio": 0.90,
        }
    )
    side_records = {}
    frames = {}
    legacy_removal_records = []
    hardware: dict[str, bpy.types.Object] = {}
    tools: dict[str, bpy.types.Object] = {}
    tool_owners: dict[str, str] = {}
    hardware_owners: dict[str, set[str]] = {}
    for side in SIDES:
        segment, fraction, allocation_count = modules[side]
        legacy_name = f"gate9_v10__legacy_{side}_ear_interface"
        legacy_tabs, legacy_record = gate5.create_internal_flange_tabs(
            legacy_name,
            segment,
            fraction,
            allocation_count,
            model,
            points,
            gate8_config,
            materials["legacy"],
        )
        legacy_frame = interface_frame(
            legacy_name,
            segment,
            fraction,
            allocation_count,
            model,
            points,
            gate8_config,
        )
        for section, tab in legacy_tabs.items():
            legacy_removal_records.append(
                {
                    "side": side,
                    "section": section,
                    "legacy_fastener_count": int(
                        legacy_record["internal_m3_screws"]
                    ),
                    "disposition": (
                        "encapsulated by the larger solid V10 saddle; "
                        "the two middle legacy bores are filled and the "
                        "two outer stations are recut as round plus slot"
                    ),
                    "topology_before": topology_record(parts[section]),
                }
            )
            bpy.data.objects.remove(tab, do_unlink=True)
        candidate_name = f"gate9_v10__primary_{side}_ear_interface"
        tabs, tab_record = gate5.create_internal_flange_tabs(
            candidate_name,
            segment,
            fraction,
            allocation_count,
            model,
            points,
            candidate_config,
            materials["flange"],
        )
        frame = interface_frame(
            candidate_name,
            segment,
            fraction,
            allocation_count,
            model,
            points,
            candidate_config,
        )
        frames[side] = frame
        for section, tab in tabs.items():
            root_intersection = intersection_volume(
                tab,
                parts[section],
                f"gate9_v10__root_intersection__{section}",
            )
            gate5.apply_boolean(
                parts[section],
                tab,
                "UNION",
                solver="MANIFOLD",
            )
            require_single_manifold(
                parts[section],
                f"{section} broad primary ear flange union",
            )
            add_slot(
                parts[section],
                f"{candidate_name}__{section}",
                frame["screw_points"][1],
                frame,
                values,
            )
            tab_record[f"{section}_root_intersection_mm3"] = round(
                root_intersection,
                3,
            )
            tab_record[f"{section}_attachment_bridge_lengths_mm"] = []
        screw_records = []
        for index, screw_point in enumerate(
            frame["screw_points"],
            start=1,
        ):
            station = "round" if index == 1 else "slot"
            owner_start = (
                frame["owner_center"]
                + frame["bolt_axis"]
                * (
                    frame["tab_thickness_mm"] / 2.0
                    + float(values["tool_start_clearance_mm"])
                )
            )
            receiver_start = (
                frame["receiver_center"]
                - frame["bolt_axis"]
                * (
                    frame["tab_thickness_mm"] / 2.0
                    + float(values["tool_start_clearance_mm"])
                )
            )
            driver = gate5.cylinder(
                f"gate9_v10__{side}_{station}_driver_tool",
                owner_start,
                owner_start
                + frame["bolt_axis"]
                * float(values["tool_envelope_length_mm"]),
                float(values["driver_envelope_diameter_mm"]),
                materials["driver"],
                vertices=32,
            )
            nut_tool = gate5.cylinder(
                f"gate9_v10__{side}_{station}_nut_tool",
                receiver_start,
                receiver_start
                - frame["bolt_axis"]
                * float(values["tool_envelope_length_mm"]),
                float(values["nut_tool_envelope_diameter_mm"]),
                materials["nut_tool"],
                vertices=32,
            )
            tools[driver.name] = driver
            tools[nut_tool.name] = nut_tool
            tool_owners[driver.name] = frame["owner"]
            tool_owners[nut_tool.name] = frame["receiver"]
            screw = gate5.cylinder(
                f"gate9_v10__{side}_{station}_m3_screw",
                receiver_start - frame["bolt_axis"] * 0.5,
                owner_start + frame["bolt_axis"] * 0.5,
                3.0,
                materials["hardware"],
                vertices=24,
            )
            hardware[screw.name] = screw
            hardware_owners[screw.name] = {
                frame["owner"],
                frame["receiver"],
            }
            screw_records.append(
                {
                    "station": station,
                    "center_head_mm": [
                        round(value, 4) for value in screw_point
                    ],
                    "axis_head": [
                        round(value, 6) for value in frame["bolt_axis"]
                    ],
                    "nominal_opening_mm": (
                        [float(values["round_clearance_diameter_mm"])]
                        if station == "round"
                        else [
                            float(values["slot_width_mm"]),
                            float(values["slot_overall_length_mm"]),
                        ]
                    ),
                }
            )
        side_records[side] = {
            "legacy": legacy_record,
            "candidate": tab_record,
            "module_length_mm": round(
                frame["module_length_mm"],
                3,
            ),
            "required_inward_shift_mm": round(
                frame["required_inward_shift_mm"],
                3,
            ),
            "outward_removal_direction_head": [
                round(value, 6) for value in -frame["bolt_axis"]
            ],
            "screws": screw_records,
        }
    stage("legacy ear saddles replaced on four parts", started_at)

    complementary_relief_records = []
    for side in SIDES:
        frame = frames[side]
        cutter = duplicate_object(
            parts[f"{side}_upper_head"],
            f"gate9_v10__{side}_head_interface_relief_cutter",
        )
        cutter_volume = gate5.mesh_volume(cutter)
        cutter.location += (
            -frame["bolt_axis"]
            * float(values["complementary_relief_clearance_mm"])
        )
        ear = parts[f"{side}_ear"]
        before = gate5.mesh_volume(ear)
        gate5.apply_boolean(
            ear,
            cutter,
            "DIFFERENCE",
            solver="MANIFOLD",
        )
        cleanup = gate5.keep_largest_component(ear)
        require_single_manifold(
            ear,
            f"{side} localized complementary ear relief",
        )
        residual_cleanup = []
        for pass_index in (1, 2):
            pass_record = v8.apply_local_relief(
                parts[f"{side}_upper_head"],
                ear,
                f"{side}_ear_residual_{pass_index}",
                0.10,
                float(config["validation"]["zero_volume_tolerance_mm3"]),
                1.0,
                {},
            )
            residual_cleanup.append(pass_record)
            if (
                float(pass_record["overlap_after_mm3"])
                <= float(
                    config["validation"]["zero_volume_tolerance_mm3"]
                )
            ):
                break
        complementary_relief_records.append(
            {
                "side": side,
                "clearance_mm": float(
                    values["complementary_relief_clearance_mm"]
                ),
                "source_head_cutter_volume_mm3": round(cutter_volume, 3),
                "removed_ear_volume_mm3": round(
                    before - gate5.mesh_volume(ear),
                    3,
                ),
                "detached_component_cleanup": cleanup,
                "residual_component_cleanup": residual_cleanup,
                "minimum_analytic_joint_clearance_mm": float(
                    values["complementary_relief_clearance_mm"]
                ),
                "topology_after": topology_record(ear),
            }
        )

    fixed_parts = {
        "left_upper_head": parts["left_upper_head"],
        "right_upper_head": parts["right_upper_head"],
        "left_lower_face": bpy.data.objects[
            "gate9_v9__left_lower_face"
        ],
        "right_lower_face": bpy.data.objects[
            "gate9_v9__right_lower_face"
        ],
        "rear_bezel": bpy.data.objects["gate9_v9__rear_bezel"],
        "bottom_keel": bpy.data.objects["gate9_v9__bottom_keel"],
        "left_socket_cap": bpy.data.objects[
            "gate9_v9__left_socket_cap"
        ],
        "right_socket_cap": bpy.data.objects[
            "gate9_v9__right_socket_cap"
        ],
    }
    for obj in bpy.data.objects:
        if obj.name.startswith("body_seam_bridge__"):
            fixed_parts[obj.name] = obj
    all_printed_parts = {
        **fixed_parts,
        "left_ear": parts["left_ear"],
        "right_ear": parts["right_ear"],
    }
    assembly_paths = {}
    for side in SIDES:
        ear_name = f"{side}_ear"
        assembly_paths[ear_name] = assembly_path(
            parts[ear_name],
            {
                name: obj
                for name, obj in fixed_parts.items()
                if name != f"{side}_upper_head"
            }
            | {
                f"{side}_upper_head": parts[f"{side}_upper_head"],
                f"{'right' if side == 'left' else 'left'}_ear": parts[
                    f"{'right' if side == 'left' else 'left'}_ear"
                ],
            },
            -frames[side]["bolt_axis"],
            [
                float(value)
                for value in config["assembly_paths"][
                    "ear_outward_removal_offsets_mm"
                ]
            ],
            f"gate9_v10__{side}_ear_path",
        )
    tool_collisions = {}
    for tool_name, tool in tools.items():
        owner = tool_owners[tool_name]
        collision_targets = {
            name: obj
            for name, obj in all_printed_parts.items()
            if name != owner
        }
        tool_collisions[tool_name] = collision_group(
            tool,
            collision_targets,
            "gate9_v10__tool_collision",
        )
    hardware_collisions = {}
    for hardware_name, item in hardware.items():
        owners = hardware_owners[hardware_name]
        collision_targets = {
            name: obj
            for name, obj in all_printed_parts.items()
            if name not in owners
        }
        hardware_collisions[hardware_name] = collision_group(
            item,
            collision_targets,
            "gate9_v10__hardware_collision",
        )
    metal_objects = {
        obj.name: obj
        for obj in bpy.data.objects
        if obj.name.startswith("metal_v05__")
    }
    updated_part_metal_collisions = {
        name: v7.collision_summary(obj, metal_objects)
        for name, obj in parts.items()
    }
    tool_metal_collisions = {
        name: v7.collision_summary(obj, metal_objects)
        for name, obj in tools.items()
    }
    seated_ear_head_overlap = {}
    for side in SIDES:
        volume = intersection_volume(
            parts[f"{side}_ear"],
            parts[f"{side}_upper_head"],
            f"gate9_v10__seated_{side}_ear_head",
        )
        seated_ear_head_overlap[side] = round(volume, 6)
    topology = {
        name: topology_record(obj) for name, obj in parts.items()
    }
    exterior_preservation = {
        name: {
            "bounds_inside_source_extents": bounds_inside(
                obj,
                source_bounds[name],
            ),
            "source_volume_mm3": round(source_volumes[name], 3),
            "candidate_volume_mm3": round(
                gate5.mesh_volume(obj),
                3,
            ),
        }
        for name, obj in parts.items()
    }
    left_points = side_records["left"]["screws"]
    right_points = side_records["right"]["screws"]
    mirror_errors = []
    for left, right in zip(left_points, right_points, strict=True):
        lp = left["center_head_mm"]
        rp = right["center_head_mm"]
        mirror_errors.append(
            max(
                abs(lp[0] + rp[0]),
                abs(lp[1] - rp[1]),
                abs(lp[2] - rp[2]),
            )
        )
    zero_tolerance = float(
        config["validation"]["zero_volume_tolerance_mm3"]
    )
    validation = {
        "exactly_two_m3_stations_per_ear": all(
            len(record["screws"]) == 2
            for record in side_records.values()
        ),
        "every_ear_has_one_round_and_one_tolerance_slot": all(
            [screw["station"] for screw in record["screws"]]
            == ["round", "slot"]
            for record in side_records.values()
        ),
        "legacy_four_bore_saddles_are_encapsulated_and_recut": (
            len(legacy_removal_records) == 4
            and all(
                record["legacy_fastener_count"] == 4
                and "encapsulated" in record["disposition"]
                for record in legacy_removal_records
            )
        ),
        "all_primary_flange_roots_exceed_minimum_volume": all(
            float(record["candidate"][
                f"{section}_root_intersection_mm3"
            ])
            >= float(values["minimum_root_intersection_mm3"])
            for side, record in side_records.items()
            for section in (
                f"{side}_upper_head",
                f"{side}_ear",
            )
        ),
        "localized_complementary_relief_is_internal_and_manifold": (
            len(complementary_relief_records) == 2
            and all(
                record["minimum_analytic_joint_clearance_mm"] >= 0.50
                and record["topology_after"]["components"] == 1
                and record["topology_after"]["boundary_edges"] == 0
                and record["topology_after"]["nonmanifold_edges"] == 0
                for record in complementary_relief_records
            )
        ),
        "all_four_updated_parts_are_single_closed_manifolds": all(
            record["components"]
            == int(config["validation"]["required_component_count"])
            and record["boundary_edges"]
            == int(config["validation"]["required_boundary_edges"])
            and record["nonmanifold_edges"]
            == int(config["validation"]["required_nonmanifold_edges"])
            for record in topology.values()
        ),
        "seated_ear_head_pairs_have_zero_positive_overlap": all(
            value <= zero_tolerance
            for value in seated_ear_head_overlap.values()
        ),
        "both_ears_have_clear_outward_removal_paths": all(
            record["all_samples_clear"]
            for record in assembly_paths.values()
        ),
        "all_driver_and_nut_tool_envelopes_are_clear": all(
            collision["clear"]
            for group in tool_collisions.values()
            for collision in group.values()
        ),
        "all_m3_hardware_envelopes_clear_non_owned_parts": all(
            collision["clear"]
            for group in hardware_collisions.values()
            for collision in group.values()
        ),
        "updated_ear_parts_and_tools_clear_complete_m2_metal": (
            all(
                record["clear"]
                for record in updated_part_metal_collisions.values()
            )
            and all(
                record["clear"]
                for record in tool_metal_collisions.values()
            )
        ),
        "exterior_bounds_are_preserved": all(
            record["bounds_inside_source_extents"]
            for record in exterior_preservation.values()
        ),
        "left_and_right_fastener_centers_are_mirrored": (
            max(mirror_errors) <= 0.05
        ),
    }
    stage("ear paths, tools, hardware, and metal validated", started_at)
    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for name in UPDATED_PARTS:
        export_stl(parts[name], parts_dir / f"{name}.stl")
    keep = set(parts.values()) | set(tools.values()) | set(hardware.values())
    for obj in bpy.data.objects:
        obj.hide_viewport = obj not in keep
        obj.hide_render = obj not in keep
    blend_path = output_dir / "gate9-ear-primary-interface-v10.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    summary = {
        "gate": "Gate 9 V10 complementary primary ear interfaces",
        "status": config["status"],
        "interface_revision": v9_summary["interface_revision"],
        "metal_handoff_revision": v9_summary[
            "metal_handoff_revision"
        ],
        "source_v9_blend": config["source_v9_blend"],
        "output_blend": str(blend_path.relative_to(REPO_ROOT)),
        "architecture": values["architecture"],
        "hardware": {
            key: values[key]
            for key in (
                "fastener_nominal",
                "fastener_count_per_ear",
                "round_clearance_diameter_mm",
                "slot_width_mm",
                "slot_overall_length_mm",
                "m3_socket_cap_screw_length_mm",
                "washer_outer_diameter_mm",
                "washer_thickness_mm",
                "m3_nyloc_across_flats_mm",
                "m3_nyloc_height_mm",
            )
        },
        "dimensions": {
            key: values[key]
            for key in (
                "flange_face_clearance_mm",
                "flange_tab_thickness_mm",
                "flange_tab_depth_mm",
                "flange_shell_overlap_mm",
                "minimum_tab_exterior_recess_mm",
                "root_web_length_mm",
                "root_web_thickness_mm",
                "root_web_end_margin_mm",
                "root_web_boolean_overlap_mm",
                "complementary_relief_clearance_mm",
                "driver_envelope_diameter_mm",
                "nut_tool_envelope_diameter_mm",
                "tool_envelope_length_mm",
            )
        },
        "side_interfaces": side_records,
        "legacy_saddle_disposition": legacy_removal_records,
        "localized_complementary_relief": complementary_relief_records,
        "topology": topology,
        "seated_ear_head_positive_overlap_mm3": seated_ear_head_overlap,
        "ear_outward_assembly_paths": assembly_paths,
        "tool_to_non_owned_printed_part_collisions": tool_collisions,
        "hardware_to_non_owned_printed_part_collisions": (
            hardware_collisions
        ),
        "updated_parts_to_m2_metal_collisions": (
            updated_part_metal_collisions
        ),
        "tool_to_m2_metal_collisions": tool_metal_collisions,
        "exterior_preservation": exterior_preservation,
        "mirror_fastener_center_max_error_mm": round(
            max(mirror_errors),
            6,
        ),
        "digital_validation": {
            **validation,
            "digital_v10_primary_ear_interface_candidate_pass": all(
                validation.values()
            ),
        },
        "prusa_mk4_generic_asa_validation": None,
        "resolved_physical_findings": [
            "F-12 primary under-ear flange access and structural weakness",
            "F-22 pin-against-pin ear interface",
            "A-18 primary ear flange access and broad-root requirement",
            "A-27 complementary two-path round-and-slot ear interface",
        ],
        "remaining_ear_blockers": [
            "F-13/F-14 and A-11: redesign the under-ear translucent insert and add the spatially separated reinforced M2.5 outer anti-flap tie.",
            "A-12: validate the complete physical install/removal sequence with the under-ear insert and anti-flap tie present.",
            "Print a local round/slot ASA interface coupon before committing the full ears if the actual M3 hardware stack differs from the documented M3 x 20, washers, and nyloc nuts.",
        ],
        "acceptance_holds": config["acceptance_holds"],
    }
    review_path = (
        REPO_ROOT / config["review_summary_path"]
    ).resolve()
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
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
