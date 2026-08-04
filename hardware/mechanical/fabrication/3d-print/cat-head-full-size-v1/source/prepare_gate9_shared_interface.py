#!/usr/bin/env python3
"""Resolve the Gate 9 shell config against shared interface V0.3.

This is deliberately a pure-Python preflight. It does not import Blender,
regenerate Gate 8, or write production outputs.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
COORDINATOR_PATH = PACKAGE_ROOT / "config/gate9-coordinated-asa-candidate-v1.json"
INTERFACE_MODULE_DIR = REPO_ROOT / "hardware/mechanical/interfaces"
if str(INTERFACE_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(INTERFACE_MODULE_DIR))

from cat_head_interface import gate8_portal_contract, load_interface  # noqa: E402


def repo_path(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as error:
        raise ValueError(f"Configured path escapes repository: {relative}") from error
    return path


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_resolved_config() -> tuple[dict[str, Any], dict[str, Any]]:
    coordinator = json.loads(COORDINATOR_PATH.read_text(encoding="utf-8"))
    base_path = repo_path(coordinator["base_config_path"])
    interface_path = repo_path(coordinator["shared_interface"]["path"])
    interface, interface_report = load_interface(
        interface_path,
        coordinator["shared_interface"]["required_revision"],
    )
    resolved = copy.deepcopy(json.loads(base_path.read_text(encoding="utf-8")))
    resolved["shared_interface"] = {
        "path": coordinator["shared_interface"]["path"],
        "revision": interface["interface_revision"],
        "status": interface["status"],
    }
    resolved["aluminum_upright_portals"].update(gate8_portal_contract(interface))
    resolved["generation_holds"] = list(coordinator["generation_holds"])
    resolved["generation_enabled"] = bool(coordinator["generation_enabled"])
    report = {
        "status": "PASS - GATE 9 SHARED INTERFACE PREFLIGHT",
        "consumer_id": coordinator["consumer_id"],
        "interface_revision": interface["interface_revision"],
        "interface_contract_status": interface_report["status"],
        "base_config": {
            "path": coordinator["base_config_path"],
            "sha256": file_sha256(base_path),
        },
        "shared_interface": {
            "path": coordinator["shared_interface"]["path"],
            "sha256": file_sha256(interface_path),
        },
        "resolved_portal_contract": gate8_portal_contract(interface),
        "output_namespace": coordinator["output_namespace"],
        "ready_for_architecture_comparison": True,
        "ready_for_geometry_generation": bool(coordinator["generation_enabled"]),
        "generation_holds": coordinator["generation_holds"],
    }
    return resolved, report


def main() -> None:
    _, report = load_resolved_config()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
