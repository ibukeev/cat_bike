#!/usr/bin/env python3
"""Render fixed opaque front/rear review views without saving the FCStd."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "contract.json"


def repository_root() -> Path:
    for parent in (HERE, *HERE.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def set_review_visibility(
    document: Any, visible_groups: list[str], patch_name: str
) -> None:
    for obj in document.Objects:
        view = getattr(obj, "ViewObject", None)
        if view is not None:
            view.Visibility = False
    for group_name in visible_groups:
        group = document.getObject(group_name)
        if group is None:
            raise RuntimeError(f"missing declared review group: {group_name}")
        for obj in group.Group:
            view = getattr(obj, "ViewObject", None)
            if view is not None:
                view.Visibility = True
                view.Transparency = 0
    patch = document.getObject(patch_name)
    if patch is None:
        raise RuntimeError(f"missing patch object: {patch_name}")
    patch.ViewObject.Visibility = True
    patch.ViewObject.Transparency = 0
    patch.ViewObject.ShapeColor = (1.0, 0.45, 0.0)
    patch.ViewObject.LineColor = (0.25, 0.05, 0.0)


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    root = repository_root()
    output_dir = root / contract["output"]["directory"]
    fcstd = output_dir / contract["output"]["fcstd"]
    manifest_path = output_dir / contract["output"]["manifest"]
    front = output_dir / contract["output"]["front"]
    rear = output_dir / contract["output"]["rear"]
    if not fcstd.is_file() or not manifest_path.is_file():
        raise RuntimeError("candidate FCStd or manifest is missing")
    if front.exists() or rear.exists():
        raise RuntimeError("one or more review images already exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_file(fcstd) != manifest["output_sha256"]:
        raise RuntimeError("candidate FCStd hash differs from the manifest")

    import FreeCAD as App  # type: ignore
    import FreeCADGui as Gui  # type: ignore

    Gui.showMainWindow()
    Gui.updateGui()
    document = App.openDocument(str(fcstd))
    try:
        view = Gui.activeDocument().activeView()
        view.setAnimationEnabled(False)
        set_review_visibility(
            document,
            contract["review_visible_groups"],
            contract["patch"]["object_name"],
        )
        view.viewFront()
        view.fitAll()
        Gui.updateGui()
        view.saveImage(str(front), 1600, 1200, "White")

        set_review_visibility(
            document,
            contract["review_visible_groups"],
            contract["patch"]["object_name"],
        )
        view.viewRear()
        view.fitAll()
        Gui.updateGui()
        view.saveImage(str(rear), 1600, 1200, "White")
    finally:
        App.closeDocument(document.Name)

    for image_path in (front, rear):
        if not image_path.is_file() or image_path.stat().st_size <= 0:
            raise RuntimeError(f"review image was not created: {image_path}")
    if sha256_file(fcstd) != manifest["output_sha256"]:
        raise RuntimeError("rendering unexpectedly changed the candidate FCStd")

    manifest["review_artifacts"] = {
        "front": {
            "path": str(front.relative_to(root)),
            "sha256": sha256_file(front),
            "view": "front",
            "patch_color": "orange",
            "context_transparency_percent": 0,
        },
        "rear": {
            "path": str(rear.relative_to(root)),
            "sha256": sha256_file(rear),
            "view": "rear",
            "patch_color": "orange",
            "context_transparency_percent": 0,
        },
    }
    manifest["review_artifacts_complete"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest["review_artifacts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
