#!/usr/bin/env python3
"""Audit the repaired right eye against the accepted V25 upper context.

The hash-pinned V25 document and V4 repaired-eye STEP are opened read-only.
The script evaluates the repaired eye at zero transform and measures every one
of the 42 accepted upper components. It writes deterministic JSON only. It does
not create a CAD document, trim, move, fuse, mirror, or export geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import FreeCAD as App
import Part


COMPONENT_PATTERN = re.compile(r"__C(\d{3})_")


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


def nearest_vertex_error(shape, point) -> float:
    return min(vertex.Point.distanceToPoint(point) for vertex in shape.Vertexes)


def max_bidirectional_vertex_error(first, second) -> float:
    def directed(source, target) -> float:
        return max(nearest_vertex_error(target, vertex.Point) for vertex in source.Vertexes)

    return max(directed(first, second), directed(second, first))


def component_id(obj) -> str | None:
    text = f"{obj.Name} {obj.Label}"
    if "UPPER_C012" in text:
        return "C012"
    if "UPPER_C027" in text:
        return "C027"
    match = COMPONENT_PATTERN.search(text)
    return f"C{match.group(1)}" if match else None


def copy_view(source, target) -> None:
    if source.ViewObject is None or target.ViewObject is None:
        return
    for name in (
        "ShapeColor",
        "LineColor",
        "PointColor",
        "Transparency",
        "LineWidth",
        "PointSize",
    ):
        if hasattr(source.ViewObject, name) and hasattr(target.ViewObject, name):
            try:
                setattr(target.ViewObject, name, getattr(source.ViewObject, name))
            except Exception:
                pass
    target.ViewObject.Visibility = True


def shape_summary(shape) -> dict[str, object]:
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "face_count": len(shape.Faces),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "bounds": bbox(shape),
    }


def intersection(first, second):
    common = first.common(second)
    return common, float(common.Volume)


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
    replacement_validation_path = root / replacement["validation_path"]
    expected_hashes = {
        "frozen_context_fcstd": context["sha256"],
        "frozen_context_validation": context["validation_sha256"],
        "replacement_eye_step": replacement["sha256"],
        "replacement_eye_validation": replacement["validation_sha256"],
    }
    actual_hashes = {
        "frozen_context_fcstd": sha256_file(context_path),
        "frozen_context_validation": sha256_file(context_validation_path),
        "replacement_eye_step": sha256_file(replacement_path),
        "replacement_eye_validation": sha256_file(replacement_validation_path),
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"hash-pinned input mismatch: {actual_hashes}")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/6 contract and hashes verified", flush=True)

    repaired_eye = Part.Shape()
    repaired_eye.read(str(replacement_path))
    if repaired_eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")
    print("STAGE 2/6 repaired eye imported", flush=True)

    source_document = App.openDocument(str(context_path))
    try:
        if len(source_document.Objects) != int(context["required_object_count"]):
            raise RuntimeError(
                f"unexpected V25 object count: {len(source_document.Objects)}"
            )
        old_eye_object = source_document.getObject(context["eye_object_name"])
        if old_eye_object is None or not hasattr(old_eye_object, "Shape"):
            raise RuntimeError("frozen V25 eye object missing")
        old_eye = old_eye_object.Shape.copy()

        components: dict[str, object] = {}
        for obj in source_document.Objects:
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            identifier = component_id(obj)
            if identifier is None:
                continue
            if identifier in components:
                raise RuntimeError(f"duplicate upper component identity {identifier}")
            components[identifier] = obj
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        if set(components) != expected_ids:
            raise RuntimeError(
                "upper component manifest mismatch: "
                f"missing={sorted(expected_ids - set(components))}, "
                f"unexpected={sorted(set(components) - expected_ids)}"
            )
        print("STAGE 3/6 accepted 42-component manifest verified", flush=True)

        measurements = {}
        boolean_errors = {}
        for identifier in sorted(components):
            component_shape = components[identifier].Shape
            try:
                old_common, old_volume = intersection(old_eye, component_shape)
                repaired_common, repaired_volume = intersection(repaired_eye, component_shape)
                measurements[identifier] = {
                    "source_object_name": components[identifier].Name,
                    "source_object_label": components[identifier].Label,
                    "old_eye_intersection_volume_mm3": old_volume,
                    "repaired_eye_intersection_volume_mm3": repaired_volume,
                    "intersection_delta_mm3": repaired_volume - old_volume,
                    "old_eye_distance_mm": float(old_eye.distToShape(component_shape)[0]),
                    "repaired_eye_distance_mm": float(repaired_eye.distToShape(component_shape)[0]),
                }
            except Exception as exc:
                boolean_errors[identifier] = f"{type(exc).__name__}: {exc}"
        print("STAGE 4/6 component-level collisions measured", flush=True)

        bounds_change = bbox_delta(old_eye, repaired_eye)
        volume_change = float(repaired_eye.Volume - old_eye.Volume)
        vertex_change = max_bidirectional_vertex_error(old_eye, repaired_eye)
        actual_positive = {
            identifier
            for identifier, values in measurements.items()
            if values["repaired_eye_intersection_volume_mm3"]
            > float(gates["positive_intersection_threshold_mm3"])
        }
        known_positive = set(gates["known_residual_contact_components"])
        required_clear = gates["required_clear_components"]
        clearance_checks = {
            identifier: (
                measurements[identifier]["repaired_eye_intersection_volume_mm3"]
                <= float(gates["positive_intersection_threshold_mm3"])
                and measurements[identifier]["repaired_eye_distance_mm"]
                + float(gates["clearance_tolerance_mm"])
                >= float(minimum_clearance)
            )
            for identifier, minimum_clearance in required_clear.items()
        }
        checks = {
            "input_hashes_match": actual_hashes == expected_hashes,
            "source_object_count_matches": len(source_document.Objects)
            == int(context["required_object_count"]),
            "upper_component_count_matches": len(components)
            == int(context["required_upper_component_count"]),
            "all_booleans_completed": not boolean_errors,
            "replacement_valid": bool(repaired_eye.isValid()),
            "replacement_closed": bool(repaired_eye.isClosed()),
            "replacement_solid_count_matches": len(repaired_eye.Solids)
            == int(gates["required_replacement_solid_count"]),
            "replacement_face_count_matches": len(repaired_eye.Faces)
            == int(gates["required_replacement_face_count"]),
            "replacement_bounds_preserved": max(abs(value) for value in bounds_change)
            <= float(gates["maximum_bounds_delta_mm"]),
            "replacement_volume_preserved": abs(volume_change)
            <= float(gates["maximum_absolute_volume_delta_mm3"]),
            "replacement_vertices_preserved": vertex_change
            <= float(gates["maximum_bidirectional_vertex_delta_mm"]),
            "component_intersection_volumes_preserved": not measurements
            or max(abs(values["intersection_delta_mm3"]) for values in measurements.values())
            <= float(gates["maximum_component_intersection_delta_mm3"]),
            "no_unexpected_positive_contacts": not (actual_positive - known_positive),
            "approved_c012_clearance_preserved": clearance_checks["C012"],
            "approved_c027_clearance_preserved": clearance_checks["C027"],
            "rejected_v27_geometry_absent": all("V27" not in obj.Name for obj in source_document.Objects),
        }
        passed = all(checks.values())
        print("STAGE 5/6 fail-closed gates evaluated", flush=True)

        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-repaired-eye-approved-context-audit-v28",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__REVIEW_ONLY_ZERO_GEOMETRY_AUDIT"
            if passed
            else "FAIL__OUTPUT_QUARANTINED",
            "input_hashes": actual_hashes,
            "source_eye": shape_summary(old_eye),
            "replacement_eye": shape_summary(repaired_eye),
            "replacement_preservation": {
                "bounds_delta_mm": bounds_change,
                "volume_delta_mm3": volume_change,
                "maximum_bidirectional_vertex_delta_mm": vertex_change,
            },
            "component_measurements": measurements,
            "boolean_errors": boolean_errors,
            "positive_contact_components": sorted(actual_positive),
            "known_contact_allowlist": sorted(known_positive),
            "unexpected_positive_contacts": sorted(actual_positive - known_positive),
            "required_clear_component_checks": clearance_checks,
            "checks": checks,
            "release_holds": contract["release_holds"],
            "outputs": {
                "validation": str(validation_path.relative_to(root)),
                "geometry_artifact_created": False,
                "upper_geometry_modified": False,
                "new_structural_geometry_created": False,
                "rejected_v27_geometry_used": False,
                "mirrored": False,
                "production_union_created": False,
                "stl_exported": False,
                "sliced": False,
            },
        }
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("STAGE 6/6 validation JSON saved", flush=True)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "positive_contact_components": result[
                        "positive_contact_components"
                    ],
                    "required_clear_component_checks": clearance_checks,
                    "outputs": result["outputs"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if passed else 1
    finally:
        App.closeDocument(source_document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
