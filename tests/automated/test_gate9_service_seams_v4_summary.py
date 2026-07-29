"""Regression checks for the rejected Gate 9 V4 service-seam review."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-service-seams-v4-summary.json"
)


class Gate9ServiceSeamsV4SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_interface_and_service_hardware_are_explicit(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.3",
        )
        service = self.summary["service_interface"]
        self.assertEqual(service["fastener_count"], 8)
        self.assertEqual(service["keel_hole_diameter_mm"], 3.6)
        self.assertEqual(service["wire_channel_clear_width_mm"], 13.0)
        self.assertEqual(service["rear_wire_exit_width_mm"], 20.0)

    def test_all_six_modified_meshes_are_closed_single_components(self):
        self.assertEqual(len(self.summary["topology"]), 6)
        for part, result in self.summary["topology"].items():
            with self.subTest(part=part):
                self.assertEqual(result["components"], 1)
                self.assertEqual(result["boundary_edges"], 0)
                self.assertEqual(result["nonmanifold_edges"], 0)
                self.assertGreater(result["volume_mm3"], 0.0)

    def test_rejected_digital_gate_cannot_regress_to_a_false_pass(self):
        validation = self.summary["digital_validation"]
        self.assertFalse(validation["digital_v4_service_seam_candidate_pass"])
        self.assertFalse(
            validation[
                "all_preexisting_keel_and_cassette_body_collisions_removed"
            ]
        )
        self.assertFalse(
            validation[
                "all_modified_seam_parts_clear_frozen_metal_envelopes"
            ]
        )
        self.assertGreater(
            self.summary["blocking_collisions"][
                "seated_keel_to_lower_shell_triangle_pairs"
            ]["left_lower_face"],
            0,
        )
        self.assertGreater(
            self.summary["blocking_collisions"][
                "rear_cassette_to_frozen_metal_triangle_pairs"
            ]["backplate"],
            0,
        )

    def test_slice_feasibility_is_recorded_but_not_production_authority(self):
        slicer = self.summary["slicer"]
        self.assertEqual(slicer["part_count"], 8)
        self.assertTrue(slicer["all_parts_pass_margin"])
        self.assertAlmostEqual(
            slicer["minimum_post_brim_xy_margin_mm"], 13.162
        )
        self.assertAlmostEqual(slicer["total_filament_g"], 694.62)
        self.assertAlmostEqual(slicer["total_support_g"], 347.062)
        self.assertEqual(
            self.summary["status"],
            "review_candidate_rejected_not_production_release",
        )

    def test_every_remaining_blocker_is_explicit(self):
        blockers = " ".join(self.summary["production_blockers"]).lower()
        for term in (
            "keel",
            "cassette",
            "scupper",
            "socket",
            "ear",
            "eye",
            "panel",
            "coupon",
        ):
            with self.subTest(term=term):
                self.assertIn(term, blockers)


if __name__ == "__main__":
    unittest.main()
