#!/usr/bin/env python3
"""Generate the finalized aluminum-side CAT-HEAD-SHELL-ALUMINUM-V0.4 handoff.

Run against the locked V6.1 socket assembly:

    blender --background \
      ../../3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
      --python source/generate_frame_fixed_mount_v04.py

The generated geometry closes the aluminum-side rail, shoe, anti-crush, and
backplate-hole decisions. It remains blocked from fabrication and riding until
the matching ASA rear structure, physical coupon, load, vibration, lamp, and
service-sequence gates recorded in the config and checkpoint pass.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/frame-fixed-mount-v04-final.json"
REVIEW_PATH = PACKAGE_ROOT / "review/frame-fixed-mount-v04-final-summary.json"


def repo_path(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    path.relative_to(REPO_ROOT)
    return path


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    interface_path = repo_path(config["shared_interface_path"])
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    socket_summary_path = repo_path(config["v61_socket_summary_path"])
    socket_summary = json.loads(socket_summary_path.read_text(encoding="utf-8"))
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("V0.4 generator received the wrong shared interface")
    if socket_summary["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("V6.1 socket summary and metal generator revisions differ")
    return config, interface, socket_summary


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    root = repo_path(config["output_namespace"])
    paths = {
        "root": root,
        "flat": root / "flat-plates",
        "formed": root / "machined-parts",
        "rails": root / "rail-cut-drill",
        "model": root / "review-model",
        "renders": root / "renders",
        "validation": root / "validation",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    return paths


def number(value: float) -> str:
    result = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if result == "-0" else result


def svg_document(
    width: float,
    height: float,
    body: str,
    title: str,
) -> str:
    margin = 12.0
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{number(width + 2 * margin)}mm"
 height="{number(height + 2 * margin)}mm"
 viewBox="{number(-width / 2 - margin)} {number(-height / 2 - margin)}
 {number(width + 2 * margin)} {number(height + 2 * margin)}">
 <title>{title}</title>
 <style>
  .outline{{fill:#eaf1f5;stroke:#000;stroke-width:.25}}
  .adapter{{fill:none;stroke:#8a2be2;stroke-width:.28}}
  .shell{{fill:none;stroke:#126ec2;stroke-width:.28}}
  .shoe{{fill:none;stroke:#e46c0a;stroke-width:.28}}
  .center{{fill:none;stroke:#777;stroke-width:.18;stroke-dasharray:2 2}}
  .dim{{fill:none;stroke:#c41e3a;stroke-width:.18}}
  .note{{font:3px monospace;fill:#111}}
  .warn{{font:3px monospace;fill:#c41e3a}}
 </style>
 <g transform="scale(1,-1)">{body}</g>
</svg>
"""


def svg_text(x: float, y: float, value: str, css: str = "note") -> str:
    return (
        f'<text class="{css}" x="{number(x)}" y="{number(-y)}" '
        f'transform="scale(1,-1)">{value}</text>'
    )


def svg_circle(
    x: float,
    y: float,
    diameter: float,
    css: str,
) -> str:
    return (
        f'<circle class="{css}" cx="{number(x)}" cy="{number(y)}" '
        f'r="{number(diameter / 2.0)}"/>'
    )


def dxf_start() -> list[str]:
    return ["0", "SECTION", "2", "ENTITIES"]


def dxf_line(
    output: list[str],
    first: tuple[float, float],
    second: tuple[float, float],
    layer: str = "CUT",
) -> None:
    output.extend(
        [
            "0",
            "LINE",
            "8",
            layer,
            "10",
            number(first[0]),
            "20",
            number(first[1]),
            "11",
            number(second[0]),
            "21",
            number(second[1]),
        ]
    )


def dxf_circle(
    output: list[str],
    center: tuple[float, float],
    diameter: float,
    layer: str,
) -> None:
    output.extend(
        [
            "0",
            "CIRCLE",
            "8",
            layer,
            "10",
            number(center[0]),
            "20",
            number(center[1]),
            "40",
            number(diameter / 2.0),
        ]
    )


def backplate_polygon(interface: dict[str, Any]) -> list[tuple[float, float]]:
    plate = interface["aluminum_backplate"]
    half_height = float(plate["height_mm"]) / 2.0
    return [
        (-float(plate["outer_bottom_width_mm"]) / 2.0, -half_height),
        (float(plate["outer_bottom_width_mm"]) / 2.0, -half_height),
        (float(plate["outer_top_width_mm"]) / 2.0, half_height),
        (-float(plate["outer_top_width_mm"]) / 2.0, half_height),
    ]


def adapter_holes(interface: dict[str, Any]) -> list[tuple[float, float]]:
    pattern = interface["aluminum_backplate"]["adapter_hole_pattern"]
    return [
        (float(x), float(v))
        for x in pattern["x_mm"]
        for v in pattern["local_v_mm"]
    ]


def shoe_holes(config: dict[str, Any]) -> list[tuple[float, float]]:
    right = [
        (float(point[0]), float(point[1]))
        for point in config["backplate"]["shoe_attachment"][
            "right_local_x_v_centers_mm"
        ]
    ]
    return [(-x, v) for x, v in right] + right


def shell_holes(config: dict[str, Any]) -> list[tuple[float, float]]:
    return [
        (float(point[0]), float(point[1]))
        for point in config["backplate"]["shell_attachment"][
            "local_x_v_centers_mm"
        ]
    ]


