#!/usr/bin/env python3
"""Static contract gates for the isolated Rev113 merged-mouth candidate."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-merged-mouth-pane-rev113.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Rev113MergedMouthContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_source_is_hash_pinned_rev112(self) -> None:
        source = self.contract["source"]
        path = ROOT / source["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(sha256(path), source["sha256"])

    def test_scope_is_exactly_two_mouth_panes(self) -> None:
        approval = self.contract["approval"]
        self.assertTrue(approval["merge_exact_two_rev112_mouth_panes_authorized"])
        self.assertFalse(approval["change_head_authorized"])
        self.assertFalse(approval["change_eye_panes_authorized"])
        self.assertFalse(approval["change_stops_cutters_or_zip_tie_slots_authorized"])
        self.assertFalse(approval["change_mouth_outer_surfaces_authorized"])
        self.assertFalse(approval["unrelated_geometry_authorized"])

    def test_candidate_is_not_promoted_or_sliced(self) -> None:
        approval = self.contract["approval"]
        self.assertFalse(approval["promote_final_release_authorized"])
        self.assertFalse(approval["slicer_profile_3mf_or_gcode_authorized"])
        self.assertIn("NOT_FINAL_RELEASE", self.contract["review_state"])

    def test_only_pinned_center_faces_define_bridge(self) -> None:
        operation = self.contract["operation"]
        self.assertEqual(
            operation["method"],
            "RULED_SOLID_LOFT_BETWEEN_PINNED_CENTER_SEAM_FACES_THEN_FUSE",
        )
        self.assertEqual(operation["first_anchor"]["face"], "Face1")
        self.assertEqual(operation["second_anchor"]["face"], "Face1")
        self.assertAlmostEqual(operation["measured_minimum_seam_gap_mm"], 0.5949922084458888)

    def test_panel_contract_stays_two_mm_and_hole_free(self) -> None:
        operation = self.contract["operation"]
        self.assertEqual(operation["expected_petg_thickness_mm"], 2.0)
        self.assertEqual(operation["expected_hole_count"], 0)
        self.assertEqual(operation["expected_final_print_part_count"], 4)
        self.assertEqual(operation["expected_merged_mouth_solid_count"], 1)

    def test_outputs_are_new_rev113_paths(self) -> None:
        for key, relative in self.contract["output"].items():
            if key == "preflight_report":
                continue
            self.assertIn("rev113", relative.lower())
        self.assertNotEqual(
            self.contract["source"]["path"], self.contract["output"]["candidate_fcstd"]
        )

    def test_frozen_shape_fingerprints_are_complete(self) -> None:
        fingerprints = self.contract["source"]["expected_brep_sha256"]
        self.assertEqual(
            set(fingerprints),
            {"head", "right_eye", "left_eye", "mouth_tri005", "mouth_tri006"},
        )
        for digest in fingerprints.values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
