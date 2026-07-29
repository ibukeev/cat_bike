"""Regression checks for the Gate 9 V5 complementary service-part review."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-complementary-service-parts-v5-summary.json"
)


class Gate9ComplementaryServicePartsV5SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_interface_and_complementary_construction_are_explicit(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.3",
        )
        parts = self.summary["complementary_parts"]
        self.assertIn("direct boundary", parts["construction_rule"])
        self.assertEqual(parts["bottom_keel"]["scupper_count"], 2)
        self.assertEqual(
            parts["bottom_keel"]["analytic_open_area_mm2_each"],
            80.0,
        )

    def test_all_six_modified_meshes_are_closed_single_components(self):
        self.assertEqual(len(self.summary["topology"]), 6)
        for part, result in self.summary["topology"].items():
            with self.subTest(part=part):
                self.assertEqual(result["components"], 1)
                self.assertEqual(result["boundary_edges"], 0)
                self.assertEqual(result["nonmanifold_edges"], 0)
                self.assertGreater(result["volume_mm3"], 0.0)

    def test_service_interface_and_removal_order_are_preserved(self):
        service = self.summary["service_interface"]
        self.assertEqual(service["fastener_count"], 8)
        self.assertEqual(service["wire_rib_count"], 2)
        self.assertEqual(service["wire_channel_clear_width_mm"], 13.0)
        self.assertEqual(service["rear_wire_exit_width_mm"], 20.0)
        self.assertEqual(
            service["removal_order"],
            ["bottom keel downward", "rear bezel rearward"],
        )

    def test_digital_gate_passes_with_required_clearance(self):
        validation = self.summary["digital_validation"]
        self.assertTrue(all(validation.values()))
        architecture = self.summary["architecture"]
        self.assertGreaterEqual(
            architecture["minimum_measured_sampled_seated_clearance_mm"],
            architecture["minimum_required_sampled_seated_clearance_mm"],
        )
        self.assertEqual(
            min(self.summary["seated_clearances_mm"].values()),
            architecture["minimum_measured_sampled_seated_clearance_mm"],
        )

    def test_frozen_metal_has_no_contact(self):
        clearances = self.summary[
            "rear_bezel_to_frozen_metal_clearances_mm"
        ]
        for item, clearance in clearances.items():
            with self.subTest(item=item):
                self.assertGreater(clearance, 0.0)

    def test_slice_gate_passes_but_is_not_production_authority(self):
        slicer = self.summary["slicer"]
        self.assertEqual(slicer["part_count"], 8)
        self.assertTrue(slicer["all_parts_pass_margin"])
        self.assertGreaterEqual(
            slicer["minimum_post_brim_xy_margin_mm"],
            slicer["minimum_required_post_brim_xy_margin_mm"],
        )
        self.assertAlmostEqual(slicer["total_filament_g"], 706.95)
        self.assertAlmostEqual(slicer["total_support_g"], 363.126)
        self.assertEqual(
            self.summary["status"],
            "review_candidate_passed_service_parts_not_production_release",
        )

    def test_every_remaining_blocker_is_explicit(self):
        blockers = " ".join(self.summary["production_blockers"]).lower()
        for term in (
            "socket",
            "portal",
            "ear",
            "eye",
            "panel",
            "seam",
            "coupon",
        ):
            with self.subTest(term=term):
                self.assertIn(term, blockers)


if __name__ == "__main__":
    unittest.main()
