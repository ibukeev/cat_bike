#!/usr/bin/env python3
"""Trace disconnected Gate 9 body sections through source-face adjacency.

This is a review-only diagnostic.  It works on the pre-solidify source facets
so STL coordinate welding and independently solidified closure plates cannot
hide the actual section topology.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT
    / "output/gate9-selected-face-adjacency"
    / "gate9-selected-face-adjacency.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def face_neighbors(
    faces: list[gate1.ObjFace],
) -> tuple[dict[int, set[int]], dict[tuple[int, int], list[int]]]:
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    neighbors = {index: set() for index in range(len(faces))}
    for sharing in edge_faces.values():
        for first in sharing:
            neighbors[first].update(
                second for second in sharing if second != first
            )
    return neighbors, edge_faces


def connected_components(
    selected: set[int], neighbors: dict[int, set[int]]
) -> list[set[int]]:
    remaining = set(selected)
    result: list[set[int]] = []
    while remaining:
        start = remaining.pop()
        component = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        result.append(component)
    return sorted(result, key=len, reverse=True)


def shortest_face_path(
    first: set[int],
    second: set[int],
    neighbors: dict[int, set[int]],
) -> list[int]:
    """Return a minimum-edge face path between two selected components."""
    queue = deque(sorted(first))
    previous: dict[int, int | None] = {face: None for face in first}
    target: int | None = None
    while queue:
        current = queue.popleft()
        if current in second:
            target = current
            break
        for neighbor in sorted(neighbors[current]):
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)
    if target is None:
        return []
    path = [target]
    while previous[path[-1]] is not None:
        path.append(previous[path[-1]])  # type: ignore[arg-type]
    path.reverse()
    return path


def face_record(
    face_index: int,
    model: gate1.ObjModel,
    assignments: list[str],
    transformed: list[tuple[float, float, float]],
    cassette_faces: set[int],
) -> dict[str, Any]:
    face = model.faces[face_index]
    points = [transformed[index] for index in face.indices]
    centroid = [
        sum(point[axis] for point in points) / len(points)
        for axis in range(3)
    ]
    return {
        "face_index": face_index,
        "source_panel_id": gate1.canonical_source_panel_id(face.group),
        "assigned_section": assignments[face_index],
        "owned_by_rear_cassette": face_index in cassette_faces,
        "vertex_indices": list(face.indices),
        "centroid_head_mm": [round(value, 3) for value in centroid],
    }


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
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
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    )
    source_scale, source_origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices),
        float(gate1_config["target_height_mm"]),
    )
    roles, _ = gate1.build_roles(units, gate1_config, source_scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
    assignments = gate2.assign_faces(
        model.faces,
        model.vertices,
        roles,
        gate2_config,
        source_scale,
        source_origin,
    )
    transformed = [
        gate1.transform_point(vertex, source_scale, source_origin)
        for vertex in model.vertices
    ]
    threshold = float(
        config["variants"]["rear_cassette_full_scale"][
            "rear_cassette_threshold_mm"
        ]
    )
    cassette_faces = comparison.selected_cassette_faces(
        model,
        assignments,
        transformed,
        interface,
        threshold,
    )
    neighbors, _ = face_neighbors(model.faces)

    sections: dict[str, Any] = {}
    for section in comparison.BODY_SECTIONS:
        selected = {
            index
            for index, assignment in enumerate(assignments)
            if assignment == section and index not in cassette_faces
        }
        components = connected_components(selected, neighbors)
        component_records = []
        for component_index, component in enumerate(components, start=1):
            component_records.append(
                {
                    "component_index": component_index,
                    "face_count": len(component),
                    "faces": [
                        face_record(
                            index,
                            model,
                            assignments,
                            transformed,
                            cassette_faces,
                        )
                        for index in sorted(component)
                    ],
                }
            )
        paths = []
        if len(components) > 1:
            for component_index, component in enumerate(
                components[1:], start=2
            ):
                path = shortest_face_path(
                    components[0], component, neighbors
                )
                paths.append(
                    {
                        "from_component": 1,
                        "to_component": component_index,
                        "path_face_count": len(path),
                        "foreign_bridge_face_count": sum(
                            1 for index in path if index not in selected
                        ),
                        "path": [
                            face_record(
                                index,
                                model,
                                assignments,
                                transformed,
                                cassette_faces,
                            )
                            for index in path
                        ],
                    }
                )
        sections[section] = {
            "selected_source_face_count": len(selected),
            "source_edge_component_count": len(components),
            "components": component_records,
            "minimum_face_paths": paths,
            "configured_bottom_closure_faces": config["shell"].get(
                "bottom_closure_faces", {}
            ).get(section, []),
        }

    report = {
        "status": "review_only_pre_solidify_source_adjacency",
        "interface_revision": interface["interface_revision"],
        "rear_cassette_threshold_mm": threshold,
        "finding": (
            "Configured bottom-closure triangles are deliberately excluded "
            "from source-face connectivity because they are not source faces."
        ),
        "sections": sections,
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
                "status": report["status"],
                "sections": {
                    section: {
                        "source_edge_component_count": value[
                            "source_edge_component_count"
                        ],
                        "component_face_counts": [
                            component["face_count"]
                            for component in value["components"]
                        ],
                        "minimum_paths": [
                            {
                                "foreign_bridge_face_count": path[
                                    "foreign_bridge_face_count"
                                ],
                                "path": [
                                    {
                                        "face_index": face["face_index"],
                                        "section": face[
                                            "assigned_section"
                                        ],
                                        "cassette": face[
                                            "owned_by_rear_cassette"
                                        ],
                                    }
                                    for face in path["path"]
                                ],
                            }
                            for path in value["minimum_face_paths"]
                        ],
                    }
                    for section, value in sections.items()
                },
                "report": str(output_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
