from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
GENERATOR_PATH = CONTROL / "generate_right_eye_parametric_fit_prototype_v3.py"
BASELINE_PATH = CONTROL / "v2/approved-baseline-v34.json"
V1_CONTRACT_PATH = CONTROL / "v2/right-eye-parametric-fit-prototype-v1.json"
V3_CONTRACT_PATH = CONTROL / "v2/right-eye-parametric-fit-prototype-v3.json"
V3_ITERATION_ID = "right-eye-parametric-fit-prototype-v3"
V1_ITERATION_ID = "right-eye-parametric-fit-prototype-v1"
V3_OUTPUT = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-parametric-fit-prototype-v3"
)
WRAPPER_PARAMETER_KEYS = {"tooling_dependencies", "historical_evidence"}


def normalize_iteration_id(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(V3_ITERATION_ID, V1_ITERATION_ID)
    if isinstance(value, list):
        return [normalize_iteration_id(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_iteration_id(item) for key, item in value.items()}
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: expected a JSON object")
    return value


class RightEyeParametricFitToolingV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        appdir_value = os.environ.get("CAT_HEAD_FREECAD_APPDIR")
        if not appdir_value:
            raise unittest.SkipTest("CAT_HEAD_FREECAD_APPDIR is required")
        cls.appdir = Path(appdir_value).resolve()
        if not (cls.appdir / "AppRun").is_file():
            raise unittest.SkipTest("pinned FreeCAD AppRun is unavailable")

    def run_preflight(self, contract_path: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        freecad_lib = self.appdir / "usr/lib"
        old_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{freecad_lib}:{old_pythonpath}"
            if old_pythonpath
            else str(freecad_lib)
        )
        command = [
            str(self.appdir / "AppRun"),
            "python",
            str(GENERATOR_PATH),
            "--baseline",
            str(BASELINE_PATH),
            "--contract",
            str(contract_path),
            "--preflight-only",
        ]
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )

    def test_exact_v3_entrypoint_preflight_creates_nothing(self):
        self.assertFalse(V3_OUTPUT.exists(), "V3 output must be new before smoke test")
        completed = self.run_preflight(V3_CONTRACT_PATH)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        report = json.loads(completed.stdout)

        self.assertEqual(
            report["status"],
            "PASS__NO_OUTPUT_CREATED__NO_GEOMETRY_CONSTRUCTED",
        )
        self.assertEqual(report["iteration_id"], V3_ITERATION_ID)
        self.assertEqual(report["resolved_iteration_id"], V3_ITERATION_ID)
        self.assertEqual(report["shared_contract_preflight"], "PASS")
        self.assertTrue(report["geometry_parameters_match_v1"])
        self.assertFalse(report["output_exists"])
        self.assertFalse(report["candidate_exists"])
        self.assertFalse(report["geometry_construction_started"])
        self.assertFalse(report["v1_implementation"]["main_invoked"])
        self.assertEqual(
            report["v1_implementation"]["iteration_id"], V1_ITERATION_ID
        )
        self.assertFalse(V3_OUTPUT.exists())
        self.assertFalse((V3_OUTPUT / "candidate.FCStd").exists())

    def test_mismatched_iteration_id_fails_before_output_or_construction(self):
        self.assertFalse(V3_OUTPUT.exists(), "V3 output must remain absent")
        contract = copy.deepcopy(load_json(V3_CONTRACT_PATH))
        contract["iteration_id"] = "right-eye-parametric-fit-prototype-v3-mismatch"
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="right-eye-v3-mismatch-",
            suffix=".json",
            dir=CONTROL / "v2",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(contract, handle, indent=2, sort_keys=True)
            handle.write("\n")
            mismatch_path = Path(handle.name)
        self.addCleanup(mismatch_path.unlink, missing_ok=True)

        completed = self.run_preflight(mismatch_path)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("iteration ID mismatch", completed.stdout)
        self.assertIn('"geometry_construction_started": false', completed.stdout)
        self.assertNotIn("STAGE 2/6", completed.stdout)
        self.assertFalse(V3_OUTPUT.exists())
        self.assertFalse((V3_OUTPUT / "candidate.FCStd").exists())

    def test_v3_geometry_parameters_are_exact_v1_values(self):
        v1 = load_json(V1_CONTRACT_PATH)
        v3 = load_json(V3_CONTRACT_PATH)
        expected = v1["allowed_mutations"][0]["parameters"]
        v3_parameters = v3["allowed_mutations"][0]["parameters"]
        actual = {
            key: value
            for key, value in v3_parameters.items()
            if key not in WRAPPER_PARAMETER_KEYS
        }
        self.assertEqual(normalize_iteration_id(actual), expected)

        for key in (
            "module_lcs",
            "visible_aperture_mm",
            "approved_shell_opening_boundary_mm",
            "head_mounts",
            "fit_objectives",
            "fit_references",
        ):
            self.assertEqual(normalize_iteration_id(actual[key]), expected[key])


if __name__ == "__main__":
    unittest.main()
