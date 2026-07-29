#!/usr/bin/env python3
"""Regression tests for the shared cat-head shell/aluminum interface."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INTERFACE_DIR = REPO_ROOT / "hardware/mechanical/interfaces"
if str(INTERFACE_DIR) not in sys.path:
    sys.path.insert(0, str(INTERFACE_DIR))

from cat_head_interface import (  # noqa: E402
    DEFAULT_REVISION,
    default_interface_path,
    validate_interface,
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHELL_PREFLIGHT = load_module(
    "prepare_gate9_shared_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/prepare_gate9_shared_interface.py",
)
METAL_PREFLIGHT = load_module(
    "prepare_frame_fixed_mount_v03_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v03_interface.py",
)


class CatHeadSharedInterfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.interface = json.loads(default_interface_path().read_text(encoding="utf-8"))

    def test_measured_contract_passes(self) -> None:
        report = validate_interface(self.interface)
        self.assertTrue(report["status"].startswith("PASS"))
        self.assertEqual(self.interface["interface_revision"], DEFAULT_REVISION)
        profile = self.interface["rail_system"]["profile"]
        self.assertEqual(
            (
                profile["outside_width_mm"],
                profile["outside_height_mm"],
                profile["wall_thickness_mm"],
                profile["available_stock_length_mm"],
            ),
            (19.0, 19.0, 2.0, 914.4),
        )
        self.assertAlmostEqual(
            report["derived"]["socket_clearance_each_side_mm"], 0.75
        )

    def test_shell_and_metal_consumers_use_identical_revision(self) -> None:
        shell_config, shell_report = SHELL_PREFLIGHT.load_resolved_config()
        metal_config, metal_report = METAL_PREFLIGHT.load_resolved_config()
        self.assertEqual(shell_report["interface_revision"], DEFAULT_REVISION)
        self.assertEqual(metal_report["interface_revision"], DEFAULT_REVISION)
        shell_portal = shell_config["aluminum_upright_portals"]
        metal_rail = metal_config["head_interface"]["internal_rails"]
        self.assertEqual(shell_portal["tube_outer_width_mm"], 19.0)
        self.assertEqual(shell_portal["tube_outer_height_mm"], 19.0)
        self.assertEqual(shell_portal["tube_wall_thickness_mm"], 2.0)
        self.assertEqual(metal_rail["outer_width_mm"], 19.0)
        self.assertEqual(metal_rail["outer_height_mm"], 19.0)
        self.assertEqual(metal_rail["wall_thickness_mm"], 2.0)
        self.assertEqual(
            shell_portal["lower_route_left_mm"],
            metal_rail["left_lower_target_head_mm"],
        )
        self.assertEqual(
            shell_portal["lower_route_right_mm"],
            metal_rail["right_lower_target_head_mm"],
        )

    def test_inconsistent_recorded_inside_dimension_fails(self) -> None:
        invalid = copy.deepcopy(self.interface)
        invalid["rail_system"]["profile"]["derived_inside_width_mm"] = 15.5
        report = validate_interface(invalid)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(
            report["checks"]["inside_dimensions_match_measured_wall"]["pass"]
        )


if __name__ == "__main__":
    unittest.main()
