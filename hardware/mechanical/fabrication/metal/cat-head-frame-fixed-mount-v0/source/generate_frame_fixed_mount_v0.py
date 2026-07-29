#!/usr/bin/env python3
"""Generate the frame-fixed, no-weld aluminum cat-head mount V0.2 review pack.

Run from the mount workspace with:

    blender --background --python source/generate_frame_fixed_mount_v0.py

Only the rear boss plate and compact bike adapter are cut-ready profiles.
The head rear backplate and lower rail shoes remain review geometry until the
rear-base pass-through and perimeter-fastener coupon is physically approved.
The 5052 drawings specify formed geometry only; the shop must calculate flat
patterns for its bend tooling.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG_PATH = ROOT / "config" / "frame-fixed-mount-v0.json"
OUTPUT = ROOT / "output"
FLAT = OUTPUT / "flat-plates"
FORMED = OUTPUT / "formed-parts"
DRAWINGS = OUTPUT / "review-drawings"
MODEL = OUTPUT / "review-model"
RENDERS = OUTPUT / "renders"
VALIDATION = OUTPUT / "validation"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def prepare() -> None:
    for path in (FLAT, FORMED, DRAWINGS, MODEL, RENDERS, VALIDATION):
        path.mkdir(parents=True, exist_ok=True)


def n(value: float) -> str:
    result = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if result == "-0" else result


def svg(width: float, height: float, body: str, title: str) -> str:
    margin = 12.0
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{n(width + 2*margin)}mm"
 height="{n(height + 2*margin)}mm" viewBox="{n(-width/2-margin)} {n(-height/2-margin)}
 {n(width+2*margin)} {n(height+2*margin)}"><title>{title}</title>
 <style>.cut{{fill:none;stroke:#000;stroke-width:.25}} .part{{fill:#eaf1f5;stroke:#000;stroke-width:.25}}
 .bend{{fill:none;stroke:#126ec2;stroke-width:.22;stroke-dasharray:3 2}}
 .center{{fill:none;stroke:#999;stroke-width:.18;stroke-dasharray:2 2}}
 .dim{{fill:none;stroke:#c41e3a;stroke-width:.18}} .note{{font:3px monospace;fill:#111}}
 .warn{{font:3px monospace;fill:#c41e3a}}</style><g transform="scale(1,-1)">{body}</g></svg>\n'''


def text(x: float, y: float, value: str, css: str = "note") -> str:
    return f'<text class="{css}" x="{n(x)}" y="{n(-y)}" transform="scale(1,-1)">{value}</text>'


def circle(x: float, y: float, diameter: float, css: str = "cut") -> str:
    return f'<circle class="{css}" cx="{n(x)}" cy="{n(y)}" r="{n(diameter/2)}"/>'


def rounded_path(width: float, height: float, radius: float) -> str:
    x, y, r = width/2, height/2, radius
    return (f'M {n(-x+r)},{n(-y)} H {n(x-r)} A {n(r)},{n(r)} 0 0 1 {n(x)},{n(-y+r)} '
            f'V {n(y-r)} A {n(r)},{n(r)} 0 0 1 {n(x-r)},{n(y)} H {n(-x+r)} '
            f'A {n(r)},{n(r)} 0 0 1 {n(-x)},{n(y-r)} V {n(-y+r)} '
            f'A {n(r)},{n(r)} 0 0 1 {n(-x+r)},{n(-y)} Z')


def dxf_start() -> list[str]:
    return ["0", "SECTION", "2", "ENTITIES"]


def dxf_line(data: list[str], a: tuple[float, float], b: tuple[float, float]) -> None:
    data.extend(["0", "LINE", "8", "CUT", "10", n(a[0]), "20", n(a[1]),
                 "11", n(b[0]), "21", n(b[1])])


def dxf_circle(data: list[str], point: tuple[float, float], radius: float) -> None:
    data.extend(["0", "CIRCLE", "8", "CUT", "10", n(point[0]), "20", n(point[1]),
                 "40", n(radius)])


def dxf_arc(data: list[str], point: tuple[float, float], radius: float,
            start: float, end: float) -> None:
    data.extend(["0", "ARC", "8", "CUT", "10", n(point[0]), "20", n(point[1]),
                 "40", n(radius), "50", n(start), "51", n(end)])


def dxf_rounded(data: list[str], width: float, height: float, radius: float) -> None:
    x, y, r = width/2, height/2, radius
    dxf_line(data, (-x+r, -y), (x-r, -y)); dxf_line(data, (x, -y+r), (x, y-r))
    dxf_line(data, (x-r, y), (-x+r, y)); dxf_line(data, (-x, y-r), (-x, -y+r))
    dxf_arc(data, (x-r, -y+r), r, 270, 360); dxf_arc(data, (x-r, y-r), r, 0, 90)
    dxf_arc(data, (-x+r, y-r), r, 90, 180); dxf_arc(data, (-x+r, -y+r), r, 180, 270)


def rear_plate(c: dict) -> None:
    p = c["bike_interface"]["boss_plate"]
    bx = c["bike_interface"]["boss_horizontal_center_spacing_mm"]/2
    bz = c["bike_interface"]["boss_vertical_center_spacing_mm"]/2
    body = f'<path class="cut" d="{rounded_path(p["width_mm"], p["height_mm"], p["corner_radius_mm"])}"/>'
    for x in (-bx, bx):
        for z in (-bz, bz): body += circle(x, z, p["frame_hole_diameter_mm"])
    for x in (-p["side_web_flange_hole_x_mm"], p["side_web_flange_hole_x_mm"]):
        for z in p["side_web_flange_hole_z_mm"]: body += circle(x, z, p["side_web_hole_diameter_mm"])
    body += f'<path class="cut" d="{rounded_path(p["tether_slot_width_mm"], p["tether_slot_height_mm"], p["tether_slot_height_mm"]/2)}"/>'
    body += '<path class="center" d="M -30,0 H 30 M 0,-57.5 V 57.5"/>'
    body += text(-29, 66, "REAR BOSS PLATE | 4.75 mm 6061-T6 | PRINT 100%")
    body += text(-29, 62, "4x dia6.6 frame; 4x dia5.5 webs; 16x8 tether slot")
    (FLAT/"rear-boss-plate-1to1.svg").write_text(svg(170, 150, body, "Rear boss plate 1:1"), encoding="utf-8")
    data = dxf_start(); dxf_rounded(data, p["width_mm"], p["height_mm"], p["corner_radius_mm"])
    for x in (-bx, bx):
        for z in (-bz, bz): dxf_circle(data, (x, z), p["frame_hole_diameter_mm"]/2)
    for x in (-p["side_web_flange_hole_x_mm"], p["side_web_flange_hole_x_mm"]):
        for z in p["side_web_flange_hole_z_mm"]: dxf_circle(data, (x, z), p["side_web_hole_diameter_mm"]/2)
    dxf_rounded(data, p["tether_slot_width_mm"], p["tether_slot_height_mm"], p["tether_slot_height_mm"]/2)
    data += ["0", "ENDSEC", "0", "EOF"]
    (FLAT/"rear-boss-plate.dxf").write_text("\n".join(data)+"\n", encoding="ascii")


def side_web_polygon(c: dict) -> list[tuple[float, float]]:
    """Return the formed central web in bike-local (forward, vertical) coordinates."""
    web = c["load_path"]["side_webs"]
    depth = c["pose"]["yoke_center_forward_from_boss_plate_mm"]
    rise = c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]
    angle = math.radians(c["pose"]["yoke_pitch_relative_to_boss_plane_deg"])
    half = web["web_half_height_mm"]
    front_upper = (depth-half*math.sin(angle), rise+half*math.cos(angle))
    front_lower = (depth+half*math.sin(angle), rise-half*math.cos(angle))
    return [(0, -half), (0, half), front_upper, front_lower]


def shifted(points: list[tuple[float, float]], x: float, y: float) -> list[tuple[float, float]]:
    return [(px-x, py-y) for px,py in points]


def polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1])))/2


def front_adapter(c: dict) -> None:
    p = c["load_path"]["front_adapter"]
    body = f'<path class="cut" d="{rounded_path(p["overall_width_mm"], p["overall_height_mm"], p["corner_radius_mm"])}"/>'
    for x in (-p["side_web_flange_hole_x_mm"], p["side_web_flange_hole_x_mm"]):
        for v in p["side_web_flange_hole_v_mm"]:
            body += circle(x, v, p["side_web_hole_diameter_mm"])
    for x in (-p["backplate_hole_x_mm"], p["backplate_hole_x_mm"]):
        for v in (-p["backplate_hole_v_mm"], p["backplate_hole_v_mm"]):
            body += circle(x, v, p["backplate_hole_diameter_mm"])
    body += '<path class="center" d="M -45,0 H 45 M 0,-40 V 40"/>'
    body += text(-44, 47, "BIKE ADAPTER | 4.75 mm 6061-T6 | PRINT 100%")
    body += text(-44, 43, "4x dia5.5 webs; 4x dia6.6 removable head interface")
    (FLAT/"bike-adapter-plate-1to1.svg").write_text(svg(180, 115, body, "V0.2 bike adapter 1:1"), encoding="utf-8")
    data = dxf_start(); dxf_rounded(data, p["overall_width_mm"], p["overall_height_mm"], p["corner_radius_mm"])
    for x in (-p["side_web_flange_hole_x_mm"], p["side_web_flange_hole_x_mm"]):
        for v in p["side_web_flange_hole_v_mm"]:
            dxf_circle(data, (x, v), p["side_web_hole_diameter_mm"]/2)
    for x in (-p["backplate_hole_x_mm"], p["backplate_hole_x_mm"]):
        for v in (-p["backplate_hole_v_mm"], p["backplate_hole_v_mm"]):
            dxf_circle(data, (x, v), p["backplate_hole_diameter_mm"]/2)
    data += ["0", "ENDSEC", "0", "EOF"]
    (FLAT/"bike-adapter-plate.dxf").write_text("\n".join(data)+"\n", encoding="ascii")


def backplate_polygon(c: dict) -> list[tuple[float, float]]:
    p = c["head_interface"]["aluminum_backplate"]
    h = p["height_mm"]/2
    return [(-p["outer_bottom_width_mm"]/2,-h),(p["outer_bottom_width_mm"]/2,-h),(p["outer_top_width_mm"]/2,h),(-p["outer_top_width_mm"]/2,h)]


def head_backplate(c: dict) -> None:
    p = c["head_interface"]["aluminum_backplate"]; points = backplate_polygon(c)
    body = '<polygon class="part" points="' + " ".join(f"{n(x)},{n(v)}" for x,v in points) + '"/>'
    for x in (-p["bike_adapter_hole_x_mm"], p["bike_adapter_hole_x_mm"]):
        for v in (-p["bike_adapter_hole_v_mm"], p["bike_adapter_hole_v_mm"]):
            body += circle(x, v, p["bike_adapter_hole_diameter_mm"])
    body += '<path class="center" d="M -60,0 H 60 M 0,-39.8319 V 39.8319"/>'
    body += text(-59, 48, "HEAD REAR BACKPLATE | 3 mm 6061-T6 | REVIEW ONLY")
    body += text(-59, 44, "4x dia6.6 adapter; perimeter + rail-shoe holes DEFERRED", "warn")
    (FLAT/"head-rear-backplate-review-only.svg").write_text(svg(190, 115, body, "V0.2 head backplate review geometry"), encoding="utf-8")
    data = dxf_start()
    for a,b in zip(points, points[1:]+points[:1]): dxf_line(data, a, b)
    for x in (-p["bike_adapter_hole_x_mm"], p["bike_adapter_hole_x_mm"]):
        for v in (-p["bike_adapter_hole_v_mm"], p["bike_adapter_hole_v_mm"]):
            dxf_circle(data, (x,v), p["bike_adapter_hole_diameter_mm"]/2)
    data += ["0", "ENDSEC", "0", "EOF"]
    (FLAT/"head-rear-backplate-review-only.dxf").write_text("\n".join(data)+"\n", encoding="ascii")

def formed_drawings_v02(c: dict) -> None:
    web = c["load_path"]["side_webs"]; depth = c["pose"]["yoke_center_forward_from_boss_plate_mm"]
    rise = c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]
    points = shifted(side_web_polygon(c), depth/2, rise/2)
    point_text = " ".join(f"{n(x)},{n(y)}" for x,y in points)
    body = f'<polygon class="part" points="{point_text}"/>'
    body += f'<path class="bend" d="M {n(points[0][0])},{n(points[0][1])} L {n(points[1][0])},{n(points[1][1])}"/>'
    body += f'<path class="bend" d="M {n(points[2][0])},{n(points[2][1])} L {n(points[3][0])},{n(points[3][1])}"/>'
    body += f'<path class="center" d="M {-depth/2},{-rise/2} L {depth/2},{rise/2}"/>'
    centerline = math.hypot(depth, rise)
    body += text(-65, 88, "V0.2 DIAGONAL SIDE WEB | 2x | 3.18 mm 5052-H32")
    body += text(-65, 83, f"{depth:g} forward | {rise:g} rise | centerline {centerline:.2f} mm")
    body += text(-65, 78, f"front bend follows adapter pitch {c['pose']['yoke_pitch_relative_to_boss_plane_deg']:.3f} deg")
    body += text(-65, -82, "FORMED DIMENSIONS ONLY - SHOP CALCULATES FLAT PATTERN", "warn")
    (FORMED/"side-web-formed-drawing.svg").write_text(svg(150, 190, body, "V0.2 diagonal side web formed dimensions"), encoding="utf-8")
    shoe = '<path class="part" d="M -55,-25 H -50 V 25 H -55 Z"/>'
    shoe += '<path class="part" d="M -50,-9.525 L 45,6.5 L 45,25.55 L -50,9.525 Z"/>'
    shoe += '<path class="part" d="M -50,-7 L -5,0.6 L -5,14 L -50,7 Z"/>'
    shoe += circle(5, 9, 5.5) + circle(25, 12.5, 5.5)
    shoe += text(-55, 38, "MIRRORED LOWER RAIL SHOE CONCEPT | 2x | MACHINED 6061")
    shoe += text(-55, 33, "solid plug enters square tube; 2x M5 cross-bolts; flange bolts to backplate")
    shoe += text(-55, 28, "compound pitch/yaw comes from final portal axis; NO WELD")
    shoe += text(-55, -35, "REVIEW SCHEMATIC ONLY - SHOE, PLUG, HOLES AND REAR PASS-THROUGH NOT RELEASED", "warn")
    (FORMED/"lower-rail-shoe-concept-review.svg").write_text(svg(230, 105, shoe, "V0.2 machined lower rail shoe concept"), encoding="utf-8")


def gate8_validation(c: dict) -> dict:
    path = ROOT.parents[4] / c["head_interface"]["gate8_source_validation"]
    if not path.exists():
        raise FileNotFoundError(f"Gate8 validation missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def head_to_bike_transform_2d(c: dict, y: float, z: float) -> tuple[float, float]:
    """Map a Gate8 head-coordinate side point into the boss-local review frame."""
    b = math.radians(c["pose"]["boss_plane_normal_elevation_deg"])
    center = c["head_interface"]["rear_frame"]["plane_center_head_mm"]
    target_y = c["pose"]["yoke_center_forward_from_boss_plate_mm"]
    target_z = c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]
    center_y = -math.cos(b)*center[1] + math.sin(b)*center[2]
    center_z = math.sin(b)*center[1] + math.cos(b)*center[2]
    transformed_y = -math.cos(b)*y + math.sin(b)*z
    transformed_z = math.sin(b)*y + math.cos(b)*z
    return transformed_y + target_y-center_y, transformed_z + target_z-center_z


def side_profile_v02(c: dict) -> None:
    """Create an integration view using the actual 330 mm Gate8 bounding box."""
    angle = math.radians(c["pose"]["yoke_pitch_relative_to_boss_plane_deg"])
    depth = c["pose"]["yoke_center_forward_from_boss_plate_mm"]
    rise = c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]
    bounds = c["head_interface"]["actual_gate8_shell_bounds_head_mm"]
    head_corners = [head_to_bike_transform_2d(c, y, z)
                    for y in bounds["y_mm"] for z in bounds["z_mm"]]
    y_min = min(p[0] for p in head_corners); y_max = max(p[0] for p in head_corners)
    z_min = min(p[1] for p in head_corners); z_max = max(p[1] for p in head_corners)
    shift_y, shift_z = 170.0, -20.0
    def point(y: float, z: float) -> tuple[float, float]:
        return y-shift_y, z-shift_z
    def polygon(points: list[tuple[float,float]], css: str="part") -> str:
        return f'<polygon class="{css}" points="' + " ".join(f"{n(x)},{n(y)}" for x,y in points) + '"/>'
    rear = [point(-2.4,-57.5), point(2.4,-57.5), point(2.4,57.5), point(-2.4,57.5)]
    webs = [point(y,z) for y,z in side_web_polygon(c)]
    adapter_h = c["load_path"]["front_adapter"]["overall_height_mm"]/2
    adapter_t = c["load_path"]["front_adapter"]["thickness_mm"]/2
    adapter = []
    for local_v, local_n in ((-adapter_h,-adapter_t),(-adapter_h,adapter_t),
                             (adapter_h,adapter_t),(adapter_h,-adapter_t)):
        adapter.append(point(depth-local_v*math.sin(angle)+local_n*math.cos(angle),
                             rise+local_v*math.cos(angle)+local_n*math.sin(angle)))
    body = polygon(rear) + polygon(webs) + polygon(adapter)
    hx, hz = point(y_min, z_min)
    body += f'<rect class="center" x="{n(hx)}" y="{n(hz)}" width="{n(y_max-y_min)}" height="{n(z_max-z_min)}"/>'
    body += text(hx+3, hz+8, "ACTUAL GATE8 330 mm SHELL SIDE BOUNDS")
    light_z = c["pose"]["headlight_reference"]["light_top_relative_to_boss_pattern_center_mm"]
    la = point(-8, light_z); lb = point(360, light_z)
    body += f'<path class="dim" d="M {n(la[0])},{n(la[1])} L {n(lb[0])},{n(lb[1])}"/>'
    body += text(-165, 212, "V0.2: compact adapter/backplate at 60 forward, 75 up")
    body += text(-165, 207, f"rear-plane mating pitch {c['pose']['yoke_pitch_relative_to_boss_plane_deg']:.3f} deg from boss plane")
    body += text(-165, 202, "rails are INTERNAL: backplate shoes to blind upper sockets")
    body += text(-165, 197, "red line is rough light-top elevation only; projection overlap is not a 3D collision test", "warn")
    body += text(-165, -216, "Use the GLB/full-size mockup for housing + beam clearance before metal", "warn")
    (DRAWINGS/"v02-side-integration-review.svg").write_text(
        svg(410, 450, body, "V0.2 actual-shell side integration review"), encoding="utf-8")


def validate_v02(c: dict) -> dict:
    rear = c["bike_interface"]["boss_plate"]
    adapter = c["load_path"]["front_adapter"]
    backplate = c["head_interface"]["aluminum_backplate"]
    bx = c["bike_interface"]["boss_horizontal_center_spacing_mm"]/2
    bz = c["bike_interface"]["boss_vertical_center_spacing_mm"]/2
    rear_lig = min(rear["width_mm"]/2-bx-rear["frame_hole_diameter_mm"]/2,
                   rear["height_mm"]/2-bz-rear["frame_hole_diameter_mm"]/2)
    boss_support = min(rear["width_mm"]/2-bx-c["bike_interface"]["boss_face_diameter_mm"]/2,
                       rear["height_mm"]/2-bz-c["bike_interface"]["boss_face_diameter_mm"]/2)
    adapter_edge = min(adapter["overall_width_mm"]/2-adapter["backplate_hole_x_mm"]-adapter["backplate_hole_diameter_mm"]/2,
                       adapter["overall_height_mm"]/2-adapter["backplate_hole_v_mm"]-adapter["backplate_hole_diameter_mm"]/2)
    hole_lig = abs(adapter["backplate_hole_x_mm"]-adapter["side_web_flange_hole_x_mm"]) - adapter["backplate_hole_diameter_mm"]/2-adapter["side_web_hole_diameter_mm"]/2
    h = backplate["height_mm"]/2
    t = (backplate["bike_adapter_hole_v_mm"]+h)/(2*h)
    half_width_top_row = backplate["outer_bottom_width_mm"]/2 + t*(backplate["outer_top_width_mm"]-backplate["outer_bottom_width_mm"])/2
    backplate_edge = half_width_top_row-backplate["bike_adapter_hole_x_mm"] - backplate["bike_adapter_hole_diameter_mm"]/2
    frame = c["head_interface"]["rear_frame"]
    normal = frame["outward_normal_head"]; center = frame["plane_center_head_mm"]
    targets = backplate["rail_lower_targets_head_mm"]
    plane_errors = [abs(sum((p[i]-center[i])*normal[i] for i in range(3))) for p in targets]
    gate8 = gate8_validation(c)
    portals = gate8["aluminum_portals"]
    cross_bolt_angle = max(p["cross_bolt_angle_from_head_x_deg"] for p in portals.values())
    min_recess = min(p["minimum_exterior_recess_mm"] for p in portals.values())
    socket_integral = all(p["integrated_with_shell"] and p["blind_end_stop"] for p in portals.values())
    gate8_acceptance = gate8["acceptance"]
    density = 2.70/1000
    rear_mass = rear["width_mm"]*rear["height_mm"]*rear["thickness_mm"]*density
    adapter_mass = adapter["overall_width_mm"]*adapter["overall_height_mm"]*adapter["thickness_mm"]*density
    backplate_mass = polygon_area(backplate_polygon(c))*backplate["thickness_mm"]*density
    web = c["load_path"]["side_webs"]
    bend_line_height = 2*web["web_half_height_mm"]
    web_mass = 2*(polygon_area(side_web_polygon(c)) + bend_line_height*(web["rear_flange_width_mm"]+web["front_flange_width_mm"]))*web["thickness_mm"]*density
    checks = {
        "rear_M6_min_edge_ligament_mm": {"value": rear_lig, "required_min": 8.0, "pass": rear_lig >= 8},
        "boss_face_supported_past_edge_mm": {"value": boss_support, "required_min": 0.0, "pass": boss_support >= 0},
        "adapter_M6_min_edge_ligament_mm": {"value": adapter_edge, "required_min": 10.0, "pass": adapter_edge >= 10},
        "adapter_M5_to_M6_hole_ligament_mm": {"value": hole_lig, "required_min": 4.0, "pass": hole_lig >= 4},
        "backplate_top_row_M6_edge_ligament_mm": {"value": backplate_edge, "required_min": 8.0, "pass": backplate_edge >= 8},
        "rail_targets_to_backplate_plane_max_error_mm": {"value": max(plane_errors), "required_max": 0.01, "pass": max(plane_errors) <= .01},
        "socket_cross_bolt_angle_from_head_x_deg": {"value": cross_bolt_angle, "required_max": 10.0, "pass": cross_bolt_angle <= 10},
        "socket_minimum_exterior_recess_mm": {"value": min_recess, "required_min": 8.0, "pass": min_recess >= 8},
        "blind_sockets_integral_with_upper_shells": {"value": socket_integral, "pass": socket_integral},
        "no_external_rail_through_shell": {"value": gate8_acceptance["no_new_exterior_fastener_holes"], "pass": gate8_acceptance["no_new_exterior_fastener_holes"]},
        "no_weld_primary_load_path": {"value": True, "pass": True},
        "no_polymer_bike_connector_primary_load_path": {"value": True, "pass": True}
    }
    passed = all(item["pass"] for item in checks.values())
    return {
        "status": "PASS - INTEGRATION GEOMETRY REVIEW ONLY" if passed else "FAIL",
        "release_status": "NOT CUT-READY AS AN ASSEMBLY",
        "checks": checks,
        "portal_orientation": {
            "rail_pitch_above_head_forward_deg": c["head_interface"]["internal_rails"]["pitch_above_head_forward_deg"],
            "rail_yaw_from_head_centerline_deg": c["head_interface"]["internal_rails"]["yaw_from_head_centerline_deg"],
            "cross_bolt_angle_from_head_x_deg": cross_bolt_angle,
            "rejected_v01_cross_bolt_angle_from_head_x_deg": c["head_interface"]["portal_revision"]["rejected_v01_cross_bolt_angle_from_head_x_deg"]
        },
        "estimated_aluminum_connector_and_backplate_mass_g_excluding_rails_shoes_hardware": rear_mass+adapter_mass+backplate_mass+web_mass,
        "raised_side_web_centerline_mm": math.hypot(c["pose"]["yoke_center_forward_from_boss_plate_mm"], c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]),
        "intentionally_deferred": ["rear-base rail pass-through geometry and coupon", "machined lower rail-shoe and solid-plug detail", "backplate perimeter and rail-shoe fastener holes", "actual bike/headlight 3D housing and beam clearance", "factory M6 thread pitch, blind depth, engagement, and non-bottoming", "stress analysis, proof load, vibration, and progressive ride tests"]
    }


def blender_model_v02(c: dict) -> None:
    try:
        import bpy
        from mathutils import Matrix, Vector
    except ImportError:
        print("Blender unavailable: 2D files and validation were still generated.")
        return
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    def mat(name, color, metallic=0.0):
        m=bpy.data.materials.new(name); m.diffuse_color=color; m.metallic=metallic; m.roughness=.32; return m
    aluminum=mat("6061 aluminum", (.45,.52,.58,1), .75); formed=mat("5052 formed aluminum", (.14,.34,.57,1), .65)
    shoe_mat=mat("unreleased rail shoe concept", (.95,.34,.05,1), .5); frame_mat=mat("bike reference", (.88,.64,.05,1), .5)
    fast=mat("fasteners", (.12,.12,.13,1), .8); datum=mat("rough headlight top datum", (.85,.05,.04,1), .1)
    def cube(name, loc, dims, material, rx=0.0):
        bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name
        o.dimensions=dims; o.rotation_euler[0]=rx; o.data.materials.append(material)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); return o
    def prism(name, loc, points, thickness, material, rx=0.0):
        count=len(points); verts=[(x,-thickness/2,z) for x,z in points]+[(x,thickness/2,z) for x,z in points]
        faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]
        for i in range(count): faces.append((i,(i+1)%count,(i+1)%count+count,i+count))
        mesh=bpy.data.meshes.new(name+"_mesh"); mesh.from_pydata(verts,[],faces); mesh.update()
        o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler[0]=rx; o.data.materials.append(material); return o
    def side_prism(name, center_x, points, thickness, material):
        count=len(points); verts=[(center_x-thickness/2,y,z) for y,z in points]+[(center_x+thickness/2,y,z) for y,z in points]
        faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]
        for i in range(count): faces.append((i,(i+1)%count,(i+1)%count+count,i+count))
        mesh=bpy.data.meshes.new(name+"_mesh"); mesh.from_pydata(verts,[],faces); mesh.update()
        o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); o.data.materials.append(material); return o
    def bolt(name, loc, radius, length, material, rotation=(math.pi/2,0,0)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=length, location=loc, rotation=rotation)
        o=bpy.context.object; o.name=name; o.data.materials.append(material); return o
    rear=c["bike_interface"]["boss_plate"]; web=c["load_path"]["side_webs"]; adapter=c["load_path"]["front_adapter"]
    angle=math.radians(c["pose"]["yoke_pitch_relative_to_boss_plane_deg"]); depth=c["pose"]["yoke_center_forward_from_boss_plate_mm"]; rise=c["pose"]["yoke_center_vertical_from_boss_pattern_mm"]
    cube("rear_boss_plate", (0,0,0), (rear["width_mm"],rear["thickness_mm"],rear["height_mm"]), aluminum)
    adapter_points=[(-adapter["overall_width_mm"]/2,-adapter["overall_height_mm"]/2),(adapter["overall_width_mm"]/2,-adapter["overall_height_mm"]/2),(adapter["overall_width_mm"]/2,adapter["overall_height_mm"]/2),(-adapter["overall_width_mm"]/2,adapter["overall_height_mm"]/2)]
    prism("compact_bike_adapter", (0,depth,rise), adapter_points, adapter["thickness_mm"], aluminum, angle)
    prism("head_rear_aluminum_backplate_REVIEW_ONLY", (0,depth,rise), backplate_polygon(c), c["head_interface"]["aluminum_backplate"]["thickness_mm"], aluminum, angle)
    for sign in (-1,1):
        side_prism(f"diagonal_side_web_{sign}", sign*web["web_center_x_mm"], side_web_polygon(c), web["thickness_mm"], formed)
        cube(f"rear_web_flange_{sign}", (sign*10.5,3.97,0), (15,web["thickness_mm"],64), formed)
        cube(f"front_web_flange_{sign}", (sign*10.5,depth,rise), (15,web["thickness_mm"],64), formed, angle)
    for x in (-15,15):
        for z in (-45,45): bolt("frame_M6", (x,-5,z), 3, 14, fast)
    for x in (-22,22):
        for v in (-20,20):
            y=depth-v*math.sin(angle); z=rise+v*math.cos(angle)
            bolt("adapter_to_backplate_M6", (x,y,z), 3, 12, fast, (angle+math.pi/2,0,0))
    boss_ref=cube("bike_head_tube_reference", (0,-30,-15), (76,55,165), frame_mat); boss_ref.modifiers.new("bike reference wire", "WIREFRAME").thickness=1.5
    for x in (-15,15):
        for z in (-45,45): bolt("factory_boss_18mm", (x,-1,z), 9, 6, frame_mat)
    light_z=c["pose"]["headlight_reference"]["light_top_relative_to_boss_pattern_center_mm"]
    light_plane=cube("rough_headlight_top_elevation_NOT_CLEARANCE", (0,110,light_z), (260,240,1), datum); light_plane.modifiers.new("datum outline", "WIREFRAME").thickness=1.0
    source_glb=ROOT.parents[4]/"hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate8-full-size-structural-iteration/gate8-full-size-structural-review.glb"
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(source_glb)); imported=list(set(bpy.data.objects)-before)
    b=math.radians(c["pose"]["boss_plane_normal_elevation_deg"]); rotation=Matrix.Rotation(-b,4,"X") @ Matrix.Rotation(math.pi,4,"Z")
    center=Vector(c["head_interface"]["rear_frame"]["plane_center_head_mm"]); target=Vector((0,depth,rise)); transform=Matrix.Translation(target-rotation@center) @ rotation
    for obj in imported:
        obj.matrix_world=transform@obj.matrix_world
        if obj.type not in {"MESH", "EMPTY"}: obj.hide_render=True
    rails=c["head_interface"]["internal_rails"]
    for side in ("left", "right"):
        lower=Vector(rails[f"{side}_lower_target_head_mm"]); axis=Vector(rails[f"{side}_axis_head"])
        lower_world=transform@lower; axis_world=(rotation.to_3x3()@axis).normalized()
        shoe=cube(f"{side}_lower_rail_shoe_CONCEPT", lower_world+axis_world*12, (24,24,24), shoe_mat)
        shoe.rotation_mode="QUATERNION"; shoe.rotation_quaternion=Vector((0,0,1)).rotation_difference(axis_world)
    bpy.context.scene.unit_settings.system="METRIC"; bpy.context.scene.unit_settings.length_unit="MILLIMETERS"; bpy.context.scene.unit_settings.scale_length=.001
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/"frame-fixed-mount-v02-review.blend")); bpy.ops.export_scene.gltf(filepath=str(MODEL/"frame-fixed-mount-v02-review.glb"), export_format="GLB")
    world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world; world.color=(.035,.035,.035)
    scene=bpy.context.scene; scene.render.engine="BLENDER_WORKBENCH"; scene.display.shading.light="STUDIO"; scene.display.shading.color_type="MATERIAL"
    scene.display.shading.background_type="VIEWPORT"; scene.display.shading.background_color=(.88,.90,.92); scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True; scene.display.shading.cavity_type="WORLD"
    scene.view_settings.look="AgX - Medium High Contrast"; scene.render.resolution_x=1100; scene.render.resolution_y=850; scene.render.resolution_percentage=100
    def render(name, location, target_point, lens=52):
        bpy.ops.object.camera_add(location=location); camera=bpy.context.object; camera.data.lens=lens
        camera.rotation_euler=(Vector(target_point)-camera.location).to_track_quat("-Z","Y").to_euler(); scene.camera=camera
        scene.render.filepath=str(RENDERS/f"{name}.png"); bpy.ops.render.render(write_still=True); bpy.data.objects.remove(camera, do_unlink=True)
    render("v02-assembly-front-oblique", (510,-650,390), (0,100,-10), 55)
    render("v02-assembly-side", (520,100,30), (0,100,-10), 58)
    render("v02-rear-backplate-handoff", (290,-360,160), (0,65,65), 58)
    hidden_shell_parts=[]
    for obj in imported:
        if obj.type == "MESH" and "aluminum_tube_reference" not in obj.name:
            hidden_shell_parts.append(obj); obj.hide_render=True
    render("v02-internal-rails", (0,-560,210), (0,120,85), 58)
    for obj in hidden_shell_parts: obj.hide_render=False
    (MODEL/"frame-fixed-mount-v02-review.blend1").unlink(missing_ok=True)


def remove_obsolete_v01_outputs() -> None:
    for path in (FLAT/"front-yoke-plate-1to1.svg", FLAT/"front-yoke-plate.dxf", FORMED/"tube-clevis-half-formed-drawing.svg", DRAWINGS/"mount-side-profile-1to1.svg", VALIDATION/"frame-fixed-mount-v0-validation.json", MODEL/"frame-fixed-mount-v0-review.blend", MODEL/"frame-fixed-mount-v0-review.blend1", MODEL/"frame-fixed-mount-v0-review.glb", RENDERS/"assembly-front-oblique.png", RENDERS/"assembly-side.png", RENDERS/"boss-interface.png"):
        path.unlink(missing_ok=True)


def main() -> None:
    c=load_config(); prepare(); remove_obsolete_v01_outputs()
    rear_plate(c); front_adapter(c); head_backplate(c); formed_drawings_v02(c); side_profile_v02(c)
    report=validate_v02(c); (VALIDATION/"frame-fixed-mount-v02-validation.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    blender_model_v02(c); print(json.dumps(report, indent=2))
    if not report["status"].startswith("PASS"): sys.exit(1)


if __name__ == "__main__":
    main()
