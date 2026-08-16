#!/usr/bin/env python3
"""Substitute the topology-repaired V4 right eye into frozen V18 context.

This generator copies the hash-pinned one-sided V18 review into a new FreeCAD
document and replaces only its V17 eye object with the hash-pinned repaired V4
STEP. It verifies that the repair preserves the approved mating gaps and C046 /
C048 clearances. No source file, mirror, production union, STL, slice, or
G-code is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Mesh
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


def distance_mm(first, second) -> float:
    return float(first.distToShape(second)[0])


def copy_view(source, target) -> None:
    if source.ViewObject is None or target.ViewObject is None:
        return
    for name in ("ShapeColor", "LineColor", "PointColor", "Transparency", "LineWidth", "PointSize"):
        if hasattr(source.ViewObject, name) and hasattr(target.ViewObject, name):
            try:
                setattr(target.ViewObject, name, getattr(source.ViewObject, name))
            except Exception:
                pass
    target.ViewObject.Visibility = source.ViewObject.Visibility


def copy_context_object(document, source):
    if hasattr(source, "Shape") and not source.Shape.isNull():
        target = document.addObject("Part::Feature", source.Name)
        target.Shape = source.Shape.copy()
    elif hasattr(source, "Mesh"):
        target = document.addObject("Mesh::Feature", source.Name)
        target.Mesh = source.Mesh.copy()
    else:
        target = document.addObject("App::FeaturePython", source.Name)
    target.Label = source.Label
    if hasattr(source, "Placement") and hasattr(target, "Placement"):
        target.Placement = source.Placement
    copy_view(source, target)
    return target


def shape_summary(shape) -> dict[str, object]:
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "face_count": len(shape.Faces),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "bounds": bbox(shape),
    }


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    context = contract["frozen_context"]
    replacement = contract["replacement_eye"]
    gates = contract["gates"]
    context_path = root / context["path"]
    context_validation_path = root / context["validation_path"]
    replacement_path = root / replacement["path"]

    actual_hashes = {
        "frozen_context_fcstd": sha256_file(context_path),
        "frozen_context_validation": sha256_file(context_validation_path),
        "replacement_eye_step": sha256_file(replacement_path),
    }
    expected_hashes = {
        "frozen_context_fcstd": context["sha256"],
        "frozen_context_validation": context["validation_sha256"],
        "replacement_eye_step": replacement["sha256"],
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"hash-pinned input mismatch: {actual_hashes}")

    output_dir = root / contract["output"]["directory"]
    review_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/7 contract and hashes verified", flush=True)

    repaired_eye = Part.Shape()
    repaired_eye.read(str(replacement_path))
    if repaired_eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")
    print("STAGE 2/7 replacement STEP imported", flush=True)

    source_document = App.openDocument(str(context_path))
    review_document = None
    try:
        if len(source_document.Objects) != int(gates["required_context_object_count"]):
            raise RuntimeError("unexpected frozen V18 context object count")
        required_names = [
            context["eye_object_name"],
            context["outer_head_flange_object_name"],
            context["lower_head_flange_object_name"],
            context["c046_solid_object_name"],
            context["c048_solid_object_name"],
        ]
        required = {name: source_document.getObject(name) for name in required_names}
        if any(obj is None for obj in required.values()):
            missing = [name for name, obj in required.items() if obj is None]
            raise RuntimeError(f"missing frozen V18 objects: {missing}")

        old_eye = required[context["eye_object_name"]].Shape.copy()
        neighbors = {
            "outer_head_flange": required[context["outer_head_flange_object_name"]].Shape.copy(),
            "lower_head_flange": required[context["lower_head_flange_object_name"]].Shape.copy(),
            "c046": required[context["c046_solid_object_name"]].Shape.copy(),
            "c048": required[context["c048_solid_object_name"]].Shape.copy(),
        }
        baseline_clearances = {name: distance_mm(old_eye, shape) for name, shape in neighbors.items()}
        repaired_clearances = {name: distance_mm(repaired_eye, shape) for name, shape in neighbors.items()}
        clearance_delta = {
            name: repaired_clearances[name] - baseline_clearances[name]
            for name in neighbors
        }
        print("STAGE 3/7 frozen and repaired clearances measured", flush=True)

        review_document = App.newDocument("CAT_HEAD_RIGHT_EYE_TOPOLOGY_REPAIRED_FULL_CONTEXT_REVIEW_V5")
        copied_names = []
        for source in source_document.Objects:
            if source.Name == context["eye_object_name"]:
                target = review_document.addObject("Part::Feature", replacement["object_name"])
                target.Label = replacement["label"]
                target.Shape = repaired_eye.copy()
                copy_view(source, target)
                target.addProperty("App::PropertyString", "ReplacesObject", "ChangeControl")
                target.ReplacesObject = source.Name
                target.addProperty("App::PropertyString", "ContractId", "ChangeControl")
                target.ContractId = contract["contract_id"]
                target.addProperty("App::PropertyString", "ReleaseState", "ChangeControl")
                target.ReleaseState = "REVIEW_ONLY__NO_MIRROR_NO_STL_NO_PRINT"
            else:
                target = copy_context_object(review_document, source)
            copied_names.append(target.Name)
        review_document.recompute()
        print("STAGE 4/7 V5 review context assembled", flush=True)

        bounds_change = bbox_delta(old_eye, repaired_eye)
        volume_change = float(repaired_eye.Volume - old_eye.Volume)
        vertex_change = max_bidirectional_vertex_error(old_eye, repaired_eye)
        checks = {
            "input_hashes_match": actual_hashes == expected_hashes,
            "context_object_count_preserved": len(copied_names) == int(gates["required_context_object_count"]),
            "replacement_valid": bool(repaired_eye.isValid()),
            "replacement_closed": bool(repaired_eye.isClosed()),
            "replacement_solid_count": len(repaired_eye.Solids) == int(gates["required_replacement_solid_count"]),
            "replacement_face_count": len(repaired_eye.Faces) == int(gates["required_replacement_face_count"]),
            "bounds_preserved": max(abs(value) for value in bounds_change) <= float(gates["maximum_bounds_delta_mm"]),
            "volume_preserved": abs(volume_change) <= float(gates["maximum_absolute_volume_delta_mm3"]),
            "vertices_preserved_within_topology_tolerance": vertex_change <= float(gates["maximum_bidirectional_vertex_delta_mm"]),
            "all_clearance_changes_within_tolerance": max(abs(value) for value in clearance_delta.values()) <= float(gates["maximum_clearance_change_mm"]),
            "outer_head_mating_gap_preserved": abs(repaired_clearances["outer_head_flange"] - float(gates["required_mating_gap_mm"])) <= float(gates["mating_gap_tolerance_mm"]),
            "lower_head_mating_gap_preserved": abs(repaired_clearances["lower_head_flange"] - float(gates["required_mating_gap_mm"])) <= float(gates["mating_gap_tolerance_mm"]),
            "c046_clearance_passes": repaired_clearances["c046"] >= float(gates["minimum_c046_clearance_mm"]),
            "c048_clearance_passes": repaired_clearances["c048"] >= float(gates["minimum_c048_clearance_mm"]),
        }
        passed = all(checks.values())
        print("STAGE 5/7 preservation and clearance gates measured", flush=True)

        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-eye-topology-repaired-full-context-review-v5",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__REVIEW_ONLY_CONTEXT" if passed else "FAIL__OUTPUT_QUARANTINED",
            "input_hashes": actual_hashes,
            "source_eye": shape_summary(old_eye),
            "replacement_eye": shape_summary(repaired_eye),
            "preservation": {
                "bounds_delta_mm": bounds_change,
                "volume_delta_mm3": volume_change,
                "maximum_bidirectional_vertex_delta_mm": vertex_change,
            },
            "clearances_mm": {
                name: {
                    "frozen_v18": baseline_clearances[name],
                    "repaired_v5": repaired_clearances[name],
                    "delta": clearance_delta[name],
                }
                for name in neighbors
            },
            "context": {
                "source_object_count": len(source_document.Objects),
                "output_object_count": len(copied_names),
                "copied_object_names": copied_names,
                "only_substitution": context["eye_object_name"],
                "zero_transform": True,
            },
            "checks": checks,
            "release_holds": contract["release_holds"],
            "outputs": {
                "fcstd": str(review_path.relative_to(root)),
                "validation": str(validation_path.relative_to(root)),
                "mirrored": False,
                "production_union_created": False,
                "stl_exported": False,
                "sliced": False,
            },
        }
        if not passed:
            validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1

        review_document.saveAs(str(review_path))
        print("STAGE 6/7 V5 review FCStd saved", flush=True)
        result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
        validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("STAGE 7/7 validation saved", flush=True)
        print(json.dumps({"status": result["status"], "checks": checks, "clearances_mm": result["clearances_mm"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
        return 0
    finally:
        if review_document is not None:
            App.closeDocument(review_document.Name)
        App.closeDocument(source_document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
