#!/usr/bin/env python3
"""Resolve aluminum mount V0.4 review inputs from the shared interface.

This preflight preserves the V0.2 generated review pack and performs no
Blender generation, metal drawing export, cutting, or drilling release.
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
COORDINATOR_PATH = PACKAGE_ROOT / "config/frame-fixed-mount-v04-interface.json"
INTERFACE_MODULE_DIR = REPO_ROOT / "hardware/mechanical/interfaces"
if str(INTERFACE_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(INTERFACE_MODULE_DIR))

from cat_head_interface import load_interface, metal_head_interface_contract  # noqa: E402


def repo_path(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as error:
        raise ValueError(f"Configured path escapes repository: {relative}") from error
    return path


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_dict(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_dict(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def load_resolved_config() -> tuple[dict[str, Any], dict[str, Any]]:
    coordinator = json.loads(COORDINATOR_PATH.read_text(encoding="utf-8"))
    base_path = repo_path(coordinator["base_config_path"])
    interface_path = repo_path(coordinator["shared_interface"]["path"])
    final_path = repo_path(coordinator["final_config_path"])
    interface, interface_report = load_interface(
        interface_path,
        coordinator["shared_interface"]["required_revision"],
    )
    final_config = json.loads(final_path.read_text(encoding="utf-8"))
    resolved = copy.deepcopy(json.loads(base_path.read_text(encoding="utf-8")))
    merge_dict(resolved["head_interface"], metal_head_interface_contract(interface))
    resolved["shared_interface"] = {
        "path": coordinator["shared_interface"]["path"],
        "revision": interface["interface_revision"],
        "status": interface["status"],
    }
    resolved["generation_enabled"] = bool(coordinator["generation_enabled"])
    resolved["generation_holds"] = list(coordinator["generation_holds"])

    adapter = resolved["load_path"]["front_adapter"]
    plate = resolved["head_interface"]["aluminum_backplate"]
    adapter_pattern_matches = (
        float(adapter["backplate_hole_diameter_mm"])
        == float(plate["bike_adapter_hole_diameter_mm"])
        and float(adapter["backplate_hole_x_mm"])
        == float(plate["bike_adapter_hole_x_mm"])
        and float(adapter["backplate_hole_v_mm"])
        == float(plate["bike_adapter_hole_v_mm"])
    )
    pitch_matches = abs(
        float(resolved["pose"]["yoke_pitch_relative_to_boss_plane_deg"])
        - float(interface["rear_interface_plane"]["mating_pitch_relative_to_estimated_boss_plane_deg"])
    ) <= 1e-6
    checks = {
        "adapter_hole_pattern_matches_shared_backplate": adapter_pattern_matches,
        "rear_plane_mating_pitch_matches_shared_interface": pitch_matches,
        "measured_profile_is_19_by_19_by_2_mm": (
            resolved["head_interface"]["internal_rails"]["outer_width_mm"] == 19.0
            and resolved["head_interface"]["internal_rails"]["outer_height_mm"] == 19.0
            and resolved["head_interface"]["internal_rails"]["wall_thickness_mm"] == 2.0
        ),
        "final_config_uses_v04_interface": (
            final_config["required_interface_revision"]
            == interface["interface_revision"]
        ),
        "final_rail_cut_length_is_149p672_mm": (
            float(final_config["rails"]["finished_cut_length_mm"])
            == float(
                interface["rail_system"]["profile"][
                    "finished_cut_length_mm"
                ]
            )
            == 149.672
        ),
        "final_backplate_has_six_shell_and_six_shoe_holes": (
            len(
                final_config["backplate"]["shell_attachment"][
                    "local_x_v_centers_mm"
                ]
            ) == 6
            and 2 * len(
                final_config["backplate"]["shoe_attachment"][
                    "right_local_x_v_centers_mm"
                ]
            ) == 6
        ),
        "final_shoes_use_37_mm_solid_plug_insertion": (
            float(
                final_config["lower_shoe"]["solid_plug"][
                    "insertion_inside_tube_mm"
                ]
            ) == 37.0
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"Metal V0.4 interface preflight failed: {failed}")
    report = {
        "status": "PASS - METAL V0.4 SHARED INTERFACE PREFLIGHT",
        "consumer_id": coordinator["consumer_id"],
        "interface_revision": interface["interface_revision"],
        "interface_contract_status": interface_report["status"],
        "checks": checks,
        "base_config": {
            "path": coordinator["base_config_path"],
            "sha256": file_sha256(base_path),
        },
        "shared_interface": {
            "path": coordinator["shared_interface"]["path"],
            "sha256": file_sha256(interface_path),
        },
        "final_config": {
            "path": coordinator["final_config_path"],
            "sha256": file_sha256(final_path),
        },
        "resolved_head_interface": metal_head_interface_contract(interface),
        "ready_for_geometry_generation": bool(coordinator["generation_enabled"]),
        "generation_holds": coordinator["generation_holds"],
    }
    return resolved, report


def main() -> None:
    _, report = load_resolved_config()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
