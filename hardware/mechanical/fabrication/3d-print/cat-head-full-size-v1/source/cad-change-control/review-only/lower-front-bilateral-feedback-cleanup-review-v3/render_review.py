#!/usr/bin/env python3
"""Render six fixed views of the V2 bilateral feedback-cleanup review."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
OUTPUT_DIR = (PROJECT_ROOT / CONTRACT["outputs"]["directory"]).resolve()
FCSTD = OUTPUT_DIR / CONTRACT["outputs"]["fcstd"]
OUTPUTS = [OUTPUT_DIR / name for name in CONTRACT["outputs"]["views"]]


def set_visibility(document, visible_groups: tuple[str, ...]) -> None:
    for obj in document.Objects:
        view = getattr(obj, "ViewObject", None)
        if view is not None:
            view.Visibility = False
    for group_name in visible_groups:
        group = document.getObject(group_name)
        if group is None:
            raise RuntimeError(f"missing V2 review group: {group_name}")
        for obj in group.Group:
            view = getattr(obj, "ViewObject", None)
            if view is not None:
                view.Visibility = True


def save(view, path: Path, orientation: str) -> None:
    getattr(view, orientation)()
    view.fitAll()
    view.saveImage(str(path), 1500, 1050, "Current")


def main() -> int:
    if not FCSTD.exists():
        raise RuntimeError(f"V2 review FCStd is missing: {FCSTD}")
    if any(path.exists() for path in OUTPUTS):
        raise RuntimeError("one or more V2 fixed views already exist")

    import FreeCAD as App  # type: ignore
    import FreeCADGui as Gui  # type: ignore

    Gui.showMainWindow()
    Gui.updateGui()
    document = App.openDocument(str(FCSTD))
    try:
        view = Gui.activeDocument().activeView()
        view.setAnimationEnabled(False)
        assembled = (
            "OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS",
            "OPAQUE_RIGHT_UPPER_OWNERS", "OPAQUE_LEFT_UPPER_OWNERS",
            "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES",
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS",
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
        )
        set_visibility(document, assembled)
        save(view, OUTPUTS[0], "viewFront")
        set_visibility(document, assembled)
        save(view, OUTPUTS[1], "viewRear")

        set_visibility(document, (
            "OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS",
            "REFERENCE_REMOVED_CLEANUP_GEOMETRY",
        ))
        save(view, OUTPUTS[2], "viewAxonometric")

        set_visibility(document, (
            "OPAQUE_RIGHT_LOWER_OWNERS",
            "REFERENCE_USER_MANUAL_FLANGE_SOURCES",
            "REFERENCE_HIDDEN_MANUAL_FLANGE_ROOTS",
            "REFERENCE_REMOVED_CLEANUP_GEOMETRY",
        ))
        save(view, OUTPUTS[3], "viewAxonometric")

        set_visibility(document, (
            "OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS",
            "REFERENCE_REMOVED_CLEANUP_GEOMETRY",
        ))
        save(view, OUTPUTS[4], "viewFront")

        set_visibility(document, (
            "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES",
            "REFERENCE_OUTBOARD_LEDGE_HARDWARE",
            "REFERENCE_OUTBOARD_LEDGE_CUTTERS",
        ))
        save(view, OUTPUTS[5], "viewRear")
    finally:
        App.closeDocument(document.Name)

    if any(not path.exists() for path in OUTPUTS):
        raise RuntimeError("one or more V2 fixed views were not created")
    print("\n".join(str(path) for path in OUTPUTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
