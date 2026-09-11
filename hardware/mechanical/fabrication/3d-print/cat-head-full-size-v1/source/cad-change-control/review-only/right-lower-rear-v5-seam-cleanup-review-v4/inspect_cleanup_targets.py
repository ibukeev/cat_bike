#!/usr/bin/env python3
"""Read-only ownership and adjacency inspection for the V4 seam cleanup."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "inspection-contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(item: dict[str, Any]) -> Path:
    path = (PROJECT_ROOT / item["path"]).resolve()
    actual = sha256(path)
    if actual != item["sha256"]:
        raise RuntimeError(
            f"hash mismatch: {path}: expected {item[sha256]}, got {actual}"
        )
    return path


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point(values: Any) -> list[float]:
    return [float(values.x), float(values.y), float(values.z)]


def bbox(shape: Any) -> dict[str, Any]:
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        "size_mm": [float(box.XLength), float(box.YLength), float(box.ZLength)],
    }


def center_of_mass(shape: Any) -> list[float]:
    solids = list(shape.Solids)
    total = sum(float(solid.Volume) for solid in solids)
    if not solids or total <= 1.0e-12:
        return point(shape.BoundBox.Center)
    weighted = solids[0].CenterOfMass * float(solids[0].Volume)
    for solid in solids[1:]:
        weighted = weighted + solid.CenterOfMass * float(solid.Volume)
    return point(weighted / total)


def edge_record(edge: Any) -> dict[str, Any]:
    vertices = edge.Vertexes
    direction = None
    if len(vertices) >= 2:
        delta = vertices[-1].Point - vertices[0].Point
        if float(delta.Length) > 1.0e-12:
            delta.normalize()
            direction = point(delta)
    return {
        "length_mm": float(edge.Length),
        "start_mm": point(vertices[0].Point) if vertices else None,
        "end_mm": point(vertices[-1].Point) if vertices else None,
        "direction_unit": direction,
    }


def dominant_edges(shape: Any) -> list[dict[str, Any]]:
    return [
        edge_record(edge)
        for edge in sorted(shape.Edges, key=lambda item: float(item.Length), reverse=True)[:6]
    ]


def nearest(left: Any, right: Any) -> dict[str, Any]:
    result = left.distToShape(right)
    pairs = []
    for pair in result[1][:4]:
        pairs.append({"left_mm": point(pair[0]), "right_mm": point(pair[1])})
    return {"distance_mm": float(result[0]), "nearest_pairs": pairs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not str(args.report.resolve()).startswith("/tmp/"):
        raise RuntimeError("inspection report must stay under /tmp")
    if args.report.exists():
        raise RuntimeError(f"inspection report already exists: {args.report}")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-lower-rear-v5-seam-cleanup-inspection-v4":
        raise RuntimeError("unexpected inspection contract schema")
    for item in contract["inputs"].values():
        require_hash(item)
    v3 = load_module(require_hash(contract["inputs"]["v3_generator"]), "v3_for_v4_inspection")
    built = v3.build()
    retained = built[1]
    cassette = built[2]

    records = {}
    for owner_name, items in (("retained_front", retained), ("rear_cassette", cassette)):
        for item in items:
            component_index = int(item["component_index"])
            records[(owner_name, component_index)] = item

    front_target = records.get(("retained_front", 57))
    if front_target is None:
        raise RuntimeError("selected retained component 057 is missing")
    front_shape = front_target["shape"]
    component_001_front = records[("retained_front", 1)]["shape"]
    component_001_rear = records[("rear_cassette", 1)]["shape"]

    inspected = []
    requested = set(map(int, contract["candidate_adjacent_components"]))
    for (owner_name, component_index), item in sorted(records.items()):
        if component_index not in requested:
            continue
        shape = item["shape"]
        inspected.append(
            {
                "owner": owner_name,
                "component_index": component_index,
                "record_name": item["name"],
                "record_owner": item["owner"],
                "volume_mm3": float(shape.Volume),
                "center_of_mass_mm": center_of_mass(shape),
                "bbox": bbox(shape),
                "valid": bool(shape.isValid()),
                "closed": bool(shape.isClosed()),
                "solid_count": len(shape.Solids),
                "dominant_edges": dominant_edges(shape),
                "to_component_057": nearest(shape, front_shape),
                "to_component_001_front": nearest(shape, component_001_front),
                "to_component_001_rear": nearest(shape, component_001_rear),
            }
        )

    report = {
        "schema_version": "cat-head-right-lower-rear-v5-seam-cleanup-target-inspection-v4",
        "status": "INSPECTION_COMPLETE__NO_GEOMETRY_OUTPUT",
        "authority": contract["authority"],
        "selected_front_residual": contract["selected_front_residual"],
        "review_overlay_to_remove": contract["review_overlay_to_remove"],
        "inspected_components": inspected,
        "io_trace": {
            "v3_saved": False,
            "canonical_saved": False,
            "geometry_mutated": False,
            "geometry_output_created": False,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "components": [
            {
                "owner": item["owner"],
                "component": item["component_index"],
                "volume_mm3": item["volume_mm3"],
                "distance_to_057_mm": item["to_component_057"]["distance_mm"],
            }
            for item in inspected
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
