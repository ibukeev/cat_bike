#!/usr/bin/env python3
"""Create the isolated V13 topology-only repair for lower-face component 001."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/right-lower-face-topology-repair-review-v13.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
            "nonmanifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        }
    finally:
        bm.free()


def bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


def self_intersection_count(obj: bpy.types.Object) -> int:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        tree = BVHTree.FromBMesh(bm, epsilon=0.0)
        pairs: set[tuple[int, int]] = set()
        for first_index, second_index in tree.overlap(tree):
            if first_index == second_index:
                continue
            pair = tuple(sorted((first_index, second_index)))
            if pair in pairs:
                continue
            first = bm.faces[pair[0]]
            second = bm.faces[pair[1]]
            if {vertex.index for vertex in first.verts} & {
                vertex.index for vertex in second.verts
            }:
                continue
            pairs.add(pair)
        return len(pairs)
    finally:
        bm.free()


def maximum_candidate_to_source_surface_deviation(
    candidate: bpy.types.Object,
    source: bpy.types.Object,
) -> float:
    source_coordinates = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    source_polygons = [tuple(polygon.vertices) for polygon in source.data.polygons]
    source_tree = BVHTree.FromPolygons(source_coordinates, source_polygons, all_triangles=True)
    source_face_coordinate_sets = {
        frozenset(tuple(source.matrix_world @ source.data.vertices[index].co) for index in polygon.vertices)
        for polygon in source.data.polygons
    }
    distances: list[float] = []
    for polygon in candidate.data.polygons:
        coordinates = [
            candidate.matrix_world @ candidate.data.vertices[index].co
            for index in polygon.vertices
        ]
        if frozenset(tuple(coordinate) for coordinate in coordinates) in source_face_coordinate_sets:
            distances.extend(0.0 for _ in range(len(coordinates) + 1))
            continue
        samples = coordinates + [sum(coordinates, Vector()) / len(coordinates)]
        for point in samples:
            nearest = source_tree.find_nearest(point)
            if nearest is None:
                raise RuntimeError("Surface-deviation query failed")
            distances.append(float(nearest[3]))
    return max(distances, default=0.0)


def manifold_face_regions(bm: bmesh.types.BMesh) -> list[list[int]]:
    bm.faces.ensure_lookup_table()
    adjacency = {face.index: set() for face in bm.faces}
    for edge in bm.edges:
        if len(edge.link_faces) != 2:
            continue
        first, second = (face.index for face in edge.link_faces)
        adjacency[first].add(second)
        adjacency[second].add(first)
    assigned: dict[int, int] = {}
    regions: list[list[int]] = []
    for face in bm.faces:
        if face.index in assigned:
            continue
        region_index = len(regions)
        stack = [face.index]
        members: list[int] = []
        while stack:
            face_index = stack.pop()
            if face_index in assigned:
                continue
            assigned[face_index] = region_index
            members.append(face_index)
            stack.extend(adjacency[face_index] - assigned.keys())
        regions.append(members)
    return regions


def make_removed_region_evidence(
    candidate: bpy.types.Object,
    bm: bmesh.types.BMesh,
    removed_face_indices: set[int],
) -> bpy.types.Object:
    coordinates: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for face_index in sorted(removed_face_indices):
        face = bm.faces[face_index]
        start = len(coordinates)
        coordinates.extend(tuple(vertex.co) for vertex in face.verts)
        faces.append(tuple(range(start, start + len(face.verts))))
    mesh = bpy.data.meshes.new("REVIEW_ONLY__REMOVED_INTERNAL_REGIONS_V13_MESH")
    mesh.from_pydata(coordinates, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("REVIEW_ONLY__REMOVED_INTERNAL_REGIONS_V13", mesh)
    obj.matrix_world = candidate.matrix_world.copy()
    bpy.context.scene.collection.objects.link(obj)
    material = bpy.data.materials.new("REVIEW_ONLY__REMOVED_INTERNAL_RED_V13")
    material.diffuse_color = (0.9, 0.03, 0.03, 1.0)
    obj.data.materials.append(material)
    obj.hide_render = True
    obj.hide_viewport = True
    return obj


def main() -> None:
    config_path = parse_args().config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = config["locked_contract"]
    source_path = repo_path(config["source_component_obj"])
    output_dir = repo_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256(source_path) != config["source_component_sha256"]:
        raise RuntimeError("Frozen component 001 OBJ SHA-256 changed")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(source_path))
    source = bpy.context.selected_objects[0]
    source.name = "FROZEN__RIGHT_LOWER_FACE__COMPONENT_001_V13"
    # Freeze Blender's OBJ axis conversion into the mesh before copying it.
    # Otherwise the Boolean result and the frozen reference can acquire
    # different object transforms even though their local coordinates match.
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    source_topology = topology(source)
    if source_topology["vertices"] != int(contract["source_vertex_count"]):
        raise RuntimeError(f"Unexpected source vertex count: {source_topology}")

    candidate = source.copy()
    candidate.data = source.data.copy()
    candidate.name = "PROPOSED__RIGHT_LOWER_FACE__COMPONENT_001_TOPOLOGY_REPAIRED_V13"
    bpy.context.scene.collection.objects.link(candidate)
    empty_mesh = bpy.data.meshes.new("TOOL__EMPTY_EXACT_SELF_CLEAN_V13_MESH")
    empty_tool = bpy.data.objects.new("TOOL__EMPTY_EXACT_SELF_CLEAN_V13", empty_mesh)
    bpy.context.scene.collection.objects.link(empty_tool)
    bpy.context.view_layer.objects.active = candidate
    candidate.select_set(True)
    modifier = candidate.modifiers.new("EXACT_SELF_REPARTITION_V13", "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = empty_tool
    modifier.use_self = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(empty_tool, do_unlink=True)

    bm = bmesh.new()
    bm.from_mesh(candidate.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    regions = manifold_face_regions(bm)
    region_face_counts = [len(region) for region in regions]
    expected_counts = sorted(contract["expected_exact_union_region_face_counts"])
    if sorted(region_face_counts) != expected_counts:
        raise RuntimeError(
            f"Exact-union region contract changed: {region_face_counts} != {expected_counts}"
        )
    keep_region = max(range(len(regions)), key=lambda index: len(regions[index]))
    removed_face_indices = {
        face_index
        for region_index, region in enumerate(regions)
        if region_index != keep_region
        for face_index in region
    }
    if len(removed_face_indices) != int(
        contract["expected_removed_internal_region_face_count"]
    ):
        raise RuntimeError("Unexpected internal-region face count")
    removed_evidence = make_removed_region_evidence(candidate, bm, removed_face_indices)
    bmesh.ops.delete(
        bm,
        geom=[bm.faces[index] for index in sorted(removed_face_indices)],
        context="FACES",
    )
    bmesh.ops.delete(
        bm,
        geom=[vertex for vertex in bm.verts if not vertex.link_faces],
        context="VERTS",
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(candidate.data)
    bm.free()
    candidate.data.update(calc_edges=True)
    snap_candidate_vertex = int(contract["boolean_only_snap_candidate_vertex"])
    snap_source_vertex = int(contract["boolean_only_snap_source_vertex"])
    snap_distance = (
        candidate.data.vertices[snap_candidate_vertex].co
        - source.data.vertices[snap_source_vertex].co
    ).length
    if snap_distance > float(contract["maximum_boolean_only_snap_distance_mm"]):
        raise RuntimeError(f"Boolean-only corner snap exceeds contract: {snap_distance}")
    candidate.data.vertices[snap_candidate_vertex].co = source.data.vertices[
        snap_source_vertex
    ].co.copy()
    candidate.data.update(calc_edges=True)
    bpy.context.view_layer.update()

    source_bounds = bounds(source)
    candidate_bounds = bounds(candidate)
    bbox_deviation = max(
        abs(source_bounds[key][axis] - candidate_bounds[key][axis])
        for key in ("min", "max")
        for axis in range(3)
    )
    surface_deviation = maximum_candidate_to_source_surface_deviation(candidate, source)
    candidate_topology = topology(candidate)
    candidate_intersections = self_intersection_count(candidate)
    expected_topology = {
        "vertices": int(contract["expected_candidate_vertex_count"]),
        "edges": int(contract["expected_candidate_edge_count"]),
        "faces": int(contract["expected_candidate_face_count"]),
        "boundary_edges": int(contract["required_boundary_edges"]),
        "nonmanifold_edges": int(contract["required_nonmanifold_edges"]),
    }
    passed = (
        candidate_topology == expected_topology
        and candidate_intersections == int(contract["required_self_intersections"])
        and surface_deviation
        <= float(contract["maximum_candidate_to_source_surface_deviation_mm"])
        and bbox_deviation <= float(contract["maximum_bbox_deviation_mm"])
    )
    result = {
        "status": "PASS_BLENDER_ISOLATED" if passed else "FAIL",
        "scope": "component 001 only; no other component or interface changed",
        "source": str(source_path.relative_to(REPO_ROOT)),
        "source_sha256": sha256(source_path),
        "source_topology": source_topology,
        "mapped_source_intersections": contract["mapped_source_intersections"],
        "mapped_legacy_face_pairs": contract["mapped_legacy_face_pairs"],
        "exact_union_region_face_counts": region_face_counts,
        "kept_region_index": keep_region,
        "removed_internal_region_face_count": len(removed_face_indices),
        "boolean_only_snap_candidate_vertex": snap_candidate_vertex,
        "boolean_only_snap_source_vertex": snap_source_vertex,
        "boolean_only_snap_distance_mm": snap_distance,
        "candidate_topology": candidate_topology,
        "candidate_self_intersections": candidate_intersections,
        "maximum_candidate_to_source_surface_deviation_mm": surface_deviation,
        "maximum_bbox_deviation_mm": bbox_deviation,
        "source_bounds": source_bounds,
        "candidate_bounds": candidate_bounds,
        "production_union_performed": False,
        "owner_integration_performed": False,
        "mirror_performed": False,
    }
    validation_path = output_dir / "validation-v13.json"

    source.hide_viewport = True
    source.hide_render = True
    removed_evidence.hide_viewport = True
    removed_evidence.hide_render = True
    candidate.hide_viewport = False
    candidate.hide_render = False
    candidate_material = bpy.data.materials.new("PROPOSED__TOPOLOGY_REPAIRED_BLUE_V13")
    candidate_material.diffuse_color = (0.08, 0.38, 0.78, 1.0)
    candidate.data.materials.append(candidate_material)
    blend_path = output_dir / "CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    candidate.select_set(True)
    bpy.context.view_layer.objects.active = candidate
    obj_path = output_dir / "right_lower_face_component_001_topology_repaired_v13.obj"
    bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
    result["proposal_blend"] = str(blend_path.relative_to(REPO_ROOT))
    result["proposal_obj"] = str(obj_path.relative_to(REPO_ROOT))
    result["proposal_obj_sha256"] = sha256(obj_path)
    validation_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not passed:
        raise RuntimeError("V13 topology-only proposal failed locked Blender gates")


if __name__ == "__main__":
    main()
