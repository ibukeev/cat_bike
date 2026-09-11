#!/usr/bin/env python3
"""Regression-test V2 preservation against canonical V34 and quarantine evidence."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import FreeCAD as App

import compare_fcstd_preservation_v2 as comparator
import fcstd_preservation_v2 as preservation
import validate_iteration_v2 as preflight
from probe_freecad_runtime_v2 import runtime_record


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--existing-candidate", type=Path, required=True)
    parser.add_argument("--existing-snapshot", type=Path, required=True)
    parser.add_argument("--target-object", required=True)
    parser.add_argument("--changed-protected-object", required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def load_inventory(path: Path) -> dict[str, dict[str, Any]]:
    document = App.openDocument(str(path))
    try:
        return comparator.inventory(document, path)
    finally:
        App.closeDocument(document.Name)


def save_no_op_roundtrip(source: Path, destination: Path) -> None:
    document = App.openDocument(str(source))
    try:
        document.saveAs(str(destination))
    finally:
        App.closeDocument(document.Name)


def mutate_protected_shape(
    source: Path,
    destination: Path,
    object_name: str,
) -> None:
    document = App.openDocument(str(source))
    try:
        document.saveAs(str(destination))
        obj = document.getObject(object_name)
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            raise RuntimeError(f"protected test object is not shaped: {object_name}")
        changed_shape = obj.Shape.copy()
        changed_shape.translate(App.Vector(0.125, 0.0, 0.0))
        obj.Shape = changed_shape
        document.recompute()
        document.save()
    finally:
        App.closeDocument(document.Name)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repository_root = preflight.find_repository_root(args.baseline)
    baseline_manifest = preflight.load_json(args.baseline)
    runtime_manifest = preflight.load_json(args.runtime_manifest)
    baseline_errors = preflight.validate_baseline(
        baseline_manifest,
        repository_root,
        verify_files=True,
    )
    runtime_errors = preflight.validate_runtime_manifest(
        runtime_manifest,
        repository_root,
        verify_files=True,
    )
    if baseline_errors or runtime_errors:
        result = {
            "schema_version": "2.0",
            "status": "FAIL__PINNED_INPUTS",
            "errors": baseline_errors + runtime_errors,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    baseline_path = repository_root / baseline_manifest["assembly"]["path"]
    existing_candidate = args.existing_candidate
    if not existing_candidate.is_absolute():
        existing_candidate = repository_root / existing_candidate
    existing_snapshot = args.existing_snapshot
    if not existing_snapshot.is_absolute():
        existing_snapshot = repository_root / existing_snapshot
    report_path = args.report
    if not report_path.is_absolute():
        report_path = repository_root / report_path

    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    observed_runtime = runtime_record()
    runtime_matches = observed_runtime == expected_runtime

    with tempfile.TemporaryDirectory(
        prefix="cat-head-preservation-v2-",
        dir="/tmp",
    ) as temporary_name:
        temporary = Path(temporary_name)
        reference_path = temporary / "reference-no-op.FCStd"
        control_path = temporary / "control-no-op.FCStd"
        changed_path = temporary / "changed-protected.FCStd"
        changed_reference_path = temporary / "changed-protected-no-op.FCStd"

        save_no_op_roundtrip(baseline_path, reference_path)
        save_no_op_roundtrip(baseline_path, control_path)
        reference_shapes_before = preservation.raw_shape_digests(reference_path)
        control_shapes_before = preservation.raw_shape_digests(control_path)
        reference_presentation = preservation.restore_canonical_presentation(
            baseline_path,
            reference_path,
        )
        control_presentation = preservation.restore_canonical_presentation(
            baseline_path,
            control_path,
        )
        presentation_kept_shapes_exact = (
            reference_shapes_before == preservation.raw_shape_digests(reference_path)
            and control_shapes_before == preservation.raw_shape_digests(control_path)
        )

        baseline_inventory = load_inventory(baseline_path)
        reference_inventory = load_inventory(reference_path)
        control_inventory = load_inventory(control_path)
        baseline_names = set(baseline_inventory)
        reference_names = set(reference_inventory)
        control_names = set(control_inventory)
        reference_stable_differences = comparator.stable_inventory_differences(
            baseline_inventory,
            reference_inventory,
            baseline_names & reference_names,
        )
        control_stable_differences = comparator.stable_inventory_differences(
            baseline_inventory,
            control_inventory,
            baseline_names & control_names,
        )
        no_op_shapes = preservation.raw_shape_comparison(
            reference_path,
            control_path,
        )
        no_op_pass = (
            runtime_matches
            and baseline_names == reference_names == control_names
            and not reference_stable_differences
            and not control_stable_differences
            and no_op_shapes["status"] == "PASS"
            and reference_presentation["status"] == "PASS"
            and control_presentation["status"] == "PASS"
            and presentation_kept_shapes_exact
        )

        mutate_protected_shape(
            baseline_path,
            changed_path,
            args.changed_protected_object,
        )
        preservation.capture_single_no_op_backup(
            changed_path,
            changed_reference_path,
        )
        changed_reference_shapes_before_presentation = (
            preservation.raw_shape_digests(changed_reference_path)
        )
        changed_shapes_before_presentation = preservation.raw_shape_digests(
            changed_path
        )
        changed_reference_presentation = (
            preservation.restore_canonical_presentation(
                baseline_path,
                changed_reference_path,
            )
        )
        changed_presentation = preservation.restore_canonical_presentation(
            baseline_path,
            changed_path,
        )
        changed_reference_shapes_after_presentation = (
            preservation.raw_shape_digests(changed_reference_path)
        )
        changed_shapes_after_presentation = preservation.raw_shape_digests(
            changed_path
        )
        changed_shape_comparison = preservation.raw_shape_comparison(
            changed_reference_path,
            changed_path,
        )
        detected_names = sorted(changed_shape_comparison["mismatches"])
        deliberate_change_detected = (
            changed_shape_comparison["status"] == "FAIL"
            and detected_names == [args.changed_protected_object]
            and not changed_shape_comparison["missing_shape_entries"]
            and not changed_shape_comparison["added_shape_entries"]
            and changed_reference_presentation["status"] == "PASS"
            and changed_presentation["status"] == "PASS"
            and changed_reference_shapes_before_presentation
            == changed_reference_shapes_after_presentation
            and changed_shapes_before_presentation == changed_shapes_after_presentation
        )

    existing_shape_comparison = preservation.raw_shape_comparison(
        existing_snapshot,
        existing_candidate,
        excluded_objects={args.target_object},
    )
    existing_candidate_matches = (
        existing_shape_comparison["status"] == "PASS"
        and existing_shape_comparison["checked_count"] == 44
        and not existing_shape_comparison["mismatches"]
    )

    overall_pass = (
        no_op_pass
        and deliberate_change_detected
        and existing_candidate_matches
    )
    result = {
        "schema_version": "2.0",
        "status": "PASS" if overall_pass else "FAIL",
        "runtime": {
            "manifest": str(args.runtime_manifest),
            "manifest_sha256": preflight.sha256_file(args.runtime_manifest),
            "expected": expected_runtime,
            "observed": observed_runtime,
            "matches": runtime_matches,
        },
        "canonical": {
            "path": baseline_manifest["assembly"]["path"],
            "sha256": preflight.sha256_file(baseline_path),
            "document_program_version": preservation.document_program_version(
                baseline_path
            ),
        },
        "no_op_control": {
            "status": "PASS" if no_op_pass else "FAIL",
            "reference_object_count": len(reference_inventory),
            "control_object_count": len(control_inventory),
            "reference_stable_differences": reference_stable_differences,
            "control_stable_differences": control_stable_differences,
            "shape_comparison": no_op_shapes,
            "reference_presentation": reference_presentation,
            "control_presentation": control_presentation,
            "presentation_restore_kept_shape_entries_exact": (
                presentation_kept_shapes_exact
            ),
        },
        "deliberately_changed_protected_object": {
            "object": args.changed_protected_object,
            "status": (
                "PASS__CHANGE_DETECTED"
                if deliberate_change_detected
                else "FAIL__CHANGE_NOT_DETECTED_EXACTLY"
            ),
            "detected_objects": detected_names,
            "shape_comparison": changed_shape_comparison,
            "reference_presentation": changed_reference_presentation,
            "presentation": changed_presentation,
            "presentation_restore_kept_shape_entries_exact": (
                changed_reference_shapes_before_presentation
                == changed_reference_shapes_after_presentation
                and
                changed_shapes_before_presentation
                == changed_shapes_after_presentation
            ),
        },
        "existing_quarantine_evidence": {
            "candidate": str(args.existing_candidate),
            "candidate_sha256": preflight.sha256_file(existing_candidate),
            "pre_mutation_snapshot": str(args.existing_snapshot),
            "pre_mutation_snapshot_sha256": preflight.sha256_file(
                existing_snapshot
            ),
            "target_excluded": args.target_object,
            "status": "PASS" if existing_candidate_matches else "FAIL",
            "protected_shape_comparison": existing_shape_comparison,
        },
        "temporary_geometry_retained": False,
        "candidate_geometry_mutated": False,
        "errors": [
            message
            for passed, message in (
                (runtime_matches, "runtime mismatch"),
                (no_op_pass, "no-op control failed"),
                (
                    deliberate_change_detected,
                    "deliberately changed protected object was not detected exactly",
                ),
                (
                    existing_candidate_matches,
                    "existing candidate does not match its pre-mutation snapshot",
                ),
            )
            if not passed
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
