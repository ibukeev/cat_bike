from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path
from typing import Any

try:
    import FreeCAD as App
    import Part
except ModuleNotFoundError:
    App = None
    Part = None


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
VALIDATOR_PATH = CONTROL / "validate_c002_rounded_terminal_release_v2_004.py"
CONTRACT_PATH = (
    CONTROL
    / "v2/c002-rounded-terminal-profile-prototype-v2-release-validation-004.json"
)
VALIDATION_003_CONTRACT_PATH = (
    CONTROL
    / "v2/c002-rounded-terminal-profile-prototype-v2-release-validation-003.json"
)
ITERATION_PATH = CONTROL / "v2/c002-rounded-terminal-profile-prototype-v2.json"
INTERFACE_PATH = (
    ROOT / "hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json"
)
SNAPSHOT_PATH = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "c002-rounded-terminal-profile-prototype-v2/no-op-snapshot.FCStd"
)
CANDIDATE_PATH = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "c002-rounded-terminal-profile-prototype-v2/candidate.FCStd"
)

MODULE: Any = None
if App is not None:
    sys.path.insert(0, str(CONTROL))
    SPEC = importlib.util.spec_from_file_location(
        "c002_release_validation_004", VALIDATOR_PATH
    )
    assert SPEC is not None and SPEC.loader is not None
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@unittest.skipIf(App is None, "requires the pinned FreeCAD runtime")
class C002RoundedTerminalReleaseValidation004Tests(unittest.TestCase):
    origin = None if App is None else App.Vector(0.0, 0.0, 0.0)
    axis_u = None if App is None else App.Vector(1.0, 0.0, 0.0)
    axis_v = None if App is None else App.Vector(0.0, 1.0, 0.0)
    axis_t = None if App is None else App.Vector(0.0, 0.0, 1.0)

    def regular_tunnel(
        self,
        radius: float = 2.25,
        center_v: float = 0.0,
        center_t: float = -19.2,
        sides: int = 16,
        phase_rad: float = 0.0,
    ):
        points = [
            App.Vector(
                -20.0,
                center_v
                + radius
                * math.cos(phase_rad + 2.0 * math.pi * index / sides),
                center_t
                + radius
                * math.sin(phase_rad + 2.0 * math.pi * index / sides),
            )
            for index in range(sides)
        ]
        wire = Part.makePolygon([*points, points[0]])
        return Part.Face(wire).extrude(App.Vector(40.0, 0.0, 0.0))

    def fixture(self) -> dict[str, Any]:
        outer = Part.makeBox(
            30.0, 30.0, 32.0, App.Vector(-15.0, -15.0, -30.0)
        )
        old_void = Part.makeBox(
            20.5,
            20.5,
            29.2,
            App.Vector(-10.25, -10.25, -29.2),
        )
        target_void = Part.makeBox(
            21.0,
            21.0,
            29.2,
            App.Vector(-10.5, -10.5, -29.2),
        )
        tunnel = self.regular_tunnel()
        snapshot = outer.cut(old_void).cut(tunnel)
        candidate = outer.cut(target_void).cut(tunnel)
        contract = copy.deepcopy(load_json(CONTRACT_PATH))
        parameters = copy.deepcopy(
            load_json(ITERATION_PATH)["allowed_mutations"][0]["parameters"]
        )
        interface = copy.deepcopy(load_json(INTERFACE_PATH))
        interface["rail_system"]["socket"][
            "expected_cross_bolt_angle_from_head_x_deg"
        ] = 0.0
        fixture = {
            "outer": outer,
            "old_void": old_void,
            "target_void": target_void,
            "snapshot": snapshot,
            "candidate": candidate,
            "parameters": parameters,
            "contract": contract,
            "interface": interface,
        }
        self.update_historical_observation(fixture)
        return fixture

    def smooth_gauge(self, fixture: dict[str, Any]):
        return MODULE.axis_cylinder(
            2.25,
            fixture["contract"]["m4_inspection"]["axial_half_length_mm"],
            self.origin,
            self.axis_u,
            self.axis_t,
            -19.2,
        )

    def update_historical_observation(self, fixture: dict[str, Any]) -> float:
        observed = MODULE.shape_volume(
            fixture["snapshot"]
            .cut(fixture["candidate"])
            .common(self.smooth_gauge(fixture))
        )
        fixture["contract"]["validation_001_disposition"][
            "reported_removed_inside_smooth_gauge_mm3"
        ] = observed
        return observed

    def evaluate(self, fixture: dict[str, Any], candidate=None) -> dict[str, Any]:
        return MODULE.evaluate_m4_preservation(
            fixture["snapshot"],
            fixture["candidate"] if candidate is None else candidate,
            fixture["target_void"],
            fixture["old_void"],
            self.origin,
            self.axis_u,
            self.axis_v,
            self.axis_t,
            fixture["parameters"],
            fixture["contract"],
            fixture["interface"],
        )

    def assert_gate_failure(
        self, fixture: dict[str, Any], candidate, expected: set[str]
    ):
        with self.assertRaises(MODULE.GateFailure) as caught:
            self.evaluate(fixture, candidate)
        self.assertIn(caught.exception.gate_id, expected)

    def test_authorized_widening_has_independent_left_and_right_signatures(self):
        fixture = self.fixture()
        metrics = self.evaluate(fixture)
        baseline = metrics["baseline_signature"]
        candidate = metrics["candidate_signature"]
        for side in ("left", "right"):
            self.assertEqual(baseline[side]["facet_plane_count"], 16)
            self.assertEqual(candidate[side]["facet_plane_count"], 16)
            self.assertAlmostEqual(
                candidate[side]["center_local_v_mm"], 0.0, places=7
            )
            self.assertAlmostEqual(
                candidate[side]["station_local_t_mm"], -19.2, places=7
            )
            self.assertAlmostEqual(
                candidate[side]["clearance_circumdiameter_mm"], 4.5, places=7
            )
            self.assertAlmostEqual(
                candidate[side]["remaining_printed_bearing"][
                    "minimum_printed_bearing_length_wall_thickness_mm"
                ],
                4.5,
                places=7,
            )

    def test_real_face150_face151_opposite_side_pattern_is_accepted(self):
        iteration = load_json(ITERATION_PATH)
        parameters = iteration["allowed_mutations"][0]["parameters"]
        contract = load_json(CONTRACT_PATH)
        interface = load_json(INTERFACE_PATH)
        origin, axis_u, axis_v, axis_t = MODULE.core.orthonormal_frame(parameters)
        station = float(parameters["m4_tunnel"]["station_t_mm"])
        radius = (
            float(parameters["m4_tunnel"]["nominal_clearance_diameter_mm"])
            / 2.0
        )
        snapshot_document = App.openDocument(str(SNAPSHOT_PATH))
        candidate_document = App.openDocument(str(CANDIDATE_PATH))
        try:
            snapshot_shape = snapshot_document.getObject(
                MODULE.core.TARGET_OBJECT
            ).Shape.copy()
            candidate_shape = candidate_document.getObject(
                MODULE.core.TARGET_OBJECT
            ).Shape.copy()
            baseline = MODULE.extract_bilateral_faceted_m4_signature(
                snapshot_shape,
                origin,
                axis_u,
                axis_v,
                axis_t,
                station,
                radius,
                float(parameters["profile"]["current_straight_across_flats_mm"])
                / 2.0,
                contract["m4_inspection"],
            )
            candidate = MODULE.extract_bilateral_faceted_m4_signature(
                candidate_shape,
                origin,
                axis_u,
                axis_v,
                axis_t,
                station,
                radius,
                float(parameters["profile"]["straight_across_flats_mm"])
                / 2.0,
                contract["m4_inspection"],
            )
            try:
                comparison = MODULE.compare_bilateral_signatures(
                    baseline,
                    candidate,
                    axis_u,
                    station,
                    2.0 * radius,
                    contract,
                    interface,
                )
            except MODULE.GateFailure as exc:
                self.fail(
                    json.dumps(
                        {
                            "failure": exc.record(),
                            "baseline_signature": baseline,
                            "candidate_signature": candidate,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
        finally:
            App.closeDocument(candidate_document.Name)
            App.closeDocument(snapshot_document.Name)

        self.assertIn("Face150", baseline["left"]["selected_face_identifiers"])
        self.assertIn("Face151", baseline["right"]["selected_face_identifiers"])
        self.assertNotIn("Face151", baseline["left"]["selected_face_identifiers"])
        self.assertNotIn("Face150", baseline["right"]["selected_face_identifiers"])
        self.assertEqual(baseline["left"]["facet_plane_count"], 16)
        self.assertEqual(baseline["right"]["facet_plane_count"], 16)
        self.assertEqual(set(comparison), {"left", "right"})

    def test_duplicate_parallel_facet_within_one_side_fails(self):
        fixture = self.fixture()
        groups = MODULE.partition_faceted_m4_bearing_faces(
            fixture["candidate"],
            self.origin,
            self.axis_u,
            self.axis_v,
            self.axis_t,
            -19.2,
            2.25,
            10.5,
            fixture["contract"]["m4_inspection"],
        )
        duplicate = dict(groups["left"][0])
        duplicate["face_identifier"] = "SyntheticDuplicate"
        duplicate["_axial_directions"] = list(
            groups["left"][0]["_axial_directions"]
        )
        with self.assertRaises(MODULE.GateFailure) as caught:
            MODULE.reconstruct_circumferential_side_signature(
                "left",
                [*groups["left"], duplicate],
                self.axis_u,
                self.axis_v,
                self.axis_t,
                -19.2,
                10.5,
                fixture["contract"]["m4_inspection"],
            )
        self.assertEqual(
            caught.exception.gate_id,
            "M4_LEFT_NO_DUPLICATE_OR_PARALLEL_FACETS",
        )

    def test_shifted_m4_tunnel_fails(self):
        fixture = self.fixture()
        shifted = fixture["outer"].cut(fixture["target_void"]).cut(
            self.regular_tunnel(center_v=0.20)
        )
        self.assert_gate_failure(
            fixture,
            shifted,
            {
                "M4_ORIGINAL_VOID_NOT_REFILLED",
                "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
                "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_SNAPSHOT_TARGET_VOID_INTERSECTION",
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_LEFT_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
                "M4_RIGHT_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
            },
        )

    def test_rotated_m4_tunnel_fails(self):
        fixture = self.fixture()
        rotated = fixture["outer"].cut(fixture["target_void"]).cut(
            self.regular_tunnel(phase_rad=math.radians(5.0))
        )
        self.assert_gate_failure(
            fixture,
            rotated,
            {
                "M4_ORIGINAL_VOID_NOT_REFILLED",
                "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
                "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_SNAPSHOT_TARGET_VOID_INTERSECTION",
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_LEFT_FACET_ORDER_AND_SUPPORT_MATCH_BASELINE",
                "M4_RIGHT_FACET_ORDER_AND_SUPPORT_MATCH_BASELINE",
            },
        )

    def test_resized_m4_tunnel_fails(self):
        fixture = self.fixture()
        resized = fixture["outer"].cut(fixture["target_void"]).cut(
            self.regular_tunnel(radius=2.40)
        )
        self.assert_gate_failure(
            fixture,
            resized,
            {
                "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
                "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_SNAPSHOT_TARGET_VOID_INTERSECTION",
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_LEFT_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
                "M4_RIGHT_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
                "M4_LEFT_CANDIDATE_MATCHES_FROZEN_INTERFACE",
                "M4_RIGHT_CANDIDATE_MATCHES_FROZEN_INTERFACE",
            },
        )

    def test_obstructed_m4_tunnel_fails(self):
        fixture = self.fixture()
        obstruction = Part.makeBox(
            1.0,
            1.0,
            1.0,
            App.Vector(11.0, -0.5, -19.7),
        )
        self.assert_gate_failure(
            fixture,
            fixture["candidate"].fuse(obstruction),
            {"M4_ORIGINAL_VOID_NOT_REFILLED"},
        )

    def test_refilled_m4_tunnel_fails(self):
        fixture = self.fixture()
        refilled = fixture["outer"].cut(fixture["target_void"])
        self.assert_gate_failure(
            fixture,
            refilled,
            {"M4_ORIGINAL_VOID_NOT_REFILLED"},
        )

    def test_missing_right_bearing_fails(self):
        fixture = self.fixture()
        right_bearing_removal = Part.makeBox(
            4.5,
            30.0,
            32.0,
            App.Vector(10.5, -15.0, -30.0),
        )
        missing = fixture["candidate"].cut(right_bearing_removal)
        self.assert_gate_failure(
            fixture,
            missing,
            {
                "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_RIGHT_FACETED_TUNNEL_SIGNATURE",
                "M4_RIGHT_BEARING_REMAINS_PRINTED",
            },
        )

    def test_all_determinable_gate_collector_does_not_hide_later_results(self):
        collector = MODULE.GateCollector()
        collector.require(False, "EARLY_INDEPENDENT_FAILURE", 1, 0)
        collector.require(True, "LATER_INDEPENDENT_PASS", 2, 2)
        self.assertEqual(
            [item["status"] for item in collector.records], ["FAIL", "PASS"]
        )

    def test_validation_003_physical_tolerances_are_unchanged(self):
        validation_003 = load_json(VALIDATION_003_CONTRACT_PATH)
        validation_004 = load_json(CONTRACT_PATH)
        self.assertEqual(
            validation_004["tolerances"], validation_003["tolerances"]
        )
        self.assertEqual(
            validation_004["m4_inspection"], validation_003["m4_inspection"]
        )
        self.assertEqual(
            validation_004["validation_003_disposition"]["classification"],
            "VALIDATOR_DEFECT__BASELINE_AXIAL_FACE_FRAGMENT_PAIRING",
        )
        self.assertEqual(
            validation_004["validation_003_disposition"][
                "candidate_disposition"
            ],
            "CANDIDATE_UNCHANGED",
        )


if __name__ == "__main__":
    unittest.main()
