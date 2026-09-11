#!/usr/bin/env python3
"""Restore one deleted opaque under-mouth sector into a fresh user-edit copy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_root() -> Path:
    for parent in (HERE, *HERE.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("repository root not found")


def find_object(document, key: str):
    found = document.getObject(key)
    if found is not None:
        return found
    matches = [obj for obj in document.Objects if obj.Name == key or obj.Label == key]
    if len(matches) != 1:
        raise RuntimeError(f"expected one object {key!r}, found {len(matches)}")
    return matches[0]


def bbox_record(shape) -> list[float]:
    box = shape.BoundBox
    return [
        float(box.XMin),
        float(box.YMin),
        float(box.ZMin),
        float(box.XMax),
        float(box.YMax),
        float(box.ZMax),
    ]


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    root = repo_root()
    source_path = root / contract["source"]["path"]
    target_path = root / contract["target"]["path"]
    output_path = root / contract["output"]["path"]

    for record, path in (
        (contract["source"], source_path),
        (contract["target"], target_path),
    ):
        actual = sha256(path)
        if actual != record["sha256"]:
            raise RuntimeError(
                f"input hash mismatch for {path}: expected {record['sha256']}, got {actual}"
            )
    if output_path.exists():
        raise RuntimeError(f"fresh output already exists: {output_path}")

    import FreeCAD as App  # type: ignore

    source_doc = App.openDocument(str(source_path))
    target_doc = App.openDocument(str(target_path))
    try:
        source_obj = find_object(source_doc, contract["source"]["object_name"])
        if target_doc.getObject(contract["source"]["object_name"]) is not None:
            raise RuntimeError("source sector is already present in the user-edit document")
        if target_doc.getObject(contract["output"]["object_name"]) is not None:
            raise RuntimeError("recovery object name is already present")

        source_shape = source_obj.Shape.copy()
        source_placement = source_obj.Placement
        source_volume = float(source_shape.Volume)
        source_bbox = bbox_record(source_shape)
        if source_shape.isNull() or source_volume <= 0.0:
            raise RuntimeError("recovery source is not a positive-volume shape")

        recovered = target_doc.addObject(
            "Part::Feature", contract["output"]["object_name"]
        )
        recovered.Label = contract["output"]["label"]
        recovered.Shape = source_shape
        recovered.Placement = source_placement
        recovered.addProperty("App::PropertyString", "Authority", "Recovery")
        recovered.Authority = contract["authority"]
        recovered.addProperty("App::PropertyString", "SourceObject", "Recovery")
        recovered.SourceObject = contract["source"]["object_name"]
        recovered.addProperty("App::PropertyString", "SourceFCStdSHA256", "Recovery")
        recovered.SourceFCStdSHA256 = contract["source"]["sha256"]

        target_doc.recompute()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        target_doc.saveAs(str(output_path))
    finally:
        App.closeDocument(source_doc.Name)
        App.closeDocument(target_doc.Name)

    if sha256(target_path) != contract["target"]["sha256"]:
        raise RuntimeError("original user-edit file changed unexpectedly")

    check_doc = App.openDocument(str(output_path))
    try:
        check_obj = find_object(check_doc, contract["output"]["object_name"])
        check_shape = check_obj.Shape
        check_volume = float(check_shape.Volume)
        check_bbox = bbox_record(check_shape)
        if check_shape.isNull() or not check_shape.isValid():
            raise RuntimeError("recovered output shape is null or invalid")
        if abs(check_volume - source_volume) > 1.0e-6:
            raise RuntimeError("recovered sector volume does not match its source")
        if max(abs(a - b) for a, b in zip(check_bbox, source_bbox)) > 1.0e-6:
            raise RuntimeError("recovered sector bounds do not match its source")
    finally:
        App.closeDocument(check_doc.Name)

    print(
        json.dumps(
            {
                "status": "PASS__UNDER_MOUTH_SECTOR_RECOVERED",
                "restored_object": contract["source"]["object_name"],
                "output_object": contract["output"]["object_name"],
                "output_path": str(output_path),
                "output_sha256": sha256(output_path),
                "restored_volume_mm3": source_volume,
                "restored_bbox_mm": source_bbox,
                "original_user_edit_unchanged": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
