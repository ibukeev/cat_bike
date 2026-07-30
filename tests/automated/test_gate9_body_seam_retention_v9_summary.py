"""Regression checks for the Gate 9 V9 removable body-seam retention."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-body-seam-retention-v9-summary.json"
)


class Gate9BodySeamRetentionV9SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(
            SUMMARY_PATH.read_text(encoding="utf-8")
        )

    def test_shared_interface_and_hardware_are_locked(self):
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )
        self.assertEqual(
            self.summary["metal_handoff_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
        )
        hardware = self.summary["hardware"]
        self.assertEqual(hardware["m3_screw_total"], 10)
        self.assertEqual(hardware["m3_heat_set_insert_total"], 10)
        self.assertEqual(
            hardware["m3_socket_cap_screw_length_mm"],
            8.0,
        )
        self.assertEqual(hardware["insert_pilot_diameter_mm"], 4.1)
        self.assertEqual(hardware["insert_pilot_depth_mm"], 5.8)

    def test_five_removable_bridges_use_ten_broad_supported_pads(self):
        modules = self.summary["selected_modules"]
        self.assertEqual(len(modules), 5)
        self.assertEqual(
            {module["module"] for module in modules},
            {
                "left_lower_face__left_upper_head_02",
                "left_lower_face__right_lower_face_05",
                "left_upper_head__right_upper_head_02",
                "left_upper_head__right_upper_head_03",
                "right_lower_face__right_upper_head_02",
            },
        )
        pads = [pad for module in modules for pad in module["pads"]]
        bearings = [
            bearing
            for module in modules
            for bearing in module["bridge_bearing"]
        ]
        self.assertEqual(len(pads), 10)
        self.assertEqual(len(bearings), 10)
        for pad in pads:
            with self.subTest(section=pad["section"]):
                self.assertGreaterEqual(
                    pad["root_intersection_mm3"],
                    20.0,
                )
                self.assertEqual(pad["pilot_residual_mm3"], 0.0)
                self.assertGreaterEqual(
                    pad["insert_bearing_support_ratio"],
                    0.95,
                )
        self.assertTrue(
            all(
                bearing["support_ratio"] >= 0.95
                for bearing in bearings
            )
        )

    def test_legacy_sites_without_final_v8_roots_are_rejected(self):
        rejected = self.summary["rejected_legacy_modules"]
        self.assertEqual(len(rejected), 9)
        for record in rejected:
            with self.subTest(module=record["module"]):
                self.assertIn("no broad root", record["reason"])
                self.assertTrue(
                    any(
                        value == 0.0
                        for value in record[
                            "root_intersection_mm3"
                        ].values()
                    )
                )

    def test_only_lower_center_receives_local_internal_relief(self):
        records = self.summary["local_bridge_clearance_relief"]
        self.assertEqual(len(records), 2)
        self.assertEqual(
            {record["section"] for record in records},
            {"left_lower_face", "right_lower_face"},
        )
        self.assertEqual(
            {record["bridge"] for record in records},
            {
                "body_seam_bridge__left_lower_face__right_lower_face_05"
            },
        )
        for record in records:
            with self.subTest(section=record["section"]):
                self.assertLessEqual(
                    record["overlap_before_mm3"],
                    12.0,
                )
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

    def test_all_thirteen_parts_are_manifold_and_collision_free(self):
        topology = {
            **self.summary["topology"],
            **self.summary["bridge_topology"],
        }
        self.assertEqual(len(topology), 13)
        for part, record in topology.items():
            with self.subTest(part=part):
                self.assertEqual(record["components"], 1)
                self.assertEqual(record["boundary_edges"], 0)
                self.assertEqual(record["nonmanifold_edges"], 0)
                self.assertGreater(record["volume_mm3"], 0.0)
        for matrix_name in (
            "body_pair_matrix_before_local_relief",
            "body_pair_matrix_after_local_relief",
            "seated_production_pair_matrix",
            "bridge_body_pair_matrix",
            "bridge_bridge_pair_matrix",
        ):
            matrix = self.summary[matrix_name]
            self.assertTrue(
                all(
                    record["positive_overlap_volume_mm3"] == 0.0
                    for record in matrix.values()
                ),
                matrix_name,
            )

    def test_body_bridge_tool_and_metal_paths_are_clear(self):
        for group_name in (
            "assembly_paths",
            "bridge_inward_assembly_paths",
        ):
            group = self.summary[group_name]
            self.assertEqual(len(group), 5)
            self.assertTrue(
                all(record["all_samples_clear"] for record in group.values())
            )
        for group_name in (
            "tool_to_printed_part_collisions",
            "v9_to_m2_metal_collisions",
            "bridge_to_m2_metal_collisions",
            "tool_to_m2_metal_collisions",
        ):
            group = self.summary[group_name]
            self.assertTrue(
                all(record["clear"] for record in group.values()),
                group_name,
            )

    def test_clean_exterior_and_mirror_landings_are_preserved(self):
        dimensions = self.summary["dimensions"]
        self.assertEqual(
            dimensions["minimum_analytic_pad_exterior_recess_mm"],
            0.5,
        )
        for part, record in self.summary[
            "exterior_preservation"
        ].items():
            with self.subTest(part=part):
                self.assertTrue(record["bounds_inside_v8_extents"])
                self.assertGreaterEqual(
                    record[
                        "minimum_analytic_added_pad_exterior_recess_mm"
                    ],
                    0.5,
                )
        landing = self.summary["mirror_panel_landing_validation"]
        self.assertEqual(
            landing["pad_triangle_overlap_pair_count"],
            0,
        )
        self.assertEqual(
            landing["relief_cutter_triangle_overlap_pair_count"],
            0,
        )

    def test_real_prusa_mk4_generic_asa_slice_passes(self):
        slicer = self.summary["prusa_mk4_generic_asa_validation"]
        self.assertTrue(
            slicer["all_parts_pass_xy_margin_and_z_height"]
        )
        self.assertGreaterEqual(
            slicer["observed_minimum_xy_margin_mm"],
            slicer["required_minimum_xy_margin_mm"],
        )
        totals = slicer["exact_thirteen_part_set"]
        self.assertEqual(totals["part_count"], 13)
        self.assertTrue(totals["all_parts_pass_margin"])
        self.assertAlmostEqual(totals["minimum_xy_margin_mm"], 11.61)
        self.assertAlmostEqual(totals["estimated_filament_g"], 734.77)
        self.assertAlmostEqual(
            totals["estimated_support_filament_g"],
            304.728,
        )
        self.assertEqual(
            slicer["selected_parts"]["left_lower_face"][
                "rotation_xyz_degrees"
            ],
            [111.0, 30.0, 30.0],
        )

    def test_all_digital_flags_pass_but_final_asa_stays_held(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))
        blockers = " ".join(
            self.summary["remaining_production_blockers"]
        ).lower()
        for term in (
            "coupon",
            "physical",
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
