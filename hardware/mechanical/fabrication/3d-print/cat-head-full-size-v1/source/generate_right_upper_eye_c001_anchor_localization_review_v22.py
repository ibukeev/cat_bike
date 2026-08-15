#!/usr/bin/env python3
"""Generate the review-only V22 C001/eye anchor-localization package.

This script copies the frozen V21 source objects into a new document and
exposes only the exact C001 BREP faces that touch the C001/eye diagnostic.
It does not trim, fuse, cut, mirror, or export production geometry.
"""

from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App
import Part


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = (
    PACKAGE_ROOT
    / "output/70-freecad-pilots/opposite-side-flange-pilot-v1"
)
SOURCE_REVIEW = (
    PILOT_ROOT
    / "right-upper-eye-residual-collision-localization-review-v21"
    / "CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21.FCStd"
)
OUTPUT_DIR = PILOT_ROOT / "right-upper-eye-c001-anchor-localization-review-v22"
OUTPUT_FCSTD = OUTPUT_DIR / "CAT_HEAD_RIGHT_UPPER_EYE_C001_ANCHOR_LOCALIZATION_REVIEW_V22.FCStd"
OUTPUT_JSON = OUTPUT_DIR / "validation-v22.json"

SOURCE_NAME = (
    "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C001_SOLID_V3_ref_ref_ref_ref"
)
EYE_NAME = "PROPOSED__RIGHT_EYE_BUCKET_WITH_BOTH_EXACT_FLANGE_ROOTS_V17_ref_ref_ref_ref"
DIAGNOSTIC_NAME = "DIAGNOSTIC__EYE_INTERSECTION__C001__V21"

# These are the dominant exact BREP faces found by the read-only V21 audit.
# Face364 and Face385 are deliberately excluded: their selected cursor points
# were outside the saved C001/eye collision bounds.
TOP_FACES = (382,)
SIDE_FACES = (324, 536, 554)
REJECTED_PREVIOUS_FACES = (364, 385)


def vector_tuple(vector: App.Vector) -> list[float]:
    return [round(float(vector.x), 9), round(float(vector.y), 9), round(float(vector.z), 9)]


def bbox_dict(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [round(box.XMin, 9), round(box.YMin, 9), round(box.ZMin, 9)],
        "maximum_mm": [round(box.XMax, 9), round(box.YMax, 9), round(box.ZMax, 9)],
    }


def add_shape(document, name: str, shape, label: str | None = None):
    obj = document.addObject("Part::Feature", name)
    obj.Label = label or name
    obj.Shape = shape.copy()
    return obj


