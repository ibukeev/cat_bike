#!/usr/bin/env python3
"""Create and open a presentation-only visible copy of a preserved FCStd."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fcstd_preservation_v2 as preservation


TARGET = "CAVITY_ONLY_3MM_SHELL"
HIDDEN_OBJECTS = {
    "REFERENCE__INNER_CAVITY",
    "REFERENCE__FROZEN_OUTER",
    "CavityReviewParameters",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def write_visible_review_archive(
    candidate_path: Path,
    presentation_source_path: Path,
    output_path: Path,
) -> dict:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")
    candidate_presentation = preservation.presentation_entry_names(
        candidate_path,
        allow_missing_gui_document=True,
    )
    if candidate_presentation:
        raise RuntimeError("candidate is not the expected headless FCStd")
    presentation_names = preservation.presentation_entry_names(
        presentation_source_path,
    )
    if preservation.GUI_DOCUMENT not in presentation_names:
        raise RuntimeError("temporary GUI save did not create GuiDocument.xml")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_path.with_suffix(output_path.suffix + ".tmp")
    if temporary_output.exists():
        raise FileExistsError(f"refusing to overwrite {temporary_output}")
    try:
        with zipfile.ZipFile(candidate_path, "r") as candidate_archive:
            candidate_infos = preservation.unique_zip_infos(candidate_archive)
            with zipfile.ZipFile(presentation_source_path, "r") as source_archive:
                source_infos = preservation.unique_zip_infos(source_archive)
                with zipfile.ZipFile(temporary_output, "w", allowZip64=True) as output:
                    output.comment = candidate_archive.comment
                    for info in candidate_archive.infolist():
                        output.writestr(info, candidate_archive.read(info.filename))
                    for name in presentation_names:
                        if name in candidate_infos:
                            raise RuntimeError(
                                f"presentation entry already exists in candidate: {name}"
                            )
                        output.writestr(source_infos[name], source_archive.read(name))
        os.replace(temporary_output, output_path)
    finally:
        temporary_output.unlink(missing_ok=True)

    with zipfile.ZipFile(candidate_path, "r") as candidate_archive:
        candidate_infos = preservation.unique_zip_infos(candidate_archive)
        candidate_payloads = {
            name: hashlib.sha256(candidate_archive.read(name)).hexdigest()
            for name in candidate_infos
        }
    with zipfile.ZipFile(output_path, "r") as output_archive:
        output_infos = preservation.unique_zip_infos(output_archive)
        unchanged_payloads = all(
            name in output_infos
            and hashlib.sha256(output_archive.read(name)).hexdigest() == digest
            for name, digest in candidate_payloads.items()
        )
    if not unchanged_payloads:
        raise RuntimeError("visible review copy changed a candidate archive payload")
    if preservation.raw_shape_digests(candidate_path) != preservation.raw_shape_digests(
        output_path
    ):
        raise RuntimeError("visible review copy changed raw Shape.brp bytes")
    presentation_check = preservation.presentation_comparison(
        presentation_source_path,
        output_path,
    )
    if presentation_check["status"] != "PASS":
        raise RuntimeError("visible review presentation injection failed")
    return {
        "candidate_entry_count": len(candidate_payloads),
        "visible_entry_count": len(output_infos),
        "presentation_entries_added": list(presentation_names),
        "candidate_payloads_unchanged": unchanged_payloads,
        "raw_shape_payloads_unchanged": True,
        "presentation": presentation_check,
    }


def main() -> None:
    import FreeCAD as App
    import FreeCADGui as Gui

    candidate_path = Path(os.environ["CAT_HEAD_VISIBLE_SOURCE_FCSTD"]).resolve()
    preservation_path = Path(
        os.environ["CAT_HEAD_VISIBLE_PRESERVATION_REPORT"]
    ).resolve()
    output_path = Path(os.environ["CAT_HEAD_VISIBLE_OUTPUT_FCSTD"]).resolve()
    report_path = Path(os.environ["CAT_HEAD_VISIBLE_OUTPUT_REPORT"]).resolve()
    expected_candidate_hash = os.environ["CAT_HEAD_VISIBLE_SOURCE_SHA256"]
    if output_path.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite visible FreeCAD review output")
    candidate_hash_before = sha256(candidate_path)
    if candidate_hash_before != expected_candidate_hash:
        raise RuntimeError("candidate FCStd hash mismatch")
    preservation_report = load_json(preservation_path)
    if preservation_report.get("status") != "PASS__READY_FOR_FIXED_VIEW_REVIEW":
        raise RuntimeError("candidate did not pass independent preservation")
    if preservation_report.get("candidate", {}).get("sha256") != candidate_hash_before:
        raise RuntimeError("preservation report references another candidate")

    with tempfile.TemporaryDirectory(
        prefix="cat-head-rev98-visible-freecad-",
        dir="/tmp",
    ) as temporary_name:
        presentation_source = Path(temporary_name) / "presentation-source.FCStd"
        document = App.openDocument(str(candidate_path))
        try:
            target = document.getObject(TARGET)
            if target is None or target.Shape.isNull() or not target.Shape.isValid():
                raise RuntimeError("candidate target is missing or invalid")
            for obj in document.Objects:
                try:
                    obj.ViewObject.Visibility = False
                except Exception:
                    pass
            target.ViewObject.Visibility = True
            target.ViewObject.ShapeColor = (0.82, 0.86, 0.92)
            target.ViewObject.LineColor = (0.12, 0.12, 0.12)
            target.ViewObject.Transparency = 0
            try:
                target.ViewObject.DisplayMode = "Flat Lines"
            except Exception:
                pass
            for possible_parent in document.Objects:
                if hasattr(possible_parent, "Group") and any(
                    child.Name == TARGET for child in possible_parent.Group
                ):
                    possible_parent.ViewObject.Visibility = True
            for name in HIDDEN_OBJECTS:
                obj = document.getObject(name)
                if obj is not None:
                    obj.ViewObject.Visibility = False
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
            Gui.updateGui()
            document.saveAs(str(presentation_source))
            document.recompute()
            document.save()
        finally:
            App.closeDocument(document.Name)

        archive_result = write_visible_review_archive(
            candidate_path,
            presentation_source,
            output_path,
        )

    candidate_hash_after = sha256(candidate_path)
    if candidate_hash_after != candidate_hash_before:
        raise RuntimeError("validated Revision 98 candidate changed")
    visible_hash = sha256(output_path)
    result = {
        "status": "CREATED__VISIBLE_FREECAD_REVIEW_COPY",
        "role": "PRESENTATION_ONLY__NOT_GEOMETRY_SOURCE",
        "candidate_fcstd": str(candidate_path),
        "candidate_fcstd_sha256_before": candidate_hash_before,
        "candidate_fcstd_sha256_after": candidate_hash_after,
        "candidate_unchanged": True,
        "preservation_report": str(preservation_path),
        "visible_review_fcstd": str(output_path),
        "visible_review_fcstd_sha256": visible_hash,
        "target_visible": TARGET,
        "hidden_review_objects": sorted(HIDDEN_OBJECTS),
        "camera": "AXONOMETRIC__FIT_ALL",
        "geometry_mutation_performed": False,
        "archive": archive_result,
    }
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("CAT_HEAD_VISIBLE_FREECAD_JSON=" + json.dumps(result, sort_keys=True))

    visible_document = App.openDocument(str(output_path))
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()
    Gui.activeDocument().activeView().redraw()
    print(f"VISIBLE_FREECAD_READY={visible_document.Name}", flush=True)


if __name__ == "__main__":
    main()
