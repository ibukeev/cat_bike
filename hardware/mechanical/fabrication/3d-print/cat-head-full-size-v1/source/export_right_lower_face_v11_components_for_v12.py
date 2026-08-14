#!/usr/bin/env python3
"""Export the frozen V11 lower-face loose solids for controlled FreeCAD fusion."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_eye_outer_neck_removal_upper_head_owner_review_v10 as v10

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG = PACKAGE_ROOT / "config/right-lower-face-topology-repair-review-v12.json"


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source_name = "PROPOSED__RIGHT_LOWER_FACE__V10_NECK_REMOVAL_WITH_V2_CLEARANCE_RESTORED_V11"
    source = bpy.data.objects[source_name]
    expected = config["locked_contract"]["source_fingerprint"]
    actual = v10.v9.v3.fingerprint(source)
    if actual != expected:
        raise RuntimeError(f"V11 lower-face fingerprint changed: {actual}")

    output = REPO_ROOT / config["output_dir"] / "components"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty component directory: {output}")

    world = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    records = []
    components = v10.v9.components(source)
    if len(components) != int(config["locked_contract"]["source_component_count"]):
        raise RuntimeError(f"expected 60 components, found {len(components)}")

    for number, indices in enumerate(components, start=1):
        ordered = sorted(indices)
        remap = {old: new for new, old in enumerate(ordered)}
        faces = [
            tuple(remap[index] for index in polygon.vertices)
            for polygon in source.data.polygons
            if set(polygon.vertices).issubset(indices)
        ]
        name = f"V11_LOWER_COMPONENT_{number:03d}"
        mesh = bpy.data.meshes.new(f"{name}_MESH")
        mesh.from_pydata([world[index] for index in ordered], [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        path = output / f"{name.lower()}.obj"
        v10.v9.v3.export_obj(obj, path)
        low, high = v10.v9.world_bbox(obj, set(range(len(obj.data.vertices))))
        records.append(
            {
                "name": name,
                "path": str(path.relative_to(REPO_ROOT)),
                "fingerprint": v10.v9.v3.fingerprint(obj),
                "topology": v10.v9.v3.topology(obj),
                "bbox_min_mm": [round(value, 5) for value in low],
                "bbox_max_mm": [round(value, 5) for value in high],
            }
        )
        bpy.data.objects.remove(obj, do_unlink=True)

    inventory = {
        "status": "exact component export only; no geometry change",
        "source_object": source_name,
        "source_fingerprint": actual,
        "component_count": len(records),
        "components": records,
    }
    (output.parent / "component-inventory-v12.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"component_count": len(records), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
