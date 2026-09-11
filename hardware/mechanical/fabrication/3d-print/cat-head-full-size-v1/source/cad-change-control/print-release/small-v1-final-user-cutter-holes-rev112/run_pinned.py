#!/usr/bin/env python3
"""Hash-pinned one-shot authorization wrapper for the Rev112 printable release."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


ROOT = _find_repo_root()
FILES = {
    "core": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-final-user-cutter-holes-rev112/core.py",
        "ef478d56bb0cfa93cb5cf6e0f3fabbf6721076e34b349b62eca4654737eccdd0",
    ),
    "preflight": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-final-user-cutter-holes-rev112/preflight.py",
        "5017317206e6b2c2729c0beab81896143a61a0bb81d0d443b69fd450ba164bb3",
    ),
    "generator": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-final-user-cutter-holes-rev112/generate.py",
        "d4a2bfc383eb5bb75e1d45600ae88f5742c7f9c8e7b09cd0908ae1132bf18ce5",
    ),
    "contract": (
        "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
        "small-v1-final-user-cutter-holes-rev112.json",
        "31bf0290188bbb70e48abc4661ae20745e8eb16ac551d86e3c67723aae523160",
    ),
    "passed_preflight_report": (
        "hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/validation/small-v1-final-user-cutter-holes-rev112/"
        "preflight-report.json",
        "d3832cfab2d84b1dc5816d0f3e9277c2c30641e4fbfa7839e62cf84e691ed680",
    ),
    "approved_runtime_manifest": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/v2/freecad-runtime-1.1.3-r20260725-occt-7.8.1.json",
        "0051cd65fc00f3270aadecd992ad7f571a327646054399e9ee17f39ae48c4bf1",
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for label, (relative, expected) in FILES.items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"Rev112 pinned input changed: {label}")

    report = json.loads(
        (ROOT / FILES["passed_preflight_report"][0]).read_text(encoding="utf-8")
    )
    if report.get("status") != "CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS":
        raise RuntimeError("Rev112 pinned preflight report is not a pass")
    if report.get("contract_sha256") != FILES["contract"][1]:
        raise RuntimeError("Rev112 preflight contract hash disagrees with the pinned contract")
    source_hash = report.get("source_sha256_after")
    contract = json.loads((ROOT / FILES["contract"][0]).read_text(encoding="utf-8"))
    if source_hash != contract["source"]["sha256"]:
        raise RuntimeError("Rev112 preflight source hash disagrees with the pinned source")

    runtime = json.loads(
        (ROOT / FILES["approved_runtime_manifest"][0]).read_text(encoding="utf-8")
    )
    if runtime["approval"]["status"] != "approved":
        raise RuntimeError("Rev112 FreeCAD runtime manifest is not approved")
    if runtime["freecad"]["release"] != "1.1.3" or runtime["occt"]["version"] != "7.8.1":
        raise RuntimeError("Rev112 FreeCAD/OCCT runtime version changed")

    generator = ROOT / FILES["generator"][0]
    runpy.run_path(str(generator), run_name="__main__")


if __name__ == "__main__":
    main()
