"""Regression checks for the Gate 9 V11 under-ear insert redesign."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-under-ear-insert-antiflap-v11-summary.json"
)


class Gate9UnderEarInsertAntiflapV11SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_shared_interface_and_insert_clearances_are_locked(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )
        self.assertEqual(
            self.summary["metal_handoff_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
        )
        dimensions = self.summary["insert_dimensions"]
        self.assertEqual(dimensions["visible_thickness_mm"], 1.5)
        self.assertEqual(dimensions["deep_body_perimeter_clearance_mm"], 0.8)
        self.assertEqual(dimensions["visible_cap_perimeter_clearance_mm"], 0.15)
        self.assertEqual(dimensions["final_shell_local_relief_clearance_mm"], 0.6)

    def test_body_retainers_use_captive_m2_5_round_and_slot_pairs(self):
        hardware = self.summary["body_retention_hardware"]
        self.assertEqual(hardware["fastener_nominal"], "M2.5")
        self.assertEqual(hardware["fastener_count_per_insert"], 2)
        self.assertEqual(hardware["m2_5_socket_cap_screw_length_mm"], 10.0)
        self.assertEqual(hardware["tab_thickness_mm"], 5.0)
        self.assertEqual(hardware["washer_outer_diameter_mm"], 5.0)
        self.assertEqual(hardware["m2_5_nyloc_height_mm"], 3.8)
        for side, interface in self.summary["side_interfaces"].items():
            with self.subTest(side=side):
                retainers = interface["body_retainers"]
                self.assertEqual(
                    [retainer["station"] for retainer in retainers],
                    ["round", "slot"],
                )
                self.assertEqual(
                    [retainer["nominal_opening_mm"] for retainer in retainers],
                    [[2.8], [2.8, 4.0]],
                )
                for retainer in retainers:
                    self.assertGreaterEqual(
                        retainer["insert_root_pad_intersection_mm3"], 10.0
                    )
                    self.assertGreaterEqual(
                        retainer["insert_tab_root_intersection_mm3"], 20.0
                    )
                    self.assertGreaterEqual(
                        retainer["upper_tab_root_intersection_mm3"], 20.0
                    )

    def test_outer_anti_flap_ties_are_separate_non_primary_load_paths(self):
        hardware = self.summary["anti_flap_hardware"]
        self.assertEqual(hardware["fastener_nominal"], "M2.5")
        self.assertEqual(hardware["fastener_count_per_ear"], 1)
        self.assertEqual(hardware["m2_5_socket_cap_screw_length_mm"], 14.0)
        self.assertEqual(hardware["lug_thickness_mm"], 6.0)
        self.assertFalse(hardware["primary_load_path"])
        for side, interface in self.summary["side_interfaces"].items():
            tie = interface["outer_anti_flap"]
            with self.subTest(side=side):
                self.assertGreaterEqual(
                    tie["nearest_primary_m3_center_distance_mm"], 60.0
                )
                self.assertGreaterEqual(
                    tie["insert_root_pad_intersection_mm3"], 10.0
                )
                self.assertGreaterEqual(
                    tie["insert_lug_root_intersection_mm3"], 20.0
                )
                self.assertGreaterEqual(
                    tie["ear_tab_root_intersection_mm3"], 20.0
                )
                self.assertFalse(tie["primary_load_path"])

    def test_all_seven_parts_are_closed_and_all_seated_pairs_clear(self):
        self.assertEqual(
            set(self.summary["topology"]),
            {
                "left_upper_head",
                "right_upper_head",
                "left_ear",
                "right_ear",
                "rear_bezel",
                "left_under_ear_insert",
                "right_under_ear_insert",
            },
        )
        for part, topology in self.summary["topology"].items():
            with self.subTest(part=part):
                self.assertEqual(topology["components"], 1)
                self.assertEqual(topology["boundary_edges"], 0)
                self.assertEqual(topology["nonmanifold_edges"], 0)
        self.assertTrue(
            all(
                volume == 0.0
                for volume in self.summary[
                    "seated_positive_overlap_mm3"
                ].values()
            )
        )

    def test_service_paths_tools_hardware_and_complete_metal_are_clear(self):
        self.assertEqual(len(self.summary["service_paths"]), 4)
        for path in self.summary["service_paths"].values():
            self.assertTrue(path["all_samples_clear"])
            self.assertEqual(
                [sample["offset_mm"] for sample in path["samples"]],
                [0.0, 2.5, 5.0, 10.0, 20.0, 40.0, 80.0],
            )
        for group_name in (
            "tool_to_non_owned_printed_part_collisions",
            "hardware_to_non_owned_printed_part_collisions",
        ):
            for owner in self.summary[group_name].values():
                self.assertTrue(
                    all(record["clear"] for record in owner.values())
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

    def test_external_skin_mirror_and_real_mixed_material_slice_pass(self):
        for part, record in self.summary["exterior_preservation"].items():
            with self.subTest(part=part):
                self.assertTrue(record["external_skin_bounds_safe"])
                self.assertLessEqual(record["hidden_ear_root_extension_mm"], 6.0)
        self.assertLessEqual(
            self.summary["mirror_fastener_center_max_error_mm"], 0.05
        )
        slicer = self.summary["prusa_mk4_asa_petg_validation"]
        self.assertTrue(slicer["all_parts_pass_xy_margin_and_z_height"])
        totals = slicer["exact_seven_part_set"]
        self.assertEqual(totals["part_count"], 7)
        self.assertTrue(totals["all_parts_pass_margin"])
        self.assertGreaterEqual(totals["minimum_xy_margin_mm"], 10.0)
        self.assertEqual(
            {record["material"] for record in slicer["selected_parts"].values()},
            {"ASA", "PETG"},
        )

    def test_complete_digital_candidate_passes_but_physical_checks_remain(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))
        holds = " ".join(self.summary["remaining_release_holds"]).lower()
        for term in ("a-07", "a-12", "physical", "m2.5", "m3"):
            self.assertIn(term, holds)


if __name__ == "__main__":
    unittest.main()
