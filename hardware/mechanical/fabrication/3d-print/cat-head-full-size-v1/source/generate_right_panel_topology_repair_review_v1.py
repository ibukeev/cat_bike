#!/usr/bin/env python3
"""Create an isolated, vertex-preserving right-panel triangulation proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/right-panel-topology-repair-review-v1.json"


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


def mesh_fingerprint(obj: bpy.types.Object) -> str:
    payload = {
        "vertices": [
            [round(float(value), 9) for value in obj.matrix_world @ vertex.co]
            for vertex in obj.data.vertices
        ],
        "faces": [list(polygon.vertices) for polygon in obj.data.polygons],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def world_vertices(obj: bpy.types.Object) -> list[tuple[float, float, float]]:
    return [
        tuple(float(value) for value in obj.matrix_world @ vertex.co)
        for vertex in obj.data.vertices
    ]


def bounds(points: list[tuple[float, float, float]]) -> dict[str, list[float]]:
    return {
        "min_mm": [min(point[axis] for point in points) for axis in range(3)],
        "max_mm": [max(point[axis] for point in points) for axis in range(3)],
    }


def coordinate_signature(
    points: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    return sorted(tuple(round(value, 9) for value in point) for point in points)


def topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
        nonmanifold = sum(1 for edge in bm.edges if len(edge.link_faces) != 2)
        unseen = set(bm.faces)
        components = 0
        while unseen:
            components += 1
            stack = [unseen.pop()]
            while stack:
                face = stack.pop()
                for edge in face.edges:
                    for linked in edge.link_faces:
                        if linked in unseen:
                            unseen.remove(linked)
                            stack.append(linked)
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": boundary,
            "nonmanifold_edges": nonmanifold,
            "connected_components": components,
        }
    finally:
        bm.free()


def triangulated_world_copy(
    source: bpy.types.Object, name: str
) -> bpy.types.Object:
    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    try:
        matrix = source.matrix_world
        vertices = [matrix @ vertex.co for vertex in evaluated_mesh.vertices]
        faces = [list(polygon.vertices) for polygon in evaluated_mesh.polygons]
    finally:
        evaluated.to_mesh_clear()

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    proposal = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(proposal)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    try:
        bmesh.ops.triangulate(
            bm,
            faces=list(bm.faces),
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        bm.normal_update()
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update(calc_edges=True)
    return proposal


def export_stl(obj: bpy.types.Object, destination: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(destination),
        export_selected_objects=True,
        apply_modifiers=True,
        ascii_format=False,
    )


def main() -> None:
    args = parse_args()
    config: dict[str, Any] = json.loads(args.config.resolve().read_text())
    source_path = repo_path(config["source_blend"])
    source_hash = sha256(source_path)
    if source_hash != config["source_sha256"]:
        raise RuntimeError(
            f"Frozen V10 hash mismatch: expected {config['source_sha256']}, "
            f"got {source_hash}"
        )

    bpy.ops.wm.open_mainfile(filepath=str(source_path))
    source = bpy.data.objects.get(config["source_object"])
    if source is None or source.type != "MESH":
        raise RuntimeError(f"Missing mesh source: {config['source_object']}")

    source_fingerprint_before = mesh_fingerprint(source)
    source_points = world_vertices(source)
    proposal = triangulated_world_copy(source, config["proposal_object"])
    proposal_points = world_vertices(proposal)
    source_fingerprint_after = mesh_fingerprint(source)

    source_signature = coordinate_signature(source_points)
    proposal_signature = coordinate_signature(proposal_points)
    vertices_preserved = source_signature == proposal_signature
    source_bounds = bounds(source_points)
    proposal_bounds = bounds(proposal_points)
    bounds_preserved = source_bounds == proposal_bounds
    source_unchanged = source_fingerprint_before == source_fingerprint_after
    proposal_topology = topology(proposal)
    contract = config["contract"]
    blender_topology_pass = (
        proposal_topology["connected_components"]
        == int(contract["required_connected_components"])
        and proposal_topology["boundary_edges"]
        == int(contract["required_boundary_edges"])
        and proposal_topology["nonmanifold_edges"]
        == int(contract["required_nonmanifold_edges"])
    )

    output_dir = repo_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{proposal.name}.stl"
    blend_path = output_dir / "CAT_HEAD_RIGHT_PANEL_TOPOLOGY_REPAIR_REVIEW_V1.blend"
    validation_path = output_dir / "validation.json"

    for obj in bpy.context.scene.objects:
        obj.hide_render = obj != proposal
        obj.hide_viewport = obj != proposal
    proposal.hide_render = False
    proposal.hide_viewport = False
    export_stl(proposal, stl_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    validation = {
        "review_id": config["review_id"],
        "status": "PASS_BLENDER_ONLY" if (
            vertices_preserved
            and bounds_preserved
            and source_unchanged
            and blender_topology_pass
        ) else "FAIL",
        "source_blend": config["source_blend"],
        "source_sha256": source_hash,
        "source_object": source.name,
        "source_object_fingerprint_before": source_fingerprint_before,
        "source_object_fingerprint_after": source_fingerprint_after,
        "source_object_unchanged": source_unchanged,
        "operation": contract["operation"],
        "source_topology": topology(source),
        "proposal_topology": proposal_topology,
        "existing_vertex_coordinates_preserved": vertices_preserved,
        "source_bounds": source_bounds,
        "proposal_bounds": proposal_bounds,
        "bounding_box_preserved": bounds_preserved,
        "proposal_stl": str(stl_path.relative_to(REPO_ROOT)),
        "proposal_stl_sha256": sha256(stl_path),
        "proposal_blend": str(blend_path.relative_to(REPO_ROOT)),
        "proposal_blend_sha256": sha256(blend_path),
        "freecad_validation": "PENDING",
        "holds": [
            "This is a right-panel-only topology proposal.",
            "FreeCAD closed-solid and self-intersection validation is pending.",
            "No flange, head, ear, left-side, aluminum, STL release, or print release is authorized."
        ],
    }
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))

    if validation["status"] != "PASS_BLENDER_ONLY":
        raise RuntimeError("Right-panel triangulation proposal failed Blender gates")


if __name__ == "__main__":
    main()
