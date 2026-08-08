import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source"
    / "print_topology_policy.py"
)
SPEC = importlib.util.spec_from_file_location("print_topology_policy", POLICY_PATH)
assert SPEC is not None and SPEC.loader is not None
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class PrintTopologyPolicyTest(unittest.TestCase):
    def test_accepts_exactly_one_closed_manifold_body(self):
        self.assertTrue(
            POLICY.is_single_closed_body(
                {
                    "connected_components": 1,
                    "boundary_edges": 0,
                    "nonmanifold_edges": 0,
                }
            )
        )

    def test_rejects_disconnected_manifold_mesh(self):
        self.assertFalse(
            POLICY.is_single_closed_body(
                {
                    "connected_components": 6,
                    "boundary_edges": 0,
                    "nonmanifold_edges": 0,
                }
            )
        )

    def test_rejects_open_or_nonmanifold_mesh(self):
        base = {
            "connected_components": 1,
            "boundary_edges": 0,
            "nonmanifold_edges": 0,
        }
        for key in ("boundary_edges", "nonmanifold_edges"):
            invalid = dict(base)
            invalid[key] = 1
            with self.subTest(key=key):
                self.assertFalse(POLICY.is_single_closed_body(invalid))

    def test_rejects_empty_part_collection(self):
        self.assertFalse(POLICY.all_single_closed_bodies([]))

    def test_accepts_ten_mm_per_side_xy_reserve(self):
        self.assertTrue(
            POLICY.has_minimum_xy_boundary_clearance(
                {
                    "fits": True,
                    "oriented_dimensions_mm_sorted": [180.0, 190.0, 230.0],
                    "envelope_mm_sorted": [200.0, 210.0, 240.0],
                },
                10.0,
            )
        )

    def test_rejects_old_lower_face_orientation_margin(self):
        self.assertFalse(
            POLICY.has_minimum_xy_boundary_clearance(
                {
                    "fits": True,
                    "oriented_dimensions_mm_sorted": [192.202, 203.784, 229.302],
                    "envelope_mm_sorted": [200.0, 210.0, 240.0],
                },
                10.0,
            )
        )

    def test_margin_pass_is_only_pre_brim_and_support(self):
        self.assertFalse(
            POLICY.has_minimum_xy_boundary_clearance(
                {
                    "fits": False,
                    "oriented_dimensions_mm_sorted": [180.0, 190.0, 230.0],
                    "envelope_mm_sorted": [200.0, 210.0, 240.0],
                },
                10.0,
            )
        )

    def test_require_all_acceptance_returns_on_pass(self):
        self.assertIsNone(
            POLICY.require_all_acceptance("Gate test", {"topology": True})
        )

    def test_require_all_acceptance_raises_with_every_failure(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Gate test validation failed: \['topology', 'margin'\]",
        ):
            POLICY.require_all_acceptance(
                "Gate test",
                {"topology": False, "other": True, "margin": False},
            )


if __name__ == "__main__":
    unittest.main()
