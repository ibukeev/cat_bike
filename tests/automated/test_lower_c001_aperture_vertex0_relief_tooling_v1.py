from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
GENERATOR_PATH = CONTROL / "generate_lower_c001_aperture_vertex0_relief_v1.py"
VALIDATOR_PATH = CONTROL / "validate_lower_c001_aperture_vertex0_relief_v1.py"
BASELINE_PATH = CONTROL / "v2/approved-baseline-v34.json"
CONTRACT_PATH = CONTROL / "v2/lower-c001-aperture-vertex0-relief-v1.json"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = load_module("lower_c001_relief_generator_v1", GENERATOR_PATH)
VALIDATOR = load_module("lower_c001_relief_validator_v1", VALIDATOR_PATH)


class LowerC001ReliefToolingV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.parameters = cls.contract["allowed_mutations"][0]["parameters"]

    def test_exact_single_owner_authorization_and_dimensions(self) -> None:
        self.assertEqual(self.contract["target_object"], GENERATOR.TARGET_OBJECT)
        self.assertEqual(len(self.contract["allowed_mutations"]), 1)
        mutation = self.contract["allowed_mutations"][0]
        self.assertEqual(mutation["kind"], "replace_geometry")
        self.assertEqual(mutation["object"], "FROZEN_RIGHT_LOWER_MAIN_V34")
        relief = self.parameters["relief"]
        self.assertEqual(relief["authorized_owner"], mutation["object"])
        self.assertEqual(relief["vertex_id"], "V0")
        self.assertEqual(self.parameters["design_control"]["tooling_revision"], 3)
        self.assertEqual(
            self.parameters["construction_algorithm_id"],
            "lower-c001-v0-staged-clean-intersection-relief-A@3",
        )
        self.assertEqual(relief["exclusion_envelope_radius_mm"], 1.0)
        self.assertEqual(relief["nominal_maximum_retreat_mm"], 0.41)
        self.assertEqual(relief["hard_cap_retreat_mm"], 0.411)
        self.assertEqual(relief["required_post_relief_span_mm"], 1.0)
        self.assertEqual(relief["measurement_tolerance_mm"], 0.001)
        self.assertIn("APPROVE LOWER-C001 0.411 MM RELIEF", self.contract["user_approval"]["exact_instruction"])
        self.assertIn("APPROVE 0.58 MM LOWER BEZEL COVER LIP", self.contract["user_approval"]["exact_instruction"])
        lip = self.parameters["cover_lip_interface"]
        self.assertEqual(lip["nominal_in_plane_reach_mm"], 0.58)
        self.assertEqual(lip["nominal_outward_axial_cover_mm"], 0.022)
        self.assertEqual(lip["required_measured_outward_cover_mm"], 0.011005)
        self.assertEqual(lip["adverse_dimensional_tolerance_mm"], 0.01)
        self.assertEqual(lip["coverage_envelope_inward_depth_mm"], 0.012)
        self.assertEqual(lip["minimum_printed_wall_mm"], 0.7)
        self.assertEqual(lip["baseline_exterior_face_index"], 321)

    def test_aperture_digest_and_design_signature_are_exact(self) -> None:
        relief = self.parameters["relief"]
        aperture = self.parameters["aperture_lcs"]["visible_aperture_mm"]
        self.assertEqual(
            GENERATOR.canonical_json_sha256(aperture),
            relief["immutable_aperture_coordinates_sha256"],
        )
        result = GENERATOR.validate_design_control(ROOT, self.contract, self.parameters)
        self.assertEqual(
            result["signature_sha256"],
            self.parameters["design_control"]["design_signature"]["sha256"],
        )

    def passing_values(self) -> dict[str, Any]:
        relief = self.parameters["relief"]
        return {
            "aperture_coordinates_sha256": relief["immutable_aperture_coordinates_sha256"],
            "pre_relief_span_mm": relief["approved_pre_relief_span_mm"],
            "post_relief_span_mm": 1.0,
            "maximum_retreat_mm": 0.4097763364463181,
            "removed_volume_mm3": 0.2,
            "added_volume_mm3": 0.0,
            "expected_minus_actual_mm3": 0.0,
            "actual_minus_expected_mm3": 0.0,
            "removed_outside_eye_opening_mm3": 0.18044128899471354,
            "exterior_patch_area_mm2": 0.47532604762257014,
            "covered_exterior_patch_area_mm2": 0.47532604762257014,
            "uncovered_exterior_patch_area_mm2": 0.0,
            "cover_area_balance_residual_mm2": 0.0,
            "cover_lip_effective_reach_mm": 0.57,
            "cover_lip_effective_outward_cover_mm": 0.012,
            "cover_lip_minimum_printed_wall_mm": 0.7,
            "removed_solid_count": 1,
            "candidate_solid_count": 1,
            "candidate_valid": True,
            "candidate_closed": True,
            "baseline_deep_bop_defects": {"Face:BOPAlgo SelfIntersect": 4},
            "candidate_deep_bop_defects": {"Face:BOPAlgo SelfIntersect": 3},
            "new_deep_bop_defects": {},
            "removed_deep_bop_defects": {},
            "target_identity_preserved": True,
            "metadata_exact": True,
            "review_pack_complete": True,
        }

    def test_all_physical_gates_pass_at_authorized_values(self) -> None:
        result = VALIDATOR.evaluate_gates(self.passing_values(), self.parameters, True)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed_gates"], [])

    def test_every_gate_fails_closed_individually(self) -> None:
        cases = {
            "R01_PRESERVATION_PASS": ("preservation", False),
            "R02_APERTURE_COORDINATES_EXACT": ("aperture_coordinates_sha256", "bad"),
            "R03_BASELINE_SPAN_PINNED": ("pre_relief_span_mm", 0.5),
            "R04_SINGLE_CONNECTED_REMOVAL": ("removed_solid_count", 2),
            "R05_SUBTRACTION_ONLY": ("added_volume_mm3", 0.01),
            "R06_EXACT_ENVELOPE_INTERSECTION": ("actual_minus_expected_mm3", 0.01),
            "R07_POST_SPAN_AT_LEAST_1MM": ("post_relief_span_mm", 0.9),
            "R08_RETREAT_WITHIN_HARD_CAP": ("maximum_retreat_mm", 0.412),
            "R09_EXTERIOR_RELIEF_FULLY_COVERED_BY_PINNED_LIP": ("uncovered_exterior_patch_area_mm2", 0.01),
            "R10_VALID_CLOSED_SINGLE_TARGET": ("new_deep_bop_defects", {"Edge:BOPAlgo SelfIntersect": 1}),
            "R11_NONZERO_BOUNDED_RELIEF": ("removed_volume_mm3", 0.0),
            "R12_TARGET_IDENTITY_AND_PLACEMENT": ("target_identity_preserved", False),
            "R13_METADATA_EXACT": ("metadata_exact", False),
            "R14_REVIEW_PACK_COMPLETE": ("review_pack_complete", False),
        }
        for expected_gate, (field, value) in cases.items():
            with self.subTest(gate=expected_gate):
                values = self.passing_values()
                preservation_ok = True
                if field == "preservation":
                    preservation_ok = bool(value)
                else:
                    values[field] = value
                result = VALIDATOR.evaluate_gates(values, self.parameters, preservation_ok)
                self.assertEqual(result["status"], "FAIL")
                self.assertIn(expected_gate, result["failed_gates"])

    def test_cover_lip_gate_rejects_area_axial_and_wall_expansion(self) -> None:
        cases = {
            "exterior_patch_area_mm2": 0.50,
            "cover_area_balance_residual_mm2": 0.01,
            "cover_lip_effective_reach_mm": 0.568,
            "cover_lip_effective_outward_cover_mm": 0.010,
            "cover_lip_minimum_printed_wall_mm": 0.69,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                values = self.passing_values()
                values[field] = value
                result = VALIDATOR.evaluate_gates(values, self.parameters, True)
                self.assertEqual(result["status"], "FAIL")
                self.assertIn(
                    "R09_EXTERIOR_RELIEF_FULLY_COVERED_BY_PINNED_LIP",
                    result["failed_gates"],
                )

    def test_inherited_baseline_deep_defects_are_not_misclassified_as_new(self) -> None:
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        document = VALIDATOR.App.openDocument(str(ROOT / baseline["assembly"]["path"]))
        try:
            target = document.getObject(GENERATOR.TARGET_OBJECT)
            self.assertIsNotNone(target)
            inherited = VALIDATOR.deep_bop_defect_counts(target.Shape)
        finally:
            VALIDATOR.App.closeDocument(document.Name)
        self.assertGreater(sum(inherited.values()), 0)
        self.assertIn("Face:BOPAlgo SelfIntersect", inherited)
        self.assertEqual(VALIDATOR.added_deep_bop_defects(inherited, inherited), {})

    def test_new_deep_defect_category_or_count_is_rejected(self) -> None:
        baseline = {"Face:BOPAlgo SelfIntersect": 4}
        self.assertEqual(
            VALIDATOR.added_deep_bop_defects(
                baseline,
                {
                    "Face:BOPAlgo SelfIntersect": 5,
                    "Edge:BOPAlgo SelfIntersect": 1,
                },
            ),
            {"Face:BOPAlgo SelfIntersect": 1, "Edge:BOPAlgo SelfIntersect": 1},
        )

    def test_persisted_equivalence_avoids_reverse_boolean_fragmentation(self) -> None:
        Part = VALIDATOR.Part
        base = Part.makeBox(5.0, 5.0, 5.0)
        expected_removed = Part.makeBox(1.0, 1.0, 1.0)
        expected_candidate = base.cut(expected_removed).removeSplitter()
        removed, measurements = VALIDATOR.exact_authorized_removal_from_candidate(
            base, expected_candidate, expected_removed, 1.0e-9
        )
        self.assertAlmostEqual(float(removed.Volume), 1.0, places=9)
        self.assertEqual(
            measurements,
            {
                "candidate_minus_expected_candidate_mm3": 0.0,
                "expected_candidate_minus_candidate_mm3": 0.0,
            },
        )
        with self.assertRaises(RuntimeError):
            VALIDATOR.exact_authorized_removal_from_candidate(
                base, base, expected_removed, 1.0e-9
            )

    def test_output_state_and_release_holds(self) -> None:
        output = ROOT / self.contract["output"]["directory"]
        held = self.parameters["held_candidate_evidence"]
        if output.exists():
            candidate = ROOT / self.contract["output"]["candidate_fcstd"]
            preservation = output / "preservation-report.json"
            self.assertTrue(candidate.is_file())
            self.assertTrue(preservation.is_file())
            self.assertEqual(
                hashlib.sha256(candidate.read_bytes()).hexdigest(),
                held["candidate_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(preservation.read_bytes()).hexdigest(),
                held["preservation_report_sha256"],
            )
        self.assertTrue(self.contract["budget"]["fresh_chat_required"])
        self.assertEqual(self.contract["budget"]["max_candidates"], 1)
        self.assertEqual(self.contract["budget"]["max_repair_attempts"], 0)
        self.assertTrue(all(value is False for value in self.contract["release_holds"].values()))

    def test_scripts_fail_closed_on_save_and_retry_boundaries(self) -> None:
        generator_source = GENERATOR_PATH.read_text(encoding="utf-8")
        validator_source = VALIDATOR_PATH.read_text(encoding="utf-8")
        self.assertIn("--in-memory-finalization-preflight", generator_source)
        self.assertIn('"save_as_called": False', generator_source)
        self.assertIn('"document_save_called": False', generator_source)
        self.assertIn('"retry_allowed": False', validator_source)
        self.assertNotIn("saveAs(", validator_source)
        self.assertNotIn(".save()", validator_source)
        self.assertNotIn("generate_lower_c001", validator_source)
        self.assertIn("proposed_cover_lip_envelope", generator_source)
        self.assertIn("proposed_cover_lip_envelope", validator_source)
        self.assertIn("Face321", generator_source)
        self.assertIn("Face321", validator_source)
        self.assertIn("exact_authorized_removal_from_candidate", validator_source)
        self.assertNotIn(
            "removed = base_shape.cut(candidate_shape).removeSplitter()",
            validator_source,
        )


if __name__ == "__main__":
    unittest.main()
