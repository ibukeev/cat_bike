#!/usr/bin/env python3
"""Static-only REVIEW_ONLY surface carrier with a 0.20 mm adhesive seat."""

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
EPSILON = 1.0e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def load_module(path: Path, digest: str, name: str) -> Any:
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"pinned module changed: {actual} != {digest}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve(root: Path, spec: dict[str, Any]) -> Path:
    path = Path(str(spec["path"]))
    return path if path.is_absolute() else root / path


def aabb_near(first: Any, second: Any, margin: float = 0.0) -> bool:
    a, b = first.BoundBox, second.BoundBox
    return not (
        a.XMax + margin < b.XMin or b.XMax + margin < a.XMin
        or a.YMax + margin < b.YMin or b.YMax + margin < a.YMin
        or a.ZMax + margin < b.ZMin or b.ZMax + margin < a.ZMin
    )


def common_volume(first: Any, second: Any) -> float:
    if not aabb_near(first, second):
        return 0.0
    common = first.common(second)
    return 0.0 if common.isNull() else float(common.Volume)


def load_dependencies(contract: dict[str, Any]) -> tuple[Path, Any, Any, dict[str, Path]]:
    root = HERE.parents[8]
    paths = {key: resolve(root, value) for key, value in contract["inputs"].items()}
    for key, path in paths.items():
        actual = sha256_file(path)
        if actual != contract["inputs"][key]["sha256"]:
            raise RuntimeError(f"{key} hash mismatch: {actual}")
    v1 = load_module(paths["v1_generator"], contract["inputs"]["v1_generator"]["sha256"], "_static_vhb_v1")
    validator = load_module(paths["v1_validator"], contract["inputs"]["v1_validator"]["sha256"], "_static_vhb_validator")
    if v1.repo_root() != root:
        raise RuntimeError("repository root mismatch")
    return root, v1, validator, paths


def construct_exact_front_base(parameters: dict[str, Any], v1: Any, validator: Any, App: Any, Part: Any) -> dict[str, Any]:
    refs = validator._reference_geometry(parameters, App, Part)
    toolkit = v1.toolkit
    lcs, geometry = parameters["aperture_lcs"], parameters["geometry"]
    origin, axis_u, axis_v, axis_n = refs["origin"], refs["axis_u"], refs["axis_v"], refs["axis_n"]
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in geometry["shell_opening_boundary_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    outer_front = v1._locally_inset_loop(
        App, opening, geometry["front_optical_cassette"]["front_outer_vertex_insets_mm"], axis_n
    )
    outer_rear = v1._locally_inset_loop(
        App, opening, geometry["front_optical_cassette"]["rear_outer_vertex_insets_mm"], axis_n
    )
    upper = refs["mounts"]["upper"]
    ligament, ligament_record = v1._explicit_mount_ligament(
        "upper", upper, outer_rear, geometry["head_mount"],
        origin, axis_u, axis_v, axis_n, App, Part,
    )
    base = toolkit.fuse_shapes(
        [refs["pocket"], refs["cover_lip"], upper["drilled"], ligament],
        "static front carrier exact V1 base",
    ).cut(upper["bore_cutter_solid"]).removeSplitter()
    toolkit.require_single_solid(base, "static front carrier exact V1 base")
    return {
        "refs": refs, "opening": opening, "outer_front": outer_front,
        "outer_rear": outer_rear, "base": base, "upper_ligament": ligament,
        "upper_ligament_record": ligament_record,
    }


def construct_surface_carrier(contract: dict[str, Any], geometry: dict[str, Any], v1: Any, Part: Any) -> dict[str, Any]:
    values = contract["surface_carrier"]
    adhesive_values = contract["adhesive_interface"]
    axis_n = geometry["refs"]["axis_n"]
    extension = float(values["outer_extension_from_v1_outer_front_mm"])
    expanded_outer = v1._locally_inset_loop(
        geometry["refs"]["App"] if "App" in geometry["refs"] else geometry["base"].Placement.Base,
        geometry["outer_front"], [-extension] * len(geometry["outer_front"]), axis_n,
    )
    # _locally_inset_loop only needs App.Vector construction through its passed App;
    # callers replace the sentinel above before invoking this function.
    raise AssertionError("construct_surface_carrier requires explicit App")


