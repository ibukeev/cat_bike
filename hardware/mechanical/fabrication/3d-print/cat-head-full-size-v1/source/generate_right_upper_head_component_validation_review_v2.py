#!/usr/bin/env python3
"""Split the frozen right upper head into unchanged validation components."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_panel_topology_repair_review_v1 as topology_base  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/right-upper-head-component-validation-review-v2.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def face_components(faces: list[list[int]]) -> list[list[int]]:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(faces):
        for offset, start in enumerate(face):
            end = face[(offset + 1) % len(face)]
            edge = tuple(sorted((start, end)))
            edge_faces.setdefault(edge, []).append(face_index)
    neighbors = [set() for _ in faces]
    for linked in edge_faces.values():
        for face_index in linked:
            neighbors[face_index].update(linked)
            neighbors[face_index].discard(face_index)
    unseen = set(range(len(faces)))
    components: list[list[int]] = []
    while unseen:
        stack = [unseen.pop()]
        component: list[int] = []
        while stack:
            face_index = stack.pop()
            component.append(face_index)
            for linked in neighbors[face_index]:
                if linked in unseen:
                    unseen.remove(linked)
                    stack.append(linked)
        components.append(sorted(component))
    return sorted(components, key=lambda indices: (-len(indices), indices[0]))


def main() -> None:
    args = parse_args()
    config: dict[str, Any] = json.loads(args.config.resolve().read_text())
    source_path = topology_base.repo_path(config["source_blend"])
    source_hash = topology_base.sha256(source_path)
    if source_hash != config["source_sha256"]:
        raise RuntimeError(
            f"Frozen V10 hash mismatch: expected {config['source_sha256']}, "
            f"got {source_hash}"
        )

    bpy.ops.wm.open_mainfile(filepath=str(source_path))
    source = bpy.data.objects.get(config["source_object"])
    if source is None or source.type != "MESH":
        raise RuntimeError(f"Missing mesh source: {config['source_object']}")

    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    source_mesh = evaluated.to_mesh()
    try:
        matrix = source.matrix_world
        vertices = [matrix @ vertex.co for vertex in source_mesh.vertices]
        faces = [list(polygon.vertices) for polygon in source_mesh.polygons]
    finally:
        evaluated.to_mesh_clear()

    source_fingerprint_before = topology_base.mesh_fingerprint(source)
    source_topology = topology_base.topology(source)
    components = face_components(faces)
    contract = config["contract"]
    expected_components = int(contract["expected_source_connected_components"])
    if len(components) != expected_components:
        raise RuntimeError(
            f"Source component count changed: expected {expected_components}, "
            f"got {len(components)}"
        )

    output_dir = topology_base.repo_path(config["output_dir"])
    components_dir = output_dir / "components"
    components_dir.mkdir(parents=True, exist_ok=True)
    component_records = []
    proposal_objects = []
    aggregate_points = []
    aggregate_faces = 0

    for component_number, face_indices in enumerate(components, start=1):
        used = sorted({index for face_index in face_indices for index in faces[face_index]})
        remap = {source_index: local_index for local_index, source_index in enumerate(used)}
        component_vertices = [vertices[index] for index in used]
        component_faces = [
            [remap[index] for index in faces[face_index]]
            for face_index in face_indices
        ]
        name = f"{config['component_prefix']}__C{component_number:03d}"
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata(component_vertices, [], component_faces)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        component_topology = topology_base.topology(obj)
        stl_path = components_dir / f"{name}.stl"
        topology_base.export_stl(obj, stl_path)
        component_records.append(
            {
                "name": name,
                "source_face_indices": face_indices,
                "source_vertex_indices": used,
                "topology": component_topology,
                "bounds": topology_base.bounds(topology_base.world_vertices(obj)),
                "stl": str(stl_path.relative_to(REPO_ROOT)),
                "stl_sha256": topology_base.sha256(stl_path),
            }
        )
        proposal_objects.append(obj)
        aggregate_points.extend(topology_base.world_vertices(obj))
        aggregate_faces += len(component_faces)

    source_points = [tuple(float(value) for value in point) for point in vertices]
    vertices_preserved = (
        topology_base.coordinate_signature(source_points)
        == topology_base.coordinate_signature(aggregate_points)
    )
    source_bounds = topology_base.bounds(source_points)
    proposal_bounds = topology_base.bounds(aggregate_points)
    bounds_preserved = source_bounds == proposal_bounds
    faces_preserved = aggregate_faces == len(faces)
    source_fingerprint_after = topology_base.mesh_fingerprint(source)
    source_unchanged = source_fingerprint_before == source_fingerprint_after
    component_topology_pass = all(
        record["topology"]["connected_components"] == 1
        and record["topology"]["boundary_edges"]
        == int(contract["required_boundary_edges_per_component"])
        and record["topology"]["nonmanifold_edges"]
        == int(contract["required_nonmanifold_edges_per_component"])
        for record in component_records
    )
    passed = (
        vertices_preserved
        and bounds_preserved
        and faces_preserved
        and source_unchanged
        and component_topology_pass
    )

    for obj in bpy.context.scene.objects:
        obj.hide_render = obj not in proposal_objects
        obj.hide_viewport = obj not in proposal_objects
    blend_path = output_dir / "CAT_HEAD_RIGHT_UPPER_HEAD_COMPONENT_VALIDATION_REVIEW_V2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    validation_path = output_dir / "validation.json"
    validation = {
        "review_id": config["review_id"],
        "status": "PASS_BLENDER_ONLY" if passed else "FAIL",
        "source_blend": config["source_blend"],
        "source_sha256": source_hash,
        "source_object": source.name,
        "source_object_fingerprint_before": source_fingerprint_before,
        "source_object_fingerprint_after": source_fingerprint_after,
        "source_object_unchanged": source_unchanged,
        "operation": contract["operation"],
        "source_topology": source_topology,
        "component_count": len(component_records),
        "production_union_performed": False,
        "existing_vertex_coordinates_preserved": vertices_preserved,
        "faces_preserved": faces_preserved,
        "source_bounds": source_bounds,
        "proposal_bounds": proposal_bounds,
        "bounding_box_preserved": bounds_preserved,
        "all_component_source_topology_valid": component_topology_pass,
        "components": component_records,
        "proposal_blend": str(blend_path.relative_to(REPO_ROOT)),
        "proposal_blend_sha256": topology_base.sha256(blend_path),
        "freecad_validation": "PENDING",
        "holds": [
            "The 42 source components are preserved separately and are not unioned.",
            "FreeCAD per-component solid validation and compound validation are pending.",
            "No panel, flange, ear, left-side, aluminum, fabrication, or print change is authorized."
        ],
    }
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({key: value for key, value in validation.items() if key != "components"}, indent=2))
    if not passed:
        raise RuntimeError("Upper-head component validation split failed Blender gates")


if __name__ == "__main__":
    main()
