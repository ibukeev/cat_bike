#!/usr/bin/env python3
"""No-output preflight for the isolated Rev113 merged-mouth candidate."""

from __future__ import annotations

import json

import FreeCAD as App

import core


def main() -> None:
    contract = core.load_contract()
    output = contract["output"]
    candidate_directory = core.REPO_ROOT / output["candidate_directory"]
    forbidden_keys = (
        "candidate_fcstd",
        "generation_report",
        "head_stl",
        "right_eye_stl",
        "left_eye_stl",
        "merged_mouth_stl",
        "bridge_review_stl",
    )
    if candidate_directory.exists():
        raise RuntimeError("Rev113 candidate directory already exists; preflight refuses overwrite")
    for key in forbidden_keys:
        if (core.REPO_ROOT / output[key]).exists():
            raise RuntimeError(f"Rev113 preflight found forbidden candidate output: {key}")

    source_path = core.REPO_ROOT / contract["source"]["path"]
    source_hash_before = core.sha256(source_path)
    package = core.construct_package(contract)
    disposable = App.newDocument("Rev113MergedMouthNoOutputDisposable")
    try:
        finalization = core.finalize_document(disposable, package, contract)
        for key in (
            "target_assignment_performed",
            "typed_metadata_assignment_performed",
            "recompute_performed",
            "final_assertions_performed",
        ):
            if not finalization[key]:
                raise RuntimeError(f"Rev113 in-memory finalization did not complete: {key}")
    finally:
        App.closeDocument(disposable.Name)

    source_hash_after = core.sha256(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Pinned Rev112 source changed during Rev113 no-output preflight")
    report = {
        "status": "CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS",
        "iteration_id": contract["iteration_id"],
        "design_id": contract["design_id"],
        "tooling_revision": contract["tooling_revision"],
        "contract_path": str(core.CONTRACT_PATH.relative_to(core.REPO_ROOT)),
        "contract_sha256": core.sha256(core.CONTRACT_PATH),
        "source_path": contract["source"]["path"],
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "construction_evidence": package["evidence"],
        "finalization": finalization,
        "no_output_assertions": {
            "source_save_called": False,
            "source_overwritten": False,
            "candidate_directory_created": False,
            "fcstd_created": False,
            "stl_created": False,
            "slicer_project_created_or_changed": False,
            "gcode_created": False,
        },
    }
    report_path = core.REPO_ROOT / output["preflight_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "report": str(report_path.relative_to(core.REPO_ROOT)),
        "source_sha256": source_hash_after,
        "seam_distance_mm": package["evidence"]["seam_distance_mm"],
        "bridge_volume_mm3": package["evidence"]["bridge"]["volume_mm3"],
        "merged_mouth_volume_mm3": package["evidence"]["merged_mouth"]["volume_mm3"],
        "merged_head_overlap_mm3": package["evidence"]["merged_head_overlap_mm3"],
    }, indent=2))


if __name__ == "__main__":
    main()
