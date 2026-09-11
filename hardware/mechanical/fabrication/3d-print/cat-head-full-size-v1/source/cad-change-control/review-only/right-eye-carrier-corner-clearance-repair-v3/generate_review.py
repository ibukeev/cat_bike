#!/usr/bin/env python3
"""Build the review-only V3 eye-carrier repair with measured corner clearance."""

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
    if contract.get("schema_version") != "cat-head-right-eye-carrier-corner-clearance-repair-v3":
        raise RuntimeError("unexpected V3 contract schema")
    return contract


def verify_inputs(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(str(item["path"]))
        actual = sha256(path)
        if actual != str(item["sha256"]):
            raise RuntimeError(f"input hash mismatch for {key}: {actual}")
        records[key] = {"path": str(item["path"]), "sha256": actual}
    return records


def prepare() -> dict[str, Any]:
    contract = load_contract()
    inputs = verify_inputs(contract)
    v2_path = project_path(str(contract["inputs"]["withdrawn_v2_generator"]["path"]))
    v2 = load_module(v2_path, "_pinned_withdrawn_v2_for_corner_clearance_v3")
    context = v2.prepare()
    v2.construct(context)
    context.update({
        "v3_contract": contract,
        "v3_inputs": inputs,
        "v2_module": v2,
        "v2_candidate": context["candidate"].copy(),
        "v2_added": context["added"].copy(),
        "v2_full_depth_spine": context["full_depth_spine"].copy(),
        "v2_structural_backing": context["structural_backing"].copy(),
    })
    owner_name = str(contract["measured_contact"]["shell_owner"])
    matches = [shape for name, shape in context["shell_records"] if str(name) == owner_name]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one measured corner owner {owner_name}, found {len(matches)}")
    context["corner_shell_owner"] = matches[0]
    return context


def make_box(Part: Any, App: Any, minimum: Sequence[float], maximum: Sequence[float]) -> Any:
    x0, y0, z0 = map(float, minimum)
    x1, y1, z1 = map(float, maximum)
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def expanded_contact_bounds(contract: dict[str, Any]) -> tuple[list[float], list[float]]:
    contact = contract["measured_contact"]
    padding = float(contract["repair_dimensions_mm"]["local_clearance_box_padding"])
    minimum = [float(value) - padding for value in contact["section_bbox_minimum_world_mm"]]
    maximum = [float(value) + padding for value in contact["section_bbox_maximum_world_mm"]]
    return minimum, maximum


def construct(context: dict[str, Any]) -> None:
    contract = context["v3_contract"]
    toolkit = context["toolkit"]
    minimum, maximum = expanded_contact_bounds(contract)
    clearance_box = make_box(context["Part"], context["App"], minimum, maximum)
    trimmed_spine = context["v2_full_depth_spine"].cut(clearance_box).removeSplitter()
    toolkit.require_single_solid(trimmed_spine, "corner-cleared full-depth outer spine")
    reinforcement = toolkit.fuse_shapes(
        [trimmed_spine, context["v2_structural_backing"]],
        "corner-cleared outer spine plus exact V2 inner backing",
    ).removeSplitter()
    toolkit.require_single_solid(reinforcement, "V3 corner-cleared structural bypass")
    source = context["final_shapes"]["carrier"]
    candidate = toolkit.fuse_shapes(
        [source, reinforcement],
        "source carrier plus V3 corner-cleared structural repair",
    ).removeSplitter()
    toolkit.require_single_solid(candidate, "V3 corner-cleared right eye carrier")
    added = candidate.cut(source).removeSplitter()
    context.update({
        "clearance_box": clearance_box,
        "full_depth_spine": trimmed_spine,
        "structural_backing": context["v2_structural_backing"],
        "reinforcement": reinforcement,
        "candidate": candidate,
        "added": added,
    })


def shape_record(context: dict[str, Any], shape: Any) -> dict[str, Any]:
    return context["v1_module"].shape_record(shape)


def shell_clearance_records(context: dict[str, Any], shape: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for owner_name, owner in context["shell_records"]:
        if not context["v3_module"].aabb_near(shape, owner, 2.5):
            continue
        result = shape.distToShape(owner)
        section = shape.section(owner)
        records.append({
            "owner": str(owner_name),
            "distance_mm": float(result[0]),
            "positive_common_mm3": float(shape.common(owner).Volume),
            "section_edge_count": len(section.Edges) if not section.isNull() else 0,
            "section_vertex_count": len(section.Vertexes) if not section.isNull() else 0,
        })
    records.sort(key=lambda item: (item["distance_mm"], item["owner"]))
    return records


def projection_span(shape: Any, origin: Any, axis: Any) -> float:
    values = [float(axis.dot(vertex.Point - origin)) for vertex in shape.Vertexes]
    if not values:
        return 0.0
    return max(values) - min(values)


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["v3_contract"]
    dimensions = contract["repair_dimensions_mm"]
    gates = contract["gates"]
    v1 = context["v1_module"]
    source = context["final_shapes"]["carrier"]
    candidate = context["candidate"]
    added = context["added"]
    spine = context["full_depth_spine"]
    backing = context["structural_backing"]
    reinforcement = context["reinforcement"]
    corner_owner = context["corner_shell_owner"]

    chain = {
        "spine_to_front_filler_mm3": v1.common_volume(spine, context["opening_cover"]),
        "spine_to_opening_connector_mm3": v1.common_volume(spine, context["opening_cover_connector"]),
        "spine_to_bezel_mm3": v1.common_volume(spine, context["bezel"]),
        "spine_to_lens_surround_mm3": v1.common_volume(spine, context["lens_surround"]),
        "spine_to_backing_mm3": v1.common_volume(spine, backing),
        "backing_to_walls_mm3": v1.common_volume(backing, context["walls"]),
        "backing_to_transition_mm3": v1.common_volume(backing, context["wall_transition_shelf"]),
    }
    source_removed = float(source.cut(candidate).Volume)
    manual_additions = source.cut(context["carrier"]).removeSplitter()
    manual_missing = float(manual_additions.cut(candidate).Volume)
    backing_missing = float(backing.cut(reinforcement).Volume)
    added_volume = float(added.Volume)
    volume_balance = abs(float(candidate.Volume) - float(source.Volume) - added_volume)
    removed_from_v2_spine = float(context["v2_full_depth_spine"].cut(spine).Volume)

    shell_records = shell_clearance_records(context, added)
    minimum_shell_clearance = min((item["distance_mm"] for item in shell_records), default=2.5)
    total_shell_section_edges = sum(int(item["section_edge_count"]) for item in shell_records)
    corner_result = added.distToShape(corner_owner)
    corner_section = added.section(corner_owner)
    corner_clearance = float(corner_result[0])

    lens_common = v1.common_volume(added, context["final_shapes"]["lens"])
    rear_common = v1.common_volume(added, context["final_shapes"]["rear_plate"])
    side_screw_common = v1.common_volume(added, context["side_screw_references"])
    rear_screw_common = v1.common_volume(added, context["rear_screw_references"])
    led_common = sum(v1.common_volume(added, item) for item in context["led_shapes"])
    wire_common = v1.common_volume(added, context["wire_corridor"])
    zero_protected = float(gates["zero_protected_intersection_mm3"])

    source_record = shape_record(context, source)
    spine_record = shape_record(context, spine)
    reinforcement_record = shape_record(context, reinforcement)
    candidate_record = shape_record(context, candidate)
    full_depth_span = projection_span(spine, context["origin"], context["axis_n"])
    mesh = context["MeshPart"].meshFromShape(
        Shape=candidate,
        LinearDeflection=float(dimensions["mesh_linear_deflection"]),
        AngularDeflection=float(dimensions["mesh_angular_deflection"]),
        Relative=False,
    )
    mesh_record = context["mesh_checker"].mesh_topology(mesh)
    required_clearance = float(dimensions["minimum_new_material_to_any_shell_clearance"])
    clearance_tolerance = float(dimensions["clearance_measurement_tolerance"])
    checks = {
        "source_carrier_and_manual_flange_are_additively_preserved": (
            source_removed <= float(gates["zero_removed_volume_from_source_carrier_mm3"])
            and manual_missing <= float(gates["zero_removed_volume_from_source_carrier_mm3"])
        ),
        "exact_v2_structural_backing_is_retained": backing_missing <= EPSILON_MM3,
        "clearance_notch_removes_positive_v2_spine_material": removed_from_v2_spine > 0.1,
        "corner_owner_has_no_contact_section": (
            len(corner_section.Edges) == 0 and len(corner_section.Vertexes) == 0
        ),
        "new_material_has_required_clearance_to_every_shell_owner": (
            minimum_shell_clearance + clearance_tolerance >= required_clearance
        ),
        "new_material_has_zero_positive_shell_overlap": max(
            (float(item["positive_common_mm3"]) for item in shell_records), default=0.0
        ) <= zero_protected,
        "new_material_has_no_shell_section_edges": total_shell_section_edges == 0,
        "spine_is_one_valid_closed_solid": (
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
            len(candidate_record["deep_check_messages"]) <= len(source_record["deep_check_messages"])
        ),
        "candidate_volume_balance_is_exact": volume_balance <= 1.0e-5,
        "global_full_depth_span_is_preserved": (
            full_depth_span + 1.0e-6 >= float(gates["minimum_global_full_depth_span_mm"])
        ),
        "front_filler_has_large_positive_spine_root": (
            chain["spine_to_front_filler_mm3"] >= float(gates["minimum_spine_to_front_filler_overlap_mm3"])
        ),
        "opening_connector_has_large_positive_spine_root": (
            chain["spine_to_opening_connector_mm3"] >= float(gates["minimum_spine_to_opening_connector_overlap_mm3"])
        ),
        "bezel_has_large_positive_spine_root": (
            chain["spine_to_bezel_mm3"] >= float(gates["minimum_spine_to_bezel_overlap_mm3"])
        ),
        "lens_surround_has_large_positive_spine_root": (
            chain["spine_to_lens_surround_mm3"] >= float(gates["minimum_spine_to_lens_surround_overlap_mm3"])
        ),
        "spine_has_large_positive_backing_root": (
            chain["spine_to_backing_mm3"] >= float(gates["minimum_spine_to_backing_overlap_mm3"])
        ),
        "backing_has_large_positive_wall_root": (
            chain["backing_to_walls_mm3"] >= float(gates["minimum_backing_to_wall_overlap_mm3"])
        ),
        "backing_has_large_positive_transition_root": (
            chain["backing_to_transition_mm3"] >= float(gates["minimum_backing_to_transition_overlap_mm3"])
        ),
        "repair_clears_lens_rear_hardware_leds_and_wire": max(
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
        "schema_version": "cat-head-right-eye-carrier-corner-clearance-repair-validation-v3",
        "status": "FEASIBILITY_PASS__V3_REVIEW_ALLOWED" if not failed else "FEASIBILITY_FAIL__NO_V3_REVIEW_OUTPUT",
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "measurements": {
            "source_carrier": source_record,
            "candidate_carrier": candidate_record,
            "corner_cleared_spine": spine_record,
            "structural_bypass": reinforcement_record,
            "replacement_chain_roots": chain,
            "clearance_box_minimum_world_mm": expanded_contact_bounds(contract)[0],
            "clearance_box_maximum_world_mm": expanded_contact_bounds(contract)[1],
            "v2_spine_material_removed_by_clearance_notch_mm3": removed_from_v2_spine,
            "added_structural_material_mm3": added_volume,
            "source_removed_mm3": source_removed,
            "manual_flange_missing_mm3": manual_missing,
            "v2_structural_backing_missing_mm3": backing_missing,
            "volume_balance_error_mm3": volume_balance,
            "global_full_depth_spine_span_mm": full_depth_span,
            "corner_owner_new_material_clearance_mm": corner_clearance,
            "corner_owner_section_edge_count": len(corner_section.Edges),
            "corner_owner_section_vertex_count": len(corner_section.Vertexes),
            "minimum_new_material_to_any_shell_clearance_mm": minimum_shell_clearance,
            "shell_clearance_records_within_2p5_mm": shell_records,
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
            "inputs": context["v3_inputs"],
        },
        "io_trace": {
            "target_assignment_performed": False,
            "metadata_assignment_performed": False,
            "recompute_performed": False,
            "final_assertions_performed": False,
            "save_as_called": False,
            "document_save_called": False,
            "candidate_exists": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }


def in_memory_finalize(context: dict[str, Any], result: dict[str, Any]) -> None:
    doc = context["App"].newDocument("DisposableV3CornerClearanceFinalization")
    try:
        target = doc.addObject("Part::Feature", "DisposableTarget")
        target.Label = "DISPOSABLE V3 CORNER-CLEARANCE TARGET"
        target.Shape = context["candidate"].copy()
        target.addProperty("App::PropertyString", "Authority", "ReviewControl")
        target.Authority = "DISPOSABLE_IN_MEMORY__NOT_SAVED"
        target.addProperty("App::PropertyFloat", "MinimumAddedShellClearance", "ReviewControl")
        target.MinimumAddedShellClearance = float(
            result["measurements"]["minimum_new_material_to_any_shell_clearance_mm"]
        )
        doc.recompute()
        context["toolkit"].require_single_solid(target.Shape, "disposable V3 final target")
        if target.Label != "DISPOSABLE V3 CORNER-CLEARANCE TARGET":
            raise RuntimeError("disposable target identity changed")
        result["io_trace"].update({
            "target_assignment_performed": True,
            "metadata_assignment_performed": True,
            "recompute_performed": True,
            "final_assertions_performed": True,
        })
    finally:
        context["App"].closeDocument(doc.Name)


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
    doc = context["App"].newDocument("RightEyeCarrierCornerClearanceRepairReviewV3")
    try:
        add_feature(
            doc,
            "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL",
            "REFERENCE — RELIEVED RIGHT HEAD SHELL",
            context["shell"],
            (0.72, 0.72, 0.75),
            76,
        )
        candidate = add_feature(
            doc,
            "PROPOSED__CORNER_CLEARED_STRUCTURALLY_REPAIRED_RIGHT_CARRIER",
            "PROPOSED — CORNER-CLEARED STRUCTURALLY REPAIRED RIGHT CARRIER",
            context["candidate"],
            (0.12, 0.72, 0.28),
            0,
        )
        candidate.addProperty("App::PropertyString", "Repair", "ReviewControl")
        candidate.Repair = "V2 full-depth structural bypass retained; only the zero-clearance outer-spine corner is notched"
        add_feature(
            doc,
            "REVIEW__V3_ADDED_STRUCTURAL_MATERIAL_ONLY",
            "REVIEW — V3 ADDED STRUCTURAL MATERIAL ONLY",
            context["added"],
            (1.00, 0.48, 0.02),
            24,
        )
        add_feature(
            doc,
            "REVIEW__MEASURED_CORNER_CLEARANCE_VOLUME",
            "REVIEW — MEASURED CORNER CLEARANCE BOX (NOT PART OF CARRIER)",
            context["clearance_box"],
            (0.10, 0.80, 0.94),
            72,
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
        path = output / context["v3_contract"]["outputs"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        context["App"].closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["toolkit"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    candidate = toolkit.shape_record(context["candidate"], (36, 182, 72), deflection=0.22)
    added = toolkit.shape_record(context["added"], (255, 122, 8), deflection=0.10)
    lens = toolkit.shape_record(context["final_shapes"]["lens"], (80, 218, 242), deflection=0.18)
    rear = toolkit.shape_record(context["final_shapes"]["rear_plate"], (22, 94, 48), deflection=0.18)
    clearance_box = toolkit.shape_record(context["clearance_box"], (36, 204, 238), deflection=0.10)

    contact_min, contact_max = expanded_contact_bounds(context["v3_contract"])
    local_min = [value - 2.0 for value in contact_min]
    local_max = [value + 2.0 for value in contact_max]
    local_box = make_box(context["Part"], context["App"], local_min, local_max)
    local_shell_shape = context["corner_shell_owner"].common(local_box).removeSplitter()
    local_v2_added_shape = context["v2_added"].common(local_box).removeSplitter()
    local_added_shape = context["added"].common(local_box).removeSplitter()
    local_shell = toolkit.shape_record(local_shell_shape, (142, 146, 152), deflection=0.08)
    local_v2_added = toolkit.shape_record(local_v2_added_shape, (196, 42, 38), deflection=0.06)
    local_added = toolkit.shape_record(local_added_shape, (36, 182, 72), deflection=0.06)

    toolkit.render_side_by_side(
        output / "assembled-context.png",
        [shell, candidate, lens, rear],
        [candidate, lens, rear],
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "corner-shell-clearance-closeup.png",
        [local_shell, local_v2_added],
        [local_shell, local_added],
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "repair-only-corner-closeup.png",
        [local_v2_added, clearance_box],
        [local_added, clearance_box],
        (0.0, -1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "left-seam.png",
        [candidate, added],
        [candidate],
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    toolkit.render_side_by_side(
        output / "right-seam.png",
        [candidate, added],
        [candidate],
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def write_review(context: dict[str, Any], result: dict[str, Any], feasibility_sha: str) -> Path:
    output = project_path(str(context["v3_contract"]["outputs"]["directory"]))
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    with tempfile.TemporaryDirectory(prefix="right-eye-corner-clearance-v3-") as temporary:
        staging = Path(temporary) / "review"
        staging.mkdir()
        fcstd = create_fcstd(context, staging)
        render_views(context, staging)
        review = dict(result)
        review["status"] = "REVIEW_ONLY_READY__AWAITING_CORNER_CLEARANCE_LGTM"
        review["review_fcstd"] = str(
            Path(context["v3_contract"]["outputs"]["directory"]) / fcstd.name
        )
        review["review_fcstd_sha256"] = sha256(fcstd)
        review["feasibility_report_sha256"] = feasibility_sha
        review["io_trace"].update({
            "review_saved": True,
            "candidate_exists": False,
        })
        validation = staging / context["v3_contract"]["outputs"]["validation"]
        validation.write_text(
            json.dumps(review, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
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
    if result["status"] == "FEASIBILITY_PASS__V3_REVIEW_ALLOWED":
        in_memory_finalize(context, result)
    result["elapsed_seconds"] = time.monotonic() - started
    if result["status"] != "FEASIBILITY_PASS__V3_REVIEW_ALLOWED":
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
    if feasibility.get("status") != "FEASIBILITY_PASS__V3_REVIEW_ALLOWED":
        raise RuntimeError("feasibility report is not passing")
    output = write_review(context, result, args.feasibility_sha256)
    print(json.dumps({"status": "REVIEW_ONLY_READY", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
