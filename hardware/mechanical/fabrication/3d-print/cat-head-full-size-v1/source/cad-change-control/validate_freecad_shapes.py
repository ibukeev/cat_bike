#!/usr/bin/env python3
"""Read-only OCCT/FreeCAD shape validation governed by a checked-in contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App
import Part

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_change_contract import (  # noqa: E402
    find_repository_root,
    load_json,
    sha256_file,
    validate_files,
)


def shape_metrics(shape: Part.Shape) -> dict[str, Any]:
    box = shape.BoundBox
    check_errors: list[str] = []
    try:
        raw_check = shape.check(True)
        if raw_check:
            check_errors = [str(item) for item in raw_check]
    except Exception as exc:  # FreeCAD versions expose different check returns.
        check_errors = [f"OCCT check raised: {exc}"]
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "vertex_count": len(shape.Vertexes),
        "volume_mm3": float(shape.Volume),
        "bounding_box_mm": {
            "min": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "max": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        },
        "occt_check_messages": check_errors,
    }


def load_step(path: Path) -> Part.Shape:
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise ValueError(f"STEP import produced a null shape: {path}")
    return shape


def load_fcstd(path: Path, object_names: list[str]) -> tuple[list[Part.Shape], Any]:
    if not object_names:
        raise ValueError(f"FCStd artifact requires declared object_names: {path}")
    document = App.openDocument(str(path))
    shapes: list[Part.Shape] = []
    for name in object_names:
        matches = [
            obj
            for obj in document.Objects
            if obj.Name == name or obj.Label == name
        ]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one FCStd object {name!r} in {path}")
        shape = getattr(matches[0], "Shape", None)
        if shape is None or shape.isNull():
            raise ValueError(f"FCStd object has no usable Shape: {name!r}")
        shapes.append(shape.copy())
    return shapes, document


def load_artifact_shape(root: Path, artifact: dict[str, Any]) -> tuple[Part.Shape, Any | None]:
    path = root / artifact["path"]
    if artifact["format"] == "step":
        return load_step(path), None
    if artifact["format"] == "fcstd":
        shapes, document = load_fcstd(path, artifact.get("object_names", []))
        if len(shapes) != 1:
            raise ValueError("pilot validator requires one declared shape per FCStd artifact")
        return shapes[0], document
    raise ValueError(f"BREP validator does not load format {artifact['format']!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    preflight = validate_files(args.manifest, args.contract, verify_files=True)
    if preflight["status"] != "PASS":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 1

    root = find_repository_root(args.manifest)
    manifest = load_json(args.manifest)
    contract = load_json(args.contract)
    artifacts = {item["id"]: item for item in manifest["artifacts"]}

    report_path = args.report if args.report.is_absolute() else root / args.report
    output_root = root / contract["output_directory"]
    try:
        report_path.resolve().relative_to(output_root.resolve())
    except ValueError:
        raise ValueError("report path must be inside the contracted output_directory")
    if report_path.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {report_path}")

    loaded: dict[str, Part.Shape] = {}
    documents: list[Any] = []
    shape_reports: dict[str, Any] = {}
    errors: list[str] = []
    gates = contract["shape_gates"]

    try:
        for artifact_id in contract["artifacts_to_inspect"]:
            artifact = artifacts[artifact_id]
            shape, document = load_artifact_shape(root, artifact)
            loaded[artifact_id] = shape
            if document is not None:
                documents.append(document)
            metrics = shape_metrics(shape)
            metrics["sha256"] = sha256_file(root / artifact["path"])
            shape_reports[artifact_id] = metrics
            if gates["require_valid"] and not metrics["valid"]:
                errors.append(f"{artifact_id}: shape is invalid")
            if gates["require_closed"] and not metrics["closed"]:
                errors.append(f"{artifact_id}: shape is open")
            if gates["require_clean_occt_check"] and metrics["occt_check_messages"]:
                errors.append(
                    f"{artifact_id}: OCCT deep check reported "
                    f"{len(metrics['occt_check_messages'])} issue(s)"
                )
            if metrics["solid_count"] != gates["required_solid_count"]:
                errors.append(
                    f"{artifact_id}: expected {gates['required_solid_count']} solids, "
                    f"found {metrics['solid_count']}"
                )
            expected = artifact.get("expected_shape", {})
            for key in ("valid", "closed", "solid_count"):
                if key in expected and metrics[key] != expected[key]:
                    errors.append(
                        f"{artifact_id}: manifest expected {key}={expected[key]!r}, "
                        f"found {metrics[key]!r}"
                    )

        clearance_reports: list[dict[str, Any]] = []
        for gate in contract["clearance_gates"]:
            first = loaded[gate["first"]]
            second = loaded[gate["second"]]
            if gate["mode"] == "actual_geometry":
                distance = float(first.distToShape(second)[0])
                passed = distance >= float(gate["minimum_distance_mm"])
                item = {**gate, "measured_distance_mm": distance, "passed": passed}
            else:
                intersection = float(first.common(second).Volume)
                passed = intersection <= 0.0
                item = {**gate, "measured_intersection_mm3": intersection, "passed": passed}
            clearance_reports.append(item)
            if not passed:
                errors.append(f"clearance gate failed: {gate['id']}")

        result = {
            "schema_version": "1.0",
            "validator": "read-only-freecad-occt-v1",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS" if not errors else "FAIL",
            "geometry_mutated": False,
            "automatic_healing_used": False,
            "release_holds": contract["release_holds"],
            "shapes": shape_reports,
            "clearance_gates": clearance_reports,
            "errors": errors,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not errors else 1
    finally:
        for document in documents:
            App.closeDocument(document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
