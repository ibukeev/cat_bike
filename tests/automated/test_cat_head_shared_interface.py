#!/usr/bin/env python3
"""Regression tests for the shared cat-head shell/aluminum interface."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INTERFACE_DIR = REPO_ROOT / "hardware/mechanical/interfaces"
if str(INTERFACE_DIR) not in sys.path:
    sys.path.insert(0, str(INTERFACE_DIR))

from cat_head_interface import (  # noqa: E402
    DEFAULT_REVISION,
    default_interface_path,
    validate_interface,
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHELL_PREFLIGHT = load_module(
    "prepare_gate9_shared_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/prepare_gate9_shared_interface.py",
)
METAL_PREFLIGHT = load_module(
    "prepare_frame_fixed_mount_v03_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v03_interface.py",
)
METAL_V04_PREFLIGHT = load_module(
    "prepare_frame_fixed_mount_v04_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v04_interface.py",
)
METAL_V05_PREFLIGHT = load_module(
    "prepare_frame_fixed_mount_v05_interface",
    REPO_ROOT
    / "hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v05_interface.py",
)


class CatHeadSharedInterfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.interface = json.loads(default_interface_path().read_text(encoding="utf-8"))

    def test_measured_contract_passes(self) -> None:
        report = validate_interface(self.interface)
        self.assertTrue(report["status"].startswith("PASS"))
        self.assertEqual(self.interface["interface_revision"], DEFAULT_REVISION)
        profile = self.interface["rail_system"]["profile"]
        self.assertEqual(
            (
                profile["outside_width_mm"],
                profile["outside_height_mm"],
                profile["wall_thickness_mm"],
                profile["available_stock_length_mm"],
            ),
            (19.0, 19.0, 2.0, 914.4),
        )
        self.assertAlmostEqual(
            report["derived"]["socket_clearance_each_side_mm"], 0.75
        )

    def test_shell_and_metal_consumers_use_identical_revision(self) -> None:
        shell_config, shell_report = SHELL_PREFLIGHT.load_resolved_config()
        metal_config, metal_report = METAL_PREFLIGHT.load_resolved_config()
        self.assertEqual(shell_report["interface_revision"], DEFAULT_REVISION)
        self.assertEqual(metal_report["interface_revision"], DEFAULT_REVISION)
        shell_portal = shell_config["aluminum_upright_portals"]
        metal_rail = metal_config["head_interface"]["internal_rails"]
        self.assertEqual(shell_portal["tube_outer_width_mm"], 19.0)
        self.assertEqual(shell_portal["tube_outer_height_mm"], 19.0)
        self.assertEqual(shell_portal["tube_wall_thickness_mm"], 2.0)
        self.assertEqual(metal_rail["outer_width_mm"], 19.0)
        self.assertEqual(metal_rail["outer_height_mm"], 19.0)
        self.assertEqual(metal_rail["wall_thickness_mm"], 2.0)
        self.assertEqual(
            shell_portal["lower_route_left_mm"],
            metal_rail["left_lower_target_head_mm"],
        )
        self.assertEqual(
            shell_portal["lower_route_right_mm"],
            metal_rail["right_lower_target_head_mm"],
        )

    def test_v04_conservative_socket_contract_and_metal_preflight_pass(self) -> None:
        path = INTERFACE_DIR / "cat-head-shell-aluminum-interface-v04.json"
        interface = json.loads(path.read_text(encoding="utf-8"))
        report = validate_interface(interface)
        self.assertTrue(report["status"].startswith("PASS"))
        self.assertEqual(interface["head_envelope"], self.interface["head_envelope"])
        self.assertEqual(interface["rear_interface_plane"], self.interface["rear_interface_plane"])
        for key in (
            "material",
            "thickness_mm",
            "outer_top_width_mm",
            "outer_bottom_width_mm",
            "height_mm",
            "adapter_hole_pattern",
        ):
            self.assertEqual(
                interface["aluminum_backplate"][key],
                self.interface["aluminum_backplate"][key],
            )
        for key in (
            "description",
            "outside_width_mm",
            "outside_height_mm",
            "wall_thickness_mm",
            "derived_inside_width_mm",
            "derived_inside_height_mm",
            "available_stock_length_mm",
        ):
            self.assertEqual(
                interface["rail_system"]["profile"][key],
                self.interface["rail_system"]["profile"][key],
            )
        self.assertEqual(
            interface["rail_system"]["accepted_axes_head"],
            self.interface["rail_system"]["accepted_axes_head"],
        )
        self.assertEqual(
            interface["rail_system"]["lower_targets_head_mm"],
            self.interface["rail_system"]["lower_targets_head_mm"],
        )
        self.assertEqual(
            interface["rail_system"]["modeled_installed_reference_length_mm"],
            self.interface["rail_system"]["modeled_installed_reference_length_mm"],
        )
        self.assertEqual(interface["interface_revision"], "CAT-HEAD-SHELL-ALUMINUM-V0.4")
        self.assertEqual(report["derived"]["socket_clearance_each_side_mm"], 1.0)
        socket = interface["rail_system"]["socket"]
        self.assertEqual(socket["printed_opening_width_mm"], 21.0)
        self.assertEqual(socket["lead_in_depth_mm"], 1.0)
        self.assertEqual(socket["lead_in_mouth_width_mm"], 23.0)
        plate = interface["aluminum_backplate"]
        self.assertEqual(
            len(plate["shell_attachment_hole_pattern"][
                "local_x_v_centers_mm"
            ]),
            6,
        )
        self.assertEqual(
            plate["rail_shoe_hole_pattern"][
                "right_local_x_v_centers_mm"
            ],
            [[36.0, -30.0], [47.4, -30.0], [38.0, -9.0]],
        )
        rails = interface["rail_system"]
        self.assertEqual(
            rails["profile"]["finished_cut_length_mm"],
            152.476123,
        )
        self.assertEqual(
            rails["lower_shoe"]["solid_plug"][
                "insertion_inside_tube_mm"
            ],
            39.592,
        )
        _, metal_report = METAL_V04_PREFLIGHT.load_resolved_config()
        self.assertEqual(
            metal_report["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.4",
        )
        self.assertTrue(all(metal_report["checks"].values()))
        self.assertTrue(metal_report["ready_for_geometry_generation"])

    def test_v05_changes_only_the_coordinated_bottom_shell_centers(self) -> None:
        v04_path = INTERFACE_DIR / "cat-head-shell-aluminum-interface-v04.json"
        v05_path = INTERFACE_DIR / "cat-head-shell-aluminum-interface-v05.json"
        v04 = json.loads(v04_path.read_text(encoding="utf-8"))
        v05 = json.loads(v05_path.read_text(encoding="utf-8"))
        report = validate_interface(v05)
        self.assertTrue(report["status"].startswith("PASS"))
        self.assertEqual(v05["interface_revision"], "CAT-HEAD-SHELL-ALUMINUM-V0.5")
        old_centers = v04["aluminum_backplate"][
            "shell_attachment_hole_pattern"
        ]["local_x_v_centers_mm"]
        new_centers = v05["aluminum_backplate"][
            "shell_attachment_hole_pattern"
        ]["local_x_v_centers_mm"]
        self.assertEqual(new_centers[:4], old_centers[:4])
        self.assertEqual(old_centers[4:], [[-10.0, -30.0], [10.0, -30.0]])
        self.assertEqual(new_centers[4:], [[-7.4, -30.0], [7.4, -30.0]])
        for key in (
            "material",
            "thickness_mm",
            "outer_top_width_mm",
            "outer_bottom_width_mm",
            "height_mm",
            "adapter_hole_pattern",
            "rail_shoe_hole_pattern",
        ):
            self.assertEqual(
                v05["aluminum_backplate"][key],
                v04["aluminum_backplate"][key],
            )
        self.assertEqual(v05["rail_system"], v04["rail_system"])
        self.assertFalse(v05["coordination_record"]["fabrication_authorized"])
        _, metal_report = METAL_V05_PREFLIGHT.load_resolved_config()
        self.assertTrue(all(metal_report["checks"].values()))
        self.assertEqual(
            metal_report["interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )

    def test_v05_final_metal_summary_records_coordinated_clearances(self) -> None:
        path = (
            REPO_ROOT
            / "hardware/mechanical/fabrication/metal/"
            "cat-head-frame-fixed-mount-v0/review/"
            "frame-fixed-mount-v05-final-summary.json"
        )
        summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(summary["status"].startswith("PASS"))
        self.assertTrue(all(summary["checks"].values()))
        derived = summary["derived"]
        self.assertEqual(
            derived["coordinated_bottom_shell_centers_mm"],
            [[-7.4, -30.0], [7.4, -30.0]],
        )
        self.assertAlmostEqual(
            derived["minimum_bottom_shell_washer_edge_margin_mm"], 4.8319
        )
        self.assertAlmostEqual(
            derived["minimum_bottom_shell_tool_edge_margin_mm"], 2.8319
        )
        self.assertAlmostEqual(
            derived["opposing_bottom_shell_tool_gap_mm"], 0.8
        )
        self.assertAlmostEqual(
            derived["minimum_bottom_tool_to_adapter_hole_clearance_mm"],
            7.3963,
        )

    def test_gate9_v7_consumes_v05_and_keeps_full_release_held(self) -> None:
        config_path = (
            REPO_ROOT
            / "hardware/mechanical/fabrication/3d-print/"
            "cat-head-full-size-v1/config/"
            "gate9-m2-rear-interface-candidate-v7.json"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(
            config["required_interface_revision"],
            "CAT-HEAD-SHELL-ALUMINUM-V0.5",
        )
        structure = config["rear_structure"]
        self.assertEqual(
            (
                structure["bottom_pad_width_mm"],
                structure["bottom_pad_height_mm"],
                structure["pad_depth_mm"],
            ),
            (14.0, 36.0, 12.0),
        )
        self.assertEqual(structure["lower_truss_source_x_abs_mm"], 7.4)
        self.assertEqual(
            structure["owner_by_local_x_v"]["-7.4,-30"],
            "left_lower_face",
        )
        review_path = (
            REPO_ROOT
            / "hardware/mechanical/fabrication/3d-print/"
            "cat-head-full-size-v1/review/"
            "gate9-v7-v05-coordinated-interface-validation.json"
        )
        review = json.loads(review_path.read_text(encoding="utf-8"))
        self.assertTrue(review["status"].startswith("PASS - V0.5"))
        self.assertFalse(review["fabrication_authorized"])
        self.assertFalse(review["final_asa_print_authorized"])
        self.assertTrue(
            review["bottom_pad_shell_validation"]["washer_and_tool_check"]
        )
        self.assertTrue(
            review["bottom_pad_shell_validation"]["seated_complete_m2_clear"]
        )
        self.assertFalse(
            review["full_v7_validation"][
                "digital_v7_m2_rear_interface_candidate_pass"
            ]
        )

    def test_v04_final_metal_summary_passes_with_recorded_bezel_handoff(self) -> None:
        path = (
            REPO_ROOT
            / "hardware/mechanical/fabrication/metal/"
            "cat-head-frame-fixed-mount-v0/review/"
            "frame-fixed-mount-v04-final-summary.json"
        )
        summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(summary["status"].startswith("PASS"))
        self.assertTrue(all(summary["checks"].values()))
        self.assertEqual(
            summary["dimensions"]["rail_centerline_finished_length_mm"],
            152.476123,
        )
        self.assertEqual(
            summary["dimensions"]["backplate_hole_counts"],
            {"adapter_m6": 4, "shell_m5": 6, "angle_base_m5": 6},
        )
        collision = summary["current_v61_shell_collision_preflight"]
        self.assertTrue(
            collision["checks"][
                "current_v61_collision_matrix_recorded_for_shell_reintegration"
            ]
        )
        self.assertEqual(
            collision["collision_record_counts"]["metal_parts"],
            9,
        )
        self.assertIn("regenerate", collision["required_shell_followup"])

    def test_inconsistent_recorded_inside_dimension_fails(self) -> None:
        invalid = copy.deepcopy(self.interface)
        invalid["rail_system"]["profile"]["derived_inside_width_mm"] = 15.5
        report = validate_interface(invalid)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(
            report["checks"]["inside_dimensions_match_measured_wall"]["pass"]
        )


if __name__ == "__main__":
    unittest.main()
