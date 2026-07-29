"""Regression checks for the Gate 9 combined aperture-frame/keel V3 review."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-aperture-frame-and-keel-v3-summary.json"
)


class Gate9ApertureFrameAndKeelV3SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_full_scale_frozen_interface_and_partition(self):
        architecture = self.summary["architecture"]
        self.assertEqual(
            self.summary["interface_revision"], "CAT-HEAD-SHELL-ALUMINUM-V0.3"
        )
        self.assertEqual(architecture["full_scale_width_mm"], 330.0)
        self.assertEqual(architecture["rear_cassette_offset_mm"], -70.0)
        self.assertEqual(architecture["lower_rail_x_mm"], [-40.0, 40.0])
        self.assertEqual(architecture["keel_source_face_ids"], [109, 110])
        self.assertEqual(architecture["keel_cassette_seam_owner"], "rear_cassette")
        self.assertGreaterEqual(architecture["keel_cassette_clearance_mm"], 0.6)

    def test_every_v3_mesh_is_one_closed_manifold_component(self):
        topology = self.summary["topology"]
        self.assertEqual(
            set(topology),
            {
                "left_upper_head",
                "right_upper_head",
                "left_lower_face",
                "right_lower_face",
                "bottom_keel",
            },
        )
        for part_name, result in topology.items():
            with self.subTest(part=part_name):
                self.assertEqual(result["components"], 1)
                self.assertEqual(result["boundary_edges"], 0)
                self.assertEqual(result["nonmanifold_edges"], 0)
                self.assertGreater(result["volume_mm3"], 0.0)

    def test_frame_recess_and_coarse_keepouts_pass(self):
        frame = self.summary["aperture_frame"]
        self.assertGreaterEqual(frame["verified_minimum_exterior_recess_mm"], 0.3)

        for check_name, passed in self.summary["coarse_keepout_checks"].items():
            with self.subTest(check=check_name):
                self.assertTrue(passed)

    def test_all_eight_parts_have_real_slice_results_and_pass_margin(self):
        slicer = self.summary["slicer"]
        parts = slicer["parts"]
        expected_parts = {
            "left_upper_head",
            "right_upper_head",
            "left_lower_face",
            "right_lower_face",
            "left_ear",
            "right_ear",
            "rear_cassette",
            "bottom_keel",
        }
        self.assertEqual(set(parts), expected_parts)
        self.assertEqual(slicer["part_count"], 8)
        self.assertAlmostEqual(slicer["minimum_post_brim_xy_margin_mm"], 12.887)
        self.assertAlmostEqual(slicer["total_filament_g"], 600.27)
        self.assertAlmostEqual(slicer["total_support_g"], 285.272)
        self.assertEqual(slicer["total_time_seconds"], 195335)

        for part_name, result in parts.items():
            with self.subTest(part=part_name):
                self.assertTrue(result["passed"])
                self.assertGreaterEqual(result["post_brim_xy_margin_mm"], 10.0)
                self.assertGreater(result["filament_g"], 0.0)
                self.assertGreaterEqual(result["support_g"], 0.0)

    def test_remaining_feedback_is_explicitly_held(self):
        holds = " ".join(self.summary["production_holds"]).lower()
        for expected_term in (
            "eye",
            "glow",
            "ear",
            "socket",
            "seam",
            "coupon",
        ):
            with self.subTest(term=expected_term):
                self.assertIn(expected_term, holds)


if __name__ == "__main__":
    unittest.main()
