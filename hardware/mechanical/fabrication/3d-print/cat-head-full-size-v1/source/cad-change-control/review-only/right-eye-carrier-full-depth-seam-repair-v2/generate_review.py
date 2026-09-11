#!/usr/bin/env python3
"""Build a full-depth, review-only seam repair for the failed right eye carrier."""

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
    if contract.get("schema_version") != "cat-head-right-eye-carrier-full-depth-seam-repair-v2":
        raise RuntimeError("unexpected V2 contract schema")
    return contract


def verify_inputs(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(str(item["path"]))
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


def prepare() -> dict[str, Any]:
    contract = load_contract()
    inputs = verify_inputs(contract)
    v1_path = project_path(str(contract["inputs"]["withdrawn_v1_generator"]["path"]))
    v1 = load_module(v1_path, "_withdrawn_v1_imported_only_for_pinned_inputs")
    context = v1.prepare()
    context.update({
        "v2_contract": contract,
        "v2_inputs": inputs,
        "v1_module": v1,
    })
    return context


def occupied_shapes(context: dict[str, Any]) -> list[Any]:
    shapes = [owner for _, owner in context["shell_records"]]
    shapes.extend([
        context["final_shapes"]["lens"],
        context["final_shapes"]["rear_plate"],
        context["wire_corridor"],
    ])
    shapes.extend(context["led_shapes"])
    for compound_key in ("side_screw_references", "rear_screw_references"):
        compound = context[compound_key]
        solids = list(compound.Solids)
        shapes.extend(solids if solids else [compound])
    return shapes


def trim_new_material(context: dict[str, Any], shape: Any, exclusions: Sequence[Any]) -> Any:
    trimmed = shape.copy()
    v3 = context["v3_module"]
    for occupied in exclusions:
        if v3.aabb_near(trimmed, occupied, 0.0):
            trimmed = trimmed.cut(occupied).removeSplitter()
            if trimmed.isNull():
                raise RuntimeError("protected-volume trim consumed the full-depth seam repair")
    return trimmed


def construct(context: dict[str, Any]) -> None:
    contract = context["v2_contract"]
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
    raw_spine = toolkit.ring_prism(
        Part,
        context["rim_outer"],
        context["lens_outer"],
        float(values["full_depth_spine_front_depth"]),
        float(values["full_depth_spine_rear_depth"]),
        axis_n,
        "continuous full-depth front-panel-to-box seam spine",
    )
    raw_backing = toolkit.ring_prism(
        Part,
        backing_outer,
        context["box_inner"],
        float(values["structural_backing_front_depth"]),
        float(values["structural_backing_rear_depth"]),
        axis_n,
        "continuous full-depth seam-to-wall backing",
    )
    exclusions = occupied_shapes(context)
    spine = trim_new_material(context, raw_spine, exclusions)
    backing = trim_new_material(context, raw_backing, exclusions)
    toolkit.require_single_solid(spine, "trimmed continuous full-depth seam spine")
    toolkit.require_single_solid(backing, "trimmed seam-to-wall backing")
    reinforcement = toolkit.fuse_shapes(
        [spine, backing], "full-depth front-panel-to-wall reinforcement"
    ).removeSplitter()
    toolkit.require_single_solid(reinforcement, "full-depth seam reinforcement")

    source_carrier = context["final_shapes"]["carrier"]
    candidate = toolkit.fuse_shapes(
        [source_carrier, reinforcement],
        "user carrier plus full-depth front-panel seam repair",
    ).removeSplitter()
    toolkit.require_single_solid(candidate, "full-depth seam-repaired right eye carrier")
    added = candidate.cut(source_carrier).removeSplitter()
    context.update({
        "backing_outer": backing_outer,
        "raw_full_depth_spine": raw_spine,
        "raw_structural_backing": raw_backing,
        "full_depth_spine": spine,
        "structural_backing": backing,
        "reinforcement": reinforcement,
        "candidate": candidate,
        "added": added,
    })


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["v2_contract"]
    values = contract["repair_dimensions_mm"]
    gates = contract["gates"]
    v1 = context["v1_module"]
    source = context["final_shapes"]["carrier"]
    candidate = context["candidate"]
    added = context["added"]
    spine = context["full_depth_spine"]
    backing = context["structural_backing"]
    reinforcement = context["reinforcement"]

    chain = {
        "spine_to_front_filler_mm3": v1.common_volume(spine, context["opening_cover"]),
        "spine_to_opening_connector_mm3": v1.common_volume(spine, context["opening_cover_connector"]),
        "spine_to_bezel_mm3": v1.common_volume(spine, context["bezel"]),
        "spine_to_lens_surround_mm3": v1.common_volume(spine, context["lens_surround"]),
        "spine_to_backing_mm3": v1.common_volume(spine, backing),
        "backing_to_walls_mm3": v1.common_volume(backing, context["walls"]),
        "backing_to_transition_mm3": v1.common_volume(backing, context["wall_transition_shelf"]),
    }
    original_weak_roots = {
        "front_filler_to_opening_connector_mm3": v1.common_volume(
            context["opening_cover"], context["opening_cover_connector"]
        ),
        "opening_connector_to_bezel_mm3": v1.common_volume(
            context["opening_cover_connector"], context["bezel"]
        ),
    }
    source_removed = float(source.cut(candidate).Volume)
    manual_additions = source.cut(context["carrier"]).removeSplitter()
    manual_missing = float(manual_additions.cut(candidate).Volume)
    spine_missing = float(spine.cut(candidate).Volume)
    reinforcement_missing = float(reinforcement.cut(candidate).Volume)
    added_volume = float(added.Volume)
    volume_balance = abs(float(candidate.Volume) - float(source.Volume) - added_volume)

    shell_common = float(context["repair_v7"].shell_common(context, added))
    lens_common = v1.common_volume(added, context["final_shapes"]["lens"])
    rear_common = v1.common_volume(added, context["final_shapes"]["rear_plate"])
    side_screw_common = v1.common_volume(added, context["side_screw_references"])
    rear_screw_common = v1.common_volume(added, context["rear_screw_references"])
    led_common = sum(v1.common_volume(added, item) for item in context["led_shapes"])
    wire_common = v1.common_volume(added, context["wire_corridor"])

    source_record = v1.shape_record(source)
    candidate_record = v1.shape_record(candidate)
    spine_record = v1.shape_record(spine)
    reinforcement_record = v1.shape_record(reinforcement)
    mesh = context["MeshPart"].meshFromShape(
        Shape=candidate,
        LinearDeflection=float(values["mesh_linear_deflection"]),
        AngularDeflection=float(values["mesh_angular_deflection"]),
        Relative=False,
    )
    mesh_record = context["mesh_checker"].mesh_topology(mesh)
    spine_span = (
        float(values["full_depth_spine_rear_depth"])
        - float(values["full_depth_spine_front_depth"])
    )
    zero_protected = float(gates["zero_protected_intersection_mm3"])
    checks = {
        "full_depth_spine_is_one_valid_closed_solid": (
            spine_record["valid"] and spine_record["closed"] and spine_record["solid_count"] == 1
        ),
        "reinforcement_is_one_valid_closed_solid": (
            reinforcement_record["valid"]
            and reinforcement_record["closed"]
            and reinforcement_record["solid_count"] == 1
        ),
        "candidate_is_one_valid_closed_solid": (
            candidate_record["valid"]
            and candidate_record["closed"]
            and candidate_record["solid_count"] == 1
        ),
        "candidate_adds_no_deep_occt_defects": (
            len(candidate_record["deep_check_messages"])
            <= len(source_record["deep_check_messages"])
        ),
        "user_carrier_and_manual_flange_are_additively_preserved": (
            source_removed <= float(gates["zero_removed_volume_from_user_carrier_mm3"])
            and manual_missing <= float(gates["zero_removed_volume_from_user_carrier_mm3"])
        ),
        "entire_spine_and_reinforcement_are_retained_in_candidate": (
            spine_missing <= EPSILON_MM3 and reinforcement_missing <= EPSILON_MM3
        ),
        "candidate_volume_balance_is_exact": volume_balance <= 1.0e-5,
        "full_depth_spine_span_is_at_least_4p2_mm": (
            spine_span + 1.0e-9 >= float(gates["minimum_full_depth_spine_span_mm"])
        ),
        "front_filler_has_large_positive_spine_root": (
            chain["spine_to_front_filler_mm3"]
            >= float(gates["minimum_spine_to_front_filler_overlap_mm3"])
        ),
        "opening_connector_has_large_positive_spine_root": (
            chain["spine_to_opening_connector_mm3"]
            >= float(gates["minimum_spine_to_opening_connector_overlap_mm3"])
        ),
        "bezel_has_large_positive_spine_root": (
            chain["spine_to_bezel_mm3"]
            >= float(gates["minimum_spine_to_bezel_overlap_mm3"])
        ),
        "lens_surround_has_large_positive_spine_root": (
            chain["spine_to_lens_surround_mm3"]
            >= float(gates["minimum_spine_to_lens_surround_overlap_mm3"])
        ),
        "spine_has_large_positive_backing_root": (
            chain["spine_to_backing_mm3"]
            >= float(gates["minimum_spine_to_backing_overlap_mm3"])
        ),
        "backing_has_large_positive_wall_root": (
            chain["backing_to_walls_mm3"]
            >= float(gates["minimum_backing_to_wall_overlap_mm3"])
        ),
        "backing_has_large_positive_transition_root": (
            chain["backing_to_transition_mm3"]
            >= float(gates["minimum_backing_to_transition_overlap_mm3"])
        ),
        "repair_clears_shell_lens_rear_hardware_leds_and_wire": max(
            shell_common,
            lens_common,
            rear_common,
            side_screw_common,
            rear_screw_common,
            led_common,
            wire_common,
        ) <= zero_protected,
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
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-right-eye-carrier-full-depth-seam-repair-validation-v2",
        "status": "FEASIBILITY_PASS__V2_REVIEW_ALLOWED" if not failed else "FEASIBILITY_FAIL__NO_V2_REVIEW_OUTPUT",
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "measurements": {
            "source_carrier": source_record,
            "candidate_carrier": candidate_record,
            "full_depth_spine": spine_record,
            "reinforcement": reinforcement_record,
            "original_weak_roots": original_weak_roots,
            "replacement_chain_roots": chain,
            "full_depth_spine_span_mm": spine_span,
            "added_structural_material_mm3": added_volume,
            "source_removed_mm3": source_removed,
            "manual_flange_missing_mm3": manual_missing,
            "spine_missing_from_candidate_mm3": spine_missing,
            "reinforcement_missing_from_candidate_mm3": reinforcement_missing,
            "volume_balance_error_mm3": volume_balance,
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
            "inputs": context["v2_inputs"],
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
        view.LineColor = tuple(max(0.0, item * 0.45) for item in color)
        view.Transparency = transparency
    return obj


def create_fcstd(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeCarrierFullDepthSeamRepairReviewV2")
    try:
        add_feature(
            doc,
            "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL",
            "REFERENCE — RELIEVED RIGHT HEAD SHELL",
            context["shell"],
            (0.72, 0.72, 0.75),
            82,
        )
        candidate = add_feature(
            doc,
            "PROPOSED__FULL_DEPTH_SEAM_REPAIRED_RIGHT_CARRIER",
            "PROPOSED — FULL-DEPTH SEAM-REPAIRED RIGHT CARRIER",
            context["candidate"],
            (0.12, 0.72, 0.28),
            0,
        )
        candidate.addProperty("App::PropertyString", "Repair", "ReviewControl")
        candidate.Repair = "Continuous -0.50..3.70 mm spine bypasses every front-panel-to-wall weak link"
        add_feature(
            doc,
            "REVIEW__ADDED_FULL_DEPTH_SEAM_REPAIR_ONLY",
            "REVIEW — ADDED FULL-DEPTH SEAM REPAIR ONLY",
            context["added"],
            (1.00, 0.48, 0.02),
            24,
        )
        add_feature(
            doc,
            "REFERENCE__APPROVED_LENS_UNCHANGED",
            "REFERENCE — APPROVED TRANSLUCENT LENS UNCHANGED",
            context["final_shapes"]["lens"],
            (0.35, 0.86, 0.96),
            58,
        )
        add_feature(
            doc,
            "REFERENCE__REAR_PLATE_UNCHANGED",
            "REFERENCE — REMOVABLE LED REAR PLATE UNCHANGED",
            context["final_shapes"]["rear_plate"],
            (0.08, 0.34, 0.14),
            28,
        )
        doc.recompute()
        path = output / context["v2_contract"]["outputs"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["toolkit"]
    v3 = context["v3_module"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    source = toolkit.shape_record(context["final_shapes"]["carrier"], (188, 48, 42), deflection=0.30)
    candidate = toolkit.shape_record(context["candidate"], (36, 182, 72), deflection=0.24)
    added = toolkit.shape_record(context["added"], (255, 122, 8), deflection=0.12)
    lens = toolkit.shape_record(context["final_shapes"]["lens"], (80, 218, 242), deflection=0.18)
    rear = toolkit.shape_record(context["final_shapes"]["rear_plate"], (22, 94, 48), deflection=0.18)
    axis_n = v3.tuple3(context["axis_n"])
    axis_u = v3.tuple3(context["axis_u"])
    toolkit.render_side_by_side(
        output / "front-context.png",
        [shell, source, lens, rear],
        [shell, candidate, lens, rear],
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "left-seam-source-vs-repair.png",
        [source], [candidate],
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "right-seam-source-vs-repair.png",
        [source], [candidate],
        (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "rear-seam-highlight.png",
        [source, added], [candidate, added],
        (0.0, -1.0, 0.0), (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "aperture-normal-highlight.png",
        [source, added], [candidate, added],
        tuple(-item for item in axis_n), axis_u,
    )


def write_review(context: dict[str, Any], result: dict[str, Any], feasibility_sha: str) -> Path:
    output = project_path(str(context["v2_contract"]["outputs"]["directory"]))
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    with tempfile.TemporaryDirectory(prefix="right-eye-full-depth-seam-v2-") as temporary:
        staging = Path(temporary) / "review"
        staging.mkdir()
        fcstd = create_fcstd(context, staging)
        render_views(context, staging)
        review = dict(result)
        review["status"] = "REVIEW_ONLY_READY__AWAITING_FULL_DEPTH_SEAM_LGTM"
        review["review_fcstd"] = str(Path(context["v2_contract"]["outputs"]["directory"]) / fcstd.name)
        review["review_fcstd_sha256"] = sha256(fcstd)
        review["feasibility_report_sha256"] = feasibility_sha
        review["io_trace"] = {
            "source_saved": False,
            "review_saved": True,
            "geometry_export_created": False,
            "production_output_created": False,
        }
        validation = staging / context["v2_contract"]["outputs"]["validation"]
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
    if result["status"] != "FEASIBILITY_PASS__V2_REVIEW_ALLOWED":
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
    feasibility = args.feasibility_report.resolve()
    if sha256(feasibility) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    pinned = json.loads(feasibility.read_text(encoding="utf-8"))
    if pinned.get("status") != "FEASIBILITY_PASS__V2_REVIEW_ALLOWED":
        raise RuntimeError("feasibility report is not passing")
    output = write_review(context, result, args.feasibility_sha256)
    print(json.dumps({"status": "REVIEW_ONLY_READY", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
