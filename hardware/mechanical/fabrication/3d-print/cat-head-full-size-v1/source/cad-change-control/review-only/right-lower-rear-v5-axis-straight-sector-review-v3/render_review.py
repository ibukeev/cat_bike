#!/usr/bin/env python3
"""Render fixed read-only views of the completed V3 review FCStd."""

from __future__ import annotations

import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
REVIEW_DIR = (
    PROJECT_ROOT
    / "output/70-freecad-pilots/review-only/"
    "right-lower-rear-v5-axis-straight-sector-review-v3"
)
FCSTD = REVIEW_DIR / "RIGHT_LOWER_REAR_V5_AXIS_STRAIGHT_SECTOR_REVIEW_ONLY_V3.FCStd"
EXPECTED_SHA256 = "9489e2f5a114467bc1212680ea15e083178780207bb4d2c2218a4dda6f7b4255"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if sha256(FCSTD) != EXPECTED_SHA256:
        raise RuntimeError("V3 review FCStd hash mismatch")
    outputs = [
        REVIEW_DIR / "03-component-001-closeup.png",
        REVIEW_DIR / "04-transferred-sector-isolated.png",
    ]
    if any(path.exists() for path in outputs):
        raise RuntimeError("fixed review view already exists")

    import FreeCAD as App  # type: ignore
    import FreeCADGui as Gui  # type: ignore

    Gui.showMainWindow()
    Gui.updateGui()
    document = App.openDocument(str(FCSTD))
    try:
        Gui.activeDocument().activeView().setAnimationEnabled(False)
        retained = document.getObject("RET_001")
        cassette = document.getObject("CAS_001")
        transfer = document.getObject("PROPOSED_FACE30_SECTOR_TRANSFER")
        old_marker = document.getObject("REFERENCE_V2_DIAGONAL_SEAM")
        new_marker = document.getObject("PROPOSED_V3_AXIS_STRAIGHT_EDGE")
        if any(
            item is None
            for item in (retained, cassette, transfer, old_marker, new_marker)
        ):
            raise RuntimeError("V3 review highlight objects are missing")
        for obj in document.Objects:
            if getattr(obj, "ViewObject", None) is not None:
                obj.ViewObject.Visibility = False
        retained.ViewObject.Visibility = True
        cassette.ViewObject.Visibility = True
        transfer.ViewObject.Visibility = True
        old_marker.ViewObject.Visibility = True
        new_marker.ViewObject.Visibility = True
        retained.ViewObject.ShapeColor = (0.25, 0.65, 0.95)
        retained.ViewObject.Transparency = 70
        cassette.ViewObject.ShapeColor = (1.0, 0.48, 0.12)
        cassette.ViewObject.Transparency = 40
        transfer.ViewObject.ShapeColor = (0.2, 1.0, 0.25)
        transfer.ViewObject.Transparency = 0

        view = Gui.activeDocument().activeView()
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(str(outputs[0]), 1400, 1000, "Current")

        retained.ViewObject.Visibility = False
        cassette.ViewObject.Visibility = False
        transfer.ViewObject.Visibility = True
        old_marker.ViewObject.Visibility = True
        new_marker.ViewObject.Visibility = True
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(str(outputs[1]), 1400, 1000, "Current")
    finally:
        App.closeDocument(document.Name)
    if any(not path.exists() for path in outputs):
        raise RuntimeError("one or more fixed views were not created")
    print("\n".join(str(path) for path in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
