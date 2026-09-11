from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/review-only/right-eye-parallel-left-edge-orthogonal-wall-led-cassette-review-v4"
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")
V3_SOURCE = (
    ROOT / CONTRACT["inputs"]["v3_review_generator"]["path"]
).read_text(encoding="utf-8")


class ParallelLeftEdgeOrthogonalWallReviewTests(unittest.TestCase):
    def test_review_only_authority_and_scope(self) -> None:
        self.assertEqual(
            CONTRACT["authority"],
            "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE",
        )
        self.assertEqual(
            CONTRACT["supersedes_review_id"],
            "right-eye-shape-preserved-expanded-led-cassette-review-v3",
        )
        self.assertEqual(CONTRACT["anchors"]["selected_aperture_edge"]["vertex_indices"], [0, 1])
        self.assertEqual(CONTRACT["anchors"]["parallel_shell_edge"]["vertex_indices"], [0, 1])
        self.assertEqual(CONTRACT["anchors"]["frozen_aperture_vertices"], [2, 3])

    def test_selected_edge_contract_is_explicit(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["selected_left_edge_shell_normal_offset"], 2.2)
        self.assertEqual(dimensions["selected_edge_deep_rim_relief_inward_span"], 0.6)
        self.assertEqual(dimensions["selected_left_edge_lower_along_shell_edge_inset"], 2.2)
        self.assertEqual(dimensions["selected_edge_deep_rim_relief_endpoint_extension"], 3.0)
        self.assertIn("def parallel_left_edge_loop", SOURCE)
        self.assertIn("selected_left_edge_parallel_to_shell_edge", SOURCE)
        self.assertIn("selected_left_edge_length_preserved_from_v3", SOURCE)
        self.assertIn("lower_left_corner_moved_toward_shell_corner", SOURCE)
        self.assertIn("unselected_aperture_vertices_unchanged", SOURCE)
        self.assertIn("def selected_edge_relief_cutter", SOURCE)
        self.assertIn("selected_edge_deep_rim_relief_applied", SOURCE)

    def test_box_walls_are_constant_section_and_perpendicular(self) -> None:
        dimensions = CONTRACT["dimensions_mm"]
        self.assertEqual(dimensions["straight_box_outer_inset_from_aperture"], 0.5)
        self.assertEqual(dimensions["straight_sidewall_thickness"], 1.2)
        self.assertIn("perpendicular straight sidewalls", SOURCE)
        self.assertIn("sidewalls_perpendicular_to_front_plane", SOURCE)
        self.assertIn("maximum_sidewall_lateral_drift_mm", SOURCE)
        self.assertNotIn("loft_ring(", SOURCE)

    def test_lower_panel_leds_and_wire_remain_explicit(self) -> None:
        self.assertEqual(CONTRACT["dimensions_mm"]["opening_cover_perimeter_clearance"], 0.6)
        self.assertEqual(CONTRACT["dimensions_mm"]["pixel_count"], 4)
        self.assertEqual(CONTRACT["dimensions_mm"]["wire_port_diameter"], 4.0)
        self.assertIn("lower filler panel", SOURCE)
        self.assertIn("wire_port_clear_of_led_references", V3_SOURCE)
        self.assertIn("base = v3.evaluate(context)", SOURCE)

    def test_physical_fit_gates_remain_fail_closed(self) -> None:
        gates = CONTRACT["gates"]
        self.assertGreaterEqual(gates["minimum_static_shell_clearance_mm"], 0.3)
        self.assertGreaterEqual(gates["minimum_actual_sidewall_thickness_mm"], 1.0)
        self.assertIn("straight_front_insertion_clear", V3_SOURCE)
        self.assertIn("rear_plate_inside_service_clear", V3_SOURCE)
        self.assertIn("zero_static_shell_intersection", V3_SOURCE)

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
