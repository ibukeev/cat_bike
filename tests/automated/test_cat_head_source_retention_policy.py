import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source"
    / "source_retention_policy.py"
)
SPEC = importlib.util.spec_from_file_location("source_retention_policy", POLICY_PATH)
assert SPEC is not None and SPEC.loader is not None
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class SourceRetentionPolicyTest(unittest.TestCase):
    def test_accepts_owner_that_retains_every_required_source(self):
        self.assertTrue(
            POLICY.all_required_sources_retained(
                {"bezel": 120.0, "chamber": 845.5, "upper_rim": 0.25}
            )
        )

    def test_rejects_owner_that_silently_drops_tangent_source(self):
        self.assertFalse(
            POLICY.all_required_sources_retained(
                {"bezel": 120.0, "chamber": 845.5, "upper_rim": 0.0}
            )
        )

    def test_rejects_empty_source_ledger(self):
        self.assertFalse(POLICY.all_required_sources_retained({}))

    def test_honors_explicit_retained_volume_threshold(self):
        self.assertFalse(
            POLICY.all_required_sources_retained(
                {"upper_rim": 0.25},
                minimum_retained_volume_mm3=0.5,
            )
        )

    def test_rejects_nonpositive_threshold(self):
        with self.assertRaisesRegex(
            ValueError,
            "minimum_retained_volume_mm3 must be positive",
        ):
            POLICY.all_required_sources_retained(
                {"upper_rim": 1.0},
                minimum_retained_volume_mm3=0.0,
            )


if __name__ == "__main__":
    unittest.main()
