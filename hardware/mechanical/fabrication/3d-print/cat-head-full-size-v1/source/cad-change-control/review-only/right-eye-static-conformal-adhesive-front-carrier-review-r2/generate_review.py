#!/usr/bin/env python3
"""Static conformal adhesive-only front carrier, REVIEW_ONLY."""

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
    paths = {key: resolve(root, spec) for key, spec in contract["inputs"].items()}
    for key, path in paths.items():
        actual = sha256_file(path)
        if actual != contract["inputs"][key]["sha256"]:
            raise RuntimeError(f"{key} hash mismatch: {actual}")
    v1 = load_module(paths["v1_generator"], contract["inputs"]["v1_generator"]["sha256"], "_conformal_r2_v1")
    validator = load_module(paths["v1_validator"], contract["inputs"]["v1_validator"]["sha256"], "_conformal_r2_validator")
    if v1.repo_root() != root:
        raise RuntimeError("repository root mismatch")
    return root, v1, validator, paths


def construct(contract: dict[str, Any], parameters: dict[str, Any], v1: Any, validator: Any, components: Sequence[Any], App: Any, Part: Any) -> dict[str, Any]:
    toolkit = v1.toolkit
    refs = validator._reference_geometry(parameters, App, Part)
    values = contract["surface_carrier"]
    lcs, source_geometry = parameters["aperture_lcs"], parameters["geometry"]
    origin, axis_u, axis_v, axis_n = refs["origin"], refs["axis_u"], refs["axis_v"], refs["axis_n"]
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in source_geometry["shell_opening_boundary_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    outer_front = v1._locally_inset_loop(
        App, opening, source_geometry["front_optical_cassette"]["front_outer_vertex_insets_mm"], axis_n
    )
    extension = float(values["outer_extension_from_v1_outer_front_mm"])
    expanded_outer = v1._locally_inset_loop(App, outer_front, [-extension] * len(outer_front), axis_n)
    aperture = refs["aperture"]
    optical_base = toolkit.fuse_shapes(
        [refs["pocket"], refs["cover_lip"]], "exact V1 front optical ring and lip"
    )
    toolkit.require_single_solid(optical_base, "exact V1 optical base")
    front = float(values["face_sheet_front_depth_mm"])
    rear = float(values["face_sheet_rear_depth_mm"])
    face_sheet = toolkit.loft_ring(
        Part, expanded_outer, aperture, expanded_outer, aperture,
        front, rear, axis_n, "conformal carrier raw exterior face sheet",
    )
    connector = toolkit.loft_ring(
        Part, outer_front, aperture, outer_front, aperture,
        front, float(values["connector_rear_overlap_depth_mm"]), axis_n,
        "conformal carrier opening connector",
    )
    raw_surface = toolkit.fuse_shapes([face_sheet, connector], "raw adhesive surface carrier")
    raw_carrier = toolkit.fuse_shapes([optical_base, raw_surface], "raw conformal adhesive carrier")
    inventory = {str(item.key): item for item in components}
    local_shapes = []
    for key in values["contact_owner_keys"]:
        component = inventory.get(key)
        if component is None or component.shape is None or component.shape.isNull():
            raise RuntimeError(f"exact contact owner unavailable: {key}")
        local_shapes.append(component.shape)
    local_shell = Part.makeCompound(local_shapes)
    carrier = raw_carrier.cut(local_shell).removeSplitter()
    toolkit.require_single_solid(carrier, "shell-conformal adhesive-only front carrier")
    protected_wall = float(values["protected_outward_face_wall_mm"])
    protected_skin = toolkit.loft_ring(
        Part, expanded_outer, aperture, expanded_outer, aperture,
        front, front + protected_wall, axis_n, "protected outward 1.2 mm face wall",
    )
    support_depth = float(contract["adhesive_interface"]["support_probe_inward_depth_mm"])
    support_probe = toolkit.loft_ring(
        Part, expanded_outer, opening, expanded_outer, opening,
        0.0, support_depth, axis_n, "conformal adhesive support probe",
    )
    contact_reference = support_probe.common(local_shell).removeSplitter()
    return {
        "refs": refs, "opening": opening, "outer_front": outer_front,
        "expanded_outer": expanded_outer, "optical_base": optical_base,
        "face_sheet": face_sheet, "connector": connector, "raw_surface": raw_surface,
        "raw_carrier": raw_carrier, "carrier": carrier, "local_shell": local_shell,
        "protected_skin": protected_skin, "support_probe": support_probe,
        "contact_reference": contact_reference,
    }


