from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/"
    "lower-front-bilateral-modular-closure-review-v1"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_freecad_review.py").read_text(encoding="utf-8")


class LowerFrontBilateralModularClosureReviewV1Tests(unittest.TestCase):
    def test_review_authority_is_not_print_release(self) -> None:
        self.assertEqual(
            CONTRACT["authority"],
            "REVIEW_ONLY_NON_AUTHORITATIVE_NOT_A_PRINT_SOURCE",
        )

    def test_every_requested_class_remains_modular(self) -> None:
        policy = " ".join(CONTRACT["decision"]["modularity"]).lower()
        for token in (
            "opaque owner",
            "mirrored owner",
            "translucent",
            "mouth facets",
            "center seam",
            "panel flange",
            "head flange",
            "fastener reference",
        ):
            self.assertIn(token, policy)

    def test_opaque_ownership_is_explicit_and_non_mutating(self) -> None:
        resolution = CONTRACT["decision"]["opaque_ownership_resolution"]
        self.assertIn("world X=0", resolution["bilateral_seam"])
        self.assertIn("subtract", resolution["lower_upper_seam"])
        self.assertFalse(resolution["source_mutation"])

    def test_translucent_trim_preserves_declared_mount_zones(self) -> None:
        resolution = CONTRACT["decision"]["translucent_ownership_resolution"]
        self.assertIn("subtract only rejected intersection solids", resolution["policy"])
        self.assertFalse(resolution["source_stl_mutation"])
        self.assertFalse(resolution["component_fusion"])
        self.assertGreaterEqual(
            CONTRACT["numeric_gates"]["minimum_declared_lower_translucent_mount_groups"],
            2,
        )

    def test_mouth_is_shape_preserving_and_clearanced(self) -> None:
        mouth = CONTRACT["mouth"]
        self.assertEqual(mouth["source_panel_ids"], ["TRI005", "TRI006"])
        self.assertGreaterEqual(mouth["deep_body"]["perimeter_clearance_mm"], 0.65)
        self.assertGreaterEqual(mouth["visible_cap"]["perimeter_clearance_mm"], 0.35)
        self.assertGreaterEqual(
            CONTRACT["numeric_gates"]["mouth_minimum_head_clearance_mm"], 0.04
        )

    def test_mouth_has_independent_seam_and_two_fastener_pairs(self) -> None:
        mouth = CONTRACT["mouth"]
        self.assertEqual(mouth["mount_pair"]["fastener"].split()[0], "M2.5")
        self.assertEqual(mouth["mount_pair"]["face_gap_mm"], 0.3)
        self.assertGreaterEqual(mouth["mount_pair"]["panel_root_extension_mm"], 1.0)
        self.assertGreaterEqual(mouth["center_seam"]["width_mm"], 1.2)

    def test_generator_contains_fail_closed_interface_gates(self) -> None:
        for token in (
            "right_left_opaque_common_is_zero",
            "lower_upper_opaque_common_is_zero",
            "translucent_common_is_only_at_declared_mounts",
            "declared_lower_translucent_mount_roots_remain_positive",
            "mouth_facets_do_not_intersect_opaque_head",
            "mouth_facets_meet_head_clearance",
            "panel_flange_roots_meet_minimum",
            "head_flange_roots_meet_minimum",
        ):
            self.assertIn(token, SOURCE)

    def test_generator_cannot_export_or_release_print_files(self) -> None:
        for forbidden in ("exportStl", "exportMesh", "exportStep", "write_gcode"):
            self.assertNotIn(forbidden, SOURCE)
        self.assertIn('"geometry_export_created": False', SOURCE)
        self.assertIn('"production_output_created": False', SOURCE)


if __name__ == "__main__":
    unittest.main()
