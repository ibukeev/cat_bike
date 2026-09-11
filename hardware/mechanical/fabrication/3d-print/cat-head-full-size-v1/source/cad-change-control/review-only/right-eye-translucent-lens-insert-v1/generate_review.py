#!/usr/bin/env python3
"""Validate and render the final static front carrier + translucent lens."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
EPSILON_MM3 = 1.0e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def load_module(path: Path, digest: str, name: str) -> Any:
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"{path}: hash mismatch {actual} != {digest}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def aabb_near(first: Any, second: Any) -> bool:
    a, b = first.BoundBox, second.BoundBox
    return not (
        a.XMax < b.XMin or b.XMax < a.XMin
        or a.YMax < b.YMin or b.YMax < a.YMin
        or a.ZMax < b.ZMin or b.ZMax < a.ZMin
    )


def common_volume(first: Any, second: Any) -> float:
    if not aabb_near(first, second):
        return 0.0
    common = first.common(second)
    return 0.0 if common.isNull() else float(common.Volume)


def prepare() -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    front_spec = contract["front_interface"]
    front_path = (HERE / front_spec["generator"]).resolve()
    adjudication_path = (HERE / front_spec["adjudication"]).resolve()
    validation_path = (HERE / front_spec["review_validation"]).resolve()
    front = load_module(front_path, front_spec["generator_sha256"], "_lens_v1_front")
    if sha256_file(adjudication_path) != front_spec["adjudication_sha256"]:
        raise RuntimeError("front adjudication hash mismatch")
    if sha256_file(validation_path) != front_spec["review_validation_sha256"]:
        raise RuntimeError("front review validation hash mismatch")
    adjudication = load_json(adjudication_path)
    if adjudication.get("disposition") != "FRONT_CARRIER_ACCEPTED__LOCAL_WALL_MANUFACTURING_DEVIATION":
        raise RuntimeError("front carrier adjudication is not accepted")

    context = front.prepare()
    App, Part = context["App"], context["Part"]
    toolkit = context["v1"].toolkit
    refs = context["construction"]["refs"]
    carrier = context["construction"]["carrier"]
    lens_values = contract["lens"]
    aperture = refs["aperture"]
    axis_n = refs["axis_n"]
    lens_outer = toolkit.radial_offset_loop(
        App, aperture, float(lens_values["outer_offset_from_visible_aperture_mm"]), axis_n
    )
    thickness = float(lens_values["thickness_mm"])
    front_depth = float(lens_values["front_depth_mm"])
    lens = toolkit.polygon_face(Part, lens_outer).extrude(axis_n * thickness)
    lens.translate(axis_n * front_depth)
    lens = lens.removeSplitter()
    toolkit.require_single_solid(lens, "translucent PETG eye glass")

    seat_inner = toolkit.radial_offset_loop(
        App, aperture, float(lens_values["front_carrier_rear_inner_offset_mm"]), axis_n
    )
    seat_face = toolkit.polygon_face(Part, lens_outer).cut(toolkit.polygon_face(Part, seat_inner))
    seat_area = 0.0 if seat_face.isNull() else float(seat_face.Area)
    aperture_face = toolkit.polygon_face(Part, aperture)
    lens_face = toolkit.polygon_face(Part, lens_outer)
    uncovered_aperture_area = float(aperture_face.cut(lens_face).Area)
    carrier_common = common_volume(carrier, lens)
    carrier_distance = float(carrier.distToShape(lens)[0])

    shell_intersections: dict[str, float] = {}
    minimum_shell_distance = math.inf
    for component in context["components"]:
        shape = component.shape
        if shape is None or shape.isNull():
            box = lens.BoundBox
            separated = (
                box.XMax < float(component.minimum_mm[0])
                or float(component.maximum_mm[0]) < box.XMin
                or box.YMax < float(component.minimum_mm[1])
                or float(component.maximum_mm[1]) < box.YMin
                or box.ZMax < float(component.minimum_mm[2])
                or float(component.maximum_mm[2]) < box.ZMin
            )
            if not separated:
                raise RuntimeError(f"unavailable shell owner overlaps lens AABB: {component.key}")
            continue
        volume = common_volume(lens, shape)
        if volume > EPSILON_MM3:
            shell_intersections[str(component.key)] = volume
        if aabb_near(lens, shape):
            minimum_shell_distance = min(minimum_shell_distance, float(lens.distToShape(shape)[0]))

    allowed = lens_values["allowed_thickness_mm"]
    overlap = (
        float(lens_values["outer_offset_from_visible_aperture_mm"])
        - float(lens_values["front_carrier_rear_inner_offset_mm"])
    )
    checks = {
        "front_adjudication_pinned": True,
        "lens_valid_closed_one_solid": bool(lens.isValid() and lens.isClosed() and len(lens.Solids) == 1),
        "lens_thickness_allowed": float(allowed[0]) <= thickness <= float(allowed[1]),
        "visible_aperture_fully_covered": uncovered_aperture_area <= 1.0e-6,
        "continuous_seat_overlap": overlap >= float(lens_values["minimum_continuous_seat_overlap_mm"]),
        "continuous_seat_area": seat_area >= float(lens_values["minimum_continuous_seat_area_mm2"]),
        "zero_front_penetration": carrier_common <= EPSILON_MM3,
        "front_contact": carrier_distance <= 1.0e-6,
        "zero_shell_penetration": not shell_intersections,
        "three_silicone_dabs": int(lens_values["silicone_dab_count"]) == 3,
        "no_cyanoacrylate": not bool(lens_values["cyanoacrylate_permitted"]),
        "no_screws": not bool(lens_values["screws_permitted"]),
        "front_non_wall_gates_unchanged": all(
            value for key, value in context["evaluation"]["checks"].items()
            if key != "protected_outward_1p2_wall_unchanged"
        ),
    }
    failed = [key for key, value in checks.items() if not value]
    evaluation = {
        "status": "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED" if not failed else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "failed_checks": failed,
        "measurements": {
            "lens_volume_mm3": float(lens.Volume),
            "lens_thickness_mm": thickness,
            "lens_outer_offset_mm": float(lens_values["outer_offset_from_visible_aperture_mm"]),
            "continuous_seat_overlap_mm": overlap,
            "continuous_seat_area_mm2": seat_area,
            "uncovered_visible_aperture_area_mm2": uncovered_aperture_area,
            "front_carrier_intersection_mm3": carrier_common,
            "front_carrier_distance_mm": carrier_distance,
            "shell_intersections_mm3": shell_intersections,
            "minimum_shell_distance_mm": minimum_shell_distance,
        },
    }
    context.update({
        "lens_contract": contract, "lens": lens, "lens_outer": lens_outer,
        "lens_evaluation": evaluation, "lens_seat_face": seat_face,
        "lens_generator_path": Path(__file__),
        "front_adjudication_path": adjudication_path,
        "front_validation_path": validation_path,
    })
    return context


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "review_id": context["lens_contract"]["review_id"],
        "authority": context["lens_contract"]["authority"],
        "mode": mode,
        **context["lens_evaluation"],
        "pins": {
            "generator_sha256": sha256_file(Path(__file__)),
            "contract_sha256": sha256_file(HERE / "contract.json"),
            "front_adjudication_sha256": sha256_file(context["front_adjudication_path"]),
            "front_review_validation_sha256": sha256_file(context["front_validation_path"]),
        },
        "elapsed_seconds": elapsed,
        "io_trace": {
            "front_source_opened_read_only": True,
            "front_source_saved": False,
            "canonical_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
            "review_fcstd_saved": mode == "single_review_artifact",
        },
    }


def create_review(context: dict[str, Any], output: Path) -> Path:
    App, Part = context["App"], context["Part"]
    doc = App.newDocument("RightEyeFrontCarrierTranslucentLensReviewV1")
    try:
        entries = [
            ("REFERENCE__SHELL_101", context["shell"], (0.72, 0.72, 0.74), 80),
            ("PRINT_CANDIDATE__CONFORMAL_FRONT_CARRIER", context["construction"]["carrier"], (0.14, 0.72, 0.34), 0),
            ("PRINT_CANDIDATE__TRANSLUCENT_EYE_GLASS", context["lens"], (0.40, 0.88, 0.95), 58),
            ("REFERENCE__CONTINUOUS_LENS_SEAT", context["lens_seat_face"], (0.95, 0.55, 0.10), 25),
        ]
        for name, shape, color, transparency in entries:
            obj = doc.addObject("Part::Feature", name)
            obj.Label = name.replace("__", " — ")
            obj.Shape = shape.copy()
            obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = context["lens_contract"]["authority"]
            if obj.ViewObject is not None:
                obj.ViewObject.ShapeColor = color
                obj.ViewObject.Transparency = transparency
        lens_obj = doc.getObject("PRINT_CANDIDATE__TRANSLUCENT_EYE_GLASS")
        lens_obj.addProperty("App::PropertyString", "Material", "Fabrication")
        lens_obj.Material = "Natural translucent PETG, 0.9 mm nominal"
        lens_obj.addProperty("App::PropertyString", "Retention", "Fabrication")
        lens_obj.Retention = "Three tiny clear neutral-cure silicone dabs; no CA; no screws"
        doc.recompute()
        path = output / context["lens_contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def tuple3(vector: Any) -> tuple[float, float, float]:
    return float(vector.x), float(vector.y), float(vector.z)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["v1"].toolkit
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    carrier = toolkit.shape_record(context["construction"]["carrier"], (44, 180, 92), deflection=0.4)
    lens = toolkit.shape_record(context["lens"], (102, 224, 242), deflection=0.35)
    seat = toolkit.shape_record(context["lens_seat_face"], (244, 140, 35), deflection=0.25)
    proposed = [shell, carrier, lens]
    axis_n = context["construction"]["refs"]["axis_n"]
    axis_u = context["construction"]["refs"]["axis_u"]
    fixed = {
        "front.png": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear.png": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "lens-seat.png": (tuple(-value for value in tuple3(axis_n)), tuple3(axis_u)),
        "side.png": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    }
    for name, (direction, up) in fixed.items():
        toolkit.render_side_by_side(output / name, [shell, carrier], proposed, direction, up)
    exploded = context["lens"].copy()
    exploded.translate(axis_n * 7.0)
    toolkit.render_side_by_side(
        output / "exploded.png", [shell, carrier],
        [shell, carrier, toolkit.shape_record(exploded, (102, 224, 242), deflection=0.35), seat],
        (0.0, -1.0, 0.0), (0.0, 0.0, 1.0),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = prepare()
    if context["lens_evaluation"]["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(public_report(context, "bounded_no_save_feasibility", time.monotonic() - started), indent=2, sort_keys=True))
        raise RuntimeError("translucent lens feasibility failed")
    if args.mode == "feasibility":
        if args.report is None:
            raise RuntimeError("--report is required for feasibility")
        if args.report.exists():
            raise RuntimeError(f"feasibility report exists: {args.report}")
        report = public_report(context, "bounded_no_save_feasibility", time.monotonic() - started)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(report["status"])
        return 0
    if args.feasibility_report is None or not args.feasibility_sha256:
        raise RuntimeError("review requires pinned feasibility report")
    if sha256_file(args.feasibility_report) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    output = context["root"] / context["lens_contract"]["output"]["directory"]
    if output.exists():
        raise RuntimeError(f"review output exists: {output}")
    output.mkdir(parents=True)
    fcstd = create_review(context, output)
    render_views(context, output)
    report = public_report(context, "single_review_artifact", time.monotonic() - started)
    report["review_fcstd"] = str(fcstd.relative_to(context["root"]))
    report["review_fcstd_sha256"] = sha256_file(fcstd)
    report["feasibility_report_sha256"] = args.feasibility_sha256
    validation_path = output / context["lens_contract"]["output"]["validation"]
    validation_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
