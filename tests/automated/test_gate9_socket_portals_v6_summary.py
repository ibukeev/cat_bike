"""Regression checks for the Gate 9 V6 socket/portal review."""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review"
    / "gate9-socket-portals-v6-summary.json"
)


class Gate9SocketPortalsV6SummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_frozen_interface_is_exact(self):
        interface = self.summary["frozen_interface"]
        self.assertEqual(
            self.summary["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.4",
        )
        self.assertEqual(interface["tube_outside_mm"], [19.0, 19.0])
        self.assertEqual(interface["socket_opening_mm"], [21.0, 21.0])
        self.assertEqual(interface["nominal_clearance_each_side_mm"], 1.0)
        self.assertEqual(interface["socket_insertion_depth_mm"], 30.0)
        self.assertEqual(interface["rail_reference_length_mm"], 158.172)
        self.assertEqual(
            interface["cross_bolt_angle_from_head_x_deg"],
            5.333,
        )

    def test_portals_are_mirrored_and_have_true_union_roots(self):
        portals = self.summary["portal_construction"]
        self.assertGreaterEqual(
            portals["measured_socket_exterior_recess_mm"],
            portals["minimum_required_socket_exterior_recess_mm"],
        )
        self.assertEqual(portals["socket_outer_width_mm"], 32.5)
        self.assertEqual(portals["socket_wall_mm"], 5.75)
        self.assertEqual(portals["socket_lead_in_depth_mm"], 1.0)
        self.assertEqual(portals["socket_lead_in_mouth_width_mm"], 23.0)
        self.assertEqual(portals["socket_lead_in_slope_deg"], 45.0)
        self.assertGreater(
            portals["left"][
                "pad_to_shell_triangle_overlap_pairs_before_union"
            ],
            0,
        )
        self.assertGreater(
            portals["left"][
                "pad_to_socket_triangle_overlap_pairs_before_union"
            ],
            0,
        )
        self.assertEqual(
            portals["left"]["open_center_mm"][0],
            -portals["right"]["open_center_mm"][0],
        )
        self.assertEqual(
            portals["left"]["bolt_center_mm"][0],
            -portals["right"]["bolt_center_mm"][0],
        )

    def test_all_current_parts_and_coupon_are_closed_single_components(self):
        self.assertEqual(len(self.summary["topology"]), 7)
        for part, result in self.summary["topology"].items():
            with self.subTest(part=part):
                self.assertEqual(result["components"], 1)
                self.assertEqual(result["boundary_edges"], 0)
                self.assertEqual(result["nonmanifold_edges"], 0)
                self.assertGreater(result["volume_mm3"], 0.0)

    def test_rail_insertion_and_hardware_access_are_clear(self):
        rail = self.summary["rail_path_validation"]
        self.assertTrue(rail["left_all_sampled_positions_clear"])
        self.assertTrue(rail["right_all_sampled_positions_clear"])
        self.assertEqual(
            rail["withdrawal_offsets_mm"],
            [0.0, 20.0, 50.0, 100.0, 160.0],
        )
        self.assertGreaterEqual(
            rail["minimum_seated_clearance_to_owner_socket_stop_mm"],
            0.5,
        )
        hardware = self.summary["m4_hardware_review"]
        for key, value in hardware.items():
            if key.endswith("_mm"):
                with self.subTest(clearance=key):
                    self.assertGreater(value, 0.0)

    def test_all_digital_acceptance_flags_pass(self):
        self.assertTrue(all(self.summary["digital_validation"].values()))

    def test_slice_gate_passes_but_is_not_production_authority(self):
        slicer = self.summary["slicer"]
        changed = slicer["changed_three_part_set"]
        complete = slicer["current_eight_part_set"]
        self.assertTrue(changed["all_parts_pass_margin"])
        self.assertTrue(complete["all_parts_pass_margin"])
        self.assertGreaterEqual(
            complete["minimum_post_brim_xy_margin_mm"],
            slicer["minimum_required_post_brim_xy_margin_mm"],
        )
        self.assertAlmostEqual(complete["total_filament_g"], 774.66)
        self.assertAlmostEqual(complete["total_support_g"], 388.317)
        self.assertEqual(
            self.summary["status"],
            "review_candidate_passed_digital_socket_gate_user_accepted_coupon_bypass",
        )

    def test_coupon_bypass_and_remaining_blockers_are_explicit(self):
        decision = self.summary["coupon_decision"]
        self.assertEqual(
            decision["decision"],
            "user accepted bypassing the physical socket coupon",
        )
        self.assertEqual(decision["straight_socket_opening_mm"], [21.0, 21.0])
        self.assertEqual(decision["lead_in_mouth_mm"], [23.0, 23.0])
        self.assertEqual(decision["outer_socket_envelope_mm"], [32.5, 32.5])
        self.assertTrue(decision["m4_cross_bolt_retained"])
        self.assertTrue(decision["optional_diagnostic_coupon_retained"])
        self.assertIn("shim", decision["permitted_rattle_mitigation"].lower())
        blockers = " ".join(self.summary["production_blockers"]).lower()
        for term in (
            "rail cut",
            "shoe",
            "lamp",
            "ear",
            "eye",
            "panel",
            "seam",
        ):
            with self.subTest(term=term):
                self.assertIn(term, blockers)


if __name__ == "__main__":
    unittest.main()