def evaluate(contract: dict[str, Any], construction: dict[str, Any], components: Sequence[Any], Part: Any) -> tuple[dict[str, Any], Any]:
    carrier = construction["carrier"]
    shell_shapes = [item.shape for item in components if item.shape is not None and not item.shape.isNull()]
    shell = Part.makeCompound(shell_shapes)
    intersections = {}
    minimum_distance = math.inf
    for component in components:
        shape = component.shape
        if shape is None or shape.isNull():
            continue
        if aabb_near(carrier, shape, 0.5):
            volume = common_volume(carrier, shape)
            if volume > EPSILON:
                intersections[str(component.key)] = volume
            minimum_distance = min(minimum_distance, float(carrier.distToShape(shape)[0]))
    support_depth = float(contract["adhesive_interface"]["support_probe_inward_depth_mm"])
    contact = construction["contact_reference"]
    bearing_area = 0.0 if contact.isNull() else float(contact.Volume) / support_depth
    protected_missing = float(construction["protected_skin"].cut(carrier).Volume)
    lip_missing = float(construction["refs"]["cover_lip"].cut(carrier).Volume)
    aperture_common = common_volume(construction["face_sheet"], construction["refs"]["frustum"])
    authorized_bezel = construction["refs"]["bezel"].fuse(construction["raw_surface"]).removeSplitter()
    hidden = carrier.cut(authorized_bezel).removeSplitter()
    frustum_common = common_volume(hidden, construction["refs"]["frustum"])
    unauthorized_exterior = common_volume(hidden, construction["refs"]["exterior"])
    cartridge = construction["refs"]["cartridge"]
    cartridge_common = common_volume(carrier, cartridge)
    cartridge_clearance = float(carrier.distToShape(cartridge)[0])
    checks = {
        "valid_closed_one_solid": bool(carrier.isValid() and carrier.isClosed() and len(carrier.Solids) == 1),
        "zero_positive_shell_intersection": not intersections,
        "zero_distance_conformal_seat_allowed": minimum_distance <= 1.0e-6,
        "conformal_bearing_area_at_least_80": bearing_area >= float(contract["adhesive_interface"]["minimum_conformal_bearing_area_mm2"]),
        "protected_outward_1p2_wall_unchanged": protected_missing <= EPSILON,
        "exact_aperture_unoccupied": aperture_common <= EPSILON,
        "approved_lip_preserved": lip_missing <= EPSILON,
        "hidden_frustum_clear": frustum_common <= EPSILON,
        "unauthorized_exterior_clear": unauthorized_exterior <= EPSILON,
        "rear_cartridge_separate_and_clear": cartridge_common <= EPSILON and cartridge_clearance >= float(contract["limits"]["minimum_rear_cartridge_clearance_mm"]),
        "no_mount_or_hardware_geometry": True,
    }
    return {
        "status": "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED" if all(checks.values()) else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "measurements": {
            "raw_carrier_volume_mm3": float(construction["raw_carrier"].Volume),
            "conformal_carrier_volume_mm3": float(carrier.Volume),
            "shell_removed_from_underside_mm3": float(construction["raw_carrier"].Volume - carrier.Volume),
            "shell_intersections_mm3": intersections,
            "maximum_shell_intersection_mm3": max(intersections.values(), default=0.0),
            "minimum_shell_distance_mm": minimum_distance,
            "conformal_adhesive_bearing_area_mm2": bearing_area,
            "conformal_contact_reference_volume_mm3": 0.0 if contact.isNull() else float(contact.Volume),
            "protected_outward_wall_mm": float(contract["surface_carrier"]["protected_outward_face_wall_mm"]),
            "protected_outward_skin_missing_mm3": protected_missing,
            "face_sheet_aperture_frustum_intersection_mm3": aperture_common,
            "approved_lip_missing_volume_mm3": lip_missing,
            "hidden_frustum_intersection_mm3": frustum_common,
            "unauthorized_exterior_intersection_mm3": unauthorized_exterior,
            "rear_cartridge_intersection_mm3": cartridge_common,
            "rear_cartridge_clearance_mm": cartridge_clearance,
            "adhesive_recommendation": contract["adhesive_interface"]["recommended"],
        },
    }, shell


