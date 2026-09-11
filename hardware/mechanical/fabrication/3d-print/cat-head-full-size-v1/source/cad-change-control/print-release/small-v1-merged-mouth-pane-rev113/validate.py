#!/usr/bin/env python3
"""Independent saved-artifact validator for the Rev113 merged-mouth candidate."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import FreeCAD as App
import Part

import core


def required_object(document, name: str):
    obj = document.getObject(name)
    if obj is None:
        raise RuntimeError(f"Published Rev113 object is absent: {name}")
    return obj


def prusa_info(path: Path) -> dict:
    completed = subprocess.run(
        ["prusa-slicer", "--info", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    parsed = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
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
    source_contract = contract["source"]
    operation = contract["operation"]
    validation = contract["validation"]
    output = contract["output"]
    candidate_path = core.REPO_ROOT / output["candidate_fcstd"]
    generation_path = core.REPO_ROOT / output["generation_report"]
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    if generation.get("status") != "GENERATED_REV113_REVIEW_CANDIDATE__VALIDATION_PENDING":
        raise RuntimeError("Rev113 generation report state changed")
    if core.sha256(candidate_path) != generation["candidate_sha256"]:
        raise RuntimeError("Rev113 FCStd hash disagrees with its generation report")

    source_path = core.REPO_ROOT / source_contract["path"]
    source_hash_before = core.sha256(source_path)
    if source_hash_before != source_contract["sha256"]:
        raise RuntimeError("Pinned Rev112 source changed before Rev113 validation")

    print("Rev113 validation 1 of 4: reopen the FCStd and prove the four print owners", flush=True)
    candidate = App.openDocument(str(candidate_path))
    source = App.openDocument(str(source_path))
    try:
        body = required_object(candidate, "FINAL_HEAD_BODY_REV113")
        head = required_object(candidate, "PRINT__CAT_HEAD_FINAL_REV113")
        right_eye = required_object(candidate, "PRINT__RIGHT_EYE_TRANSLUCENT_PANE_REV113")
        left_eye = required_object(candidate, "PRINT__LEFT_EYE_TRANSLUCENT_PANE_REV113")
        mouth = required_object(candidate, "PRINT__MERGED_MOUTH_TRANSLUCENT_PANE_REV113")
        bridge = required_object(candidate, "PROPOSED__MOUTH_CENTER_SEAM_BRIDGE_REV113")
        if body.TypeId != "PartDesign::Body" or body.Tip is None or body.Tip.Name != head.Name:
            raise RuntimeError("Rev113 final head Body/tip relationship is invalid")
        print_records = {
            "head": core.require_closed_solids(head.Shape, "Reopened Rev113 head", 1),
            "right_eye": core.require_closed_solids(right_eye.Shape, "Reopened Rev113 right eye", 1),
            "left_eye": core.require_closed_solids(left_eye.Shape, "Reopened Rev113 left eye", 1),
            "merged_mouth": core.require_closed_solids(mouth.Shape, "Reopened Rev113 merged mouth", 1),
        }
        if len(print_records) != operation["expected_final_print_part_count"]:
            raise RuntimeError("Rev113 printable part count changed")
        body_record = core.require_closed_solids(body.Shape, "Reopened Rev113 final head Body", 1)
        topology_fields = ("solid_count", "shell_count", "face_count", "edge_count", "vertex_count")
        if any(body_record[field] != print_records["head"][field] for field in topology_fields):
            raise RuntimeError("Rev113 Body topology differs from its tip")
        if abs(body_record["volume_mm3"] - print_records["head"]["volume_mm3"]) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Rev113 Body volume differs from its tip")

        print("Rev113 validation 2 of 4: prove frozen head/eyes and the seam-only mouth addition", flush=True)
        frozen_object_pairs = {
            "head": (head, required_object(source, source_contract["head_object"])),
            "right_eye": (right_eye, required_object(source, source_contract["right_eye_object"])),
            "left_eye": (left_eye, required_object(source, source_contract["left_eye_object"])),
        }
        frozen_records = {}
        for key, (saved, original) in frozen_object_pairs.items():
            saved_record = core.require_closed_solids(saved.Shape, f"Saved frozen {key}", 1)
            original_record = core.require_closed_solids(original.Shape, f"Source frozen {key}", 1)
            if original_record["brep_sha256"] != source_contract["expected_brep_sha256"][key]:
                raise RuntimeError(f"Pinned source {key} BREP changed")
            difference = core.symmetric_difference(saved.Shape, original.Shape)
            if max(difference.values()) > validation["boolean_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Rev113 saved {key} geometry differs from Rev112")
            if any(saved_record[field] != original_record[field] for field in topology_fields):
                raise RuntimeError(f"Rev113 saved {key} topology differs from Rev112")
            frozen_records[key] = {"saved": saved_record, "source": original_record, "symmetric_difference_mm3": difference}

        tri005 = required_object(candidate, "REFERENCE__MOUTH_TRI005_REV112").Shape
        tri006 = required_object(candidate, "REFERENCE__MOUTH_TRI006_REV112").Shape
        source_tri005 = required_object(source, source_contract["mouth_tri005_object"]).Shape
        source_tri006 = required_object(source, source_contract["mouth_tri006_object"]).Shape
        original_mouth_records = {}
        for key, saved, original in (
            ("mouth_tri005", tri005, source_tri005),
            ("mouth_tri006", tri006, source_tri006),
        ):
            saved_record = core.require_closed_solids(saved, f"Saved reference {key}", 1)
            original_record = core.require_closed_solids(original, f"Source {key}", 1)
            if original_record["brep_sha256"] != source_contract["expected_brep_sha256"][key]:
                raise RuntimeError(f"Rev112 source {key} changed")
            difference = core.symmetric_difference(saved, original)
            if max(difference.values()) > validation["boolean_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Rev113 reference {key} differs from Rev112")
            if any(saved_record[field] != original_record[field] for field in topology_fields):
                raise RuntimeError(f"Rev113 reference {key} topology differs from Rev112")
            original_mouth_records[key] = {"saved": saved_record, "source": original_record, "symmetric_difference_mm3": difference}

        bridge_record = core.require_closed_solids(bridge.Shape, "Reopened Rev113 bridge", 1)
        if abs(bridge_record["volume_mm3"] - operation["expected_bridge_volume_mm3"]) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Saved Rev113 bridge volume changed")
        if abs(print_records["merged_mouth"]["volume_mm3"] - operation["expected_merged_volume_mm3"]) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Saved Rev113 merged-mouth volume changed")
        if core.bbox_residual(mouth.Shape, operation["expected_merged_bbox_min_mm"], operation["expected_merged_bbox_max_mm"]) > validation["bbox_tolerance_mm"]:
            raise RuntimeError("Saved Rev113 merged-mouth bounds changed")
        preservation = {
            "mouth_tri005_minus_merged_mm3": float(tri005.cut(mouth.Shape).Volume),
            "mouth_tri006_minus_merged_mm3": float(tri006.cut(mouth.Shape).Volume),
        }
        if max(preservation.values()) > validation["boolean_residual_volume_maximum_mm3"]:
            raise RuntimeError("Saved Rev113 mouth does not preserve both original halves")
        original_compound = Part.makeCompound([tri005, tri006])
        addition_outside_originals = float(mouth.Shape.cut(original_compound).Volume)
        addition_vs_bridge_residual = abs(addition_outside_originals - float(bridge.Shape.Volume))
        if addition_vs_bridge_residual > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Saved Rev113 addition is not exactly the saved bridge")
        merged_head_overlap = float(mouth.Shape.common(head.Shape).Volume)
        if merged_head_overlap > validation["pane_head_overlap_maximum_mm3"]:
            raise RuntimeError("Saved Rev113 merged mouth collides with the head")

        zip_residuals = {}
        for side in ("RIGHT", "LEFT"):
            corridor = required_object(candidate, f"REVIEW_ONLY__{side}_ZIP_TIE_CORRIDOR_REV113").Shape
            residual = float(head.Shape.common(corridor).Volume)
            if residual > validation["zip_tie_corridor_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Rev113 {side.lower()} zip-tie corridor is obstructed")
            zip_residuals[side.lower()] = residual

        print("Rev113 validation 3 of 4: run OCCT BOP checks on the changed mouth solid", flush=True)
        check_errors = list(mouth.Shape.check(True) or [])
        if check_errors:
            raise RuntimeError(f"OCCT BOP check reported merged-mouth errors: {check_errors!r}")
        bop_report = {
            "status": "PASS_OCCT_BOP_CHECK",
            "candidate_fcstd": output["candidate_fcstd"],
            "candidate_sha256": core.sha256(candidate_path),
            "object": mouth.Name,
            "errors": [],
        }
        bop_path = candidate_path.parent / "occt-bop-check-report.json"
        bop_path.write_text(json.dumps(bop_report, indent=2) + "\n", encoding="utf-8")
    finally:
        App.closeDocument(source.Name)
        App.closeDocument(candidate.Name)

    source_hash_after = core.sha256(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Pinned Rev112 source changed during Rev113 validation")

    print("Rev113 validation 4 of 4: inspect all four print STLs and the review bridge", flush=True)
    stl_keys = ("head_stl", "right_eye_stl", "left_eye_stl", "merged_mouth_stl", "bridge_review_stl")
    mesh_records = {key: prusa_info(core.REPO_ROOT / output[key]) for key in stl_keys}
    for key, expected_sha in source_contract["rev112_stl_sha256"].items():
        report_key = {"head": "head_stl", "right_eye": "right_eye_stl", "left_eye": "left_eye_stl"}[key]
        if mesh_records[report_key]["sha256"] != expected_sha:
            raise RuntimeError(f"Rev113 frozen {key} STL differs byte-for-byte from Rev112")
    for export_key, export_record in generation["mesh_exports"].items():
        report_key = {
            "head": "head_stl",
            "right_eye": "right_eye_stl",
            "left_eye": "left_eye_stl",
            "merged_mouth": "merged_mouth_stl",
            "review_only_bridge": "bridge_review_stl",
        }[export_key]
        if mesh_records[report_key]["sha256"] != export_record["sha256"]:
            raise RuntimeError(f"Published Rev113 STL hash changed: {report_key}")

    report = {
        "status": "PASS_REV113_MERGED_MOUTH_CAD_AND_MESH_REVIEW_VALIDATION",
        "review_state": contract["review_state"],
        "iteration_id": contract["iteration_id"],
        "contract_sha256": core.sha256(core.CONTRACT_PATH),
        "generation_report_sha256": core.sha256(generation_path),
        "candidate_fcstd": output["candidate_fcstd"],
        "candidate_sha256": core.sha256(candidate_path),
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "final_body": body_record,
        "print_parts": print_records,
        "frozen_geometry": frozen_records,
        "original_mouth_halves": original_mouth_records,
        "bridge": bridge_record,
        "original_halves_preservation": preservation,
        "addition_outside_originals_mm3": addition_outside_originals,
        "addition_vs_bridge_volume_residual_mm3": addition_vs_bridge_residual,
        "merged_head_overlap_mm3": merged_head_overlap,
        "zip_tie_corridor_residuals_mm3": zip_residuals,
        "occt_bop_check": {
            "report": str(bop_path.relative_to(core.REPO_ROOT)),
            "report_sha256": core.sha256(bop_path),
            "status": bop_report["status"],
            "errors": [],
        },
        "prusa_slicer_mesh_validation": mesh_records,
        "final_print_part_count": 4,
        "final_release_promoted": False,
        "slicer_project_created_or_changed": False,
        "physical_insertion_and_slicer_fit_pending": True,
    }
    report_path = candidate_path.parent / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "report": str(report_path.relative_to(core.REPO_ROOT)),
        "candidate_sha256": report["candidate_sha256"],
        "merged_mouth": report["print_parts"]["merged_mouth"],
        "bridge_volume_mm3": report["bridge"]["volume_mm3"],
        "merged_head_overlap_mm3": merged_head_overlap,
        "zip_tie_corridor_residuals_mm3": zip_residuals,
        "production_stl_count": 4,
        "all_stls_manifold_single_part": True,
    }, indent=2))


if __name__ == "__main__":
    main()
