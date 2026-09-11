#!/usr/bin/env python3
"""Reopen and independently validate the published Rev112 FCStd and STL package."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import FreeCAD as App

import core


def _required_object(document, name: str):
    obj = document.getObject(name)
    if obj is None:
        raise RuntimeError(f"Published Rev112 object is absent: {name}")
    return obj


def _symmetric_difference(first, second) -> dict:
    return {
        "first_minus_second_mm3": float(first.cut(second).Volume),
        "second_minus_first_mm3": float(second.cut(first).Volume),
    }


def _prusa_info(path: Path) -> dict:
    completed = subprocess.run(
        ["prusa-slicer", "--info", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    parsed = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    if parsed.get("manifold") != "yes":
        raise RuntimeError(f"PrusaSlicer reports non-manifold mesh: {path.name}")
    if int(parsed.get("number_of_parts", "0")) != 1:
        raise RuntimeError(f"PrusaSlicer reports multiple mesh parts: {path.name}")
    return {
        "path": str(path.relative_to(core.REPO_ROOT)),
        "sha256": core.sha256(path),
        "manifold": parsed["manifold"],
        "number_of_parts": int(parsed["number_of_parts"]),
        "number_of_facets": int(parsed["number_of_facets"]),
        "volume_mm3": float(parsed["volume"]),
        "size_mm": [float(parsed["size_x"]), float(parsed["size_y"]), float(parsed["size_z"])],
    }


def main() -> None:
    contract = core.load_contract()
    output = contract["output"]
    validation = contract["validation"]
    candidate_path = core.REPO_ROOT / output["candidate_fcstd"]
    generation_report_path = core.REPO_ROOT / output["generation_report"]
    generation = json.loads(generation_report_path.read_text(encoding="utf-8"))
    if generation.get("status") != "GENERATED_PRINTABLE_GEOMETRY__VALIDATION_PENDING":
        raise RuntimeError("Rev112 generation report state changed")
    if core.sha256(candidate_path) != generation["candidate_sha256"]:
        raise RuntimeError("Rev112 candidate FCStd hash disagrees with the generation report")

    source_path = core.REPO_ROOT / contract["source"]["path"]
    source_hash_before = core.sha256(source_path)
    if source_hash_before != contract["source"]["sha256"]:
        raise RuntimeError("Pinned user source changed before Rev112 validation")

    print("Rev112 validation 1 of 4: reopen the published FCStd and validate the final Body", flush=True)
    candidate = App.openDocument(str(candidate_path))
    source = App.openDocument(str(source_path))
    try:
        body = _required_object(candidate, "FINAL_HEAD_BODY_REV112")
        head = _required_object(candidate, "PRINT__CAT_HEAD_FINAL_CUT_HOLES_REV112")
        if body.TypeId != "PartDesign::Body":
            raise RuntimeError("Published Rev112 final head owner is not a Part Design Body")
        if body.Tip is None or body.Tip.Name != head.Name:
            raise RuntimeError("Published Rev112 final head feature is not the Body tip")
        head_record = core.require_closed_solids(head.Shape, "Reopened Rev112 final head", 1)
        body_record = core.require_closed_solids(body.Shape, "Reopened Rev112 final Body", 1)
        topology_fields = ("solid_count", "shell_count", "face_count", "edge_count", "vertex_count")
        body_tip_topology_match = all(
            body_record[field] == head_record[field] for field in topology_fields
        )
        body_tip_volume_residual = abs(
            body_record["volume_mm3"] - head_record["volume_mm3"]
        )
        body_bounds = body_record["bbox"]["min_mm"] + body_record["bbox"]["max_mm"]
        head_bounds = head_record["bbox"]["min_mm"] + head_record["bbox"]["max_mm"]
        body_tip_bbox_residual = max(
            abs(actual - expected) for actual, expected in zip(body_bounds, head_bounds)
        )
        if not body_tip_topology_match:
            raise RuntimeError("Published Rev112 Body topology disagrees with its final tip")
        if body_tip_volume_residual > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Published Rev112 Body volume disagrees with its final tip")
        if body_tip_bbox_residual > validation["bbox_tolerance_mm"]:
            raise RuntimeError("Published Rev112 Body bounds disagree with its final tip")

        print("Rev112 validation 2 of 4: run OCCT BOP self-intersection checking", flush=True)
        bop_report_path = candidate_path.parent / "occt-bop-check-report.json"
        if bop_report_path.is_file():
            bop_record = json.loads(bop_report_path.read_text(encoding="utf-8"))
            if bop_record.get("status") != "PASS_OCCT_BOP_CHECK":
                raise RuntimeError("Existing Rev112 OCCT BOP report is not a pass")
            if bop_record.get("candidate_sha256") != core.sha256(candidate_path):
                raise RuntimeError("Existing Rev112 OCCT BOP report belongs to another candidate")
        else:
            check_result = head.Shape.check(True)
            check_errors = list(check_result or [])
            if check_errors:
                raise RuntimeError(f"OCCT BOP check reported errors: {check_errors!r}")
            bop_record = {
                "status": "PASS_OCCT_BOP_CHECK",
                "candidate_fcstd": output["candidate_fcstd"],
                "candidate_sha256": core.sha256(candidate_path),
                "object": head.Name,
                "errors": [],
            }
            bop_report_path.write_text(
                json.dumps(bop_record, indent=2) + "\n", encoding="utf-8"
            )

        before = _required_object(candidate, "REFERENCE__REV108_HEAD_BEFORE_USER_CUTTERS").Shape
        cutter_compound = _required_object(candidate, "REVIEW_ONLY__USER_CUTTER_COMPOUND_REV112").Shape
        removed_volume = float(before.Volume) - float(head.Shape.Volume)
        expected_removed = generation["construction_evidence"]["removed_volume_mm3"]
        if abs(removed_volume - expected_removed) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Reopened Rev112 removed volume changed")
        cutter_residual = float(head.Shape.common(cutter_compound).Volume)
        if cutter_residual > validation["boolean_residual_volume_maximum_mm3"]:
            raise RuntimeError("Reopened Rev112 head retains cutter material")
        added_volume = float(head.Shape.cut(before).Volume)
        if added_volume > validation["boolean_residual_volume_maximum_mm3"]:
            raise RuntimeError("Reopened Rev112 head contains material outside Rev108")

        individual_records = []
        expected_overlaps = generation["construction_evidence"][
            "individual_cutter_overlaps_mm3"
        ]
        for index in range(1, 5):
            cutter = _required_object(candidate, f"REVIEW_ONLY__CUTTER{index}_REV112").Shape
            cutter_record = core.require_closed_solids(
                cutter, f"Reopened Rev112 Cutter{index}", 1
            )
            overlap_before = float(expected_overlaps[index - 1])
            residual_after_upper_bound = cutter_residual
            if overlap_before < validation["minimum_individual_cutter_overlap_mm3"]:
                raise RuntimeError(f"Published Cutter{index} lacks a source-head intersection")
            if residual_after_upper_bound > validation["boolean_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Published Cutter{index} was not fully subtracted")
            individual_records.append({
                "index": index,
                "saved_cutter": cutter_record,
                "source_head_overlap_mm3": overlap_before,
                "final_head_residual_upper_bound_mm3": residual_after_upper_bound,
                "residual_proof": "ZERO_AGGREGATE_COMPOUND_RESIDUAL_BOUNDS_EACH_MEMBER",
            })

        zip_residuals = {}
        for side in ("RIGHT", "LEFT"):
            corridor = _required_object(
                candidate, f"REVIEW_ONLY__{side}_ZIP_TIE_CORRIDOR_REV112"
            ).Shape
            residual = float(head.Shape.common(corridor).Volume)
            if residual > validation["zip_tie_corridor_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Published {side.lower()} zip-tie corridor is obstructed")
            zip_residuals[side.lower()] = residual

        print("Rev112 validation 3 of 4: compare all four saved panes to the pinned source", flush=True)
        output_pane_names = {
            "right_eye": "PRINT__RIGHT_EYE_TRANSLUCENT_PANE_REV112",
            "left_eye": "PRINT__LEFT_EYE_TRANSLUCENT_PANE_REV112",
            "mouth_TRI005": "PRINT__MOUTH_TRI005_TRANSLUCENT_PANE_REV112",
            "mouth_TRI006": "PRINT__MOUTH_TRI006_TRANSLUCENT_PANE_REV112",
        }
        pane_records = {}
        for key, output_name in output_pane_names.items():
            saved = _required_object(candidate, output_name).Shape
            original = _required_object(source, contract["source"]["protected_panes"][key]).Shape
            saved_record = core.require_closed_solids(saved, f"Reopened Rev112 {key} pane", 1)
            original_record = core.require_closed_solids(original, f"Pinned source {key} pane", 1)
            difference = _symmetric_difference(saved, original)
            if max(difference.values()) > validation["pane_shape_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Published Rev112 {key} pane changed from the pinned source")
            for field in ("solid_count", "face_count", "edge_count", "vertex_count"):
                if saved_record[field] != original_record[field]:
                    raise RuntimeError(f"Published Rev112 {key} pane topology changed: {field}")
            pane_records[key] = {
                "saved": saved_record,
                "source": original_record,
                "symmetric_difference_mm3": difference,
            }
    finally:
        App.closeDocument(source.Name)
        App.closeDocument(candidate.Name)

    source_hash_after = core.sha256(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Pinned source FCStd changed during Rev112 validation")

    print("Rev112 validation 4 of 4: inspect all five STL exports with PrusaSlicer", flush=True)
    stl_keys = (
        "head_stl",
        "right_eye_stl",
        "left_eye_stl",
        "mouth_tri005_stl",
        "mouth_tri006_stl",
    )
    mesh_records = {key: _prusa_info(core.REPO_ROOT / output[key]) for key in stl_keys}
    for key, export in generation["mesh_exports"].items():
        report_key = {
            "head": "head_stl",
            "right_eye": "right_eye_stl",
            "left_eye": "left_eye_stl",
            "mouth_TRI005": "mouth_tri005_stl",
            "mouth_TRI006": "mouth_tri006_stl",
        }[key]
        if mesh_records[report_key]["sha256"] != export["sha256"]:
            raise RuntimeError(f"Published Rev112 STL hash changed: {report_key}")

    report = {
        "status": "PASS_PRINTABLE_REV112_CAD_AND_MESH_VALIDATION",
        "iteration_id": contract["iteration_id"],
        "contract_sha256": core.sha256(core.CONTRACT_PATH),
        "generation_report_sha256": core.sha256(generation_report_path),
        "candidate_fcstd": output["candidate_fcstd"],
        "candidate_sha256": core.sha256(candidate_path),
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "final_body": body_record,
        "final_head": head_record,
        "body_tip_topology_match": body_tip_topology_match,
        "body_tip_volume_residual_mm3": body_tip_volume_residual,
        "body_tip_bbox_residual_mm": body_tip_bbox_residual,
        "occt_bop_check": {
            "report": str(bop_report_path.relative_to(core.REPO_ROOT)),
            "report_sha256": core.sha256(bop_report_path),
            "status": bop_record["status"],
            "errors": bop_record["errors"],
        },
        "removed_volume_mm3": removed_volume,
        "cutter_compound_residual_mm3": cutter_residual,
        "added_volume_outside_rev108_mm3": added_volume,
        "individual_cutters": individual_records,
        "zip_tie_corridor_residuals_mm3": zip_residuals,
        "protected_panes": pane_records,
        "prusa_slicer_mesh_validation": mesh_records,
        "slicer_project_created_or_changed": False,
        "physical_slicer_fit_test_pending": True,
    }
    report_path = candidate_path.parent / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "report": str(report_path.relative_to(core.REPO_ROOT)),
        "candidate_sha256": report["candidate_sha256"],
        "final_head": report["final_head"],
        "removed_volume_mm3": removed_volume,
        "cutter_residual_mm3": cutter_residual,
        "zip_tie_corridor_residuals_mm3": zip_residuals,
        "all_stls_manifold_single_part": True,
    }, indent=2))


if __name__ == "__main__":
    main()
