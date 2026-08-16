#!/usr/bin/env python3
"""Read-only exact-topology audit for the approved V17/V9 skin repair.

This diagnostic never writes CAD.  It reports the local OCCT topology around
the frozen host face and penetrating edge so the subsequent mutation can be
limited to the smallest possible split-and-weld operation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import FreeCAD as App
import Part


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--host-face", type=int, default=587)
    parser.add_argument("--edge", type=int, default=1278)
    return parser.parse_args()


def point(value: App.Vector) -> list[float]:
    return [round(float(value.x), 12), round(float(value.y), 12), round(float(value.z), 12)]


def edge_record(shape, index: int, target: App.Vector) -> dict[str, object]:
    edge = shape.Edges[index - 1]
    return {
        "edge": index,
        "length_mm": float(edge.Length),
        "curve_type": type(edge.Curve).__name__,
        "endpoints_mm": [point(vertex.Point) for vertex in edge.Vertexes],
        "target_distance_mm": float(Part.Vertex(target).distToShape(edge)[0]),
    }


def face_record(shape, index: int) -> dict[str, object]:
    face = shape.Faces[index - 1]
    nodes, triangles = face.tessellate(0.001)
    global_edges = [
        edge_index
        for edge_index, source_edge in enumerate(shape.Edges, start=1)
        if any(source_edge.isSame(local_edge) for local_edge in face.Edges)
    ]
    return {
        "face": index,
        "surface_type": type(face.Surface).__name__,
        "area_mm2": float(face.Area),
        "vertices_mm": [point(vertex.Point) for vertex in face.Vertexes],
        "global_edges": global_edges,
        "tessellation_nodes_mm": [point(node) for node in nodes],
        "tessellation_triangles_zero_based": [list(triangle) for triangle in triangles],
    }


def main() -> int:
    args = parse_args()
    shape = Part.read(str(args.source))
    if shape.isNull():
        raise RuntimeError("source STEP imported as a null shape")

    host = shape.Faces[args.host_face - 1]
    penetrating = shape.Edges[args.edge - 1]
    target = penetrating.Vertexes[1].Point
    host_global_edges = [
        index
        for index, candidate in enumerate(shape.Edges, start=1)
        if any(candidate.isSame(local) for local in host.Edges)
    ]
    edge_owner_faces = [
        index
        for index, face in enumerate(shape.Faces, start=1)
        if any(candidate.isSame(penetrating) for candidate in face.Edges)
    ]

    target_vertices = []
    for vertex_index, vertex in enumerate(shape.Vertexes, start=1):
        distance = vertex.Point.distanceToPoint(target)
        if distance <= 1.0e-6:
            target_vertices.append(
                {
                    "vertex": vertex_index,
                    "distance_mm": float(distance),
                    "same_as_penetrating_endpoint": bool(
                        vertex.isSame(penetrating.Vertexes[1])
                    ),
                    "incident_edges": [
                        edge_index
                        for edge_index, edge in enumerate(shape.Edges, start=1)
                        if any(candidate.isSame(vertex) for candidate in edge.Vertexes)
                    ],
                    "incident_faces": [
                        face_index
                        for face_index, face in enumerate(shape.Faces, start=1)
                        if any(candidate.isSame(vertex) for candidate in face.Vertexes)
                    ],
                }
            )

    incident_faces: dict[str, list[int]] = {}
    for edge_index in host_global_edges:
        source_edge = shape.Edges[edge_index - 1]
        incident_faces[str(edge_index)] = [
            face_index
            for face_index, face in enumerate(shape.Faces, start=1)
            if any(candidate.isSame(source_edge) for candidate in face.Edges)
        ]

    report = {
        "status": "PASS__READ_ONLY_TOPOLOGY_AUDIT",
        "source": str(args.source),
        "source_valid": bool(shape.isValid()),
        "source_closed": bool(shape.isClosed()),
        "source_solids": len(shape.Solids),
        "host_face": args.host_face,
        "host_surface_type": type(host.Surface).__name__,
        "host_area_mm2": float(host.Area),
        "host_wires": len(host.Wires),
        "host_vertices_mm": [point(vertex.Point) for vertex in host.Vertexes],
        "host_global_edges": host_global_edges,
        "host_edge_records": [edge_record(shape, index, target) for index in host_global_edges],
        "host_edge_incident_faces": incident_faces,
        "local_face_records": [face_record(shape, index) for index in (263, 400, 581, 582, 587)],
        "penetrating_edge": edge_record(shape, args.edge, target),
        "penetrating_edge_owner_faces": edge_owner_faces,
        "intersection_target_mm": point(target),
        "coincident_target_vertices": target_vertices,
        "target_to_host_mm": float(Part.Vertex(target).distToShape(host)[0]),
        "edge_host_section_vertices_mm": [
            point(vertex.Point) for vertex in penetrating.section(host).Vertexes
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