def write_backplate_outputs(
    config: dict[str, Any],
    interface: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    plate = interface["aluminum_backplate"]
    outline = backplate_polygon(interface)
    body = (
        '<polygon class="outline" points="'
        + " ".join(f"{number(x)},{number(v)}" for x, v in outline)
        + '"/>'
    )
    for x, v in adapter_holes(interface):
        body += svg_circle(
            x,
            v,
            float(plate["adapter_hole_pattern"]["diameter_mm"]),
            "adapter",
        )
    for x, v in shell_holes(config):
        body += svg_circle(
            x,
            v,
            float(
                config["backplate"]["shell_attachment"][
                    "clearance_diameter_mm"
                ]
            ),
            "shell",
        )
    for x, v in shoe_holes(config):
        body += svg_circle(
            x,
            v,
            float(
                config["backplate"]["shoe_attachment"][
                    "plate_clearance_diameter_mm"
                ]
            ),
            "shoe",
        )
    body += (
        '<path class="center" d="M -60,0 H 60 '
        'M 0,-39.8319 V 39.8319"/>'
    )
    body += svg_text(
        -59,
        49,
        "V0.4 HEAD BACKPLATE | 3 mm 6061-T6 | PRINT 100%",
    )
    body += svg_text(
        -59,
        45,
        "purple 4x dia6.6 adapter | blue 6x dia5.5 shell | orange 6x dia5.5 shoes",
    )
    body += svg_text(
        -59,
        -48,
        "DIGITALLY FINALIZED METAL-SIDE PATTERN; PHYSICAL COUPON + ASA INTEGRATION REQUIRED",
        "warn",
    )
    (paths["flat"] / "head-rear-backplate-v04-1to1.svg").write_text(
        svg_document(
            190.0,
            115.0,
            body,
            "V0.4 finalized aluminum backplate 1:1",
        ),
        encoding="utf-8",
    )

    dxf = dxf_start()
    for first, second in zip(outline, outline[1:] + outline[:1]):
        dxf_line(dxf, first, second)
    for center in adapter_holes(interface):
        dxf_circle(
            dxf,
            center,
            float(plate["adapter_hole_pattern"]["diameter_mm"]),
            "ADAPTER_M6",
        )
    for center in shell_holes(config):
        dxf_circle(
            dxf,
            center,
            float(
                config["backplate"]["shell_attachment"][
                    "clearance_diameter_mm"
                ]
            ),
            "SHELL_M5",
        )
    for center in shoe_holes(config):
        dxf_circle(
            dxf,
            center,
            float(
                config["backplate"]["shoe_attachment"][
                    "plate_clearance_diameter_mm"
                ]
            ),
            "SHOE_M5",
        )
    dxf.extend(["0", "ENDSEC", "0", "EOF"])
    (paths["flat"] / "head-rear-backplate-v04.dxf").write_text(
        "\n".join(dxf) + "\n",
        encoding="ascii",
    )


def write_rail_output(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    rails = config["rails"]
    length = float(rails["drawing_rounded_cut_length_mm"])
    half = length / 2.0
    y = 0.0
    body = (
        f'<rect class="outline" x="{number(-half)}" y="-9.5" '
        f'width="{number(length)}" height="19"/>'
    )
    for offset in rails["lower_m5_centers_from_lower_cut_end_mm"]:
        x = -half + float(offset)
        body += svg_circle(x, y, 5.5, "shoe")
        body += svg_text(x - 5.0, -15.0, f"M5 @ {float(offset):g}")
    upper = float(rails["upper_m4_center_from_lower_cut_end_mm"])
    body += svg_circle(-half + upper, y, 4.5, "shell")
    body += svg_text(-half + upper - 8.0, 14.0, f"M4 @ {upper:.3f}")
    body += svg_text(
        -half,
        26.0,
        "2x 19 x 19 x 2 tube | FINISH 149.672 +/-0.25 mm | square/deburred ends",
    )
    body += svg_text(
        -half,
        21.0,
        "lower M5 holes transfer-drilled with matched solid-plug shoe; upper M4 uses V6.1 socket jig",
    )
    body += svg_text(
        -half,
        -25.0,
        "HOLE AXIS = head-X projected perpendicular to each accepted rail axis",
        "warn",
    )
    (paths["rails"] / "rail-cut-and-drill-v04-1to1.svg").write_text(
        svg_document(
            190.0,
            75.0,
            body,
            "V0.4 rail cut and drill drawing",
        ),
        encoding="utf-8",
    )


def write_shoe_output(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    shoe = config["lower_shoe"]
    foot = [
        (float(point[0]), float(point[1]))
        for point in shoe["right_foot_local_x_v_polygon_mm"]
    ]
    body = (
        '<polygon class="outline" points="'
        + " ".join(f"{number(x)},{number(v)}" for x, v in foot)
        + '"/>'
    )
    for x, v in config["backplate"]["shoe_attachment"][
        "right_local_x_v_centers_mm"
    ]:
        body += svg_circle(float(x), float(v), 4.2, "shoe")
    body += svg_circle(40.0, -24.8319, 2.0, "center")
    body += svg_text(
        2.0,
        15.0,
        "RIGHT SHOE BACKPLATE FACE | mirror X for left | 10 mm 6061-T6 billet foot",
    )
    body += svg_text(
        2.0,
        10.0,
        "3x M5 blind taps: 4.2 tap drill, 9 deep, minimum 8 thread engagement",
    )
    body += svg_text(
        2.0,
        5.0,
        "14.7 square fitted plug: start axis+5.3, end axis+45.0; rail seats at axis+8.0",
    )
    body += svg_text(
        2.0,
        0.0,
        "plug 1.2 long-edge chamfers + 1.0 nose chamfer; fit actual deburred tube",
    )
    body += svg_text(
        2.0,
        -46.0,
        "MONOLITHIC CNC PART - NO WELD - DO NOT TIGHTEN CROSS-BOLT WITHOUT FITTED PLUG",
        "warn",
    )
    (paths["formed"] / "lower-rail-shoe-v04-plan.svg").write_text(
        svg_document(
            130.0,
            85.0,
            body,
            "V0.4 lower rail shoe plan",
        ),
        encoding="utf-8",
    )


def point_to_segment_distance(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    denominator = dx * dx + dy * dy
    if denominator == 0.0:
        return math.dist(point, first)
    ratio = (
        (point[0] - first[0]) * dx
        + (point[1] - first[1]) * dy
    ) / denominator
    ratio = min(1.0, max(0.0, ratio))
    closest = (first[0] + ratio * dx, first[1] + ratio * dy)
    return math.dist(point, closest)


def edge_ligament(
    point: tuple[float, float],
    diameter: float,
    outline: list[tuple[float, float]],
) -> float:
    boundary_distance = min(
        point_to_segment_distance(point, first, second)
        for first, second in zip(outline, outline[1:] + outline[:1])
    )
    return boundary_distance - diameter / 2.0


def minimum_pair_ligament(
    groups: list[tuple[str, list[tuple[float, float]], float]],
) -> tuple[float, tuple[str, str, tuple[float, float], tuple[float, float]]]:
    best = math.inf
    detail: tuple[str, str, tuple[float, float], tuple[float, float]] | None = None
    flattened = [
        (name, point, diameter)
        for name, points, diameter in groups
        for point in points
    ]
    for index, first in enumerate(flattened):
        for second in flattened[index + 1 :]:
            gap = (
                math.dist(first[1], second[1])
                - first[2] / 2.0
                - second[2] / 2.0
            )
            if gap < best:
                best = gap
                detail = (first[0], second[0], first[1], second[1])
    if detail is None:
        raise ValueError("At least two holes are required")
    return best, detail


def minimum_envelope_gap(
    config: dict[str, Any],
    interface: dict[str, Any],
) -> tuple[float, tuple[str, str, tuple[float, float], tuple[float, float]]]:
    envelopes = config["backplate"]["hardware_envelopes"]
    return minimum_pair_ligament(
        [
            (
                "adapter",
                adapter_holes(interface),
                float(envelopes["adapter_hardware_diameter_mm"]),
            ),
            (
                "shell",
                shell_holes(config),
                float(envelopes["shell_attachment_tool_diameter_mm"]),
            ),
            (
                "shoe",
                shoe_holes(config),
                float(envelopes["shoe_fastener_tool_diameter_mm"]),
            ),
        ]
    )


def shoe_foot_clearances(
    config: dict[str, Any],
    interface: dict[str, Any],
) -> tuple[float, float]:
    foot = [
        (float(point[0]), float(point[1]))
        for point in config["lower_shoe"][
            "right_foot_local_x_v_polygon_mm"
        ]
    ]
    segments = list(zip(foot, foot[1:] + foot[:1]))
    adapter_radius = (
        float(
            config["backplate"]["hardware_envelopes"][
                "adapter_hardware_diameter_mm"
            ]
        )
        / 2.0
    )
    adapter_gap = min(
        min(
            point_to_segment_distance(point, first, second)
            for first, second in segments
        )
        - adapter_radius
        for point in adapter_holes(interface)
        if point[0] > 0.0
    )
    tap_radius = 4.2 / 2.0
    tapped_ligament = min(
        min(
            point_to_segment_distance(
                (float(point[0]), float(point[1])),
                first,
                second,
            )
            for first, second in segments
        )
        - tap_radius
        for point in config["backplate"]["shoe_attachment"][
            "right_local_x_v_centers_mm"
        ]
    )
    return adapter_gap, tapped_ligament


def base_validation(
    config: dict[str, Any],
    interface: dict[str, Any],
    socket_summary: dict[str, Any],
) -> dict[str, Any]:
    outline = backplate_polygon(interface)
    adapter_diameter = float(
        interface["aluminum_backplate"]["adapter_hole_pattern"][
            "diameter_mm"
        ]
    )
    shell_diameter = float(
        config["backplate"]["shell_attachment"]["clearance_diameter_mm"]
    )
    shoe_diameter = float(
        config["backplate"]["shoe_attachment"][
            "plate_clearance_diameter_mm"
        ]
    )
    edge_values = {
        "adapter": min(
            edge_ligament(point, adapter_diameter, outline)
            for point in adapter_holes(interface)
        ),
        "shell": min(
            edge_ligament(point, shell_diameter, outline)
            for point in shell_holes(config)
        ),
        "shoe": min(
            edge_ligament(point, shoe_diameter, outline)
            for point in shoe_holes(config)
        ),
    }
    pair_ligament, pair_detail = minimum_pair_ligament(
        [
            ("adapter", adapter_holes(interface), adapter_diameter),
            ("shell", shell_holes(config), shell_diameter),
            ("shoe", shoe_holes(config), shoe_diameter),
        ]
    )
    envelope_gap, envelope_detail = minimum_envelope_gap(config, interface)
    adapter_to_foot_gap, tapped_foot_ligament = shoe_foot_clearances(
        config,
        interface,
    )
    rails = config["rails"]
    derived_cut_length = (
        float(rails["socket_stop_reference_length_mm"])
        - float(rails["upper_seated_end_clearance_mm"])
        - float(rails["lower_shoe_standoff_mm"])
    )
    plug_config = config["lower_shoe"]["solid_plug"]
    lower_bolts = config["lower_shoe"]["rail_cross_bolts"]
    bolt_radius = float(lower_bolts["clearance_diameter_mm"]) / 2.0
    plug_start_from_tube_end = (
        float(plug_config["start_offset_from_lower_target_along_axis_mm"])
        - float(rails["lower_shoe_standoff_mm"])
    )
    plug_end_from_tube_end = (
        float(plug_config["end_offset_from_lower_target_along_axis_mm"])
        - float(rails["lower_shoe_standoff_mm"])
    )
    lower_bolt_centers = [
        float(value)
        for value in lower_bolts["centers_from_tube_lower_cut_end_mm"]
    ]
    minimum_plug_cross_hole_end_ligament = min(
        min(lower_bolt_centers) - plug_start_from_tube_end - bolt_radius,
        plug_end_from_tube_end - max(lower_bolt_centers) - bolt_radius,
    )
    derived_upper_m4_from_lower = (
        float(rails["socket_stop_reference_length_mm"])
        - (
            float(
                interface["rail_system"]["socket"]["insertion_depth_mm"]
            )
            - float(
                socket_summary["portal_construction"][
                    "socket_end_overlap_mm"
                ]
            )
        )
        + float(
            interface["rail_system"]["socket"][
                "cross_bolt_offset_from_open_end_mm"
            ]
        )
        - float(rails["lower_shoe_standoff_mm"])
    )
    thresholds = config["backplate"]["minimum_hole_edge_ligament_mm"]
    checks = {
        "interface_revision_is_v04": (
            interface["interface_revision"]
            == "CAT-HEAD-SHELL-ALUMINUM-V0.4"
        ),
        "locked_socket_opening_remains_21_mm": (
            float(
                interface["rail_system"]["socket"][
                    "printed_opening_width_mm"
                ]
            )
            == float(config["validation"]["frozen_socket_opening_mm"])
            == float(
                socket_summary["frozen_interface"][
                    "socket_opening_mm"
                ][0]
            )
        ),
        "accepted_axes_unchanged": (
            interface["rail_system"]["accepted_axes_head"]
            == socket_summary["frozen_interface"]["accepted_axes_head"]
        ),
        "accepted_lower_targets_unchanged": (
            interface["rail_system"]["lower_targets_head_mm"]
            == socket_summary["frozen_interface"][
                "lower_targets_head_mm"
            ]
        ),
        "rail_cut_length_derivation_matches": (
            abs(
                derived_cut_length
                - float(rails["finished_cut_length_mm"])
            )
            <= float(config["validation"]["rail_length_tolerance_mm"])
        ),
        "upper_m4_station_derivation_matches": (
            abs(
                derived_upper_m4_from_lower
                - float(rails["upper_m4_center_from_lower_cut_end_mm"])
            )
            <= float(config["validation"]["rail_length_tolerance_mm"])
        ),
        "stock_covers_two_rough_cuts": (
            float(rails["stock_available_mm"])
            >= float(rails["stock_required_including_two_rough_cuts_mm"])
        ),
        "adapter_holes_meet_edge_ligament": (
            edge_values["adapter"] >= float(thresholds["m6_adapter"])
        ),
        "shell_holes_meet_edge_ligament": (
            edge_values["shell"] >= float(thresholds["m5_shell"])
        ),
        "shoe_holes_meet_edge_ligament": (
            edge_values["shoe"] >= float(thresholds["m5_shoe"])
        ),
        "all_cut_holes_meet_pair_ligament": (
            pair_ligament
            >= float(
                config["backplate"][
                    "minimum_cut_hole_to_cut_hole_ligament_mm"
                ]
            )
        ),
        "hardware_and_tool_envelopes_do_not_overlap": (
            envelope_gap
            >= float(
                config["backplate"][
                    "minimum_hardware_envelope_gap_mm"
                ]
            )
        ),
        "adapter_hardware_clears_shoe_foot": (
            adapter_to_foot_gap
            >= float(
                config["backplate"][
                    "minimum_adapter_hardware_to_shoe_foot_gap_mm"
                ]
            )
        ),
        "shoe_tapped_holes_have_required_foot_ligament": (
            tapped_foot_ligament
            >= float(
                config["backplate"][
                    "minimum_tapped_hole_ligament_in_shoe_foot_mm"
                ]
            )
        ),
        "plug_cross_holes_meet_end_ligament": (
            minimum_plug_cross_hole_end_ligament
            >= float(
                config["validation"][
                    "minimum_plug_cross_hole_end_ligament_mm"
                ]
            )
        ),
        "shoe_uses_fitted_solid_anti_crush_plug": (
            float(
                config["lower_shoe"]["solid_plug"][
                    "insertion_inside_tube_mm"
                ]
            )
            >= 30.0
            and len(
                config["lower_shoe"]["rail_cross_bolts"][
                    "centers_from_tube_lower_cut_end_mm"
                ]
            )
            == 2
        ),
        "no_backplate_or_shell_rail_pass_through": (
            config["service_interface"]["backplate_rail_pass_through"]
            == "none"
            and config["service_interface"]["printed_shell_pass_through"].startswith(
                "none"
            )
        ),
    }
    return {
        "checks": checks,
        "dimensions": {
            "rail_finished_cut_length_mm": float(
                rails["finished_cut_length_mm"]
            ),
            "rail_drawing_rounded_cut_length_mm": float(
                rails["drawing_rounded_cut_length_mm"]
            ),
            "rail_finished_length_tolerance_mm": float(
                rails["finished_length_tolerance_mm"]
            ),
            "rail_upper_m4_from_lower_cut_end_mm": float(
                rails["upper_m4_center_from_lower_cut_end_mm"]
            ),
            "rail_upper_m4_from_upper_cut_end_mm": float(
                rails["upper_m4_center_from_upper_cut_end_mm"]
            ),
            "rail_lower_m5_from_lower_cut_end_mm": [
                float(value)
                for value in rails[
                    "lower_m5_centers_from_lower_cut_end_mm"
                ]
            ],
            "shoe_plug_insertion_mm": float(
                config["lower_shoe"]["solid_plug"][
                    "insertion_inside_tube_mm"
                ]
            ),
            "backplate_hole_counts": {
                "adapter_m6": len(adapter_holes(interface)),
                "shell_m5": len(shell_holes(config)),
                "shoe_m5": len(shoe_holes(config)),
            },
        },
        "derived": {
            "rail_cut_length_mm": round(derived_cut_length, 6),
            "upper_m4_from_lower_cut_end_mm": round(
                derived_upper_m4_from_lower,
                6,
            ),
            "minimum_hole_edge_ligament_mm": {
                name: round(value, 4)
                for name, value in edge_values.items()
            },
            "minimum_cut_hole_pair_ligament_mm": round(
                pair_ligament,
                4,
            ),
            "minimum_cut_hole_pair": {
                "first_group": pair_detail[0],
                "second_group": pair_detail[1],
                "first_center_mm": list(pair_detail[2]),
                "second_center_mm": list(pair_detail[3]),
            },
            "minimum_hardware_envelope_gap_mm": round(
                envelope_gap,
                4,
            ),
            "minimum_hardware_envelope_pair": {
                "first_group": envelope_detail[0],
                "second_group": envelope_detail[1],
                "first_center_mm": list(envelope_detail[2]),
                "second_center_mm": list(envelope_detail[3]),
            },
            "minimum_plug_cross_hole_end_ligament_mm": round(
                minimum_plug_cross_hole_end_ligament,
                4,
            ),
            "minimum_adapter_hardware_to_shoe_foot_gap_mm": round(
                adapter_to_foot_gap,
                4,
            ),
            "minimum_tapped_hole_ligament_in_shoe_foot_mm": round(
                tapped_foot_ligament,
                4,
            ),
        },
    }


def blender_geometry(
    config: dict[str, Any],
    interface: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    try:
        import bpy
        from mathutils import Vector
    except ImportError as error:
        raise RuntimeError(
            "V0.4 final generation requires Blender so the shell collision "
            "preflight cannot be skipped"
        ) from error

    shell_source = repo_path(config["v61_socket_blend_path"])
    current_source = Path(bpy.data.filepath).resolve()
    if current_source != shell_source:
        raise ValueError(
            "Run Blender with the locked V6.1 BLEND as the input file; "
            f"expected {shell_source}, received {current_source}"
        )

    source_dir = (
        REPO_ROOT
        / "hardware/mechanical/fabrication/3d-print/"
        "cat-head-full-size-v1/source"
    )
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    import generate_gate5_ribs_and_joints as gate5  # noqa: WPS433
    import generate_gate9_rear_architecture_comparison as comparison  # noqa: WPS433

    for obj in list(bpy.data.objects):
        if obj.name.startswith("metal_v04__"):
            bpy.data.objects.remove(obj, do_unlink=True)

    def material(
        name: str,
        color: tuple[float, float, float, float],
        metallic: float,
    ):
        value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        value.diffuse_color = color
        value.metallic = metallic
        value.roughness = 0.32
        return value

    plate_material = material(
        "metal_v04_backplate",
        (0.48, 0.58, 0.68, 1.0),
        0.8,
    )
    rail_material = material(
        "metal_v04_rails",
        (0.15, 0.39, 0.72, 1.0),
        0.75,
    )
    shoe_material = material(
        "metal_v04_shoes",
        (0.95, 0.36, 0.04, 1.0),
        0.7,
    )
    hardware_material = material(
        "metal_v04_hardware",
        (0.12, 0.12, 0.14, 1.0),
        0.9,
    )
    tool_material = material(
        "metal_v04_tool_envelopes",
        (0.82, 0.08, 0.08, 1.0),
        0.1,
    )

    plane = interface["rear_interface_plane"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    across_plate = Vector((1.0, 0.0, 0.0))
    vertical = normal.cross(across_plate).normalized()
    plate_thickness = float(
        interface["aluminum_backplate"]["thickness_mm"]
    )

    def local_point(x: float, v: float, n: float = 0.0) -> Vector:
        return center + across_plate * x + vertical * v + normal * n

    def prism(
        name: str,
        polygon: list[tuple[float, float]],
        normal_min: float,
        normal_max: float,
        assigned_material,
    ):
        count = len(polygon)
        vertices = [
            local_point(x, v, normal_min) for x, v in polygon
        ] + [
            local_point(x, v, normal_max) for x, v in polygon
        ]
        faces = [
            tuple(range(count - 1, -1, -1)),
            tuple(range(count, 2 * count)),
        ]
        for index in range(count):
            nxt = (index + 1) % count
            faces.append((index, nxt, nxt + count, index + count))
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata([tuple(value) for value in vertices], [], faces)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(assigned_material)
        gate5.require_manifold(obj, f"{name} prism")
        return obj

    def oriented_box(
        name: str,
        box_center: Vector,
        axes: tuple[Vector, Vector, Vector],
        dimensions: tuple[float, float, float],
        assigned_material,
    ):
        return gate5.box(
            name,
            box_center,
            axes,
            dimensions,
            assigned_material,
        )

    def chamfered_plug(
        name: str,
        start: Vector,
        end: Vector,
        across: Vector,
        other: Vector,
        width: float,
        long_chamfer: float,
        nose_chamfer: float,
        assigned_material,
    ):
        axis = (end - start).normalized()
        length = (end - start).length

        def profile(profile_width: float) -> list[tuple[float, float]]:
            half = profile_width / 2.0
            chamfer = min(long_chamfer, half / 2.0)
            return [
                (-half + chamfer, -half),
                (half - chamfer, -half),
                (half, -half + chamfer),
                (half, half - chamfer),
                (half - chamfer, half),
                (-half + chamfer, half),
                (-half, half - chamfer),
                (-half, -half + chamfer),
            ]

        rings = [
            (start, profile(width)),
            (end - axis * nose_chamfer, profile(width)),
            (end, profile(width - 2.0 * nose_chamfer)),
        ]
        vertices = [
            ring_center + across * x + other * y
            for ring_center, ring in rings
            for x, y in ring
        ]
        count = 8
        faces = [
            tuple(range(count - 1, -1, -1)),
            tuple(range(2 * count, 3 * count)),
        ]
        for ring_index in range(2):
            first = ring_index * count
            second = (ring_index + 1) * count
            for index in range(count):
                nxt = (index + 1) % count
                faces.append(
                    (first + index, first + nxt, second + nxt, second + index)
                )
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata([tuple(value) for value in vertices], [], faces)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(assigned_material)
        gate5.require_manifold(obj, f"{name} chamfered plug")
        return obj

    def cut_cylinder(
        obj,
        name: str,
        first: Vector,
        second: Vector,
        diameter: float,
    ) -> None:
        cutter = gate5.cylinder(
            name,
            first,
            second,
            diameter,
            vertices=24,
        )
        gate5.apply_boolean(obj, cutter, "DIFFERENCE", solver="MANIFOLD")
        gate5.require_manifold(obj, f"{obj.name} {name} cut")

    backplate = prism(
        "metal_v04__backplate",
        backplate_polygon(interface),
        -plate_thickness / 2.0,
        plate_thickness / 2.0,
        plate_material,
    )
    hole_sets = [
        (
            "adapter",
            adapter_holes(interface),
            float(
                interface["aluminum_backplate"]["adapter_hole_pattern"][
                    "diameter_mm"
                ]
            ),
        ),
        (
            "shell",
            shell_holes(config),
            float(
                config["backplate"]["shell_attachment"][
                    "clearance_diameter_mm"
                ]
            ),
        ),
        (
            "shoe",
            shoe_holes(config),
            float(
                config["backplate"]["shoe_attachment"][
                    "plate_clearance_diameter_mm"
                ]
            ),
        ),
    ]
    for group, points, diameter in hole_sets:
        for index, (x, v) in enumerate(points):
            cut_cylinder(
                backplate,
                f"metal_v04__backplate_{group}_{index:02d}",
                local_point(x, v, -plate_thickness),
                local_point(x, v, plate_thickness),
                diameter,
            )

    objects: dict[str, Any] = {"backplate": backplate}
    lower_service_envelopes: dict[str, Any] = {}
    rail_values = config["rails"]
    shoe_values = config["lower_shoe"]
    tube_size = float(
        interface["rail_system"]["profile"]["outside_width_mm"]
    )
    rail_length = float(rail_values["finished_cut_length_mm"])
    standoff = float(rail_values["lower_shoe_standoff_mm"])
    plug = shoe_values["solid_plug"]
    stop = shoe_values["rail_stop"]
    right_foot = [
        (float(point[0]), float(point[1]))
        for point in shoe_values["right_foot_local_x_v_polygon_mm"]
    ]
    right_shoe_holes = [
        (float(point[0]), float(point[1]))
        for point in config["backplate"]["shoe_attachment"][
            "right_local_x_v_centers_mm"
        ]
    ]
    all_printed = {
        name: bpy.data.objects[name]
        for name in (
            "gate9_frame_candidate__left_lower_face",
            "gate9_frame_candidate__left_upper_head",
            "gate9_frame_candidate__right_lower_face",
            "gate9_frame_candidate__right_upper_head",
            "gate9_v5__rear_bezel",
            "gate9_v5__bottom_keel",
        )
    }

    for side in ("left", "right"):
        sign = -1.0 if side == "left" else 1.0
        lower = Vector(
            interface["rail_system"]["lower_targets_head_mm"][side]
        )
        axis = Vector(
            interface["rail_system"]["accepted_axes_head"][side]
        ).normalized()
        across = (
            Vector((1.0, 0.0, 0.0))
            - axis * Vector((1.0, 0.0, 0.0)).dot(axis)
        ).normalized()
        other = axis.cross(across).normalized()

        rail_start = lower + axis * standoff
        rail = oriented_box(
            f"metal_v04__rail_{side}",
            rail_start + axis * (rail_length / 2.0),
            (across, other, axis),
            (tube_size, tube_size, rail_length),
            rail_material,
        )
        for index, offset in enumerate(
            rail_values["lower_m5_centers_from_lower_cut_end_mm"]
        ):
            hole_center = rail_start + axis * float(offset)
            cut_cylinder(
                rail,
                f"metal_v04__rail_{side}_lower_m5_{index:02d}",
                hole_center - across * 15.0,
                hole_center + across * 15.0,
                float(
                    shoe_values["rail_cross_bolts"][
                        "clearance_diameter_mm"
                    ]
                ),
            )
        upper_center = (
            rail_start
            + axis
            * float(
                rail_values["upper_m4_center_from_lower_cut_end_mm"]
            )
        )
        cut_cylinder(
            rail,
            f"metal_v04__rail_{side}_upper_m4",
            upper_center - across * 15.0,
            upper_center + across * 15.0,
            float(
                interface["rail_system"]["socket"][
                    "cross_bolt_clearance_diameter_mm"
                ]
            ),
        )

        foot_polygon = [
            (sign * x, v) for x, v in right_foot
        ]
        if side == "left":
            foot_polygon.reverse()
        foot = prism(
            f"metal_v04__shoe_{side}",
            foot_polygon,
            -plate_thickness / 2.0
            - float(shoe_values["foot_thickness_mm"]),
            -plate_thickness / 2.0,
            shoe_material,
        )
        plug_start = float(plug["start_offset_from_lower_target_along_axis_mm"])
        plug_end = float(plug["end_offset_from_lower_target_along_axis_mm"])
        tongue = chamfered_plug(
            f"metal_v04__shoe_{side}_plug",
            lower + axis * plug_start,
            lower + axis * plug_end,
            across,
            other,
            float(plug["nominal_width_mm"]),
            float(plug["long_edge_chamfer_mm"]),
            float(plug["nose_chamfer_mm"]),
            shoe_material,
        )
        gate5.apply_boolean(foot, tongue, "UNION", solver="MANIFOLD")
        gate5.require_manifold(foot, f"{side} shoe foot/plug union")
        collar_start = float(stop["collar_start_offset_mm"])
        collar_end = float(stop["collar_end_offset_mm"])
        collar = oriented_box(
            f"metal_v04__shoe_{side}_collar",
            lower + axis * ((collar_start + collar_end) / 2.0),
            (across, other, axis),
            (
                float(stop["collar_across_axis_width_mm"]),
                float(stop["collar_other_axis_height_mm"]),
                collar_end - collar_start,
            ),
            shoe_material,
        )
        gate5.apply_boolean(foot, collar, "UNION", solver="MANIFOLD")
        gate5.require_manifold(foot, f"{side} shoe collar union")

        current_shoe_holes = [
            (sign * x, v) for x, v in right_shoe_holes
        ]
        tap_diameter = 4.2
        tap_depth = float(
            config["backplate"]["shoe_attachment"][
                "shoe_blind_tap_depth_mm"
            ]
        )
        for index, (x, v) in enumerate(current_shoe_holes):
            cut_cylinder(
                foot,
                f"metal_v04__shoe_{side}_tap_{index:02d}",
                local_point(x, v, -plate_thickness / 2.0 + 0.5),
                local_point(
                    x,
                    v,
                    -plate_thickness / 2.0 - tap_depth,
                ),
                tap_diameter,
            )
        for index, offset in enumerate(
            shoe_values["rail_cross_bolts"][
                "centers_from_tube_lower_cut_end_mm"
            ]
        ):
            hole_center = (
                lower
                + axis
                * (
                    standoff
                    + float(offset)
                )
            )
            cut_cylinder(
                foot,
                f"metal_v04__shoe_{side}_cross_m5_{index:02d}",
                hole_center - across * 15.0,
                hole_center + across * 15.0,
                float(
                    shoe_values["rail_cross_bolts"][
                        "clearance_diameter_mm"
                    ]
                ),
            )

        objects[f"rail_{side}"] = rail
        objects[f"shoe_{side}"] = foot
        comparison.export_stl(
            foot,
            paths["formed"] / f"lower-rail-shoe-{side}-v04.stl",
        )

        bolt_values = shoe_values["rail_cross_bolts"]
        center_side = -1.0 if side == "right" else 1.0
        tube_half = tube_size / 2.0
        head_stack = float(
            bolt_values["head_washer_stack_thickness_mm"]
        )
        nut_stack = float(
            bolt_values["nut_washer_stack_thickness_mm"]
        )
        tool_length = float(
            bolt_values["straight_tool_approach_length_mm"]
        )
        tool_diameter = float(
            bolt_values["straight_tool_approach_diameter_mm"]
        )
        for index, offset in enumerate(
            rail_values["lower_m5_centers_from_lower_cut_end_mm"]
        ):
            bolt_center = rail_start + axis * float(offset)
            bolt_body = gate5.cylinder(
                f"metal_v04__lower_m5_{side}_{index:02d}_body",
                bolt_center - across * 16.0,
                bolt_center + across * 16.0,
                5.0,
                hardware_material,
                vertices=24,
            )
            center_face = bolt_center + across * center_side * tube_half
            outer_face = bolt_center - across * center_side * tube_half
            head_outer = center_face + across * center_side * head_stack
            nut_outer = outer_face - across * center_side * nut_stack
            head = gate5.cylinder(
                f"metal_v04__lower_m5_{side}_{index:02d}_head_washer",
                center_face,
                head_outer,
                float(bolt_values["head_washer_envelope_diameter_mm"]),
                hardware_material,
                vertices=24,
            )
            nut = gate5.cylinder(
                f"metal_v04__lower_m5_{side}_{index:02d}_nut_washer",
                outer_face,
                nut_outer,
                float(bolt_values["nut_washer_envelope_diameter_mm"]),
                hardware_material,
                vertices=24,
            )
            head_tool = gate5.cylinder(
                f"metal_v04__lower_m5_{side}_{index:02d}_head_tool",
                head_outer,
                head_outer + across * center_side * tool_length,
                tool_diameter,
                tool_material,
                vertices=24,
            )
            nut_tool = gate5.cylinder(
                f"metal_v04__lower_m5_{side}_{index:02d}_nut_tool",
                nut_outer,
                nut_outer - across * center_side * tool_length,
                tool_diameter,
                tool_material,
                vertices=24,
            )
            objects[f"lower_m5_{side}_{index}_body"] = bolt_body
            objects[f"lower_m5_{side}_{index}_head"] = head
            objects[f"lower_m5_{side}_{index}_nut"] = nut
            lower_service_envelopes[
                f"lower_m5_{side}_{index}_body"
            ] = bolt_body
            lower_service_envelopes[
                f"lower_m5_{side}_{index}_head_washer"
            ] = head
            lower_service_envelopes[
                f"lower_m5_{side}_{index}_nut_washer"
            ] = nut
            lower_service_envelopes[
                f"lower_m5_{side}_{index}_head_tool"
            ] = head_tool
            lower_service_envelopes[
                f"lower_m5_{side}_{index}_nut_tool"
            ] = nut_tool

    printed_collision_records: dict[str, Any] = {}
    for metal_name in (
        "backplate",
        "rail_left",
        "rail_right",
        "shoe_left",
        "shoe_right",
    ):
        metal = objects[metal_name]
        printed_collision_records[metal_name] = {
            printed_name: comparison.collision_record(metal, printed)
            for printed_name, printed in all_printed.items()
        }
    backplate_expected_clear = all(
        not record["intersects"]
        for record in printed_collision_records["backplate"].values()
    )
    fixed_shell_names = (
        "gate9_frame_candidate__left_lower_face",
        "gate9_frame_candidate__left_upper_head",
        "gate9_frame_candidate__right_lower_face",
        "gate9_frame_candidate__right_upper_head",
        "gate9_v5__bottom_keel",
    )
    lower_service_collision_records = {
        name: {
            printed: comparison.collision_record(envelope, all_printed[printed])
            for printed in fixed_shell_names
        }
        for name, envelope in lower_service_envelopes.items()
    }
    lower_service_fixed_shell_clear = all(
        not record["intersects"]
        for records in lower_service_collision_records.values()
        for record in records.values()
    )
    minimum_lower_service_fixed_shell_clearance = min(
        float(record["minimum_sampled_vertex_to_surface_distance_mm"])
        for records in lower_service_collision_records.values()
        for record in records.values()
    )
    shoe_fixed_shell_clear = all(
        not printed_collision_records[name][printed]["intersects"]
        for name in ("shoe_left", "shoe_right")
        for printed in fixed_shell_names
    )
    rear_bezel_shoe_overlap_pairs = sum(
        int(
            printed_collision_records[name]["gate9_v5__rear_bezel"][
                "triangle_overlap_pair_count"
            ]
        )
        for name in ("shoe_left", "shoe_right")
    )
    rail_expected_clear = all(
        not record["intersects"]
        for name in ("rail_left", "rail_right")
        for record in printed_collision_records[name].values()
    )
    service_names = ("gate9_v5__rear_bezel", "gate9_v5__bottom_keel")
    minimum_shoe_fixed_shell_clearance = min(
        float(
            printed_collision_records[name]["gate9_v5__bottom_keel"][
                "minimum_sampled_vertex_to_surface_distance_mm"
            ]
        )
        for name in ("shoe_left", "shoe_right")
    )
    minimum_rail_service_clearance = min(
        float(printed_collision_records[name][printed]["minimum_sampled_vertex_to_surface_distance_mm"])
        for name in ("rail_left", "rail_right")
        for printed in service_names
    )
    checks = {
        "backplate_clears_current_v61_printed_parts": backplate_expected_clear,
        "final_shoes_clear_current_v61_fixed_shell_and_keel": shoe_fixed_shell_clear,
        "current_rear_bezel_shoe_conflict_is_isolated_and_recorded": (
            shoe_fixed_shell_clear and rear_bezel_shoe_overlap_pairs > 0
        ),
        "final_rails_clear_current_v61_printed_parts": rail_expected_clear,
        "lower_m5_hardware_and_tools_clear_fixed_shell_and_keel": (
            lower_service_fixed_shell_clear
        ),
        "final_shoes_clear_fixed_bottom_keel_by_minimum": (
            minimum_shoe_fixed_shell_clearance
            >= float(
                config["validation"][
                    "minimum_shoe_to_shell_sampled_clearance_mm"
                ]
            )
        ),
        "final_rails_clear_service_parts_by_minimum": (
            minimum_rail_service_clearance
            >= float(
                config["validation"][
                    "minimum_rail_to_shell_sampled_clearance_mm"
                ]
            )
        ),
    }

    keep_visible = set(all_printed.values()) | set(objects.values())
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            visible = obj in keep_visible
            obj.hide_render = not visible
            obj.hide_viewport = not visible

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.9, 0.92, 0.94)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100

    def render(
        name: str,
        location: tuple[float, float, float],
        target: tuple[float, float, float],
        hidden: set[Any] | None = None,
        lens: float = 55.0,
    ) -> None:
        hidden = hidden or set()
        prior = {obj: obj.hide_render for obj in hidden}
        for obj in hidden:
            obj.hide_render = True
        bpy.ops.object.camera_add(location=location)
        camera = bpy.context.object
        camera.data.lens = lens
        camera.rotation_euler = (
            Vector(target) - camera.location
        ).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.render.filepath = str(paths["renders"] / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera, do_unlink=True)
        for obj, value in prior.items():
            obj.hide_render = value

    shell_objects = set(all_printed.values())
    render(
        "v04-shell-integration-rear",
        (245.0, 520.0, 240.0),
        (0.0, 240.0, 175.0),
    )
    render(
        "v04-metal-and-shoes-rear",
        (220.0, 500.0, 220.0),
        (0.0, 240.0, 170.0),
        hidden=shell_objects,
    )
    render(
        "v04-right-shoe-detail",
        (145.0, 365.0, 135.0),
        (40.0, 260.0, 150.0),
        hidden=shell_objects
        | {
            objects["rail_left"],
            objects["shoe_left"],
        },
        lens=62.0,
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=str(
            paths["model"] / "frame-fixed-mount-v04-final-review.blend"
        )
    )
    backup = (
        paths["model"] / "frame-fixed-mount-v04-final-review.blend1"
    )
    backup.unlink(missing_ok=True)
    return {
        "status": (
            "PASS - V0.4 METAL PREFLIGHT; CURRENT REAR BEZEL REINTEGRATION REQUIRED"
            if all(checks.values())
            else "FAIL"
        ),
        "checks": checks,
        "minimum_sampled_service_clearance_mm": {
            "shoe_to_fixed_bottom_keel": round(
                minimum_shoe_fixed_shell_clearance,
                4,
            ),
            "rail_to_rear_bezel_or_bottom_keel": round(
                minimum_rail_service_clearance,
                4,
            ),
            "lower_m5_hardware_or_tool_to_fixed_shell": round(
                minimum_lower_service_fixed_shell_clearance,
                4,
            ),
        },
        "current_rear_bezel_shoe_overlap_pair_count": rear_bezel_shoe_overlap_pairs,
        "required_shell_followup": "regenerate the rear bezel and six ASA structural pads from this exact V0.4 metal handoff, then rerun A-39",
        "lower_m5_hardware_and_tool_collision_records": (
            lower_service_collision_records
        ),
        "collision_records": printed_collision_records,
    }


def main() -> None:
    config, interface, socket_summary = load_inputs()
    paths = output_paths(config)
    write_backplate_outputs(config, interface, paths)
    write_rail_output(config, paths)
    write_shoe_output(config, paths)
    validation = base_validation(config, interface, socket_summary)
    geometry = blender_geometry(config, interface, paths)
    all_checks = {
        **validation["checks"],
        **geometry["checks"],
    }
    passed = all(all_checks.values())
    report = {
        "schema_version": 1,
        "status": (
            "PASS - V0.4 ALUMINUM-SIDE INTERFACE DIGITALLY FINALIZED"
            if passed
            else "FAIL"
        ),
        "release_status": (
            "NOT A FABRICATION OR RIDING RELEASE; HANDOFF TO SHELL "
            "INTEGRATION AND PHYSICAL VALIDATION"
        ),
        "interface_revision": interface["interface_revision"],
        "socket_geometry_policy": (
            "unchanged V6.1 21.0 mm straight socket opening, 1.0 mm "
            "lead-in, 30.0 mm insertion depth, and frozen axes/targets"
        ),
        "checks": all_checks,
        "dimensions": validation["dimensions"],
        "derived": validation["derived"],
        "lower_shoe": config["lower_shoe"],
        "backplate": config["backplate"],
        "rails": config["rails"],
        "service_interface": config["service_interface"],
        "current_v61_shell_collision_preflight": geometry,
        "review_outputs": {
            "backplate_svg": str(
                (
                    paths["flat"]
                    / "head-rear-backplate-v04-1to1.svg"
                ).relative_to(REPO_ROOT)
            ),
            "backplate_dxf": str(
                (
                    paths["flat"] / "head-rear-backplate-v04.dxf"
                ).relative_to(REPO_ROOT)
            ),
            "rail_drawing": str(
                (
                    paths["rails"]
                    / "rail-cut-and-drill-v04-1to1.svg"
                ).relative_to(REPO_ROOT)
            ),
            "shoe_drawing": str(
                (
                    paths["formed"]
                    / "lower-rail-shoe-v04-plan.svg"
                ).relative_to(REPO_ROOT)
            ),
            "review_blend": str(
                (
                    paths["model"]
                    / "frame-fixed-mount-v04-final-review.blend"
                ).relative_to(REPO_ROOT)
            ),
            "renders": [
                str(path.relative_to(REPO_ROOT))
                for path in sorted(paths["renders"].glob("v04-*.png"))
            ],
        },
        "release_holds": config["release_holds"],
    }
    serialized = json.dumps(report, indent=2) + "\n"
    (paths["validation"] / "frame-fixed-mount-v04-validation.json").write_text(
        serialized,
        encoding="utf-8",
    )
    tracked_report = json.loads(serialized)
    tracked_collision = tracked_report[
        "current_v61_shell_collision_preflight"
    ]
    tracked_collision["full_collision_record_location"] = str(
        (
            paths["validation"]
            / "frame-fixed-mount-v04-validation.json"
        ).relative_to(REPO_ROOT)
    )
    tracked_collision["collision_record_counts"] = {
        "metal_parts": len(tracked_collision["collision_records"]),
        "lower_m5_hardware_and_tools": len(
            tracked_collision[
                "lower_m5_hardware_and_tool_collision_records"
            ]
        ),
    }
    tracked_collision.pop("collision_records")
    tracked_collision.pop(
        "lower_m5_hardware_and_tool_collision_records"
    )
    REVIEW_PATH.write_text(
        json.dumps(tracked_report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(serialized)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
