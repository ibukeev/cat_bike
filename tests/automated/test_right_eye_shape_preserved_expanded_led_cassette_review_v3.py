from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/review-only/right-eye-shape-preserved-expanded-led-cassette-review-v3"
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")


class ShapePreservedExpandedLedCassetteReviewTests(unittest.TestCase):
    def test_review_only_authority(self) -> None:
        self.assertEqual(CONTRACT["authority"], "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE")

    def test_front_is_inset_and_has_no_surface_flange(self) -> None:
        self.assertEqual(CONTRACT["dimensions_mm"]["opening_cover_perimeter_clearance"], 0.6)
        self.assertGreaterEqual(CONTRACT["dimensions_mm"]["front_perimeter_radial_inset"], 1.2)
        self.assertGreaterEqual(CONTRACT["dimensions_mm"]["rear_perimeter_radial_inset"], 6.0)
        self.assertEqual(CONTRACT["dimensions_mm"]["visible_aperture_uniform_scale"], 0.88)
        self.assertIn("def similar_scaled_loop", SOURCE)
        self.assertIn("visible_aperture_shape_preserved_exactly", SOURCE)
        self.assertIn("visible_aperture_is_larger_than_v2", SOURCE)
        self.assertIn("lower filler panel", SOURCE)
        self.assertIn("opening-cover connector collar", SOURCE)
        self.assertIn("integral_lower_opening_panel_present", SOURCE)
        self.assertIn("def polygon_inset_loop", SOURCE)
        self.assertNotIn("_locally_inset_loop(\n        App, opening", SOURCE)

    def test_led_and_wire_requirements_are_explicit(self) -> None:
        self.assertEqual(CONTRACT["dimensions_mm"]["pixel_count"], 4)
        self.assertEqual(CONTRACT["dimensions_mm"]["wire_port_diameter"], 4.0)
        self.assertEqual(CONTRACT["dimensions_mm"]["wire_port_minor_axis_offset"], 3.0)
        self.assertGreaterEqual(CONTRACT["gates"]["minimum_led_to_lens_gap_mm"], 9.0)
        self.assertIn("wire_port_clear_of_led_references", SOURCE)

    def test_insertion_is_a_fail_closed_gate(self) -> None:
        self.assertIn("straight_front_insertion_clear", SOURCE)
        self.assertIn("positive_intersections_mm3", SOURCE)

    def test_all_head_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_review_mode_requires_pinned_feasibility(self) -> None:
        self.assertIn("--feasibility-report", SOURCE)
        self.assertIn("feasibility report hash mismatch", SOURCE)

    def test_no_manufacturing_export_path(self) -> None:
        for forbidden in ("exportStl", "exportMesh", "write_gcode", "exportStep"):
            self.assertNotIn(forbidden, SOURCE)

    def test_rejected_carrier_is_not_an_input(self) -> None:
        paths = [value["path"] for value in CONTRACT["inputs"].values()]
        self.assertFalse(any("static-conformal-adhesive-front-carrier" in path for path in paths))
        self.assertIn("not imported or reused", CONTRACT["inputs"]["former_lens_print_source_fcstd"]["role"])


if __name__ == "__main__":
    unittest.main()
