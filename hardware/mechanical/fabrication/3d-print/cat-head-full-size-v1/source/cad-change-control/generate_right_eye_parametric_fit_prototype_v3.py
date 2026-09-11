#!/usr/bin/env python3
"""Generate the one authorized right-eye parametric-fit V3 candidate.

This tooling wrapper keeps the V1 eye construction and review implementation
hash-pinned and unchanged while accepting only the V3 iteration contract.  It
performs the shared contract, runtime, dependency, historical-evidence,
reference, and canonical-baseline checks before it creates an output directory
or calls ``saveAs``.

``--preflight-only`` imports the pinned V1 construction implementation and
performs every immutable check, then exits without creating an output
directory, saving a document, replacing the target, or constructing geometry.
The V1 ``main`` entrypoint is never invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App


ITERATION_ID = "right-eye-parametric-fit-prototype-v3"
V1_ITERATION_ID = "right-eye-parametric-fit-prototype-v1"
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
WRAPPER_PARAMETER_KEYS = {"tooling_dependencies", "historical_evidence"}
REQUIRED_V1_FUNCTIONS = (
    "attach_parametric_history",
    "build_candidate_shape",
    "render_review_pack",
    "require_single_solid",
    "verify_reference_hashes",
)


class RuntimePreconditionError(RuntimeError):
    """The loaded FreeCAD/OCCT runtime differs from the approved pin."""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_pinned_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pinned_dependency(root: Path, item: dict[str, Any], label: str) -> Path:
    path = root / str(item["path"])
    expected = str(item["sha256"])
    actual = sha256_file(path) if path.is_file() else None
    if actual != expected:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "pinned tooling dependency mismatch",
                    "dependency": label,
                    "path": str(item["path"]),
                    "actual_sha256": actual,
                    "expected_sha256": expected,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return path


def verify_runtime(
    root: Path,
    runtime_reference: dict[str, Any],
) -> dict[str, Any]:
    manifest_path = root / str(runtime_reference["manifest_path"])
    expected_manifest_hash = str(runtime_reference["manifest_sha256"])
    actual_manifest_hash = sha256_file(manifest_path) if manifest_path.is_file() else None
    if actual_manifest_hash != expected_manifest_hash:
        raise RuntimePreconditionError(
            json.dumps(
                {
                    "error": "approved runtime manifest mismatch before generation",
                    "runtime_manifest": str(runtime_reference["manifest_path"]),
                    "actual_sha256": actual_manifest_hash,
                    "expected_sha256": expected_manifest_hash,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    manifest = load_json(manifest_path)
    probe_path = verify_pinned_dependency(
        root,
        {
            "path": manifest["probe"]["script_path"],
            "sha256": manifest["probe"]["script_sha256"],
        },
        "shared FreeCAD runtime probe",
    )
    probe = import_pinned_module(probe_path, "cat_head_shared_runtime_probe_v2")
    actual = probe.runtime_record()
    expected = {
        "freecad_version": manifest["freecad"]["version_record"],
        "freecad_program_version": manifest["freecad"]["program_version"],
        "occt_version": manifest["occt"]["version"],
        "python_version": manifest["python"]["version"],
        "platform_machine": manifest["platform"]["machine"],
    }
    if actual != expected:
        raise RuntimePreconditionError(
            json.dumps(
                {
                    "error": "FreeCAD runtime mismatch before generation",
                    "actual_runtime": actual,
                    "expected_runtime": expected,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return actual


def validate_contract_scope(contract: dict[str, Any]) -> dict[str, Any]:
    observed_iteration = contract.get("iteration_id")
    if observed_iteration != ITERATION_ID:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "iteration ID mismatch",
                    "expected_iteration_id": ITERATION_ID,
                    "observed_iteration_id": observed_iteration,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    if contract.get("target_object") != TARGET_OBJECT:
        raise RuntimeError("target object mismatch")
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or mutations[0].get("kind") != "replace_geometry":
        raise RuntimeError("generator requires exactly one replace_geometry mutation")
    if mutations[0].get("object") != TARGET_OBJECT:
        raise RuntimeError("mutation object mismatch")
    parameters = mutations[0].get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError("mutation parameters must be an object")
    return parameters


def normalize_iteration_id(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(ITERATION_ID, V1_ITERATION_ID)
    if isinstance(value, list):
        return [normalize_iteration_id(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_iteration_id(item) for key, item in value.items()}
    return value


def verify_v1_parameter_reuse(
    parameters: dict[str, Any],
    v1_contract: dict[str, Any],
) -> list[str]:
    v1_mutations = v1_contract.get("allowed_mutations", [])
    if len(v1_mutations) != 1:
        raise RuntimeError("pinned V1 contract no longer has exactly one mutation")
    expected = v1_mutations[0].get("parameters")
    actual = {
        key: value
        for key, value in parameters.items()
        if key not in WRAPPER_PARAMETER_KEYS
    }
    if normalize_iteration_id(actual) != expected:
        expected_keys = set(expected) if isinstance(expected, dict) else set()
        raise RuntimeError(
            json.dumps(
                {
                    "error": "V3 geometry parameters differ from the pinned V1 contract",
                    "missing_parameter_keys": sorted(expected_keys - set(actual)),
                    "unexpected_parameter_keys": sorted(set(actual) - expected_keys),
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return sorted(actual)


def verify_historical_evidence(
    root: Path,
    evidence: dict[str, Any],
) -> dict[str, str]:
    verified: dict[str, str] = {}
    for iteration_id, iteration in evidence.items():
        artifacts = iteration.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise RuntimeError(f"historical evidence {iteration_id} artifacts are invalid")
        for artifact_name, artifact in artifacts.items():
            label = f"historical evidence {iteration_id}/{artifact_name}"
            path = verify_pinned_dependency(root, artifact, label)
            verified[label] = sha256_file(path)
    return verified


def immutable_preflight(
    baseline_argument: Path,
    contract_argument: Path,
) -> dict[str, Any]:
    root = repository_root(contract_argument)
    baseline = load_json(baseline_argument)
    contract = load_json(contract_argument)
    parameters = validate_contract_scope(contract)
    tooling = parameters.get("tooling_dependencies")
    if not isinstance(tooling, dict):
        raise RuntimeError("V3 contract lacks tooling_dependencies")

    validator_path = verify_pinned_dependency(
        root, tooling["shared_validator"], "shared_validator"
    )
    validator = import_pinned_module(validator_path, "cat_head_shared_validator_v2")
    shared_validation = validator.validate_files(
        baseline_argument,
        contract_argument,
        verify_files=True,
        require_new_output=True,
    )
    if shared_validation.get("status") != "PASS":
        raise RuntimeError(
            json.dumps(
                {
                    "error": "shared V2 contract preflight failed",
                    "shared_validation": shared_validation,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )

    runtime_record = verify_runtime(root, contract["runtime"])
    for key in (
        "shared_runner",
        "shared_preservation_module",
        "shared_preservation_comparator",
    ):
        verify_pinned_dependency(root, tooling[key], key)

    v1_contract_path = verify_pinned_dependency(
        root, tooling["v1_eye_contract"], "pinned V1 eye contract"
    )
    v1_contract = load_json(v1_contract_path)
    geometry_parameter_keys = verify_v1_parameter_reuse(parameters, v1_contract)

    v1_implementation_path = verify_pinned_dependency(
        root,
        tooling["v1_eye_construction_implementation"],
        "hash-pinned V1 eye construction implementation",
    )
    v1 = import_pinned_module(
        v1_implementation_path, "right_eye_parametric_fit_v1_pinned"
    )
    if v1.ITERATION_ID != V1_ITERATION_ID or v1.TARGET_OBJECT != TARGET_OBJECT:
        raise RuntimeError("pinned V1 implementation identity changed")
    missing_functions = [
        name for name in REQUIRED_V1_FUNCTIONS if not callable(getattr(v1, name, None))
    ]
    if missing_functions:
        raise RuntimeError(f"pinned V1 implementation lacks {missing_functions}")

    historical = parameters.get("historical_evidence")
    if not isinstance(historical, dict):
        raise RuntimeError("V3 contract lacks historical_evidence")
    verified_historical = verify_historical_evidence(root, historical)
    v1.verify_reference_hashes(root, parameters["fit_references"])

    baseline_path = root / baseline["assembly"]["path"]
    baseline_hash = sha256_file(baseline_path)
    if baseline_hash != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    if baseline.get("baseline_id") != contract.get("baseline_id"):
        raise RuntimeError("contract baseline ID differs from baseline manifest")

    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if output_dir.exists() or candidate_path.exists():
        raise RuntimeError(f"V3 output already exists: {output_dir}")

    document = App.openDocument(str(baseline_path))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None:
            raise RuntimeError(f"canonical V34 lacks target {TARGET_OBJECT}")
        if target.TypeId != "Part::Feature":
            raise RuntimeError(f"unexpected target type {target.TypeId}")
        if target.Shape.isNull():
            raise RuntimeError("canonical V34 target shape is null")
        original_name = target.Name
        original_label = target.Label
        original_placement = App.Placement(target.Placement)
        if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
            raise RuntimeError("canonical V34 changed during immutable preflight")
    except Exception:
        App.closeDocument(document.Name)
        raise

    return {
        "root": root,
        "baseline": baseline,
        "contract": contract,
        "parameters": parameters,
        "runtime": runtime_record,
        "shared_validation": shared_validation,
        "geometry_parameter_keys": geometry_parameter_keys,
        "v1": v1,
        "v1_implementation_path": v1_implementation_path,
        "verified_historical": verified_historical,
        "baseline_path": baseline_path,
        "output_dir": output_dir,
        "candidate_path": candidate_path,
        "document": document,
        "target": target,
        "original_name": original_name,
        "original_label": original_label,
        "original_placement": original_placement,
        "geometry_construction_started": False,
    }


def preflight_report(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS__NO_OUTPUT_CREATED__NO_GEOMETRY_CONSTRUCTED",
        "iteration_id": ITERATION_ID,
        "resolved_iteration_id": context["contract"]["iteration_id"],
        "runtime": context["runtime"],
        "baseline": {
            "path": str(context["baseline"]["assembly"]["path"]),
            "sha256": str(context["baseline"]["assembly"]["sha256"]),
        },
        "target_object": TARGET_OBJECT,
        "shared_contract_preflight": context["shared_validation"]["status"],
        "v1_implementation": {
            "path": str(
                context["v1_implementation_path"].relative_to(context["root"])
            ),
            "sha256": sha256_file(context["v1_implementation_path"]),
            "iteration_id": context["v1"].ITERATION_ID,
            "imported_functions": list(REQUIRED_V1_FUNCTIONS),
            "main_invoked": False,
        },
        "geometry_parameter_key_count": len(context["geometry_parameter_keys"]),
        "geometry_parameters_match_v1": True,
        "historical_evidence_hashes_verified": context["verified_historical"],
        "output_directory": str(context["contract"]["output"]["directory"]),
        "output_exists": context["output_dir"].exists(),
        "candidate_exists": context["candidate_path"].exists(),
        "geometry_construction_started": context["geometry_construction_started"],
    }


def construct_candidate(context: dict[str, Any]) -> None:
    root = context["root"]
    baseline = context["baseline"]
    contract = context["contract"]
    parameters = context["parameters"]
    v1 = context["v1"]
    document = context["document"]
    target = context["target"]

    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["candidate_path"].parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(context["candidate_path"]))
    print("STAGE 1/6 immutable preflight passed and candidate saveAs completed", flush=True)

    context["geometry_construction_started"] = True
    candidate_shape, construction = v1.build_candidate_shape(parameters)
    print("STAGE 2/6 five V1 feature families constructed unchanged", flush=True)
    target.Shape = candidate_shape
    v1.attach_parametric_history(
        target,
        parameters,
        construction["origin"],
        construction["axis_u"],
        construction["axis_v"],
        construction["axis_n"],
        construction["aperture_exact"],
    )
    target.PrototypeIterationId = ITERATION_ID
    document.recompute()
    if target.Name != context["original_name"] or target.Label != context["original_label"]:
        raise RuntimeError("target identity changed during replacement")
    if target.Placement != context["original_placement"]:
        raise RuntimeError("target placement changed during replacement")
    v1.require_single_solid(target.Shape, "saved target replacement")
    document.save()
    print("STAGE 3/6 candidate saved with only target shape replaced", flush=True)

    v1.render_review_pack(document, target, parameters, construction, root, contract)
    print("STAGE 4/6 six fixed whole-head views rendered", flush=True)
    print("STAGE 5/6 six requested focused review views rendered", flush=True)

    if sha256_file(context["baseline_path"]) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 6/6 canonical V34 remains hash-identical", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    context = immutable_preflight(args.baseline, args.contract)
    try:
        if args.preflight_only:
            print(json.dumps(preflight_report(context), indent=2, sort_keys=True))
            return 0
        construct_candidate(context)
        return 0
    finally:
        App.closeDocument(context["document"].Name)


if __name__ == "__main__":
    raise SystemExit(main())
