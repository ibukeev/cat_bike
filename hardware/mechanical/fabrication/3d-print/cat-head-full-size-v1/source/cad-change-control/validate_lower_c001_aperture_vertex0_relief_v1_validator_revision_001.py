#!/usr/bin/env python3
"""Additive R05 validator correction for the immutable lower-C001 relief."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App


REVISION_ID = "lower-c001-aperture-vertex0-relief-v1-validator-revision-001"
SOURCE_REL = Path(
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
    "cad-change-control/validate_lower_c001_aperture_vertex0_relief_v1.py"
)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


ROOT = repository_root(Path(__file__))
_SPEC = importlib.util.spec_from_file_location("lower_c001_relief_validator_source", ROOT / SOURCE_REL)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load source validator")
SOURCE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(SOURCE)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preservation-report", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def rooted(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def corrected_r05_measurements(values: dict[str, Any]) -> dict[str, Any]:
    """Use exact candidate-vs-authorized-result equivalence for R05."""
    corrected = dict(values)
    corrected["r05_unstable_reverse_boolean_diagnostic_mm3"] = float(
        values["added_volume_mm3"]
    )
    corrected["added_volume_mm3"] = float(
        values["candidate_minus_expected_candidate_mm3"]
    )
    corrected["r05_measurement_basis"] = (
        "candidate_minus_exact_authorized_expected_candidate"
    )
    return corrected


def r05_subtraction_only(values: dict[str, Any], epsilon: float) -> bool:
    return float(corrected_r05_measurements(values)["added_volume_mm3"]) <= epsilon


def verify_preflight(args: argparse.Namespace) -> dict[str, Any]:
    authorization_path = rooted(args.authorization)
    if SOURCE.sha256_file(authorization_path) != args.authorization_sha256:
        raise RuntimeError("authorization SHA-256 mismatch")
    authorization = SOURCE.load_json(authorization_path)
    if authorization.get("authorization_id") != REVISION_ID:
        raise RuntimeError("validator revision authorization ID mismatch")
    if authorization.get("status") != "APPROVED_ONE_SHOT":
        raise RuntimeError("validator revision is not approved")
    revision = authorization["validator_revision"]
    if rooted(Path(revision["path"])).resolve() != Path(__file__).resolve():
        raise RuntimeError("validator revision path mismatch")
    if SOURCE.sha256_file(Path(__file__)) != revision["sha256"]:
        raise RuntimeError("validator revision SHA-256 mismatch")
    for label, record in authorization["pinned_evidence"].items():
        path = rooted(Path(record["path"]))
        if not path.is_file():
            raise RuntimeError(f"{label} missing: {path}")
        if SOURCE.sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"{label} SHA-256 mismatch")
    expected_cli = {
        "baseline_manifest": rooted(args.baseline),
        "contract": rooted(args.contract),
        "preservation_report": rooted(args.preservation_report),
    }
    for label, path in expected_cli.items():
        pinned = rooted(Path(authorization["pinned_evidence"][label]["path"]))
        if path.resolve() != pinned.resolve():
            raise RuntimeError(f"{label} CLI path mismatch")
    report_path = rooted(args.report)
    expected_report = rooted(Path(authorization["fresh_report_path"]))
    if report_path.resolve() != expected_report.resolve():
        raise RuntimeError(f"report must be exactly {expected_report}")
    if report_path.exists():
        raise RuntimeError("validator-revision report already exists; retry forbidden")
    failed = SOURCE.load_json(
        rooted(Path(authorization["pinned_evidence"]["consumed_failed_report"]["path"]))
    )
    expected_failure = authorization["consumed_failure"]
    if (
        failed.get("status") != "FAIL"
        or failed.get("failed_gates") != ["R05_SUBTRACTION_ONLY"]
        or float(failed["measurements"]["candidate_minus_expected_candidate_mm3"])
        != float(expected_failure["candidate_minus_expected_candidate_mm3"])
        or float(failed["measurements"]["expected_candidate_minus_candidate_mm3"])
        != float(expected_failure["expected_candidate_minus_candidate_mm3"])
    ):
        raise RuntimeError("consumed R05 failure evidence changed")
    if any(
        not passed
        for name, passed in failed["gates"].items()
        if name != "R05_SUBTRACTION_ONLY"
    ):
        raise RuntimeError("consumed report contains a non-R05 failure")
    return {
        "authorization": authorization,
        "report_path": report_path,
        "failed_report": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    preflight = verify_preflight(args)
    if args.preflight_only:
        print(
            json.dumps(
                {
                    "status": "VALIDATOR_REVISION_PREFLIGHT_PASS__NOT_EXECUTED",
                    "revision_id": REVISION_ID,
                    "candidate_opened": False,
                    "report_created": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    baseline = SOURCE.load_json(rooted(args.baseline))
    contract = SOURCE.load_json(rooted(args.contract))
    candidate_path = ROOT / contract["output"]["candidate_fcstd"]
    preservation_path = rooted(args.preservation_report)
    candidate_sha256 = SOURCE.sha256_file(candidate_path)
    preservation_ok, preservation_summary = SOURCE.preservation_gate(
        SOURCE.load_json(preservation_path), contract, candidate_sha256
    )
    baseline_path = ROOT / baseline["assembly"]["path"]
    baseline_sha256 = SOURCE.sha256_file(baseline_path)
    if baseline_sha256 != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    runtime_manifest = SOURCE.load_json(ROOT / contract["runtime"]["manifest_path"])
    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    observed_runtime = SOURCE.runtime_record()
    if observed_runtime != expected_runtime:
        raise RuntimeError(f"runtime mismatch: {observed_runtime} != {expected_runtime}")
    baseline_document = App.openDocument(str(baseline_path))
    candidate_document = App.openDocument(str(candidate_path))
    try:
        measured = SOURCE.measure(
            ROOT, baseline, contract, baseline_document, candidate_document
        )
    finally:
        App.closeDocument(candidate_document.Name)
        App.closeDocument(baseline_document.Name)
    values = corrected_r05_measurements(measured)
    result = SOURCE.evaluate_gates(
        values, contract["allowed_mutations"][0]["parameters"], preservation_ok
    )
    report = {
        "schema_version": "2.0",
        "validator_revision_id": REVISION_ID,
        "iteration_id": SOURCE.ITERATION_ID,
        "status": (
            "RELIEF_VALIDATION_PASS__READY_FOR_HUMAN_VISUAL_REVIEW"
            if result["status"] == "PASS"
            else "RELIEF_VALIDATION_FAIL__CANDIDATE_UNCHANGED"
        ),
        "gate_status": result["status"],
        "gates": result["gates"],
        "failed_gates": result["failed_gates"],
        "baseline": {"path": baseline["assembly"]["path"], "sha256": baseline_sha256},
        "candidate": {"path": contract["output"]["candidate_fcstd"], "sha256": candidate_sha256},
        "preservation": preservation_summary,
        "runtime": observed_runtime,
        "measurements": values,
        "source_failed_report": {
            "path": preflight["authorization"]["pinned_evidence"]["consumed_failed_report"]["path"],
            "sha256": preflight["authorization"]["pinned_evidence"]["consumed_failed_report"]["sha256"],
            "classification": "VALIDATOR_DEFECT__UNSTABLE_CANDIDATE_MINUS_BASELINE_BOOLEAN",
        },
        "candidate_modified": False,
        "retry_allowed": False,
        "downstream_holds_active": True,
    }
    preflight["report_path"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
