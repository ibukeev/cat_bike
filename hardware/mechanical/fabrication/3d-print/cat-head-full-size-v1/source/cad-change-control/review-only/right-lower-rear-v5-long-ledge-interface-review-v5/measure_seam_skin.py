#!/usr/bin/env python3
"""Measure V4 inner-skin intervals in the approved straight-seam frame."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "measurement-contract.json"


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
            f"hash mismatch: {path}: expected {item['sha256']}, got {actual}"
        )
    return path


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def projection(point: Any, origin: Any, axis: Any) -> float:
    return float((point - origin).dot(axis))


def section_values(shape: Any, ray: Any, origin: Any, axis_v: Any) -> list[float]:
    section = shape.section(ray)
    values = [projection(vertex.Point, origin, axis_v) for vertex in section.Vertexes]
    return sorted({round(value, 9) for value in values})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not str(args.report.resolve()).startswith("/tmp/"):
        raise RuntimeError("measurement report must remain under /tmp")
    if args.report.exists():
        raise RuntimeError(f"measurement report already exists: {args.report}")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = "cat-head-right-lower-rear-v5-long-ledge-measurement-v5"
    if contract.get("schema_version") != expected:
        raise RuntimeError("unexpected V5 measurement contract")
    for item in contract["inputs"].values():
        require_hash(item)
    v4 = load_module(require_hash(contract["inputs"]["v4_generator"]), "v4_for_v5_measurement")
    built = v4.build()
    retained, cassette = built[1], built[2]
    if built[0]["status"] != "PASS__V4_SEAM_CLEANUP_REVIEW_READY__NOT_PRINT_RELEASED":
        raise RuntimeError("pinned V4 reconstruction did not pass")

    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    v4_contract = v4.load_contract()
    v3_contract = json.loads(
        v4.require_hash(v4_contract["inputs"]["v3_contract"]).read_text(encoding="utf-8")
    )
    frame = v3_contract["local_partition"]
    origin = App.Vector(*map(float, frame["point_world_mm"]))
    axis_u = App.Vector(*map(float, frame["axis_u_selected_edge_unit"]))
    axis_v = App.Vector(*map(float, frame["axis_v_orthogonalized_shell_inward_unit"]))
    axis_n = App.Vector(*map(float, frame["normal_toward_cassette_unit"]))
    axis_u.normalize(); axis_v.normalize(); axis_n.normalize()

    front_001 = next(
        record["shape"] for record in retained if int(record["component_index"]) == 1
    )
    rear_001 = next(
        record["shape"] for record in cassette if int(record["component_index"]) == 1
    )
    front_all = Part.makeCompound([record["shape"] for record in retained])
    rear_all = Part.makeCompound([record["shape"] for record in cassette])
    sampling = contract["sampling"]
    records = []
    for u_offset in map(float, sampling["u_offsets_mm"]):
        for n_offset in map(float, sampling["n_offsets_mm"]):
            ray_origin = origin + axis_u * u_offset + axis_n * n_offset
            start = ray_origin + axis_v * float(sampling["v_ray_min_mm"])
            end = ray_origin + axis_v * float(sampling["v_ray_max_mm"])
            ray = Part.makeLine(start, end)
            records.append({
                "u_mm": u_offset,
                "n_mm": n_offset,
                "front_001_v_intersections_mm": section_values(front_001, ray, origin, axis_v),
                "rear_001_v_intersections_mm": section_values(rear_001, ray, origin, axis_v),
                "front_all_v_intersections_mm": section_values(front_all, ray, origin, axis_v),
                "rear_all_v_intersections_mm": section_values(rear_all, ray, origin, axis_v),
            })

    report = {
        "schema_version": "cat-head-right-lower-rear-v5-long-ledge-seam-measurement-v5",
        "status": "MEASUREMENT_COMPLETE__NO_GEOMETRY_OUTPUT",
        "authority": contract["authority"],
        "frame": frame,
        "samples": records,
        "io_trace": {
            "v4_saved": False,
            "geometry_mutated": False,
            "geometry_output_created": False,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    populated = sum(
        1 for record in records
        if record["front_all_v_intersections_mm"] or record["rear_all_v_intersections_mm"]
    )
    print(json.dumps({"status": report["status"], "sample_count": len(records), "populated": populated}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
