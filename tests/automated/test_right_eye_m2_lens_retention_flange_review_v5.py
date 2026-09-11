from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/"
    "right-eye-m2-lens-retention-flanges-review-v5"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")


class M2LensRetentionFlangeReviewTests(unittest.TestCase):
    def test_review_only_v5_scope_is_explicit(self) -> None:
        self.assertEqual(
            CONTRACT["authority"],
            "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE",
        )
        self.assertEqual(
            CONTRACT["supersedes_review_id"],
            "right-eye-parallel-left-edge-orthogonal-wall-led-cassette-review-v4",
        )
        self.assertIn("V4 LGTM", CONTRACT["visual_decision"])

    def test_four_small_inward_tabs_are_dimensioned(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["lens_retention_tab_count"], 4)
        self.assertEqual(dimensions["lens_retention_tab_width"], 4.0)
        self.assertEqual(dimensions["lens_retention_tab_inward_projection"], 3.0)
        self.assertEqual(dimensions["lens_retention_tab_wall_overlap"], 0.3)
        self.assertEqual(dimensions["lens_retention_tab_axial_thickness"], 3.0)
        self.assertIn("inward * tab_projection", SOURCE)
        self.assertIn("V5 carrier with four inward lens-retention tabs", SOURCE)

    def test_m2_holes_and_screw_specification_match(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["lens_retention_pilot_diameter"], 1.6)
        self.assertEqual(dimensions["lens_clearance_hole_diameter"], 2.2)
        self.assertEqual(dimensions["lens_screw_nominal_diameter"], 2.0)
        self.assertEqual(dimensions["lens_screw_length"], 4.0)
        self.assertEqual(CONTRACT["hardware"]["quantity"], 4)
        self.assertIn("M2x4", CONTRACT["hardware"]["fastener"])
        self.assertIn("lens_and_carrier_hole_axes_align", SOURCE)

    def test_tab_material_margin_is_fail_closed(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        pilot_radius = dimensions["lens_retention_pilot_diameter"] / 2.0
        margins = (
            dimensions["lens_retention_tab_width"] / 2.0 - pilot_radius,
            dimensions["lens_retention_hole_center_inward_projection"]
            + dimensions["lens_retention_tab_wall_overlap"]
            - pilot_radius,
            dimensions["lens_retention_tab_inward_projection"]
            - dimensions["lens_retention_hole_center_inward_projection"]
            - pilot_radius,
        )
        self.assertGreaterEqual(
            min(margins),
            CONTRACT["gates"]["minimum_lens_retention_material_around_pilot_mm"],
        )
        self.assertIn("lens_retention_material_around_pilots", SOURCE)

    def test_v4_geometry_is_inherited_not_rebuilt(self) -> None:
        self.assertIn("v4.construct(context, App, Part)", SOURCE)
        self.assertIn("base = v4.evaluate(context)", SOURCE)
        self.assertIn("v4_aperture_coordinates_unchanged", SOURCE)
        self.assertIn(
            "head-mounting flanges remain the next serial stage",
            CONTRACT["architecture"]["head_attachment"],
        )

    def test_hardware_context_gates_are_explicit(self) -> None:
        self.assertIn("m2_reference_screws_clear_shell", SOURCE)
        self.assertIn("m2_reference_screws_clear_leds", SOURCE)
        self.assertIn("m2_reference_screws_clear_rear_plate", SOURCE)
        self.assertLessEqual(
            CONTRACT["gates"]["maximum_reference_screw_shell_collision_mm3"],
            0.000001,
        )

    def test_all_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_review_mode_requires_pinned_feasibility(self) -> None:
        self.assertIn("--feasibility-report", SOURCE)
        self.assertIn("feasibility report hash mismatch", SOURCE)

    def test_no_manufacturing_export_path(self) -> None:
        for forbidden in ("exportStl", "exportMesh", "write_gcode", "exportStep"):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
