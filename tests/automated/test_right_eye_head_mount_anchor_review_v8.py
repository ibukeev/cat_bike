from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/right-eye-head-mount-anchor-review-v8"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_review.py").read_text(encoding="utf-8")


class RightEyeHeadMountAnchorReviewV8Tests(unittest.TestCase):
    def test_review_contains_no_connector_geometry(self) -> None:
        self.assertIn("NO_CONNECTOR_GEOMETRY", CONTRACT["authority"])
        self.assertIn("ANCHORS_ONLY", CONTRACT["holds"])
        self.assertIn("connector_geometry_created\": False", SOURCE)

    def test_asymmetric_layout_matches_user_instruction(self) -> None:
        deferred = CONTRACT["deferred_connector_contract"]
        self.assertIn("no separate top eye flange", deferred["top"])
        self.assertIn("one eye-owned flange plus one head-owned flange", deferred["bottom_left"])

    def test_top_uses_selected_structured_face382(self) -> None:
        self.assertEqual(CONTRACT["anchor_policy"]["top_head_face"], "Face382")
        self.assertIn("ANCHOR__TOP_HEAD_FACE382", SOURCE)

    def test_bottom_left_is_on_bottom_edge_near_left_corner(self) -> None:
        policy = CONTRACT["anchor_policy"]
        self.assertEqual(policy["bottom_left_eye_wall_edge_index"], 3)
        self.assertEqual(policy["bottom_left_eye_wall_tangent_fraction"], 0.75)

    def test_m3_default_and_structural_gates_are_recorded(self) -> None:
        deferred = CONTRACT["deferred_connector_contract"]
        self.assertIn("M3 x 16", deferred["fastener_default"])
        self.assertGreaterEqual(deferred["minimum_bore_to_edge_material_mm"], 3.5)
        self.assertGreaterEqual(deferred["minimum_owner_root_overlap_mm3"], 80.0)

    def test_all_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_no_export_or_production_operations(self) -> None:
        for forbidden in ("exportStl", "exportMesh", "exportStep", "write_gcode"):
            self.assertNotIn(forbidden, SOURCE)

    def test_tooling_revision_two_and_freecad_vertex_api_repair(self) -> None:
        self.assertEqual(CONTRACT["tooling_revision"], 2)
        self.assertIn("Part.Vertex(target)", SOURCE)
        self.assertNotIn("App.Vertex(", SOURCE)
        self.assertNotIn("distanceToPoint", SOURCE)
        self.assertNotIn("if False", SOURCE)


if __name__ == "__main__":
    unittest.main()
