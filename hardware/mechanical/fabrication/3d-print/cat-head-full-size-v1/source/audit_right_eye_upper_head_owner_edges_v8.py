#!/usr/bin/env python3
"""Measure which right-eye perimeter edge can support an upper-head-owned pair.

This is a read-only geometry audit.  It creates temporary flange leaves in the
open V7 Blender source, reports exact owner overlaps and pair gaps, and removes
the temporary objects without saving the blend file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate5_ribs_and_joints as gate5
import generate_gate6_eye_modules as gate6
import generate_eye_all_eight_flange_broad_base_review_v3 as frames
import generate_right_eye_all_four_plain_flange_thickness_review_v5 as v5
import generate_right_eye_head_flange_exterior_clip_review_v6 as v6


def frame_for_edge(geometry: dict, edge: tuple[int, int]) -> dict:
    settings = gate6.CONFIG["head_mount"]
    outer = geometry["outer"]
    aperture = geometry["aperture"]
    inward = geometry["inward"]
    first, second = edge
    anchor = (outer[first] + outer[second]) / 2.0
    aperture_midpoint = (aperture[first] + aperture[second]) / 2.0
    tangent = outer[second] - outer[first]
    tangent -= inward * tangent.dot(inward)
    tangent.normalize()
    radial = inward.cross(tangent).normalized()
    if radial.dot(aperture_midpoint - anchor) < 0.0:
        radial = -radial
    length = float(settings["tab_length_mm"])
    depth = float(settings["tab_depth_mm"])
    thickness = float(settings["tab_thickness_mm"])
    gap = float(settings["tab_face_gap_mm"])
    overlap = float(settings["shell_overlap_mm"])
    front_recess = float(settings["front_recess_mm"])
    hole_depth = float(settings["bolt_depth_from_eye_plane_mm"])
    head_center = anchor + radial * (thickness / 2.0 - overlap) + inward * (front_recess + depth / 2.0)
    eye_center = anchor + radial * (thickness - overlap + gap + thickness / 2.0) + inward * (front_recess + depth / 2.0)
    return {
        "role": f"edge_{first}_{second}",
        "edge": [first, second],
        "anchor": anchor,
        "tangent": tangent,
        "inward": inward,
        "radial": radial,
        "dimensions": (length, depth, thickness),
        "head_center": head_center,
        "eye_center": eye_center,
        "head_hole_center": head_center + inward * (hole_depth - depth / 2.0),
        "eye_hole_center": eye_center + inward * (hole_depth - depth / 2.0),
        "hole_diameter": float(settings["m2_5_clearance_diameter_mm"]),
        "front_recess": front_recess,
        "mating_gap": gap,
    }


def evaluate_frame(frame: dict, upper_head, bucket, material, added_thickness: float = 2.4) -> dict:
    leaves = []
    try:
        for owner_kind in ("head", "eye"):
            leaf = v5.create_thick_plain_flange(
                f"AUDIT__V8__{frame['role']}__{owner_kind}",
                frame,
                owner_kind,
                added_thickness,
                material,
            )
            leaves.append(leaf)
        return {
            "edge": frame["edge"],
            "anchor_mm": [round(value, 5) for value in frame["anchor"]],
            "radial": [round(value, 7) for value in frame["radial"]],
            "upper_head_overlap_mm3": round(v5.v3.intersection_volume(leaves[0], upper_head), 6),
            "eye_bucket_overlap_mm3": round(v5.v3.intersection_volume(leaves[1], bucket), 6),
            "pair_clearance_mm": round(v5.v3.distance(leaves[0], leaves[1]), 6),
            "pair_interference_mm3": round(v5.v3.intersection_volume(leaves[0], leaves[1]), 6),
            "upper_head_distance_mm": round(v5.v3.distance(leaves[0], upper_head), 6),
            "eye_bucket_distance_mm": round(v5.v3.distance(leaves[1], bucket), 6),
        }
    finally:
        for leaf in leaves:
            if leaf.name in bpy.data.objects:
                bpy.data.objects.remove(leaf, do_unlink=True)


def reversed_pair(frame: dict, upper_head, bucket, material) -> dict:
    """Put the upper-head leaf on +radial and the eye leaf on -radial."""
    original = float(frame["dimensions"][2])
    total = original + 2.4
    leaves = []
    try:
        for owner_kind, source_kind, backing_sign in (
            ("head", "eye", +1.0),
            ("eye", "head", -1.0),
        ):
            center = frame[f"{source_kind}_center"] + frame["radial"] * backing_sign * 1.2
            leaf = gate5.box(
                f"AUDIT__V8_REVERSED__{frame['role']}__{owner_kind}",
                center,
                (frame["tangent"], frame["inward"], frame["radial"]),
                (float(frame["dimensions"][0]), float(frame["dimensions"][1]), total),
                material,
            )
            gate6.cut_axis_hole(
                leaf,
                f"{leaf.name}__M2_5_THROUGH",
                frame[f"{source_kind}_hole_center"],
                frame["radial"],
                float(frame["hole_diameter"]),
                total + 8.0,
            )
            leaves.append(leaf)
        return {
            "upper_head_overlap_mm3": round(v5.v3.intersection_volume(leaves[0], upper_head), 6),
            "eye_bucket_overlap_mm3": round(v5.v3.intersection_volume(leaves[1], bucket), 6),
            "pair_clearance_mm": round(v5.v3.distance(leaves[0], leaves[1]), 6),
            "pair_interference_mm3": round(v5.v3.intersection_volume(leaves[0], leaves[1]), 6),
            "upper_head_distance_mm": round(v5.v3.distance(leaves[0], upper_head), 6),
            "eye_bucket_distance_mm": round(v5.v3.distance(leaves[1], bucket), 6),
        }
    finally:
        for leaf in leaves:
            if leaf.name in bpy.data.objects:
                bpy.data.objects.remove(leaf, do_unlink=True)


def evaluate_clipped_pair(frame: dict, upper_head, bucket, material) -> dict:
    """Measure the pair after clipping the head blank to the real exterior skin."""
    original = float(frame["dimensions"][2])
    total = float(frame["target_total_thickness_mm"])
    added = total - original
    leaves = []
    clip_material = v5.v3.material("AUDIT__V8_INTERIOR_HALFSPACE", (0.0, 1.0, 0.0, 1.0))
    try:
        head = v6.create_thick_plain_flange_blank(
            f"AUDIT__V8_CLIPPED__{frame['role']}__head",
            frame,
            added,
            material,
        )
        leaves.append(head)
        point, normal, face_index, anchor_distance, diagnostics = v6.exterior_plane(
            upper_head, frame, head
        )
        clip_point, _ = v6.clip_to_interior_halfspace(
            head, frame, point, normal, 0.03, clip_material
        )
        gate6.cut_axis_hole(
            head,
            f"{head.name}__M2_5_THROUGH",
            frame["head_hole_center"],
            frame["radial"],
            float(frame["hole_diameter"]),
            total + 8.0,
        )
        v6.triangulate_for_exact_exchange(head)
        eye = v5.create_thick_plain_flange(
            f"AUDIT__V8_CLIPPED__{frame['role']}__eye",
            frame,
            "eye",
            added,
            material,
        )
        leaves.append(eye)
        return {
            "upper_head_overlap_mm3": round(v5.v3.intersection_volume(head, upper_head), 6),
            "eye_bucket_overlap_mm3": round(v5.v3.intersection_volume(eye, bucket), 6),
            "pair_clearance_mm": round(v5.v3.distance(head, eye), 6),
            "pair_interference_mm3": round(v5.v3.intersection_volume(head, eye), 6),
            "post_clip_exterior_deviation_mm": round(
                v6.maximum_signed_distance(head, clip_point, normal), 6
            ),
            "clip_face_zero_based": face_index,
            "clip_anchor_distance_mm": round(anchor_distance, 6),
            "head_topology": v5.v3.topology(head),
            "eye_topology": v5.v3.topology(eye),
            "clip_diagnostics": diagnostics,
        }
    except Exception as error:
        return {"error": str(error)}
    finally:
        for leaf in leaves:
            if leaf.name in bpy.data.objects:
                bpy.data.objects.remove(leaf, do_unlink=True)


def main() -> None:
    geometry = next(item for item in gate6.eye_geometry() if item["side"] == "right")
    upper_head = bpy.data.objects["right_upper_head"]
    bucket = bpy.data.objects["FROZEN__RIGHT_EYE_BUCKET_V9_V6"]
    material = v5.v3.material("AUDIT__V8_EDGE_CONTACT", (1.0, 0.0, 1.0, 1.0))
    results = []
    for first in range(4):
        edge = (first, (first + 1) % 4)
        frame = frame_for_edge(geometry, edge)
        result = evaluate_frame(frame, upper_head, bucket, material)
        result["reversed_order"] = reversed_pair(frame, upper_head, bucket, material)
        results.append(result)
    print("V8_EDGE_OWNER_AUDIT=" + json.dumps(results, sort_keys=True))
    shared = frames.mount_frames(geometry)["outer"]
    shifted_results = []
    for shift in (-20.0, -18.0, 18.0, 20.0):
        shifted = dict(shared)
        delta = shared["tangent"] * shift
        for key in ("anchor", "head_center", "eye_center", "head_hole_center", "eye_hole_center"):
            shifted[key] = shared[key] + delta
        shifted["role"] = f"shared_edge_shift_{shift:+.1f}"
        record = evaluate_frame(shifted, upper_head, bucket, material)
        record["tangent_shift_mm"] = shift
        shifted_results.append(record)
    print("V8_SHARED_EDGE_SHIFT_AUDIT=" + json.dumps(shifted_results, sort_keys=True))
    perimeter_sweep = []
    for edge in ((0, 1), (1, 2), (2, 3)):
        base = frame_for_edge(geometry, edge)
        half_length = (geometry["outer"][edge[1]] - geometry["outer"][edge[0]]).length / 2.0
        for fraction in (-0.38, -0.25, 0.0, 0.25, 0.38):
            shift = half_length * fraction * 2.0
            shifted = dict(base)
            delta = base["tangent"] * shift
            for key in ("anchor", "head_center", "eye_center", "head_hole_center", "eye_hole_center"):
                shifted[key] = base[key] + delta
            shifted["role"] = f"edge_{edge[0]}_{edge[1]}_fraction_{fraction:+.2f}"
            record = evaluate_frame(shifted, upper_head, bucket, material)
            record["edge_fraction_from_midpoint"] = fraction
            record["tangent_shift_mm"] = round(shift, 5)
            perimeter_sweep.append(record)
    print("V8_PERIMETER_POSITION_SWEEP=" + json.dumps(perimeter_sweep, sort_keys=True))
    direct_root_sweep = []
    base = frame_for_edge(geometry, (0, 1))
    edge_length = (geometry["outer"][1] - geometry["outer"][0]).length
    for fraction in (0.18, 0.20, 0.22, 0.24, 0.26, 0.28):
        shift = edge_length * fraction
        shifted = dict(base)
        delta = base["tangent"] * shift
        for key in ("anchor", "head_center", "eye_center", "head_hole_center", "eye_hole_center"):
            shifted[key] = base[key] + delta
        shifted["role"] = f"direct_upper_head_fraction_{fraction:.2f}"
        for total_thickness in (4.8, 6.0, 7.2, 8.0):
            record = evaluate_frame(
                shifted,
                upper_head,
                bucket,
                material,
                total_thickness - float(shifted["dimensions"][2]),
            )
            record["edge_fraction_from_midpoint"] = fraction
            record["total_radial_thickness_mm"] = total_thickness
            direct_root_sweep.append(record)
    print("V8_DIRECT_UPPER_HEAD_ROOT_SWEEP=" + json.dumps(direct_root_sweep, sort_keys=True))
    plain_rectangle_sweep = []
    base = frame_for_edge(geometry, (0, 1))
    shift = (geometry["outer"][1] - geometry["outer"][0]).length * 0.26
    delta = base["tangent"] * shift
    for length, depth, total_thickness in (
        (14.0, 10.0, 4.8),
        (16.0, 10.0, 4.8),
        (16.0, 10.0, 6.0),
        (16.0, 12.0, 4.8),
        (18.0, 10.0, 4.8),
    ):
        shifted = dict(base)
        depth_delta = depth - float(base["dimensions"][1])
        shifted["dimensions"] = (length, depth, float(base["dimensions"][2]))
        for key in ("anchor", "head_center", "eye_center", "head_hole_center", "eye_hole_center"):
            shifted[key] = base[key] + delta
        for key in ("head_center", "eye_center"):
            shifted[key] += base["inward"] * (depth_delta / 2.0)
        shifted["role"] = f"plain_{length:.0f}x{depth:.0f}x{total_thickness:.1f}"
        record = evaluate_frame(
            shifted,
            upper_head,
            bucket,
            material,
            total_thickness - float(base["dimensions"][2]),
        )
        record["dimensions_mm"] = [length, depth, total_thickness]
        record["edge_fraction_from_midpoint"] = 0.26
        plain_rectangle_sweep.append(record)
    print("V8_PLAIN_RECTANGLE_SWEEP=" + json.dumps(plain_rectangle_sweep, sort_keys=True))
    post_clip_sweep = []
    for fraction in (0.22, 0.24, 0.26, 0.28, 0.30):
        base = frame_for_edge(geometry, (0, 1))
        edge_length = (geometry["outer"][1] - geometry["outer"][0]).length
        tangent_delta = base["tangent"] * edge_length * fraction
        for length, depth, total_thickness in (
            (14.0, 10.0, 4.8),
            (14.0, 14.0, 4.8),
            (14.0, 18.0, 4.8),
            (18.0, 14.0, 4.8),
            (18.0, 18.0, 4.8),
            (22.0, 18.0, 4.8),
            (18.0, 18.0, 6.0),
        ):
            candidate = dict(base)
            depth_delta = depth - float(base["dimensions"][1])
            candidate["dimensions"] = (length, depth, float(base["dimensions"][2]))
            candidate["target_total_thickness_mm"] = total_thickness
            for key in ("anchor", "head_center", "eye_center", "head_hole_center", "eye_hole_center"):
                candidate[key] = base[key] + tangent_delta
            for key in ("head_center", "eye_center"):
                candidate[key] += base["inward"] * (depth_delta / 2.0)
            candidate["role"] = f"post_clip_{fraction:.2f}_{length:.0f}x{depth:.0f}x{total_thickness:.1f}"
            record = evaluate_clipped_pair(candidate, upper_head, bucket, material)
            record["edge_fraction_from_midpoint"] = fraction
            record["dimensions_mm"] = [length, depth, total_thickness]
            post_clip_sweep.append(record)
    print("V8_POST_CLIP_ROOT_SWEEP=" + json.dumps(post_clip_sweep, sort_keys=True))


if __name__ == "__main__":
    main()
