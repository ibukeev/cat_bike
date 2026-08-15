#!/usr/bin/env python3
"""Read-only exact BREP-face audit for the V21 C009 and upper-C012 contacts.

Run inside FreeCAD's Python environment. The script opens the saved V21 review,
finds source BREP faces that geometrically touch each matching eye-intersection
diagnostic, and prints JSON. It never saves or changes the source document.
"""

from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    PACKAGE_ROOT
    / "output/70-freecad-pilots/opposite-side-flange-pilot-v1"
    / "right-upper-eye-residual-collision-localization-review-v21"
    / "CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21.FCStd"
)

TARGETS = {
    "C009": {
        "source": "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C009_SOLID_V3_ref_ref_ref_ref",
        "diagnostic": "DIAGNOSTIC__EYE_INTERSECTION__C009__V21",
    },
    "UPPER_C012": {
        "source": "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C012_SOLID_V3_ref_ref_ref_ref",
        "diagnostic": "DIAGNOSTIC__EYE_INTERSECTION__UPPER_C012__V21",
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


def boxes_overlap(first, second, tolerance: float = 1e-7) -> bool:
    return not (
        first.XMax < second.XMin - tolerance
        or first.XMin > second.XMax + tolerance
        or first.YMax < second.YMin - tolerance
        or first.YMin > second.YMax + tolerance
        or first.ZMax < second.ZMin - tolerance
        or first.ZMin > second.ZMax + tolerance
    )


def audit_target(document, key: str, definition: dict[str, str]) -> dict:
    source = document.getObject(definition["source"])
    diagnostic = document.getObject(definition["diagnostic"])
    if source is None or diagnostic is None:
        raise RuntimeError(f"V21 source or diagnostic missing for {key}")

    candidates = []
    diagnostic_box = diagnostic.Shape.BoundBox
    for index, face in enumerate(source.Shape.Faces, start=1):
        if not boxes_overlap(face.BoundBox, diagnostic_box):
            continue
        distance = float(face.distToShape(diagnostic.Shape)[0])
        if distance > 1e-6:
            continue
        common = face.common(diagnostic.Shape)
        candidates.append(
            {
                "face": f"Face{index}",
                "centroid_mm": vector_tuple(face.CenterOfMass),
                "area_mm2": round(float(face.Area), 9),
                "diagnostic_common_area_mm2": round(float(common.Area), 9),
                "diagnostic_common_length_mm": round(float(common.Length), 9),
                "distance_to_diagnostic_mm": round(distance, 12),
                "bounds": bbox_dict(face),
            }
        )

    candidates.sort(
        key=lambda item: (
            item["diagnostic_common_area_mm2"],
            item["diagnostic_common_length_mm"],
        ),
        reverse=True,
    )
    return {
        "source_object": definition["source"],
        "diagnostic_object": definition["diagnostic"],
        "source_face_count": len(source.Shape.Faces),
        "source_volume_mm3": round(float(source.Shape.Volume), 9),
        "diagnostic_bounds": bbox_dict(diagnostic.Shape),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main() -> None:
    document = App.openDocument(str(REVIEW_PATH))
    try:
        report = {
            "status": "READ_ONLY__NO_GEOMETRY_CHANGE",
            "review_file": str(REVIEW_PATH.relative_to(PACKAGE_ROOT)),
            "targets": {
                key: audit_target(document, key, definition)
                for key, definition in TARGETS.items()
            },
        }
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__":
    main()
