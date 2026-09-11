from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/"
    "right-eye-lens-integral-side-screw-flanges-review-v6"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")


class LensIntegralSideScrewFlangeReviewTests(unittest.TestCase):
    def test_review_is_non_authoritative_and_v4_based(self) -> None:
        self.assertEqual(
            CONTRACT["authority"],
            "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE",
        )
        self.assertEqual(
            CONTRACT["basis"]["approved_geometry"],
            "right-eye-parallel-left-edge-orthogonal-wall-led-cassette-review-v4",
        )
        self.assertIn("v5", CONTRACT["basis"]["rejected_interpretation"])
        self.assertNotIn("right-eye-m2-lens-retention-flanges-review-v5", SOURCE)

    def test_four_flanges_belong_to_lens(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["lens_integral_flange_count"], 4)
        self.assertEqual(dimensions["lens_integral_flange_width"], 4.5)
        self.assertEqual(dimensions["lens_integral_flange_radial_depth"], 3.0)
        self.assertEqual(dimensions["lens_integral_flange_rear_length"], 4.25)
        self.assertIn(
            "V6 translucent lens with four integral rearward flanges",
            SOURCE,
        )
        self.assertIn("predrill_lens", SOURCE)

    def test_side_screws_are_radial_not_front_normal(self) -> None:
        self.assertIn("inward = axis_n.cross(tangent)", SOURCE)
        self.assertIn(
            "screw_axes_are_parallel_to_eye_front_plane", SOURCE
        )
        self.assertLessEqual(
            CONTRACT["gates"]["maximum_screw_axis_front_normal_dot"],
            1.0e-9,
        )

    def test_carrier_and_lens_have_correct_hole_ownership(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(
            dimensions["carrier_side_clearance_hole_diameter"], 2.2
        )
        self.assertEqual(
            dimensions["lens_integral_flange_pilot_diameter"], 1.6
        )
        self.assertIn("carrier_side_clearance_holes_are_open", SOURCE)
        self.assertIn("lens_flange_pilot_holes_are_open", SOURCE)

    def test_hidden_head_recess_preserves_structural_wall(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        remaining = (
            dimensions["box_wall_thickness"]
            - dimensions["carrier_side_head_recess_depth"]
        )
        self.assertEqual(
            dimensions["carrier_side_head_recess_diameter"], 4.4
        )
        self.assertGreaterEqual(
            remaining,
            CONTRACT["gates"]["minimum_wall_behind_head_recess_mm"],
        )
        self.assertIn(
            "carrier_wall_behind_head_recess_is_structural", SOURCE
        )

    def test_heads_are_gated_out_of_visible_cavity(self) -> None:
        self.assertIn(
            "screw_heads_are_outside_visible_aperture_cavity", SOURCE
        )
        self.assertLessEqual(
            CONTRACT["gates"]["maximum_visible_aperture_head_collision_mm3"],
            1.0e-6,
        )
        self.assertTrue(
            CONTRACT["gates"]["require_no_front_visible_fasteners"]
        )

    def test_flange_material_margin_is_fail_closed(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        radius = dimensions["lens_integral_flange_pilot_diameter"] / 2.0
        margins = (
            dimensions["lens_integral_flange_width"] / 2.0 - radius,
            dimensions["lens_integral_flange_pilot_rear_offset"]
            + dimensions["lens_integral_flange_front_overlap"]
            - radius,
            dimensions["lens_integral_flange_rear_length"]
            - dimensions["lens_integral_flange_pilot_rear_offset"]
            - radius,
        )
        self.assertGreaterEqual(
            min(margins),
            CONTRACT["gates"]["minimum_flange_material_around_pilot_mm"],
        )
        self.assertIn(
            "lens_flange_material_around_pilots_is_printable", SOURCE
        )

    def test_context_collisions_fail_closed(self) -> None:
        for check in (
            "reference_side_screws_clear_head_shell",
            "reference_side_screws_clear_led_pixels",
            "reference_side_screws_clear_rear_plate",
            "reference_side_screws_clear_carrier_after_drilling",
        ):
            self.assertIn(check, SOURCE)

    def test_all_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_review_requires_pinned_feasibility_and_has_no_export(self) -> None:
        self.assertIn("--feasibility-report", SOURCE)
        self.assertIn("feasibility report hash mismatch", SOURCE)
        for forbidden in (
            "exportStl", "exportMesh", "write_gcode", "exportStep"
        ):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
