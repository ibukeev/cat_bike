#!/usr/bin/env python3
"""Render five fixed views of the modular lower-front review FCStd."""

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
            raise RuntimeError(f"missing review group: {group_name}")
        for obj in group.Group:
            if getattr(obj, "ViewObject", None) is not None:
                obj.ViewObject.Visibility = True


def main() -> int:
    if not FCSTD.exists():
        raise RuntimeError(f"review FCStd is missing: {FCSTD}")
    if any(path.exists() for path in OUTPUTS):
        raise RuntimeError("one or more fixed review views already exist")

    import FreeCAD as App  # type: ignore
    import FreeCADGui as Gui  # type: ignore

    Gui.showMainWindow()
    Gui.updateGui()
    document = App.openDocument(str(FCSTD))
    try:
        view = Gui.activeDocument().activeView()
        view.setAnimationEnabled(False)
        assembled = (
            "OPAQUE_RIGHT_LOWER_OWNERS",
            "OPAQUE_LEFT_LOWER_OWNERS",
            "OPAQUE_RIGHT_UPPER_OWNERS",
            "OPAQUE_LEFT_UPPER_OWNERS",
            "SEPARATE_V5_LOWER_REAR_LEDGES",
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS",
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
        )

        set_visibility(document, assembled)
        view.viewFront()
        view.fitAll()
        view.saveImage(str(OUTPUTS[0]), 1400, 1000, "Current")

        set_visibility(document, assembled)
        view.viewRear()
        view.fitAll()
        view.saveImage(str(OUTPUTS[1]), 1400, 1000, "Current")

        set_visibility(document, (
            "OPAQUE_RIGHT_LOWER_OWNERS",
            "OPAQUE_LEFT_LOWER_OWNERS",
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
        ))
        for group_name in ("OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS"):
            for obj in document.getObject(group_name).Group:
                obj.ViewObject.Transparency = 72
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(str(OUTPUTS[2]), 1400, 1000, "Current")

        set_visibility(document, (
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
            "REFERENCE_MOUTH_FASTENERS_AND_CUTTERS",
        ))
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(str(OUTPUTS[3]), 1400, 1000, "Current")

        set_visibility(document, (
            "OPAQUE_RIGHT_LOWER_OWNERS",
            "OPAQUE_LEFT_LOWER_OWNERS",
            "OPAQUE_RIGHT_UPPER_OWNERS",
            "OPAQUE_LEFT_UPPER_OWNERS",
            "SEPARATE_V5_LOWER_REAR_LEDGES",
        ))
        view.viewAxonometric()
        view.fitAll()
        view.saveImage(str(OUTPUTS[4]), 1400, 1000, "Current")
    finally:
        App.closeDocument(document.Name)

    if any(not path.exists() for path in OUTPUTS):
        raise RuntimeError("one or more fixed review views were not created")
    print("\n".join(str(path) for path in OUTPUTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
