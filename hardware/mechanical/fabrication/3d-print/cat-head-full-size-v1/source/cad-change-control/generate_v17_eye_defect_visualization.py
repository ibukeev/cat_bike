#!/usr/bin/env python3
"""Generate the approved review-only V17 eye defect visualization.

The exact frozen V17 STEP is copied into a new FreeCAD document together with
five separately colored source faces representing the three localized,
non-adjacent OCCT defect pairs. This script never heals, cuts, fuses, moves,
mirrors, or saves over a source artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App
import FreeCADGui as Gui
import Part

from validate_change_contract import load_json, validate_files


FACE_STYLE = {
    587: ((1.0, 0.15, 0.10), "V9_SKIN_SHARED_FACE"),
    263: ((1.0, 0.50, 0.05), "V9_SKIN_PAIR_A"),
    400: ((1.0, 0.90, 0.05), "V9_SKIN_PAIR_B"),
    72: ((0.70, 0.25, 1.0), "OUTER_INWARD_ROOT_PAIR_A"),
    489: ((0.10, 0.85, 1.0), "OUTER_INWARD_ROOT_PAIR_B"),
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def artifact_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in manifest["artifacts"]}


def bbox(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [round(box.XMin, 9), round(box.YMin, 9), round(box.ZMin, 9)],
        "maximum_mm": [round(box.XMax, 9), round(box.YMax, 9), round(box.ZMax, 9)],
    }


def vector(vector_value) -> list[float]:
    return [
        round(float(vector_value.x), 9),
        round(float(vector_value.y), 9),
        round(float(vector_value.z), 9),
    ]


def add_shape(document, name: str, shape, label: str | None = None):
    obj = document.addObject("Part::Feature", name)
    obj.Label = label or name
    obj.Shape = shape.copy()
    return obj


def ensure_gui_view_providers() -> None:
    """Initialize an isolated GUI context so FCStd display colors are persisted."""
    Gui.showMainWindow()
    Gui.updateGui()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.manifest)
    preflight = validate_files(args.manifest, args.contract, verify_files=True)
    if preflight["status"] != "PASS":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 1

    manifest = load_json(args.manifest)
    contract = load_json(args.contract)
    if contract.get("contract_id") != "read-only-v17-eye-defect-visualization-v1":
        raise RuntimeError("wrong contract for V17 defect visualization")
    if contract.get("geometry_changes_allowed") is not False:
        raise RuntimeError("geometry changes must remain forbidden")

    artifacts = artifact_map(manifest)
    source_path = root / artifacts["right_eye_v17"]["path"]
    lineage_path = root / artifacts["right_eye_v17_lineage_fcstd"]["path"]
    visualization = contract["review_visualization"]
    output_fcstd = root / visualization["output_fcstd"]
    report_dir = root / contract["output_directory"]
    output_report = report_dir / "validation-v1.json"

    if output_fcstd.exists() or output_report.exists():
        raise RuntimeError("refusing to overwrite an existing V17 visualization artifact")

    source_hash_before = sha256_file(source_path)
    lineage_hash_before = sha256_file(lineage_path)
    source_shape = Part.read(str(source_path))
    if source_shape.isNull():
        raise RuntimeError("V17 STEP imported as a null shape")
    if len(source_shape.Faces) < max(FACE_STYLE):
        raise RuntimeError(f"V17 STEP has only {len(source_shape.Faces)} faces")

    requested_pairs = [tuple(item["faces"]) for item in visualization["source_face_pairs"]]
    if requested_pairs != [(587, 263), (587, 400), (72, 489)]:
        raise RuntimeError("contract face pairs do not match the approved localization")

    output_fcstd.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    ensure_gui_view_providers()
    document = App.newDocument("CAT_HEAD_RIGHT_EYE_V17_DEFECT_VISUALIZATION_V1")
    face_records: list[dict[str, Any]] = []
    try:
        context_group = document.addObject("App::DocumentObjectGroup", "FROZEN_V17_CONTEXT")
        source_obj = add_shape(
            document,
            "FROZEN_EXACT_RIGHT_EYE_V17",
            source_shape,
            "FROZEN exact V17 right eye — review context",
        )
        source_obj.addProperty("App::PropertyString", "SourceArtifact", "Traceability")
        source_obj.addProperty("App::PropertyString", "SourceSha256", "Traceability")
        source_obj.addProperty("App::PropertyString", "AllowedAction", "ChangeControl")
        source_obj.SourceArtifact = artifacts["right_eye_v17"]["path"]
        source_obj.SourceSha256 = source_hash_before
        source_obj.AllowedAction = "REVIEW_ONLY__NO_GEOMETRY_CHANGE"
        source_obj.ViewObject.ShapeColor = (0.72, 0.72, 0.74)
        source_obj.ViewObject.Transparency = 72
        context_group.addObject(source_obj)

        v9_group = document.addObject("App::DocumentObjectGroup", "DEFECT_REGION__V9_SKIN")
        root_group = document.addObject(
            "App::DocumentObjectGroup", "DEFECT_REGION__OUTER_INWARD_ROOT"
        )
        for face_index, (color, role) in FACE_STYLE.items():
            face = source_shape.Faces[face_index - 1]
            obj = add_shape(
                document,
                f"REVIEW_ONLY__V17__FACE{face_index}__{role}",
                face,
                f"Face{face_index} — {role}",
            )
            obj.addProperty("App::PropertyString", "SourceArtifact", "Traceability")
            obj.addProperty("App::PropertyString", "SourceFace", "Traceability")
            obj.addProperty("App::PropertyString", "Region", "Localization")
            obj.addProperty("App::PropertyString", "AllowedAction", "ChangeControl")
            obj.SourceArtifact = "right_eye_v17"
            obj.SourceFace = f"Face{face_index}"
            obj.Region = (
                "V9_SKIN_DEFECT_REGION" if face_index in {587, 263, 400}
                else "OUTER_INWARD_ROOT_DEFECT_REGION"
            )
            obj.AllowedAction = "REVIEW_ONLY__NO_REPAIR_AUTHORIZED"
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = color
            obj.ViewObject.LineWidth = 5.0
            obj.ViewObject.Transparency = 0
            (v9_group if face_index in {587, 263, 400} else root_group).addObject(obj)
            face_records.append(
                {
                    "object": obj.Name,
                    "source_face": obj.SourceFace,
                    "role": role,
                    "region": obj.Region,
                    "area_mm2": round(float(face.Area), 9),
                    "centroid_mm": vector(face.CenterOfMass),
                    "bounds": bbox(face),
                }
            )

        read_me = document.addObject("App::FeaturePython", "READ_ME__V17_DEFECT_REVIEW")
        read_me.addProperty("App::PropertyString", "Status", "Review")
        read_me.addProperty("App::PropertyStringList", "DefectPairs", "Review")
        read_me.addProperty("App::PropertyString", "CleanRegion", "Review")
        read_me.addProperty("App::PropertyString", "GeometryAuthorization", "ChangeControl")
        read_me.addProperty("App::PropertyString", "ReleaseStatus", "ChangeControl")
        read_me.Status = "THREE_NON_ADJACENT_DEFECT_PAIRS_LOCALIZED"
        read_me.DefectPairs = ["Face587 / Face263", "Face587 / Face400", "Face72 / Face489"]
        read_me.CleanRegion = "SECOND_EYE_ROOT__CLEAN_DO_NOT_MODIFY"
        read_me.GeometryAuthorization = "NONE__VISUALIZATION_ONLY"
        read_me.ReleaseStatus = "NO_STL__NO_GCODE__NO_ASA_PRINT_RELEASE"

        document.recompute()
        document.saveAs(str(output_fcstd))
    finally:
        App.closeDocument(document.Name)

    source_hash_after = sha256_file(source_path)
    lineage_hash_after = sha256_file(lineage_path)
    if source_hash_after != source_hash_before or lineage_hash_after != lineage_hash_before:
        raise RuntimeError("a frozen source artifact changed during visualization generation")

    report = {
        "status": "PASS__REVIEW_ONLY_VISUALIZATION_GENERATED",
        "contract_id": contract["contract_id"],
        "source": {
            "path": artifacts["right_eye_v17"]["path"],
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "face_count": len(source_shape.Faces),
            "solid_count": len(source_shape.Solids),
            "valid": bool(source_shape.isValid()),
            "closed": bool(source_shape.isClosed()),
        },
        "lineage": {
            "path": artifacts["right_eye_v17_lineage_fcstd"]["path"],
            "sha256_before": lineage_hash_before,
            "sha256_after": lineage_hash_after,
        },
        "review_file": str(output_fcstd.relative_to(root)),
        "review_file_sha256": sha256_file(output_fcstd),
        "face_pairs": [list(pair) for pair in requested_pairs],
        "face_objects": face_records,
        "clean_region": visualization["clean_region"],
        "geometry_changes": 0,
        "production_geometry_authorized": False,
        "release_holds": contract["release_holds"],
        "next_review": (
            "Open the FCStd, toggle each defect group, and visually confirm the localized "
            "V9 skin and outer-inward-root regions. Do not approve a repair from this file."
        ),
    }
    output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
