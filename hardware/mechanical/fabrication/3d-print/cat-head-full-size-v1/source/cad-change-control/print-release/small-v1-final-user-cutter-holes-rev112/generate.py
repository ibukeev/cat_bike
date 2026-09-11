#!/usr/bin/env python3
"""One-shot generator for the Rev112 final head and unchanged translucent panes."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import FreeCAD as App
import MeshPart

import core


def export_mesh(shape, staging_path: Path, published_relative_path: str, contract: dict) -> dict:
    validation = contract["validation"]
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=validation["mesh_linear_deflection_mm"],
        AngularDeflection=validation["mesh_angular_deflection_rad"],
        Relative=False,
    )
    if mesh.CountFacets <= 0:
        raise RuntimeError(f"No facets generated for {staging_path.name}")
    mesh.write(str(staging_path))
    if not staging_path.is_file() or staging_path.stat().st_size <= 0:
        raise RuntimeError(f"Mesh export failed for {staging_path.name}")
    return {
        "path": published_relative_path,
        "sha256": core.sha256(staging_path),
        "bytes": staging_path.stat().st_size,
        "facets": int(mesh.CountFacets),
        "points": int(mesh.CountPoints),
        "volume_mm3": float(mesh.Volume),
    }


def main() -> None:
    contract = core.load_contract()
    output = contract["output"]
    preflight_path = core.REPO_ROOT / output["preflight_report"]
    if not preflight_path.is_file():
        raise RuntimeError("Rev112 passed no-output preflight report is missing")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS":
        raise RuntimeError("Rev112 no-output preflight did not pass")
    if preflight.get("contract_sha256") != core.sha256(core.CONTRACT_PATH):
        raise RuntimeError("Rev112 contract changed after no-output preflight")

    source_path = core.REPO_ROOT / contract["source"]["path"]
    source_hash_before = core.sha256(source_path)
    if source_hash_before != contract["source"]["sha256"]:
        raise RuntimeError("Rev112 source changed before generation")

    candidate_directory = core.REPO_ROOT / output["candidate_directory"]
    staging_directory = candidate_directory.parent / f".{candidate_directory.name}.staging"
    if candidate_directory.exists():
        raise RuntimeError("Rev112 candidate directory already exists; one-shot generator refuses overwrite")
    if staging_directory.exists():
        raise RuntimeError("Rev112 staging directory already exists; inspect it before retrying")
    staging_directory.mkdir(parents=True, exist_ok=False)

    succeeded = False
    try:
        package = core.construct_package(contract)
        document = App.newDocument("CAT_HEAD_MEDIUM_ILYA_FINAL_CUT_HOLES_REV112")
        try:
            finalization = core.finalize_document(document, package, contract)
            head = document.getObject(finalization["head_object"])
            panes = {
                key: document.getObject(name) for key, name in finalization["pane_objects"].items()
            }
            if head.ViewObject is not None:
                head.ViewObject.ShapeColor = (0.72, 0.76, 0.80)
            for pane in panes.values():
                if pane.ViewObject is not None:
                    pane.ViewObject.ShapeColor = (0.35, 0.90, 0.95)
                    pane.ViewObject.Transparency = 55
            for name in finalization["review_evidence_objects"]:
                evidence = document.getObject(name)
                if evidence.ViewObject is not None:
                    evidence.ViewObject.Visibility = False
            document.recompute()

            candidate_name = Path(output["candidate_fcstd"]).name
            staging_fcstd = staging_directory / candidate_name
            document.saveAs(str(staging_fcstd))
            if not staging_fcstd.is_file() or staging_fcstd.stat().st_size <= 0:
                raise RuntimeError("Rev112 FCStd save failed")

            mesh_exports = {
                "head": export_mesh(
                    head.Shape,
                    staging_directory / Path(output["head_stl"]).name,
                    output["head_stl"],
                    contract,
                ),
                "right_eye": export_mesh(
                    panes["right_eye"].Shape,
                    staging_directory / Path(output["right_eye_stl"]).name,
                    output["right_eye_stl"],
                    contract,
                ),
                "left_eye": export_mesh(
                    panes["left_eye"].Shape,
                    staging_directory / Path(output["left_eye_stl"]).name,
                    output["left_eye_stl"],
                    contract,
                ),
                "mouth_TRI005": export_mesh(
                    panes["mouth_TRI005"].Shape,
                    staging_directory / Path(output["mouth_tri005_stl"]).name,
                    output["mouth_tri005_stl"],
                    contract,
                ),
                "mouth_TRI006": export_mesh(
                    panes["mouth_TRI006"].Shape,
                    staging_directory / Path(output["mouth_tri006_stl"]).name,
                    output["mouth_tri006_stl"],
                    contract,
                ),
            }
            candidate_sha256 = core.sha256(staging_fcstd)
            candidate_bytes = staging_fcstd.stat().st_size
        finally:
            App.closeDocument(document.Name)

        source_hash_after = core.sha256(source_path)
        if source_hash_after != source_hash_before:
            raise RuntimeError("Pinned source FCStd changed during Rev112 generation")

        report = {
            "status": "GENERATED_PRINTABLE_GEOMETRY__VALIDATION_PENDING",
            "iteration_id": contract["iteration_id"],
            "design_id": contract["design_id"],
            "tooling_revision": contract["tooling_revision"],
            "contract_path": str(core.CONTRACT_PATH.relative_to(core.REPO_ROOT)),
            "contract_sha256": core.sha256(core.CONTRACT_PATH),
            "preflight_path": output["preflight_report"],
            "preflight_sha256": core.sha256(preflight_path),
            "source_path": contract["source"]["path"],
            "source_sha256_before": source_hash_before,
            "source_sha256_after": source_hash_after,
            "candidate_fcstd": output["candidate_fcstd"],
            "candidate_sha256": candidate_sha256,
            "candidate_bytes": candidate_bytes,
            "mesh_exports": mesh_exports,
            "construction_evidence": package["evidence"],
            "finalization": finalization,
            "release_scope": {
                "new_final_head_body_created": True,
                "all_four_user_cutters_subtracted": True,
                "head_and_four_panel_stls_created": True,
                "source_fcstd_overwritten": False,
                "translucent_panes_changed": False,
                "slicer_project_created_or_changed": False,
                "gcode_created": False,
            },
        }
        report_path = staging_directory / Path(output["generation_report"]).name
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        staging_directory.rename(candidate_directory)
        succeeded = True
        print(json.dumps({
            "status": report["status"],
            "candidate_fcstd": output["candidate_fcstd"],
            "candidate_sha256": candidate_sha256,
            "head_stl": output["head_stl"],
            "individual_cutter_overlaps_mm3": package["evidence"]["individual_cutter_overlaps_mm3"],
            "removed_volume_mm3": package["evidence"]["removed_volume_mm3"],
            "cutter_residual_volume_mm3": package["evidence"]["cutter_residual_volume_mm3"],
            "zip_tie_final_residuals_mm3": package["evidence"]["zip_tie_final_residuals_mm3"],
        }, indent=2))
    finally:
        if not succeeded and staging_directory.exists():
            shutil.rmtree(staging_directory)


if __name__ == "__main__":
    main()
