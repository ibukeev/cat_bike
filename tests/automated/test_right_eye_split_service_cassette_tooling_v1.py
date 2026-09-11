#!/usr/bin/env python3
"""Deterministic regressions for split-service cassette D tooling."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


generator = load(
    SOURCE / "generate_right_eye_split_service_cassette_prototype_v1.py",
    "_test_split_cassette_generator",
)
validator = load(
    SOURCE / "validate_right_eye_split_service_cassette_previsual_v1.py",
    "_test_split_cassette_validator",
)


LIMITS = {
    "maximum_unintended_positive_intersection_mm3": 0.000001,
    "minimum_non_mating_shell_clearance_mm": 0.3,
    "minimum_signed_mount_axis_dot": 0.999999,
    "minimum_bore_to_edge_material_mm": 3.5,
    "maximum_bore_center_axis_offset_mm": 0.00001,
}


def passing_observations():
    return {
        "topology": {
            "valid": True,
            "closed": True,
            "solid_count": 1,
            "self_intersection_count": 0,
        },
        "preservation": {
            "status": "PASS__READY_FOR_FIXED_VIEW_REVIEW",
            "candidate_hash_matches": True,
            "protected_difference_count": 0,
        },
        "shell": {
            "unresolved_count": 0,
            "maximum_intersection_mm3": 0.0,
            "cover_lip_maximum_intersection_mm3": 0.0,
            "cover_lip_uncovered_patch_area_mm2": 0.0,
            "minimum_clearance_mm": 0.3,
        },
        "containment": {
            "outside_authorized_envelope_mm3": 0.0,
            "missing_authorized_envelope_mm3": 0.0,
        },
        "exterior": {"non_bezel_exterior_mm3": 0.0},
        "view_frustum": {"hidden_structure_mm3": 0.0},
        "eye_motion": {
            "maximum_collision_mm3": 0.0,
            "samples_complete": True,
        },
        "cartridge_motion": {
            "maximum_collision_mm3": 0.0,
            "samples_complete": True,
        },
        "hardware": {
            "maximum_target_obstruction_mm3": 0.0,
            "maximum_cartridge_or_shell_obstruction_mm3": 0.0,
        },
        "mounts": {
            "minimum_signed_axis_dot": 1.0,
            "minimum_bearing_material_mm": 3.5,
            "maximum_center_offset_mm": 0.0,
        },
        "interfaces": {
            "diffuser_intersection_mm3": 0.0,
            "cartridge_intersection_mm3": 0.0,
            "cartridge_clearance_mm": 0.3,
            "required_cartridge_clearance_mm": 0.3,
            "continuous_rear_chamber_present": False,
            "rear_connector_boss_count": 0,
        },
    }


class SplitCassetteToolingTests(unittest.TestCase):
    def test_clean_lineage_identity(self):
        self.assertEqual(
            generator.DESIGN_ID, "right-eye-split-service-cassette-D"
        )
        self.assertEqual(
            generator.ITERATION_ID,
            "right-eye-split-service-cassette-prototype-v1",
        )

    def test_generator_does_not_reference_quarantined_candidate(self):
        source = Path(generator.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "right-eye-serviceable-fit-prototype-v6-attempt-002/candidate.FCStd",
            source,
        )
        self.assertNotIn("App.openDocument(str(candidate", source)

    def test_clearance_uses_direct_locally_inset_ring_and_ligaments(self):
        source = Path(generator.__file__).read_text(encoding="utf-8")
        self.assertEqual(
            generator.CONTACT_OWNER_KEYS,
            ("upper_C001", "lower_C001", "lower_C012", "lower_C013"),
        )
        self.assertNotIn("_sampled_clearance_directions", source)
        self.assertNotIn("four-owner-contact-aabb-clearance-v1", source)
        self.assertNotIn("Part.makeBox(", source)
        self.assertIn("locally-inset-aperture-lcs-ring-v1", source)
        self.assertIn("_explicit_mount_ligament", source)

    def test_cover_lip_is_exactly_trimmed_not_shell_mutated(self):
        source = Path(generator.__file__).read_text(encoding="utf-8")
        self.assertIn("raw.cut(lower_c001).removeSplitter()", source)
        self.assertNotIn("lower_c001.cut(raw)", source)
        self.assertIn("expected_hidden_attachment_trim_mm3", source)
        self.assertIn("uncovered_exterior_patch_area_mm2", source)

    def test_serial_relief_baseline_and_compact_geometry_are_pinned(self):
        import json

        contract = json.loads(
            (SOURCE / "v2/right-eye-split-service-cassette-prototype-v1.json").read_text()
        )
        parameters = contract["allowed_mutations"][0]["parameters"]
        self.assertEqual(contract["baseline_id"], "v34-lower-c001-relief-v1")
        self.assertEqual(
            parameters["geometry"]["front_optical_cassette"]
            ["rear_outer_vertex_insets_mm"],
            [2.0, 3.0, 3.0, 2.0],
        )
        self.assertEqual(
            parameters["geometry"]["rear_cartridge_interface"]
            ["cartridge_outer_vertex_insets_mm"],
            [1.2, 1.8, 1.8, 1.2],
        )
        lip = parameters["geometry"]["lower_c001_cover_lip"]
        self.assertEqual(lip["outward_reach_mm"], 0.58)
        self.assertEqual(lip["tangent_length_mm"], 3.0)
        self.assertEqual(lip["outward_axial_cover_mm"], 0.022)
        self.assertEqual(lip["minimum_printed_wall_mm"], 0.7)

        mount = parameters["geometry"]["head_mount"]
        self.assertEqual(mount["lower_c007_shell_face_retreat_mm"], 0.01)
        self.assertEqual(mount["lower_c007_clearance_owner"], "lower_C007")

    def test_lower_c007_retreat_is_lower_mount_face_only(self):
        source = Path(generator.__file__).read_text(encoding="utf-8")
        validator_source = Path(validator.__file__).read_text(encoding="utf-8")
        for text in (source, validator_source):
            self.assertIn('if role == "lower"', text)
            self.assertIn("pilot_length - shell_face_retreat", text)
            self.assertIn(
                'pilot_base = base + frame["bore_axis_vector"] * shell_face_retreat',
                text,
            )
        self.assertIn("else 0.0", source)

    def test_authoritative_inventory_resolves_all_components_including_lower_c009(self):
        components = []
        for key in generator.EXPECTED_SHELL_COMPONENT_KEYS:
            components.append(
                types.SimpleNamespace(
                    key=key,
                    shape=None if key == "lower_C009" else object(),
                    minimum_mm=[0.0, 0.0, 0.0],
                    maximum_mm=[1.0, 1.0, 1.0],
                    source=f"authoritative/{key}",
                )
            )
        resolved = generator._authoritative_shell_inventory(components)
        self.assertEqual(len(resolved), 101)
        self.assertEqual(set(resolved), set(generator.EXPECTED_SHELL_COMPONENT_KEYS))
        self.assertIn("lower_C009", resolved)
        self.assertEqual(resolved["lower_C009"].source, "authoritative/lower_C009")

    def test_all_pass(self):
        report = validator.evaluate(passing_observations(), LIMITS)
        self.assertEqual(
            report["status"], "PREVISUAL_PASS__READY_FOR_FIXED_VIEW_REVIEW"
        )
        self.assertIsNone(report["first_failed_gate"])

    def test_each_gate_fails_closed(self):
        mutations = {
            "G01": ("topology", "valid", False),
            "G02": ("preservation", "protected_difference_count", 1),
            "G03": ("shell", "maximum_intersection_mm3", 0.01),
            "G04": ("containment", "outside_authorized_envelope_mm3", 0.01),
            "G05": ("exterior", "non_bezel_exterior_mm3", 0.01),
            "G06": ("view_frustum", "hidden_structure_mm3", 0.01),
            "G07": ("eye_motion", "maximum_collision_mm3", 0.01),
            "G08": ("cartridge_motion", "maximum_collision_mm3", 0.01),
            "G09": ("hardware", "maximum_target_obstruction_mm3", 0.01),
            "G10": (
                "hardware",
                "maximum_cartridge_or_shell_obstruction_mm3",
                0.01,
            ),
            "G11": ("mounts", "minimum_signed_axis_dot", 0.9),
            "G12": ("interfaces", "cartridge_intersection_mm3", 0.01),
        }
        for gate, (section, key, value) in mutations.items():
            with self.subTest(gate=gate):
                observations = passing_observations()
                observations[section][key] = value
                report = validator.evaluate(observations, LIMITS)
                self.assertEqual(report["first_failed_gate"], gate)
                self.assertEqual(report["gates"][gate]["status"], "FAIL")

    def test_shell_clearance_fails_closed(self):
        observations = passing_observations()
        observations["shell"]["minimum_clearance_mm"] = 0.299
        self.assertEqual(
            validator.evaluate(observations, LIMITS)["first_failed_gate"],
            "G03",
        )

    def test_cover_lip_overlap_and_uncovered_patch_fail_closed(self):
        for key in (
            "cover_lip_maximum_intersection_mm3",
            "cover_lip_uncovered_patch_area_mm2",
        ):
            with self.subTest(key=key):
                observations = passing_observations()
                observations["shell"][key] = 0.01
                self.assertEqual(
                    validator.evaluate(observations, LIMITS)["first_failed_gate"],
                    "G03",
                )

    def test_missing_authorized_geometry_fails_closed(self):
        observations = passing_observations()
        observations["containment"]["missing_authorized_envelope_mm3"] = 0.01
        self.assertEqual(
            validator.evaluate(observations, LIMITS)["first_failed_gate"],
            "G04",
        )

    def test_cartridge_clearance_fails_closed(self):
        observations = passing_observations()
        observations["interfaces"]["cartridge_clearance_mm"] = 0.299
        self.assertEqual(
            validator.evaluate(observations, LIMITS)["first_failed_gate"],
            "G12",
        )

    def test_continuous_chamber_is_rejected(self):
        observations = passing_observations()
        observations["interfaces"]["continuous_rear_chamber_present"] = True
        self.assertEqual(
            validator.evaluate(observations, LIMITS)["first_failed_gate"],
            "G12",
        )

    def test_rear_connector_boss_is_rejected(self):
        observations = passing_observations()
        observations["interfaces"]["rear_connector_boss_count"] = 1
        self.assertEqual(
            validator.evaluate(observations, LIMITS)["first_failed_gate"],
            "G12",
        )


if __name__ == "__main__":
    unittest.main()
