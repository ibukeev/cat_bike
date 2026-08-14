#!/usr/bin/env python3
"""Read-only component audit for the rejected right lower-face eye-mount neck."""

from __future__ import annotations

import json
from collections import deque

import bpy
from mathutils import Vector


LOWER_FACE = "right_lower_face"
HEAD_FLANGE = "PROPOSED__RIGHT_LOWER_HEAD__PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7"


def world_vertices(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def main() -> None:
    lower = bpy.data.objects[LOWER_FACE]
    flange = bpy.data.objects[HEAD_FLANGE]
    vertices = world_vertices(lower)
    flange_vertices = world_vertices(flange)
    flange_center = sum(flange_vertices, Vector()) / len(flange_vertices)

    adjacency: list[set[int]] = [set() for _ in vertices]
    for edge in lower.data.edges:
        first, second = edge.vertices
        adjacency[first].add(second)
        adjacency[second].add(first)

    unseen = set(range(len(vertices)))
    components: list[dict[str, object]] = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        indices = [seed]
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
                    indices.append(neighbor)

        points = [vertices[index] for index in indices]
        low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
        high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
        closest_to_center = min((point - flange_center).length for point in points)
        closest_to_flange = min(
            (point - flange_point).length
            for point in points
            for flange_point in flange_vertices
        )
        index_set = set(indices)
        face_count = sum(
            1 for polygon in lower.data.polygons
            if all(index in index_set for index in polygon.vertices)
        )
        components.append({
            "vertex_count": len(indices),
            "face_count": face_count,
            "bbox_min_mm": [round(value, 5) for value in low],
            "bbox_max_mm": [round(value, 5) for value in high],
            "bbox_size_mm": [round(value, 5) for value in high - low],
            "minimum_vertex_distance_to_flange_mm": round(closest_to_flange, 6),
            "minimum_vertex_distance_to_flange_center_mm": round(closest_to_center, 6),
        })

    components.sort(key=lambda item: item["minimum_vertex_distance_to_flange_mm"])
    print("RIGHT_LOWER_FACE_NECK_COMPONENT_AUDIT=" + json.dumps({
        "lower_face": LOWER_FACE,
        "head_flange": HEAD_FLANGE,
        "flange_center_mm": [round(value, 5) for value in flange_center],
        "component_count": len(components),
        "components_nearest_flange": components[:20],
    }, indent=2))


if __name__ == "__main__":
    main()
