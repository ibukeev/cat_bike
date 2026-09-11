#!/usr/bin/env python3
"""Hash-pinned one-shot wrapper for the Rev113 merged-mouth candidate."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path


def find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


ROOT = find_repo_root()
FILES = {
    "core": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-merged-mouth-pane-rev113/core.py",
        "fca55cf6e4f703c33b314946a645ef8fddb7e15856b82a9415eaa31962734d00",
    ),
    "preflight": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-merged-mouth-pane-rev113/preflight.py",
        "001e1c10e214b627d9131facc4c081d053b1562123648e70c134a4c14ad05dcc",
    ),
    "generator": (
        "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
        "cad-change-control/print-release/small-v1-merged-mouth-pane-rev113/generate.py",
        "5aabaaf9e61ca735c619ac74eb7e53ee041cdfa385c024459332e6db66ec34ed",
    ),
    "contract": (
        "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
        "small-v1-merged-mouth-pane-rev113.json",
        "845edfe340744cae74309fbe05f1373741f2b2bd6a9976d9c608841f53933130",
    ),
    "passed_preflight_report": (
        "hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/validation/small-v1-merged-mouth-pane-rev113/"
        "preflight-report.json",
        "aab72aa5d5f18bbc46474b090cc958f5b178875b67e22016a48d89a9f7607c90",
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
            raise RuntimeError(f"Rev113 pinned input changed: {label}")

    report = json.loads((ROOT / FILES["passed_preflight_report"][0]).read_text(encoding="utf-8"))
    if report.get("status") != "CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS":
        raise RuntimeError("Rev113 pinned preflight report is not a pass")
    if report.get("contract_sha256") != FILES["contract"][1]:
        raise RuntimeError("Rev113 preflight contract hash disagrees with the pin")
    contract = json.loads((ROOT / FILES["contract"][0]).read_text(encoding="utf-8"))
    if report.get("source_sha256_after") != contract["source"]["sha256"]:
        raise RuntimeError("Rev113 preflight source hash disagrees with the pinned Rev112 source")

    runtime = json.loads((ROOT / FILES["approved_runtime_manifest"][0]).read_text(encoding="utf-8"))
    if runtime["approval"]["status"] != "approved":
        raise RuntimeError("Rev113 FreeCAD runtime manifest is not approved")
    if runtime["freecad"]["release"] != "1.1.3" or runtime["occt"]["version"] != "7.8.1":
        raise RuntimeError("Rev113 FreeCAD/OCCT runtime version changed")

    runpy.run_path(str(ROOT / FILES["generator"][0]), run_name="__main__")


if __name__ == "__main__":
    main()
