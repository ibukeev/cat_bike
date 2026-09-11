#!/usr/bin/env python3
"""One-shot generator for the Rev113 four-part merged-mouth candidate."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import FreeCAD as App
import MeshPart

import core


def copy_frozen_stl(source: Path, destination: Path, published_relative_path: str, expected_sha256: str) -> dict:
    if core.sha256(source) != expected_sha256:
        raise RuntimeError(f"Frozen Rev112 STL hash changed: {source.name}")
    shutil.copyfile(source, destination)
    if core.sha256(destination) != expected_sha256:
        raise RuntimeError(f"Frozen STL byte copy failed: {destination.name}")
    return {
        "path": published_relative_path,
        "sha256": expected_sha256,
        "bytes": destination.stat().st_size,
        "frozen_byte_copy_from": str(source.relative_to(core.REPO_ROOT)),
    }


def export_mesh(shape, path: Path, published_relative_path: str, contract: dict) -> dict:
    validation = contract["validation"]
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=validation["mesh_linear_deflection_mm"],
        AngularDeflection=validation["mesh_angular_deflection_rad"],
        Relative=False,
    )
    if mesh.CountFacets <= 0:
        raise RuntimeError(f"No facets generated for {path.name}")
    mesh.write(str(path))
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"Mesh export failed for {path.name}")
    return {
        "path": published_relative_path,
        "sha256": core.sha256(path),
        "bytes": path.stat().st_size,
        "facets": int(mesh.CountFacets),
        "points": int(mesh.CountPoints),
        "volume_mm3": float(mesh.Volume),
    }


def main() -> None:
    contract = core.load_contract()
    output = contract["output"]
    preflight_path = core.REPO_ROOT / output["preflight_report"]
    if not preflight_path.is_file():
        raise RuntimeError("Rev113 passed no-output preflight report is missing")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS":
        raise RuntimeError("Rev113 no-output preflight did not pass")
    if preflight.get("contract_sha256") != core.sha256(core.CONTRACT_PATH):
        raise RuntimeError("Rev113 contract changed after no-output preflight")

    source_path = core.REPO_ROOT / contract["source"]["path"]
    source_hash_before = core.sha256(source_path)
    if source_hash_before != contract["source"]["sha256"]:
        raise RuntimeError("Rev112 source changed before Rev113 generation")

    candidate_directory = core.REPO_ROOT / output["candidate_directory"]
    staging_directory = candidate_directory.parent / f".{candidate_directory.name}.staging"
    if candidate_directory.exists():
        raise RuntimeError("Rev113 candidate directory exists; one-shot generator refuses overwrite")
    if staging_directory.exists():
        raise RuntimeError("Rev113 staging directory exists; inspect it before retrying")
    staging_directory.mkdir(parents=True, exist_ok=False)

    succeeded = False
    try:
        package = core.construct_package(contract)
        document = App.newDocument("CAT_HEAD_MEDIUM_ILYA_MERGED_MOUTH_REV113")
        try:
            finalization = core.finalize_document(document, package, contract)
            head = document.getObject(finalization["head_object"])
            eyes = {
                key: document.getObject(name)
                for key, name in finalization["eye_objects"].items()
            }
            mouth = document.getObject(finalization["merged_mouth_object"])
            bridge = document.getObject(finalization["bridge_object"])
            if head.ViewObject is not None:
                head.ViewObject.ShapeColor = (0.72, 0.76, 0.80)
            for eye in eyes.values():
                if eye.ViewObject is not None:
                    eye.ViewObject.ShapeColor = (0.35, 0.90, 0.95)
                    eye.ViewObject.Transparency = 55
            if mouth.ViewObject is not None:
                mouth.ViewObject.ShapeColor = (0.35, 0.90, 0.95)
                mouth.ViewObject.Transparency = 55
            for name in finalization["review_evidence_objects"]:
                evidence = document.getObject(name)
                if evidence.ViewObject is not None:
                    evidence.ViewObject.Visibility = False
            document.recompute()

            staging_fcstd = staging_directory / Path(output["candidate_fcstd"]).name
            document.saveAs(str(staging_fcstd))
            if not staging_fcstd.is_file() or staging_fcstd.stat().st_size <= 0:
                raise RuntimeError("Rev113 FCStd save failed")
            mesh_exports = {
                "head": copy_frozen_stl(
                    core.REPO_ROOT / contract["source"]["rev112_stl_paths"]["head"],
                    staging_directory / Path(output["head_stl"]).name,
                    output["head_stl"],
                    contract["source"]["rev112_stl_sha256"]["head"],
                ),
                "right_eye": copy_frozen_stl(
                    core.REPO_ROOT / contract["source"]["rev112_stl_paths"]["right_eye"],
                    staging_directory / Path(output["right_eye_stl"]).name,
                    output["right_eye_stl"],
                    contract["source"]["rev112_stl_sha256"]["right_eye"],
                ),
                "left_eye": copy_frozen_stl(
                    core.REPO_ROOT / contract["source"]["rev112_stl_paths"]["left_eye"],
                    staging_directory / Path(output["left_eye_stl"]).name,
                    output["left_eye_stl"],
                    contract["source"]["rev112_stl_sha256"]["left_eye"],
                ),
                "merged_mouth": export_mesh(mouth.Shape, staging_directory / Path(output["merged_mouth_stl"]).name, output["merged_mouth_stl"], contract),
                "review_only_bridge": export_mesh(bridge.Shape, staging_directory / Path(output["bridge_review_stl"]).name, output["bridge_review_stl"], contract),
            }
            candidate_sha256 = core.sha256(staging_fcstd)
            candidate_bytes = staging_fcstd.stat().st_size
        finally:
            App.closeDocument(document.Name)

        source_hash_after = core.sha256(source_path)
        if source_hash_after != source_hash_before:
            raise RuntimeError("Pinned Rev112 source changed during Rev113 generation")
        report = {
            "status": "GENERATED_REV113_REVIEW_CANDIDATE__VALIDATION_PENDING",
            "iteration_id": contract["iteration_id"],
            "design_id": contract["design_id"],
            "tooling_revision": contract["tooling_revision"],
            "review_state": contract["review_state"],
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
                "rev112_head_frozen": True,
                "rev112_eye_panes_frozen": True,
                "rev112_mouth_halves_preserved": True,
                "seam_only_bridge_added": True,
                "final_print_part_count": 4,
                "final_release_promoted": False,
                "slicer_project_created_or_changed": False,
                "gcode_created": False,
            },
        }
        report_path = staging_directory / Path(output["generation_report"]).name
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        staging_directory.rename(candidate_directory)
        succeeded = True
    finally:
        if not succeeded and staging_directory.exists():
            print(f"Rev113 staging preserved for diagnosis: {staging_directory}", flush=True)

    print(json.dumps({
        "status": report["status"],
        "candidate_fcstd": report["candidate_fcstd"],
        "candidate_sha256": report["candidate_sha256"],
        "mesh_exports": report["mesh_exports"],
        "review_state": report["review_state"],
    }, indent=2))


if __name__ == "__main__":
    main()
