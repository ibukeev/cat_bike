from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/"
    "right-eye-rear-plate-hook-two-screw-retention-review-v7"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")


class RearPlateHookTwoScrewReviewV7Tests(unittest.TestCase):
    def test_review_is_non_authoritative_and_v6_based(self) -> None:
        self.assertEqual(
            CONTRACT["authority"],
            "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE",
        )
        self.assertEqual(
            CONTRACT["basis"]["approved_geometry"],
            "right-eye-lens-integral-side-screw-flanges-review-v6",
        )
        self.assertIn("run_v6_construct", SOURCE)
        self.assertIn("run_v6_evaluate", SOURCE)

    def test_mechanism_is_two_hooks_and_two_rear_screws(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["hook_count"], 2)
        self.assertEqual(dimensions["rear_screw_count"], 2)
        self.assertEqual(CONTRACT["hardware"]["quantity"], 2)
        self.assertIn("two plate-owned hooks", CONTRACT["approved_decision"]["mechanism"])
        self.assertIn("M2 x 6", CONTRACT["approved_decision"]["mechanism"])

    def test_hooks_are_anchored_to_wire_side_edge(self) -> None:
        self.assertIn("wire-exit", CONTRACT["approved_decision"]["hook_anchor"])
        self.assertIn("edge_wire_distances", SOURCE)
        self.assertIn("hook_edge_is_structured_edge_nearest_wire_exit", SOURCE)
        self.assertEqual(CONTRACT["dimensions_mm"]["hook_tangent_fractions"], [0.25, 0.75])

    def test_screws_are_on_opposite_edge(self) -> None:
        self.assertIn("opposite", CONTRACT["approved_decision"]["screw_anchor"])
        self.assertIn("screw_edge_index = (hook_edge_index", SOURCE)
        self.assertIn("screw_edge_is_opposite_hook_edge", SOURCE)

    def test_hook_clearance_and_engagement_are_explicit(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["hook_axial_clearance"], 0.05)
        self.assertGreaterEqual(
            dimensions["hook_radial_engagement"],
            CONTRACT["gates"]["minimum_hook_radial_engagement_mm"],
        )
        self.assertIn("hooks_capture_rearward_pullout", SOURCE)

    def test_plate_has_continuous_light_blocking_stop(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["rear_plate_to_locating_rim_gap"], 0.05)
        self.assertIn("rear plate locating and light-blocking rim", SOURCE)
        self.assertIn("continuous_locating_rim_has_pinned_gap", SOURCE)

    def test_boss_material_is_sized_around_m2_pilot(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        radius = dimensions["carrier_boss_pilot_diameter"] / 2.0
        tangent_margin = dimensions["carrier_boss_tangent_width"] / 2.0 - radius
        radial_margin = min(
            dimensions["carrier_boss_center_radial_offset"]
            - dimensions["carrier_boss_radial_start"]
            - radius,
            dimensions["carrier_boss_radial_end"]
            - dimensions["carrier_boss_center_radial_offset"]
            - radius,
        )
        self.assertGreaterEqual(
            min(tangent_margin, radial_margin),
            CONTRACT["gates"]["minimum_boss_material_around_pilot_mm"],
        )

    def test_plate_and_boss_holes_are_complementary(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["rear_plate_clearance_hole_diameter"], 2.2)
        self.assertEqual(dimensions["carrier_boss_pilot_diameter"], 1.6)
        self.assertIn("rear_plate_clearance_holes_are_open", SOURCE)
        self.assertIn("rear_boss_pilot_holes_are_open", SOURCE)
        self.assertIn("rear_screw_axes_align_with_plate_and_boss_holes", SOURCE)

    def test_service_access_and_motion_fail_closed(self) -> None:
        self.assertEqual(CONTRACT["dimensions_mm"]["rear_driver_corridor_diameter"], 5.0)
        self.assertIn("rear_driver_corridors_clear_head_shell", SOURCE)
        self.assertIn("rear_driver_corridors_clear_eye_geometry", SOURCE)
        self.assertIn("rear_plate_pivots_open_without_unintended_collision", SOURCE)
        self.assertIn("rear_plate_hooks_disengage_on_bounded_inward_slide", SOURCE)
        self.assertEqual(CONTRACT["dimensions_mm"]["pivot_review_angles_deg"][-1], 4.0)

    def test_v6_lens_aperture_leds_and_wire_are_protected(self) -> None:
        for check in (
            "approved_v6_lens_geometry_is_unchanged",
            "approved_v6_aperture_coordinates_are_unchanged",
            "new_retention_features_clear_led_pixels",
            "new_retention_features_clear_wire_route",
            "new_retention_features_clear_lens",
            "new_retention_features_clear_head_shell",
        ):
            self.assertIn(check, SOURCE)

    def test_all_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_review_requires_pinned_feasibility_and_has_no_export(self) -> None:
        self.assertIn("--feasibility-report", SOURCE)
        self.assertIn("feasibility report hash mismatch", SOURCE)
        for forbidden in ("exportStl", "exportMesh", "write_gcode", "exportStep"):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