def build_surface(contract: dict[str, Any], geometry: dict[str, Any], v1: Any, App: Any, Part: Any) -> dict[str, Any]:
    values = contract["surface_carrier"]
    adhesive_values = contract["adhesive_interface"]
    axis_n = geometry["refs"]["axis_n"]
    extension = float(values["outer_extension_from_v1_outer_front_mm"])
    expanded_outer = v1._locally_inset_loop(
        App, geometry["outer_front"], [-extension] * len(geometry["outer_front"]), axis_n
    )
    aperture = geometry["refs"]["aperture"]
    face_sheet = v1.toolkit.loft_ring(
        Part, expanded_outer, aperture, expanded_outer, aperture,
        float(values["face_sheet_front_depth_mm"]),
        float(values["face_sheet_rear_depth_mm"]), axis_n,
        "static exterior 1.2 mm face sheet",
    )
    connector = v1.toolkit.loft_ring(
        Part, geometry["outer_front"], aperture,
        geometry["outer_front"], aperture,
        float(values["face_sheet_front_depth_mm"]),
        float(values["connector_rear_overlap_depth_mm"]), axis_n,
        "static carrier opening-side connector",
    )
    surface = v1.toolkit.fuse_shapes([face_sheet, connector], "static stepped surface carrier")
    carrier = v1.toolkit.fuse_shapes([geometry["base"], surface], "static VHB front carrier").removeSplitter()
    v1.toolkit.require_single_solid(face_sheet, "static face sheet")
    v1.toolkit.require_single_solid(carrier, "static VHB front carrier")
    adhesive = v1.toolkit.loft_ring(
        Part, expanded_outer, geometry["opening"], expanded_outer, geometry["opening"],
        float(adhesive_values["front_depth_mm"]), float(adhesive_values["rear_depth_mm"]),
        axis_n, "0.20 mm VHB bedding interface",
    )
    support_probe = v1.toolkit.loft_ring(
        Part, expanded_outer, geometry["opening"], expanded_outer, geometry["opening"],
        0.0, float(adhesive_values["support_probe_inward_depth_mm"]),
        axis_n, "adhesive shell support probe",
    )
    return {
        "expanded_outer": expanded_outer, "face_sheet": face_sheet,
        "connector": connector, "surface": surface, "carrier": carrier,
        "adhesive": adhesive, "support_probe": support_probe,
    }


