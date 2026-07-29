#!/usr/bin/env python3
"""Audit Gate 9 bridge sites from pre-export component topology."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_gate9_selected_bridge_sites as audit  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_OUTPUT = (
    PACKAGE_ROOT
    / "output/gate9-selected-bridge-site-audit-v2"
)
PREFIX = "rear_cassette_full_scale"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--candidate-bridge-diameter-mm", type=float, default=14.0
    )
    parser.add_argument(
        "--candidate-end-overlap-mm", type=float, default=6.0
    )
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args)


def duplicate_object(
    source: bpy.types.Object, name: str
) -> bpy.types.Object:
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    duplicate.name = name
    bpy.context.collection.objects.link(duplicate)
    duplicate.hide_viewport = False
    duplicate.hide_render = False
    return duplicate


def object_centroid(obj: bpy.types.Object) -> Vector:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return sum(points, Vector()) / len(points)


def bridge_candidates_from_primary(
    part_name: str,
    components: list[bpy.types.Object],
    diameter_mm: float,
    overlap_mm: float,
) -> tuple[list[bpy.types.Object], list[dict[str, Any]]]:
    primary = components[0]
    bridges = []
    records = []
    for component_index, component in enumerate(
        components[1:], start=2
    ):
        first, second, distance = audit.closest_vertex_pair(
            primary, component
        )
        contact_type = "separated_surfaces"
        if distance < 0.01:
            contact_type = "coincident_point_or_edge_only"
            direction = object_centroid(component) - object_centroid(primary)
            if direction.length < 0.01:
                direction = Vector((0.0, 1.0, 0.0))
            direction.normalize()
            shared = (first + second) / 2.0
            first = shared - direction
            second = shared + direction
        bridge = audit.create_bridge_candidate(
            f"{part_name}__broad_bridge_candidate_{component_index}",
            first,
            second,
            diameter_mm,
            overlap_mm,
        )
        bridges.append(bridge)
        records.append(
            {
                "primary_component": primary.name,
                "target_component": component.name,
                "contact_type": contact_type,
                "raw_closest_distance_mm": round(distance, 6),
                "candidate_axis_first_head_mm": [
                    round(value, 3) for value in first
                ],
                "candidate_axis_second_head_mm": [
                    round(value, 3) for value in second
                ],
                "candidate_bridge_diameter_mm": diameter_mm,
                "candidate_end_overlap_mm": overlap_mm,
                "candidate_bridge_length_mm": round(
                    (second - first).length + 2.0 * overlap_mm,
                    3,
                ),
            }
        )
    return bridges, records


def selected_object(suffix: str) -> bpy.types.Object:
    name = f"{PREFIX}__{suffix}"
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise KeyError(
            f"{name} not found; load the Gate 9 comparison BLEND first"
        )
    return obj


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    for obj in bpy.data.objects:
        obj.hide_render = True
        obj.hide_viewport = True

    component_objects: dict[str, list[bpy.types.Object]] = {}
    bridge_objects: dict[str, list[bpy.types.Object]] = {}
    report_parts: dict[str, Any] = {}
    for part in audit.BODY_PARTS:
        duplicate = duplicate_object(
            selected_object(part), f"audit_v2__{part}"
        )
        components = audit.split_loose_parts(duplicate, part)
        bridges, bridge_records = bridge_candidates_from_primary(
            part,
            components,
            args.candidate_bridge_diameter_mm,
            args.candidate_end_overlap_mm,
        )
        component_objects[part] = components
        bridge_objects[part] = bridges
        report_parts[part] = {
            "component_count": len(components),
            "components": [
                audit.object_component_stats(component)
                for component in components
            ],
            "broad_bridge_candidates": bridge_records,
        }

    cassette = duplicate_object(
        selected_object("rear_cassette"), "audit_v2__rear_cassette"
    )
    cassette.color = (0.54, 0.58, 0.64, 1.0)
    metal_suffixes = (
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
    metal = {
        suffix: duplicate_object(
            selected_object(suffix), f"audit_v2__{suffix}"
        )
        for suffix in metal_suffixes
    }
    for obj in metal.values():
        obj.color = (0.72, 0.74, 0.78, 1.0)

    for part, bridges in bridge_objects.items():
        collision_records = []
        for bridge in bridges:
            collision_records.append(
                {
                    "bridge": bridge.name,
                    "cassette": comparison.collision_record(
                        bridge, cassette
                    ),
                    "metal_envelopes": {
                        name: comparison.collision_record(
                            bridge, envelope
                        )
                        for name, envelope in metal.items()
                    },
                }
            )
        report_parts[part]["candidate_keepout_collisions"] = (
            collision_records
        )

    camera = audit.configure_workbench_render()
    all_review_objects = [
        *[
            obj
            for objects in component_objects.values()
            for obj in objects
        ],
        *[
            obj for objects in bridge_objects.values() for obj in objects
        ],
        cassette,
        *metal.values(),
    ]
    for part in audit.BODY_PARTS:
        audit.render_part(
            part,
            [*component_objects[part], *bridge_objects[part]],
            all_review_objects,
            output_dir,
            camera,
        )
    for obj in all_review_objects:
        obj.hide_render = False
        obj.hide_viewport = False
    bpy.ops.wm.save_as_mainfile(
        filepath=str(
            output_dir
            / "gate9-selected-bridge-site-audit-v2.blend"
        )
    )

    report = {
        "status": "review_only_pre_export_topology_bridge_audit",
        "selected_variant": "rear_cassette_full_scale",
        "source_topology": (
            "pre-export Blender objects; coincident coordinates are not "
            "welded as STL import would weld them"
        ),
        "candidate_bridge_policy": {
            "diameter_mm": args.candidate_bridge_diameter_mm,
            "end_overlap_mm": args.candidate_end_overlap_mm,
            "meaning": "visual/collision envelope only; not approved production geometry",
        },
        "parts": report_parts,
        "acceptance_holds": [
            "coincident point or edge contact is structurally rejected even if STL import or a slicer reports one object",
            "candidate cylinders are bridge-site markers, not final rib geometry",
            "final ribs must be broad, inboard, gusseted, boolean-unioned, and clear every keep-out",
            "every released part must be one closed manifold component before STL export",
        ],
    }
    report_path = output_dir / "gate9-selected-bridge-site-audit-v2.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "parts": {
                    part: {
                        "component_count": value["component_count"],
                        "bridge_candidates": value[
                            "broad_bridge_candidates"
                        ],
                        "cassette_collision_count": sum(
                            1
                            for record in value[
                                "candidate_keepout_collisions"
                            ]
                            if record["cassette"]["intersects"]
                        ),
                        "metal_envelope_collision_count": sum(
                            1
                            for record in value[
                                "candidate_keepout_collisions"
                            ]
                            for collision in record[
                                "metal_envelopes"
                            ].values()
                            if collision["intersects"]
                        ),
                    }
                    for part, value in report_parts.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
