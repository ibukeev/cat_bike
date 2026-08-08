#!/usr/bin/env python3
"""Create an isolated deterministic topology repair for the frozen right ear."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_panel_topology_repair_review_v1 as topology_base  # noqa: E402
import generate_right_upper_head_component_validation_review_v2 as component_base  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/right-ear-deterministic-topology-repair-review-v1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def main() -> None:
    args = parse_args()
    config: dict[str, Any] = json.loads(args.config.resolve().read_text())
    contract = config["contract"]
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

    source_fingerprint_before = topology_base.mesh_fingerprint(source)
    if source_fingerprint_before != config["source_object_fingerprint"]:
        raise RuntimeError(
            "Frozen right-ear fingerprint mismatch: expected "
            f"{config['source_object_fingerprint']}, got {source_fingerprint_before}"
        )

    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    source_mesh = evaluated.to_mesh()
    try:
        matrix = source.matrix_world
        vertices = [matrix @ vertex.co for vertex in source_mesh.vertices]
        faces = [list(polygon.vertices) for polygon in source_mesh.polygons]
    finally:
        evaluated.to_mesh_clear()

    source_topology = topology_base.topology(source)
    components = component_base.face_components(faces)
    expected_components = int(contract["expected_source_connected_components"])
    if len(components) != expected_components:
        raise RuntimeError(
            f"Source component count changed: expected {expected_components}, "
            f"got {len(components)}"
        )
    if len(vertices) != int(contract["expected_source_vertices"]):
        raise RuntimeError(
            f"Source vertex count changed: expected {contract['expected_source_vertices']}, "
            f"got {len(vertices)}"
        )

    output_dir = topology_base.repo_path(config["output_dir"])
    components_dir = output_dir / "components"
    components_dir.mkdir(parents=True, exist_ok=True)
    component_records = []
    proposal_objects = []
    aggregate_points = []
    repaired_triangles = 0

    for component_number, face_indices in enumerate(components, start=1):
        used = sorted(
            {index for face_index in face_indices for index in faces[face_index]}
        )
        remap = {
            source_index: local_index
            for local_index, source_index in enumerate(used)
        }
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

        bm = bmesh.new()
        bm.from_mesh(mesh)
        before_vertex_count = len(bm.verts)
        try:
            bmesh.ops.triangulate(
                bm,
                faces=list(bm.faces),
                quad_method=contract["triangulation_quad_method"],
                ngon_method=contract["triangulation_ngon_method"],
            )
            bm.normal_update()
            if len(bm.verts) != before_vertex_count:
                raise RuntimeError(
                    f"{name} triangulation changed vertex count from "
                    f"{before_vertex_count} to {len(bm.verts)}"
                )
            bm.to_mesh(mesh)
        finally:
            bm.free()
        mesh.update(calc_edges=True)

        component_points = topology_base.world_vertices(obj)
        component_topology = topology_base.topology(obj)
        stl_path = components_dir / f"{name}.stl"
        topology_base.export_stl(obj, stl_path)
        aggregate_points.extend(component_points)
        repaired_triangles += component_topology["faces"]
        component_records.append(
            {
                "name": name,
                "source_face_indices": face_indices,
                "source_vertex_indices": used,
                "source_vertex_count": before_vertex_count,
                "topology": component_topology,
                "bounds": topology_base.bounds(component_points),
                "stl": str(stl_path.relative_to(REPO_ROOT)),
                "stl_sha256": topology_base.sha256(stl_path),
            }
        )
        proposal_objects.append(obj)

    source_points = [tuple(float(value) for value in point) for point in vertices]
    proposal_points = [
        tuple(float(value) for value in point) for point in aggregate_points
    ]
    vertices_preserved = (
        topology_base.coordinate_signature(source_points)
        == topology_base.coordinate_signature(proposal_points)
    )
    source_bounds = topology_base.bounds(source_points)
    proposal_bounds = topology_base.bounds(proposal_points)
    bounds_preserved = source_bounds == proposal_bounds
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
        and source_unchanged
        and component_topology_pass
        and repaired_triangles == int(contract["expected_repaired_triangles"])
    )

    for obj in bpy.context.scene.objects:
        obj.hide_render = obj not in proposal_objects
        obj.hide_viewport = obj not in proposal_objects
    blend_path = output_dir / "CAT_HEAD_RIGHT_EAR_TOPOLOGY_REPAIR_REVIEW_V1.blend"
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
        "maximum_existing_vertex_displacement_mm": (
            0.0 if vertices_preserved else None
        ),
        "source_bounds": source_bounds,
        "proposal_bounds": proposal_bounds,
        "bounding_box_preserved": bounds_preserved,
        "repaired_triangle_count": repaired_triangles,
        "all_component_blender_topology_valid": component_topology_pass,
        "components": component_records,
        "proposal_blend": str(blend_path.relative_to(REPO_ROOT)),
        "proposal_blend_sha256": topology_base.sha256(blend_path),
        "freecad_validation": "PENDING",
        "holds": [
            "The two repaired source components remain separate and are not unioned.",
            "FreeCAD component solid and compound validation are pending.",
            "No panel, head, flange, left-side, lower/rear, reinforcement, eye, C006, aluminum, fabrication, or print change is authorized."
        ],
    }
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in validation.items() if key != "components"},
            indent=2,
        )
    )
    if not passed:
        raise RuntimeError("Right-ear deterministic topology repair failed Blender gates")


if __name__ == "__main__":
    main()
