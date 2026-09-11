#!/usr/bin/env python3
"""Create a review-only structured-anchor pack for asymmetric eye mounts.

This script reconstructs the hash-pinned V7 review in memory and saves only a
new review document containing unchanged reference shapes plus highlighted
anchor faces/points.  It creates no connector geometry and mutates neither V7
nor any canonical head or eye source.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / ".git").exists() and (candidate / "hardware").exists():
            return candidate
    raise RuntimeError("repository root not found")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def load_v7(root: Path, contract: dict[str, Any]) -> Any:
    for name, pin in contract["inputs"].items():
        path = root / str(pin["path"])
        actual = sha256_file(path)
        if actual != str(pin["sha256"]):
            raise RuntimeError(f"{name}: pin mismatch {actual} != {pin['sha256']}")
    source = root / str(contract["inputs"]["v7_generator"]["path"])
    spec = importlib.util.spec_from_file_location("_pinned_eye_v7_for_mount_anchors", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def vector_values(value: Any) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def normalized(App: Any, value: Any, label: str) -> Any:
    result = App.Vector(float(value.x), float(value.y), float(value.z))
    if float(result.Length) <= 1.0e-9:
        raise RuntimeError(f"{label} is degenerate")
    result.normalize()
    return result


def face_normal(App: Any, face: Any) -> Any:
    try:
        u0, u1, v0, v1 = face.ParameterRange
        return normalized(App, face.normalAt((u0 + u1) * 0.5, (v0 + v1) * 0.5), "face normal")
    except Exception:
        center = face.CenterOfMass
        nearest = min(face.Vertexes, key=lambda vertex: float((vertex.Point - center).Length))
        return normalized(App, center - nearest.Point, "fallback face normal")


def edge_frame(App: Any, loop: Sequence[Any], index: int, axis_n: Any, center: Any) -> tuple[Any, Any, Any, float]:
    start = loop[index]
    end = loop[(index + 1) % len(loop)]
    delta = end - start
    length = float(delta.Length)
    tangent = normalized(App, delta, f"edge {index} tangent")
    inward = normalized(App, axis_n.cross(tangent), f"edge {index} inward")
    midpoint = (start + end) * 0.5
    if float((center - midpoint).dot(inward)) < 0.0:
        inward = inward * -1.0
    return start, tangent, inward, length


def select_carrier_face(carrier: Any, target: Any, desired_normal: Any, App: Any, Part: Any) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, face in enumerate(carrier.Faces, start=1):
        center = face.CenterOfMass
        distance = float((target - center).Length)
        try:
            shape_distance = float(face.distToShape(Part.Vertex(target))[0])
        except Exception:
            shape_distance = distance
        normal = face_normal(App, face)
        alignment = abs(float(normal.dot(desired_normal)))
        records.append({
            "face_index": index,
            "face_name": f"Face{index}",
            "area_mm2": float(face.Area),
            "centroid_world_mm": vector_values(center),
            "normal_world": vector_values(normal),
            "centroid_distance_mm": distance,
            "shape_distance_mm": shape_distance,
            "normal_alignment_abs": alignment,
            "shape": face,
        })
    records.sort(key=lambda item: (item["shape_distance_mm"], -item["normal_alignment_abs"], -item["area_mm2"]))
    return records[0]


def select_bottom_head_faces(
    shell: Any,
    target: Any,
    eye_outward: Any,
    policy: dict[str, Any],
    App: Any,
    Part: Any,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    minimum_area = float(policy["minimum_head_face_area_mm2"])
    maximum_distance = float(policy["maximum_bottom_head_face_distance_mm"])
    minimum_facing = float(policy["minimum_facing_normal_dot"])
    for index, face in enumerate(shell.Faces, start=1):
        if float(face.Area) < minimum_area:
            continue
        center = face.CenterOfMass
        distance = float(face.distToShape(Part.Vertex(target))[0])
        if distance > maximum_distance:
            continue
        normal = face_normal(App, face)
        facing = abs(float(normal.dot(eye_outward)))
        if facing < minimum_facing:
            continue
        candidates.append({
            "face_index": index,
            "face_name": f"Face{index}",
            "area_mm2": float(face.Area),
            "centroid_world_mm": vector_values(center),
            "normal_world": vector_values(normal),
            "distance_to_bottom_left_eye_anchor_mm": distance,
            "facing_alignment_abs": facing,
            "shape": face,
        })
    candidates.sort(key=lambda item: (item["distance_to_bottom_left_eye_anchor_mm"], -item["facing_alignment_abs"], -item["area_mm2"]))
    count = int(policy["bottom_head_candidate_count"])
    if not candidates:
        raise RuntimeError("no bottom-left head face satisfies the declared anchor policy")
    return candidates[:count]


def strip_shape(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "shape"}


def build_context() -> dict[str, Any]:
    root = repository_root()
    contract = load_json(HERE / "contract.json")
    v7 = load_v7(root, contract)
    context = v7.prepare()
    App = context["App"]
    Part = context["Part"]
    policy = contract["anchor_policy"]
    box_outer = context["box_outer"]
    box_center = context["toolkit"].average(App, box_outer)
    axis_n = context["axis_n"]
    depth = float(policy["anchor_front_depth_mm"])

    top_edge = int(policy["top_eye_wall_edge_index"])
    top_start, top_tangent, top_inward, top_length = edge_frame(App, box_outer, top_edge, axis_n, box_center)
    top_eye_point = top_start + top_tangent * (top_length * float(policy["top_eye_wall_tangent_fraction"])) + axis_n * depth
    top_eye_outward = top_inward * -1.0

    bottom_edge = int(policy["bottom_left_eye_wall_edge_index"])
    bottom_start, bottom_tangent, bottom_inward, bottom_length = edge_frame(App, box_outer, bottom_edge, axis_n, box_center)
    bottom_eye_point = bottom_start + bottom_tangent * (bottom_length * float(policy["bottom_left_eye_wall_tangent_fraction"])) + axis_n * depth
    bottom_eye_outward = bottom_inward * -1.0

    top_face_index = int(str(policy["top_head_face"]).replace("Face", ""))
    if top_face_index < 1 or top_face_index > len(context["shell"].Faces):
        raise RuntimeError("declared top head face is unavailable")
    top_head_face = context["shell"].Faces[top_face_index - 1]
    top_head_normal = face_normal(App, top_head_face)
    top_eye_face = select_carrier_face(context["carrier"], top_eye_point, top_eye_outward, App, Part)
    bottom_eye_face = select_carrier_face(context["carrier"], bottom_eye_point, bottom_eye_outward, App, Part)
    bottom_candidates = select_bottom_head_faces(context["shell"], bottom_eye_point, bottom_eye_outward, policy, App, Part)
    bottom_head = bottom_candidates[0]

    top_gap = float(top_head_face.distToShape(Part.Vertex(top_eye_point))[0])
    bottom_gap = float(bottom_head["shape"].distToShape(Part.Vertex(bottom_eye_point))[0])

    context.update({
        "anchor_contract": contract,
        "anchor_top_eye_point": top_eye_point,
        "anchor_top_eye_outward": top_eye_outward,
        "anchor_bottom_eye_point": bottom_eye_point,
        "anchor_bottom_eye_outward": bottom_eye_outward,
        "anchor_top_head_face": top_head_face,
        "anchor_top_head_record": {
            "face_index": top_face_index,
            "face_name": f"Face{top_face_index}",
            "area_mm2": float(top_head_face.Area),
            "centroid_world_mm": vector_values(top_head_face.CenterOfMass),
            "normal_world": vector_values(top_head_normal),
            "distance_to_top_eye_anchor_mm": top_gap,
        },
        "anchor_top_eye_face": top_eye_face["shape"],
        "anchor_top_eye_record": strip_shape(top_eye_face),
        "anchor_bottom_eye_face": bottom_eye_face["shape"],
        "anchor_bottom_eye_record": strip_shape(bottom_eye_face),
        "anchor_bottom_head_face": bottom_head["shape"],
        "anchor_bottom_head_record": strip_shape(bottom_head),
        "anchor_bottom_head_candidates": [strip_shape(item) for item in bottom_candidates],
        "anchor_top_gap_mm": top_gap,
        "anchor_bottom_gap_mm": bottom_gap,
    })
    return context


def add_feature(v7: Any, context: dict[str, Any], doc: Any, name: str, label: str, shape: Any, color: tuple[float, float, float], transparency: int) -> Any:
    return v7.add_feature(context, doc, name, label, shape, color, transparency)


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    Part = context["Part"]
    generator = load_v7(context["root"], context["anchor_contract"])
    policy = context["anchor_contract"]["anchor_policy"]
    marker_radius = float(policy["marker_radius_mm"])
    normal_length = float(policy["normal_marker_length_mm"])
    top_marker = Part.makeSphere(marker_radius, context["anchor_top_eye_point"])
    bottom_marker = Part.makeSphere(marker_radius, context["anchor_bottom_eye_point"])
    top_axis = Part.makeCylinder(0.22, normal_length, context["anchor_top_eye_point"], context["anchor_top_eye_outward"])
    bottom_axis = Part.makeCylinder(0.22, normal_length, context["anchor_bottom_eye_point"], context["anchor_bottom_eye_outward"])
    doc = App.newDocument("RightEyeHeadMountAnchorReviewV8")
    try:
        add_feature(generator, context, doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL", "REFERENCE — RELIEVED RIGHT HEAD SHELL", context["shell"], (0.70, 0.70, 0.73), 72)
        add_feature(generator, context, doc, "REFERENCE__APPROVED_V7_EYE_CARRIER", "REFERENCE — APPROVED V7 EYE CARRIER", context["carrier"], (0.12, 0.72, 0.28), 58)
        add_feature(generator, context, doc, "ANCHOR__TOP_HEAD_FACE382", "ANCHOR — TOP HEAD FACE382", context["anchor_top_head_face"], (0.15, 0.40, 1.00), 0)
        add_feature(generator, context, doc, "ANCHOR__TOP_EYE_WALL_FACE", f"ANCHOR — TOP EYE WALL {context['anchor_top_eye_record']['face_name']}", context["anchor_top_eye_face"], (0.08, 0.95, 0.35), 0)
        add_feature(generator, context, doc, "ANCHOR__TOP_FASTENER_POINT_AND_AXIS", "ANCHOR — TOP DIRECT WALL FASTENER", Part.makeCompound([top_marker, top_axis]), (1.00, 0.80, 0.05), 0)
        add_feature(generator, context, doc, "ANCHOR__BOTTOM_LEFT_HEAD_FACE", f"ANCHOR — BOTTOM-LEFT HEAD {context['anchor_bottom_head_record']['face_name']}", context["anchor_bottom_head_face"], (0.80, 0.20, 0.95), 0)
        add_feature(generator, context, doc, "ANCHOR__BOTTOM_LEFT_EYE_WALL_FACE", f"ANCHOR — BOTTOM-LEFT EYE {context['anchor_bottom_eye_record']['face_name']}", context["anchor_bottom_eye_face"], (0.10, 0.95, 0.92), 0)
        add_feature(generator, context, doc, "ANCHOR__BOTTOM_LEFT_PAIR_POINT_AND_AXIS", "ANCHOR — BOTTOM-LEFT MATING FLANGE PAIR", Part.makeCompound([bottom_marker, bottom_axis]), (1.00, 0.25, 0.08), 0)
        doc.recompute()
        path = output / context["anchor_contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def report(context: dict[str, Any], elapsed: float, fcstd: Path | None) -> dict[str, Any]:
    result = {
        "schema_version": "cat-head-right-eye-head-mount-anchor-review-v8-report",
        "status": "ANCHOR_REVIEW_READY__NO_CONNECTOR_GEOMETRY",
        "authority": context["anchor_contract"]["authority"],
        "elapsed_seconds": elapsed,
        "top": {
            "head": context["anchor_top_head_record"],
            "eye": context["anchor_top_eye_record"],
            "point_world_mm": vector_values(context["anchor_top_eye_point"]),
            "outward_axis_world": vector_values(context["anchor_top_eye_outward"]),
            "gap_to_head_face_mm": context["anchor_top_gap_mm"],
            "architecture": context["anchor_contract"]["deferred_connector_contract"]["top"],
        },
        "bottom_left": {
            "head": context["anchor_bottom_head_record"],
            "eye": context["anchor_bottom_eye_record"],
            "point_world_mm": vector_values(context["anchor_bottom_eye_point"]),
            "outward_axis_world": vector_values(context["anchor_bottom_eye_outward"]),
            "gap_to_head_face_mm": context["anchor_bottom_gap_mm"],
            "ranked_head_candidates": context["anchor_bottom_head_candidates"],
            "architecture": context["anchor_contract"]["deferred_connector_contract"]["bottom_left"],
        },
        "pins": {
            "contract_sha256": sha256_file(HERE / "contract.json"),
            "generator_sha256": sha256_file(Path(__file__)),
            **{name + "_sha256": value["sha256"] for name, value in context["anchor_contract"]["inputs"].items()},
        },
        "holds": context["anchor_contract"]["holds"],
        "io_trace": {
            "v7_reconstructed_in_memory": True,
            "v7_source_saved": False,
            "connector_geometry_created": False,
            "review_fcstd_saved": fcstd is not None,
            "geometry_export_created": False,
        },
    }
    if fcstd is not None:
        result["review_fcstd"] = str(fcstd.relative_to(context["root"]))
        result["review_fcstd_sha256"] = sha256_file(fcstd)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("measure", "review"), required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = build_context()
    if args.mode == "measure":
        data = report(context, time.monotonic() - started, None)
        if args.report is not None:
            if args.report.exists():
                raise RuntimeError(f"report already exists: {args.report}")
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    output = context["root"] / context["anchor_contract"]["output"]["directory"]
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    output.mkdir(parents=True)
    fcstd = create_review(context, output)
    data = report(context, time.monotonic() - started, fcstd)
    validation = output / context["anchor_contract"]["output"]["validation"]
    validation.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(data["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
