"""Regression checks for the V9 M3 insert and bridge coupon."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "v9-m3-insert-bridge-coupon-summary.json"
)


class V9M3InsertBridgeCouponSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(
            SUMMARY_PATH.read_text(encoding="utf-8")
        )

    def test_three_ordered_pilot_sizes_are_present(self):
        stations = self.summary["pilot_station_map_left_to_right"]
        self.assertEqual(
            [station["position"] for station in stations],
            ["left", "center", "right"],
        )
        self.assertEqual(
            [station["pilot_diameter_mm"] for station in stations],
            [4.0, 4.1, 4.2],
        )
        self.assertTrue(
            all(station["pilot_residual_mm3"] == 0.0 for station in stations)
        )

    def test_coupon_replicates_v9_structural_dimensions(self):
        dimensions = self.summary["dimensions"]
        self.assertEqual(dimensions["base_thickness_mm"], 1.8)
        self.assertEqual(dimensions["boss_diameter_mm"], 12.0)
        self.assertEqual(dimensions["boss_total_depth_mm"], 12.0)
        self.assertEqual(dimensions["boss_base_overlap_mm"], 1.3)
        self.assertEqual(dimensions["pilot_depth_mm"], 5.8)
        self.assertEqual(dimensions["bridge_end_diameter_mm"], 8.0)
        self.assertEqual(dimensions["bridge_thickness_mm"], 3.5)
        self.assertEqual(dimensions["bridge_clearance_diameter_mm"], 3.6)
        self.assertEqual(dimensions["m3_socket_cap_screw_length_mm"], 8.0)
        self.assertEqual(
            self.summary["derived_dimensions"][
                "m3x8_available_thread_engagement_mm"
            ],
            4.5,
        )

    def test_both_parts_are_single_closed_manifolds(self):
        self.assertEqual(set(self.summary["topology"]), {"base", "bridge"})
        for part, record in self.summary["topology"].items():
            with self.subTest(part=part):
                self.assertEqual(record["components"], 1)
                self.assertEqual(record["boundary_edges"], 0)
                self.assertEqual(record["nonmanifold_edges"], 0)
                self.assertGreater(record["volume_mm3"], 0.0)

    def test_real_flat_asa_slice_is_small_and_support_free(self):
        slicer = self.summary["prusa_mk4_generic_asa_validation"]
        self.assertTrue(slicer["all_parts_pass_xy_margin_and_z_height"])
        totals = slicer["exact_two_part_set"]
        self.assertEqual(totals["part_count"], 2)
        self.assertTrue(totals["all_parts_pass_margin"])
        self.assertEqual(totals["estimated_support_filament_g"], 0.0)
        self.assertEqual(totals["estimated_support_volume_cm3"], 0.0)
        self.assertLess(totals["estimated_filament_g"], 6.0)
        self.assertLess(totals["estimated_print_time_seconds"], 1800)
        self.assertTrue(
            all(
                record["rotation_xyz_degrees"] == [0.0, 0.0, 0.0]
                for record in slicer["selected_parts"].values()
            )
        )

    def test_digital_candidate_passes_but_physical_selection_is_pending(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))
        self.assertTrue(self.summary["physical_test_required"])
        self.assertFalse(self.summary["physical_test_completed"])
        self.assertIsNone(self.summary["selected_pilot_diameter_mm"])


if __name__ == "__main__":
    unittest.main()
