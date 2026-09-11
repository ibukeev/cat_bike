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
VALIDATOR_PATH = CONTROL / "validate_c002_rounded_terminal_release_v2_002.py"
CONTRACT_PATH = (
    CONTROL
    / "v2/c002-rounded-terminal-profile-prototype-v2-release-validation-002.json"
)
ITERATION_PATH = CONTROL / "v2/c002-rounded-terminal-profile-prototype-v2.json"
INTERFACE_PATH = ROOT / "hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json"

MODULE: Any = None
if App is not None:
    sys.path.insert(0, str(CONTROL))
    SPEC = importlib.util.spec_from_file_location("c002_release_validation_002", VALIDATOR_PATH)
    assert SPEC is not None and SPEC.loader is not None
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@unittest.skipIf(App is None, "requires the pinned FreeCAD runtime")
class C002RoundedTerminalReleaseValidation002Tests(unittest.TestCase):
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
    ):
        points = [
            App.Vector(
                -20.0,
                center_v + radius * math.cos(2.0 * math.pi * index / sides),
                center_t + radius * math.sin(2.0 * math.pi * index / sides),
            )
            for index in range(sides)
        ]
        wire = Part.makePolygon([*points, points[0]])
        return Part.Face(wire).extrude(App.Vector(40.0, 0.0, 0.0))

    def fixture(self) -> dict[str, Any]:
        outer = Part.makeBox(30.0, 30.0, 32.0, App.Vector(-15.0, -15.0, -30.0))
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

        production_contract = load_json(CONTRACT_PATH)
        contract = copy.deepcopy(production_contract)
        parameters = copy.deepcopy(
            load_json(ITERATION_PATH)["allowed_mutations"][0]["parameters"]
        )
        interface = copy.deepcopy(load_json(INTERFACE_PATH))
        interface["rail_system"]["socket"][
            "expected_cross_bolt_angle_from_head_x_deg"
        ] = 0.0

        smooth_gauge = MODULE.axis_cylinder(
            2.25,
            contract["m4_inspection"]["axial_half_length_mm"],
            self.origin,
            self.axis_u,
            self.axis_t,
            -19.2,
        )
        observed = MODULE.shape_volume(snapshot.cut(candidate).common(smooth_gauge))
        contract["validation_001_disposition"][
            "reported_removed_inside_smooth_gauge_mm3"
        ] = observed
        return {
            "outer": outer,
            "old_void": old_void,
            "target_void": target_void,
            "snapshot": snapshot,
            "candidate": candidate,
            "parameters": parameters,
            "contract": contract,
            "interface": interface,
            "historical_observation": observed,
        }

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

    def assert_gate_failure(self, fixture: dict[str, Any], candidate, expected: set[str]):
        with self.assertRaises(MODULE.GateFailure) as caught:
            self.evaluate(fixture, candidate)
        self.assertIn(caught.exception.gate_id, expected)

    def test_authorized_widening_passes_and_reports_both_bearings(self):
        fixture = self.fixture()
        metrics = self.evaluate(fixture)
        overlap = metrics["authorized_profile_overlap"]
        self.assertEqual(
            overlap["classification"],
            "INTENTIONAL_20_50_TO_21_00_PROFILE_ENLARGEMENT_INTERSECTION",
        )
        self.assertAlmostEqual(
            overlap["measured_removed_inside_smooth_gauge_mm3"],
            fixture["historical_observation"],
            places=9,
        )
        self.assertLessEqual(
            overlap["removed_outside_authorized_target_void_mm3"],
            fixture["contract"]["tolerances"][
                "m4_removed_outside_authorized_cavity_volume_mm3_max"
            ],
        )
        signature = metrics["candidate_signature"]
        self.assertEqual(signature["facet_plane_count"], 16)
        self.assertAlmostEqual(signature["center_local_v_mm"], 0.0, places=7)
        self.assertAlmostEqual(signature["station_local_t_mm"], -19.2, places=7)
        self.assertAlmostEqual(signature["clearance_circumdiameter_mm"], 4.5, places=7)
        bearing = metrics["remaining_printed_bearing_length_wall_thickness"]
        self.assertAlmostEqual(
            bearing["left"]["minimum_printed_bearing_length_wall_thickness_mm"],
            4.5,
            places=7,
        )
        self.assertAlmostEqual(
            bearing["right"]["minimum_printed_bearing_length_wall_thickness_mm"],
            4.5,
            places=7,
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
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
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
                "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_AUTHORIZED_PROFILE_ENLARGEMENT",
                "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
                "M4_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
                "M4_CANDIDATE_MATCHES_FROZEN_INTERFACE",
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
        obstructed = fixture["candidate"].fuse(obstruction)
        self.assert_gate_failure(
            fixture,
            obstructed,
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

    def test_validation_001_tolerances_were_not_broadened(self):
        old_contract = load_json(
            CONTROL
            / "v2/c002-rounded-terminal-profile-prototype-v2-release-validation.json"
        )
        new_contract = load_json(CONTRACT_PATH)
        old_exact = old_contract["tolerances"]["m4_changed_volume_mm3_max"]
        strict_new = (
            "m4_original_void_refill_volume_mm3_max",
            "m4_removed_outside_authorized_cavity_volume_mm3_max",
            "m4_intentional_overlap_symmetric_difference_volume_mm3_max",
            "m4_historical_observation_volume_mm3_max",
            "m4_bearing_symmetric_difference_volume_mm3_max",
        )
        for name in strict_new:
            self.assertLessEqual(new_contract["tolerances"][name], old_exact)


if __name__ == "__main__":
    unittest.main()