def add_face_candidate(document, source, diagnostic, index: int, region: str):
    face = source.Shape.Faces[index - 1]
    common = face.common(diagnostic.Shape)
    name = f"REVIEW_ONLY__C001__{region}__FACE{index}__V22"
    obj = add_shape(document, name, face)
    obj.addProperty("App::PropertyString", "SourceObject", "Traceability")
    obj.addProperty("App::PropertyString", "SourceFace", "Traceability")
    obj.addProperty("App::PropertyString", "ReviewStatus", "ChangeControl")
    obj.addProperty("App::PropertyString", "AllowedAction", "ChangeControl")
    obj.addProperty("App::PropertyFloat", "DiagnosticCommonAreaMm2", "Audit")
    obj.SourceObject = SOURCE_NAME
    obj.SourceFace = f"Face{index}"
    obj.ReviewStatus = "CANDIDATE_ONLY__USER_APPROVAL_REQUIRED"
    obj.AllowedAction = "NONE__NO_TRIM_AUTHORIZED"
    obj.DiagnosticCommonAreaMm2 = float(common.Area)
    obj.ViewObject.ShapeColor = (1.0, 0.75, 0.0)
    obj.ViewObject.LineColor = (0.75, 0.20, 0.0)
    obj.ViewObject.LineWidth = 4.0
    return obj, {
        "object": name,
        "source_face": f"Face{index}",
        "region": region,
        "centroid_mm": vector_tuple(face.CenterOfMass),
        "area_mm2": round(float(face.Area), 9),
        "diagnostic_common_area_mm2": round(float(common.Area), 9),
        "diagnostic_common_length_mm": round(float(common.Length), 9),
        "bounds": bbox_dict(face),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_document = App.openDocument(str(SOURCE_REVIEW))
    review_document = App.newDocument("CAT_HEAD_RIGHT_UPPER_EYE_C001_ANCHOR_LOCALIZATION_REVIEW_V22")
    try:
        source = source_document.getObject(SOURCE_NAME)
        eye = source_document.getObject(EYE_NAME)
        diagnostic = source_document.getObject(DIAGNOSTIC_NAME)
        if source is None or eye is None or diagnostic is None:
            raise RuntimeError("V21 source, exact eye, or C001 diagnostic is missing")

        frozen_group = review_document.addObject("App::DocumentObjectGroup", "FROZEN_CONTEXT__V22")
        frozen_source = add_shape(review_document, "FROZEN__C001_SOURCE__V22", source.Shape)
        frozen_eye = add_shape(review_document, "FROZEN__EXACT_EYE__V17__V22", eye.Shape)
        frozen_diagnostic = add_shape(
            review_document, "DIAGNOSTIC__C001_EYE_INTERSECTION__V21__V22", diagnostic.Shape
        )
        frozen_group.addObject(frozen_source)
        frozen_group.addObject(frozen_eye)
        frozen_group.addObject(frozen_diagnostic)
        frozen_source.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
        frozen_source.ViewObject.Transparency = 78
        frozen_eye.ViewObject.ShapeColor = (0.35, 0.80, 1.0)
        frozen_eye.ViewObject.Transparency = 68
        frozen_diagnostic.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
        frozen_diagnostic.ViewObject.Transparency = 5

        top_group = review_document.addObject("App::DocumentObjectGroup", "REVIEW__TOP_CANDIDATES__V22")
        side_group = review_document.addObject("App::DocumentObjectGroup", "REVIEW__SIDE_CANDIDATES__V22")
        records = []
        for index in TOP_FACES:
            obj, record = add_face_candidate(review_document, source, diagnostic, index, "TOP")
            top_group.addObject(obj)
            records.append(record)
        for index in SIDE_FACES:
            obj, record = add_face_candidate(review_document, source, diagnostic, index, "SIDE")
            side_group.addObject(obj)
            records.append(record)

        rejected_group = review_document.addObject("App::DocumentObjectGroup", "REJECTED_ANCHORS__V22")
        for index in REJECTED_PREVIOUS_FACES:
            face = source.Shape.Faces[index - 1]
            obj = add_shape(
                review_document,
                f"REJECTED__WRONG_C001_ANCHOR__FACE{index}__V22",
                face,
            )
            obj.addProperty("App::PropertyString", "Reason", "ChangeControl")
            obj.Reason = "OUTSIDE_SAVED_C001_EYE_COLLISION_BOUNDS__DO_NOT_TRIM"
            obj.ViewObject.ShapeColor = (0.35, 0.35, 0.35)
            obj.ViewObject.Visibility = False
            rejected_group.addObject(obj)

        contract = review_document.addObject("App::FeaturePython", "C001_CHANGE_CONTROL_CONTRACT__V22")
        contract.addProperty("App::PropertyString", "Status", "Contract")
        contract.addProperty("App::PropertyString", "TargetClearance", "Contract")
        contract.addProperty("App::PropertyString", "ProtectedGeometry", "Contract")
        contract.addProperty("App::PropertyString", "AuthorizedOperation", "Contract")
        contract.Status = "REVIEW_ONLY__CORRECTED_FACE_APPROVAL_REQUIRED"
        contract.TargetClearance = ">= 4.0 mm from exact V17 eye"
        contract.ProtectedGeometry = (
            "Exact V17 eye; all visible exterior; C006; lower/rear ownership; ears; V0.5-M2"
        )
        contract.AuthorizedOperation = "NONE__NO_CUT_OR_TRIM_IN_V22"

        review_document.recompute()
        review_document.saveAs(str(OUTPUT_FCSTD))

        report = {
            "status": "REVIEW_ONLY__NO_GEOMETRY_CHANGE",
            "source_review": str(SOURCE_REVIEW.relative_to(PACKAGE_ROOT)),
            "review_file": str(OUTPUT_FCSTD.relative_to(PACKAGE_ROOT)),
            "source_object": SOURCE_NAME,
            "exact_eye_object": EYE_NAME,
            "diagnostic_object": DIAGNOSTIC_NAME,
            "diagnostic_bounds": bbox_dict(diagnostic.Shape),
            "candidate_faces": records,
            "rejected_previous_faces": [f"Face{index}" for index in REJECTED_PREVIOUS_FACES],
            "numeric_contract": {
                "minimum_eye_clearance_mm": 4.0,
                "preserve_exact_eye": True,
                "preserve_visible_exterior": True,
                "preserve_c006": True,
                "preserve_lower_and_rear_ownership": True,
                "preserve_ears": True,
                "preserve_aluminum_v05_m2": True,
            },
            "authorized_geometry_change": False,
            "next_review": (
                "Approve or reject Face382 for TOP and Face324/Face536/Face554 for SIDE. "
                "No trim may be generated before that corrected approval."
            ),
        }
        OUTPUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        App.closeDocument(review_document.Name)
        App.closeDocument(source_document.Name)


if __name__ == "__main__":
    main()
