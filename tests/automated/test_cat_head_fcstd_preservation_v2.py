import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAD_CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
sys.path.insert(0, str(CAD_CONTROL))

import fcstd_preservation_v2 as preservation


BASELINE = CAD_CONTROL / "v2/approved-baseline-v34.json"
RUNTIME_MANIFEST = CAD_CONTROL / (
    "v2/freecad-runtime-1.1.3-r20260725-occt-7.8.1.json"
)
V1_CONTRACT = CAD_CONTROL / "v2/right-eye-parametric-fit-prototype-v1.json"
V2_CONTRACT = CAD_CONTROL / "v2/right-eye-parametric-fit-prototype-v2.json"
REGRESSION = CAD_CONTROL / "regress_fcstd_preservation_v2.py"
QUARANTINE = ROOT / (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-parametric-fit-prototype-v1"
)
CANDIDATE = QUARANTINE / "candidate.FCStd"
SNAPSHOT = QUARANTINE / "candidate.20260816-231443.FCBak"
TARGET = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
CHANGED_PROTECTED = "RETAINED_RIGHT_UPPER_C001_V34"


def normalize_v2_iteration_id(value):
    if isinstance(value, str):
        return value.replace(
            "right-eye-parametric-fit-prototype-v2",
            "right-eye-parametric-fit-prototype-v1",
        )
    if isinstance(value, list):
        return [normalize_v2_iteration_id(item) for item in value]
    if isinstance(value, dict):
        return {
            key: normalize_v2_iteration_id(item)
            for key, item in value.items()
        }
    return value


class CatHeadEyePrototypeV2ContractTests(unittest.TestCase):
    def test_v2_reuses_v1_design_and_generator_exactly(self):
        v1 = json.loads(V1_CONTRACT.read_text(encoding="utf-8"))
        v2 = json.loads(V2_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(v2["target_object"], v1["target_object"])
        self.assertEqual(
            normalize_v2_iteration_id(v2["allowed_mutations"]),
            v1["allowed_mutations"],
        )
        self.assertEqual(v2["generator"]["script_path"], v1["generator"]["script_path"])
        self.assertEqual(
            v2["generator"]["script_sha256"],
            v1["generator"]["script_sha256"],
        )
        self.assertEqual(v2["budget"], v1["budget"])
        self.assertEqual(v2["protected_objects"], v1["protected_objects"])


class CatHeadFcstdPreservationV2Tests(unittest.TestCase):
    def setUp(self):
        appdir_value = os.environ.get("CAT_HEAD_FREECAD_APPDIR")
        if not appdir_value:
            self.skipTest("CAT_HEAD_FREECAD_APPDIR is required for FreeCAD integration")
        self.appdir = Path(appdir_value).resolve()
        if not (self.appdir / "AppRun").is_file():
            self.skipTest("FreeCAD AppRun is unavailable")

    def test_unapproved_runtime_mismatch_is_rejected(self):
        manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
        manifest["occt"]["version"] = "0.0.0-unapproved"
        result = preservation.verify_runtime(self.appdir, ROOT, manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(
            "runtime probe does not match the approved manifest",
            result["errors"],
        )

    @unittest.skipUnless(
        CANDIDATE.is_file() and SNAPSHOT.is_file(),
        "existing quarantine evidence is unavailable",
    )
    def test_canonical_v34_round_trip_and_quarantine_evidence(self):
        with tempfile.TemporaryDirectory(
            prefix="cat-head-preservation-test-",
            dir="/tmp",
        ) as temporary_name:
            report = Path(temporary_name) / "regression-report.json"
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
                str(REGRESSION),
                "--baseline",
                str(BASELINE),
                "--runtime-manifest",
                str(RUNTIME_MANIFEST),
                "--existing-candidate",
                str(CANDIDATE),
                "--existing-snapshot",
                str(SNAPSHOT),
                "--target-object",
                TARGET,
                "--changed-protected-object",
                CHANGED_PROTECTED,
                "--report",
                str(report),
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["no_op_control"]["status"], "PASS")
            self.assertEqual(
                result["deliberately_changed_protected_object"]["status"],
                "PASS__CHANGE_DETECTED",
            )
            existing = result["existing_quarantine_evidence"]
            self.assertEqual(existing["status"], "PASS")
            self.assertEqual(
                existing["protected_shape_comparison"]["checked_count"],
                44,
            )
            self.assertEqual(
                existing["protected_shape_comparison"]["mismatches"],
                {},
            )


if __name__ == "__main__":
    unittest.main()
