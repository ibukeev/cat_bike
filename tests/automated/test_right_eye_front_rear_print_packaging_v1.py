import copy
import importlib.util
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source"
    / "cad-change-control/tooling-only/right-eye-front-rear-print-packaging-v1"
)
CONTRACT_PATH = PACKAGE / "contract.json"
SPEC = importlib.util.spec_from_file_location("right_eye_print_packaging_preflight", PACKAGE / "preflight.py")
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class RightEyeFrontLensPrintPackagingV1Test(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_only_tooling_is_ready(self):
        self.assertEqual(PREFLIGHT.contract_errors(self.contract, CONTRACT_PATH), [])

    def test_release_ready_passes_only_with_pinned_print_source(self):
        errors = PREFLIGHT.release_errors(self.contract, CONTRACT_PATH)
        self.assertEqual(errors, [])
        fixture = copy.deepcopy(self.contract)
        fixture["source_release"]["fcstd_sha256"] = "0" * 64
        self.assertTrue(PREFLIGHT.release_errors(fixture, CONTRACT_PATH))

    def test_exactly_two_parts_and_no_mount_hardware_contract(self):
        self.assertEqual(
            [item["id"] for item in self.contract["source_release"]["parts"]],
            ["front_carrier", "translucent_eye_glass"],
        )
        encoded = json.dumps(self.contract).lower()
        self.assertNotIn("rear_cartridge", encoded)
        self.assertNotIn("m2.5", encoded)
        self.assertNotIn("m2_5", encoded)
        self.assertNotIn("mount_datums", encoded)

    def test_wall_and_lens_thickness_cannot_be_relaxed(self):
        for key, value in (("minimum_wall_mm", 0.699), ("eye_glass_thickness_mm", 0.901)):
            fixture = copy.deepcopy(self.contract)
            fixture["geometry_gates"][key] = value
            with self.subTest(key=key):
                self.assertTrue(PREFLIGHT.contract_errors(fixture, CONTRACT_PATH))

    def test_mesh_repair_scale_and_topology_are_fail_closed(self):
        fixtures = (
            ("allow_automatic_repair", True),
            ("scale", 0.99),
            ("maximum_boundary_edges", 1),
            ("maximum_nonmanifold_edges", 1),
            ("maximum_duplicate_facets", 1),
            ("required_connected_components_each", 2),
        )
        for key, value in fixtures:
            fixture = copy.deepcopy(self.contract)
            fixture["mesh_gates"][key] = value
            with self.subTest(key=key):
                self.assertTrue(PREFLIGHT.contract_errors(fixture, CONTRACT_PATH))

    def test_manufacturing_conditioner_is_exact_and_fail_closed(self):
        values = self.contract["mesh_gates"][
            "front_carrier_manufacturing_conditioning"
        ]
        self.assertEqual(
            values["algorithm_id"],
            "micron-weld-and-zero-area-filter-v1",
        )
        for key, value in (
            ("maximum_weld_distance_mm", 0.000021),
            ("hidden_seam_groove_width_mm", 0.026),
            ("automatic_repair", True),
        ):
            fixture = copy.deepcopy(self.contract)
            fixture["mesh_gates"][
                "front_carrier_manufacturing_conditioning"
            ][key] = value
            with self.subTest(key=key):
                self.assertTrue(
                    PREFLIGHT.contract_errors(fixture, CONTRACT_PATH)
                )

    def test_petg_profiles_and_six_layer_lens_are_mandatory(self):
        parts = {item["id"]: item for item in self.contract["source_release"]["parts"]}
        self.assertEqual(parts["front_carrier"]["material"], "conditioned opaque PETG")
        fixture = copy.deepcopy(self.contract)
        for part in self.contract["source_release"]["parts"]:
            values, errors = PREFLIGHT.parse_profile(PACKAGE / part["profile"])
            self.assertEqual(errors, [])
            self.assertEqual(values["filament_type"], "PETG")
            self.assertEqual(values["nozzle_diameter"], "0.4")
        lens_values, _ = PREFLIGHT.parse_profile(PACKAGE / parts["translucent_eye_glass"]["profile"])
        self.assertEqual(lens_values["layer_height"], "0.15")
        self.assertEqual(lens_values["first_layer_height"], "0.15")
        self.assertEqual(lens_values["top_solid_layers"], "6")
        self.assertEqual(lens_values["bottom_solid_layers"], "6")

    def test_three_dab_retention_ca_and_screw_prohibitions_are_mandatory(self):
        fixtures = (
            ("primary_retention", "Use clear silicone."),
            ("retention_dab_count", 2),
            ("adhesive_warning", "Use any clear adhesive."),
            ("fastener_warning", "Screws are optional."),
        )
        for key, value in fixtures:
            fixture = copy.deepcopy(self.contract)
            fixture["assembly"][key] = value
            with self.subTest(key=key):
                self.assertTrue(PREFLIGHT.contract_errors(fixture, CONTRACT_PATH))

    def test_exact_output_names_and_commands_are_declared(self):
        commands = "\n".join(PREFLIGHT.command_plan(self.contract, CONTRACT_PATH))
        for part in self.contract["source_release"]["parts"]:
            self.assertIn(part["stl_name"], commands)
            self.assertIn(part["project_name"], commands)
        self.assertNotIn("export-gcode", commands)
        self.assertNotIn("REAR_CARTRIDGE", commands)
        self.assertIn("--dont-arrange", commands)
        self.assertIn("--no-ensure-on-bed", commands)


if __name__ == "__main__":
    unittest.main()
