#!/usr/bin/env python3
"""Generate the compact V9 M3 heat-set insert and bridge clamp coupon."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]

import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_rear_architecture_comparison as review  # noqa: E402


DEFAULT_CONFIG = PACKAGE_ROOT / "config/v9-m3-insert-bridge-coupon.json"
AXES = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))


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
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "components": len(gate5.components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "volume_mm3": round(gate5.mesh_volume(obj), 3),
        "bounds_minimum_mm": [
            round(min(point[axis] for point in points), 4)
            for axis in range(3)
        ],
        "bounds_maximum_mm": [
            round(max(point[axis] for point in points), 4)
            for axis in range(3)
        ],
    }


def require_single_manifold(obj: bpy.types.Object, operation: str) -> None:
    gate5.require_manifold(obj, operation)
    components = len(gate5.components(obj))
    if components != 1:
        raise ValueError(
            f"{operation}: {obj.name} has {components} components"
        )


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path),
        export_selected_objects=True,
    )
    obj.select_set(False)


def build_base(
    values: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, list[dict[str, Any]]]:
    base_thickness = float(values["base_thickness_mm"])
    boss_y = float(values["boss_center_y_mm"])
    boss_diameter = float(values["boss_diameter_mm"])
    boss_depth = float(values["boss_total_depth_mm"])
    overlap = float(values["boss_base_overlap_mm"])
    pilot_depth = float(values["pilot_depth_mm"])
    base = gate5.box(
        "v9_coupon__insert_base",
        Vector((0.0, boss_y, base_thickness / 2.0)),
        AXES,
        (
            float(values["base_length_mm"]),
            float(values["base_width_mm"]),
            base_thickness,
        ),
        material,
    )
    boss_bottom = base_thickness - overlap
    boss_top = boss_bottom + boss_depth
    root_volume = (
        math.pi * (boss_diameter / 2.0) ** 2 * overlap
    )
    records = []
    for index, (center_x, pilot_diameter) in enumerate(
        zip(
            values["boss_centers_x_mm"],
            values["pilot_diameters_left_to_right_mm"],
            strict=True,
        ),
        start=1,
    ):
        center = Vector((float(center_x), boss_y, 0.0))
        boss = gate5.cylinder(
            f"v9_coupon__boss_{index}",
            center + Vector((0, 0, boss_bottom)),
            center + Vector((0, 0, boss_top)),
            boss_diameter,
            material,
            vertices=48,
        )
        gate5.apply_boolean(base, boss, "UNION", solver="MANIFOLD")
        pilot = gate5.cylinder(
            f"v9_coupon__pilot_{index}",
            center + Vector((0, 0, boss_top + 0.2)),
            center + Vector((0, 0, boss_top - pilot_depth)),
            float(pilot_diameter),
            vertices=32,
        )
        gate5.apply_boolean(base, pilot, "DIFFERENCE", solver="MANIFOLD")
        require_single_manifold(base, f"boss {index} union and pilot")
        probe = gate5.cylinder(
            f"v9_coupon__pilot_probe_{index}",
            center + Vector((0, 0, boss_top + 0.1)),
            center + Vector((0, 0, boss_top - pilot_depth + 0.1)),
            float(pilot_diameter) - 0.1,
            vertices=24,
        )
        residual = intersection_volume(
            probe,
            base,
            f"v9_coupon__pilot_residual_{index}",
        )
        bpy.data.objects.remove(probe, do_unlink=True)
        records.append(
            {
                "station": index,
                "position": ("left", "center", "right")[index - 1],
                "center_x_mm": float(center_x),
                "pilot_diameter_mm": float(pilot_diameter),
                "pilot_depth_mm": pilot_depth,
                "minimum_radial_sidewall_mm": round(
                    (boss_diameter - float(pilot_diameter)) / 2.0,
                    3,
                ),
                "analytic_root_volume_mm3": round(root_volume, 3),
                "pilot_residual_mm3": round(residual, 6),
            }
        )
    base.name = "v9_m3_insert_coupon_base"
    return base, records


def build_bridge(
    values: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    center_y = float(values["bridge_center_y_mm"])
    spacing = float(values["bridge_hole_spacing_mm"])
    end_diameter = float(values["bridge_end_diameter_mm"])
    spine_width = float(values["bridge_spine_width_mm"])
    thickness = float(values["bridge_thickness_mm"])
    first_x, second_x = -spacing / 2.0, spacing / 2.0
    bridge = gate5.cylinder(
        "v9_coupon__bridge_end_1",
        Vector((first_x, center_y, 0.0)),
        Vector((first_x, center_y, thickness)),
        end_diameter,
        material,
        vertices=48,
    )
    spine = gate5.box(
        "v9_coupon__bridge_spine",
        Vector((0.0, center_y, thickness / 2.0)),
        AXES,
        (spacing, spine_width, thickness),
        material,
    )
    gate5.apply_boolean(bridge, spine, "UNION", solver="MANIFOLD")
    second = gate5.cylinder(
        "v9_coupon__bridge_end_2",
        Vector((second_x, center_y, 0.0)),
        Vector((second_x, center_y, thickness)),
        end_diameter,
        material,
        vertices=48,
    )
    gate5.apply_boolean(bridge, second, "UNION", solver="MANIFOLD")
    for index, center_x in enumerate((first_x, second_x), start=1):
        clearance = gate5.cylinder(
            f"v9_coupon__bridge_clearance_{index}",
            Vector((center_x, center_y, -0.2)),
            Vector((center_x, center_y, thickness + 0.2)),
            float(values["bridge_clearance_diameter_mm"]),
            vertices=32,
        )
        gate5.apply_boolean(
            bridge,
            clearance,
            "DIFFERENCE",
            solver="MANIFOLD",
        )
    bridge.name = "v9_m3_insert_coupon_bridge"
    require_single_manifold(bridge, "coupon bridge")
    return bridge


def main() -> None:
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_v9 = json.loads(
        (REPO_ROOT / config["source_v9_config"]).read_text(
            encoding="utf-8"
        )
    )
    values = config["coupon"]
    gate3.clean_scene()
    materials = {
        "base": review.create_material("v9_coupon_base", "#3B3D42"),
        "bridge": review.create_material("v9_coupon_bridge", "#D99A31"),
    }
    base, pilot_records = build_base(values, materials["base"])
    bridge = build_bridge(values, materials["bridge"])
    topology = {
        "base": topology_record(base),
        "bridge": topology_record(bridge),
    }
    minimum_sidewall = min(
        record["minimum_radial_sidewall_mm"]
        for record in pilot_records
    )
    bearing_width = (
        float(values["bridge_end_diameter_mm"])
        - float(values["bridge_clearance_diameter_mm"])
    ) / 2.0
    available_thread_engagement = (
        float(values["m3_socket_cap_screw_length_mm"])
        - float(values["bridge_thickness_mm"])
    )
    v9_values = source_v9["retention_system"]
    geometry_validation = {
        "base_and_bridge_are_single_closed_manifolds": all(
            record["components"] == 1
            and record["boundary_edges"] == 0
            and record["nonmanifold_edges"] == 0
            for record in topology.values()
        ),
        "all_three_blind_pilots_are_open": all(
            record["pilot_residual_mm3"] <= 0.001
            for record in pilot_records
        ),
        "all_boss_roots_exceed_minimum_volume": all(
            record["analytic_root_volume_mm3"]
            >= float(values["minimum_root_volume_mm3"])
            for record in pilot_records
        ),
        "minimum_boss_sidewall_is_preserved": (
            minimum_sidewall
            >= float(values["minimum_boss_sidewall_mm"])
        ),
        "bridge_bearing_width_is_preserved": (
            bearing_width
            >= float(values["minimum_bridge_bearing_width_mm"])
        ),
        "m3x8_has_positive_non_bottoming_insert_engagement": (
            available_thread_engagement > 0.0
            and available_thread_engagement
            < float(values["nominal_insert_length_mm"])
        ),
        "coupon_matches_v9_pad_bridge_and_hardware_dimensions": (
            float(values["base_thickness_mm"]) == 1.8
            and float(values["boss_diameter_mm"])
            == float(v9_values["pad_diameter_mm"])
            and float(values["boss_total_depth_mm"])
            == float(v9_values["pad_depth_mm"])
            and float(values["boss_base_overlap_mm"])
            == float(v9_values["pad_shell_overlap_mm"])
            and float(values["pilot_depth_mm"])
            == float(v9_values["insert_pilot_depth_mm"])
            and float(values["bridge_end_diameter_mm"])
            == float(v9_values["bridge_end_diameter_mm"])
            and float(values["bridge_thickness_mm"])
            == float(v9_values["bridge_end_thickness_mm"])
            and float(values["bridge_clearance_diameter_mm"])
            == float(v9_values["bridge_clearance_diameter_mm"])
            and float(values["m3_socket_cap_screw_length_mm"])
            == float(v9_values["m3_socket_cap_screw_length_mm"])
        ),
    }
    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    export_stl(base, parts_dir / "v9_m3_insert_coupon_base.stl")
    export_stl(bridge, parts_dir / "v9_m3_insert_coupon_bridge.stl")
    blend_path = output_dir / "v9-m3-insert-bridge-coupon.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    summary = {
        "gate": "V9 M3 heat-set insert and bridge clamp coupon",
        "status": config["status"],
        "source_v9_config": config["source_v9_config"],
        "output_blend": str(blend_path.relative_to(REPO_ROOT)),
        "material": values["material"],
        "dimensions": values,
        "pilot_station_map_left_to_right": pilot_records,
        "derived_dimensions": {
            "minimum_boss_radial_sidewall_mm": round(
                minimum_sidewall, 3
            ),
            "bridge_radial_bearing_width_mm": round(
                bearing_width, 3
            ),
            "m3x8_available_thread_engagement_mm": round(
                available_thread_engagement, 3
            ),
        },
        "topology": topology,
        "digital_validation": {
            **geometry_validation,
            "digital_coupon_geometry_candidate_pass": all(
                geometry_validation.values()
            ),
        },
        "prusa_mk4_generic_asa_validation": None,
        "physical_test_required": True,
        "physical_test_completed": False,
        "selected_pilot_diameter_mm": None,
        "production_release_effect": (
            "No V9 body or ear production print is authorized until the "
            "actual insert is tested; regenerate V9 if the selected pilot "
            "is not 4.1 mm."
        ),
        "physical_test": config["physical_test"],
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
                "validation": geometry_validation,
                "pilot_stations": pilot_records,
                "review": str(review_path.relative_to(REPO_ROOT)),
                "blend": str(blend_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not all(geometry_validation.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
