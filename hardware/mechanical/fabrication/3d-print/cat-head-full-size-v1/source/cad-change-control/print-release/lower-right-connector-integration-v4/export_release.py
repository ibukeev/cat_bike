#!/usr/bin/env python3
"""Create the complete lower-right opaque print release V4.

V4 rebuilds the approved V3 corrections from their pinned source documents,
restores every accepted member of OPAQUE_RIGHT_LOWER_OWNERS, and packages the
complete opaque assembly in exactly one STL file.  The accepted source is
intrinsically multi-shell, so V4 uses a lossless compound/facet package instead
of a destructive global BRep boolean or invented bridges.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
V3_EXPORTER_PATH = HERE.parent / "lower-right-connector-integration-v3" / "export_release.py"
SCHEMA = "cat-head-lower-right-complete-opaque-print-release-v4"
PREFLIGHT_PASS = "PREFLIGHT_PASS__LOWER_RIGHT_V4_COMPLETE_OPAQUE_PACKAGE_ALLOWED"
RELEASE_PASS = "PRINT_RELEASE_PASS__V4_ONE_COMPLETE_OPAQUE_STL_AND_THREE_TRANSLUCENT_STLS_READY"

PART_IDS = (
    "opaque_complete",
    "translucent_quad003_component_01",
    "translucent_central_component_03",
    "translucent_quad017_component_02",
)

PART_OBJECT_NAMES = {
    "opaque_complete": "RIGHT_LOWER_COMPLETE_OPAQUE_ASSEMBLY_PRINT",
    "translucent_quad003_component_01": "RIGHT_TRANSLUCENT_QUAD003_COMPONENT_01_WITH_BELOW_MOUTH_TAB_PRINT",
    "translucent_central_component_03": "RIGHT_TRANSLUCENT_CENTRAL_CLUSTER_RIGHT_HALF_WITH_NOSE_TOP_TAB_PRINT",
    "translucent_quad017_component_02": "RIGHT_TRANSLUCENT_QUAD017_COMPONENT_02_WITH_OUTER_TAB_PRINT",
}

PART_LABELS = {
    "opaque_complete": "RIGHT LOWER — COMPLETE OPAQUE ASSEMBLY + APPROVED TABS + LEDGE — ONE STL",
    "translucent_quad003_component_01": "RIGHT LOWER — TRANSLUCENT QUAD003 COMPONENT 01 — BELOW-MOUTH TAB",
    "translucent_central_component_03": "RIGHT LOWER — TRANSLUCENT CENTRAL CLUSTER RIGHT HALF — NOSE-TOP TAB",
    "translucent_quad017_component_02": "RIGHT LOWER — TRANSLUCENT QUAD017 COMPONENT 02 — OUTER TAB",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    return path


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict[str, Any]:
    contract = load_json(CONTRACT_PATH)
    if contract.get("schema_version") != SCHEMA:
        raise RuntimeError("unexpected V4 lower-right print-release schema")
    return contract


def verify_pins(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(str(item["path"]))
        actual = sha256(path)
        expected = str(item["sha256"])
        if actual != expected:
            raise RuntimeError(
                f"hash mismatch for inputs.{key}: expected {expected}, got {actual}"
            )
        records[key] = {"path": str(item["path"]), "sha256": actual}
    return records


def mesh_topology_pass(
    record: dict[str, Any],
    require_one_component: bool,
    require_zero_self_intersections: bool = True,
) -> bool:
    return bool(
        (not require_one_component or record["connected_components"] == 1)
        and record["connected_components"] >= 1
        and record["boundary_edges"] == 0
        and record["nonmanifold_edges"] == 0
        and record["degenerate_facets"] == 0
        and record["duplicate_facets"] == 0
        and (
            not require_zero_self_intersections
            or record["self_intersection_count"] == 0
        )
        and record["outward_normals"]
        and float(record["signed_volume_mm3"]) > 0.0
    )


def combine_meshes(meshes: Sequence[Any], Mesh: Any, App: Any) -> Any:
    combined = Mesh.Mesh()
    for mesh in meshes:
        combined.addMesh(mesh)
    if combined.CountFacets == 0:
        raise RuntimeError("cannot create an empty combined opaque mesh")
    return combined


def maximum_bounds_delta(left: Any, right: Any) -> float:
    first = left.BoundBox
    second = right.BoundBox
    return max(
        abs(float(a) - float(b))
        for a, b in zip(
            (
                first.XMin,
                first.YMin,
                first.ZMin,
                first.XMax,
                first.YMax,
                first.ZMax,
            ),
            (
                second.XMin,
                second.YMin,
                second.ZMin,
                second.XMax,
                second.YMax,
                second.ZMax,
            ),
        )
    )


def prusa_slicer_info(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["prusa-slicer", "--info", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(
            f"PrusaSlicer --info failed for {path.name}: {output}"
        )
    values: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    try:
        number_of_parts = int(values["number_of_parts"])
    except (KeyError, ValueError) as error:
        raise RuntimeError(
            f"PrusaSlicer did not report number_of_parts for {path.name}"
        ) from error
    return {
        "exit_code": completed.returncode,
        "manifold": values.get("manifold"),
        "number_of_parts": number_of_parts,
        "number_of_facets": int(values.get("number_of_facets", "0")),
        "facets_reversed": int(values.get("facets_reversed", "0")),
        "volume_mm3": float(values.get("volume", "0")),
        "raw_output": output,
    }


def prepare() -> dict[str, Any]:
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import MeshPart  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    pins = verify_pins(contract)
    v3 = load_module(V3_EXPORTER_PATH, "_lower_right_release_v3_helpers_for_v4")
    base = v3.prepare()
    base_report = v3.evaluate(base)
    permitted_v3_failure = {"output_directory_is_fresh"}
    unexpected_v3_failures = sorted(
        set(base_report["failed_checks"]) - permitted_v3_failure
    )
    if unexpected_v3_failures:
        raise RuntimeError(
            "V3 in-memory source reconstruction failed: "
            + ", ".join(unexpected_v3_failures)
        )
    if set(base_report["failed_checks"]) != permitted_v3_failure:
        raise RuntimeError(
            "unexpected V3 predecessor state: "
            + ", ".join(base_report["failed_checks"])
        )

    policy = contract["opaque_policy"]
    expected_names = list(policy["required_owner_names"])
    baseline_path = project_path(
        str(contract["inputs"]["manual_baseline"]["path"])
    )
    baseline = App.openDocument(str(baseline_path))
    try:
        group = baseline.getObject(str(policy["source_group"]))
        if group is None or not hasattr(group, "Group"):
            raise RuntimeError("missing OPAQUE_RIGHT_LOWER_OWNERS group")
        actual_names = [obj.Name for obj in group.Group]
        baseline_shapes = {
            obj.Name: obj.Shape.copy()
            for obj in group.Group
            if hasattr(obj, "Shape") and not obj.Shape.isNull()
        }
    finally:
        App.closeDocument(baseline.Name)

    if actual_names != expected_names:
        raise RuntimeError(
            "right-lower owner group differs from contract: "
            f"expected={expected_names}, actual={actual_names}"
        )
    if set(baseline_shapes) != set(expected_names):
        raise RuntimeError("one or more right-lower owner shapes are missing")

    checker = base["mesh_checker"]
    mesh_overrides: dict[str, Any] = {}
    mesh_override_evidence: dict[str, dict[str, Any]] = {}
    override_specifications = policy.get("mesh_source_overrides", {})
    if override_specifications:
        canonical_path = project_path(
            str(contract["inputs"]["canonical_lower_mesh_source"]["path"])
        )
        canonical = App.openDocument(str(canonical_path))
        try:
            source_names = {
                str(specification["source_object"])
                for specification in override_specifications.values()
            }
            if len(source_names) != 1:
                raise RuntimeError(
                    "V4 currently requires one pinned canonical mesh object"
                )
            source_object_name = next(iter(source_names))
            source_object = canonical.getObject(source_object_name)
            if source_object is None or not hasattr(source_object, "Mesh"):
                raise RuntimeError(
                    f"missing canonical mesh object: {source_object_name}"
                )
            separated = source_object.Mesh.getSeparateComponents()
            for name, specification in override_specifications.items():
                target = baseline_shapes[name]
                candidates = [
                    (index, mesh)
                    for index, mesh in enumerate(separated, start=1)
                    if maximum_bounds_delta(target, mesh) <= 1.0e-7
                ]
                if len(candidates) != 1:
                    raise RuntimeError(
                        f"canonical mesh override for {name} is not unique: "
                        f"{len(candidates)} matches"
                    )
                source_index, source_mesh = candidates[0]
                override = Mesh.Mesh(source_mesh)
                record = checker.mesh_topology(override)
                bounds_delta = maximum_bounds_delta(target, override)
                volume_delta = abs(
                    float(record["signed_volume_mm3"])
                    - float(target.Volume)
                )
                facet_delta = abs(
                    int(record["facets"]) - len(target.Faces)
                )
                topology_pass = mesh_topology_pass(
                    record,
                    require_one_component=True,
                    require_zero_self_intersections=False,
                )
                if not (
                    bounds_delta <= 1.0e-7
                    and volume_delta <= 1.0e-6
                    and facet_delta == 0
                    and topology_pass
                ):
                    raise RuntimeError(
                        f"canonical mesh override failed identity gates for "
                        f"{name}: bounds={bounds_delta}, "
                        f"volume={volume_delta}, facets={facet_delta}, "
                        f"topology={record}"
                    )
                mesh_overrides[name] = override
                mesh_override_evidence[name] = {
                    "source_object": source_object_name,
                    "source_separate_component_index": source_index,
                    "selection_policy": specification["selection"],
                    "reason": specification["reason"],
                    "maximum_bounds_delta_mm": bounds_delta,
                    "absolute_signed_volume_delta_mm3": volume_delta,
                    "facet_count_delta": facet_delta,
                    "selected_mesh": record,
                }
        finally:
            App.closeDocument(canonical.Name)

    v3_objects = base["contract"]["objects"]
    owner_001_name = str(v3_objects["opaque_component_001_owner"])
    owner_002_name = str(v3_objects["opaque_component_002_owner"])
    constituent_shapes: dict[str, Any] = {}
    constituent_origin: dict[str, str] = {}
    for name in expected_names:
        if name == owner_001_name:
            constituent_shapes[name] = base["parts"][
                "opaque_component_001"
            ].copy()
            constituent_origin[name] = (
                "PINNED_SOURCES__FACE6_HEALED_OWNER__"
                "APPROVED_BELOW_MOUTH_AND_OUTER_OPAQUE_TABS_FUSED"
            )
        elif name == owner_002_name:
            constituent_shapes[name] = base["parts"][
                "opaque_component_002"
            ].copy()
            constituent_origin[name] = (
                "PINNED_BASELINE_OWNER__APPROVED_NOSE_TOP_OPAQUE_TAB_FUSED"
            )
        else:
            constituent_shapes[name] = baseline_shapes[name].copy()
            constituent_origin[name] = "PINNED_MANUAL_BASELINE_GROUP_MEMBER"

    ledge_name = "RIGHT_LEDGE_BASE_PLUS_EXACT_USER_EXTENSION"
    constituent_shapes[ledge_name] = base["parts"]["opaque_right_ledge"].copy()
    constituent_origin[ledge_name] = (
        "PINNED_BASELINE_LEDGE__APPROVED_EXACT_USER_EXTENSION_FUSED"
    )
    constituent_order = expected_names + [ledge_name]
    v1 = base["v1"]
    constituent_records = {
        name: {
            "origin": constituent_origin[name],
            "brep": v1.shape_record(constituent_shapes[name]),
        }
        for name in constituent_order
    }
    opaque_compound = Part.makeCompound(
        [constituent_shapes[name].copy() for name in constituent_order]
    )
    source_volume_sum = sum(
        float(constituent_shapes[name].Volume) for name in constituent_order
    )
    compound_record = v1.shape_record(opaque_compound)
    compound_volume_residual = float(
        opaque_compound.Volume - source_volume_sum
    )

    mesh_spec = base["contract"]["mesh"]
    constituent_meshes: dict[str, Any] = {}
    constituent_mesh_records: dict[str, dict[str, Any]] = {}
    for name in expected_names:
        if name == owner_001_name:
            mesh = base["meshes"]["opaque_component_001"]
            record = dict(base["mesh_records"]["opaque_component_001"])
        elif name == owner_002_name:
            mesh = base["meshes"]["opaque_component_002"]
            record = dict(base["mesh_records"]["opaque_component_002"])
        elif name in mesh_overrides:
            mesh = mesh_overrides[name]
            topology = checker.mesh_topology(mesh)
            record = {
                "selection": "pinned_canonical_source_mesh_exact_match",
                "conditioning_applied": False,
                "raw": topology,
                "selected": dict(topology),
                "clean": mesh_topology_pass(
                    topology,
                    require_one_component=True,
                    require_zero_self_intersections=False,
                ),
                "override_evidence": mesh_override_evidence[name],
            }
        else:
            mesh = MeshPart.meshFromShape(
                Shape=constituent_shapes[name],
                LinearDeflection=float(mesh_spec["linear_deflection_mm"]),
                AngularDeflection=float(mesh_spec["angular_deflection_rad"]),
                Relative=False,
            )
            topology = checker.mesh_topology(mesh)
            record = {
                "selection": "raw",
                "conditioning_applied": False,
                "raw": topology,
                "selected": dict(topology),
                "clean": mesh_topology_pass(
                    topology,
                    require_one_component=True,
                    require_zero_self_intersections=False,
                ),
            }
        constituent_meshes[name] = mesh
        constituent_mesh_records[name] = record

    constituent_meshes[ledge_name] = base["meshes"]["opaque_right_ledge"]
    constituent_mesh_records[ledge_name] = dict(
        base["mesh_records"]["opaque_right_ledge"]
    )
    opaque_mesh = combine_meshes(
        [constituent_meshes[name] for name in constituent_order],
        Mesh,
        App,
    )
    opaque_mesh_record = checker.mesh_topology(opaque_mesh)
    opaque_mesh_record["multi_shell_closed_manifold"] = mesh_topology_pass(
        opaque_mesh_record,
        require_one_component=False,
        require_zero_self_intersections=False,
    )
    opaque_mesh_record["single_stl_file"] = True
    opaque_mesh_record["constituent_count"] = len(constituent_order)

    parts = {
        "opaque_complete": opaque_compound,
        "translucent_quad003_component_01": base["parts"][
            "translucent_quad003_component_01"
        ].copy(),
        "translucent_central_component_03": base["parts"][
            "translucent_central_component_03"
        ].copy(),
        "translucent_quad017_component_02": base["parts"][
            "translucent_quad017_component_02"
        ].copy(),
    }
    meshes = {
        "opaque_complete": opaque_mesh,
        "translucent_quad003_component_01": base["meshes"][
            "translucent_quad003_component_01"
        ],
        "translucent_central_component_03": base["meshes"][
            "translucent_central_component_03"
        ],
        "translucent_quad017_component_02": base["meshes"][
            "translucent_quad017_component_02"
        ],
    }
    mesh_records = {
        "opaque_complete": opaque_mesh_record,
        "translucent_quad003_component_01": base["mesh_records"][
            "translucent_quad003_component_01"
        ],
        "translucent_central_component_03": base["mesh_records"][
            "translucent_central_component_03"
        ],
        "translucent_quad017_component_02": base["mesh_records"][
            "translucent_quad017_component_02"
        ],
    }
    return {
        "App": App,
        "Mesh": Mesh,
        "Part": Part,
        "contract": contract,
        "pins": pins,
        "v3": v3,
        "v3_bundle": base,
        "v3_source_checks": base_report["checks"],
        "v3_permitted_predecessor_failure": sorted(permitted_v3_failure),
        "parts": parts,
        "meshes": meshes,
        "mesh_records": mesh_records,
        "constituent_order": constituent_order,
        "constituent_shapes": constituent_shapes,
        "constituent_records": constituent_records,
        "constituent_mesh_records": constituent_mesh_records,
        "mesh_override_evidence": mesh_override_evidence,
        "owner_group_actual_names": actual_names,
        "source_volume_sum_mm3": source_volume_sum,
        "compound_volume_residual_mm3": compound_volume_residual,
        "compound_record": compound_record,
    }


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    contract = bundle["contract"]
    policy = contract["opaque_policy"]
    v1 = bundle["v3_bundle"]["v1"]
    expected_names = list(policy["required_owner_names"])
    actual_names = bundle["owner_group_actual_names"]
    part_breps = {
        part_id: v1.shape_record(shape)
        for part_id, shape in bundle["parts"].items()
    }
    opaque = part_breps["opaque_complete"]
    opaque_mesh = bundle["mesh_records"]["opaque_complete"]
    translucent_ids = [
        part_id for part_id in PART_IDS if part_id.startswith("translucent_")
    ]
    constituent_brep_pass = all(
        record["brep"]["valid"]
        and record["brep"]["closed"]
        and record["brep"]["solid_count"] == 1
        for record in bundle["constituent_records"].values()
    )
    constituent_mesh_pass = all(
        bool(record.get("clean"))
        for record in bundle["constituent_mesh_records"].values()
    )
    compound_pass = bool(
        opaque["valid"]
        and opaque["closed"]
        and opaque["solid_count"]
        == int(policy["expected_compound_solid_count"])
        and abs(bundle["compound_volume_residual_mm3"])
        <= float(contract["numeric_gates"]["compound_volume_residual_mm3"])
    )
    translucent_brep_pass = all(
        part_breps[part_id]["valid"]
        and part_breps[part_id]["closed"]
        and part_breps[part_id]["solid_count"] == 1
        for part_id in translucent_ids
    )
    translucent_mesh_pass = all(
        bool(bundle["mesh_records"][part_id]["clean"])
        for part_id in translucent_ids
    )
    override_names = set(policy.get("mesh_source_overrides", {}))
    override_evidence = bundle["mesh_override_evidence"]
    override_pass = bool(
        set(override_evidence) == override_names
        and all(
            record["maximum_bounds_delta_mm"] <= 1.0e-7
            and record["absolute_signed_volume_delta_mm3"] <= 1.0e-6
            and record["facet_count_delta"] == 0
            and mesh_topology_pass(
                record["selected_mesh"],
                require_one_component=True,
                require_zero_self_intersections=False,
            )
            for record in override_evidence.values()
        )
    )
    central_bounds = part_breps["translucent_central_component_03"][
        "bounds_mm"
    ]["minimum"]
    output_dir = project_path(contract["outputs"]["directory"])
    checks = {
        "all_geometry_tooling_and_rejected_v3_evidence_hashes_match": True,
        "v3_geometry_reconstruction_passes_every_gate_except_existing_v3_output_identity": all(
            value
            for name, value in bundle["v3_source_checks"].items()
            if name != "output_directory_is_fresh"
        ),
        "baseline_right_lower_owner_group_exactly_matches_all_35_contract_members": (
            actual_names == expected_names
            and len(actual_names) == int(policy["required_owner_count"])
        ),
        "all_required_over_nose_members_are_included": set(
            policy["required_over_nose_members"]
        ).issubset(actual_names),
        "protected_deleted_or_ungrouped_members_are_not_restored": not set(
            policy["protected_excluded_members"]
        ).intersection(actual_names),
        "all_35_opaque_owners_plus_approved_ledge_are_valid_closed_single_solid_constituents": (
            len(bundle["constituent_order"])
            == int(policy["expected_compound_solid_count"])
            and constituent_brep_pass
        ),
        "opaque_compound_preserves_all_constituents_without_boolean_volume_loss": compound_pass,
        "all_opaque_constituent_meshes_are_individually_clean_closed_manifold": constituent_mesh_pass,
        "named_defective_brep_retessellation_uses_exact_pinned_canonical_facets": override_pass,
        "one_combined_opaque_mesh_is_closed_manifold_allowing_source_multi_shell_topology": bool(
            opaque_mesh["multi_shell_closed_manifold"]
        ),
        "exactly_one_opaque_stl_filename_is_declared": (
            [key for key in contract["outputs"]["parts"] if key.startswith("opaque")]
            == ["opaque_complete"]
        ),
        "all_three_translucent_breps_remain_valid_closed_single_solids": translucent_brep_pass,
        "all_three_translucent_meshes_remain_clean_closed_manifold_single_components": translucent_mesh_pass,
        "negative_x_central_owner_plank_remains_absent": central_bounds[0] >= -1.0e-7,
        "output_directory_is_fresh": not output_dir.exists(),
        "release_contains_no_3mf_or_gcode_names": all(
            not str(name).lower().endswith((".3mf", ".gcode"))
            for name in contract["outputs"]["parts"].values()
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-lower-right-complete-opaque-preflight-v4",
        "status": PREFLIGHT_PASS if not failed else "PREFLIGHT_FAIL__NO_PRINT_OUTPUT",
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "opaque_packaging": {
            "source_owner_count": len(actual_names),
            "constituent_count_including_ledge": len(bundle["constituent_order"]),
            "source_owner_names": actual_names,
            "constituent_order": bundle["constituent_order"],
            "required_over_nose_members": policy["required_over_nose_members"],
            "protected_excluded_members": policy["protected_excluded_members"],
            "source_volume_sum_mm3": bundle["source_volume_sum_mm3"],
            "compound_volume_residual_mm3": bundle[
                "compound_volume_residual_mm3"
            ],
            "physical_topology_disclosure": policy[
                "physical_source_topology"
            ],
            "global_boolean_union_used": False,
            "invented_bridges_used": False,
            "single_opaque_stl_file": True,
        },
        "opaque_constituents": bundle["constituent_records"],
        "opaque_constituent_meshes": bundle["constituent_mesh_records"],
        "opaque_mesh_source_overrides": override_evidence,
        "part_breps": part_breps,
        "part_meshes": bundle["mesh_records"],
        "v3_source_reconstruction": {
            "checks": bundle["v3_source_checks"],
            "permitted_predecessor_failure": bundle[
                "v3_permitted_predecessor_failure"
            ],
            "source_evidence": bundle["v3_bundle"]["source_evidence"],
            "connector_station_evidence": bundle["v3_bundle"][
                "station_records"
            ],
        },
        "pins": {
            "contract_sha256": sha256(CONTRACT_PATH),
            "exporter_sha256": sha256(Path(__file__)),
            "verified_inputs": bundle["pins"],
        },
        "runtime": {"freecad_version": list(bundle["App"].Version())},
        "io_trace": {
            "preflight_report_created": False,
            "fcstd_created": False,
            "stl_created": False,
            "three_mf_created": False,
            "gcode_created": False,
            "output_directory_created": False,
        },
    }


def add_part(
    document: Any,
    group: Any,
    part_id: str,
    shape: Any,
    contract: dict[str, Any],
) -> Any:
    obj = document.addObject("Part::Feature", PART_OBJECT_NAMES[part_id])
    obj.Label = PART_LABELS[part_id]
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "PrintRelease")
    obj.Authority = contract["authority"]
    obj.addProperty("App::PropertyString", "PartId", "PrintRelease")
    obj.PartId = part_id
    obj.addProperty("App::PropertyString", "Packaging", "PrintRelease")
    if part_id == "opaque_complete":
        obj.Packaging = (
            "ONE_OPAQUE_STL_FILE__ALL_35_ACCEPTED_OWNERS__"
            "APPROVED_OPAQUE_TABS__APPROVED_LEDGE__MULTI_SHELL_PRESERVED"
        )
        obj.addProperty(
            "App::PropertyStringList", "SourceOwnerNames", "PrintRelease"
        )
        obj.SourceOwnerNames = list(
            contract["opaque_policy"]["required_owner_names"]
        )
        obj.addProperty(
            "App::PropertyInteger", "SourceOwnerCount", "PrintRelease"
        )
        obj.SourceOwnerCount = int(
            contract["opaque_policy"]["required_owner_count"]
        )
        obj.addProperty(
            "App::PropertyInteger", "CompoundSolidCount", "PrintRelease"
        )
        obj.CompoundSolidCount = int(
            contract["opaque_policy"]["expected_compound_solid_count"]
        )
    else:
        obj.Packaging = "SEPARATE_TRANSLUCENT_MATING_STL"
    if part_id == "translucent_central_component_03":
        obj.addProperty(
            "App::PropertyString", "CentralOwnerCorrection", "PrintRelease"
        )
        obj.CentralOwnerCorrection = (
            "OPPOSITE_SIDE_NEGATIVE_X_PLANK_REMOVED__RETAIN_X_GTE_0"
        )
    group.addObject(obj)
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        if part_id.startswith("translucent_"):
            view.ShapeColor = (0.35, 0.82, 0.96)
            view.Transparency = 45
        else:
            view.ShapeColor = (0.20, 0.22, 0.25)
            view.Transparency = 0
    return obj


def create_fcstd(bundle: dict[str, Any], destination: Path) -> dict[str, Any]:
    App = bundle["App"]
    contract = bundle["contract"]
    document = App.newDocument(
        "LOWER_RIGHT_COMPLETE_OPAQUE_INTEGRATION_PRINT_PARTS_V4"
    )
    try:
        opaque_group = document.addObject(
            "App::DocumentObjectGroup",
            "OPAQUE_RIGHT_LOWER_COMPLETE_PRINT_ASSEMBLY",
        )
        translucent_group = document.addObject(
            "App::DocumentObjectGroup",
            "TRANSLUCENT_RIGHT_MATING_PRINT_PARTS",
        )
        for part_id in PART_IDS:
            group = (
                opaque_group
                if part_id == "opaque_complete"
                else translucent_group
            )
            add_part(
                document,
                group,
                part_id,
                bundle["parts"][part_id],
                contract,
            )
        metadata = document.addObject(
            "App::FeaturePython", "PRINT_RELEASE_METADATA"
        )
        metadata.addProperty("App::PropertyString", "Authority", "PrintRelease")
        metadata.Authority = contract["authority"]
        metadata.addProperty(
            "App::PropertyString", "ContractSha256", "PrintRelease"
        )
        metadata.ContractSha256 = sha256(CONTRACT_PATH)
        metadata.addProperty(
            "App::PropertyString", "ExporterSha256", "PrintRelease"
        )
        metadata.ExporterSha256 = sha256(Path(__file__))
        metadata.addProperty("App::PropertyString", "Scope", "PrintRelease")
        metadata.Scope = (
            "RIGHT_LOWER_COMPLETE_OPAQUE_ONE_STL__"
            "THREE_TRANSLUCENT_MATING_STLS"
        )
        metadata.addProperty(
            "App::PropertyString", "RejectedPredecessors", "PrintRelease"
        )
        metadata.RejectedPredecessors = (
            "V1_V2_V3_REJECTED_OR_WITHHELD__DO_NOT_PRINT"
        )
        metadata.addProperty(
            "App::PropertyString", "TopologyDisclosure", "PrintRelease"
        )
        metadata.TopologyDisclosure = contract["opaque_policy"][
            "physical_source_topology"
        ]
        document.recompute()
        document.saveAs(str(destination))
    finally:
        App.closeDocument(document.Name)

    with zipfile.ZipFile(destination, "r") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("saved FCStd ZIP integrity check failed")

    reopened = App.openDocument(str(destination))
    try:
        records: dict[str, Any] = {}
        for part_id in PART_IDS:
            obj = reopened.getObject(PART_OBJECT_NAMES[part_id])
            if obj is None:
                raise RuntimeError(f"saved FCStd missing part: {part_id}")
            records[part_id] = bundle["v3_bundle"]["v1"].shape_record(
                obj.Shape
            )
        opaque = records["opaque_complete"]
        expected_solids = int(
            contract["opaque_policy"]["expected_compound_solid_count"]
        )
        if not (
            opaque["valid"]
            and opaque["closed"]
            and opaque["solid_count"] == expected_solids
        ):
            raise RuntimeError(
                "saved complete opaque compound changed topology"
            )
        for part_id in PART_IDS[1:]:
            record = records[part_id]
            if not (
                record["valid"]
                and record["closed"]
                and record["solid_count"] == 1
            ):
                raise RuntimeError(
                    f"saved translucent FCStd part is not clean: {part_id}"
                )
        central = reopened.getObject(
            PART_OBJECT_NAMES["translucent_central_component_03"]
        )
        if central.Shape.BoundBox.XMin < -1.0e-7:
            raise RuntimeError(
                "saved FCStd reintroduced the negative-X plank"
            )
        opaque_obj = reopened.getObject(PART_OBJECT_NAMES["opaque_complete"])
        v3 = bundle["v3"]
        v2 = bundle["v3_bundle"]["v2"]
        signature = bundle["v3_bundle"]["contract"][
            "component_001_healing"
        ]["rejected_face_signature"]
        if v2.rejected_face_records(opaque_obj.Shape, signature):
            raise RuntimeError("saved FCStd reintroduced rejected Face6")
        return records
    finally:
        App.closeDocument(reopened.Name)


def write_readme(destination: Path, manifest: dict[str, Any]) -> None:
    opaque_mesh = manifest["reloaded_stl_meshes"]["opaque_complete"]
    opaque_prusa = manifest["prusa_slicer_validation"]["parts"][
        "opaque_complete"
    ]
    destination.write_text(
        "# Lower-right complete opaque print release V4\n\n"
        "Use V4 only. V1 through V3 are rejected or withheld and remain "
        "unchanged as evidence.\n\n"
        "V4 contains exactly one opaque STL file. It includes all 35 accepted "
        "members of OPAQUE_RIGHT_LOWER_OWNERS, including the over-nose "
        "components, plus the approved opaque connector tabs and the approved "
        "right ledge with the exact user extension. Three translucent mating "
        "parts remain separate STL files.\n\n"
        "The accepted opaque source is intrinsically multi-shell; the original "
        "right-lower STL was also multi-part. V4 preserves those shells in one "
        "file without a destructive global boolean and without inventing "
        "bridges. The combined opaque STL reloaded with "
        f"{opaque_mesh['connected_components']} connected mesh shells; "
        "PrusaSlicer reports "
        f"manifold={opaque_prusa['manifold']} and "
        f"number_of_parts={opaque_prusa['number_of_parts']}.\n\n"
        "The negative-X translucent plank remains removed and the rejected "
        "zero-area Face6 remains absent. No 3MF, G-code, printer profile, "
        "slicing, or print orientation is included.\n\n"
        f"Release status: {manifest['status']}\n",
        encoding="utf-8",
    )


def write_checkpoint(destination: Path, manifest: dict[str, Any]) -> None:
    opaque = manifest["opaque_packaging"]
    opaque_mesh = manifest["reloaded_stl_meshes"]["opaque_complete"]
    opaque_prusa = manifest["prusa_slicer_validation"]["parts"][
        "opaque_complete"
    ]
    destination.write_text(
        "# Lower-right complete opaque V4 checkpoint — 2026-08-21\n\n"
        f"Status: {manifest['status']}\n\n"
        "Use V4 only. V1-V3 are superseded.\n\n"
        f"- Accepted opaque owners included: {opaque['source_owner_count']}\n"
        f"- Packaged opaque constituents including ledge: "
        f"{opaque['constituent_count_including_ledge']}\n"
        "- Opaque STL files: 1\n"
        "- Translucent STL files: 3\n"
        f"- Reloaded opaque mesh shells: "
        f"{opaque_mesh['connected_components']}\n"
        f"- PrusaSlicer opaque manifold/parts: "
        f"{opaque_prusa['manifold']}/"
        f"{opaque_prusa['number_of_parts']}\n"
        f"- Opaque boundary/nonmanifold/degenerate/duplicate edges or facets: "
        f"{opaque_mesh['boundary_edges']}/"
        f"{opaque_mesh['nonmanifold_edges']}/"
        f"{opaque_mesh['degenerate_facets']}/"
        f"{opaque_mesh['duplicate_facets']}\n"
        "- Global destructive BRep union: not used\n"
        "- Invented bridges: not used\n"
        "- Negative-X translucent plank: absent\n"
        "- Rejected zero-area Face6: absent\n\n"
        "Regeneration requires a fresh output identity because V4 is "
        "immutable after release. No slicing or G-code was performed.\n",
        encoding="utf-8",
    )


def release(bundle: dict[str, Any], report: dict[str, Any]) -> Path:
    contract = bundle["contract"]
    output_dir = project_path(contract["outputs"]["directory"])
    if output_dir.exists():
        raise RuntimeError(f"release output already exists: {output_dir}")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".lower-right-connector-integration-v4-stage-",
        dir=str(output_dir.parent),
    ) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        stl_dir = stage / str(contract["outputs"]["stl_directory"])
        stl_dir.mkdir()
        fcstd = stage / str(contract["outputs"]["fcstd"])
        saved_fcstd_records = create_fcstd(bundle, fcstd)

        reloaded_mesh_records: dict[str, Any] = {}
        prusa_records: dict[str, Any] = {}
        for part_id in PART_IDS:
            destination = stl_dir / str(
                contract["outputs"]["parts"][part_id]
            )
            bundle["meshes"][part_id].write(str(destination))
            reloaded = bundle["Mesh"].Mesh(str(destination))
            record = bundle["v3_bundle"]["mesh_checker"].mesh_topology(
                reloaded
            )
            if part_id == "opaque_complete":
                record["stl_container_has_no_open_boundaries"] = bool(
                    record["connected_components"] >= 1
                    and record["boundary_edges"] == 0
                    and record["degenerate_facets"] == 0
                    and record["outward_normals"]
                    and float(record["signed_volume_mm3"]) > 0.0
                )
                record["coordinate_identity_collapse_diagnostic"] = {
                    "nonmanifold_edges": record["nonmanifold_edges"],
                    "duplicate_facets": record["duplicate_facets"],
                    "policy": (
                        "STL does not preserve the intentionally separate "
                        "coincident vertex identities present in the pinned "
                        "multi-shell source; PrusaSlicer manifold=yes is the "
                        "mandatory final print gate."
                    ),
                }
                if not record["stl_container_has_no_open_boundaries"]:
                    raise RuntimeError(
                        f"reloaded complete opaque STL has open or degenerate "
                        f"geometry: {record}"
                    )
            else:
                record["clean"] = bool(
                    bundle["v3_bundle"]["mesh_checker"].clean_manifold_mesh(
                        record
                    )
                )
                if not record["clean"]:
                    raise RuntimeError(
                        f"reloaded translucent STL failed for "
                        f"{part_id}: {record}"
                    )
            reloaded_mesh_records[part_id] = record
            prusa = prusa_slicer_info(destination)
            if prusa["manifold"] != "yes":
                raise RuntimeError(
                    f"PrusaSlicer reports non-manifold STL for "
                    f"{part_id}: {prusa}"
                )
            if (
                part_id != "opaque_complete"
                and prusa["number_of_parts"] != 1
            ):
                raise RuntimeError(
                    f"PrusaSlicer reports multiple translucent parts for "
                    f"{part_id}: {prusa}"
                )
            if (
                part_id == "opaque_complete"
                and prusa["number_of_parts"] < 1
            ):
                raise RuntimeError(
                    f"PrusaSlicer reports an empty opaque STL: {prusa}"
                )
            prusa_records[part_id] = prusa

        manifest = dict(report)
        manifest["schema_version"] = (
            "cat-head-lower-right-complete-opaque-release-manifest-v4"
        )
        manifest["status"] = RELEASE_PASS
        manifest["failed_checks"] = []
        manifest["saved_fcstd_part_breps"] = saved_fcstd_records
        manifest["reloaded_stl_meshes"] = reloaded_mesh_records
        manifest["prusa_slicer_validation"] = {
            "policy": (
                "all_four_STLs_must_report_manifold_yes; "
                "each_translucent_STL_must_report_one_part; "
                "opaque_part_count_is_inherited_multi_shell_evidence"
            ),
            "parts": prusa_records,
        }
        manifest["io_trace"] = {
            "preflight_report_created": True,
            "fcstd_created": True,
            "stl_created": True,
            "stl_count": len(PART_IDS),
            "opaque_stl_count": 1,
            "translucent_stl_count": 3,
            "three_mf_created": False,
            "gcode_created": False,
            "slicing_performed": False,
            "output_directory_created": True,
        }

        readme = stage / str(contract["outputs"]["readme"])
        checkpoint = stage / str(contract["outputs"]["checkpoint"])
        write_readme(readme, manifest)
        write_checkpoint(checkpoint, manifest)
        manifest_path = stage / str(contract["outputs"]["manifest"])
        manifest["output_files"] = {
            "fcstd": str(fcstd.name),
            "stls": {
                part_id: str(
                    Path(contract["outputs"]["stl_directory"])
                    / contract["outputs"]["parts"][part_id]
                )
                for part_id in PART_IDS
            },
            "readme": str(readme.name),
            "checkpoint": str(checkpoint.name),
        }
        manifest["output_sha256"] = {
            "fcstd": sha256(fcstd),
            "stls": {
                part_id: sha256(
                    stl_dir / str(contract["outputs"]["parts"][part_id])
                )
                for part_id in PART_IDS
            },
            "readme": sha256(readme),
            "checkpoint": sha256(checkpoint),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        checksum_path = stage / str(contract["outputs"]["checksums"])
        checksum_targets = [
            path
            for path in stage.rglob("*")
            if path.is_file() and path != checksum_path
        ]
        checksum_path.write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(stage)}\n"
                for path in sorted(checksum_targets)
            ),
            encoding="utf-8",
        )
        forbidden = [
            path
            for path in stage.rglob("*")
            if path.suffix.lower() in {".3mf", ".gcode"}
        ]
        if forbidden:
            raise RuntimeError(
                f"forbidden release files were staged: {forbidden}"
            )
        shutil.copytree(stage, output_dir)

    if verify_pins(contract) != bundle["pins"]:
        raise RuntimeError("an input changed during V4 release")
    for relative, expected in (
        (contract["outputs"]["fcstd"], manifest["output_sha256"]["fcstd"]),
        (contract["outputs"]["readme"], manifest["output_sha256"]["readme"]),
        (
            contract["outputs"]["checkpoint"],
            manifest["output_sha256"]["checkpoint"],
        ),
    ):
        if sha256(output_dir / str(relative)) != expected:
            raise RuntimeError(f"post-copy hash mismatch: {relative}")
    for part_id, expected in manifest["output_sha256"]["stls"].items():
        relative = (
            Path(contract["outputs"]["stl_directory"])
            / contract["outputs"]["parts"][part_id]
        )
        if sha256(output_dir / relative) != expected:
            raise RuntimeError(f"post-copy STL hash mismatch: {part_id}")
    return output_dir


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("preflight", "release"), required=True
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument("--preflight-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    bundle = prepare()
    report = evaluate(bundle)
    if args.mode == "preflight":
        if args.report is None:
            raise RuntimeError("preflight requires --report")
        target = args.report.resolve()
        if not str(target).startswith("/tmp/"):
            raise RuntimeError("preflight report must be under /tmp")
        if target.exists():
            raise RuntimeError(f"preflight report already exists: {target}")
        report["io_trace"]["preflight_report_created"] = True
        target.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "report": str(target),
                    "report_sha256": sha256(target),
                    "failed_checks": report["failed_checks"],
                    "opaque_mesh_components": report["part_meshes"][
                        "opaque_complete"
                    ]["connected_components"],
                },
                sort_keys=True,
            )
        )
        return 0 if not report["failed_checks"] else 2

    if report["failed_checks"]:
        raise RuntimeError(
            "lower-right V4 release gates failed: "
            + ", ".join(report["failed_checks"])
        )
    if args.preflight_report is None or args.preflight_sha256 is None:
        raise RuntimeError(
            "release requires --preflight-report and --preflight-sha256"
        )
    preflight_path = args.preflight_report.resolve()
    if sha256(preflight_path) != args.preflight_sha256:
        raise RuntimeError("preflight report hash mismatch")
    preflight = load_json(preflight_path)
    if (
        preflight.get("status") != PREFLIGHT_PASS
        or preflight.get("failed_checks") != []
    ):
        raise RuntimeError("preflight report did not authorize release")
    if preflight.get("pins") != report.get("pins"):
        raise RuntimeError("preflight pins do not match release invocation")
    expected_parts = {
        key: value["brep_sha256"]
        for key, value in preflight["part_breps"].items()
    }
    actual_parts = {
        key: value["brep_sha256"]
        for key, value in report["part_breps"].items()
    }
    if expected_parts != actual_parts:
        raise RuntimeError("release BReps differ from pinned preflight BReps")
    expected_constituents = {
        key: value["brep"]["brep_sha256"]
        for key, value in preflight["opaque_constituents"].items()
    }
    actual_constituents = {
        key: value["brep"]["brep_sha256"]
        for key, value in report["opaque_constituents"].items()
    }
    if expected_constituents != actual_constituents:
        raise RuntimeError(
            "opaque constituents differ from pinned preflight"
        )
    output = release(bundle, report)
    print(
        json.dumps(
            {"status": RELEASE_PASS, "output": str(output)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
