#!/usr/bin/env python3
"""Export the approved isolated V17/V9 skin repair as a new review STEP.

The source FCStd is hash-pinned and opened read-only.  The frozen V17 STEP and
the V1 repair review are never overwritten.  This script exports only the
already-generated proposal object, imports the new STEP back into OCCT, applies
fail-closed round-trip gates, and saves a separate review document plus JSON.
It does not export STL, mirror geometry, create a production union, or release
anything for printing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def max_bidirectional_vertex_error(first, second) -> float:
    first_points = [
        (float(vertex.X), float(vertex.Y), float(vertex.Z)) for vertex in first.Vertexes
    ]
    second_points = [
        (float(vertex.X), float(vertex.Y), float(vertex.Z)) for vertex in second.Vertexes
    ]

    def directed(source_points, target_points) -> float:
        return max(
            math.sqrt(
                min(
                    (x - tx) ** 2 + (y - ty) ** 2 + (z - tz) ** 2
                    for tx, ty, tz in target_points
                )
            )
            for x, y, z in source_points
        )

    return max(
        directed(first_points, second_points),
        directed(second_points, first_points),
    )


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
    print("STAGE 1/7 contract loaded", flush=True)
    source_path = root / contract["source"]["path"]
    if sha256_file(source_path) != contract["source"]["sha256"]:
        raise RuntimeError("V1 repair FCStd SHA-256 mismatch")

    frozen_step = root / contract["frozen_v17_step"]["path"]
    if sha256_file(frozen_step) != contract["frozen_v17_step"]["sha256"]:
        raise RuntimeError("frozen V17 STEP SHA-256 mismatch")

    output_dir = root / contract["output"]["directory"]
    step_path = output_dir / contract["output"]["step"]
    review_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 2/7 output directory reserved", flush=True)

    source_document = App.openDocument(str(source_path))
    try:
        source_object = source_document.getObject(contract["source"]["object_name"])
        if source_object is None or source_object.Shape.isNull():
            raise RuntimeError("approved V1 proposal object is missing")
        candidate = source_object.Shape.copy()
        print("STAGE 3/7 hash-pinned proposal loaded", flush=True)
        Part.export([source_object], str(step_path))
        print("STAGE 4/7 new STEP exported", flush=True)
    finally:
        App.closeDocument(source_document.Name)

    roundtrip = Part.Shape()
    roundtrip.read(str(step_path))
    print("STAGE 5/7 new STEP imported", flush=True)
    if roundtrip.isNull():
        raise RuntimeError("new review STEP imported as a null shape")

    gates = contract["gates"]
    bounds_delta = bbox_delta(candidate, roundtrip)
    print("STAGE 5A/7 bounds measured", flush=True)
    vertex_error = max_bidirectional_vertex_error(candidate, roundtrip)
    print("STAGE 5B/7 vertices measured", flush=True)
    volume_delta = float(roundtrip.Volume - candidate.Volume)
    print("STAGE 5C/7 volume measured", flush=True)
    candidate_valid = bool(candidate.isValid())
    candidate_closed = bool(candidate.isClosed())
    roundtrip_valid = bool(roundtrip.isValid())
    roundtrip_closed = bool(roundtrip.isClosed())
    print("STAGE 5D/7 topology measured", flush=True)
    checks = {
        "source_fcstd_hash_matches": sha256_file(source_path)
        == contract["source"]["sha256"],
        "frozen_v17_hash_matches": sha256_file(frozen_step)
        == contract["frozen_v17_step"]["sha256"],
        "candidate_valid": candidate_valid,
        "candidate_closed": candidate_closed,
        "candidate_solid_count": len(candidate.Solids)
        == int(gates["required_solid_count"]),
        "candidate_face_count": len(candidate.Faces)
        == int(gates["required_face_count"]),
        "roundtrip_valid": roundtrip_valid,
        "roundtrip_closed": roundtrip_closed,
        "roundtrip_solid_count": len(roundtrip.Solids)
        == int(gates["required_solid_count"]),
        "roundtrip_face_count": len(roundtrip.Faces)
        == int(gates["required_face_count"]),
        "roundtrip_bounds": max(abs(value) for value in bounds_delta)
        <= float(gates["maximum_bounds_delta_mm"]),
        "roundtrip_volume": abs(volume_delta)
        <= float(gates["maximum_absolute_volume_delta_mm3"]),
        "roundtrip_vertices": vertex_error
        <= float(gates["maximum_vertex_roundtrip_error_mm"]),
    }
    passed = all(checks.values())
    print("STAGE 6/7 round-trip measurements complete", flush=True)
    result = {
        "schema_version": "1.0",
        "generator": "freecad-v17-v9-skin-repair-step-roundtrip-review-v2",
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
        "frozen_v17_step": {
            "path": contract["frozen_v17_step"]["path"],
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
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    review_document = App.newDocument(
        "CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_STEP_REVIEW_V2"
    )
    try:
        proposed = add_shape(
            review_document,
            "PROPOSED_RIGHT_EYE_V17_V9_SKIN_REPAIRED_STEP_V2",
            "PROPOSED__RIGHT_EYE_V17_V9_SKIN_REPAIRED_STEP_V2__REVIEW_ONLY",
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

    result["outputs"]["step_sha256"] = sha256_file(step_path)
    result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
    validation_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("STAGE 7/7 review document and validation saved", flush=True)
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": checks,
                "outputs": result["outputs"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
