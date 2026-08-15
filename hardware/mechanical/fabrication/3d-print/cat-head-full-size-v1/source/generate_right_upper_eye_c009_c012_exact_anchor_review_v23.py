#!/usr/bin/env python3
"""Generate the no-cut V23 exact-anchor review for C009 and upper C012.

The package copies frozen V21 source geometry and exposes exact FreeCAD BREP
cap/root faces. It does not trim, cut, fuse, mirror, or export production parts.
"""

from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = PACKAGE_ROOT / "output/70-freecad-pilots/opposite-side-flange-pilot-v1"
SOURCE_REVIEW = (
    PILOT_ROOT
    / "right-upper-eye-residual-collision-localization-review-v21"
    / "CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21.FCStd"
)
OUTPUT_DIR = PILOT_ROOT / "right-upper-eye-c009-c012-exact-anchor-review-v23"
OUTPUT_FCSTD = OUTPUT_DIR / "CAT_HEAD_RIGHT_UPPER_EYE_C009_C012_EXACT_ANCHOR_REVIEW_V23.FCStd"
OUTPUT_JSON = OUTPUT_DIR / "validation-v23.json"

EYE_NAME = "PROPOSED__RIGHT_EYE_BUCKET_WITH_BOTH_EXACT_FLANGE_ROOTS_V17_ref_ref_ref_ref"
TARGETS = {
    "C009": {
        "source": "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C009_SOLID_V3_ref_ref_ref_ref",
        "diagnostic": "DIAGNOSTIC__EYE_INTERSECTION__C009__V21",
        "eye_cap_face": 17,
        "root_cap_face": 13,
        "minimum_travel_mm": 13.98,
        "resulting_clearance_mm": 4.000005,
        "resulting_volume_mm3": 7.189814,
        "resulting_c001_engagement_mm3": 3.093939,
        "decision": "HOLD__STRUCTURAL_ADEQUACY_UNRESOLVED__NO_TRIM_AUTHORIZED",
    },
    "UPPER_C012": {
        "source": "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C012_SOLID_V3_ref_ref_ref_ref",
        "diagnostic": "DIAGNOSTIC__EYE_INTERSECTION__UPPER_C012__V21",
        "eye_cap_face": 4,
        "root_cap_face": 18,
        "minimum_travel_mm": 5.21,
        "resulting_clearance_mm": 4.000010,
        "resulting_volume_mm3": 606.537827,
        "decision": "CANDIDATE_ONLY__USER_BREP_FACE_APPROVAL_REQUIRED",
    },
}


def vector_tuple(vector: App.Vector) -> list[float]:
    return [round(float(vector.x), 9), round(float(vector.y), 9), round(float(vector.z), 9)]


def bbox_dict(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [round(box.XMin, 9), round(box.YMin, 9), round(box.ZMin, 9)],
        "maximum_mm": [round(box.XMax, 9), round(box.YMax, 9), round(box.ZMax, 9)],
    }


def add_shape(document, name: str, shape):
    obj = document.addObject("Part::Feature", name)
    obj.Label = name
    obj.Shape = shape.copy()
    return obj


