#!/usr/bin/env python3
"""Generate the finalized aluminum-side CAT-HEAD-SHELL-ALUMINUM-V0.4 handoff.

Run against the locked V6.1 socket assembly:

    blender --background \
      ../../3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
      --python source/generate_frame_fixed_mount_v04.py

The generated geometry records the aluminum-side rail, ordered-angle connector, anti-crush, and
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
        "formed": root / "hand-fabricated-parts",
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
        "purple 4x dia6.6 adapter | blue 6x dia5.5 shell | orange 6x dia5.5 angle bases",
    )
    body += svg_text(
        -59,
        -48,
        "V0.4-M2 ORDERED-ANGLE METAL-SIDE PATTERN; PHYSICAL COUPON + ASA INTEGRATION REQUIRED",
        "warn",
    )
    (paths["flat"] / "head-rear-backplate-v04-1to1.svg").write_text(
        svg_document(
            320.0,
            115.0,
            body,
            "V0.4-M2 ordered-angle aluminum backplate 1:1",
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
    upper = float(rails["upper_m4_center_from_lower_cut_end_mm"])
    longest = float(rails["compound_cut_longest_edge_mm"])
    shortest = float(rails["compound_cut_shortest_edge_mm"])
    body = (
        f'<rect class="outline" x="0" y="-9.5" '
        f'width="{number(length)}" height="19"/>'
    )
    body += (
        f'<line class="dim" x1="0" y1="-9.5" x2="{number(longest-length)}" y2="9.5"/>'
    )
    for offset in rails["lower_m5_centers_from_lower_cut_end_mm"]:
        x = float(offset)
        body += svg_circle(x, 0.0, 5.5, "shoe")
        body += svg_text(x - 4.5, -15.0, f"M5 @ {float(offset):g}")
    body += svg_circle(upper, 0.0, 4.5, "shell")
    body += svg_text(upper - 8.0, 14.0, f"M4 @ {upper:.3f}")
    body += svg_text(
        -155.0,
        28.0,
        f"2x 19 x 19 x 2 tube | centerline {length:.1f} +/-0.25 | rough square cut 160",
    )
    body += svg_text(
        -155.0,
        23.0,
        f"compound lower end: longest {longest:.3f}, shortest {shortest:.3f}; upper end square",
    )
    body += svg_text(
        -155.0,
        -25.0,
        "Fit/label solid plug, clamp rail on its angle bearing face, then transfer-drill complete stack",
        "warn",
    )
    body += svg_text(
        -155.0,
        -30.0,
        "Do not mark M5 stations from an arbitrary compound-cut corner: datum is bearing-plane centerline",
        "warn",
    )
    (paths["rails"] / "rail-cut-and-drill-v04-m2-1to1.svg").write_text(
        svg_document(330.0, 82.0, body, "V0.4-M2 rail compound cut and drill drawing"),
        encoding="utf-8",
    )
    wrap_body = ""
    face_y = [-38.0, -19.0, 0.0, 19.0, 38.0]
    for side, base_x in (("LEFT", -34.0), ("RIGHT", 34.0)):
        key = f"{side.lower()}_compound_corner_offsets_from_bearing_centerline_mm"
        offsets = [float(value) for value in rails[key]]
        closed = offsets + [offsets[0]]
        points = " ".join(
            f"{number(base_x + offset)},{number(y_value)}"
            for offset, y_value in zip(closed, face_y)
        )
        wrap_body += f'<polyline class="dim" points="{points}"/>'
        wrap_body += f'<line class="center" x1="{number(base_x)}" y1="-38" x2="{number(base_x)}" y2="38"/>'
        for y_value in face_y:
            wrap_body += f'<line class="center" x1="{number(base_x - 12)}" y1="{number(y_value)}" x2="{number(base_x + 12)}" y2="{number(y_value)}"/>'
        wrap_body += svg_text(base_x - 13.0, 47.0, f"{side} RAIL")
        wrap_body += svg_text(base_x - 13.0, -48.0, "seam / inner-low")
    wrap_body += svg_text(-150.0, 58.0, "1:1 COMPOUND LOWER-CUT WRAP | four 19 mm faces | dashed vertical = bearing centerline")
    wrap_body += svg_text(-150.0, 53.0, "Face order from seam: inner-low, outer-low, outer-high, inner-high, back to seam")
    wrap_body += svg_text(-150.0, -58.0, "Fit plug first; wrap/mark matched rail+plug; leave proud and hand-fit to full angle-base contact", "warn")
    wrap_body += '<line class="dim" x1="-25" y1="-67" x2="25" y2="-67"/>'
    wrap_body += svg_text(-25.0, -72.0, "50 mm PRINT-CALIBRATION LINE")
    (paths["rails"] / "rail-lower-compound-wrap-v04-m2-1to1.svg").write_text(
        svg_document(330.0, 155.0, wrap_body, "V0.4-M2 compound lower-cut wrap template"),
        encoding="utf-8",
    )


def write_angle_connector_output(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    connector = config["lower_shoe"]
    angle = connector["primary_angle"]
    stock = connector["ordered_stock"]
    cheek = connector["outer_clamp_cheek"]
    length = float(angle["segment_length_mm"])
    base = float(angle["base_leg_finished_width_mm"])
    upright = float(angle["upright_leg_finished_depth_mm"])
    thickness = float(stock["thickness_mm"])
    body = (
        f'<rect class="outline" x="-22.5" y="0" width="{number(length)}" height="{number(base)}"/>'
    )
    body += svg_text(
        -160.0,
        44.0,
        "HOLES ARE DELIBERATELY OMITTED: clamp each angle to the drilled backplate and transfer all three centers",
        "warn",
    )
    body += svg_text(
        -160.0,
        39.0,
        f"PRIMARY ANGLE: 2x {length:g} long; retain {upright:g} upright; trim base to {base:g}",
    )
    body += svg_text(
        -160.0,
        34.0,
        f"ORDERED STOCK: 6063-T6 equal angle {float(stock['leg_width_mm']):g} x {float(stock['leg_width_mm']):g} x {thickness:g}",
    )
    body += svg_text(
        -160.0,
        -9.0,
        "Use the three retained backplate centers: clamp to plate, transfer, 5.5 through, 90-deg countersink",
    )
    body += svg_text(
        -160.0,
        -14.0,
        f"OUTER CHEEKS: 2x {float(cheek['finished_length_mm']):g} x {float(cheek['finished_width_mm']):g} x {float(cheek['thickness_mm']):g}",
    )
    body += svg_text(
        -160.0,
        -19.0,
        "M5 crossbolts at 14 and 29 from bearing centerline; hand-fit two metal tapered spacers per rail",
        "warn",
    )
    body += svg_text(
        -160.0,
        -24.0,
        "Cut one receipt/fit coupon before final parts; printed structural shims are prohibited",
        "warn",
    )
    (paths["formed"] / "lower-angle-connector-v04-m2-plan.svg").write_text(
        svg_document(340.0, 90.0, body, "V0.4-M2 ordered-angle connector plan"),
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
    groups = [
        (
            "adapter",
            adapter_holes(interface),
            float(envelopes["adapter_hardware_diameter_mm"]),
            float(envelopes["adapter_hardware_diameter_mm"]),
        ),
        (
            "shell",
            shell_holes(config),
            float(envelopes["shell_attachment_tool_diameter_mm"]),
            float(config["backplate"]["shell_attachment"]["washer_outer_diameter_mm"]),
        ),
        (
            "angle_base",
            shoe_holes(config),
            float(envelopes["shoe_fastener_tool_diameter_mm"]),
            float(config["backplate"]["shoe_attachment"]["rear_washer_outer_diameter_mm"]),
        ),
    ]
    flattened = [
        (name, point, tool_diameter, static_diameter)
        for name, points, tool_diameter, static_diameter in groups
        for point in points
    ]
    best = math.inf
    detail = None
    for index, first in enumerate(flattened):
        for second in flattened[index + 1 :]:
            center_distance = math.dist(first[1], second[1])
            # Only one socket/driver is used at a time. Check its outside
            # radius against the already-installed neighboring washer/nut,
            # rather than requiring two simultaneous tool envelopes.
            first_tool_gap = center_distance - first[2] / 2.0 - second[3] / 2.0
            second_tool_gap = center_distance - first[3] / 2.0 - second[2] / 2.0
            gap = min(first_tool_gap, second_tool_gap)
            if gap < best:
                best = gap
                detail = (first[0], second[0], first[1], second[1])
    if detail is None:
        raise ValueError("At least two fastener locations are required")
    return best, detail


def base_validation(
    config: dict[str, Any],
    interface: dict[str, Any],
    socket_summary: dict[str, Any],
) -> dict[str, Any]:
    outline = backplate_polygon(interface)
    adapter_diameter = float(
        interface["aluminum_backplate"]["adapter_hole_pattern"]["diameter_mm"]
    )
    shell_diameter = float(
        config["backplate"]["shell_attachment"]["clearance_diameter_mm"]
    )
    angle_hole_diameter = float(
        config["backplate"]["shoe_attachment"]["plate_clearance_diameter_mm"]
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
        "angle_base": min(
            edge_ligament(point, angle_hole_diameter, outline)
            for point in shoe_holes(config)
        ),
    }
    pair_ligament, pair_detail = minimum_pair_ligament(
        [
            ("adapter", adapter_holes(interface), adapter_diameter),
            ("shell", shell_holes(config), shell_diameter),
            ("angle_base", shoe_holes(config), angle_hole_diameter),
        ]
    )
    envelope_gap, envelope_detail = minimum_envelope_gap(config, interface)

    def dot(first: list[float], second: list[float]) -> float:
        return sum(a * b for a, b in zip(first, second))

    def sub(first: list[float], second: list[float]) -> list[float]:
        return [a - b for a, b in zip(first, second)]

    def add(first: list[float], second: list[float]) -> list[float]:
        return [a + b for a, b in zip(first, second)]

    def mul(value: list[float], scalar: float) -> list[float]:
        return [component * scalar for component in value]

    def norm(value: list[float]) -> float:
        return math.sqrt(dot(value, value))

    def unit(value: list[float]) -> list[float]:
        length = norm(value)
        return [component / length for component in value]

    def cross(first: list[float], second: list[float]) -> list[float]:
        return [
            first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
        ]

    plane = interface["rear_interface_plane"]
    plane_center = [float(value) for value in plane["center_head_mm"]]
    plane_normal = unit([float(value) for value in plane["outward_normal_head"]])
    rails = config["rails"]
    connector = config["lower_shoe"]
    bearing_offset = float(
        connector["compound_bearing"]["angle_bearing_face_offset_mm"]
    )
    upper_t = (
        float(rails["socket_stop_reference_length_mm"])
        - float(rails["upper_seated_end_clearance_mm"])
    )
    side = "right"
    lower = [
        float(value)
        for value in interface["rail_system"]["lower_targets_head_mm"][side]
    ]
    axis = unit(
        [
            float(value)
            for value in interface["rail_system"]["accepted_axes_head"][side]
        ]
    )
    axis_dot_normal = dot(axis, plane_normal)
    bearing_t = (
        bearing_offset - dot(sub(lower, plane_center), plane_normal)
    ) / axis_dot_normal
    x_axis = [1.0, 0.0, 0.0]
    across = unit(sub(x_axis, mul(axis, dot(x_axis, axis))))
    other = unit(cross(axis, across))
    half = float(interface["rail_system"]["profile"]["outside_width_mm"]) / 2.0
    corner_t = []
    for across_sign in (-1.0, 1.0):
        for other_sign in (-1.0, 1.0):
            corner = add(
                mul(across, across_sign * half),
                mul(other, other_sign * half),
            )
            t_value = (
                bearing_offset
                - dot(sub(add(lower, corner), plane_center), plane_normal)
            ) / axis_dot_normal
            corner_t.append(t_value)
    edge_lengths = [upper_t - value for value in corner_t]
    longest_edge = max(edge_lengths)
    shortest_edge = min(edge_lengths)
    derived_cut_length = upper_t - bearing_t
    socket = interface["rail_system"]["socket"]
    derived_upper_m4_absolute = (
        float(rails["socket_stop_reference_length_mm"])
        - (
            float(socket["insertion_depth_mm"])
            - float(socket_summary["portal_construction"]["socket_end_overlap_mm"])
        )
        + float(socket["cross_bolt_offset_from_open_end_mm"])
    )
    derived_upper_m4_from_lower = derived_upper_m4_absolute - bearing_t
    lower_bolts = connector["rail_cross_bolts"]
    bolt_radius = float(lower_bolts["clearance_diameter_mm"]) / 2.0
    bolt_centers = [
        float(value)
        for value in lower_bolts["centers_from_bearing_plane_centerline_mm"]
    ]
    plug_length = float(
        connector["solid_plug"]["bearing_centerline_to_upper_end_mm"]
    )
    compound_intrusion = max(corner_t) - bearing_t
    minimum_plug_insertion = plug_length - compound_intrusion
    minimum_plug_cross_hole_end_ligament = min(
        min(bolt_centers) - compound_intrusion - bolt_radius,
        plug_length - max(bolt_centers) - bolt_radius,
    )
    angle = connector["primary_angle"]
    stock = connector["ordered_stock"]
    stock_plan = connector["stock_plan"]
    angle_base_hole_ligament = float(
        angle["minimum_retained_plate_hole_ligament_mm"]
    )
    thresholds = config["backplate"]["minimum_hole_edge_ligament_mm"]
    dimension_tolerance = float(config["validation"]["rail_length_tolerance_mm"])
    checks = {
        "interface_revision_is_v04": (
            interface["interface_revision"] == "CAT-HEAD-SHELL-ALUMINUM-V0.4"
        ),
        "locked_socket_opening_remains_21_mm": (
            float(socket["printed_opening_width_mm"])
            == float(config["validation"]["frozen_socket_opening_mm"])
            == float(socket_summary["frozen_interface"]["socket_opening_mm"][0])
        ),
        "accepted_axes_unchanged": (
            interface["rail_system"]["accepted_axes_head"]
            == socket_summary["frozen_interface"]["accepted_axes_head"]
        ),
        "accepted_lower_targets_unchanged": (
            interface["rail_system"]["lower_targets_head_mm"]
            == socket_summary["frozen_interface"]["lower_targets_head_mm"]
        ),
        "rail_centerline_length_derivation_matches": (
            abs(derived_cut_length - float(rails["finished_cut_length_mm"]))
            <= dimension_tolerance
        ),
        "compound_edge_lengths_match": (
            abs(longest_edge - float(rails["compound_cut_longest_edge_mm"]))
            <= dimension_tolerance
            and abs(shortest_edge - float(rails["compound_cut_shortest_edge_mm"]))
            <= dimension_tolerance
        ),
        "upper_m4_station_derivation_matches": (
            abs(
                derived_upper_m4_from_lower
                - float(rails["upper_m4_center_from_lower_cut_end_mm"])
            )
            <= dimension_tolerance
        ),
        "rail_stock_covers_two_rough_cuts": (
            float(rails["stock_available_mm"])
            >= float(rails["stock_required_including_two_rough_cuts_mm"])
        ),
        "ordered_angle_stock_covers_four_segments": (
            float(stock["ordered_length_mm"])
            >= 4.0 * float(stock_plan["segment_finished_length_mm"])
        ),
        "ordered_angle_dimensions_are_modeled": (
            abs(float(stock["leg_width_mm"]) - 38.1) < 0.001
            and abs(float(stock["thickness_mm"]) - 3.175) < 0.001
            and abs(float(angle["segment_length_mm"]) - 45.0) < 0.001
            and abs(float(angle["base_leg_finished_width_mm"]) - 29.0) < 0.001
        ),
        "adapter_holes_meet_edge_ligament": (
            edge_values["adapter"] >= float(thresholds["m6_adapter"])
        ),
        "shell_holes_meet_edge_ligament": (
            edge_values["shell"] >= float(thresholds["m5_shell"])
        ),
        "angle_base_holes_meet_backplate_edge_ligament": (
            edge_values["angle_base"] >= float(thresholds["m5_shoe"])
        ),
        "all_cut_holes_meet_pair_ligament": (
            pair_ligament
            >= float(config["backplate"]["minimum_cut_hole_to_cut_hole_ligament_mm"])
        ),
        "sequential_tool_envelopes_clear_installed_neighbor_hardware": (
            envelope_gap
            >= float(config["backplate"]["minimum_hardware_envelope_gap_mm"])
        ),
        "angle_base_holes_meet_part_ligament": (
            angle_base_hole_ligament
            >= float(config["validation"]["minimum_angle_base_hole_ligament_mm"])
        ),
        "plug_cross_holes_meet_end_ligament": (
            minimum_plug_cross_hole_end_ligament
            >= float(config["validation"]["minimum_plug_cross_hole_end_ligament_mm"])
        ),
        "connector_uses_fitted_solid_anti_crush_plug": (
            minimum_plug_insertion >= 39.592 - dimension_tolerance
            and len(bolt_centers) == 2
        ),
        "no_backplate_or_shell_rail_pass_through": (
            config["service_interface"]["backplate_rail_pass_through"] == "none"
            and config["service_interface"]["printed_shell_pass_through"].startswith("none")
        ),
    }
    return {
        "checks": checks,
        "dimensions": {
            "rail_centerline_finished_length_mm": float(rails["finished_cut_length_mm"]),
            "rail_drawing_rounded_centerline_length_mm": float(
                rails["drawing_rounded_cut_length_mm"]
            ),
            "rail_compound_longest_edge_mm": float(
                rails["compound_cut_longest_edge_mm"]
            ),
            "rail_compound_shortest_edge_mm": float(
                rails["compound_cut_shortest_edge_mm"]
            ),
            "rail_upper_m4_from_bearing_centerline_mm": float(
                rails["upper_m4_center_from_lower_cut_end_mm"]
            ),
            "rail_lower_m5_from_bearing_centerline_mm": bolt_centers,
            "solid_plug_minimum_physical_insertion_mm": float(
                connector["solid_plug"]["minimum_finished_insertion_at_shortest_compound_cut_edge_mm"]
            ),
            "ordered_angle_stock_mm": {
                "leg": float(stock["leg_width_mm"]),
                "thickness": float(stock["thickness_mm"]),
                "length": float(stock["ordered_length_mm"]),
            },
            "backplate_hole_counts": {
                "adapter_m6": len(adapter_holes(interface)),
                "shell_m5": len(shell_holes(config)),
                "angle_base_m5": len(shoe_holes(config)),
            },
        },
        "derived": {
            "bearing_centerline_offset_from_lower_target_mm": round(bearing_t, 6),
            "axis_to_plate_normal_angle_deg": round(
                math.degrees(math.acos(abs(axis_dot_normal))), 6
            ),
            "rail_centerline_length_mm": round(derived_cut_length, 6),
            "compound_edge_lengths_mm": {
                "longest": round(longest_edge, 6),
                "shortest": round(shortest_edge, 6),
            },
            "compound_corner_t_from_lower_target_mm": [
                round(value, 6) for value in corner_t
            ],
            "upper_m4_from_bearing_centerline_mm": round(
                derived_upper_m4_from_lower, 6
            ),
            "minimum_plug_insertion_mm": round(minimum_plug_insertion, 4),
            "minimum_plug_cross_hole_end_ligament_mm": round(
                minimum_plug_cross_hole_end_ligament, 4
            ),
            "minimum_angle_base_hole_ligament_mm": round(
                angle_base_hole_ligament, 4
            ),
            "minimum_hole_edge_ligament_mm": {
                name: round(value, 4) for name, value in edge_values.items()
            },
            "minimum_cut_hole_pair_ligament_mm": round(pair_ligament, 4),
            "minimum_cut_hole_pair": {
                "first_group": pair_detail[0],
                "second_group": pair_detail[1],
                "first_center_mm": list(pair_detail[2]),
                "second_center_mm": list(pair_detail[3]),
            },
            "minimum_hardware_envelope_gap_mm": round(envelope_gap, 4),
            "minimum_hardware_envelope_pair": {
                "first_group": envelope_detail[0],
                "second_group": envelope_detail[1],
                "first_center_mm": list(envelope_detail[2]),
                "second_center_mm": list(envelope_detail[3]),
            },
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
            "V0.4-M2 generation requires Blender and the locked V6.1 shell"
        ) from error

    shell_source = repo_path(config["v61_socket_blend_path"])
    current_source = Path(bpy.data.filepath).resolve()
    if current_source != shell_source:
        raise ValueError(
            "Run Blender with the locked V6.1 BLEND as input; "
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
        "metal_v04_m2_backplate", (0.48, 0.58, 0.68, 1.0), 0.8
    )
    rail_material = material(
        "metal_v04_m2_rails", (0.12, 0.37, 0.74, 1.0), 0.75
    )
    angle_material = material(
        "metal_v04_m2_ordered_angle", (0.95, 0.48, 0.05, 1.0), 0.75
    )
    plug_material = material(
        "metal_v04_m2_solid_plug", (0.96, 0.78, 0.12, 1.0), 0.72
    )
    spacer_material = material(
        "metal_v04_m2_taper_spacers", (0.82, 0.68, 0.16, 1.0), 0.68
    )
    hardware_material = material(
        "metal_v04_m2_hardware", (0.10, 0.10, 0.12, 1.0), 0.9
    )

    plane = interface["rear_interface_plane"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    across_plate = Vector((1.0, 0.0, 0.0))
    # This is the authoritative plate-local +V convention used by
    # cat_head_interface.py. M1 accidentally reversed it in this generator.
    vertical = across_plate.cross(normal).normalized()
    plate_thickness = float(interface["aluminum_backplate"]["thickness_mm"])

    def local_point(x: float, v: float, n: float = 0.0) -> Vector:
        return center + across_plate * x + vertical * v + normal * n

    def mesh_object(name: str, vertices, faces, assigned_material):
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata([tuple(value) for value in vertices], [], faces)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(assigned_material)
        gate5.require_manifold(obj, name)
        return obj

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
        return mesh_object(name, vertices, faces, assigned_material)

    def oriented_box(name, box_center, axes, dimensions, assigned_material):
        return gate5.box(name, box_center, axes, dimensions, assigned_material)

    def cut_cylinder(obj, name, first, second, diameter):
        cutter = gate5.cylinder(name, first, second, diameter, vertices=24)
        gate5.apply_boolean(obj, cutter, "DIFFERENCE", solver="MANIFOLD")
        gate5.require_manifold(obj, f"{obj.name} {name} cut")

    def compound_member(
        name: str,
        lower: Vector,
        axis: Vector,
        across: Vector,
        other: Vector,
        width: float,
        height: float,
        upper_t: float,
        bearing_offset: float,
        assigned_material,
    ):
        half_width = width / 2.0
        half_height = height / 2.0
        offsets = [
            across * -half_width + other * -half_height,
            across * half_width + other * -half_height,
            across * half_width + other * half_height,
            across * -half_width + other * half_height,
        ]
        denominator = axis.dot(normal)
        lower_vertices = []
        lower_t_values = []
        for offset in offsets:
            t_value = (
                bearing_offset
                - (lower + offset - center).dot(normal)
            ) / denominator
            lower_t_values.append(t_value)
            lower_vertices.append(lower + offset + axis * t_value)
        upper_vertices = [lower + offset + axis * upper_t for offset in offsets]
        faces = [
            (3, 2, 1, 0),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ]
        return (
            mesh_object(
                name,
                lower_vertices + upper_vertices,
                faces,
                assigned_material,
            ),
            lower_t_values,
        )

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
            float(interface["aluminum_backplate"]["adapter_hole_pattern"]["diameter_mm"]),
        ),
        (
            "shell",
            shell_holes(config),
            float(config["backplate"]["shell_attachment"]["clearance_diameter_mm"]),
        ),
        (
            "angle",
            shoe_holes(config),
            float(config["backplate"]["shoe_attachment"]["plate_clearance_diameter_mm"]),
        ),
    ]
    for group, points, diameter in hole_sets:
        for index, (x_value, v_value) in enumerate(points):
            cut_cylinder(
                backplate,
                f"metal_v04__backplate_{group}_{index:02d}",
                local_point(x_value, v_value, -plate_thickness),
                local_point(x_value, v_value, plate_thickness),
                diameter,
            )

    rail_values = config["rails"]
    connector = config["lower_shoe"]
    stock = connector["ordered_stock"]
    primary = connector["primary_angle"]
    cheek_values = connector["outer_clamp_cheek"]
    plug_values = connector["solid_plug"]
    bolt_values = connector["rail_cross_bolts"]
    tube_size = float(interface["rail_system"]["profile"]["outside_width_mm"])
    upper_t = (
        float(rail_values["socket_stop_reference_length_mm"])
        - float(rail_values["upper_seated_end_clearance_mm"])
    )
    bearing_offset = float(
        connector["compound_bearing"]["angle_bearing_face_offset_mm"]
    )
    angle_thickness = float(stock["thickness_mm"])
    base_width = float(primary["base_leg_finished_width_mm"])
    upright_depth = float(primary["upright_leg_finished_depth_mm"])
    segment_length = float(primary["segment_length_mm"])
    plug_width = float(plug_values["nominal_width_mm"])
    plug_length = float(plug_values["bearing_centerline_to_upper_end_mm"])
    crossbolt_offsets = [
        float(value)
        for value in bolt_values["centers_from_bearing_plane_centerline_mm"]
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
        if name in bpy.data.objects
    }
    objects: dict[str, Any] = {"backplate": backplate}
    bearing_records: dict[str, Any] = {}

    right_holes = [
        (float(x_value), float(v_value))
        for x_value, v_value in config["backplate"]["shoe_attachment"][
            "right_local_x_v_centers_mm"
        ]
    ]

    for side in ("left", "right"):
        sign = -1.0 if side == "left" else 1.0
        lower = Vector(interface["rail_system"]["lower_targets_head_mm"][side])
        axis = Vector(interface["rail_system"]["accepted_axes_head"][side]).normalized()
        across = (
            Vector((1.0, 0.0, 0.0))
            - axis * Vector((1.0, 0.0, 0.0)).dot(axis)
        ).normalized()
        other = axis.cross(across).normalized()
        denominator = axis.dot(normal)
        bearing_t = (
            bearing_offset - (lower - center).dot(normal)
        ) / denominator
        bearing_center = lower + axis * bearing_t

        rail, corner_t = compound_member(
            f"metal_v04__rail_{side}",
            lower,
            axis,
            across,
            other,
            tube_size,
            tube_size,
            upper_t,
            bearing_offset,
            rail_material,
        )
        for index, offset in enumerate(crossbolt_offsets):
            hole_center = lower + axis * (bearing_t + offset)
            cut_cylinder(
                rail,
                f"metal_v04__rail_{side}_lower_m5_{index:02d}",
                hole_center - across * 18.0,
                hole_center + across * 18.0,
                float(bolt_values["clearance_diameter_mm"]),
            )
        upper_center = lower + axis * (
            bearing_t + float(rail_values["upper_m4_center_from_lower_cut_end_mm"])
        )
        cut_cylinder(
            rail,
            f"metal_v04__rail_{side}_upper_m4",
            upper_center - across * 16.0,
            upper_center + across * 16.0,
            float(interface["rail_system"]["socket"]["cross_bolt_clearance_diameter_mm"]),
        )

        plug, plug_corner_t = compound_member(
            f"metal_v04__plug_{side}",
            lower,
            axis,
            across,
            other,
            plug_width,
            plug_width,
            bearing_t + plug_length,
            bearing_offset,
            plug_material,
        )
        for index, offset in enumerate(crossbolt_offsets):
            hole_center = lower + axis * (bearing_t + offset)
            cut_cylinder(
                plug,
                f"metal_v04__plug_{side}_m5_{index:02d}",
                hole_center - across * 12.0,
                hole_center + across * 12.0,
                float(bolt_values["clearance_diameter_mm"]),
            )

        outward = across * sign
        q_axis = (axis - normal * axis.dot(normal)).normalized()
        s_axis = normal.cross(q_axis).normalized()
        if s_axis.dot(outward) < 0.0:
            s_axis = -s_axis
        contact_points = []
        for across_sign in (-1.0, 1.0):
            for other_sign in (-1.0, 1.0):
                offset_vector = (
                    across * across_sign * tube_size / 2.0
                    + other * other_sign * tube_size / 2.0
                )
                t_value = (
                    bearing_offset
                    - (lower + offset_vector - center).dot(normal)
                ) / denominator
                contact_points.append(lower + offset_vector + axis * t_value)
        current_holes = [(sign * x_value, v_value) for x_value, v_value in right_holes]
        hole_points = [
            local_point(x_value, v_value, bearing_offset)
            for x_value, v_value in current_holes
        ]
        required_points = contact_points + hole_points
        q_values = [(point - bearing_center).dot(q_axis) for point in required_points]
        s_values = [(point - bearing_center).dot(s_axis) for point in required_points]
        q_lower_bound = max(q_values) - segment_length
        q_upper_bound = min(q_values)
        q_start_default = (min(q_values) + max(q_values) - segment_length) / 2.0
        q_start = min(max(q_start_default, q_lower_bound), q_upper_bound)
        s_lower_bound = max(s_values) - base_width
        s_upper_bound = min(s_values)
        contact_s = [(point - bearing_center).dot(s_axis) for point in contact_points]
        s_start_default = min(contact_s) - angle_thickness
        s_start = min(max(s_start_default, s_lower_bound), s_upper_bound)
        q_center = q_start + segment_length / 2.0
        s_center = s_start + base_width / 2.0

        base_center = (
            bearing_center
            + q_axis * q_center
            + s_axis * s_center
            + normal * (angle_thickness / 2.0)
        )
        angle_base = oriented_box(
            f"metal_v04__angle_base_{side}",
            base_center,
            (q_axis, s_axis, normal),
            (segment_length, base_width, angle_thickness),
            angle_material,
        )
        upright_center = (
            bearing_center
            + q_axis * q_center
            + s_axis * (s_start + angle_thickness / 2.0)
            + normal * (bearing_offset + plate_thickness / 2.0 - upright_depth / 2.0)
        )
        angle_upright = oriented_box(
            f"metal_v04__angle_upright_{side}",
            upright_center,
            (q_axis, s_axis, normal),
            (segment_length, angle_thickness, upright_depth),
            angle_material,
        )
        for index, (x_value, v_value) in enumerate(current_holes):
            hole_point = local_point(x_value, v_value, 0.0)
            cut_cylinder(
                angle_base,
                f"metal_v04__angle_base_{side}_m5_{index:02d}",
                hole_point + normal * 7.0,
                hole_point - normal * 7.0,
                float(config["backplate"]["shoe_attachment"]["plate_clearance_diameter_mm"]),
            )
            plate_fastener = gate5.cylinder(
                f"metal_v04__plate_m5_{side}_{index:02d}",
                hole_point + normal * 4.0,
                hole_point - normal * 7.0,
                5.0,
                hardware_material,
                vertices=24,
            )
            objects[f"plate_m5_{side}_{index}"] = plate_fastener

        for index, offset in enumerate(crossbolt_offsets):
            hole_center = lower + axis * (bearing_t + offset)
            cut_cylinder(
                angle_upright,
                f"metal_v04__angle_upright_{side}_m5_{index:02d}",
                hole_center - across * 35.0,
                hole_center + across * 35.0,
                float(bolt_values["clearance_diameter_mm"]),
            )

        cheek_center = (
            lower
            + axis * (bearing_t + segment_length / 2.0)
            + outward * (tube_size / 2.0 + float(cheek_values["thickness_mm"]) / 2.0)
        )
        outer_cheek = oriented_box(
            f"metal_v04__outer_cheek_{side}",
            cheek_center,
            (outward, other, axis),
            (
                float(cheek_values["thickness_mm"]),
                float(cheek_values["finished_width_mm"]),
                float(cheek_values["finished_length_mm"]),
            ),
            angle_material,
        )
        for index, offset in enumerate(crossbolt_offsets):
            hole_center = lower + axis * (bearing_t + offset)
            cut_cylinder(
                outer_cheek,
                f"metal_v04__outer_cheek_{side}_m5_{index:02d}",
                hole_center - across * 25.0,
                hole_center + across * 25.0,
                float(bolt_values["clearance_diameter_mm"]),
            )

        inner = -outward
        spacer_ranges = (
            connector["roll_compensation"]["lower_spacer_finished_thickness_range_mm"],
            connector["roll_compensation"]["upper_spacer_finished_thickness_range_mm"],
        )
        for index, (offset, thickness_range) in enumerate(
            zip(crossbolt_offsets, spacer_ranges)
        ):
            hole_center = lower + axis * (bearing_t + offset)
            spacer_thickness = (
                float(thickness_range[0]) + float(thickness_range[1])
            ) / 2.0
            spacer = oriented_box(
                f"metal_v04__taper_spacer_{side}_{index:02d}",
                hole_center
                + inner * (tube_size / 2.0 + spacer_thickness / 2.0),
                (outward, other, axis),
                (spacer_thickness, 12.0, 12.0),
                spacer_material,
            )
            bolt = gate5.cylinder(
                f"metal_v04__crossbolt_{side}_{index:02d}",
                hole_center + inner * 25.0,
                hole_center + outward * 25.0,
                5.0,
                hardware_material,
                vertices=24,
            )
            head = gate5.cylinder(
                f"metal_v04__crossbolt_head_{side}_{index:02d}",
                hole_center + inner * 22.0,
                hole_center + inner * 26.0,
                float(bolt_values["head_washer_envelope_diameter_mm"]),
                hardware_material,
                vertices=24,
            )
            nut = gate5.cylinder(
                f"metal_v04__crossbolt_nut_{side}_{index:02d}",
                hole_center + outward * 22.0,
                hole_center + outward * 27.0,
                float(bolt_values["nut_washer_envelope_diameter_mm"]),
                hardware_material,
                vertices=24,
            )
            objects[f"spacer_{side}_{index}"] = spacer
            objects[f"crossbolt_{side}_{index}"] = bolt
            objects[f"crossbolt_head_{side}_{index}"] = head
            objects[f"crossbolt_nut_{side}_{index}"] = nut

        objects[f"rail_{side}"] = rail
        objects[f"plug_{side}"] = plug
        objects[f"angle_base_{side}"] = angle_base
        objects[f"angle_upright_{side}"] = angle_upright
        objects[f"outer_cheek_{side}"] = outer_cheek
        bearing_records[side] = {
            "plate_local_basis_vertical_corrected": True,
            "bearing_centerline_t_from_lower_target_mm": round(bearing_t, 6),
            "compound_corner_t_from_lower_target_mm": [
                round(value, 6) for value in corner_t
            ],
            "plug_corner_t_from_lower_target_mm": [
                round(value, 6) for value in plug_corner_t
            ],
            "angle_base_q_span_required_mm": round(max(q_values) - min(q_values), 4),
            "angle_base_s_span_required_mm": round(max(s_values) - min(s_values), 4),
            "angle_base_q_start_mm": round(q_start, 4),
            "angle_base_s_start_mm": round(s_start, 4),
        }

    collision_part_names = [
        "backplate",
        "rail_left",
        "rail_right",
        "angle_base_left",
        "angle_base_right",
        "angle_upright_left",
        "angle_upright_right",
        "outer_cheek_left",
        "outer_cheek_right",
    ]
    collision_records = {
        metal_name: {
            printed_name: comparison.collision_record(objects[metal_name], printed)
            for printed_name, printed in all_printed.items()
        }
        for metal_name in collision_part_names
    }
    fixed_shell_names = tuple(
        name
        for name in (
            "gate9_frame_candidate__left_lower_face",
            "gate9_frame_candidate__left_upper_head",
            "gate9_frame_candidate__right_lower_face",
            "gate9_frame_candidate__right_upper_head",
            "gate9_v5__bottom_keel",
        )
        if name in all_printed
    )
    current_fixed_shell_clear = all(
        not collision_records[metal_name][printed_name]["intersects"]
        for metal_name in collision_part_names
        for printed_name in fixed_shell_names
    )
    rear_bezel_overlap_pairs = sum(
        int(records.get("gate9_v5__rear_bezel", {}).get("triangle_overlap_pair_count", 0))
        for records in collision_records.values()
    )
    observed_conflicts = [
        {"metal": metal_name, "printed": printed_name}
        for metal_name, records in collision_records.items()
        for printed_name, record in records.items()
        if record["intersects"]
    ]
    checks = {
        "ordered_angle_connector_envelope_generated": all(
            name in objects
            for name in (
                "angle_base_left",
                "angle_base_right",
                "angle_upright_left",
                "angle_upright_right",
                "outer_cheek_left",
                "outer_cheek_right",
            )
        ),
        "compound_bearing_rail_and_plug_generated": all(
            name in objects
            for name in ("rail_left", "rail_right", "plug_left", "plug_right")
        ),
        "plate_local_vertical_matches_shared_interface": True,
        "current_v61_collision_matrix_recorded_for_shell_reintegration": (
            len(collision_records) == len(collision_part_names)
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

    def render(name, location, target, hidden=None, lens=55.0):
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
        for obj, previous in prior.items():
            obj.hide_render = previous

    shell_objects = set(all_printed.values())
    render(
        "v04-m2-shell-integration-rear",
        (245.0, 520.0, 225.0),
        (0.0, 247.0, 168.0),
    )
    render(
        "v04-m2-angle-frame-rear",
        (210.0, 500.0, 210.0),
        (0.0, 250.0, 165.0),
        hidden=shell_objects,
    )
    render(
        "v04-m2-angle-frame-front",
        (205.0, 65.0, 190.0),
        (0.0, 248.0, 164.0),
        hidden=shell_objects,
    )
    render(
        "v04-m2-right-connector-detail",
        (125.0, 170.0, 126.0),
        (40.0, 258.0, 150.0),
        hidden=shell_objects
        | {
            objects["rail_left"],
            objects["plug_left"],
            objects["angle_base_left"],
            objects["angle_upright_left"],
            objects["outer_cheek_left"],
        },
        lens=64.0,
    )
    render(
        "v04-m2-right-connector-internal",
        (112.0, 188.0, 120.0),
        (40.0, 258.0, 151.0),
        hidden=shell_objects
        | {
            objects["rail_left"],
            objects["plug_left"],
            objects["angle_base_left"],
            objects["angle_upright_left"],
            objects["outer_cheek_left"],
            objects["rail_right"],
            objects["outer_cheek_right"],
        },
        lens=68.0,
    )

    model_path = paths["model"] / "frame-fixed-mount-v04-m2-angle-stock-review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(model_path))
    model_path.with_suffix(".blend1").unlink(missing_ok=True)
    return {
        "status": (
            "PASS - M2 ORDERED-ANGLE ENVELOPE GENERATED; SHELL REINTEGRATION REQUIRED"
            if all(checks.values())
            else "FAIL"
        ),
        "checks": checks,
        "plate_local_basis_correction": (
            "generator now uses across_plate.cross(rear_normal), matching the shared interface"
        ),
        "bearing_and_angle_layout": bearing_records,
        "current_v61_fixed_shell_clear": current_fixed_shell_clear,
        "current_rear_bezel_overlap_pair_count": rear_bezel_overlap_pairs,
        "observed_conflicts": observed_conflicts,
        "required_shell_followup": (
            "consume this M2 angle/base/upright/cheek/hardware envelope, regenerate the rear bezel and six ASA pads, then rerun A-39"
        ),
        "collision_records": collision_records,
    }


def main() -> None:
    config, interface, socket_summary = load_inputs()
    paths = output_paths(config)
    write_backplate_outputs(config, interface, paths)
    write_rail_output(config, paths)
    write_angle_connector_output(config, paths)
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
            "PASS - V0.4-M2 ORDERED-ANGLE ALUMINUM HANDOFF GENERATED"
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
        "lower_angle_connector": config["lower_shoe"],
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
                    / "rail-cut-and-drill-v04-m2-1to1.svg"
                ).relative_to(REPO_ROOT)
            ),
            "rail_wrap_template": str(
                (
                    paths["rails"]
                    / "rail-lower-compound-wrap-v04-m2-1to1.svg"
                ).relative_to(REPO_ROOT)
            ),
            "angle_connector_drawing": str(
                (
                    paths["formed"]
                    / "lower-angle-connector-v04-m2-plan.svg"
                ).relative_to(REPO_ROOT)
            ),
            "review_blend": str(
                (
                    paths["model"]
                    / "frame-fixed-mount-v04-m2-angle-stock-review.blend"
                ).relative_to(REPO_ROOT)
            ),
            "renders": [
                str(path.relative_to(REPO_ROOT))
                for path in sorted(paths["renders"].glob("v04-m2-*.png"))
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
        "observed_conflicts": len(tracked_collision["observed_conflicts"]),
    }
    tracked_collision.pop("collision_records")
    REVIEW_PATH.write_text(
        json.dumps(tracked_report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(serialized)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
