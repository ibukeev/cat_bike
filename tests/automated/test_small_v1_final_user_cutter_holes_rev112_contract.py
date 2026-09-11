#!/usr/bin/env python3
"""Deterministic scope and source-preservation tests for the Rev112 release tooling."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-final-user-cutter-holes-rev112.json"
)
TOOLING_DIRECTORY = REPO_ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
    "cad-change-control/print-release/small-v1-final-user-cutter-holes-rev112"
)


class Rev112ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_authority_is_exact_and_source_preserving(self):
        approval = self.contract["approval"]
        self.assertTrue(approval["subtract_all_four_user_cutters_authorized"])
        self.assertTrue(approval["create_new_final_head_body_authorized"])
        self.assertTrue(approval["export_head_and_four_translucent_panels_authorized"])
        self.assertFalse(approval["overwrite_source_fcstd_authorized"])
        self.assertFalse(approval["change_translucent_panels_authorized"])
        self.assertFalse(approval["change_existing_zip_tie_slots_authorized"])
        self.assertFalse(approval["slicer_profile_or_gcode_authorized"])
        self.assertFalse(approval["unrelated_geometry_authorized"])

    def test_source_fcstd_is_hash_pinned(self):
        source = self.contract["source"]
        path = REPO_ROOT / source["path"]
        self.assertTrue(path.is_file(), path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])

    def test_exact_cumulative_four_cutter_contract(self):
        source = self.contract["source"]
        self.assertEqual(source["cutter_body_object"], "Body")
        self.assertEqual(source["cutter_body_label"], "Cutters")
        self.assertEqual(source["cumulative_tip_object"], "Pad003")
        self.assertEqual(source["expected_cutter_count"], 4)
        self.assertEqual(source["expected_cutter_compound_solid_count"], 4)
        self.assertEqual(source["individual_cutter_shape_property"], "AddSubShape")
        self.assertEqual(
            [item["object"] for item in source["individual_cutters"]],
            ["Pad", "Pad001", "Pad002", "Pad003"],
        )
        self.assertEqual(
            [item["label"] for item in source["individual_cutters"]],
            ["Cutter1", "Cutter2", "Cutter3", "Cutter4"],
        )
        self.assertTrue(all(item["expected_length_mm"] == -10.0 for item in source["individual_cutters"]))
        self.assertEqual(
            self.contract["operation"]["method"],
            "TARGET_MINUS_CUMULATIVE_CUTTER_BODY_ONCE",
        )

    def test_panes_and_zip_tie_corridors_are_protected(self):
        source = self.contract["source"]
        self.assertEqual(len(source["protected_panes"]), 4)
        self.assertEqual(len(source["existing_zip_tie_corridors"]), 2)
        self.assertEqual(self.contract["operation"]["expected_protected_pane_count"], 4)
        self.assertEqual(self.contract["operation"]["expected_zip_tie_through_slot_count"], 2)

    def test_core_performs_one_cumulative_cut_and_never_saves_source(self):
        text = (TOOLING_DIRECTORY / "core.py").read_text(encoding="utf-8")
        self.assertEqual(text.count("final_head = head.cut(cutter_compound)"), 1)
        self.assertIn("individual_cutter_overlaps", text)
        self.assertIn("zip_tie_final_residuals", text)
        self.assertIn("source_hash_after", text)
        self.assertNotIn("source_document.save", text)
        self.assertNotIn("source_document.saveAs", text)

    def test_preflight_has_no_candidate_save_or_export(self):
        text = (TOOLING_DIRECTORY / "preflight.py").read_text(encoding="utf-8")
        self.assertNotIn("saveAs(", text)
        self.assertNotIn("mesh.write(", text)
        self.assertIn('"source_overwritten": False', text)
        self.assertIn('"slicer_project_created_or_changed": False', text)

    def test_one_shot_wrapper_pins_passed_preflight_and_runtime(self):
        text = (TOOLING_DIRECTORY / "run_pinned.py").read_text(encoding="utf-8")
        self.assertIn('"passed_preflight_report"', text)
        self.assertIn('"approved_runtime_manifest"', text)
        self.assertIn('CANDIDATE_READY__NO_OUTPUT_PREFLIGHT_PASS', text)
        self.assertIn('runpy.run_path(str(generator), run_name="__main__")', text)

    def test_outputs_are_one_fcstd_and_five_stls_only(self):
        output = self.contract["output"]
        self.assertTrue(output["candidate_fcstd"].endswith(".FCStd"))
        stl_keys = (
            "head_stl",
            "right_eye_stl",
            "left_eye_stl",
            "mouth_tri005_stl",
            "mouth_tri006_stl",
        )
        self.assertTrue(all(output[key].endswith(".stl") for key in stl_keys))
        serialized = json.dumps(output).lower()
        self.assertNotIn(".3mf", serialized)
        self.assertNotIn(".gcode", serialized)


if __name__ == "__main__":
    unittest.main()
