#!/usr/bin/env python3
"""Regressions for additive lower-C001 relief validator revision 001."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
    "cad-change-control/validate_lower_c001_aperture_vertex0_relief_v1_validator_revision_001.py"
)
AUTH_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/"
    "cad-change-control/v2/lower-c001-aperture-vertex0-relief-v1-validator-revision-001-authorization.json"
)
SPEC = importlib.util.spec_from_file_location("lower_c001_relief_validator_revision_001", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load validator revision")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ValidatorRevision001Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.authorization = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    def test_revision_and_all_immutable_evidence_are_hash_pinned(self) -> None:
        self.assertEqual(
            VALIDATOR.SOURCE.sha256_file(VALIDATOR_PATH),
            self.authorization["validator_revision"]["sha256"],
        )
        for record in self.authorization["pinned_evidence"].values():
            self.assertEqual(
                VALIDATOR.SOURCE.sha256_file(ROOT / record["path"]),
                record["sha256"],
            )

    def test_consumed_report_is_sole_r05_failure(self) -> None:
        record = self.authorization["pinned_evidence"]["consumed_failed_report"]
        report = json.loads((ROOT / record["path"]).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["failed_gates"], ["R05_SUBTRACTION_ONLY"])
        self.assertTrue(all(v for k, v in report["gates"].items() if k != "R05_SUBTRACTION_ONLY"))

    def test_exact_equivalence_reclassifies_unstable_reverse_boolean(self) -> None:
        values = {
            "added_volume_mm3": 78628.04975138359,
            "candidate_minus_expected_candidate_mm3": 0.0,
        }
        corrected = VALIDATOR.corrected_r05_measurements(values)
        self.assertEqual(corrected["added_volume_mm3"], 0.0)
        self.assertEqual(
            corrected["r05_unstable_reverse_boolean_diagnostic_mm3"],
            78628.04975138359,
        )
        self.assertTrue(VALIDATOR.r05_subtraction_only(values, 1.0e-6))

    def test_positive_added_material_still_fails_r05(self) -> None:
        values = {
            "added_volume_mm3": 0.0,
            "candidate_minus_expected_candidate_mm3": 0.000002,
        }
        self.assertFalse(VALIDATOR.r05_subtraction_only(values, 1.0e-6))

    def test_fresh_report_identity_is_distinct_and_absent(self) -> None:
        report = ROOT / self.authorization["fresh_report_path"]
        consumed = ROOT / self.authorization["pinned_evidence"]["consumed_failed_report"]["path"]
        self.assertNotEqual(report.resolve(), consumed.resolve())
        self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
