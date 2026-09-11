#!/usr/bin/env python3
"""Fail-closed preflight for one bounded cat-head CAD candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT = "cat-head-full-size-v1"
SCHEMA_VERSION = "2.0"
CAT_HEAD_PREFIX = Path(
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1"
)
SOURCE_PREFIX = CAT_HEAD_PREFIX / "source"
RUNTIME_PREFIX = SOURCE_PREFIX / "cad-change-control" / "v2"
OUTPUT_PREFIX = Path("reports/generated/cat-head-cad-iterations")
VIEWS = ("front", "rear", "left", "right", "top", "bottom")
PROTECTED_INVARIANTS = {
    "existence",
    "internal_name",
    "label",
    "type",
    "shape",
    "placement",
    "visibility",
    "group_membership",
}
MUTATION_KINDS = {
    "trim_end",
    "translate",
    "rotate",
    "boolean_cut",
    "add_feature",
    "remove_feature",
    "replace_geometry",
}
RELEASE_HOLDS = {
    "mirror",
    "production_union",
    "stl",
    "three_mf",
    "slicing",
    "gcode",
    "print",
    "commit",
    "promotion",
}
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be a JSON object")
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


def check_exact_keys(
    value: Any,
    expected: set[str],
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        errors.append(f"{label} is missing keys: {sorted(missing)}")
    if unknown:
        errors.append(f"{label} has unsupported keys: {sorted(unknown)}")
    return value


def safe_relative_path(value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty repository-relative path")
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay inside the repository: {value!r}")
        return None
    return path


def check_digest(value: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        errors.append(f"{label} must be a 64-character lowercase SHA-256 digest")
        return False
    if value == "0" * 64:
        errors.append(f"{label} is still the template placeholder")
        return False
    return True


def require_within(
    path: Path | None,
    parent: Path,
    label: str,
    errors: list[str],
) -> None:
    if path is None:
        return
    try:
        path.relative_to(parent)
    except ValueError:
        errors.append(f"{label} must be under {parent}")


def verify_pinned_file(
    repository_root: Path,
    path: Path | None,
    expected_digest: Any,
    label: str,
    verify_files: bool,
    errors: list[str],
) -> None:
    digest_valid = check_digest(expected_digest, f"{label}.sha256", errors)
    if not verify_files or path is None:
        return
    absolute = repository_root / path
    if not absolute.is_file():
        errors.append(f"{label} does not exist: {path}")
    elif digest_valid and sha256_file(absolute) != expected_digest:
        errors.append(f"{label} SHA-256 mismatch: {path}")


def validate_runtime_manifest(
    manifest: dict[str, Any],
    repository_root: Path,
    verify_files: bool,
) -> list[str]:
    errors: list[str] = []
    check_exact_keys(
        manifest,
        {
            "schema_version",
            "runtime_id",
            "state",
            "freecad",
            "occt",
            "python",
            "platform",
            "probe",
            "artifacts",
            "approval",
        },
        "runtime manifest",
        errors,
    )
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"runtime manifest.schema_version must be {SCHEMA_VERSION!r}")
    runtime_id = manifest.get("runtime_id")
    if not isinstance(runtime_id, str) or not IDENTIFIER.fullmatch(runtime_id):
        errors.append("runtime manifest.runtime_id must be a lowercase kebab-case identifier")
    if manifest.get("state") != "user_approved_v2_runtime":
        errors.append("runtime manifest.state must be 'user_approved_v2_runtime'")

    freecad = check_exact_keys(
        manifest.get("freecad"),
        {"release", "program_version", "version_record", "source_appimage_sha256"},
        "runtime manifest.freecad",
        errors,
    )
    for key in ("release", "program_version"):
        if not isinstance(freecad.get(key), str) or not freecad[key].strip():
            errors.append(f"runtime manifest.freecad.{key} must be non-empty")
    version_record = freecad.get("version_record")
    if (
        not isinstance(version_record, list)
        or not version_record
        or not all(isinstance(value, str) for value in version_record)
    ):
        errors.append("runtime manifest.freecad.version_record must be a non-empty string array")
    check_digest(
        freecad.get("source_appimage_sha256"),
        "runtime manifest.freecad.source_appimage_sha256",
        errors,
    )

    occt = check_exact_keys(
        manifest.get("occt"), {"version"}, "runtime manifest.occt", errors
    )
    python = check_exact_keys(
        manifest.get("python"), {"version"}, "runtime manifest.python", errors
    )
    platform = check_exact_keys(
        manifest.get("platform"), {"machine"}, "runtime manifest.platform", errors
    )
    for container, key, label in (
        (occt, "version", "runtime manifest.occt.version"),
        (python, "version", "runtime manifest.python.version"),
        (platform, "machine", "runtime manifest.platform.machine"),
    ):
        if not isinstance(container.get(key), str) or not container[key].strip():
            errors.append(f"{label} must be non-empty")

    probe = check_exact_keys(
        manifest.get("probe"),
        {"script_path", "script_sha256"},
        "runtime manifest.probe",
        errors,
    )
    probe_path = safe_relative_path(
        probe.get("script_path"), "runtime manifest.probe.script_path", errors
    )
    require_within(
        probe_path,
        SOURCE_PREFIX,
        "runtime manifest.probe.script_path",
        errors,
    )
    if probe_path is not None and probe_path.suffix.lower() != ".py":
        errors.append("runtime manifest.probe.script_path must be a Python file")
    verify_pinned_file(
        repository_root,
        probe_path,
        probe.get("script_sha256"),
        "runtime manifest.probe",
        verify_files,
        errors,
    )

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("runtime manifest.artifacts must be a non-empty array")
        artifacts = []
    seen_artifact_paths: set[Path] = set()
    for index, artifact in enumerate(artifacts):
        item = check_exact_keys(
            artifact,
            {"path", "sha256"},
            f"runtime manifest.artifacts[{index}]",
            errors,
        )
        artifact_path = safe_relative_path(
            item.get("path"),
            f"runtime manifest.artifacts[{index}].path",
            errors,
        )
        if artifact_path is not None:
            if artifact_path in seen_artifact_paths:
                errors.append(
                    f"runtime manifest.artifacts[{index}].path is duplicated"
                )
            seen_artifact_paths.add(artifact_path)
        check_digest(
            item.get("sha256"),
            f"runtime manifest.artifacts[{index}].sha256",
            errors,
        )

    approval = check_exact_keys(
        manifest.get("approval"),
        {"status", "approved_by", "approved_at", "note"},
        "runtime manifest.approval",
        errors,
    )
    if approval.get("status") != "approved":
        errors.append("runtime manifest.approval.status must be 'approved'")
    for key in ("approved_by", "approved_at", "note"):
        if not isinstance(approval.get(key), str) or not approval[key].strip():
            errors.append(f"runtime manifest.approval.{key} must be non-empty")
    return errors


def validate_baseline(
    baseline: dict[str, Any],
    repository_root: Path,
    verify_files: bool,
) -> list[str]:
    errors: list[str] = []
    check_exact_keys(
        baseline,
        {
            "schema_version",
            "project",
            "baseline_id",
            "state",
            "assembly",
            "review_pack",
            "approval",
        },
        "baseline",
        errors,
    )
    if baseline.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"baseline.schema_version must be {SCHEMA_VERSION!r}")
    if baseline.get("project") != PROJECT:
        errors.append(f"baseline.project must be {PROJECT!r}")
    baseline_id = baseline.get("baseline_id")
    if not isinstance(baseline_id, str) or not IDENTIFIER.fullmatch(baseline_id):
        errors.append("baseline.baseline_id must be a lowercase kebab-case identifier")
    if baseline.get("state") != "human_approved_canonical":
        errors.append("baseline.state must be 'human_approved_canonical'")

    assembly = check_exact_keys(
        baseline.get("assembly"),
        {"path", "sha256", "format"},
        "baseline.assembly",
        errors,
    )
    assembly_path = safe_relative_path(
        assembly.get("path"), "baseline.assembly.path", errors
    )
    require_within(
        assembly_path,
        CAT_HEAD_PREFIX,
        "baseline.assembly.path",
        errors,
    )
    if assembly_path is not None and assembly_path.suffix.lower() != ".fcstd":
        errors.append("baseline.assembly.path must identify one FCStd file")
    if assembly.get("format") != "fcstd":
        errors.append("baseline.assembly.format must be 'fcstd'")
    verify_pinned_file(
        repository_root,
        assembly_path,
        assembly.get("sha256"),
        "baseline.assembly",
        verify_files,
        errors,
    )

    review_pack = baseline.get("review_pack")
    if not isinstance(review_pack, dict):
        errors.append("baseline.review_pack must be an object")
        review_pack = {}
    elif set(review_pack) != set(VIEWS):
        errors.append(f"baseline.review_pack must contain exactly {list(VIEWS)}")
    for view in VIEWS:
        item = check_exact_keys(
            review_pack.get(view),
            {"path", "sha256"},
            f"baseline.review_pack.{view}",
            errors,
        )
        image_path = safe_relative_path(
            item.get("path"), f"baseline.review_pack.{view}.path", errors
        )
        if image_path is not None and image_path.suffix.lower() not in {
            ".png",
            ".jpg",
            ".jpeg",
        }:
            errors.append(f"baseline.review_pack.{view}.path must be a PNG or JPEG")
        verify_pinned_file(
            repository_root,
            image_path,
            item.get("sha256"),
            f"baseline.review_pack.{view}",
            verify_files,
            errors,
        )

    approval = check_exact_keys(
        baseline.get("approval"),
        {"status", "approved_by", "approved_at", "note"},
        "baseline.approval",
        errors,
    )
    if approval.get("status") != "approved":
        errors.append("baseline.approval.status must be 'approved'")
    for key in ("approved_by", "approved_at", "note"):
        if not isinstance(approval.get(key), str) or not approval[key].strip():
            errors.append(f"baseline.approval.{key} must be non-empty")
    return errors


def validate_contract(
    contract: dict[str, Any],
    baseline: dict[str, Any],
    repository_root: Path,
    verify_files: bool,
    require_new_output: bool,
) -> list[str]:
    errors: list[str] = []
    check_exact_keys(
        contract,
        {
            "schema_version",
            "project",
            "iteration_id",
            "state",
            "baseline_id",
            "user_approval",
            "target_object",
            "allowed_mutations",
            "protected_objects",
            "budget",
            "runtime",
            "generator",
            "review_gate",
            "output",
            "release_holds",
        },
        "contract",
        errors,
    )
    if contract.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"contract.schema_version must be {SCHEMA_VERSION!r}")
    if contract.get("project") != PROJECT:
        errors.append(f"contract.project must be {PROJECT!r}")
    if contract.get("baseline_id") != baseline.get("baseline_id"):
        errors.append("contract.baseline_id must match the approved baseline")

    iteration_id = contract.get("iteration_id")
    if not isinstance(iteration_id, str) or not IDENTIFIER.fullmatch(iteration_id):
        errors.append("contract.iteration_id must be a lowercase kebab-case identifier")
    if contract.get("state") != "approved_for_one_candidate":
        errors.append("contract.state must be 'approved_for_one_candidate'")

    user_approval = check_exact_keys(
        contract.get("user_approval"),
        {"status", "approved_by", "approved_at", "exact_instruction"},
        "contract.user_approval",
        errors,
    )
    if user_approval.get("status") != "approved":
        errors.append("contract.user_approval.status must be 'approved'")
    for key in ("approved_by", "approved_at", "exact_instruction"):
        if not isinstance(user_approval.get(key), str) or not user_approval[key].strip():
            errors.append(f"contract.user_approval.{key} must be non-empty")

    target = contract.get("target_object")
    if not isinstance(target, str) or not target.strip():
        errors.append("contract.target_object must be one internal FreeCAD object name")

    mutations = contract.get("allowed_mutations")
    if not isinstance(mutations, list) or len(mutations) != 1:
        errors.append("contract.allowed_mutations must contain exactly one mutation")
        mutations = []
    for index, mutation in enumerate(mutations):
        item = check_exact_keys(
            mutation,
            {"kind", "object", "parameters"},
            f"contract.allowed_mutations[{index}]",
            errors,
        )
        if item.get("kind") not in MUTATION_KINDS:
            errors.append(
                f"contract.allowed_mutations[{index}].kind is unsupported; "
                "whole-object delete/rename is never allowed"
            )
        if item.get("object") != target:
            errors.append(
                f"contract.allowed_mutations[{index}].object must equal target_object"
            )
        parameters = item.get("parameters")
        if not isinstance(parameters, dict) or not parameters:
            errors.append(
                f"contract.allowed_mutations[{index}].parameters must encode the exact operation"
            )

    protected = check_exact_keys(
        contract.get("protected_objects"),
        {"mode", "invariants"},
        "contract.protected_objects",
        errors,
    )
    if protected.get("mode") != "all_except_target":
        errors.append("contract.protected_objects.mode must be 'all_except_target'")
    invariants = protected.get("invariants")
    if not isinstance(invariants, list) or set(invariants) != PROTECTED_INVARIANTS:
        errors.append(
            "contract.protected_objects.invariants must contain the complete V2 preservation set"
        )
    elif len(invariants) != len(PROTECTED_INVARIANTS):
        errors.append("contract.protected_objects.invariants must not contain duplicates")

    budget = check_exact_keys(
        contract.get("budget"),
        {
            "fresh_chat_required",
            "resume_previous_chat",
            "max_generation_seconds",
            "max_candidates",
            "max_repair_attempts",
            "automatic_retry",
        },
        "contract.budget",
        errors,
    )
    if budget.get("fresh_chat_required") is not True:
        errors.append("contract.budget.fresh_chat_required must be true")
    if budget.get("resume_previous_chat") is not False:
        errors.append("contract.budget.resume_previous_chat must be false")
    seconds = budget.get("max_generation_seconds")
    if not isinstance(seconds, int) or isinstance(seconds, bool) or not 1 <= seconds <= 300:
        errors.append("contract.budget.max_generation_seconds must be 1..300")
    if budget.get("max_candidates") != 1:
        errors.append("contract.budget.max_candidates must be exactly 1")
    if budget.get("max_repair_attempts") != 0:
        errors.append("contract.budget.max_repair_attempts must be exactly 0")
    if budget.get("automatic_retry") is not False:
        errors.append("contract.budget.automatic_retry must be false")

    runtime = check_exact_keys(
        contract.get("runtime"),
        {"manifest_path", "manifest_sha256"},
        "contract.runtime",
        errors,
    )
    runtime_path = safe_relative_path(
        runtime.get("manifest_path"), "contract.runtime.manifest_path", errors
    )
    require_within(
        runtime_path,
        RUNTIME_PREFIX,
        "contract.runtime.manifest_path",
        errors,
    )
    if runtime_path is not None and runtime_path.suffix.lower() != ".json":
        errors.append("contract.runtime.manifest_path must be a JSON file")
    verify_pinned_file(
        repository_root,
        runtime_path,
        runtime.get("manifest_sha256"),
        "contract.runtime",
        verify_files,
        errors,
    )
    if runtime_path is not None and (repository_root / runtime_path).is_file():
        try:
            runtime_manifest = load_json(repository_root / runtime_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"contract.runtime manifest cannot be loaded: {exc}")
        else:
            errors.extend(
                validate_runtime_manifest(
                    runtime_manifest,
                    repository_root,
                    verify_files,
                )
            )

    generator = check_exact_keys(
        contract.get("generator"),
        {"script_path", "script_sha256", "arguments", "writes_only_output_directory"},
        "contract.generator",
        errors,
    )
    script_path = safe_relative_path(
        generator.get("script_path"), "contract.generator.script_path", errors
    )
    require_within(script_path, SOURCE_PREFIX, "contract.generator.script_path", errors)
    if script_path is not None and script_path.suffix.lower() != ".py":
        errors.append("contract.generator.script_path must be a Python file")
    verify_pinned_file(
        repository_root,
        script_path,
        generator.get("script_sha256"),
        "contract.generator",
        verify_files,
        errors,
    )
    arguments = generator.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        errors.append("contract.generator.arguments must be an array of strings")
    if generator.get("writes_only_output_directory") is not True:
        errors.append("contract.generator.writes_only_output_directory must be true")

    review = check_exact_keys(
        contract.get("review_gate"),
        {
            "required_views",
            "human_visual_approval_required",
            "visual_approval_status",
            "independent_verification_required",
            "generator_may_write_validation",
            "run_occt_before_visual_approval",
        },
        "contract.review_gate",
        errors,
    )
    required_views = review.get("required_views")
    if not isinstance(required_views, list) or set(required_views) != set(VIEWS):
        errors.append(f"contract.review_gate.required_views must contain exactly {list(VIEWS)}")
    elif len(required_views) != len(VIEWS):
        errors.append("contract.review_gate.required_views must not contain duplicates")
    if review.get("human_visual_approval_required") is not True:
        errors.append("contract.review_gate.human_visual_approval_required must be true")
    if review.get("visual_approval_status") != "pending":
        errors.append("contract.review_gate.visual_approval_status must be 'pending' before generation")
    if review.get("independent_verification_required") is not True:
        errors.append("contract.review_gate.independent_verification_required must be true")
    if review.get("generator_may_write_validation") is not False:
        errors.append("contract.review_gate.generator_may_write_validation must be false")
    if review.get("run_occt_before_visual_approval") is not False:
        errors.append("contract.review_gate.run_occt_before_visual_approval must be false")

    output = check_exact_keys(
        contract.get("output"),
        {"directory", "candidate_fcstd", "no_op_snapshot_fcstd", "review_files"},
        "contract.output",
        errors,
    )
    output_dir = safe_relative_path(
        output.get("directory"), "contract.output.directory", errors
    )
    expected_dir = OUTPUT_PREFIX / str(iteration_id)
    if output_dir is not None and output_dir != expected_dir:
        errors.append(f"contract.output.directory must be exactly {expected_dir}")
    if require_new_output and output_dir is not None and (repository_root / output_dir).exists():
        errors.append(f"contract.output.directory already exists and is quarantined: {output_dir}")

    candidate_path = safe_relative_path(
        output.get("candidate_fcstd"), "contract.output.candidate_fcstd", errors
    )
    if candidate_path is not None:
        require_within(candidate_path, expected_dir, "contract.output.candidate_fcstd", errors)
        if candidate_path.suffix.lower() != ".fcstd":
            errors.append("contract.output.candidate_fcstd must end in .FCStd")

    snapshot_path = safe_relative_path(
        output.get("no_op_snapshot_fcstd"),
        "contract.output.no_op_snapshot_fcstd",
        errors,
    )
    expected_snapshot = expected_dir / "no-op-snapshot.FCStd"
    if snapshot_path is not None and snapshot_path != expected_snapshot:
        errors.append(
            "contract.output.no_op_snapshot_fcstd must be exactly "
            f"{expected_snapshot}"
        )

    review_files = output.get("review_files")
    if not isinstance(review_files, dict) or set(review_files) != set(VIEWS):
        errors.append(f"contract.output.review_files must contain exactly {list(VIEWS)}")
        review_files = {}
    for view in VIEWS:
        view_path = safe_relative_path(
            review_files.get(view), f"contract.output.review_files.{view}", errors
        )
        if view_path is not None:
            require_within(
                view_path,
                expected_dir / "review",
                f"contract.output.review_files.{view}",
                errors,
            )
            if view_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                errors.append(f"contract.output.review_files.{view} must be a PNG or JPEG")

    holds = contract.get("release_holds")
    if not isinstance(holds, dict) or set(holds) != RELEASE_HOLDS:
        errors.append(f"contract.release_holds must contain exactly {sorted(RELEASE_HOLDS)}")
    elif any(value is not False for value in holds.values()):
        errors.append("every contract.release_holds value must remain false")
    return errors


def validate_files(
    baseline_path: Path,
    contract_path: Path,
    verify_files: bool = False,
    require_new_output: bool = False,
) -> dict[str, Any]:
    repository_root = find_repository_root(baseline_path)
    baseline = load_json(baseline_path)
    contract = load_json(contract_path)
    errors = validate_baseline(baseline, repository_root, verify_files)
    errors.extend(
        validate_contract(
            contract,
            baseline,
            repository_root,
            verify_files,
            require_new_output,
        )
    )
    return {
        "status": "PASS" if not errors else "FAIL",
        "baseline": str(baseline_path),
        "contract": str(contract_path),
        "repository_root": str(repository_root),
        "verified_file_hashes": verify_files,
        "required_new_output": require_new_output,
        "errors": errors,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--verify-files", action="store_true")
    parser.add_argument("--require-new-output", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = validate_files(
        args.baseline,
        args.contract,
        verify_files=args.verify_files,
        require_new_output=args.require_new_output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