def add_anchor(document, group, key: str, role: str, source, face_index: int, decision: str):
    face = source.Shape.Faces[face_index - 1]
    obj = add_shape(document, f"REVIEW_ONLY__{key}__{role}__FACE{face_index}__V23", face)
    obj.addProperty("App::PropertyString", "SourceObject", "Traceability")
    obj.addProperty("App::PropertyString", "SourceFace", "Traceability")
    obj.addProperty("App::PropertyString", "Decision", "ChangeControl")
    obj.addProperty("App::PropertyString", "AuthorizedOperation", "ChangeControl")
    obj.SourceObject = source.Name
    obj.SourceFace = f"Face{face_index}"
    obj.Decision = decision
    obj.AuthorizedOperation = "NONE__NO_GEOMETRY_CHANGE_IN_V23"
    group.addObject(obj)
    return obj, {
        "object": obj.Name,
        "source_face": f"Face{face_index}",
        "role": role,
        "area_mm2": round(float(face.Area), 9),
        "centroid_mm": vector_tuple(face.CenterOfMass),
        "bounds": bbox_dict(face),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_document = App.openDocument(str(SOURCE_REVIEW))
    review_document = App.newDocument("CAT_HEAD_RIGHT_UPPER_EYE_C009_C012_EXACT_ANCHOR_REVIEW_V23")
    try:
        eye = source_document.getObject(EYE_NAME)
        if eye is None:
            raise RuntimeError("Exact V17 eye missing from V21 review")

        frozen_group = review_document.addObject("App::DocumentObjectGroup", "FROZEN_CONTEXT__V23")
        frozen_eye = add_shape(review_document, "FROZEN__EXACT_EYE__V17__V23", eye.Shape)
        frozen_group.addObject(frozen_eye)

        records = {}
        for key, definition in TARGETS.items():
            source = source_document.getObject(definition["source"])
            diagnostic = source_document.getObject(definition["diagnostic"])
            if source is None or diagnostic is None:
                raise RuntimeError(f"V21 source or diagnostic missing for {key}")

            group = review_document.addObject("App::DocumentObjectGroup", f"REVIEW__{key}__V23")
            frozen_source = add_shape(review_document, f"FROZEN__{key}_SOURCE__V23", source.Shape)
            frozen_diagnostic = add_shape(
                review_document, f"DIAGNOSTIC__{key}_EYE_INTERSECTION__V21__V23", diagnostic.Shape
            )
            group.addObject(frozen_source)
            group.addObject(frozen_diagnostic)
            eye_cap, eye_cap_record = add_anchor(
                review_document,
                group,
                key,
                "EYE_CAP",
                source,
                definition["eye_cap_face"],
                definition["decision"],
            )
            root_cap, root_cap_record = add_anchor(
                review_document,
                group,
                key,
                "ROOT_CAP",
                source,
                definition["root_cap_face"],
                "FROZEN_ROOT_REFERENCE__DO_NOT_MOVE",
            )
            records[key] = {
                "source_object": source.Name,
                "diagnostic_object": diagnostic.Name,
                "diagnostic_bounds": bbox_dict(diagnostic.Shape),
                "eye_cap": eye_cap_record,
                "root_cap": root_cap_record,
                "minimum_travel_mm": definition["minimum_travel_mm"],
                "resulting_clearance_mm": definition["resulting_clearance_mm"],
                "resulting_volume_mm3": definition["resulting_volume_mm3"],
                "decision": definition["decision"],
            }
            if "resulting_c001_engagement_mm3" in definition:
                records[key]["resulting_c001_engagement_mm3"] = definition[
                    "resulting_c001_engagement_mm3"
                ]

        contract = review_document.addObject("App::FeaturePython", "CHANGE_CONTROL_CONTRACT__V23")
        contract.addProperty("App::PropertyString", "Status", "Contract")
        contract.addProperty("App::PropertyString", "AuthorizedOperation", "Contract")
        contract.addProperty("App::PropertyString", "ProtectedGeometry", "Contract")
        contract.Status = "REVIEW_ONLY__EXACT_BREP_ANCHORS__NO_CUT"
        contract.AuthorizedOperation = "NONE"
        contract.ProtectedGeometry = (
            "V17 eye; exterior; C006; ears; lower/rear owners; aluminum V0.5-M2"
        )

        review_document.recompute()
        review_document.saveAs(str(OUTPUT_FCSTD))

        report = {
            "status": "REVIEW_ONLY__NO_GEOMETRY_CHANGE",
            "source_review": str(SOURCE_REVIEW.relative_to(PACKAGE_ROOT)),
            "review_file": str(OUTPUT_FCSTD.relative_to(PACKAGE_ROOT)),
            "exact_eye_object": EYE_NAME,
            "targets": records,
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
            "next_review": [
                "C009: inspect Face17 against Face13; trim remains held regardless of face approval.",
                "Upper C012: inspect Face4 against fixed root Face18; approve or reject Face4.",
                "No trim, mirror, production union, STL, G-code, or print release is authorized.",
            ],
        }
        OUTPUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        App.closeDocument(review_document.Name)
        App.closeDocument(source_document.Name)


if __name__ == "__main__":
    main()
