import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/validate_iteration_v2.py"
)
SPEC = importlib.util.spec_from_file_location("cad_iteration_v2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CadIterationV2Tests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / (
            "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
            "source/cad-change-control/v2"
        )
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.fixture_dir = Path(self.temporary.name)
        self.assembly = self.fixture_dir / "approved.FCStd"
        self.assembly.write_bytes(b"approved canonical assembly")
        self.generator = self.fixture_dir / "generate_candidate.py"
        self.generator.write_text("print('candidate')\n", encoding="utf-8")
        self.runtime_probe = self.fixture_dir / "probe_runtime.py"
        self.runtime_probe.write_text("print('{}')\n", encoding="utf-8")
        self.runtime_manifest = self.fixture_dir / "runtime.json"
        self.runtime_manifest.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "runtime_id": "test-freecad-runtime",
                    "state": "user_approved_v2_runtime",
                    "freecad": {
                        "release": "1.1.3",
                        "program_version": "1.1R20260725 (Git shallow)",
                        "version_record": ["1", "1", "3", "20260725 (Git shallow)"],
                        "source_appimage_sha256": "a" * 64,
                    },
                    "occt": {"version": "7.8.1"},
                    "python": {"version": "3.11.14"},
                    "platform": {"machine": "x86_64"},
                    "probe": {
                        "script_path": self.relative(self.runtime_probe),
                        "script_sha256": sha256(self.runtime_probe),
                    },
                    "artifacts": [{"path": "AppRun", "sha256": "b" * 64}],
                    "approval": {
                        "status": "approved",
                        "approved_by": "bsk",
                        "approved_at": "2026-08-16",
                        "note": "Test runtime.",
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.images = {}
        for view in MODULE.VIEWS:
            image = self.fixture_dir / f"{view}.png"
            image.write_bytes(f"approved {view}".encode("utf-8"))
            self.images[view] = image
        self.iteration_id = f"test-{self.fixture_dir.name.lower().replace('_', '-')[-24:]}"

    def tearDown(self):
        self.temporary.cleanup()

    def relative(self, path: Path) -> str:
        return str(path.relative_to(ROOT))

    def baseline(self):
        return {
            "schema_version": "2.0",
            "project": "cat-head-full-size-v1",
            "baseline_id": "approved-cat-head-001",
            "state": "human_approved_canonical",
            "assembly": {
                "path": self.relative(self.assembly),
                "sha256": sha256(self.assembly),
                "format": "fcstd",
            },
            "review_pack": {
                view: {"path": self.relative(path), "sha256": sha256(path)}
                for view, path in self.images.items()
            },
            "approval": {
                "status": "approved",
                "approved_by": "bsk",
                "approved_at": "2026-08-16T18:00:00-07:00",
                "note": "Approved from all six whole-assembly views.",
            },
        }

    def contract(self):
        output = Path("reports/generated/cat-head-cad-iterations") / self.iteration_id
        return {
            "schema_version": "2.0",
            "project": "cat-head-full-size-v1",
            "iteration_id": self.iteration_id,
            "state": "approved_for_one_candidate",
            "baseline_id": "approved-cat-head-001",
            "user_approval": {
                "status": "approved",
                "approved_by": "bsk",
                "approved_at": "2026-08-16T18:05:00-07:00",
                "exact_instruction": "Trim only C012 by 5.452 mm at the eye-side end.",
            },
            "target_object": "LOWER_C012",
            "allowed_mutations": [
                {
                    "kind": "trim_end",
                    "object": "LOWER_C012",
                    "parameters": {"distance_mm": 5.452, "end": "eye-side"},
                }
            ],
            "protected_objects": {
                "mode": "all_except_target",
                "invariants": sorted(MODULE.PROTECTED_INVARIANTS),
            },
            "budget": {
                "fresh_chat_required": True,
                "resume_previous_chat": False,
                "max_generation_seconds": 300,
                "max_candidates": 1,
                "max_repair_attempts": 0,
                "automatic_retry": False,
            },
            "runtime": {
                "manifest_path": self.relative(self.runtime_manifest),
                "manifest_sha256": sha256(self.runtime_manifest),
            },
            "generator": {
                "script_path": self.relative(self.generator),
                "script_sha256": sha256(self.generator),
                "arguments": ["--output", str(output)],
                "writes_only_output_directory": True,
            },
            "review_gate": {
                "required_views": list(MODULE.VIEWS),
                "human_visual_approval_required": True,
                "visual_approval_status": "pending",
                "independent_verification_required": True,
                "generator_may_write_validation": False,
                "run_occt_before_visual_approval": False,
            },
            "output": {
                "directory": str(output),
                "candidate_fcstd": str(output / "candidate.FCStd"),
                "no_op_snapshot_fcstd": str(output / "no-op-snapshot.FCStd"),
                "review_files": {
                    view: str(output / "review" / f"{view}.png")
                    for view in MODULE.VIEWS
                },
            },
            "release_holds": {key: False for key in MODULE.RELEASE_HOLDS},
        }

    def validate(self, baseline=None, contract=None, verify_files=True):
        baseline = self.baseline() if baseline is None else baseline
        contract = self.contract() if contract is None else contract
        errors = MODULE.validate_baseline(baseline, ROOT, verify_files)
        errors.extend(
            MODULE.validate_contract(
                contract,
                baseline,
                ROOT,
                verify_files,
                require_new_output=False,
            )
        )
        return errors

    def test_valid_single_candidate_contract_passes(self):
        self.assertEqual(self.validate(), [])

    def test_mixed_source_baseline_fails_closed(self):
        baseline = self.baseline()
        baseline["assemblies"] = [baseline["assembly"]]
        errors = self.validate(baseline=baseline)
        self.assertTrue(any("unsupported keys" in error for error in errors))

    def test_unapproved_baseline_fails_closed(self):
        baseline = self.baseline()
        baseline["state"] = "proposed"
        baseline["approval"]["status"] = "pending"
        errors = self.validate(baseline=baseline)
        self.assertTrue(any("human_approved_canonical" in error for error in errors))
        self.assertTrue(any("approval.status" in error for error in errors))

    def test_two_mutations_fail_closed(self):
        contract = self.contract()
        contract["allowed_mutations"].append(copy.deepcopy(contract["allowed_mutations"][0]))
        errors = self.validate(contract=contract)
        self.assertTrue(any("exactly one mutation" in error for error in errors))

    def test_unapproved_object_delete_kind_fails_closed(self):
        contract = self.contract()
        contract["allowed_mutations"][0]["kind"] = "delete_object"
        errors = self.validate(contract=contract)
        self.assertTrue(any("whole-object delete/rename" in error for error in errors))

    def test_generation_budget_over_five_minutes_fails_closed(self):
        contract = self.contract()
        contract["budget"]["max_generation_seconds"] = 301
        errors = self.validate(contract=contract)
        self.assertTrue(any("must be 1..300" in error for error in errors))

    def test_repair_or_retry_fails_closed(self):
        contract = self.contract()
        contract["budget"]["max_repair_attempts"] = 1
        contract["budget"]["automatic_retry"] = True
        errors = self.validate(contract=contract)
        self.assertTrue(any("max_repair_attempts" in error for error in errors))
        self.assertTrue(any("automatic_retry" in error for error in errors))

    def test_resumed_chat_fails_closed(self):
        contract = self.contract()
        contract["budget"]["resume_previous_chat"] = True
        errors = self.validate(contract=contract)
        self.assertTrue(any("resume_previous_chat" in error for error in errors))

    def test_incomplete_preservation_set_fails_closed(self):
        contract = self.contract()
        contract["protected_objects"]["invariants"].remove("visibility")
        errors = self.validate(contract=contract)
        self.assertTrue(any("complete V2 preservation set" in error for error in errors))

    def test_generator_cannot_validate_its_candidate(self):
        contract = self.contract()
        contract["review_gate"]["generator_may_write_validation"] = True
        errors = self.validate(contract=contract)
        self.assertTrue(any("generator_may_write_validation" in error for error in errors))

    def test_occt_before_visual_review_fails_closed(self):
        contract = self.contract()
        contract["review_gate"]["run_occt_before_visual_approval"] = True
        errors = self.validate(contract=contract)
        self.assertTrue(any("run_occt_before_visual_approval" in error for error in errors))

    def test_output_outside_quarantine_tree_fails_closed(self):
        contract = self.contract()
        contract["output"]["directory"] = "hardware/mechanical/fabrication/output"
        errors = self.validate(contract=contract)
        self.assertTrue(any("must be exactly" in error for error in errors))

    def test_hash_mismatch_fails_closed(self):
        baseline = self.baseline()
        baseline["assembly"]["sha256"] = "f" * 64
        errors = self.validate(baseline=baseline)
        self.assertTrue(any("SHA-256 mismatch" in error for error in errors))

    def test_runtime_manifest_hash_mismatch_fails_closed(self):
        contract = self.contract()
        contract["runtime"]["manifest_sha256"] = "f" * 64
        errors = self.validate(contract=contract)
        self.assertTrue(any("contract.runtime SHA-256 mismatch" in error for error in errors))

    def test_snapshot_path_outside_iteration_fails_closed(self):
        contract = self.contract()
        contract["output"]["no_op_snapshot_fcstd"] = "reports/generated/no-op.FCStd"
        errors = self.validate(contract=contract)
        self.assertTrue(
            any("no_op_snapshot_fcstd must be exactly" in error for error in errors)
        )

    def test_missing_fixed_view_fails_closed(self):
        contract = self.contract()
        del contract["output"]["review_files"]["bottom"]
        errors = self.validate(contract=contract)
        self.assertTrue(any("review_files must contain exactly" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
