#!/usr/bin/env python3
"""Focused fail-closed tests for the V2 lower-front feedback cleanup."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = REPO_ROOT / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/review-only/lower-front-bilateral-feedback-cleanup-review-v2"
CONTRACT_PATH = HERE / "contract.json"
GENERATOR_PATH = HERE / "generate_freecad_review.py"
RENDERER_PATH = HERE / "render_review.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FeedbackCleanupV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.source = GENERATOR_PATH.read_text(encoding="utf-8")

    def test_schema_and_authority_are_review_only(self) -> None:
        self.assertEqual(
            self.contract["schema_version"],
            "cat-head-lower-front-bilateral-feedback-cleanup-review-v2",
        )
        self.assertEqual(
            self.contract["authority"],
            "REVIEW_ONLY_NON_AUTHORITATIVE_NOT_A_PRINT_SOURCE",
        )

    def test_exact_five_approved_changes_are_declared(self) -> None:
        changes = self.contract["decision"]["approved_changes"]
        self.assertEqual(len(changes), 5)
        joined = " ".join(changes)
        for token in ("Face30", "component_007", "component_014", "component_021", "50 mm"):
            self.assertIn(token, joined)

    def test_cleanup_dimensions_are_fixed(self) -> None:
        cleanup = self.contract["cleanup"]
        self.assertEqual(cleanup["face30_fin"]["outboard_x_min_mm"], 80.0)
        self.assertEqual(cleanup["component_007_manual_flange"]["hidden_root_bbox_margin_mm"], 0.0)
        self.assertEqual(cleanup["component_014"]["policy"], "omit_complete_obsolete_exterior_owner")
        self.assertEqual(cleanup["component_021"]["policy"], "keep_center_half")

    def test_outboard_station_has_printable_edge_and_spacing_gates(self) -> None:
        ledge = self.contract["ledge_extension"]
        self.assertEqual(ledge["source_accessible_ear_u_mm"], 24.0)
        self.assertEqual(ledge["ear_copy_offset_mm"], 50.0)
        self.assertGreaterEqual(ledge["minimum_station_spacing_mm"], 8.0)
        self.assertGreaterEqual(ledge["minimum_bore_edge_material_mm"], 3.5)
        self.assertGreaterEqual(ledge["minimum_support_annulus_common_mm3"], 20.0)

    def test_generator_uses_subset_cleanup_and_exact_mirror(self) -> None:
        for token in (
            "front_added.common(fin_box)",
            "manual.fuse(hidden_root)",
            "if index == 14",
            "nose_source.common",
            "measured_material_exit_from_bore_common",
            "support_annulus_common_mm3",
            "ear_copy_offset_mm",
            "mirror_x0",
        ):
            self.assertIn(token, self.source)

    def test_generator_is_review_only_and_has_no_export_calls(self) -> None:
        self.assertIn("review_saved", self.source)
        self.assertNotRegex(self.source, re.compile(r"exportStl|exportStep|Mesh\.export|Part\.export"))
        self.assertNotIn("production_output_created\"] = True", self.source)

    def test_output_names_are_fresh_and_nonproduction(self) -> None:
        outputs = self.contract["outputs"]
        self.assertIn("review-only/lower-front-bilateral-feedback-cleanup-review-v2", outputs["directory"])
        self.assertEqual(len(outputs["views"]), 6)
        self.assertNotIn("FINAL-PRINT-SET", outputs["directory"])

    def test_tooling_hash_pins_match(self) -> None:
        tooling = self.contract["tooling"]
        self.assertEqual(tooling["generator_sha256"], digest(GENERATOR_PATH))
        self.assertEqual(tooling["renderer_sha256"], digest(RENDERER_PATH))
        self.assertEqual(tooling["focused_test_sha256"], digest(Path(__file__)))


if __name__ == "__main__":
    unittest.main()