def evaluate(contract: dict[str, Any], geometry: dict[str, Any], surface: dict[str, Any], components: Sequence[Any], v1: Any, Part: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    carrier = surface["carrier"]
    shell_shapes = [item.shape for item in components if item.shape is not None and not item.shape.isNull()]
    shell = Part.makeCompound(shell_shapes)
    intersections = {}
    minimum_shell_distance = math.inf
    for component in components:
        shape = component.shape
        if shape is None or shape.isNull():
            continue
        if aabb_near(carrier, shape, 0.5):
            volume = common_volume(carrier, shape)
            if volume > EPSILON:
                intersections[str(component.key)] = volume
            minimum_shell_distance = min(minimum_shell_distance, float(carrier.distToShape(shape)[0]))
    adhesive_thickness = float(contract["adhesive_interface"]["thickness_mm"])
    adhesive_footprint_area = float(surface["adhesive"].Volume) / adhesive_thickness
    probe_depth = float(contract["adhesive_interface"]["support_probe_inward_depth_mm"])
    support_common = surface["support_probe"].common(shell)
    supported_area = (0.0 if support_common.isNull() else float(support_common.Volume) / probe_depth)
    conformal_adhesive = surface["adhesive"].cut(shell).removeSplitter()

    authorized_bezel = v1.toolkit.fuse_shapes(
        [geometry["refs"]["bezel"], surface["surface"]], "authorized static bezel envelope"
    )
    hidden = carrier.cut(authorized_bezel).removeSplitter()
    frustum_common = common_volume(hidden, geometry["refs"]["frustum"])
    unauthorized_exterior = common_volume(hidden, geometry["refs"]["exterior"])
    lip_missing = float(geometry["refs"]["cover_lip"].cut(carrier).Volume)
    aperture_common = common_volume(surface["face_sheet"], geometry["refs"]["frustum"])

    hardware = v1.toolkit.hardware_shapes(contract["_parameters"], geometry["refs"], Part)["upper"]
    hardware_obstruction = {}
    for name, shape in hardware.items():
        target_common = common_volume(carrier, shape)
        shell_common = max((common_volume(shape, shell_shape) for shell_shape in shell_shapes if aabb_near(shape, shell_shape)), default=0.0)
        hardware_obstruction[name] = {"carrier_mm3": target_common, "shell_mm3": shell_common}
    maximum_hardware = max(
        (value for record in hardware_obstruction.values() for value in record.values()), default=0.0
    )
    upper_bore = common_volume(surface["surface"], geometry["refs"]["mounts"]["upper"]["bore_cutter_solid"])
    cartridge = geometry["refs"]["cartridge"]
    cartridge_common = common_volume(carrier, cartridge)
    cartridge_clearance = float(carrier.distToShape(cartridge)[0])
    wall = float(contract["surface_carrier"]["face_sheet_rear_depth_mm"]) - float(contract["surface_carrier"]["face_sheet_front_depth_mm"])
    checks = {
        "valid_closed_one_solid": bool(carrier.isValid() and carrier.isClosed() and len(carrier.Solids) == 1),
        "exact_aperture_unoccupied": aperture_common <= EPSILON,
        "approved_cover_lip_preserved": lip_missing <= EPSILON,
        "zero_positive_shell_intersection": not intersections,
        "adhesive_bearing_area_at_least_150": supported_area >= float(contract["adhesive_interface"]["minimum_bearing_area_mm2"]),
        "new_wall_at_least_1p2": wall >= float(contract["surface_carrier"]["minimum_wall_mm"]),
        "hidden_frustum_clear": frustum_common <= EPSILON,
        "unauthorized_exterior_clear": unauthorized_exterior <= EPSILON,
        "upper_hardware_corridor_clear": maximum_hardware <= float(contract["limits"]["maximum_upper_hardware_obstruction_mm3"]),
        "upper_bore_unfilled": upper_bore <= float(contract["limits"]["maximum_mount_bore_fill_mm3"]),
        "rear_cartridge_separate_and_clear": cartridge_common <= EPSILON and cartridge_clearance >= float(contract["limits"]["minimum_rear_cartridge_clearance_mm"]),
    }
    evaluation = {
        "status": "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED" if all(checks.values()) else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "measurements": {
            "carrier_volume_mm3": float(carrier.Volume), "carrier_area_mm2": float(carrier.Area),
            "new_face_sheet_wall_mm": wall, "minimum_shell_distance_mm": minimum_shell_distance,
            "shell_intersections_mm3": intersections,
            "maximum_shell_intersection_mm3": max(intersections.values(), default=0.0),
            "adhesive_footprint_area_mm2": adhesive_footprint_area,
            "shell_supported_bearing_area_mm2": supported_area,
            "adhesive_reference_volume_mm3": float(conformal_adhesive.Volume),
            "hidden_frustum_intersection_mm3": frustum_common,
            "unauthorized_exterior_intersection_mm3": unauthorized_exterior,
            "face_sheet_aperture_frustum_intersection_mm3": aperture_common,
            "approved_lip_missing_volume_mm3": lip_missing,
            "upper_hardware_obstructions_mm3": hardware_obstruction,
            "maximum_upper_hardware_obstruction_mm3": maximum_hardware,
            "upper_bore_additive_fill_mm3": upper_bore,
            "rear_cartridge_intersection_mm3": cartridge_common,
            "rear_cartridge_clearance_mm": cartridge_clearance,
        },
    }
    references = {"shell": shell, "adhesive": conformal_adhesive, "hardware": hardware}
    return evaluation, references


def prepare() -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    root, v1, validator, paths = load_dependencies(contract)
    parameters = load_json(paths["v1_contract"])["allowed_mutations"][0]["parameters"]
    contract["_parameters"] = parameters
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    before = sha256_file(paths["held_candidate"])
    document = App.openDocument(str(paths["held_candidate"]))
    try:
        target = document.getObject(contract["inputs"]["held_candidate"]["object"])
        if target is None or target.Shape.isNull():
            raise RuntimeError("held source target missing")
        held = target.Shape.copy()
    finally:
        App.closeDocument(document.Name)
    if sha256_file(paths["held_candidate"]) != before:
        raise RuntimeError("held candidate changed")
    geometry = construct_exact_front_base(parameters, v1, validator, App, Part)
    surface = build_surface(contract, geometry, v1, App, Part)
    components = v1._load_shell_components(parameters, App, Part)
    evaluation, references = evaluate(contract, geometry, surface, components, v1, Part)
    return {"root": root, "contract": contract, "paths": paths, "v1": v1, "App": App, "Part": Part, "held": held, "geometry": geometry, "surface": surface, "components": components, "evaluation": evaluation, "references": references, "candidate_before": before}


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    return {
        "schema_version": 1, "review_id": context["contract"]["review_id"],
        "authority": context["contract"]["authority"], "mode": mode,
        "pins": {"tool": sha256_file(Path(__file__)), "contract": sha256_file(HERE / "contract.json"), **{key: sha256_file(path) for key, path in context["paths"].items()}},
        **context["evaluation"], "elapsed_seconds": elapsed,
        "io_trace": {"held_candidate_opened_read_only": True, "held_candidate_saved": False, "canonical_saved": False, "geometry_export_created": False, "production_output_created": False, "review_fcstd_saved": mode == "single_review_artifact"},
    }


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeStaticVHBFrontCarrierReviewR1")
    try:
        entries = [
            ("REFERENCE__SHELL_101", context["references"]["shell"], (0.72,0.72,0.74), 72),
            ("REFERENCE__HELD_SPLIT_EYE", context["held"], (0.20,0.58,0.82), 80),
            ("PROPOSED__STATIC_VHB_FRONT_CARRIER", context["surface"]["carrier"], (0.14,0.72,0.34), 0),
            ("REFERENCE__VHB_0P20_BEDDING", context["references"]["adhesive"], (0.95,0.64,0.12), 15),
            ("REFERENCE__INSIDE_REAR_CARTRIDGE_B", context["geometry"]["refs"]["cartridge"], (0.88,0.50,0.16), 30),
        ]
        for name, shape, color, transparency in entries:
            obj = doc.addObject("Part::Feature", name); obj.Label = name.replace("__", " — ")
            obj.Shape = shape.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = context["contract"]["authority"]
            obj.ViewObject.ShapeColor = color; obj.ViewObject.Transparency = transparency
        for name, shape in context["references"]["hardware"].items():
            obj = doc.addObject("Part::Feature", f"REFERENCE__UPPER_HARDWARE_{name.upper()}")
            obj.Shape = shape.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = "REFERENCE_ONLY__UPPER_SERVICE_CORRIDOR"
            obj.ViewObject.ShapeColor = (0.25,0.55,0.92); obj.ViewObject.Transparency = 25
        proposed = doc.getObject("PROPOSED__STATIC_VHB_FRONT_CARRIER")
        proposed.addProperty("App::PropertyVector", "UpperEyeBoreCenter", "ProtectedDatums")
        proposed.addProperty("App::PropertyVector", "UpperSignedBoreAxis", "ProtectedDatums")
        proposed.UpperEyeBoreCenter = context["geometry"]["refs"]["mounts"]["upper"]["eye_bore"]
        proposed.UpperSignedBoreAxis = context["geometry"]["refs"]["mounts"]["upper"]["bore_axis_vector"]
        doc.recompute(); path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path)); return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["v1"].toolkit
    base = [toolkit.shape_record(context["references"]["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["held"], (42,142,190), deflection=0.7)]
    proposed = [toolkit.shape_record(context["references"]["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["surface"]["carrier"], (44,180,92), deflection=0.4), toolkit.shape_record(context["references"]["adhesive"], (244,166,40), deflection=0.35)]
    fixed = {
        "front.png": ((0.0,1.0,0.0),(0.0,0.0,1.0)),
        "rear.png": ((0.0,-1.0,0.0),(0.0,0.0,1.0)),
        "adhesive-seat.png": (tuple(-value for value in tuple3(context["geometry"]["refs"]["axis_n"])), tuple3(context["geometry"]["refs"]["axis_u"])),
        "side.png": ((1.0,0.0,0.0),(0.0,0.0,1.0)),
    }
    for name,(direction,up) in fixed.items(): toolkit.render_side_by_side(output/name,base,proposed,direction,up)
    inside = [*proposed, toolkit.shape_record(context["geometry"]["refs"]["cartridge"], (223,164,54), deflection=0.55)]
    toolkit.render_side_by_side(output/"inside-cartridge.png",base,inside,(0.0,-1.0,0.0),(0.0,0.0,1.0))


def tuple3(vector: Any) -> tuple[float,float,float]:
    return (float(vector.x),float(vector.y),float(vector.z))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode",choices=("feasibility","review"),required=True)
    parser.add_argument("--report",type=Path); parser.add_argument("--feasibility-report",type=Path); parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started=time.monotonic(); context=prepare()
    if context["evaluation"]["status"]!="FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(public_report(context,"bounded_no_save_static_feasibility",time.monotonic()-started),indent=2,sort_keys=True)); raise RuntimeError("static VHB carrier feasibility failed")
    if args.mode=="feasibility":
        if args.report is None or args.report.exists(): raise RuntimeError("fresh --report required")
        report=public_report(context,"bounded_no_save_static_feasibility",time.monotonic()-started); args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(report["status"]); return 0
    if args.feasibility_report is None or not args.feasibility_sha256 or sha256_file(args.feasibility_report)!=args.feasibility_sha256: raise RuntimeError("review requires exact pinned feasibility report")
    output=context["root"]/context["contract"]["output"]["directory"]
    if output.exists(): raise RuntimeError(f"review output exists: {output}")
    output.mkdir(parents=True); fcstd=create_review(context,output); render_views(context,output)
    report=public_report(context,"single_review_artifact",time.monotonic()-started); report["review_fcstd"]=str(fcstd.relative_to(context["root"])); report["review_fcstd_sha256"]=sha256_file(fcstd); report["feasibility_report_sha256"]=args.feasibility_sha256
    (output/context["contract"]["output"]["validation"]).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print("REVIEW_ONLY_ARTIFACT_CREATED__AWAIT_HUMAN_REVIEW"); return 0


if __name__=="__main__": raise SystemExit(main())
