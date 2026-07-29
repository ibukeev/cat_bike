#!/usr/bin/env python3
"""Audit source-facet candidates for a rear-loaded Gate 9 cassette seam."""

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


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
GATE2_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
INTERFACE_PATH = (
    REPO_ROOT
    / "hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v03.json"
)
MAIN_SECTIONS = {
    "left_lower_face",
    "right_lower_face",
    "left_upper_head",
    "right_upper_head",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--thresholds-mm",
        nargs="+",
        type=float,
        default=[-15.0, -25.0, -35.0, -45.0, -55.0, -65.0],
        help="Rear-plane signed-distance thresholds for cassette ownership.",
    )
    return parser.parse_args()


def face_neighbors(faces: list[gate1.ObjFace]) -> dict[int, set[int]]:
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    neighbors = {index: set() for index in range(len(faces))}
    for sharing in edge_faces.values():
        for first in sharing:
            neighbors[first].update(second for second in sharing if second != first)
    return neighbors


def component_count(selected: set[int], neighbors: dict[int, set[int]]) -> int:
    remaining = set(selected)
    count = 0
    while remaining:
        count += 1
        start = remaining.pop()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    return count


def main() -> None:
    args = parse_args()
    gate2_config = json.loads(GATE2_CONFIG.read_text(encoding="utf-8"))
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    interface = json.loads(INTERFACE_PATH.read_text(encoding="utf-8"))
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    )
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices), float(gate1_config["target_height_mm"])
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
    assignments = gate2.assign_faces(
        model.faces, model.vertices, roles, gate2_config, scale, origin
    )
    transformed = [
        gate1.transform_point(vertex, scale, origin) for vertex in model.vertices
    ]
    plane = interface["rear_interface_plane"]
    center = plane["center_head_mm"]
    normal = plane["outward_normal_head"]

    def signed_distance(point: tuple[float, float, float]) -> float:
        return sum((point[index] - center[index]) * normal[index] for index in range(3))

    records: list[dict[str, Any]] = []
    for face_index, (face, assignment) in enumerate(zip(model.faces, assignments)):
        if assignment not in MAIN_SECTIONS:
            continue
        points = [transformed[index] for index in face.indices]
        distances = [signed_distance(point) for point in points]
        centroid = tuple(
            sum(point[axis] for point in points) / len(points) for axis in range(3)
        )
        records.append(
            {
                "face_index": face_index,
                "panel_id": gate1.canonical_source_panel_id(face.group),
                "section": assignment,
                "centroid_head_mm": [round(value, 3) for value in centroid],
                "rear_plane_distance_centroid_mm": round(signed_distance(centroid), 3),
                "rear_plane_distance_min_mm": round(min(distances), 3),
                "rear_plane_distance_max_mm": round(max(distances), 3),
            }
        )

    neighbors = face_neighbors(model.faces)
    candidates = []
    for threshold in args.thresholds_mm:
        cassette = {
            record["face_index"]
            for record in records
            if record["rear_plane_distance_centroid_mm"] >= threshold
        }
        remaining_components = {}
        for section in sorted(MAIN_SECTIONS):
            selected = {
                record["face_index"]
                for record in records
                if record["section"] == section
                and record["face_index"] not in cassette
            }
            remaining_components[section] = component_count(selected, neighbors)
        candidates.append(
            {
                "threshold_mm": threshold,
                "cassette_face_count": len(cassette),
                "cassette_component_count": component_count(cassette, neighbors),
                "cassette_panel_ids": sorted(
                    {
                        record["panel_id"]
                        for record in records
                        if record["face_index"] in cassette
                    }
                ),
                "remaining_section_component_counts": remaining_components,
            }
        )

    report = {
        "status": "review_only",
        "interface_revision": interface["interface_revision"],
        "selection_rule": "whole source faces whose centroid signed distance from the rear interface plane is at least the candidate threshold",
        "rear_plane": plane,
        "faces_rear_to_front": sorted(
            records,
            key=lambda record: record["rear_plane_distance_centroid_mm"],
            reverse=True,
        ),
        "threshold_candidates": candidates,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
