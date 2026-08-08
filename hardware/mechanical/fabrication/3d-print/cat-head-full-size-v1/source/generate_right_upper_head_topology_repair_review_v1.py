#!/usr/bin/env python3
"""Create an isolated, vertex-preserving right upper-head topology proposal."""

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
    PACKAGE_ROOT / "config/right-upper-head-topology-repair-review-v1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


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

    source_fingerprint_before = topology_base.mesh_fingerprint(source)
    source_points = topology_base.world_vertices(source)
    source_topology = topology_base.topology(source)
    proposal = topology_base.triangulated_world_copy(
        source, config["proposal_object"]
    )
    proposal_points = topology_base.world_vertices(proposal)
    proposal_topology = topology_base.topology(proposal)
    source_fingerprint_after = topology_base.mesh_fingerprint(source)

    vertices_preserved = (
        topology_base.coordinate_signature(source_points)
        == topology_base.coordinate_signature(proposal_points)
    )
    source_bounds = topology_base.bounds(source_points)
    proposal_bounds = topology_base.bounds(proposal_points)
    bounds_preserved = source_bounds == proposal_bounds
    source_unchanged = source_fingerprint_before == source_fingerprint_after
    components_preserved = (
        source_topology["connected_components"]
        == proposal_topology["connected_components"]
    )
    contract = config["contract"]
    blender_topology_pass = (
        components_preserved
        and proposal_topology["boundary_edges"]
        == int(contract["required_boundary_edges"])
        and proposal_topology["nonmanifold_edges"]
        == int(contract["required_nonmanifold_edges"])
    )

    output_dir = topology_base.repo_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = output_dir / f"{proposal.name}.stl"
    blend_path = output_dir / "CAT_HEAD_RIGHT_UPPER_HEAD_TOPOLOGY_REPAIR_REVIEW_V1.blend"
    validation_path = output_dir / "validation.json"

    for obj in bpy.context.scene.objects:
        obj.hide_render = obj != proposal
        obj.hide_viewport = obj != proposal
    proposal.hide_render = False
    proposal.hide_viewport = False
    topology_base.export_stl(proposal, stl_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    passed = (
        vertices_preserved
        and bounds_preserved
        and source_unchanged
        and blender_topology_pass
    )
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
        "proposal_topology": proposal_topology,
        "connected_component_count_preserved": components_preserved,
        "production_union_performed": False,
        "existing_vertex_coordinates_preserved": vertices_preserved,
        "source_bounds": source_bounds,
        "proposal_bounds": proposal_bounds,
        "bounding_box_preserved": bounds_preserved,
        "proposal_stl": str(stl_path.relative_to(REPO_ROOT)),
        "proposal_stl_sha256": topology_base.sha256(stl_path),
        "proposal_blend": str(blend_path.relative_to(REPO_ROOT)),
        "proposal_blend_sha256": topology_base.sha256(blend_path),
        "freecad_validation": "PENDING",
        "holds": [
            "This is a right-upper-head validation reference only.",
            "Disconnected source components are preserved and not unioned.",
            "FreeCAD solid/compound and self-intersection validation is pending.",
            "No panel, flange, ear, left-side, aluminum, fabrication, or print change is authorized."
        ],
    }
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))
    if not passed:
        raise RuntimeError("Right upper-head triangulation failed Blender gates")


if __name__ == "__main__":
    main()
