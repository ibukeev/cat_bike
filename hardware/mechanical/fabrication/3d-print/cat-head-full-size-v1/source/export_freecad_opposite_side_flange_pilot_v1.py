#!/usr/bin/env python3
"""Export an immutable three-object reference set for the FreeCAD flange pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/freecad-opposite-side-flange-pilot-v1.json"


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


def world_bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "min_mm": [round(min(point[axis] for point in points), 6) for axis in range(3)],
        "max_mm": [round(max(point[axis] for point in points), 6) for axis in range(3)],
    }


def evaluated_counts(obj: bpy.types.Object) -> dict[str, int]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
        }
    finally:
        evaluated.to_mesh_clear()


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
    config_path = args.config.resolve()
    config: dict[str, Any] = json.loads(config_path.read_text())
    source_path = repo_path(config["source_blend"])
    source_hash = sha256(source_path)
    if source_hash != config["source_sha256"]:
        raise RuntimeError(
            "Frozen source hash mismatch: "
            f"expected {config['source_sha256']}, got {source_hash}"
        )

    output_dir = repo_path(config["output_dir"])
    reference_dir = output_dir / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)

    manifest_objects: list[dict[str, Any]] = []
    expected_names = {entry["blender_object"] for entry in config["objects"]}
    missing = sorted(expected_names.difference(bpy.data.objects.keys()))
    if missing:
        raise RuntimeError(f"Frozen source is missing pilot objects: {missing}")

    for entry in config["objects"]:
        obj = bpy.data.objects[entry["blender_object"]]
        if obj.type != "MESH":
            raise RuntimeError(f"Pilot object is not a mesh: {obj.name} ({obj.type})")
        destination = reference_dir / f"{entry['export_name']}.stl"
        export_stl(obj, destination)
        manifest_objects.append(
            {
                **entry,
                "stl": str(destination.relative_to(REPO_ROOT)),
                "stl_sha256": sha256(destination),
                "source_bounds": world_bounds(obj),
                "evaluated_mesh_counts": evaluated_counts(obj),
            }
        )

    manifest = {
        "pilot_id": config["pilot_id"],
        "source_blend": config["source_blend"],
        "source_sha256": source_hash,
        "reference_only": True,
        "objects": manifest_objects,
        "excluded_geometry": config["excluded_geometry"],
        "geometry_policy": config["geometry_policy"],
    }
    manifest_path = output_dir / "reference-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"FREECAD_PILOT_MANIFEST={manifest_path}")


if __name__ == "__main__":
    main()
