"""Regression checks for the Gate 9 V10 primary ear interfaces."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-ear-primary-interface-v10-summary.json"
)


class Gate9EarPrimaryInterfaceV10SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(
            SUMMARY_PATH.read_text(encoding="utf-8")
        )

    def test_shared_interface_and_two_path_hardware_are_locked(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )
        self.assertEqual(
            self.summary["metal_handoff_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
        )
        hardware = self.summary["hardware"]
        self.assertEqual(hardware["fastener_nominal"], "M3")
        self.assertEqual(hardware["fastener_count_per_ear"], 2)
        self.assertEqual(hardware["round_clearance_diameter_mm"], 3.4)
        self.assertEqual(hardware["slot_width_mm"], 3.4)
        self.assertEqual(hardware["slot_overall_length_mm"], 5.0)
        self.assertEqual(hardware["m3_socket_cap_screw_length_mm"], 20.0)

    def test_each_ear_has_one_round_and_one_slot_station(self):
        for side, interface in self.summary["side_interfaces"].items():
            with self.subTest(side=side):
                screws = interface["screws"]
                self.assertEqual(
                    [screw["station"] for screw in screws],
                    ["round", "slot"],
                )
                self.assertEqual(
                    [screw["nominal_opening_mm"] for screw in screws],
                    [[3.4], [3.4, 5.0]],
                )
                self.assertEqual(
                    interface["candidate"]["internal_m3_screws"],
                    2,
                )

    def test_legacy_four_bore_saddles_are_encapsulated(self):
        records = self.summary["legacy_saddle_disposition"]
        self.assertEqual(len(records), 4)
        for record in records:
            with self.subTest(
                side=record["side"],
                section=record["section"],
            ):
                self.assertEqual(record["legacy_fastener_count"], 4)
                disposition = record["disposition"].lower()
                self.assertIn("encapsulated", disposition)
                self.assertIn("middle legacy bores are filled", disposition)
                self.assertIn("round plus slot", disposition)

    def test_primary_flange_roots_are_broad_and_recessed(self):
        dimensions = self.summary["dimensions"]
        self.assertEqual(dimensions["root_web_length_mm"], 8.0)
        self.assertEqual(dimensions["root_web_thickness_mm"], 4.5)
        self.assertEqual(dimensions["minimum_tab_exterior_recess_mm"], 5.0)
        for side, interface in self.summary["side_interfaces"].items():
            candidate = interface["candidate"]
            with self.subTest(side=side):
                self.assertGreaterEqual(
                    candidate["minimum_tab_exterior_recess_mm"],
                    5.0,
                )
                self.assertGreaterEqual(
                    candidate["minimum_root_web_exterior_recess_mm"],
                    0.35,
                )
                for section in candidate["sections"]:
                    self.assertGreaterEqual(
                        candidate[f"{section}_root_intersection_mm3"],
                        35.0,
                    )

    def test_complementary_relief_leaves_manifold_zero_overlap_pairs(self):
        relief = self.summary["localized_complementary_relief"]
        self.assertEqual({record["side"] for record in relief}, {"left", "right"})
        for record in relief:
            with self.subTest(side=record["side"]):
                self.assertEqual(record["clearance_mm"], 0.5)
                self.assertGreater(record["removed_ear_volume_mm3"], 0.0)
                final_cleanup = record["residual_component_cleanup"][-1]
                self.assertLessEqual(final_cleanup["overlap_after_mm3"], 0.001)
                topology = record["topology_after"]
                self.assertEqual(topology["components"], 1)
                self.assertEqual(topology["boundary_edges"], 0)
                self.assertEqual(topology["nonmanifold_edges"], 0)
        self.assertEqual(
            self.summary["seated_ear_head_positive_overlap_mm3"],
            {"left": 0.0, "right": 0.0},
        )

    def test_parts_paths_tools_hardware_and_metal_are_clear(self):
        topology = self.summary["topology"]
        self.assertEqual(
            set(topology),
            {
                "left_upper_head",
                "right_upper_head",
                "left_ear",
                "right_ear",
            },
        )
        for part, record in topology.items():
            with self.subTest(part=part):
                self.assertEqual(record["components"], 1)
                self.assertEqual(record["boundary_edges"], 0)
                self.assertEqual(record["nonmanifold_edges"], 0)
        paths = self.summary["ear_outward_assembly_paths"]
        self.assertEqual(set(paths), {"left_ear", "right_ear"})
        for record in paths.values():
            self.assertTrue(record["all_samples_clear"])
            self.assertEqual(
                [sample["offset_mm"] for sample in record["samples"]],
                [0.0, 2.5, 5.0, 10.0, 20.0, 40.0, 80.0],
            )
        for group_name in (
            "tool_to_non_owned_printed_part_collisions",
            "hardware_to_non_owned_printed_part_collisions",
        ):
            for record in self.summary[group_name].values():
                self.assertTrue(
                    all(collision["clear"] for collision in record.values())
                )
        for group_name in (
            "updated_parts_to_m2_metal_collisions",
            "tool_to_m2_metal_collisions",
        ):
            self.assertTrue(
                all(
                    record["clear"]
                    for record in self.summary[group_name].values()
                )
            )

    def test_exterior_mirror_and_real_asa_slice_pass(self):
        self.assertTrue(
            all(
                record["bounds_inside_source_extents"]
                for record in self.summary["exterior_preservation"].values()
            )
        )
        self.assertLessEqual(
            self.summary["mirror_fastener_center_max_error_mm"],
            0.05,
        )
        slicer = self.summary["prusa_mk4_generic_asa_validation"]
        self.assertTrue(slicer["all_parts_pass_xy_margin_and_z_height"])
        totals = slicer["exact_four_part_set"]
        self.assertEqual(totals["part_count"], 4)
        self.assertTrue(totals["all_parts_pass_margin"])
        self.assertAlmostEqual(totals["minimum_xy_margin_mm"], 28.484)
        self.assertAlmostEqual(totals["estimated_filament_g"], 340.09)
        self.assertAlmostEqual(
            totals["estimated_support_filament_g"],
            140.561,
        )
        self.assertAlmostEqual(
            totals["estimated_support_volume_cm3"],
            131.369,
        )

    def test_primary_candidate_passes_but_anti_flap_work_remains(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))
        blockers = " ".join(self.summary["remaining_ear_blockers"]).lower()
        for term in ("under-ear", "m2.5", "anti-flap", "physical"):
            self.assertIn(term, blockers)


if __name__ == "__main__":
    unittest.main()
