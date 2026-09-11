#!/usr/bin/env python3
"""Build the additive, review-only structural-root repair for the right eye.

The exact user-edited final carrier is the immutable base.  This tool adds a
continuous hidden front-frame spine and a continuous backing collar that
overlap the approved front frame, transition shelf, and perpendicular walls by
positive volume.  It never edits the lens, rear plate, manual bottom flange,
visible aperture, LED layout, wire route, or head shell.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
EPSILON_MM3 = 1.0e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    return (PROJECT_ROOT / value).resolve()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-eye-carrier-structural-root-repair-v1":
        raise RuntimeError("unexpected contract schema")
    return contract


def verify_inputs(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(str(item["path"]))
        if not path.is_file():
            raise RuntimeError(f"missing input {key}: {path}")
        actual = sha256(path)
        if actual != str(item["sha256"]):
            raise RuntimeError(f"input hash mismatch for {key}: {actual}")
        records[key] = {"path": str(item["path"]), "sha256": actual}
    gcode = Path(str(contract["user_evidence"]["printed_gcode_path"])).resolve()
    actual = sha256(gcode)
    if actual != str(contract["user_evidence"]["printed_gcode_sha256"]):
        raise RuntimeError(f"printed G-code hash mismatch: {actual}")
    records["printed_gcode"] = {"path": str(gcode), "sha256": actual}
    return records


def common_volume(first: Any, second: Any) -> float:
    common = first.common(second)
    return 0.0 if common.isNull() else float(common.Volume)


def shape_record(shape: Any) -> dict[str, Any]:
    box = shape.BoundBox
    return {
        "shape_type": str(shape.ShapeType),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "area_mm2": float(shape.Area),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "deep_check_messages": [str(item) for item in (shape.check(True) or [])],
        "bbox_minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "bbox_maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def load_final_shapes(contract: dict[str, Any], App: Any) -> dict[str, Any]:
    source = project_path(str(contract["inputs"]["failed_final_right_fcstd"]["path"]))
    document = App.openDocument(str(source))
    try:
        result: dict[str, Any] = {}
        for key, object_name in contract["source_objects"].items():
            obj = document.getObject(str(object_name))
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"missing source object: {object_name}")
            result[key] = obj.Shape.copy()
        return result
    finally:
        App.closeDocument(document.Name)


def prepare() -> dict[str, Any]:
    contract = load_contract()
    inputs = verify_inputs(contract)
    import FreeCAD as App  # type: ignore
    import MeshPart  # type: ignore
    import Part  # type: ignore

    v7_path = project_path(str(contract["inputs"]["approved_v7_generator"]["path"]))
    v7 = load_module(v7_path, "_pinned_v7_for_structural_root_repair")
    context = v7.prepare()
    if context["evaluation"]["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        raise RuntimeError("pinned V7 no longer passes its approved gates")
    mesh_path = project_path(str(contract["inputs"]["mesh_topology_checker"]["path"]))
    mesh_checker = load_module(mesh_path, "_pinned_eye_mesh_topology_checker")
    final_shapes = load_final_shapes(contract, App)
    context.update({
        "repair_contract": contract,
        "repair_inputs": inputs,
        "repair_v7": v7,
        "mesh_checker": mesh_checker,
        "final_shapes": final_shapes,
        "App": App,
        "Part": Part,
        "MeshPart": MeshPart,
    })
    return context


def construct(context: dict[str, Any]) -> None:
    contract = context["repair_contract"]
    values = contract["repair_dimensions_mm"]
    toolkit = context["toolkit"]
    Part = context["Part"]
    App = context["App"]
    axis_n = context["axis_n"]
    v3 = context["v3_module"]

    backing_outer = v3.polygon_inset_loop(
        App,
        context["aperture"],
        -float(values["structural_backing_outer_offset_from_aperture"]),
        context["origin"],
        context["axis_u"],
        context["axis_v"],
        axis_n,
    )
    raw_front_frame_spine = toolkit.ring_prism(
        Part,
        context["rim_outer"],
        context["lens_outer"],
        float(values["front_frame_spine_front_depth"]),
        float(values["front_frame_spine_rear_depth"]),
        axis_n,
        "continuous hidden front-frame structural spine",
    )
    raw_structural_backing = toolkit.ring_prism(
        Part,
        backing_outer,
        context["box_inner"],
        float(values["structural_backing_front_depth"]),
        float(values["structural_backing_rear_depth"]),
        axis_n,
        "continuous hidden frame-to-wall backing collar",
    )
    exclusion_shapes = [owner for _, owner in context["shell_records"]]
    exclusion_shapes.extend(list(context["side_screw_references"].Solids))

    def trim_new_material(shape: Any) -> Any:
        trimmed = shape.copy()
        for occupied in exclusion_shapes:
            if context["v3_module"].aabb_near(trimmed, occupied, 0.0):
                trimmed = trimmed.cut(occupied).removeSplitter()
                if trimmed.isNull():
                    raise RuntimeError("exact occupied-volume trim consumed structural repair")
        return trimmed

    front_frame_spine = trim_new_material(raw_front_frame_spine)
    structural_backing = trim_new_material(raw_structural_backing)
    reinforcement = toolkit.fuse_shapes(
        [front_frame_spine, structural_backing],
        "continuous eye structural root reinforcement",
    ).removeSplitter()
    final_carrier = context["final_shapes"]["carrier"]
    candidate = toolkit.fuse_shapes(
        [final_carrier, reinforcement],
        "failed carrier plus continuous structural root repair",
    ).removeSplitter()
    toolkit.require_single_solid(candidate, "structurally repaired right-eye carrier")
    added = candidate.cut(final_carrier).removeSplitter()
    context.update({
        "backing_outer": backing_outer,
        "raw_front_frame_spine": raw_front_frame_spine,
        "raw_structural_backing": raw_structural_backing,
        "front_frame_spine": front_frame_spine,
        "structural_backing": structural_backing,
        "reinforcement": reinforcement,
        "candidate": candidate,
        "added": added,
    })


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["repair_contract"]
    gates = contract["future_release_gates"]
    values = contract["repair_dimensions_mm"]
    final = context["final_shapes"]["carrier"]
    lens = context["final_shapes"]["lens"]
    rear = context["final_shapes"]["rear_plate"]
    candidate = context["candidate"]
    added = context["added"]
    reinforcement = context["reinforcement"]
    v7 = context["repair_v7"]
    Part = context["Part"]

    frame_root = common_volume(context["front_frame_spine"], context["lens_surround"])
    spine_backing = common_volume(context["front_frame_spine"], context["structural_backing"])
    wall_root = common_volume(context["structural_backing"], context["walls"])
    transition_root = common_volume(
        context["structural_backing"], context["wall_transition_shelf"]
    )
    seat_root = common_volume(context["structural_backing"], context["lens_seat"])
    source_removed = common_volume(final.cut(candidate), final)
    added_volume = float(added.Volume) if not added.isNull() else 0.0
    volume_balance = abs(float(candidate.Volume) - float(final.Volume) - added_volume)
    shell_common = float(v7.shell_common(context, added))
    lens_common = common_volume(added, lens)
    rear_common = common_volume(added, rear)
    side_screw_common = common_volume(added, context["side_screw_references"])
    rear_screw_common = common_volume(added, context["rear_screw_references"])
    led_common = sum(common_volume(added, shape) for shape in context["led_shapes"])
    wire_common = common_volume(added, context["wire_corridor"])
    manual_additions = final.cut(context["carrier"]).removeSplitter()
    manual_missing = common_volume(manual_additions.cut(candidate), manual_additions)

    candidate_record = shape_record(candidate)
    source_record = shape_record(final)
    mesh = context["MeshPart"].meshFromShape(
        Shape=candidate,
        LinearDeflection=float(values["mesh_linear_deflection"]),
        AngularDeflection=float(values["mesh_angular_deflection"]),
        Relative=False,
    )
    mesh_record = context["mesh_checker"].mesh_topology(mesh)
    structural_depth = (
        float(values["structural_backing_rear_depth"])
        - float(values["structural_backing_front_depth"])
    )
    checks = {
        "candidate_is_valid_closed_one_solid": (
            candidate_record["valid"]
            and candidate_record["closed"]
            and candidate_record["solid_count"] == 1
        ),
        "candidate_adds_no_deep_occt_defects": (
            len(candidate_record["deep_check_messages"])
            <= len(source_record["deep_check_messages"])
        ),
        "failed_carrier_and_manual_flange_are_additively_preserved": (
            source_removed <= float(gates["zero_removed_volume_from_failed_carrier_mm3"])
            and manual_missing <= float(gates["zero_removed_volume_from_failed_carrier_mm3"])
        ),
        "repair_adds_positive_structural_material": added_volume > 1.0,
        "candidate_volume_balance_is_exact": volume_balance <= 1.0e-5,
        "front_frame_has_positive_volume_root": (
            frame_root >= float(gates["minimum_front_frame_root_positive_overlap_mm3"])
        ),
        "front_spine_and_backing_have_positive_volume_overlap": (
            spine_backing >= float(gates["minimum_spine_to_backing_positive_overlap_mm3"])
        ),
        "perpendicular_walls_have_positive_volume_root": (
            wall_root >= float(gates["minimum_wall_root_positive_overlap_mm3"])
        ),
        "transition_shelf_has_positive_volume_root": (
            transition_root >= float(gates["minimum_backing_to_transition_positive_overlap_mm3"])
        ),
        "structural_root_depth_is_at_least_1p6_mm": (
            structural_depth + 1.0e-9
            >= float(gates["minimum_continuous_structural_root_depth_mm"])
        ),
        "repair_clears_exact_lens": lens_common <= float(gates["zero_lens_intersection_mm3"]),
        "repair_clears_exact_rear_plate": rear_common <= float(gates["zero_rear_plate_intersection_mm3"]),
        "repair_adds_no_head_shell_intersection": shell_common <= float(gates["zero_new_shell_intersection_mm3"]),
        "repair_clears_all_existing_hardware": max(
            side_screw_common, rear_screw_common, led_common, wire_common
        ) <= EPSILON_MM3,
        "candidate_mesh_is_one_closed_manifold_component": (
            int(mesh_record["connected_components"]) == 1
            and int(mesh_record["boundary_edges"]) == 0
            and int(mesh_record["nonmanifold_edges"]) == 0
            and int(mesh_record["degenerate_facets"]) == 0
            and int(mesh_record["duplicate_facets"]) == 0
            and int(mesh_record.get("self_intersection_count") or 0) == 0
            and bool(mesh_record["outward_normals"])
        ),
    }
    failed = [key for key, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-right-eye-carrier-structural-root-repair-validation-v1",
        "status": "FEASIBILITY_PASS__RIGHT_REVIEW_ALLOWED" if not failed else "FEASIBILITY_FAIL__NO_REVIEW_OUTPUT",
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "measurements": {
            "source_carrier": source_record,
            "candidate_carrier": candidate_record,
            "added_structural_material_mm3": added_volume,
            "volume_balance_error_mm3": volume_balance,
            "front_frame_to_spine_common_mm3": frame_root,
            "spine_to_backing_common_mm3": spine_backing,
            "backing_to_perpendicular_walls_common_mm3": wall_root,
            "backing_to_transition_shelf_common_mm3": transition_root,
            "backing_to_lens_seat_common_mm3": seat_root,
            "structural_root_depth_mm": structural_depth,
            "source_removed_mm3": source_removed,
            "manual_flange_missing_mm3": manual_missing,
            "added_to_shell_common_mm3": shell_common,
            "added_to_lens_common_mm3": lens_common,
            "added_to_rear_plate_common_mm3": rear_common,
            "added_to_side_screws_common_mm3": side_screw_common,
            "added_to_rear_screws_common_mm3": rear_screw_common,
            "added_to_leds_common_mm3": led_common,
            "added_to_wire_common_mm3": wire_common,
            "mesh": mesh_record,
        },
        "pins": {
            "contract_sha256": sha256(CONTRACT_PATH),
            "generator_sha256": sha256(Path(__file__)),
            "inputs": context["repair_inputs"],
        },
        "io_trace": {
            "source_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }


def add_feature(
    doc: Any,
    name: str,
    label: str,
    shape: Any,
    color: tuple[float, float, float],
    transparency: int,
) -> Any:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
    obj.Authority = "REVIEW_ONLY__NOT_A_PRINT_SOURCE"
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.ShapeColor = color
        view.LineColor = tuple(max(0.0, value * 0.45) for value in color)
        view.Transparency = transparency
    return obj


def create_fcstd(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeCarrierStructuralRootRepairReviewV1")
    try:
        add_feature(doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL", "REFERENCE — RELIEVED RIGHT HEAD SHELL", context["shell"], (0.72, 0.72, 0.75), 82)
        original = add_feature(doc, "REFERENCE__FAILED_PRINTED_RIGHT_CARRIER", "REFERENCE — PHYSICALLY FAILED PRINTED RIGHT CARRIER", context["final_shapes"]["carrier"], (0.78, 0.12, 0.10), 72)
        original.addProperty("App::PropertyString", "PhysicalEvidence", "ReviewControl")
        original.PhysicalEvidence = "Printed ASA carrier separated at zero-positive-overlap roots"
        candidate = add_feature(doc, "PROPOSED__STRUCTURALLY_REPAIRED_RIGHT_CARRIER", "PROPOSED — RIGHT CARRIER WITH CONTINUOUS STRUCTURAL ROOT", context["candidate"], (0.12, 0.72, 0.28), 0)
        candidate.addProperty("App::PropertyString", "Repair", "ReviewControl")
        candidate.Repair = "Continuous frame spine + 1.60 mm-deep frame/wall backing collar"
        add_feature(doc, "REVIEW__ADDED_CONTINUOUS_STRUCTURAL_ROOT", "REVIEW — ADDED STRUCTURAL MATERIAL ONLY", context["added"], (1.00, 0.48, 0.02), 24)
        add_feature(doc, "REFERENCE__MANUAL_BOTTOM_FLANGE_PRESERVED", "REFERENCE — USER MANUAL BOTTOM FLANGE PRESERVED", context["final_shapes"]["carrier"].cut(context["carrier"]), (0.70, 0.18, 0.88), 22)
        add_feature(doc, "REFERENCE__APPROVED_LENS_UNCHANGED", "REFERENCE — APPROVED TRANSLUCENT LENS UNCHANGED", context["final_shapes"]["lens"], (0.35, 0.86, 0.96), 58)
        add_feature(doc, "REFERENCE__REAR_PLATE_UNCHANGED", "REFERENCE — REMOVABLE LED REAR PLATE UNCHANGED", context["final_shapes"]["rear_plate"], (0.08, 0.34, 0.14), 28)
        doc.recompute()
        path = output / context["repair_contract"]["outputs"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["toolkit"]
    v3 = context["v3_module"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    original = toolkit.shape_record(context["final_shapes"]["carrier"], (188, 48, 42), deflection=0.30)
    candidate = toolkit.shape_record(context["candidate"], (36, 182, 72), deflection=0.24)
    added = toolkit.shape_record(context["added"], (255, 122, 8), deflection=0.12)
    lens = toolkit.shape_record(context["final_shapes"]["lens"], (80, 218, 242), deflection=0.18)
    rear = toolkit.shape_record(context["final_shapes"]["rear_plate"], (22, 94, 48), deflection=0.18)
    axis_u = v3.tuple3(context["axis_u"])
    axis_v = v3.tuple3(context["axis_v"])
    axis_n = v3.tuple3(context["axis_n"])
    toolkit.render_side_by_side(output / "assembled-context.png", [shell, candidate, lens, rear], [candidate, lens, rear], axis_u, axis_v)
    toolkit.render_side_by_side(output / "structural-root-highlight.png", [original, added], [candidate, added], axis_u, axis_v)
    toolkit.render_side_by_side(output / "rear-service-context.png", [candidate, added, rear], [candidate, rear], axis_u, axis_n)


def write_review(context: dict[str, Any], feasibility: dict[str, Any], feasibility_sha: str) -> Path:
    output = project_path(str(context["repair_contract"]["outputs"]["directory"]))
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    with tempfile.TemporaryDirectory(prefix="right-eye-root-repair-v1-") as temporary:
        staging = Path(temporary) / "review"
        staging.mkdir()
        fcstd = create_fcstd(context, staging)
        render_views(context, staging)
        review = dict(feasibility)
        review["status"] = "REVIEW_ONLY_READY__AWAITING_PHYSICAL_FAILURE_REPAIR_LGTM"
        review["review_fcstd"] = str(Path(context["repair_contract"]["outputs"]["directory"]) / fcstd.name)
        review["review_fcstd_sha256"] = sha256(fcstd)
        review["feasibility_report_sha256"] = feasibility_sha
        review["io_trace"] = {
            "source_saved": False,
            "review_saved": True,
            "geometry_export_created": False,
            "production_output_created": False,
        }
        validation = staging / context["repair_contract"]["outputs"]["validation"]
        validation.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging, output)
    return output


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = prepare()
    construct(context)
    result = evaluate(context)
    result["elapsed_seconds"] = time.monotonic() - started
    if result["status"] != "FEASIBILITY_PASS__RIGHT_REVIEW_ALLOWED":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    if args.mode == "feasibility":
        if args.report is None:
            raise RuntimeError("--report is required for feasibility")
        report = args.report.resolve()
        if not str(report).startswith("/tmp/"):
            raise RuntimeError("feasibility report must remain under /tmp")
        if report.exists():
            raise RuntimeError(f"refusing to overwrite feasibility report: {report}")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(result["status"])
        return 0
    if args.feasibility_report is None or not args.feasibility_sha256:
        raise RuntimeError("review requires --feasibility-report and --feasibility-sha256")
    feasibility_path = args.feasibility_report.resolve()
    if sha256(feasibility_path) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    feasibility = json.loads(feasibility_path.read_text(encoding="utf-8"))
    if feasibility.get("status") != "FEASIBILITY_PASS__RIGHT_REVIEW_ALLOWED":
        raise RuntimeError("feasibility report is not passing")
    output = write_review(context, result, args.feasibility_sha256)
    print(json.dumps({"status": "REVIEW_ONLY_READY", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
