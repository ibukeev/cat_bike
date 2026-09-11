#!/usr/bin/env python3
"""Focused synthetic regressions for split-cassette validator revision 001."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
REVISION_PATH = CONTROL / (
    "validate_right_eye_split_service_cassette_previsual_v1_"
    "validator_revision_001.py"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


revision = load(REVISION_PATH, "_test_split_cassette_validator_revision_001")


def record(offset: float, source: str = "fixture") -> dict:
    return {
        "source": source,
        "signed_plane_offset_from_bore_center_mm": offset,
    }


class SplitCassetteValidatorRevision001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract = json.loads((ROOT / revision.CONTRACT_RELATIVE).read_text())
        cls.parameters = contract["allowed_mutations"][0]["parameters"]
        cls.hardware = cls.parameters["validation_contract"]["hardware_envelopes"]

    def test_immutable_original_and_contract_pins(self) -> None:
        self.assertEqual(
            revision.sha256_file(CONTROL / revision.ORIGINAL_VALIDATOR_FILENAME),
            revision.ORIGINAL_VALIDATOR_SHA256,
        )
        self.assertEqual(
            revision.sha256_file(ROOT / revision.CONTRACT_RELATIVE),
            revision.CONTRACT_SHA256,
        )

    def test_original_evaluator_is_reused_exactly(self) -> None:
        self.assertIs(revision.evaluate, revision.original.evaluate)

    def test_actual_external_faces_are_signed_extrema(self) -> None:
        faces = [record(-1.2), record(0.8), record(1.6)]
        self.assertEqual(
            revision.select_external_face(
                faces, side="positive", maximum_axial_distance_mm=10.0
            )["signed_plane_offset_from_bore_center_mm"],
            1.6,
        )
        self.assertEqual(
            revision.select_external_face(
                faces, side="negative", maximum_axial_distance_mm=10.0
            )["signed_plane_offset_from_bore_center_mm"],
            -1.2,
        )

    def test_legacy_eye_washer_plane_is_inside_actual_step_fixture(self) -> None:
        mount = self.parameters["geometry"]["head_mount"]
        legacy_offset = float(mount["leaf_thickness_mm"]) - float(
            mount["bore_center_to_mating_face_mm"]
        )
        actual_low = -float(mount["bore_center_to_mating_face_mm"])
        actual_high = actual_low + float(mount["total_thickness_mm"])
        self.assertEqual(legacy_offset, -0.5)
        self.assertLess(actual_low, legacy_offset)
        self.assertLess(legacy_offset, actual_high)
        self.assertAlmostEqual(actual_high, 1.6, places=12)

    def test_no_planar_bore_face_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no actual axial bore face"):
            revision.select_external_face(
                [], side="positive", maximum_axial_distance_mm=10.0
            )

    def test_wrong_signed_side_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "wrong signed offset"):
            revision.select_external_face(
                [record(-0.5)], side="positive", maximum_axial_distance_mm=10.0
            )
        with self.assertRaisesRegex(RuntimeError, "wrong signed offset"):
            revision.select_external_face(
                [record(0.5)], side="negative", maximum_axial_distance_mm=10.0
            )

    def test_out_of_bolt_span_face_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no actual axial bore face"):
            revision.select_external_face(
                [record(10.01)], side="positive", maximum_axial_distance_mm=10.0
            )

    def test_receiver_interval_requires_one_unambiguous_negative_ray_span(self) -> None:
        good = {"minimum_offset_mm": -4.7741, "maximum_offset_mm": -1.9529}
        self.assertIs(
            revision.select_unique_negative_receiver_interval([good], 0.01), good
        )
        with self.assertRaisesRegex(RuntimeError, "missing or ambiguous"):
            revision.select_unique_negative_receiver_interval([], 0.01)
        with self.assertRaisesRegex(RuntimeError, "missing or ambiguous"):
            revision.select_unique_negative_receiver_interval([good, dict(good)], 0.01)

    def test_positive_only_receiver_interval_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "missing or ambiguous"):
            revision.select_unique_negative_receiver_interval(
                [{"minimum_offset_mm": 2.0, "maximum_offset_mm": 8.0}],
                0.01,
            )

    def test_exact_hardware_contract_is_accepted(self) -> None:
        revision._assert_fixed_hardware(self.hardware)
        self.assertEqual(self.hardware["bolt_nominal"], "M2.5")
        self.assertEqual(self.hardware["washer_outer_diameter_mm"], 7.0)
        self.assertEqual(self.hardware["washer_thickness_mm"], 0.8)
        self.assertEqual(self.hardware["nyloc_outer_diameter_mm"], 7.0)
        self.assertEqual(self.hardware["nyloc_length_mm"], 5.0)
        self.assertEqual(self.hardware["tool_approach_diameter_mm"], 8.0)
        self.assertEqual(self.hardware["tool_approach_length_mm"], 20.0)

    def test_each_hardware_dimension_change_fails_closed(self) -> None:
        changes = {
            "bolt_nominal": "M3",
            "bolt_diameter_mm": 2.6,
            "washer_outer_diameter_mm": 7.1,
            "washer_thickness_mm": 0.9,
            "nyloc_outer_diameter_mm": 7.1,
            "nyloc_length_mm": 5.1,
            "tool_approach_diameter_mm": 8.1,
            "tool_approach_length_mm": 20.1,
        }
        for key, value in changes.items():
            with self.subTest(key=key):
                fixture = copy.deepcopy(self.hardware)
                fixture[key] = value
                with self.assertRaisesRegex(RuntimeError, "fixed hardware changed"):
                    revision._assert_fixed_hardware(fixture)

    def test_revision_source_does_not_use_legacy_leaf_face_formula(self) -> None:
        source = REVISION_PATH.read_text(encoding="utf-8")
        self.assertIn("axial_bore_face_records", source)
        self.assertIn("actual-analytic-planar-mount-faces-on-signed-bore-v1", source)
        self.assertIn("signed-bore-axis-protected-owner-solid-exit-v1", source)
        self.assertNotIn('mount_values["leaf_thickness_mm"]', source)
        self.assertIn("candidate_output_reused\": False", source)


if __name__ == "__main__":
    unittest.main()
