#!/usr/bin/env python3
"""Focused contract/tooling tests for the bilateral V3 eye print release."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/print-release/bilateral-eye-carrier-corner-clearance-v3-release-v1"
CONTRACT_PATH = TOOL_DIR / "contract.json"
EXPORTER_PATH = TOOL_DIR / "export_release.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("eye_v3_print_release", EXPORTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import release exporter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BilateralEyeV3PrintReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.exporter = load_exporter()

    def test_contract_is_explicit_print_release(self) -> None:
        self.assertEqual(
            self.contract["schema_version"],
            "cat-head-bilateral-eye-corner-clearance-print-release-v1",
        )
        self.assertEqual(
            self.contract["authority"],
            "PRINT_RELEASE__USER_APPROVED__STL_AND_FCSTD_ONLY",
        )
        self.assertTrue(self.contract["user_approval"]["mirror_authorized"])
        self.assertTrue(self.contract["user_approval"]["stl_export_authorized"])

    def test_mirror_datum_is_exact_x0(self) -> None:
        mirror = self.contract["mirror"]
        self.assertEqual(mirror["plane"], "YZ")
        self.assertEqual(mirror["equation"], "X=0")
        self.assertEqual(mirror["coordinate_rule"], "(-x,y,z)")

    def test_mirrored_bounds_helper(self) -> None:
        self.assertEqual(
            self.exporter.expected_mirrored_bounds([2.0, 3.0, 4.0, 7.0, 11.0, 13.0]),
            [-7.0, 3.0, 4.0, -2.0, 11.0, 13.0],
        )

    def test_coordinate_error_helper(self) -> None:
        self.assertAlmostEqual(
            self.exporter.maximum_coordinate_error([0.0, 2.0, 4.0], [0.0, 2.000001, 4.0]),
            0.000001,
        )

    def test_output_is_fresh_versioned_subdirectory(self) -> None:
        directory = self.contract["outputs"]["directory"]
        self.assertIn("FINAL_PRINT_SET/01-eye-modules/v3-corner-repair-release-v1", directory)
        self.assertNotIn("/left/source", directory)
        self.assertNotIn("/right/source", directory)

    def test_six_stl_names_are_unique_and_no_gcode_or_3mf(self) -> None:
        names = []
        for side in ("right", "left"):
            outputs = self.contract["outputs"][side]
            names.extend(outputs[key] for key in ("carrier_stl", "lens_stl", "rear_plate_stl"))
            self.assertTrue(outputs["fcstd"].endswith(".FCStd"))
        self.assertEqual(len(names), 6)
        self.assertEqual(len(set(names)), 6)
        self.assertTrue(all(name.endswith(".stl") for name in names))
        self.assertTrue(all(not name.lower().endswith((".3mf", ".gcode")) for name in names))

    def test_failed_v1_carrier_is_not_an_output(self) -> None:
        serialized = json.dumps(self.contract["outputs"], sort_keys=True)
        self.assertNotIn("RIGHT_EYE_CARRIER_WITH_MANUAL_BOTTOM_FLANGE_V1.stl", serialized)
        self.assertNotIn("LEFT_EYE_CARRIER_WITH_MIRRORED_MANUAL_BOTTOM_FLANGE_V1.stl", serialized)

    def test_all_hash_pins_are_resolved_and_exact(self) -> None:
        for namespace in ("inputs", "tooling"):
            for item in self.contract[namespace].values():
                self.assertNotIn("__PIN", item["sha256"])
                base = ROOT if item.get("root") == "repository" else (
                    ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1"
                )
                path = base / item["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(self.exporter.sha256(path), item["sha256"])

    def test_automatic_mesh_repair_is_prohibited(self) -> None:
        self.assertFalse(self.contract["mesh"]["automatic_repair_allowed"])
        self.assertTrue(self.contract["gates"]["gcode_and_3mf_prohibited"])


if __name__ == "__main__":
    unittest.main()
