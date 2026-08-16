#!/usr/bin/env python3
"""Round-trip the isolated V17 topology-repaired review through STEP.

The hash-pinned V3 FCStd is opened read-only and its proposal is exported to a
new review STEP.  The STEP is imported again and must pass the complete
shape/round-trip contract before a separate review FCStd and validation JSON
are saved.  No STL, mirror, production union, slice, or G-code is produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args()


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bbox(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def bbox_delta(first, second) -> list[float]:
    a = first.BoundBox
    b = second.BoundBox
    return [
        float(b.XMin - a.XMin),
        float(b.YMin - a.YMin),
        float(b.ZMin - a.ZMin),
        float(b.XMax - a.XMax),
        float(b.YMax - a.YMax),
        float(b.ZMax - a.ZMax),
    ]


def nearest_vertex_error(shape, target) -> float:
    return min(vertex.Point.distanceToPoint(target) for vertex in shape.Vertexes)


def max_bidirectional_vertex_error(first, second) -> float:
    def directed(source, target) -> float:
        return max(nearest_vertex_error(target, vertex.Point) for vertex in source.Vertexes)

    return max(directed(first, second), directed(second, first))


def check_messages(shape) -> list[str]:
    try:
        raw = shape.check(True)
        return [str(item) for item in raw] if raw else []
    except Exception as exc:
        return [f"OCCT check raised: {exc}"]


def add_shape(document, name: str, label: str, shape, visible: bool):
    obj = document.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = (0.72, 0.78, 0.84)
        obj.ViewObject.LineColor = (0.12, 0.12, 0.12)
        obj.ViewObject.Visibility = visible
    return obj


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    source_path = root / contract["source"]["path"]
    frozen_step = root / contract["frozen_input_step"]["path"]
    if sha256_file(source_path) != contract["source"]["sha256"]:
        raise RuntimeError("V3 repair FCStd SHA-256 mismatch")
    if sha256_file(frozen_step) != contract["frozen_input_step"]["sha256"]:
        raise RuntimeError("frozen V2 STEP SHA-256 mismatch")

    output_dir = root / contract["output"]["directory"]
    step_path = output_dir / contract["output"]["step"]
    review_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/6 contract and hashes verified", flush=True)

    source_document = App.openDocument(str(source_path))
    try:
        source_object = source_document.getObject(contract["source"]["object_name"])
        if source_object is None or source_object.Shape.isNull():
            raise RuntimeError("V3 proposal object is missing")
        candidate = source_object.Shape.copy()
        Part.export([source_object], str(step_path))
    finally:
        App.closeDocument(source_document.Name)
    print("STAGE 2/6 proposal exported to new STEP", flush=True)

    roundtrip = Part.Shape()
    roundtrip.read(str(step_path))
    if roundtrip.isNull():
        raise RuntimeError("review STEP imported as a null shape")
    print("STAGE 3/6 review STEP imported", flush=True)

    gates = contract["gates"]
    bounds_delta = bbox_delta(candidate, roundtrip)
    vertex_error = max_bidirectional_vertex_error(candidate, roundtrip)
    volume_delta = float(roundtrip.Volume - candidate.Volume)
    checks = {
        "source_hash_matches": sha256_file(source_path) == contract["source"]["sha256"],
        "frozen_input_hash_matches": sha256_file(frozen_step) == contract["frozen_input_step"]["sha256"],
        "candidate_valid": bool(candidate.isValid()),
        "candidate_closed": bool(candidate.isClosed()),
        "candidate_solid_count": len(candidate.Solids) == int(gates["required_solid_count"]),
        "candidate_face_count": len(candidate.Faces) == int(gates["required_face_count"]),
        "roundtrip_valid": bool(roundtrip.isValid()),
        "roundtrip_closed": bool(roundtrip.isClosed()),
        "roundtrip_solid_count": len(roundtrip.Solids) == int(gates["required_solid_count"]),
        "roundtrip_face_count": len(roundtrip.Faces) == int(gates["required_face_count"]),
        "roundtrip_bounds": max(abs(value) for value in bounds_delta) <= float(gates["maximum_bounds_delta_mm"]),
        "roundtrip_volume": abs(volume_delta) <= float(gates["maximum_absolute_volume_delta_mm3"]),
        "roundtrip_vertices": vertex_error <= float(gates["maximum_vertex_roundtrip_error_mm"]),
    }
    passed = all(checks.values())
    print("STAGE 4/6 round-trip gates measured", flush=True)
    result = {
        "schema_version": "1.0",
        "generator": "freecad-v17-full-topology-repair-step-roundtrip-review-v4",
        "freecad_version": App.Version(),
        "contract_id": contract["contract_id"],
        "status": "PASS__REVIEW_ONLY_STEP" if passed else "FAIL__OUTPUT_QUARANTINED",
        "source": {
            "path": contract["source"]["path"],
            "sha256": sha256_file(source_path),
            "object_name": contract["source"]["object_name"],
            "face_count": len(candidate.Faces),
            "solid_count": len(candidate.Solids),
            "volume_mm3": float(candidate.Volume),
            "bounds": bbox(candidate),
        },
        "frozen_input_step": {
            "path": contract["frozen_input_step"]["path"],
            "sha256": sha256_file(frozen_step),
            "overwritten": False,
        },
        "roundtrip": {
            "face_count": len(roundtrip.Faces),
            "solid_count": len(roundtrip.Solids),
            "volume_mm3": float(roundtrip.Volume),
            "volume_delta_mm3": volume_delta,
            "bounds": bbox(roundtrip),
            "bounds_delta_mm": bounds_delta,
            "maximum_vertex_error_mm": vertex_error,
            "global_occt_check_messages": check_messages(roundtrip),
        },
        "checks": checks,
        "release_holds": contract["release_holds"],
        "outputs": {
            "step": str(step_path.relative_to(root)),
            "fcstd": str(review_path.relative_to(root)),
            "validation": str(validation_path.relative_to(root)),
            "stl_exported": False,
            "mirrored": False,
            "production_union_created": False,
        },
    }
    if not passed:
        validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    review_document = App.newDocument("CAT_HEAD_RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIR_STEP_REVIEW_V4")
    try:
        proposed = add_shape(
            review_document,
            "PROPOSED_RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIRED_STEP_V4",
            "PROPOSED__RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIRED_STEP_V4__REVIEW_ONLY",
            roundtrip,
            True,
        )
        proposed.addProperty("App::PropertyString", "ContractId", "ChangeControl")
        proposed.ContractId = contract["contract_id"]
        proposed.addProperty("App::PropertyString", "ReleaseState", "ChangeControl")
        proposed.ReleaseState = "REVIEW_ONLY__NO_MIRROR_NO_STL_NO_PRINT"
        review_document.recompute()
        review_document.saveAs(str(review_path))
    finally:
        App.closeDocument(review_document.Name)
    print("STAGE 5/6 review FCStd saved", flush=True)

    result["outputs"]["step_sha256"] = sha256_file(step_path)
    result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
    validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STAGE 6/6 validation saved", flush=True)
    print(json.dumps({"status": result["status"], "checks": checks, "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
