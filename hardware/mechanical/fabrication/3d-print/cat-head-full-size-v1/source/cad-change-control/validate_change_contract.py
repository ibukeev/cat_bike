#!/usr/bin/env python3
"""Fail-closed validation for cat-head CAD manifests and change contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {
    "frozen_accepted",
    "approved_isolated_not_production",
    "proposed_not_approved",
    "rejected_visual",
    "known_bad_diagnostic",
    "evidence_only",
}
BLOCKED_SOURCE_STATUSES = {"rejected_visual", "known_bad_diagnostic"}
ALLOWED_FORMATS = {"step", "fcstd", "obj", "json"}
ALLOWED_OPERATIONS = {"inspect", "measure"}
OUTPUT_PREFIX = Path("reports/generated/cat-head-cad-validation")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def find_repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValueError("cannot locate repository root containing .git")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty relative path")
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay inside the repository: {value!r}")
        return None
    return path


def validate_manifest(
    manifest: dict[str, Any],
    repository_root: Path,
    verify_files: bool,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    if manifest.get("schema_version") != "1.0":
        errors.append("manifest schema_version must be '1.0'")
    if manifest.get("project") != "cat-head-full-size-v1":
        errors.append("manifest project must be 'cat-head-full-size-v1'")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return {}, errors + ["manifest artifacts must be a non-empty array"]

    by_id: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be an object")
            continue
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if artifact_id in by_id:
            errors.append(f"duplicate artifact id: {artifact_id}")
            continue
        by_id[artifact_id] = artifact

        path = safe_relative_path(artifact.get("path"), f"{label}.path", errors)
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{label}.sha256 must be a 64-character digest")
        elif any(char not in "0123456789abcdef" for char in digest):
            errors.append(f"{label}.sha256 must be lowercase hexadecimal")
        if artifact.get("format") not in ALLOWED_FORMATS:
            errors.append(f"{label}.format is unsupported")
        if artifact.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{label}.status is unsupported")

        if verify_files and path is not None:
            absolute = repository_root / path
            if not absolute.is_file():
                errors.append(f"{artifact_id}: file does not exist: {path}")
            elif isinstance(digest, str) and sha256_file(absolute) != digest:
                errors.append(f"{artifact_id}: SHA-256 mismatch for {path}")

    return by_id, errors


def validate_contract(
    contract: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "1.0":
        errors.append("contract schema_version must be '1.0'")
    if contract.get("mode") not in {"read_only_validation", "isolated_proposal"}:
        errors.append("contract mode is unsupported")
    if contract.get("geometry_changes_allowed") is not False:
        errors.append("controlled validator contracts cannot allow geometry changes")

    target = contract.get("target_owner")
    if target not in artifacts:
        errors.append(f"target_owner is undeclared: {target!r}")
    elif artifacts[target].get("status") in BLOCKED_SOURCE_STATUSES:
        errors.append(f"target_owner uses blocked status: {artifacts[target]['status']}")

    protected = contract.get("protected_owners")
    if not isinstance(protected, list):
        errors.append("protected_owners must be an array")
        protected = []
    for artifact_id in protected:
        if artifact_id not in artifacts:
            errors.append(f"protected owner is undeclared: {artifact_id!r}")
    if target in protected:
        errors.append("target_owner cannot also be a protected owner")

    operations = contract.get("permitted_operations")
    if not isinstance(operations, list) or not operations:
        errors.append("permitted_operations must be a non-empty array")
    elif not set(operations).issubset(ALLOWED_OPERATIONS):
        errors.append("only inspect and measure operations are permitted")

    inspect_ids = contract.get("artifacts_to_inspect")
    if not isinstance(inspect_ids, list) or not inspect_ids:
        errors.append("artifacts_to_inspect must be a non-empty array")
        inspect_ids = []
    if target not in inspect_ids:
        errors.append("target_owner must be present in artifacts_to_inspect")
    for artifact_id in inspect_ids:
        if artifact_id not in artifacts:
            errors.append(f"inspection artifact is undeclared: {artifact_id!r}")
        elif artifacts[artifact_id].get("status") in BLOCKED_SOURCE_STATUSES:
            errors.append(f"inspection source {artifact_id!r} has blocked status")

    shape_gates = contract.get("shape_gates")
    if not isinstance(shape_gates, dict):
        errors.append("shape_gates must be an object")
    else:
        for key in ("require_valid", "require_closed", "require_clean_occt_check"):
            if not isinstance(shape_gates.get(key), bool):
                errors.append(f"shape_gates.{key} must be boolean")
        if shape_gates.get("require_clean_occt_check") is not True:
            errors.append("shape_gates.require_clean_occt_check must be true")
        count = shape_gates.get("required_solid_count")
        if not isinstance(count, int) or count < 0:
            errors.append("shape_gates.required_solid_count must be non-negative")

    clearance_gates = contract.get("clearance_gates")
    if not isinstance(clearance_gates, list):
        errors.append("clearance_gates must be an array")
        clearance_gates = []
    seen_pairs: set[frozenset[str]] = set()
    for index, gate in enumerate(clearance_gates):
        label = f"clearance_gates[{index}]"
        if not isinstance(gate, dict):
            errors.append(f"{label} must be an object")
            continue
        first, second = gate.get("first"), gate.get("second")
        if first == second:
            errors.append(f"{label} cannot compare an artifact with itself")
        for artifact_id in (first, second):
            if artifact_id not in inspect_ids:
                errors.append(f"{label} references artifact not inspected: {artifact_id!r}")
        pair = frozenset((str(first), str(second)))
        if pair in seen_pairs:
            errors.append(f"{label} duplicates a pair and would double-count clearance")
        seen_pairs.add(pair)
        mode = gate.get("mode")
        if mode == "actual_geometry":
            if "maximum_intersection_mm3" in gate:
                errors.append(f"{label} mixes actual-geometry and keepout policies")
            value = gate.get("minimum_distance_mm")
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"{label}.minimum_distance_mm must be non-negative")
        elif mode == "inflated_keepout":
            if "minimum_distance_mm" in gate:
                errors.append(f"{label} mixes keepout and actual-geometry policies")
            if gate.get("maximum_intersection_mm3") != 0:
                errors.append(f"{label}.maximum_intersection_mm3 must be exactly zero")
        else:
            errors.append(f"{label}.mode is unsupported")

    output = safe_relative_path(contract.get("output_directory"), "output_directory", errors)
    if output is not None:
        try:
            output.relative_to(OUTPUT_PREFIX)
        except ValueError:
            errors.append(f"output_directory must be under {OUTPUT_PREFIX}")
        artifact_paths = {Path(item["path"]) for item in artifacts.values()}
        if output in artifact_paths:
            errors.append("output_directory collides with a baseline artifact")

    holds = contract.get("release_holds")
    expected_holds = {"mirror", "production_union", "stl", "gcode", "asa_print"}
    if not isinstance(holds, dict) or set(holds) != expected_holds:
        errors.append("release_holds must name exactly all five release stages")
    elif any(value is not False for value in holds.values()):
        errors.append("all release stages must remain held in validation contracts")

    return errors


def validate_files(
    manifest_path: Path,
    contract_path: Path,
    verify_files: bool = False,
) -> dict[str, Any]:
    repository_root = find_repository_root(manifest_path)
    manifest = load_json(manifest_path)
    contract = load_json(contract_path)
    artifacts, errors = validate_manifest(manifest, repository_root, verify_files)
    errors.extend(validate_contract(contract, artifacts))
    return {
        "status": "PASS" if not errors else "FAIL",
        "manifest": str(manifest_path),
        "contract": str(contract_path),
        "repository_root": str(repository_root),
        "verified_file_hashes": verify_files,
        "artifact_count": len(artifacts),
        "errors": errors,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--verify-files", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = validate_files(args.manifest, args.contract, args.verify_files)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
