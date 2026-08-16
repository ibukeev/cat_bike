import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/validate_change_contract.py"
)
SPEC = importlib.util.spec_from_file_location("cad_change_control", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def artifact(artifact_id="target", status="frozen_accepted"):
    return {
        "id": artifact_id,
        "path": f"fixtures/{artifact_id}.step",
        "sha256": "0" * 64,
        "format": "step",
        "status": status,
        "role": "test fixture",
    }


def contract():
    return {
        "schema_version": "1.0",
        "contract_id": "test-contract",
        "mode": "read_only_validation",
        "target_owner": "target",
        "protected_owners": [],
        "permitted_operations": ["inspect", "measure"],
        "geometry_changes_allowed": False,
        "artifacts_to_inspect": ["target"],
        "shape_gates": {
            "require_valid": True,
            "require_closed": True,
            "required_solid_count": 1,
        },
        "clearance_gates": [],
        "output_directory": "reports/generated/cat-head-cad-validation/test",
        "release_holds": {
            "mirror": False,
            "production_union": False,
            "stl": False,
            "gcode": False,
            "asa_print": False,
        },
    }


class CadChangeControlTests(unittest.TestCase):
    def test_valid_read_only_contract_passes(self):
        artifacts = {"target": artifact()}
        self.assertEqual(MODULE.validate_contract(contract(), artifacts), [])

    def test_rejected_artifact_cannot_become_target(self):
        artifacts = {"target": artifact(status="rejected_visual")}
        errors = MODULE.validate_contract(contract(), artifacts)
        self.assertTrue(any("blocked status" in error for error in errors))

    def test_clearance_policy_cannot_be_double_counted(self):
        value = contract()
        value["artifacts_to_inspect"].append("neighbor")
        value["clearance_gates"] = [
            {
                "id": "distance",
                "mode": "actual_geometry",
                "first": "target",
                "second": "neighbor",
                "minimum_distance_mm": 4.0,
            },
            {
                "id": "keepout",
                "mode": "inflated_keepout",
                "first": "target",
                "second": "neighbor",
                "maximum_intersection_mm3": 0,
            },
        ]
        artifacts = {"target": artifact(), "neighbor": artifact("neighbor")}
        errors = MODULE.validate_contract(value, artifacts)
        self.assertTrue(any("double-count" in error for error in errors))

    def test_output_must_stay_in_generated_validation_tree(self):
        value = contract()
        value["output_directory"] = "hardware/mechanical/fabrication/output"
        errors = MODULE.validate_contract(value, {"target": artifact()})
        self.assertTrue(any("output_directory must be under" in error for error in errors))

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fixture = Path(directory) / "fixture.step"
            fixture.write_text("not the declared digest", encoding="utf-8")
            relative = fixture.relative_to(ROOT)
            item = artifact()
            item["path"] = str(relative)
            manifest = {
                "schema_version": "1.0",
                "project": "cat-head-full-size-v1",
                "artifacts": [item],
            }
            _, errors = MODULE.validate_manifest(manifest, ROOT, verify_files=True)
            self.assertTrue(any("SHA-256 mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
