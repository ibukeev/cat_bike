#!/usr/bin/env python3
"""Exhaustive, read-only repaired-eye versus right-shell collision audit.

All sources are hash-pinned. Every retained upper component is read from the
V34 review document. The repaired lower C001 is read from its V13 document;
lower C002-C060 are reconstructed in memory from the exact OBJ files pinned by
the V14 manifest. The script writes JSON only and never edits CAD geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def bounds(shape) -> dict[str, list[float]] | None:
    if shape.isNull():
        return None
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def shape_summary(shape) -> dict[str, object]:
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "bounds": bounds(shape),
    }


def aabb_separation_lower_bound(shape, minimum_mm, maximum_mm) -> dict[str, object]:
    box = shape.BoundBox
    shape_minimum = (box.XMin, box.YMin, box.ZMin)
    shape_maximum = (box.XMax, box.YMax, box.ZMax)
    axis_gaps = [
        max(
            float(minimum_mm[index]) - float(shape_maximum[index]),
            float(shape_minimum[index]) - float(maximum_mm[index]),
            0.0,
        )
        for index in range(3)
    ]
    return {
        "axis_gaps_mm": axis_gaps,
        "euclidean_lower_bound_mm": math.sqrt(
            sum(value * value for value in axis_gaps)
        ),
    }


def reconstruct_obj_solid(path: Path, tolerance_mm: float):
    mesh = Mesh.Mesh(str(path))
    shell = Part.Shape()
    shell.makeShapeFromMesh(mesh.Topology, tolerance_mm)
    if shell.isNull() or not shell.isClosed():
        raise RuntimeError(
            f"OBJ reconstruction is not a closed shell: {path} "
            f"null={shell.isNull()} closed={shell.isClosed()}"
        )
    solid = Part.makeSolid(shell)
    if not solid.isValid() or len(solid.Solids) != 1:
        raise RuntimeError(
            f"OBJ reconstruction is not a valid one-solid shape: {path} "
            f"valid={solid.isValid()} solids={len(solid.Solids)}"
        )
    return solid, {
        "mesh_point_count": int(mesh.CountPoints),
        "mesh_facet_count": int(mesh.CountFacets),
        "occt_face_count": len(solid.Faces),
        "occt_volume_mm3": float(solid.Volume),
    }


def measure_pair(eye, component, threshold: float) -> dict[str, object]:
    common = eye.common(component)
    volume = float(common.Volume)
    distance = float(eye.distToShape(component)[0])
    return {
        "intersection_volume_mm3": volume,
        "distance_mm": distance,
        "evaluation_method": "exact_occt_common_and_dist_to_shape",
        "positive_intersection": volume > threshold,
        "intersection_bounds": bounds(common) if volume > threshold else None,
        "component": shape_summary(component),
    }


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    inputs = contract["frozen_inputs"]
    numeric = contract["numeric_contract"]
    threshold = float(numeric["positive_intersection_threshold_mm3"])
    reconstruction_tolerance = float(numeric["mesh_to_occt_tolerance_mm"])

    paths = {
        "upper_fcstd": root / inputs["right_upper_v34"]["fcstd_path"],
        "upper_validation": root
        / inputs["right_upper_v34"]["validation_path"],
        "eye_step": root / inputs["repaired_eye_v4"]["step_path"],
        "lower_validation": root
        / inputs["right_lower_v14"]["validation_path"],
        "lower_c001_fcstd": root
        / inputs["right_lower_component_001_v13"]["fcstd_path"],
    }
    expected_hashes = {
        "upper_fcstd": inputs["right_upper_v34"]["fcstd_sha256"],
        "upper_validation": inputs["right_upper_v34"]["validation_sha256"],
        "eye_step": inputs["repaired_eye_v4"]["step_sha256"],
        "lower_validation": inputs["right_lower_v14"]["validation_sha256"],
        "lower_c001_fcstd": inputs["right_lower_component_001_v13"][
            "fcstd_sha256"
        ],
    }
    actual_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if actual_hashes != expected_hashes:
        raise RuntimeError(
            "hash-pinned top-level input mismatch: "
            + json.dumps(
                {"expected": expected_hashes, "actual": actual_hashes},
                indent=2,
                sort_keys=True,
            )
        )

    upper_validation = json.loads(paths["upper_validation"].read_text())
    lower_validation = json.loads(paths["lower_validation"].read_text())
    expected_upper_ids = {
        f"C{index:03d}" for index in range(1, 43) if index != 9
    }
    manifest_upper_ids = set(upper_validation["retained_manifest"])
    if manifest_upper_ids != expected_upper_ids:
        raise RuntimeError("V34 retained upper manifest is not C001-C042 minus C009")
    lower_entries = lower_validation["unchanged_components_002_through_060"]
    expected_lower_names = {
        f"V11_LOWER_COMPONENT_{index:03d}" for index in range(2, 61)
    }
    lower_entries_by_name = {entry["name"]: entry for entry in lower_entries}
    if set(lower_entries_by_name) != expected_lower_names:
        raise RuntimeError("V14 lower component manifest is not C002-C060")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/6 contracts, hashes, and manifests verified", flush=True)

    eye = Part.Shape()
    eye.read(str(paths["eye_step"]))
    if eye.isNull() or not eye.isValid() or not eye.isClosed() or len(eye.Solids) != 1:
        raise RuntimeError("repaired-eye STEP is not a closed valid one-solid shape")
    print("STAGE 2/6 repaired eye imported", flush=True)

    upper_results: dict[str, dict[str, object]] = {}
    lower_results: dict[str, dict[str, object]] = {}
    boolean_errors: dict[str, str] = {}
    reconstruction_records: dict[str, dict[str, object]] = {}
    nonsewn_aabb_proofs: dict[str, dict[str, object]] = {}
    verified_component_hashes: dict[str, str] = {}

    upper_document = App.openDocument(str(paths["upper_fcstd"]))
    try:
        component_objects = upper_validation["review_objects"]["component_objects"]
        if set(component_objects) != expected_upper_ids:
            raise RuntimeError("V34 component object map does not match retained manifest")
        for identifier in sorted(expected_upper_ids):
            obj = upper_document.getObject(component_objects[identifier])
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                boolean_errors[f"UPPER_{identifier}"] = "missing or null V34 object"
                continue
            try:
                upper_results[identifier] = measure_pair(
                    eye, obj.Shape, threshold
                ) | {
                    "source_object_name": obj.Name,
                    "source_object_label": obj.Label,
                }
            except Exception as exc:
                boolean_errors[f"UPPER_{identifier}"] = (
                    f"{type(exc).__name__}: {exc}"
                )
    finally:
        App.closeDocument(upper_document.Name)
    print("STAGE 3/6 all 41 upper-shell components measured", flush=True)

    lower_c001_document = App.openDocument(str(paths["lower_c001_fcstd"]))
    try:
        obj = lower_c001_document.getObject(
            inputs["right_lower_component_001_v13"]["object_name"]
        )
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            boolean_errors["LOWER_C001"] = "missing or null V13 repaired C001 object"
        else:
            try:
                lower_results["C001"] = measure_pair(
                    eye, obj.Shape, threshold
                ) | {
                    "source_object_name": obj.Name,
                    "source_object_label": obj.Label,
                    "source_kind": "hash-pinned V13 FCStd OCCT solid",
                }
            except Exception as exc:
                boolean_errors["LOWER_C001"] = f"{type(exc).__name__}: {exc}"
    finally:
        App.closeDocument(lower_c001_document.Name)

    for component_number in range(2, 61):
        identifier = f"C{component_number:03d}"
        manifest_name = f"V11_LOWER_COMPONENT_{component_number:03d}"
        entry = lower_entries_by_name[manifest_name]
        source_path = root / entry["source_obj"]
        actual_sha = sha256_file(source_path)
        if actual_sha != entry["source_obj_sha256"]:
            boolean_errors[f"LOWER_{identifier}"] = (
                f"source hash mismatch expected={entry['source_obj_sha256']} "
                f"actual={actual_sha}"
            )
            continue
        verified_component_hashes[identifier] = actual_sha
        try:
            component, reconstruction = reconstruct_obj_solid(
                source_path, reconstruction_tolerance
            )
            reconstruction_records[identifier] = reconstruction
            lower_results[identifier] = measure_pair(
                eye, component, threshold
            ) | {
                "source_object_name": manifest_name,
                "source_path": entry["source_obj"],
                "source_sha256": actual_sha,
                "source_kind": "hash-pinned V14 OBJ reconstructed in memory as OCCT solid",
            }
        except Exception as exc:
            separation = aabb_separation_lower_bound(
                eye, entry["bbox_min_mm"], entry["bbox_max_mm"]
            )
            if separation["euclidean_lower_bound_mm"] > 0.0:
                proof = {
                    "source_object_name": manifest_name,
                    "source_path": entry["source_obj"],
                    "source_sha256": actual_sha,
                    "source_kind": "hash-pinned V14 OBJ with strict AABB separation proof",
                    "evaluation_method": "strict_aabb_separation_lower_bound",
                    "intersection_volume_mm3": 0.0,
                    "distance_mm": None,
                    "distance_lower_bound_mm": separation[
                        "euclidean_lower_bound_mm"
                    ],
                    "axis_gaps_mm": separation["axis_gaps_mm"],
                    "positive_intersection": False,
                    "intersection_bounds": None,
                    "component_manifest": {
                        "bounds": {
                            "minimum_mm": entry["bbox_min_mm"],
                            "maximum_mm": entry["bbox_max_mm"],
                        },
                        "topology": entry["topology"],
                    },
                    "occt_reconstruction_note": f"{type(exc).__name__}: {exc}",
                }
                lower_results[identifier] = proof
                nonsewn_aabb_proofs[identifier] = proof
            else:
                boolean_errors[f"LOWER_{identifier}"] = (
                    f"{type(exc).__name__}: {exc}; AABB separation is zero"
                )
    print("STAGE 4/6 all 60 lower-shell components measured", flush=True)

    positive_upper = sorted(
        identifier
        for identifier, record in upper_results.items()
        if record["positive_intersection"]
    )
    positive_lower = sorted(
        identifier
        for identifier, record in lower_results.items()
        if record["positive_intersection"]
    )
    checks = {
        "top_level_input_hashes_match": actual_hashes == expected_hashes,
        "upper_manifest_is_41_components": len(upper_results)
        == int(inputs["right_upper_v34"]["expected_component_count"]),
        "upper_c009_is_absent": "C009" not in upper_results,
        "lower_manifest_is_60_components": len(lower_results)
        == int(inputs["right_lower_v14"]["expected_component_count"]),
        "all_59_lower_obj_hashes_match": len(verified_component_hashes) == 59,
        "all_59_lower_obj_components_are_resolved": (
            len(reconstruction_records) + len(nonsewn_aabb_proofs) == 59
        ),
        "all_nonsewn_obj_components_have_strict_aabb_separation": all(
            record["distance_lower_bound_mm"] > 0.0
            for record in nonsewn_aabb_proofs.values()
        ),
        "all_boolean_operations_completed": not boolean_errors,
        "zero_positive_upper_intersections": not positive_upper,
        "zero_positive_lower_intersections": not positive_lower,
        "no_geometry_artifact_created": True,
    }
    passed = all(checks.values())
    total_positive_volume = sum(
        float(record["intersection_volume_mm3"])
        for record in (*upper_results.values(), *lower_results.values())
        if record["positive_intersection"]
    )
    print("STAGE 5/6 fail-closed checks evaluated", flush=True)

    result = {
        "schema_version": "1.0",
        "generator": "freecad-right-eye-all-shell-components-conflict-audit-v35",
        "freecad_version": App.Version(),
        "contract_id": contract["contract_id"],
        "status": "PASS__ZERO_EYE_SHELL_INTERSECTIONS__READ_ONLY"
        if passed
        else "FAIL__EYE_INTERSECTS_FROZEN_SHELL__NO_PRINT_RELEASE",
        "input_hashes": actual_hashes,
        "eye": shape_summary(eye),
        "numeric_contract": numeric,
        "upper_component_results": upper_results,
        "lower_component_results": lower_results,
        "lower_obj_reconstruction_records": reconstruction_records,
        "nonsewn_lower_obj_aabb_clearance_proofs": nonsewn_aabb_proofs,
        "verified_lower_component_hashes": verified_component_hashes,
        "boolean_errors": boolean_errors,
        "positive_upper_components": positive_upper,
        "positive_lower_components": positive_lower,
        "positive_intersection_count": len(positive_upper) + len(positive_lower),
        "total_positive_intersection_volume_mm3": total_positive_volume,
        "checks": checks,
        "release_holds": contract["release_holds"],
        "outputs": {
            "validation": str(validation_path.relative_to(root)),
            "geometry_artifact_created": False,
            "cad_document_created_or_modified": False,
            "geometry_modified": False,
            "mirrored": False,
            "production_union_created": False,
            "stl_exported": False,
            "sliced": False,
        },
    }
    validation_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("STAGE 6/6 deterministic validation JSON saved", flush=True)
    print(
        json.dumps(
            {
                "status": result["status"],
                "positive_upper_components": positive_upper,
                "positive_lower_components": positive_lower,
                "positive_intersection_count": result[
                    "positive_intersection_count"
                ],
                "total_positive_intersection_volume_mm3": total_positive_volume,
                "boolean_errors": boolean_errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
