from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/review-only/"
    "right-lower-rear-v5-long-ledge-interface-review-v5"
)
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
SOURCE = (HERE / "generate_freecad_review.py").read_text(encoding="utf-8")


class RightLowerRearV5LongLedgeInterfaceReviewV5Tests(unittest.TestCase):
    def test_change_bucket_is_connection_only(self) -> None:
        self.assertEqual(CONTRACT["change_bucket"], "front_to_rear_connection_interface_only")
        self.assertIn("cosmetic cleanup", " ".join(CONTRACT["prohibited"]))

    def test_continuous_ledge_dimensions_are_exact(self) -> None:
        ledge = CONTRACT["ledge"]
        self.assertEqual(ledge["u_max_mm"] - ledge["u_min_mm"], 72.0)
        self.assertEqual(ledge["n_max_mm"] - ledge["n_min_mm"], 17.0)
        self.assertEqual(ledge["shelf_thickness_mm"], 4.0)
        self.assertEqual(ledge["bearing_clearance_inward_mm"], 0.3)
        self.assertEqual(ledge["front_root_embed_outward_mm"], 1.2)
        self.assertGreaterEqual(ledge["rear_sweep_clearance_margin_mm"], 0.30)
        self.assertGreaterEqual(ledge["rear_assembled_clearance_margin_mm"], 0.30)
        self.assertEqual(ledge["rear_assembled_clearance_owner_indices"], [15, 45])

    def test_two_widely_spaced_m3_stations(self) -> None:
        fasteners = CONTRACT["fasteners"]
        self.assertEqual(fasteners["standard"], "M3")
        self.assertEqual(fasteners["count"], 2)
        self.assertEqual(fasteners["station_u_mm"], [-24.0, 24.0])
        self.assertEqual(fasteners["station_span_mm"], 48.0)
        self.assertEqual(fasteners["rear_clearance_diameter_mm"], 3.4)
        self.assertEqual(fasteners["screw_length_mm"], 16.0)

    def test_structural_defaults_are_not_weakened(self) -> None:
        gates = CONTRACT["numeric_gates"]
        self.assertGreaterEqual(gates["minimum_bore_to_edge_material_mm"], 3.5)
        self.assertGreaterEqual(gates["minimum_front_root_overlap_mm3"], 80.0)
        self.assertGreaterEqual(gates["minimum_rear_clearance_mm"], 0.29)

    def test_measured_surface_frame_is_pinned(self) -> None:
        evidence = CONTRACT["measurement_evidence"]
        self.assertRegex(evidence["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(evidence["sample_count"], 54)
        self.assertEqual(evidence["populated_sample_count"], 54)
        self.assertAlmostEqual(
            evidence["measured_inner_surface_v_per_n"],
            CONTRACT["seam_frame"]["surface_v_per_n"],
            places=12,
        )

    def test_all_repository_inputs_are_hash_pinned(self) -> None:
        for value in CONTRACT["inputs"].values():
            self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")

    def test_generator_contains_fail_closed_physical_gates(self) -> None:
        for token in (
            "front_root_overlap_mm3",
            "non_target_front_common_mm3",
            "rear_minimum_clearance_mm",
            "rear_slide_common_mm3",
            "rear_assembled_clearance_sources",
            "driver_corridor_common_mm3",
            "bore_edge_material_mm",
        ):
            self.assertIn(token, SOURCE)

    def test_generator_never_exports_or_mutates_v4(self) -> None:
        for forbidden in ("exportStl", "exportMesh", "exportStep", "write_gcode"):
            self.assertNotIn(forbidden, SOURCE)
        self.assertIn('"v4_saved": False', SOURCE)
        self.assertIn('"production_output_created": False', SOURCE)


if __name__ == "__main__":
    unittest.main()
