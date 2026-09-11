#!/usr/bin/env python3
"""Focused source/contract regressions for the additive E1 relief tooling."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/generate_right_eye_split_service_cassette_leadin_relief_e1.py"
)
CONTRACT = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/right-eye-split-service-cassette-leadin-relief-e1.json"
)
EXPECTED_GENERATOR_SHA256 = "cfb8e202d4c5ac28d2c4983dae571658f0de08961366d16e4ed9c30029c9c299"
EXPECTED_CONTRACT_SHA256 = "a66c70bc67577b08a5778c9ce2c6151aca24094531fb35125f600159c474223f"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_generator():
    spec = importlib.util.spec_from_file_location("_test_e1_generator", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class E1ReliefContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_text = SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source_text)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.generator = load_generator()

    def test_immutable_v1_pins_are_exact(self) -> None:
        self.assertEqual(
            self.generator.V1_GENERATOR_SHA256,
            "611aa4b63a0cd81420a01507168095c9a0a4d967d306688d78fe69b5383815fc",
        )
        self.assertEqual(
            self.generator.V1_CONTRACT_SHA256,
            "08fa1c89ad307598e8b0edaa3dc55085cd2ddc977904209972ca698d21790b9f",
        )

    def test_contract_embeds_exact_all_21_poses(self) -> None:
        samples = self.contract["motion_path"]["samples"]
        actual = tuple(
            (item["sample_index"], item["tilt_deg"], item["translation_mm"])
            for item in samples
        )
        self.assertEqual(actual, self.generator.POSES)
        self.assertEqual([item[0] for item in actual], list(range(21)))
        self.assertIn("stage_a_provenance_only_json", self.contract["immutable_inputs"])

    def test_collision_pose_scope_is_exact(self) -> None:
        self.assertEqual(
            self.generator.COLLISION_POSES,
            {"lower_C001": (11, 12, 13, 14, 15, 16, 17),
             "lower_C013": (17, 18)},
        )
        self.assertEqual(self.contract["relief"]["motion_clearance_mm"], 0.5)

    def test_inverse_transform_order_is_translate_then_rotate(self) -> None:
        function = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_inverse_mapped_expanded_box"
        )
        calls = [
            node.func.attr for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"translate", "rotate"}
        ]
        self.assertEqual(calls, ["translate", "rotate"])

    def test_fail_closed_clearance_and_wall_gates_are_required(self) -> None:
        preflight = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "preflight"
        )
        text = ast.unparse(preflight)
        self.assertIn("minimum_distance >= clearance - dimensional_tolerance", text)
        self.assertIn("and clearance_gate", text)
        self.assertIn("and wall_gate", text)
        self.assertIn("applied_ligament_intersection <= epsilon", text)
        self.assertIn("protected_core_missing <= epsilon", text)

    def test_no_candidate_or_geometry_write_calls_exist(self) -> None:
        calls = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
        for forbidden in ("openDocument", "save", "saveAs", "export", "writeInventor"):
            self.assertNotIn(forbidden, calls)

    def test_cli_is_in_memory_only_and_report_is_fresh_tooling_json(self) -> None:
        self.assertIn('parser.add_argument("--in-memory-preflight"', self.source_text)
        self.assertIn("refusing to overwrite tooling evidence", self.source_text)
        self.assertIn("cat-head-cad-tooling", self.source_text)

    def test_integration_hold_does_not_invent_lower_receiver(self) -> None:
        holds = " ".join(self.contract["integration_holds"]).lower()
        self.assertIn("no unambiguous receiving-owner", holds)
        self.assertIn("out of scope", holds)
        self.assertNotIn("lower_c001 receiver", self.source_text.lower())

    def test_fresh_e1_files_are_hash_pinned(self) -> None:
        self.assertEqual(digest(SOURCE), EXPECTED_GENERATOR_SHA256)
        self.assertEqual(digest(CONTRACT), EXPECTED_CONTRACT_SHA256)


if __name__ == "__main__":
    unittest.main()
