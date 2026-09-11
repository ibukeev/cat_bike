#!/usr/bin/env python3
"""Equivalence and execution regressions for eye-validator revision 001."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTROL_DIR = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
ORIGINAL_PATH = CONTROL_DIR / (
    "validate_right_eye_serviceable_fit_previsual_v6_attempt_002.py"
)
REVISION_PATH = CONTROL_DIR / (
    "validate_right_eye_serviceable_fit_previsual_v6_attempt_002_"
    "validator_revision_001.py"
)
CONTRACT_PATH = CONTROL_DIR / (
    "v2/right-eye-serviceable-fit-prototype-v6-attempt-002.json"
)
PRESERVATION_PATH = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-serviceable-fit-prototype-v6-attempt-002/"
    "preservation-report.json"
)
CANDIDATE_PATH = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-serviceable-fit-prototype-v6-attempt-002/candidate.FCStd"
)

sys.path.insert(0, str(CONTROL_DIR))
import validate_right_eye_serviceable_fit_previsual_v6_attempt_002 as immutable  # noqa: E402
import validate_right_eye_serviceable_fit_previsual_v6_attempt_002_validator_revision_001 as revision  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def passing_observations() -> dict[str, Any]:
    hardware = {
        role: {
            "bolt_length_range_mm": [8.0, 10.0],
            "washer_count": 2,
            "washer_od_mm": 7.0,
            "washer_thickness_mm": 0.8,
            "nyloc_od_mm": 7.0,
            "nyloc_length_mm": 5.0,
            "tool_diameter_mm": 8.0,
            "tool_length_mm": 20.0,
            "max_path_collision_mm3": 0.0,
            "max_prohibited_intersection_mm3": 0.0,
            "behind_flange_blocking_volume_mm3": 0.0,
        }
        for role in ("upper", "lower")
    }
    return {
        "topology": {
            "valid": True,
            "closed": True,
            "solid_count": 1,
            "connected_component_count": 1,
            "self_intersection_count": 0,
        },
        "preservation": {
            "status": "PASS__READY_FOR_FIXED_VIEW_REVIEW",
            "candidate_hash_matches": True,
            "protected_difference_count": 0,
        },
        "shell_matrix": {
            "component_count": 101,
            "unresolved_error_count": 0,
            "maximum_positive_intersection_mm3": 0.0,
            "known_f19_intersections_mm3": {
                "upper_C001": 0.0,
                "lower_C001": 0.0,
                "lower_C012": 0.0,
                "lower_C013": 0.0,
            },
            "clearance_unresolved_error_count": 0,
            "minimum_non_mating_clearance_mm": 0.5,
            "upper_c001_clearance_outside_authorized_interfaces_mm": 4.0,
        },
        "containment": {
            "outside_permitted_envelope_mm3": 0.0,
            "mount_related_outside_volume_mm3": 0.0,
        },
        "exterior_aperture": {"non_bezel_exterior_volume_mm3": 0.0},
        "view_frustum": {"mount_chamber_cap_volume_mm3": 0.0},
        "eye_insertion_removal": {
            "complete_sample_set": True,
            "maximum_unintended_collision_mm3": 0.0,
        },
        "rear_cap_sweep": {
            "complete_sample_set": True,
            "maximum_unintended_collision_mm3": 0.0,
        },
        "hardware_access": hardware,
        "mount_integrity": {
            role: {
                "direct_owner_root_engagement_mm3": 80.0,
                "bore_to_edge_material_mm": 3.5,
                "head_mount_mating_gap_mm": 0.3,
            }
            for role in ("upper", "lower")
        },
        "datum_and_interface_preservation": {
            "aperture_exact": True,
            "module_lcs_exact": True,
            "mount_datums_exact": True,
            "signed_mount_frame_pass": True,
            "signed_mount_frames_exact": True,
            "connector_dimensions_exact": True,
            "rear_cap_root_projection_pass": True,
            "rear_cap_interface_pass": True,
            "diffuser_interface_pass": True,
            "minimum_wall_pass": True,
        },
    }


class FakeBox:
    def __init__(self, minimum: tuple[float, float, float], maximum: tuple[float, float, float]) -> None:
        self.XMin, self.YMin, self.ZMin = minimum
        self.XMax, self.YMax, self.ZMax = maximum


class FakeCommon:
    def __init__(self, volume: float, bounds: FakeBox) -> None:
        self.Volume = volume
        self.BoundBox = bounds

    def isNull(self) -> bool:
        return False


class FakeShape:
    def __init__(
        self,
        minimum: tuple[float, float, float],
        maximum: tuple[float, float, float],
        *,
        common_volume: float = 0.0,
        distance: float = 0.0,
    ) -> None:
        self._box = FakeBox(minimum, maximum)
        self.common_volume = common_volume
        self.distance = distance
        self.common_calls = 0
        self.distance_calls = 0
        self.bound_box_reads = 0

    @property
    def BoundBox(self) -> FakeBox:
        self.bound_box_reads += 1
        return self._box

    def isNull(self) -> bool:
        return False

    def common(self, other: Any) -> FakeCommon:
        del other
        self.common_calls += 1
        return FakeCommon(self.common_volume, self._box)

    def distToShape(self, other: Any) -> tuple[float, list[Any], list[Any]]:
        del other
        self.distance_calls += 1
        return self.distance, [], []


class RightEyeValidatorRevision001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CONTRACT_PATH)
        cls.parameters = cls.contract["allowed_mutations"][0]["parameters"]
        cls.limits = cls.parameters["validation_contract"]["limits"]

    def evaluate_both(self, observations: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            immutable.evaluate_previsual_observations(observations, self.limits),
            revision.evaluate_previsual_observations(observations, self.limits),
        )

    def test_immutable_input_hashes_are_exact(self) -> None:
        self.assertEqual(sha256_file(ORIGINAL_PATH), revision.ORIGINAL_VALIDATOR_SHA256)
        self.assertEqual(sha256_file(CONTRACT_PATH), revision.ORIGINAL_CONTRACT_SHA256)
        self.assertEqual(sha256_file(CANDIDATE_PATH), revision.HELD_CANDIDATE_SHA256)
        self.assertEqual(
            sha256_file(PRESERVATION_PATH), revision.PRESERVATION_REPORT_SHA256
        )

    def test_revision_uses_the_original_evaluator_function_object(self) -> None:
        self.assertIs(
            revision.evaluate_previsual_observations,
            revision.original.evaluate_previsual_observations,
        )

    def test_clear_observations_are_exactly_gate_equivalent(self) -> None:
        original_result, revised_result = self.evaluate_both(passing_observations())
        self.assertEqual(original_result, revised_result)
        self.assertTrue(revised_result["passed"])
        self.assertEqual(len(revised_result["gates"]), 12)
        self.assertTrue(all(revised_result["gates"].values()))

    def test_every_single_gate_failure_is_exactly_equivalent(self) -> None:
        fixtures = {
            "G01_ONE_VALID_CLOSED_CONNECTED_TARGET": (
                "topology",
                "valid",
                False,
            ),
            "G02_EXACT_NON_TARGET_PRESERVATION": (
                "preservation",
                "protected_difference_count",
                1,
            ),
            "G03_FULL_101_SHELL_MATRIX": (
                "shell_matrix",
                "maximum_positive_intersection_mm3",
                0.01,
            ),
            "G04_PERMITTED_EYE_ENVELOPE": (
                "containment",
                "outside_permitted_envelope_mm3",
                0.01,
            ),
            "G05_ONLY_BEZEL_EXTERIOR": (
                "exterior_aperture",
                "non_bezel_exterior_volume_mm3",
                0.01,
            ),
            "G06_ZERO_APERTURE_VIEW_FRUSTUM_OCCUPANCY": (
                "view_frustum",
                "mount_chamber_cap_volume_mm3",
                0.01,
            ),
            "G07_EYE_INSERTION_AND_REMOVAL": (
                "eye_insertion_removal",
                "maximum_unintended_collision_mm3",
                0.01,
            ),
            "G08_REAR_CAP_SEATING_AND_REMOVAL": (
                "rear_cap_sweep",
                "maximum_unintended_collision_mm3",
                0.01,
            ),
            "G09_BOTH_FASTENER_AND_TOOL_PATHS": (
                "hardware_access",
                "upper.max_path_collision_mm3",
                0.01,
            ),
            "G10_HARDWARE_AVOIDS_PROHIBITED_GEOMETRY": (
                "hardware_access",
                "upper.max_prohibited_intersection_mm3",
                0.01,
            ),
            "G11_MOUNT_ROOT_AND_EDGE_MATERIAL": (
                "mount_integrity",
                "upper.direct_owner_root_engagement_mm3",
                79.99,
            ),
            "G12_DATUM_INTERFACE_AND_WALL_PRESERVATION": (
                "datum_and_interface_preservation",
                "aperture_exact",
                False,
            ),
        }
        for expected_gate, (section, field, value) in fixtures.items():
            with self.subTest(gate=expected_gate):
                observations = copy.deepcopy(passing_observations())
                if "." in field:
                    first, second = field.split(".", 1)
                    observations[section][first][second] = value
                else:
                    observations[section][field] = value
                original_result, revised_result = self.evaluate_both(observations)
                self.assertEqual(original_result, revised_result)
                self.assertEqual(revised_result["failed_gates"], [expected_gate])

    def test_deliberately_clear_fake_fixture_skips_common_and_distance(self) -> None:
        subject = FakeShape((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), distance=9.0)
        obstacle_shape = FakeShape((10.0, 0.0, 0.0), (11.0, 1.0, 1.0))
        legacy_component = immutable.ShellComponent(
            "clear", obstacle_shape, [10.0, 0.0, 0.0], [11.0, 1.0, 1.0], "fixture"
        )
        legacy_record = immutable._intersection_record(subject, legacy_component, 1.0e-6)
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        revised_record = revision.collision_only_record(
            subject,
            revision.PreparedObstacle(
                "clear",
                obstacle_shape,
                revision.Bounds3D((10.0, 0.0, 0.0), (11.0, 1.0, 1.0)),
                "fixture",
            ),
            1.0e-6,
            diagnostics,
            shape_bounds=revision.Bounds3D((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        )
        self.assertEqual(legacy_record["intersection_volume_mm3"], 0.0)
        self.assertEqual(revised_record["intersection_volume_mm3"], 0.0)
        self.assertFalse(revised_record["unresolved"])
        self.assertEqual(subject.common_calls, 0)
        self.assertEqual(subject.distance_calls, 1)
        self.assertEqual(diagnostics.counters["exact_common_volume_calls"], 0)
        self.assertEqual(diagnostics.counters["exact_distance_calls"], 0)
        self.assertEqual(
            diagnostics.counters["collision_aabb_disjoint_zero_returns"], 1
        )

    def test_deliberately_colliding_fake_fixture_uses_common_not_distance(self) -> None:
        subject = FakeShape(
            (0.0, 0.0, 0.0),
            (2.0, 2.0, 2.0),
            common_volume=1.25,
            distance=0.0,
        )
        obstacle_shape = FakeShape((1.0, 1.0, 1.0), (3.0, 3.0, 3.0))
        legacy_component = immutable.ShellComponent(
            "collision",
            obstacle_shape,
            [1.0, 1.0, 1.0],
            [3.0, 3.0, 3.0],
            "fixture",
        )
        legacy_record = immutable._intersection_record(subject, legacy_component, 1.0e-6)
        legacy_distance_calls = subject.distance_calls
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        revised_record = revision.collision_only_record(
            subject,
            revision.PreparedObstacle(
                "collision",
                obstacle_shape,
                revision.Bounds3D((1.0, 1.0, 1.0), (3.0, 3.0, 3.0)),
                "fixture",
            ),
            1.0e-6,
            diagnostics,
            shape_bounds=revision.Bounds3D((0.0, 0.0, 0.0), (2.0, 2.0, 2.0)),
        )
        self.assertEqual(
            legacy_record["intersection_volume_mm3"],
            revised_record["intersection_volume_mm3"],
        )
        self.assertEqual(revised_record["intersection_volume_mm3"], 1.25)
        self.assertEqual(legacy_distance_calls, 1)
        self.assertEqual(subject.distance_calls, legacy_distance_calls)
        self.assertEqual(diagnostics.counters["exact_common_volume_calls"], 1)
        self.assertEqual(diagnostics.counters["exact_distance_calls"], 0)

    def test_clearance_path_retains_exact_distance(self) -> None:
        subject = FakeShape((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), distance=9.0)
        obstacle_shape = FakeShape((10.0, 0.0, 0.0), (11.0, 1.0, 1.0))
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        record = revision.clearance_distance_record(
            subject,
            revision.PreparedObstacle(
                "clearance",
                obstacle_shape,
                revision.Bounds3D((10.0, 0.0, 0.0), (11.0, 1.0, 1.0)),
                "fixture",
            ),
            diagnostics,
        )
        self.assertEqual(record["distance_mm"], 9.0)
        self.assertEqual(subject.distance_calls, 1)
        self.assertEqual(diagnostics.counters["exact_distance_calls"], 1)

    def test_clearance_aabb_lower_bound_proves_gate_without_distance(self) -> None:
        subject = FakeShape((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), distance=9.0)
        obstacle_shape = FakeShape((10.0, 0.0, 0.0), (11.0, 1.0, 1.0))
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        record = revision.clearance_distance_record(
            subject,
            revision.PreparedObstacle(
                "clearance-gate",
                obstacle_shape,
                revision.Bounds3D((10.0, 0.0, 0.0), (11.0, 1.0, 1.0)),
                "fixture",
            ),
            diagnostics,
            shape_bounds=revision.Bounds3D(
                (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
            ),
            minimum_required_mm=0.5,
        )
        self.assertGreaterEqual(record["distance_mm"], 0.5)
        self.assertEqual(subject.distance_calls, 0)
        self.assertEqual(diagnostics.counters["exact_distance_calls"], 0)
        self.assertEqual(diagnostics.counters["clearance_aabb_gate_proofs"], 1)

    def test_cached_obstacle_bounds_are_reused_without_shape_bound_reads(self) -> None:
        subject = FakeShape((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        obstacle_shape = FakeShape((10.0, 0.0, 0.0), (11.0, 1.0, 1.0))
        obstacle = revision.PreparedObstacle(
            "cached",
            obstacle_shape,
            revision.Bounds3D((10.0, 0.0, 0.0), (11.0, 1.0, 1.0)),
            "fixture",
        )
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        subject_bounds = revision.Bounds3D((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        for _ in range(25):
            revision.collision_only_record(
                subject,
                obstacle,
                1.0e-6,
                diagnostics,
                shape_bounds=subject_bounds,
            )
        self.assertEqual(obstacle_shape.bound_box_reads, 0)
        self.assertEqual(
            diagnostics.counters["collision_aabb_disjoint_zero_returns"], 25
        )

    def test_actual_occt_clear_and_colliding_fixtures_match_exact_volume(self) -> None:
        try:
            import FreeCAD as App  # type: ignore
            import Part  # type: ignore
        except ImportError:
            self.skipTest("pinned FreeCAD runtime required for OCCT fixtures")
        subject = Part.makeBox(10.0, 10.0, 10.0)
        clear = Part.makeBox(10.0, 10.0, 10.0, App.Vector(20.0, 0.0, 0.0))
        colliding = Part.makeBox(10.0, 10.0, 10.0, App.Vector(5.0, 5.0, 5.0))
        epsilon = 1.0e-6
        subject_bounds = revision.bounds_from_shape(subject)
        for name, shape, expected_volume in (
            ("clear", clear, 0.0),
            ("colliding", colliding, 125.0),
        ):
            with self.subTest(fixture=name):
                box = shape.BoundBox
                legacy_component = immutable.ShellComponent(
                    name,
                    shape,
                    [box.XMin, box.YMin, box.ZMin],
                    [box.XMax, box.YMax, box.ZMax],
                    "occt-fixture",
                )
                legacy_record = immutable._intersection_record(
                    subject, legacy_component, epsilon
                )
                diagnostics = revision.RunDiagnostics(emit_progress=False)
                revised_record = revision.collision_only_record(
                    subject,
                    revision.PreparedObstacle(
                        name,
                        shape,
                        revision.bounds_from_limits(
                            legacy_component.minimum_mm,
                            legacy_component.maximum_mm,
                        ),
                        "occt-fixture",
                    ),
                    epsilon,
                    diagnostics,
                    shape_bounds=subject_bounds,
                )
                self.assertAlmostEqual(
                    float(legacy_record["intersection_volume_mm3"]),
                    expected_volume,
                    places=9,
                )
                self.assertAlmostEqual(
                    float(revised_record["intersection_volume_mm3"]),
                    expected_volume,
                    places=9,
                )
                self.assertEqual(diagnostics.counters["exact_distance_calls"], 0)

    def test_actual_occt_batched_gate_is_exact_for_clear_collision_and_subepsilon_sum(self) -> None:
        try:
            import FreeCAD as App  # type: ignore
            import Part  # type: ignore
        except ImportError:
            self.skipTest("pinned FreeCAD runtime required for OCCT fixtures")
        epsilon = 1.0e-6
        subject = Part.makeBox(10.0, 10.0, 10.0)

        def obstacle(name: str, shape: Any) -> revision.PreparedObstacle:
            return revision.PreparedObstacle(
                name,
                shape,
                revision.bounds_from_shape(shape),
                name,
            )

        clear = Part.makeBox(1.0, 1.0, 1.0, App.Vector(20.0, 0.0, 0.0))
        collision = Part.makeBox(
            1.0, 1.0, 1.0, App.Vector(9.5, 9.5, 9.5)
        )
        diagnostics = revision.RunDiagnostics(emit_progress=False)
        clear_result = revision.batched_collision_gate_maximum(
            subject,
            revision.bounds_from_shape(subject),
            [obstacle("clear", clear)],
            epsilon,
            diagnostics,
            Part,
        )
        self.assertEqual(clear_result["maximum_collision_mm3"], 0.0)
        collision_result = revision.batched_collision_gate_maximum(
            subject,
            revision.bounds_from_shape(subject),
            [obstacle("collision", collision)],
            epsilon,
            diagnostics,
            Part,
        )
        self.assertAlmostEqual(
            collision_result["maximum_collision_mm3"], 0.125, places=9
        )

        # Two distinct 0.75e-6 mm3 contacts sum above epsilon. The batch must
        # refine them and preserve the original per-obstacle PASS predicate.
        tiny_first = Part.makeBox(
            0.01, 0.01, 0.0075, App.Vector(1.0, 1.0, 1.0)
        )
        tiny_second = Part.makeBox(
            0.01, 0.01, 0.0075, App.Vector(2.0, 2.0, 2.0)
        )
        subepsilon_result = revision.batched_collision_gate_maximum(
            subject,
            revision.bounds_from_shape(subject),
            [
                obstacle("tiny-first", tiny_first),
                obstacle("tiny-second", tiny_second),
            ],
            epsilon,
            diagnostics,
            Part,
        )
        self.assertGreater(
            subepsilon_result["aggregate_common_upper_bound_mm3"], epsilon
        )
        self.assertLessEqual(
            subepsilon_result["maximum_collision_mm3"], epsilon
        )
        self.assertEqual(subepsilon_result["refined_pair_count"], 2)

        witness = collision_result["_failure_witness"]
        reused_result = revision.batched_collision_gate_maximum(
            subject,
            revision.bounds_from_shape(subject),
            [obstacle("collision", collision)],
            epsilon,
            diagnostics,
            Part,
            preferred_witness=witness,
        )
        self.assertTrue(reused_result["witness_reused"])
        self.assertAlmostEqual(
            reused_result["maximum_collision_mm3"], 0.125, places=9
        )
        self.assertEqual(
            diagnostics.counters["collision_witness_reuse_gate_failures"], 1
        )

    def test_clearance_short_circuit_is_exactly_gate_equivalent(self) -> None:
        passing_shell = passing_observations()["shell_matrix"]
        epsilon = float(
            self.limits["maximum_unintended_positive_intersection_mm3"]
        )
        self.assertTrue(
            revision.shell_collision_prerequisites_allow_clearance(
                passing_shell, epsilon
            )
        )

        observations = passing_observations()
        observations["shell_matrix"].update(
            {
                "maximum_positive_intersection_mm3": epsilon * 2.0,
                "clearance_unresolved_error_count": 1,
                "minimum_non_mating_clearance_mm": -float("inf"),
                "upper_c001_clearance_outside_authorized_interfaces_mm": (
                    -float("inf")
                ),
            }
        )
        self.assertFalse(
            revision.shell_collision_prerequisites_allow_clearance(
                observations["shell_matrix"], epsilon
            )
        )
        original_result, revised_result = self.evaluate_both(observations)
        self.assertEqual(original_result, revised_result)
        self.assertEqual(
            revised_result["failed_gates"], ["G03_FULL_101_SHELL_MATRIX"]
        )

    def test_actual_occt_chunked_sweeps_are_exactly_gate_equivalent(self) -> None:
        try:
            import FreeCAD as App  # type: ignore
            import Part  # type: ignore
        except ImportError:
            self.skipTest("pinned FreeCAD runtime required for OCCT fixtures")
        epsilon = 1.0e-6

        clear_moving = Part.makeSphere(1.0)
        clear_obstacle_shape = Part.makeBox(
            0.05, 0.05, 0.05, App.Vector(0.9, 0.9, 0.9)
        )
        clear_obstacle = revision.PreparedObstacle(
            "clear-corner",
            clear_obstacle_shape,
            revision.bounds_from_shape(clear_obstacle_shape),
            "occt-fixture",
        )
        clear_translations = [App.Vector(value, 0.0, 0.0) for value in (0.0, 0.1, 0.2, 0.3)]
        clear_diagnostics = revision.RunDiagnostics(emit_progress=False)
        clear_result = revision.measure_sweep(
            clear_moving,
            clear_translations,
            [clear_obstacle],
            epsilon,
            clear_diagnostics,
            Part,
            motion_name="clear_fixture",
            group_size=4,
        )
        clear_legacy_maximum = max(
            float(
                immutable._translated(clear_moving, translation)
                .common(clear_obstacle_shape)
                .Volume
            )
            for translation in clear_translations
        )
        self.assertLessEqual(clear_legacy_maximum, epsilon)
        self.assertLessEqual(
            clear_result["maximum_unintended_collision_mm3"], epsilon
        )
        self.assertEqual(clear_result["sample_count"], 4)
        self.assertTrue(clear_result["all_required_sample_positions_enumerated"])
        self.assertEqual(
            clear_diagnostics.counters["sweep_group_upper_bound_calls"], 1
        )

        collision_moving = Part.makeBox(1.0, 1.0, 1.0)
        collision_obstacle_shape = Part.makeBox(
            1.0, 1.0, 1.0, App.Vector(2.5, 0.0, 0.0)
        )
        collision_obstacle = revision.PreparedObstacle(
            "deliberate-collision",
            collision_obstacle_shape,
            revision.bounds_from_shape(collision_obstacle_shape),
            "occt-fixture",
        )
        collision_translations = [
            App.Vector(value, 0.0, 0.0) for value in (0.0, 2.0, 4.0, 6.0)
        ]
        collision_diagnostics = revision.RunDiagnostics(emit_progress=False)
        collision_result = revision.measure_sweep(
            collision_moving,
            collision_translations,
            [collision_obstacle],
            epsilon,
            collision_diagnostics,
            Part,
            motion_name="collision_fixture",
            group_size=4,
        )
        collision_legacy_maximum = max(
            float(
                immutable._translated(collision_moving, translation)
                .common(collision_obstacle_shape)
                .Volume
            )
            for translation in collision_translations
        )
        self.assertGreater(collision_legacy_maximum, epsilon)
        self.assertGreater(
            collision_result["maximum_unintended_collision_mm3"], epsilon
        )
        self.assertEqual(collision_result["sample_count"], 4)
        self.assertTrue(
            collision_result["all_required_sample_positions_enumerated"]
        )
        self.assertEqual(
            collision_diagnostics.counters[
                "motion_gate_short_circuited_samples"
            ],
            2,
        )

    def test_collision_only_function_contains_no_distance_call(self) -> None:
        collision_source = inspect.getsource(revision.collision_only_record)
        clearance_source = inspect.getsource(revision.clearance_distance_record)
        self.assertNotIn("distToShape", collision_source)
        self.assertIn("distToShape", clearance_source)

    def test_batched_gate_refines_only_when_aggregate_exceeds_epsilon(self) -> None:
        source = inspect.getsource(revision.batched_collision_gate_maximum)
        self.assertIn("aggregate_upper_bound <= epsilon", source)
        self.assertIn("batched_common_refinements", source)
        self.assertIn("volume > epsilon", source)

    def test_all_required_named_stages_are_present(self) -> None:
        source = REVISION_PATH.read_text(encoding="utf-8")
        stages = [
            "S00_CONTRACT_AND_DATUM_PREFLIGHT",
            "S01_REFERENCE_GEOMETRY",
            "S02_LOAD_101_SHELL_COMPONENTS",
            "S03_LOAD_PROTECTED_OBSTACLES",
            "S04_OPEN_HELD_CANDIDATE_READ_ONLY",
            "S05_TOPOLOGY_AND_PRESERVATION",
            "S06_SHELL_COLLISION_MATRIX",
            "S07_SHELL_CLEARANCE_DISTANCE",
            "S08_CONTAINMENT_AND_MOUNT_COLLISION",
            "S09_EXTERIOR_OCCUPANCY",
            "S10_VIEW_FRUSTUM",
            "S11_LOAD_HASH_PINNED_FIT_REFERENCES",
            "S12_EYE_MOTION_41_SAMPLES",
            "S13_REAR_CAP_MOTION_31_SAMPLES",
            "S14_HARDWARE_ACCESS",
            "S15_MOUNT_INTEGRITY",
            "S16_DATUM_INTERFACE_AND_WALL",
            "S17_EXACT_ORIGINAL_G01_G12_EVALUATOR",
        ]
        for stage in stages:
            self.assertIn(stage, source)

    def test_motion_workloads_and_physical_contract_are_unchanged(self) -> None:
        motion = self.parameters["validation_contract"]["motion"]
        self.assertEqual(motion["eye_sweep_samples"], 41)
        self.assertEqual(motion["rear_cap_sweep_samples"], 31)
        self.assertEqual(revision.REQUIRED_EYE_SAMPLES, 41)
        self.assertEqual(revision.REQUIRED_REAR_CAP_SAMPLES, 31)
        self.assertEqual(self.contract["iteration_id"], immutable.ITERATION_ID)
        self.assertEqual(
            self.parameters["design_control"]["design_signature"]["sha256"],
            "4a59901cbf4e2f5ebda9b5bb920c15935ccb03126a92564e4967b474612cc6a6",
        )

    def test_preflight_report_schema_suppresses_gate_publication(self) -> None:
        source = REVISION_PATH.read_text(encoding="utf-8")
        self.assertIn('"gate_verdict_publication_suppressed": True', source)
        self.assertIn('"published_gate_fields": []', source)
        self.assertIn("del observations, evaluation", source)

    def test_clearance_stage_reuses_masks_and_conservative_gate_proofs(self) -> None:
        source = inspect.getsource(revision.measure_previsual)
        self.assertIn("authorized_mask_component_cuts_avoided", source)
        self.assertIn("upper_c001_redundant_boolean_pairs_avoided", source)
        self.assertIn("minimum_required_mm=shell_clearance_requirement", source)
        self.assertIn(
            "clearance_stage_short_circuited_after_collision_failure", source
        )

    def test_validator_has_no_candidate_save_or_generator_invocation(self) -> None:
        tree = ast.parse(REVISION_PATH.read_text(encoding="utf-8"))
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("saveAs", called_attributes)
        self.assertNotIn("save", called_attributes)
        self.assertNotIn("run_iteration_v2", called_names)
        self.assertNotIn("generate_right_eye_serviceable_fit", called_names)

    def test_authorization_gate_requires_fresh_output_and_one_invocation(self) -> None:
        source = inspect.getsource(revision.validate_authorization)
        self.assertIn("AUTHORIZED__NOT_INVOKED", source)
        self.assertIn("max_invocations", source)
        self.assertIn("report_path.exists()", source)
        self.assertIn("performance preflight exceeded 180-second target", source)


if __name__ == "__main__":
    unittest.main()
