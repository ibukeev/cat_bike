"""Regression checks for the Gate 9 V8 body-seam review."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-body-seam-clearance-v8-summary.json"
)


class Gate9BodySeamClearanceV8SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(
            SUMMARY_PATH.read_text(encoding="utf-8")
        )

    def test_shared_interface_datums_remain_locked(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )
        self.assertEqual(
            self.summary["metal_handoff_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
        )

    def test_eight_seated_ownership_reliefs_are_complementary(self):
        records = self.summary["seam_ownership_and_relief"]
        self.assertEqual(len(records), 8)
        self.assertEqual(
            {record["operation"] for record in records},
            {
                "rear_bezel_to_left_upper",
                "rear_bezel_to_right_upper",
                "rear_bezel_to_left_lower",
                "rear_bezel_to_right_lower",
                "left_upper_to_left_lower",
                "right_upper_to_right_lower",
                "upper_center",
                "lower_center",
            },
        )
        for record in records:
            with self.subTest(operation=record["operation"]):
                self.assertEqual(record["clearance_mm"], 0.6)
                self.assertGreater(record["overlap_before_mm3"], 0.0)
                self.assertEqual(record["overlap_after_mm3"], 0.0)
                self.assertEqual(
                    record["topology_after"]["components"],
                    1,
                )
                self.assertEqual(
                    record["topology_after"]["boundary_edges"],
                    0,
                )
                self.assertEqual(
                    record["topology_after"]["nonmanifold_edges"],
                    0,
                )
                self.assertLessEqual(
                    record["cleanup"][
                        "removed_component_volume_mm3"
                    ],
                    5.0,
                )

    def test_rear_bezel_service_sweep_is_clear(self):
        path = self.summary["assembly_paths"]["rear_bezel_outward"]
        self.assertTrue(path["all_samples_clear"])
        self.assertEqual(
            [sample["offset_mm"] for sample in path["samples"]],
            [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 40.0, 80.0],
        )
        cuts = self.summary["rear_bezel_service_sweep_relief"]
        active = [
            record for record in cuts if record["overlap_before_mm3"] > 0.0
        ]
        self.assertEqual(len(active), 6)
        self.assertTrue(
            all(record["overlap_after_mm3"] == 0.0 for record in active)
        )

    def test_complete_topology_and_seated_matrix_pass(self):
        topology = self.summary["topology"]
        self.assertEqual(len(topology), 8)
        for part, record in topology.items():
            with self.subTest(part=part):
                self.assertEqual(record["components"], 1)
                self.assertEqual(record["boundary_edges"], 0)
                self.assertEqual(record["nonmanifold_edges"], 0)
                self.assertGreater(record["volume_mm3"], 0.0)
        matrix = self.summary["seated_pair_matrix"]
        self.assertEqual(len(matrix), 28)
        self.assertTrue(
            all(
                record["positive_overlap_volume_mm3"] == 0.0
                for record in matrix.values()
            )
        )

    def test_all_five_assembly_paths_pass(self):
        paths = self.summary["assembly_paths"]
        self.assertEqual(len(paths), 5)
        for name, record in paths.items():
            with self.subTest(path=name):
                self.assertTrue(record["all_samples_clear"])
                self.assertTrue(
                    all(sample["clear"] for sample in record["samples"])
                )

    def test_exterior_and_mirror_landings_are_preserved(self):
        preservation = self.summary[
            "subtractive_exterior_preservation"
        ]
        self.assertEqual(len(preservation), 4)
        for part, record in preservation.items():
            with self.subTest(part=part):
                self.assertTrue(record["subtractive_only"])
                self.assertTrue(record["bounds_inside_v7_extents"])
                self.assertGreater(record["removed_volume_mm3"], 0.0)
                self.assertFalse(
                    record[
                        "coplanar_boolean_residual_is_acceptance_authority"
                    ]
                )
        landing = self.summary["mirror_panel_landing_validation"]
        self.assertEqual(landing["triangle_overlap_pair_count"], 0)
        self.assertEqual(landing["perimeter_inset_mm"], 0.9)
        self.assertEqual(landing["corner_chamfer_mm"], 0.8)

    def test_real_prusa_mk4_generic_asa_slice_passes(self):
        slicer = self.summary["prusa_mk4_generic_asa_validation"]
        self.assertTrue(
            slicer["all_parts_pass_xy_margin_and_z_height"]
        )
        self.assertGreaterEqual(
            slicer["observed_minimum_xy_margin_mm"],
            slicer["required_minimum_xy_margin_mm"],
        )
        totals = slicer["exact_eight_part_set"]
        self.assertEqual(totals["part_count"], 8)
        self.assertTrue(totals["all_parts_pass_margin"])
        self.assertAlmostEqual(totals["minimum_xy_margin_mm"], 11.492)
        self.assertAlmostEqual(totals["estimated_filament_g"], 709.69)
        self.assertAlmostEqual(
            totals["estimated_support_filament_g"],
            290.728,
        )

    def test_all_digital_flags_pass_but_final_asa_stays_held(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))
        blockers = " ".join(
            self.summary["remaining_production_blockers"]
        ).lower()
        for term in (
            "physical",
            "seam",
            "ear",
            "eye",
            "glow",
            "lamp",
            "steering",
            "asa",
        ):
            with self.subTest(term=term):
                self.assertIn(term, blockers)


if __name__ == "__main__":
    unittest.main()
