#!/usr/bin/env python3
"""Read-only exact-topology audit for the isolated V17 outer-root crossing.

The hash-pinned repaired V2 STEP is inspected without saving or mutating any
document.  The report exposes the exact vertices, global edges, incident
faces, and intersection section for the localized Face72/Face489 pair so a
subsequent repair contract can be limited to the smallest possible rewiring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--first-face", type=int, default=72)
    parser.add_argument("--second-face", type=int, default=489)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def point(value: App.Vector) -> list[float]:
    return [round(float(value.x), 12), round(float(value.y), 12), round(float(value.z), 12)]


def global_edge_indices(shape, face) -> list[int]:
    return [
        index
        for index, source_edge in enumerate(shape.Edges, start=1)
        if any(source_edge.isSame(local_edge) for local_edge in face.Edges)
    ]


def global_vertex_indices(shape, face) -> list[int]:
    return [
        index
        for index, source_vertex in enumerate(shape.Vertexes, start=1)
        if any(source_vertex.isSame(local_vertex) for local_vertex in face.Vertexes)
    ]


def incident_face_indices(shape, edge) -> list[int]:
    return [
        index
        for index, face in enumerate(shape.Faces, start=1)
        if any(candidate.isSame(edge) for candidate in face.Edges)
    ]


def edge_record(shape, index: int) -> dict[str, object]:
    edge = shape.Edges[index - 1]
    return {
        "edge": index,
        "curve_type": type(edge.Curve).__name__,
        "length_mm": float(edge.Length),
        "endpoints_mm": [point(vertex.Point) for vertex in edge.Vertexes],
        "incident_faces": incident_face_indices(shape, edge),
    }


def face_record(shape, index: int) -> dict[str, object]:
    face = shape.Faces[index - 1]
    nodes, triangles = face.tessellate(0.001)
    edge_indices = global_edge_indices(shape, face)
    return {
        "face": index,
        "surface_type": type(face.Surface).__name__,
        "area_mm2": float(face.Area),
        "center_of_mass_mm": point(face.CenterOfMass),
        "wire_count": len(face.Wires),
        "global_vertices": global_vertex_indices(shape, face),
        "vertices_mm": [point(vertex.Point) for vertex in face.Vertexes],
        "global_edges": edge_indices,
        "edges": [edge_record(shape, edge_index) for edge_index in edge_indices],
        "tessellation_nodes_mm": [point(node) for node in nodes],
        "tessellation_triangles_zero_based": [list(triangle) for triangle in triangles],
        "normal": point(face.normalAt(0.5, 0.5)),
    }


def unique_points(shapes) -> list[list[float]]:
    coordinates: set[tuple[float, float, float]] = set()
    for shape in shapes:
        for vertex in shape.Vertexes:
            coordinates.add(tuple(point(vertex.Point)))
    return [list(values) for values in sorted(coordinates)]


def vertex_to_edge_records(shape, vertex, edge_indices: list[int]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for edge_index in edge_indices:
        edge = shape.Edges[edge_index - 1]
        distance, closest_pairs, _ = vertex.distToShape(edge)
        records.append(
            {
                "edge": edge_index,
                "distance_mm": float(distance),
                "vertex_mm": point(vertex.Point),
                "closest_pairs_mm": [
                    [point(first_point), point(second_point)]
                    for first_point, second_point in closest_pairs
                ],
            }
        )
    return records


def main() -> int:
    args = parse_args()
    source_hash = sha256_file(args.source)
    if source_hash != args.expected_sha256:
        raise RuntimeError(
            f"source SHA-256 mismatch: expected {args.expected_sha256}, got {source_hash}"
        )

    shape = Part.read(str(args.source))
    if shape.isNull():
        raise RuntimeError("source STEP imported as a null shape")
    if max(args.first_face, args.second_face) > len(shape.Faces):
        raise RuntimeError("requested face index is outside the source shape")

    first = shape.Faces[args.first_face - 1]
    second = shape.Faces[args.second_face - 1]
    first_edges = global_edge_indices(shape, first)
    second_edges = global_edge_indices(shape, second)
    local_face_indices = sorted(
        {
            args.first_face,
            args.second_face,
            *(
                face_index
                for edge_index in (*first_edges, *second_edges)
                for face_index in incident_face_indices(shape, shape.Edges[edge_index - 1])
            ),
        }
    )

    section = first.section(second)
    common = first.common(second)
    second_vertex_to_first_edges = [
        record
        for vertex in second.Vertexes
        for record in vertex_to_edge_records(shape, vertex, first_edges)
    ]
    nearest_second_vertex_to_first_edge = min(
        second_vertex_to_first_edges, key=lambda record: record["distance_mm"]
    )
    report = {
        "status": "PASS__READ_ONLY_OUTER_ROOT_TOPOLOGY_AUDIT",
        "source": str(args.source),
        "source_sha256": source_hash,
        "source_valid": bool(shape.isValid()),
        "source_closed": bool(shape.isClosed()),
        "source_solid_count": len(shape.Solids),
        "source_face_count": len(shape.Faces),
        "pair": [args.first_face, args.second_face],
        "distance_mm": float(first.distToShape(second)[0]),
        "common_area_mm2": float(common.Area),
        "common_length_mm": float(common.Length),
        "shared_topological_vertices": sum(
            any(first_vertex.isSame(second_vertex) for second_vertex in second.Vertexes)
            for first_vertex in first.Vertexes
        ),
        "shared_coordinate_vertices": sum(
            any(
                first_vertex.Point.distanceToPoint(second_vertex.Point) <= 1.0e-7
                for second_vertex in second.Vertexes
            )
            for first_vertex in first.Vertexes
        ),
        "intersection_section": {
            "vertex_count": len(section.Vertexes),
            "edge_count": len(section.Edges),
            "length_mm": float(section.Length),
            "vertices_mm": [point(vertex.Point) for vertex in section.Vertexes],
            "edge_endpoints_mm": [
                [point(vertex.Point) for vertex in edge.Vertexes] for edge in section.Edges
            ],
        },
        "second_vertex_to_first_edges": second_vertex_to_first_edges,
        "nearest_second_vertex_to_first_edge": nearest_second_vertex_to_first_edge,
        "pair_faces": [
            face_record(shape, args.first_face),
            face_record(shape, args.second_face),
        ],
        "local_face_indices": local_face_indices,
        "local_face_records": [face_record(shape, index) for index in local_face_indices],
        "geometry_mutated": False,
        "source_document_saved": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
