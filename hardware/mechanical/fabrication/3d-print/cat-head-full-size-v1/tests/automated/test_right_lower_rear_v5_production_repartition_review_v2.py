#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "source/cad-change-control/review-only/right-lower-rear-v5-production-repartition-review-v2"
CONTRACT_PATH = TOOL_DIR / "contract.json"
GENERATOR_PATH = TOOL_DIR / "generate_freecad_review.py"


class LowerRearV5RepartitionV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("lower_repartition_v2_test", GENERATOR_PATH)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_schema_and_authority_are_review_only(self) -> None:
        self.assertEqual(
            self.contract["schema_version"],
            "cat-head-right-lower-rear-v5-production-repartition-review-v2",
        )
        self.assertIn("REVIEW_ONLY", self.contract["authority"])
        self.assertIn("NOT_A_PRINT_SOURCE", self.contract["authority"])

    def test_approved_seam_and_clearance_are_pinned(self) -> None:
        partition = self.contract["partition"]
        self.assertEqual(partition["mating_clearance_mm"], 0.3)
        self.assertEqual(
            partition["seam_endpoints_mm"],
            [
                [126.93900299072266, 200.65199279785156, 109.98899841308594],
                [88.94550323486328, 188.3385009765625, 47.872501373291016],
            ],
        )

    def test_only_known_non_crossing_mesh_owners_may_bypass_brep(self) -> None:
        policy = self.contract["canonical_owner_policy"]
        self.assertEqual(policy["known_retained_mesh_only_owner_indices"], [9, 16, 33])
        source = GENERATOR_PATH.read_text(encoding="utf-8")
        self.assertIn("mesh-only owner is not wholly retained", source)
        self.assertIn("unexpected invalid canonical owner", source)

    def test_empty_kept_side_requires_signed_span_proof(self) -> None:
        self.assertEqual(self.module.expected_kept_sides(-1.0, 1.0, 0.3), (True, True))
        self.assertEqual(self.module.expected_kept_sides(0.066, 3.74, 0.3), (False, True))
        self.assertEqual(self.module.expected_kept_sides(-3.74, -0.066, 0.3), (True, False))
        self.assertIn(
            "empty_trim_side_requires_signed_span_proof",
            self.contract["gates"],
        )

    def test_released_v3_eye_is_the_only_eye_context(self) -> None:
        inputs = self.contract["inputs"]
        self.assertIn("released_v3_right_eye", inputs)
        self.assertNotIn("finished_right_eye_reference", inputs)
        self.assertEqual(len(self.contract["required_v3_eye_objects"]), 3)

    def test_feasibility_is_tmp_only(self) -> None:
        source = GENERATOR_PATH.read_text(encoding="utf-8")
        self.assertIn('startswith("/tmp/")', source)
        self.assertIn("feasibility requires a /tmp report", source)

    def test_no_manufacturing_export_path_exists(self) -> None:
        source = GENERATOR_PATH.read_text(encoding="utf-8")
        for forbidden in ("exportStl", "writeSTL", "exportMesh", "subprocess", "prusa-slicer"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn(".stl", json.dumps(self.contract).lower())
        self.assertNotIn(".3mf", json.dumps(self.contract).lower())
        self.assertNotIn(".gcode", json.dumps(self.contract).lower())

    def test_review_output_is_fresh_v2_namespace(self) -> None:
        output = self.contract["outputs"]
        self.assertTrue(output["directory"].endswith("right-lower-rear-v5-production-repartition-review-v2"))
        self.assertIn("REVIEW_ONLY_V2", output["fcstd"])


if __name__ == "__main__":
    unittest.main()
