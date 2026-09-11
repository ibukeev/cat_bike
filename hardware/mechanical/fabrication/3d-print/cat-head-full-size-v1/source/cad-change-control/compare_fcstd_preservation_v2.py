#!/usr/bin/env python3
"""Prove that one V2 candidate changed only its authorized target object."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App

import fcstd_preservation_v2 as preservation
import validate_iteration_v2 as preflight
from probe_freecad_runtime_v2 import runtime_record


PLACEMENT_MUTATIONS = {"translate", "rotate"}
SHAPE_FIELD = "shape_sha256_same_runtime_archive"
STABLE_FIELDS = {
    "internal_name",
    "label",
    "type",
    "placement",
    "visibility",
    "group_children",
    "parent_groups",
}
PROTECTED_STABLE_FIELDS = {*STABLE_FIELDS, "property_types"}
ALLOW_MISSING_CANONICAL_GUI_DOCUMENT = False


def placement_record(obj: Any) -> dict[str, list[float]] | None:
    if not hasattr(obj, "Placement"):
        return None
    placement = obj.Placement
    return {
        "base": [
            float(placement.Base.x),
            float(placement.Base.y),
            float(placement.Base.z),
        ],
        "rotation_q": [float(value) for value in placement.Rotation.Q],
    }


def group_names(obj: Any) -> list[str]:
    if not hasattr(obj, "Group"):
        return []
    return sorted(child.Name for child in obj.Group)


def parent_group_names(document: Any, object_name: str) -> list[str]:
    parents = []
    for possible_parent in document.Objects:
        if hasattr(possible_parent, "Group") and any(
            child.Name == object_name for child in possible_parent.Group
        ):
            parents.append(possible_parent.Name)
    return sorted(parents)


def object_record(
    document: Any,
    obj: Any,
    shape_digests: dict[str, str],
    visibility: dict[str, bool],
) -> dict[str, Any]:
    return {
        "internal_name": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
        SHAPE_FIELD: shape_digests.get(obj.Name),
        "placement": placement_record(obj),
        "visibility": visibility.get(obj.Name),
        "group_children": group_names(obj),
        "parent_groups": parent_group_names(document, obj.Name),
        "property_types": {
            name: obj.getTypeIdOfProperty(name)
            for name in sorted(obj.PropertiesList)
        },
    }


def inventory(document: Any, fcstd_path: Path) -> dict[str, dict[str, Any]]:
    shape_digests = preservation.raw_shape_digests(fcstd_path)
    visibility = preservation.visibility_map(
        fcstd_path,
        allow_missing_gui_document=ALLOW_MISSING_CANONICAL_GUI_DOCUMENT,
    )
    return {
        obj.Name: object_record(document, obj, shape_digests, visibility)
        for obj in document.Objects
    }


def field_differences(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    fields: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    selected = fields if fields is not None else set(baseline) | set(candidate)
    return {
        key: {"baseline": baseline.get(key), "candidate": candidate.get(key)}
        for key in sorted(selected)
        if baseline.get(key) != candidate.get(key)
    }


def stable_inventory_differences(
    reference: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    names: set[str],
    fields: set[str] = PROTECTED_STABLE_FIELDS,
) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for name in sorted(names):
        differences = field_differences(
            reference[name],
            candidate[name],
            fields,
        )
        if differences:
            result[name] = differences
    return result


def compare_target(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    mutation_kind: str,
) -> list[str]:
    errors: list[str] = []
    stable_diffs = field_differences(reference, candidate, STABLE_FIELDS)
    if stable_diffs:
        errors.append(f"target changed unauthorized metadata: {sorted(stable_diffs)}")

    reference_shape = reference[SHAPE_FIELD]
    candidate_shape = candidate[SHAPE_FIELD]
    reference_placement = reference["placement"]
    candidate_placement = candidate["placement"]
    if reference_shape is None or candidate_shape is None:
        errors.append("target must have a Shape.brp entry in both same-runtime files")
        return errors

    if mutation_kind in PLACEMENT_MUTATIONS:
        if reference_shape != candidate_shape:
            errors.append("placement-only target mutation also changed target shape")
        if reference_placement == candidate_placement:
            errors.append("placement-only target mutation did not change placement")
    else:
        if reference_shape == candidate_shape:
            errors.append("geometry target mutation did not change target shape")
        if reference_placement != candidate_placement:
            errors.append("geometry-only target mutation also changed target placement")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validation = preflight.validate_files(
        args.baseline,
        args.contract,
        verify_files=True,
        require_new_output=False,
    )
    if validation["status"] != "PASS":
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 1

    repository_root = Path(validation["repository_root"])
    baseline_manifest = preflight.load_json(args.baseline)
    contract = preflight.load_json(args.contract)
    baseline_path = repository_root / baseline_manifest["assembly"]["path"]
    candidate_path = repository_root / contract["output"]["candidate_fcstd"]
    snapshot_path = repository_root / contract["output"]["no_op_snapshot_fcstd"]
    output_dir = repository_root / contract["output"]["directory"]
    expected_report = output_dir / "preservation-report.json"
    report_path = args.report
    if not report_path.is_absolute():
        report_path = repository_root / report_path
    if report_path.resolve() != expected_report.resolve():
        print(
            f"report must be exactly {expected_report.relative_to(repository_root)}",
            file=sys.stderr,
        )
        return 1

    runner_result_path = output_dir / "runner-result.json"
    if not runner_result_path.is_file():
        print(
            "runner-result.json is missing; candidate bypassed the bounded runner",
            file=sys.stderr,
        )
        return 1
    runner_result = preflight.load_json(runner_result_path)
    if not str(runner_result.get("status", "")).startswith("CANDIDATE_READY"):
        print(
            "runner did not release this candidate to the preservation gate",
            file=sys.stderr,
        )
        return 1
    if not candidate_path.is_file():
        print(f"candidate FCStd is missing: {candidate_path}", file=sys.stderr)
        return 1
    if not snapshot_path.is_file():
        print(f"no-op snapshot is missing: {snapshot_path}", file=sys.stderr)
        return 1

    candidate_sha256 = preflight.sha256_file(candidate_path)
    snapshot_sha256 = preflight.sha256_file(snapshot_path)
    if runner_result.get("candidate", {}).get("sha256") != candidate_sha256:
        print("candidate changed after the bounded runner completed", file=sys.stderr)
        return 1
    runner_snapshot = runner_result.get("no_op_snapshot", {})
    if runner_snapshot.get("path") != contract["output"]["no_op_snapshot_fcstd"]:
        print("runner recorded the wrong no-op snapshot path", file=sys.stderr)
        return 1
    if runner_snapshot.get("sha256") != snapshot_sha256:
        print("no-op snapshot changed after the bounded runner completed", file=sys.stderr)
        return 1

    runtime_reference = contract["runtime"]
    runtime_manifest_path = repository_root / runtime_reference["manifest_path"]
    runtime_manifest = preflight.load_json(runtime_manifest_path)
    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    observed_runtime = runtime_record()
    runtime_errors: list[str] = []
    runner_runtime = runner_result.get("runtime", {})
    if runner_runtime.get("status") != "PASS":
        runtime_errors.append("runner runtime verification did not pass")
    if runner_runtime.get("manifest_path") != runtime_reference["manifest_path"]:
        runtime_errors.append("runner used a different runtime manifest path")
    if runner_runtime.get("manifest_sha256") != runtime_reference["manifest_sha256"]:
        runtime_errors.append("runner used a different runtime manifest digest")
    if observed_runtime != expected_runtime:
        runtime_errors.append("comparator runtime does not match the approved runtime")
    expected_program_version = runtime_manifest["freecad"]["program_version"]
    candidate_program_version = preservation.document_program_version(candidate_path)
    snapshot_program_version = preservation.document_program_version(snapshot_path)
    if candidate_program_version != expected_program_version:
        runtime_errors.append("candidate ProgramVersion differs from approved runtime")
    if snapshot_program_version != expected_program_version:
        runtime_errors.append("no-op snapshot ProgramVersion differs from approved runtime")

    candidate_presentation = preservation.presentation_comparison(
        baseline_path,
        candidate_path,
        allow_missing_gui_document=ALLOW_MISSING_CANONICAL_GUI_DOCUMENT,
    )
    snapshot_presentation = preservation.presentation_comparison(
        baseline_path,
        snapshot_path,
        allow_missing_gui_document=ALLOW_MISSING_CANONICAL_GUI_DOCUMENT,
    )
    presentation_errors: list[str] = []
    if candidate_presentation["status"] != "PASS":
        presentation_errors.append(
            "candidate does not retain canonical GUI/presentation entries"
        )
    if snapshot_presentation["status"] != "PASS":
        presentation_errors.append(
            "no-op snapshot does not retain canonical GUI/presentation entries"
        )

    baseline_document = App.openDocument(str(baseline_path))
    snapshot_document = App.openDocument(str(snapshot_path))
    candidate_document = App.openDocument(str(candidate_path))
    try:
        baseline_inventory = inventory(baseline_document, baseline_path)
        snapshot_inventory = inventory(snapshot_document, snapshot_path)
        candidate_inventory = inventory(candidate_document, candidate_path)
    finally:
        App.closeDocument(candidate_document.Name)
        App.closeDocument(snapshot_document.Name)
        App.closeDocument(baseline_document.Name)

    baseline_names = set(baseline_inventory)
    snapshot_names = set(snapshot_inventory)
    candidate_names = set(candidate_inventory)
    snapshot_missing_objects = sorted(baseline_names - snapshot_names)
    snapshot_added_objects = sorted(snapshot_names - baseline_names)
    missing_objects = sorted(baseline_names - candidate_names)
    added_objects = sorted(candidate_names - baseline_names)

    shared_snapshot_names = baseline_names & snapshot_names
    snapshot_roundtrip_differences = stable_inventory_differences(
        baseline_inventory,
        snapshot_inventory,
        shared_snapshot_names,
    )

    target = contract["target_object"]
    shared_protected_names = (baseline_names & candidate_names) - {target}
    protected_differences = stable_inventory_differences(
        baseline_inventory,
        candidate_inventory,
        shared_protected_names,
    )
    protected_shape_comparison = preservation.raw_shape_comparison(
        snapshot_path,
        candidate_path,
        excluded_objects={target},
    )
    for name, difference in protected_shape_comparison["mismatches"].items():
        protected_differences.setdefault(name, {})[SHAPE_FIELD] = {
            "baseline": difference["reference_sha256"],
            "candidate": difference["candidate_sha256"],
        }
    for name in protected_shape_comparison["missing_shape_entries"]:
        protected_differences.setdefault(name, {})[SHAPE_FIELD] = {
            "baseline": preservation.raw_shape_digests(snapshot_path).get(name),
            "candidate": None,
        }
    for name in protected_shape_comparison["added_shape_entries"]:
        protected_differences.setdefault(name, {})[SHAPE_FIELD] = {
            "baseline": None,
            "candidate": preservation.raw_shape_digests(candidate_path).get(name),
        }

    target_errors: list[str] = []
    target_differences: dict[str, dict[str, Any]] = {}
    if target not in baseline_inventory:
        target_errors.append("target is missing from the canonical baseline")
    elif target not in snapshot_inventory:
        target_errors.append("target is missing from the no-op snapshot")
    elif target not in candidate_inventory:
        target_errors.append("target was deleted from the candidate")
    else:
        target_reference = dict(baseline_inventory[target])
        target_reference[SHAPE_FIELD] = snapshot_inventory[target][SHAPE_FIELD]
        target_differences = field_differences(
            target_reference,
            candidate_inventory[target],
        )
        target_errors.extend(
            compare_target(
                target_reference,
                candidate_inventory[target],
                contract["allowed_mutations"][0]["kind"],
            )
        )

    errors: list[str] = []
    errors.extend(runtime_errors)
    errors.extend(presentation_errors)
    if snapshot_missing_objects:
        errors.append(f"no-op snapshot deleted objects: {snapshot_missing_objects}")
    if snapshot_added_objects:
        errors.append(f"no-op snapshot added objects: {snapshot_added_objects}")
    if snapshot_roundtrip_differences:
        errors.append(
            f"{len(snapshot_roundtrip_differences)} objects changed stable "
            "metadata during the no-op round trip"
        )
    if missing_objects:
        errors.append(f"objects deleted: {missing_objects}")
    if added_objects:
        errors.append(f"objects added: {added_objects}")
    if protected_differences:
        errors.append(
            f"{len(protected_differences)} protected objects changed: "
            f"{sorted(protected_differences)}"
        )
    errors.extend(target_errors)

    result = {
        "schema_version": "2.0",
        "iteration_id": contract["iteration_id"],
        "status": "PASS__READY_FOR_FIXED_VIEW_REVIEW" if not errors else "FAIL__QUARANTINED",
        "runtime": {
            "manifest_path": runtime_reference["manifest_path"],
            "manifest_sha256": runtime_reference["manifest_sha256"],
            "expected": expected_runtime,
            "observed": observed_runtime,
            "candidate_program_version": candidate_program_version,
            "snapshot_program_version": snapshot_program_version,
            "errors": runtime_errors,
        },
        "baseline": {
            "path": baseline_manifest["assembly"]["path"],
            "sha256": preflight.sha256_file(baseline_path),
            "program_version": preservation.document_program_version(baseline_path),
            "object_count": len(baseline_inventory),
        },
        "no_op_snapshot": {
            "path": contract["output"]["no_op_snapshot_fcstd"],
            "sha256": snapshot_sha256,
            "object_count": len(snapshot_inventory),
            "missing_objects": snapshot_missing_objects,
            "added_objects": snapshot_added_objects,
            "stable_metadata_differences": snapshot_roundtrip_differences,
            "presentation": snapshot_presentation,
        },
        "candidate": {
            "path": contract["output"]["candidate_fcstd"],
            "sha256": candidate_sha256,
            "object_count": len(candidate_inventory),
            "presentation": candidate_presentation,
        },
        "shape_identity": {
            "reference": "same-runtime pre-mutation no-op snapshot",
            "algorithm": "SHA-256 of raw FCStd <ObjectName>.Shape.brp entry bytes",
            "protected": protected_shape_comparison,
        },
        "target_object": target,
        "mutation_kind": contract["allowed_mutations"][0]["kind"],
        "missing_objects": missing_objects,
        "added_objects": added_objects,
        "protected_differences": protected_differences,
        "target_differences": target_differences,
        "target_errors": target_errors,
        "errors": errors,
        "occt_release_validation_run": False,
        "visual_approval_status": "PENDING",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
