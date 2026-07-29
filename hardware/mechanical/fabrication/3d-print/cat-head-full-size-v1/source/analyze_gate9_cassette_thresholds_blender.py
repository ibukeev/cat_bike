#!/usr/bin/env python3
"""Compare Gate 9 rear-cassette thresholds using generated shell topology."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "cassette-threshold-topology.json"
)
THRESHOLDS_MM = (
    -25.0,
    -35.0,
    -45.0,
    -50.0,
    -55.0,
    -60.0,
    -65.0,
    -70.0,
    -75.0,
    -80.0,
    -85.0,
    -90.0,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args)


def component_sizes(obj: bpy.types.Object) -> list[dict[str, int]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    vertex_neighbors: dict[int, set[int]] = defaultdict(set)
    vertex_faces: dict[int, set[int]] = defaultdict(set)
    for edge in bm.edges:
        first, second = edge.verts[0].index, edge.verts[1].index
        vertex_neighbors[first].add(second)
        vertex_neighbors[second].add(first)
    for face in bm.faces:
        for vertex in face.verts:
            vertex_faces[vertex.index].add(face.index)
    remaining = set(range(len(bm.verts)))
    result: list[dict[str, int]] = []
    while remaining:
        start = remaining.pop()
        queue = deque([start])
        vertices = {start}
        faces: set[int] = set()
        while queue:
            current = queue.popleft()
            faces.update(vertex_faces[current])
            for neighbor in vertex_neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    vertices.add(neighbor)
                    queue.append(neighbor)
        result.append(
            {
                "vertex_count": len(vertices),
                "face_count": len(faces),
            }
        )
    bm.free()
    return sorted(result, key=lambda item: item["face_count"], reverse=True)


def delete_object(obj: bpy.types.Object) -> None:
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    gate2_config = json.loads(
        (REPO_ROOT / config["source_gate2_config"]).read_text(
            encoding="utf-8"
        )
    )
    gate1_config = json.loads(
        gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
    )
    source_model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source_model,
        gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV),
    )
    source_scale, source_origin, _ = gate1.make_transform(
        gate1.bounds(source_model.vertices),
        float(gate1_config["target_height_mm"]),
    )
    roles, _ = gate1.build_roles(units, gate1_config, source_scale)
    model = gate2.subdivide_center_panels(source_model, gate2_config)
    assignments = gate2.assign_faces(
        model.faces,
        model.vertices,
        roles,
        gate2_config,
        source_scale,
        source_origin,
    )
    transformed_points = [
        gate1.transform_point(vertex, source_scale, source_origin)
        for vertex in model.vertices
    ]
    shell_config = config["shell"]
    scale_center = Vector(
        interface["rear_interface_plane"]["center_head_mm"]
    )

    gate3.clean_scene()
    material = comparison.create_material(
        "threshold_audit", "#4A91DB"
    )
    expected_components = {
        "right_upper_head": 1,
        "left_upper_head": 1,
        "right_lower_face": 2,
        "left_lower_face": 2,
        "rear_cassette": 1,
    }
    records: list[dict[str, Any]] = []
    for threshold in THRESHOLDS_MM:
        cassette_faces = comparison.selected_cassette_faces(
            model,
            assignments,
            transformed_points,
            interface,
            threshold,
        )
        part_records: dict[str, Any] = {}
        objects: list[bpy.types.Object] = []
        for section in comparison.BODY_SECTIONS:
            face_indices = [
                index
                for index, assignment in enumerate(assignments)
                if assignment == section and index not in cassette_faces
            ]
            source_faces = [
                model.faces[index].indices for index in face_indices
            ]
            source_faces.extend(
                tuple(face)
                for face in shell_config.get(
                    "bottom_closure_faces", {}
                ).get(section, [])
            )
            obj = comparison.create_shell_object(
                f"threshold_{abs(int(threshold))}__{section}",
                source_faces,
                model,
                source_scale,
                source_origin,
                1.0,
                scale_center,
                material,
                shell_config,
            )
            objects.append(obj)
            stats = comparison.object_stats(
                obj,
                shell_config["printer_envelope_mm"],
                int(shell_config["orientation_step_degrees"]),
            )
            stats["component_sizes"] = component_sizes(obj)
            part_records[section] = stats
        cassette = comparison.create_shell_object(
            f"threshold_{abs(int(threshold))}__rear_cassette",
            [model.faces[index].indices for index in cassette_faces],
            model,
            source_scale,
            source_origin,
            1.0,
            scale_center,
            material,
            shell_config,
        )
        objects.append(cassette)
        cassette_stats = comparison.object_stats(
            cassette,
            shell_config["printer_envelope_mm"],
            int(shell_config["orientation_step_degrees"]),
        )
        cassette_stats["component_sizes"] = component_sizes(cassette)
        part_records["rear_cassette"] = cassette_stats
        panels = sorted(
            {
                gate1.canonical_source_panel_id(
                    model.faces[index].group
                )
                for index in cassette_faces
            }
        )
        topology_pass = all(
            int(part_records[part]["connected_components"]) == expected
            and int(part_records[part]["boundary_edges"]) == 0
            and int(part_records[part]["nonmanifold_edges"]) == 0
            for part, expected in expected_components.items()
        )
        records.append(
            {
                "threshold_mm": threshold,
                "cassette_source_face_count": len(cassette_faces),
                "cassette_panel_ids": panels,
                "topology_pass": topology_pass,
                "parts": part_records,
            }
        )
        for obj in objects:
            delete_object(obj)

    report = {
        "status": "review_only",
        "interface_revision": interface["interface_revision"],
        "expected_connected_components": expected_components,
        "thresholds": records,
        "passing_thresholds_mm": [
            record["threshold_mm"]
            for record in records
            if record["topology_pass"]
        ],
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passing_thresholds_mm": report[
                    "passing_thresholds_mm"
                ],
                "summary": [
                    {
                        "threshold_mm": record["threshold_mm"],
                        "faces": record["cassette_source_face_count"],
                        "topology_pass": record["topology_pass"],
                        "components": {
                            part: stats["connected_components"]
                            for part, stats in record["parts"].items()
                        },
                        "lower_dimensions_mm": record["parts"][
                            "left_lower_face"
                        ]["dimensions_mm"],
                        "cassette_dimensions_mm": record["parts"][
                            "rear_cassette"
                        ]["dimensions_mm"],
                    }
                    for record in records
                ],
                "report": str(output_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
