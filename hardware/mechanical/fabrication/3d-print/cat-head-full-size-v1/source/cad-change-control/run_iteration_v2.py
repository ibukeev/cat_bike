#!/usr/bin/env python3
"""Run one pinned FreeCAD generator once, with a hard five-minute ceiling."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import fcstd_preservation_v2 as preservation
import validate_iteration_v2 as preflight


ALLOW_MISSING_CANONICAL_GUI_DOCUMENT = False


def stop_process_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--freecad-appdir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validation = preflight.validate_files(
        args.baseline,
        args.contract,
        verify_files=True,
        require_new_output=True,
    )
    if validation["status"] != "PASS":
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 1

    repository_root = Path(validation["repository_root"])
    baseline = preflight.load_json(args.baseline)
    contract = preflight.load_json(args.contract)
    assembly = baseline["assembly"]
    generator = contract["generator"]
    budget = contract["budget"]
    output = contract["output"]

    baseline_file = repository_root / assembly["path"]
    generator_file = repository_root / generator["script_path"]
    output_dir = repository_root / output["directory"]
    candidate_file = repository_root / output["candidate_fcstd"]
    snapshot_file = repository_root / output["no_op_snapshot_fcstd"]
    baseline_digest_before = preflight.sha256_file(baseline_file)
    generator_digest_before = preflight.sha256_file(generator_file)

    appdir_value = args.freecad_appdir or os.environ.get("CAT_HEAD_FREECAD_APPDIR")
    if not appdir_value:
        print("CAT_HEAD_FREECAD_APPDIR or --freecad-appdir is required", file=sys.stderr)
        return 1
    appdir = Path(appdir_value).resolve()
    app_run = appdir / "AppRun"
    freecad_lib = appdir / "usr/lib"
    if not app_run.is_file() or not os.access(app_run, os.X_OK):
        print(f"FreeCAD AppRun is missing or not executable: {app_run}", file=sys.stderr)
        return 1
    if not freecad_lib.is_dir():
        print(f"FreeCAD library directory is missing: {freecad_lib}", file=sys.stderr)
        return 1

    runtime_reference = contract["runtime"]
    runtime_manifest_path = repository_root / runtime_reference["manifest_path"]
    runtime_manifest = preflight.load_json(runtime_manifest_path)
    runtime_validation = preservation.verify_runtime(
        appdir,
        repository_root,
        runtime_manifest,
    )
    runtime_validation["manifest_path"] = runtime_reference["manifest_path"]
    runtime_validation["manifest_sha256"] = preflight.sha256_file(
        runtime_manifest_path
    )
    if runtime_validation["status"] != "PASS":
        print(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "iteration_id": contract["iteration_id"],
                    "status": "FAILED__UNAPPROVED_RUNTIME_MISMATCH",
                    "runtime": runtime_validation,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    command = [
        str(app_run),
        "python",
        str(generator_file),
        *generator["arguments"],
    ]
    environment = preservation.freecad_environment(appdir)

    temporary_log = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f"cat-head-{contract['iteration_id']}-",
        suffix=".log",
        dir="/tmp",
        delete=False,
    )
    log_path = Path(temporary_log.name)
    process: subprocess.Popen[Any] | None = None
    timed_out = False
    exit_code: int | None = None
    try:
        with temporary_log:
            process = subprocess.Popen(
                command,
                cwd=repository_root,
                env=environment,
                stdout=temporary_log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                exit_code = process.wait(timeout=budget["max_generation_seconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_process_group(process)
                exit_code = process.returncode
    finally:
        if process is not None:
            stop_process_group(process)

    baseline_digest_after = (
        preflight.sha256_file(baseline_file) if baseline_file.is_file() else None
    )
    generator_digest_after = (
        preflight.sha256_file(generator_file) if generator_file.is_file() else None
    )
    baseline_unchanged = baseline_digest_after == baseline_digest_before
    generator_unchanged = generator_digest_after == generator_digest_before

    generator_authored_validation: list[str] = []
    if output_dir.is_dir():
        generator_authored_validation = [
            str(path.relative_to(repository_root))
            for path in output_dir.rglob("*.json")
            if "validation" in path.name.lower()
        ]

    candidate_exists = candidate_file.is_file()
    snapshot_capture: dict[str, Any] | None = None
    presentation_result: dict[str, Any] | None = None
    postprocess_error: str | None = None
    if exit_code == 0 and candidate_exists and baseline_unchanged and generator_unchanged:
        try:
            captured_backup = preservation.capture_single_no_op_backup(
                candidate_file,
                snapshot_file,
            )
            snapshot_capture = {
                "source_backup": str(
                    captured_backup["source_backup"].relative_to(repository_root)
                ),
                "path": output["no_op_snapshot_fcstd"],
                "sha256": captured_backup["sha256"],
            }
            candidate_shapes_before = preservation.raw_shape_digests(candidate_file)
            snapshot_shapes_before = preservation.raw_shape_digests(snapshot_file)
            candidate_presentation = preservation.restore_canonical_presentation(
                baseline_file,
                candidate_file,
                allow_missing_gui_document=ALLOW_MISSING_CANONICAL_GUI_DOCUMENT,
            )
            snapshot_presentation = preservation.restore_canonical_presentation(
                baseline_file,
                snapshot_file,
                allow_missing_gui_document=ALLOW_MISSING_CANONICAL_GUI_DOCUMENT,
            )
            candidate_shapes_after = preservation.raw_shape_digests(candidate_file)
            snapshot_shapes_after = preservation.raw_shape_digests(snapshot_file)
            if candidate_shapes_before != candidate_shapes_after:
                raise RuntimeError(
                    "presentation restoration changed candidate Shape.brp bytes"
                )
            if snapshot_shapes_before != snapshot_shapes_after:
                raise RuntimeError(
                    "presentation restoration changed no-op snapshot Shape.brp bytes"
                )
            expected_program_version = runtime_manifest["freecad"]["program_version"]
            candidate_program_version = preservation.document_program_version(
                candidate_file
            )
            snapshot_program_version = preservation.document_program_version(
                snapshot_file
            )
            if candidate_program_version != expected_program_version:
                raise RuntimeError(
                    "candidate ProgramVersion does not match the approved runtime"
                )
            if snapshot_program_version != expected_program_version:
                raise RuntimeError(
                    "no-op snapshot ProgramVersion does not match the approved runtime"
                )
            presentation_result = {
                "candidate": candidate_presentation,
                "no_op_snapshot": snapshot_presentation,
                "shape_entries_unchanged": True,
            }
            snapshot_capture = {
                "source_backup": snapshot_capture["source_backup"],
                "path": output["no_op_snapshot_fcstd"],
                "sha256": preflight.sha256_file(snapshot_file),
                "program_version": snapshot_program_version,
            }
            runtime_validation["candidate_program_version"] = candidate_program_version
            runtime_validation["snapshot_program_version"] = snapshot_program_version
        except (OSError, RuntimeError, ValueError) as exc:
            postprocess_error = str(exc)

    candidate_digest = preflight.sha256_file(candidate_file) if candidate_exists else None
    snapshot_exists = snapshot_file.is_file()
    snapshot_digest = (
        preflight.sha256_file(snapshot_file) if snapshot_exists else None
    )
    if timed_out:
        status = "TIMEOUT__QUARANTINED__DO_NOT_REPAIR"
    elif exit_code != 0:
        status = "GENERATOR_FAILED__QUARANTINED__DO_NOT_REPAIR"
    elif not baseline_unchanged:
        status = "FATAL__CANONICAL_BASELINE_WAS_MUTATED"
    elif not generator_unchanged:
        status = "FAILED__GENERATOR_CHANGED_DURING_RUN__QUARANTINED"
    elif generator_authored_validation:
        status = "FAILED__GENERATOR_AUTHORED_VALIDATION__QUARANTINED"
    elif not candidate_exists:
        status = "FAILED__CANDIDATE_MISSING__QUARANTINED"
    elif postprocess_error:
        status = "FAILED__NO_OP_SNAPSHOT_OR_PRESENTATION__QUARANTINED"
    elif not snapshot_exists:
        status = "FAILED__NO_OP_SNAPSHOT_MISSING__QUARANTINED"
    else:
        status = "CANDIDATE_READY__RUN_PRESERVATION_GATE_AND_FIXED_VIEWS"

    output_dir.mkdir(parents=True, exist_ok=True)
    runner_log = output_dir / "runner.log"
    shutil.copyfile(log_path, runner_log)
    log_path.unlink(missing_ok=True)
    result = {
        "schema_version": "2.0",
        "iteration_id": contract["iteration_id"],
        "status": status,
        "command": command,
        "timeout_seconds": budget["max_generation_seconds"],
        "timed_out": timed_out,
        "exit_code": exit_code,
        "baseline": {
            "path": assembly["path"],
            "sha256_before": baseline_digest_before,
            "sha256_after": baseline_digest_after,
            "unchanged": baseline_unchanged,
        },
        "runtime": runtime_validation,
        "generator": {
            "path": generator["script_path"],
            "sha256_before": generator_digest_before,
            "sha256_after": generator_digest_after,
            "unchanged": generator_unchanged,
            "authored_validation_files": generator_authored_validation,
        },
        "candidate": {
            "path": output["candidate_fcstd"],
            "exists": candidate_exists,
            "sha256": candidate_digest,
        },
        "no_op_snapshot": snapshot_capture
        or {
            "path": output["no_op_snapshot_fcstd"],
            "exists": snapshot_exists,
            "sha256": snapshot_digest,
        },
        "presentation_retention": presentation_result,
        "postprocess_error": postprocess_error,
        "runner_log": str(runner_log.relative_to(repository_root)),
        "automatic_retry": False,
        "repair_allowed": False,
    }
    write_json(output_dir / "runner-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if status.startswith("CANDIDATE_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