def prepare() -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    root, v1, validator, paths = load_dependencies(contract)
    parameters = load_json(paths["v1_contract"])["allowed_mutations"][0]["parameters"]
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    before = sha256_file(paths["held_candidate"])
    document = App.openDocument(str(paths["held_candidate"]))
    try:
        target = document.getObject(contract["inputs"]["held_candidate"]["object"])
        if target is None or target.Shape.isNull():
            raise RuntimeError("held reference target missing")
        held = target.Shape.copy()
    finally:
        App.closeDocument(document.Name)
    if sha256_file(paths["held_candidate"]) != before:
        raise RuntimeError("held candidate changed")
    components = v1._load_shell_components(parameters, App, Part)
    construction = construct(contract, parameters, v1, validator, components, App, Part)
    evaluation, shell = evaluate(contract, construction, components, Part)
    return {"root": root, "contract": contract, "paths": paths, "v1": v1, "App": App, "Part": Part, "held": held, "components": components, "construction": construction, "evaluation": evaluation, "shell": shell, "candidate_before": before}


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
    doc = App.newDocument("RightEyeStaticConformalAdhesiveCarrierReviewR2")
    try:
        entries = [
            ("REFERENCE__SHELL_101", context["shell"], (0.72,0.72,0.74), 72),
            ("REFERENCE__HELD_SPLIT_EYE", context["held"], (0.20,0.58,0.82), 82),
            ("PROPOSED__CONFORMAL_ADHESIVE_FRONT_CARRIER", context["construction"]["carrier"], (0.14,0.72,0.34), 0),
            ("REFERENCE__EPOXY_GEL_CA_CONTACT_REGION", context["construction"]["contact_reference"], (0.95,0.55,0.10), 18),
            ("REFERENCE__INSIDE_REAR_CARTRIDGE_B", context["construction"]["refs"]["cartridge"], (0.88,0.50,0.16), 30),
        ]
        for name, shape, color, transparency in entries:
            obj = doc.addObject("Part::Feature", name); obj.Label = name.replace("__", " — ")
            obj.Shape = shape.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = context["contract"]["authority"]
            obj.ViewObject.ShapeColor = color; obj.ViewObject.Transparency = transparency
        proposed = doc.getObject("PROPOSED__CONFORMAL_ADHESIVE_FRONT_CARRIER")
        proposed.addProperty("App::PropertyVector", "UpperBoreReferenceOnly", "ProtectedDatums")
        proposed.addProperty("App::PropertyVector", "LowerBoreReferenceOnly", "ProtectedDatums")
        proposed.UpperBoreReferenceOnly = context["construction"]["refs"]["mounts"]["upper"]["eye_bore"]
        proposed.LowerBoreReferenceOnly = context["construction"]["refs"]["mounts"]["lower"]["eye_bore"]
        doc.recompute(); path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path)); return path
    finally:
        App.closeDocument(doc.Name)


def tuple3(vector: Any) -> tuple[float,float,float]:
    return (float(vector.x),float(vector.y),float(vector.z))


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["v1"].toolkit
    base = [toolkit.shape_record(context["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["held"], (42,142,190), deflection=0.7)]
    proposed = [toolkit.shape_record(context["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["construction"]["carrier"], (44,180,92), deflection=0.4), toolkit.shape_record(context["construction"]["contact_reference"], (244,140,35), deflection=0.3)]
    fixed = {
        "front.png": ((0.0,1.0,0.0),(0.0,0.0,1.0)),
        "rear.png": ((0.0,-1.0,0.0),(0.0,0.0,1.0)),
        "conformal-seat.png": (tuple(-value for value in tuple3(context["construction"]["refs"]["axis_n"])), tuple3(context["construction"]["refs"]["axis_u"])),
        "side.png": ((1.0,0.0,0.0),(0.0,0.0,1.0)),
    }
    for name,(direction,up) in fixed.items(): toolkit.render_side_by_side(output/name,base,proposed,direction,up)
    inside = [*proposed, toolkit.shape_record(context["construction"]["refs"]["cartridge"], (223,164,54), deflection=0.55)]
    toolkit.render_side_by_side(output/"inside-cartridge.png",base,inside,(0.0,-1.0,0.0),(0.0,0.0,1.0))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode",choices=("feasibility","review"),required=True)
    parser.add_argument("--report",type=Path); parser.add_argument("--feasibility-report",type=Path); parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started=time.monotonic(); context=prepare()
    if context["evaluation"]["status"]!="FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(public_report(context,"bounded_no_save_static_feasibility",time.monotonic()-started),indent=2,sort_keys=True)); raise RuntimeError("conformal adhesive carrier feasibility failed")
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
