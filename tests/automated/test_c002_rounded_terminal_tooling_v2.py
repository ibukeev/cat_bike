from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any

try:
    import FreeCAD as App
except ModuleNotFoundError:
    App = None


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
GENERATOR_PATH = CONTROL / "generate_c002_rounded_terminal_profile_prototype_v2.py"
BASELINE_PATH = CONTROL / "v2/approved-baseline-v34.json"
CONTRACT_PATH = CONTROL / "v2/c002-rounded-terminal-profile-prototype-v2.json"

MODULE: Any = None
if App is not None:
    SPEC = importlib.util.spec_from_file_location("c002_tooling_v2", GENERATOR_PATH)
    assert SPEC is not None and SPEC.loader is not None
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipIf(App is None, "requires the pinned FreeCAD runtime")
class C002RoundedTerminalToolingV2Tests(unittest.TestCase):
    def load_inputs(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return MODULE.load_json(BASELINE_PATH), MODULE.load_json(CONTRACT_PATH)

    def open_target(
        self,
        baseline: dict[str, Any],
    ) -> tuple[Any, Any]:
        document = App.openDocument(str(ROOT / baseline["assembly"]["path"]))
        target = document.getObject(MODULE.TARGET_OBJECT)
        self.assertIsNotNone(target)
        return document, target

    def resolve(
        self,
        target: Any,
        contract: dict[str, Any],
        runtime: dict[str, Any],
    ) -> dict[str, Any]:
        parameters = contract["allowed_mutations"][0]["parameters"]
        origin, _, _, axis_t = MODULE.frame_from_parameters(parameters)
        return MODULE.resolve_c002_anchors(
            target,
            parameters,
            origin,
            axis_t,
            runtime,
        )

    def temporary_json(self, value: dict[str, Any], prefix: str) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix=prefix,
            suffix=".json",
            dir=CONTROL / "v2",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def unique_output(self, label: str) -> tuple[Path, str]:
        relative = (
            Path("reports/generated/cat-head-cad-iterations")
            / f"c002-tooling-{label}-{uuid.uuid4().hex}"
        )
        absolute = ROOT / relative
        self.addCleanup(shutil.rmtree, absolute, True)
        return absolute, str(relative)

    def retarget_output(self, contract: dict[str, Any], relative: str) -> None:
        output = Path(relative)
        contract["output"]["directory"] = str(output)
        contract["output"]["candidate_fcstd"] = str(output / "candidate.FCStd")
        contract["output"]["no_op_snapshot_fcstd"] = str(
            output / "no-op-snapshot.FCStd"
        )
        contract["output"]["review_files"] = {
            name: str(output / "review" / f"{name}.png")
            for name in ("front", "rear", "left", "right", "top", "bottom")
        }
        artifacts = contract["allowed_mutations"][0]["parameters"][
            "review_artifacts"
        ]
        for name, path in list(artifacts.items()):
            artifacts[name] = str(output / "review" / Path(path).name)

    def test_canonical_v34_anchors_resolve(self):
        baseline, contract = self.load_inputs()
        runtime, _ = MODULE.verify_runtime(ROOT, contract["runtime"])
        document, target = self.open_target(baseline)
        try:
            resolved = self.resolve(target, contract, runtime)
        finally:
            App.closeDocument(document.Name)

        primary = resolved["records"]["primary_termination_datum"]
        witness = resolved["records"]["corroborating_current_cavity_witness"]
        self.assertEqual(primary["actual"]["face_identifier"], f"{MODULE.TARGET_OBJECT}.Face10")
        self.assertEqual(witness["actual"]["face_identifier"], f"{MODULE.TARGET_OBJECT}.Face164")
        self.assertEqual(primary["actual"]["area_mm2_at_approved_precision"], 1056.25)
        self.assertEqual(witness["actual"]["area_mm2_at_approved_precision"], 420.25)
        self.assertLessEqual(
            resolved["records"]["plane_coincidence_residual_mm"],
            MODULE.POSITION_TOLERANCE_MM,
        )

    def test_intentionally_wrong_anchor_fails_with_full_diagnostics(self):
        baseline, contract = self.load_inputs()
        runtime, _ = MODULE.verify_runtime(ROOT, contract["runtime"])
        contract["allowed_mutations"][0]["parameters"]["anchors"][
            "face10_expected_area_mm2"
        ] = 1056.26
        document, target = self.open_target(baseline)
        try:
            with self.assertRaises(MODULE.AnchorResolutionError) as caught:
                self.resolve(target, contract, runtime)
        finally:
            App.closeDocument(document.Name)

        diagnostic = json.loads(str(caught.exception))
        self.assertEqual(diagnostic["expected"]["area_mm2"], 1056.26)
        self.assertEqual(
            diagnostic["mapped_actuals"][0]["face_identifier"],
            f"{MODULE.TARGET_OBJECT}.Face10",
        )
        self.assertIn("area_mm2", diagnostic["mapped_actuals"][0])
        self.assertIn("centroid_head_mm", diagnostic["mapped_actuals"][0])
        self.assertIn("normal", diagnostic["mapped_actuals"][0])
        self.assertEqual(diagnostic["runtime"], runtime)

    def test_anchor_failure_creates_no_candidate_or_output_directory(self):
        _, contract = self.load_inputs()
        output_path, output_relative = self.unique_output("anchor-failure")
        self.retarget_output(contract, output_relative)
        contract["allowed_mutations"][0]["parameters"]["anchors"][
            "face10_expected_area_mm2"
        ] = 1056.26
        contract_path = self.temporary_json(contract, "c002-anchor-failure-")

        with self.assertRaises(MODULE.AnchorResolutionError):
            MODULE.main(
                [
                    "--baseline",
                    str(BASELINE_PATH),
                    "--contract",
                    str(contract_path),
                ]
            )
        self.assertFalse(output_path.exists())

    def test_runtime_mismatch_fails_before_generation_and_output(self):
        _, contract = self.load_inputs()
        output_path, output_relative = self.unique_output("runtime-mismatch")
        self.retarget_output(contract, output_relative)

        runtime_manifest = MODULE.load_json(ROOT / contract["runtime"]["manifest_path"])
        runtime_manifest["freecad"]["program_version"] = "1.1R19000101-intentionally-wrong"
        runtime_path = self.temporary_json(runtime_manifest, "c002-runtime-mismatch-")
        contract["runtime"] = {
            "manifest_path": str(runtime_path.relative_to(ROOT)),
            "manifest_sha256": sha256(runtime_path),
        }
        contract_path = self.temporary_json(contract, "c002-runtime-contract-")

        with self.assertRaises(MODULE.RuntimePreconditionError) as caught:
            MODULE.main(
                [
                    "--baseline",
                    str(BASELINE_PATH),
                    "--contract",
                    str(contract_path),
                ]
            )
        diagnostic = json.loads(str(caught.exception))
        self.assertIn("actual_runtime", diagnostic)
        self.assertIn("expected_runtime", diagnostic)
        self.assertFalse(diagnostic["geometry_construction_started"])
        self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
