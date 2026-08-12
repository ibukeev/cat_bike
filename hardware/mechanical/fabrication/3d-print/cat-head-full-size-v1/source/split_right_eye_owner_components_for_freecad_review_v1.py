#!/usr/bin/env python3
"""Split frozen right-eye owner STLs into audit-only connected components.

The outputs are temporary FreeCAD review inputs, not fabrication exports.
No source STL is modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PACKAGE_ROOT / "output/10-design-gates/gate6-eye-modules/eyes"
OUTPUT_DIR = Path("/tmp/right-eye-owner-components-v1")

SOURCES = {
    "bucket": SOURCE_DIR / "right_eye_bucket.stl",
    "cap": SOURCE_DIR / "right_eye_led_rear_cap.stl",
}


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_stl(path: Path) -> bpy.types.Object:
    bpy.ops.wm.stl_import(filepath=str(path))
    imported = list(bpy.context.selected_objects)
    if len(imported) != 1:
        raise RuntimeError(f"Expected one imported mesh for {path}, got {len(imported)}")
    return imported[0]


def world_bbox_center(obj: bpy.types.Object) -> list[float]:
    corners = [obj.matrix_world @ type(obj.location)(corner) for corner in obj.bound_box]
    return [
        sum(corner[axis] for corner in corners) / len(corners)
        for axis in range(3)
    ]


def export_component(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path),
        export_selected_objects=True,
        ascii_format=False,
    )


def split_source(role: str, path: Path) -> list[dict[str, object]]:
    clear_scene()
    source = import_stl(path)
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    components = sorted(
        list(bpy.context.selected_objects),
        key=lambda obj: tuple(round(value, 6) for value in world_bbox_center(obj)),
    )
    records = []
    for index, component in enumerate(components, start=1):
        component.name = f"{role}_component_{index:02d}"
        output = OUTPUT_DIR / f"{component.name}.stl"
        export_component(component, output)
        records.append(
            {
                "role": role,
                "index": index,
                "name": component.name,
                "file": str(output),
                "bbox_center_mm": [round(value, 6) for value in world_bbox_center(component)],
                "dimensions_mm": [round(value, 6) for value in component.dimensions],
                "vertex_count": len(component.data.vertices),
                "polygon_count": len(component.data.polygons),
            }
        )
    return records


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for role, path in SOURCES.items():
        records.extend(split_source(role, path))
    manifest = {
        "purpose": "temporary FreeCAD owner cleanup review; not print release",
        "sources": {role: str(path) for role, path in SOURCES.items()},
        "components": records,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
