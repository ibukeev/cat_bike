#!/usr/bin/env python3
"""Create the corrected lower-right connector print release V2.

V1 remains immutable visual-rejection evidence. V2 makes only the two
user-requested corrections: trim 2 mm from the free end of both nose-top
mating tabs, and remove the long zero-area Face6 from opaque component 001
with a fixed native OCCT small-strip healing operation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
V1_EXPORTER_PATH = HERE.parent / "lower-right-connector-integration-v1" / "export_release.py"
SCHEMA = "cat-head-lower-right-connector-integration-print-release-v2"
PREFLIGHT_PASS = "PREFLIGHT_PASS__LOWER_RIGHT_V2_CORRECTION_RELEASE_ALLOWED"
RELEASE_PASS = "PRINT_RELEASE_PASS__V2_CORRECTED_FCSTD_AND_SIX_STLS_READY"

PART_IDS = (
    "opaque_component_001",
    "opaque_component_002",
    "opaque_right_ledge",
    "translucent_quad003_component_01",
    "translucent_central_component_03",
    "translucent_quad017_component_02",
)

PART_OBJECT_NAMES = {
    "opaque_component_001": "RIGHT_LOWER_OPAQUE_COMPONENT_001_WITH_BELOW_MOUTH_OUTER_TABS_PRINT",
    "opaque_component_002": "RIGHT_LOWER_OPAQUE_COMPONENT_002_WITH_NOSE_TOP_TAB_PRINT",
    "opaque_right_ledge": "RIGHT_LOWER_LEDGE_WITH_USER_EXTENSION_PRINT",
    "translucent_quad003_component_01": "RIGHT_TRANSLUCENT_QUAD003_COMPONENT_01_WITH_BELOW_MOUTH_TAB_PRINT",
    "translucent_central_component_03": "RIGHT_TRANSLUCENT_CENTRAL_CLUSTER_COMPONENT_03_WITH_NOSE_TOP_TAB_PRINT",
    "translucent_quad017_component_02": "RIGHT_TRANSLUCENT_QUAD017_COMPONENT_02_WITH_OUTER_TAB_PRINT",
}

PART_LABELS = {
    "opaque_component_001": "RIGHT LOWER — OPAQUE COMPONENT 001 — BELOW-MOUTH + OUTER TABS — FACE6 REMOVED — PRINT",
    "opaque_component_002": "RIGHT LOWER — OPAQUE COMPONENT 002 — TRIMMED NOSE-TOP TAB — PRINT",
    "opaque_right_ledge": "RIGHT LOWER — LEDGE + USER EXTENSION — PRINT",
    "translucent_quad003_component_01": "RIGHT LOWER — TRANSLUCENT QUAD003 COMPONENT 01 — BELOW-MOUTH TAB — PRINT",
    "translucent_central_component_03": "RIGHT LOWER — TRANSLUCENT CENTRAL CLUSTER COMPONENT 03 — TRIMMED NOSE-TOP TAB — PRINT",
    "translucent_quad017_component_02": "RIGHT LOWER — TRANSLUCENT QUAD017 COMPONENT 02 — OUTER TAB — PRINT",
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
        raise RuntimeError("unexpected V2 lower-right print-release schema")
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


def normalized(App: Any, values: Sequence[float]) -> Any:
    vector = App.Vector(*map(float, values))
    vector.normalize()
    return vector


def oriented_box(
    App: Any,
    Part: Any,
    u: Any,
    v: Any,
    g: Any,
    origin: Any,
    length: float,
    depth: float,
    thickness: float,
) -> Any:
    matrix = App.Matrix()
    matrix.A11, matrix.A21, matrix.A31 = u.x, u.y, u.z
    matrix.A12, matrix.A22, matrix.A32 = v.x, v.y, v.z
    matrix.A13, matrix.A23, matrix.A33 = g.x, g.y, g.z
    matrix.A14, matrix.A24, matrix.A34 = origin.x, origin.y, origin.z
    return Part.makeBox(length, depth, thickness).transformGeometry(matrix)


def make_nose_pair(
    App: Any,
    Part: Any,
    specification: dict[str, Any],
    depth: float,
) -> tuple[Any, Any, dict[str, Any]]:
    u = normalized(App, specification["edge_axis"])
    v = normalized(App, specification["inward_axis"])
    g = normalized(App, specification["mating_normal"])
    root = App.Vector(*map(float, specification["root_point_mm"]))
    length = float(specification["length_along_edge_mm"])
    thickness = float(specification["thickness_mm"])
    shift = float(specification["common_mating_normal_shift_mm"])
    opaque_origin = root - u * (length / 2.0) + g * (0.15 + shift)
    translucent_origin = root - u * (length / 2.0) + g * (-3.15 + shift)
    opaque = oriented_box(
        App, Part, u, v, g, opaque_origin, length, depth, thickness
    )
    translucent = oriented_box(
        App, Part, u, v, g, translucent_origin, length, depth, thickness
    )
    hole_center_depth = float(specification["hole_center_depth_from_root_mm"])
    hole_radius = float(specification["hole_radius_mm"])
    hole_center = root + v * hole_center_depth + g * shift
    cutter = Part.makeCylinder(hole_radius, 10.0, hole_center - g * 5.0, g)
    return (
        opaque.cut(cutter),
        translucent.cut(cutter),
        {
            "depth_mm": depth,
            "hole_center_depth_from_root_mm": float((hole_center - root).dot(v)),
            "end_wall_mm": depth - hole_center_depth - hole_radius,
            "hole_center_mm": [
                float(hole_center.x),
                float(hole_center.y),
                float(hole_center.z),
            ],
        },
    )


def heal_component_001(
    Part: Any,
    shape: Any,
    specification: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    fixer = Part.ShapeFix.FixSmallFace()
    fixer.init(shape)
    fixer.Precision = float(specification["precision_mm"])
    fixer.MinTolerance = float(specification["minimum_tolerance_mm"])
    fixer.MaxTolerance = float(specification["maximum_tolerance_mm"])
    operation_result = bool(fixer.fixStripFace(True))
    return fixer.shape(), {
        "algorithm": str(specification["algorithm"]),
        "operation_result": operation_result,
        "precision_mm": float(specification["precision_mm"]),
        "minimum_tolerance_mm": float(specification["minimum_tolerance_mm"]),
        "maximum_tolerance_mm": float(specification["maximum_tolerance_mm"]),
    }


def rejected_face_records(
    shape: Any,
    signature: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, face in enumerate(shape.Faces, 1):
        box = face.BoundBox
        if (
            float(face.Area) < float(signature["maximum_area_mm2"])
            and float(box.XMax) < float(signature["maximum_x_mm"])
            and float(box.YLength) > float(signature["minimum_y_span_mm"])
            and float(box.ZLength) > float(signature["minimum_z_span_mm"])
        ):
            records.append(
                {
                    "face_index": index,
                    "area_mm2": float(face.Area),
                    "bounds_mm": {
                        "minimum": [
                            float(box.XMin),
                            float(box.YMin),
                            float(box.ZMin),
                        ],
                        "maximum": [
                            float(box.XMax),
                            float(box.YMax),
                            float(box.ZMax),
                        ],
                        "size": [
                            float(box.XLength),
                            float(box.YLength),
                            float(box.ZLength),
                        ],
                    },
                    "edge_lengths_mm": sorted(
                        float(edge.Length) for edge in face.Edges
                    ),
                }
            )
    return records


def prepare() -> dict[str, Any]:
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import MeshPart  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    pins = verify_pins(contract)
    v1 = load_module(V1_EXPORTER_PATH, "_lower_right_release_v1_helpers")
    objects = contract["objects"]
    input_paths = {
        key: project_path(str(contract["inputs"][key]["path"]))
        for key in (
            "manual_baseline",
            "validated_closed_component_001_source",
            "approved_connector_v2",
            "approved_ledge_v2",
        )
    }
    documents = {
        key: App.openDocument(str(path)) for key, path in input_paths.items()
    }
    try:
        def copied(document_key: str, object_key: str) -> Any:
            name = str(objects[object_key])
            obj = documents[document_key].getObject(name)
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"missing source shape: {document_key}.{name}")
            return obj.Shape.copy()

        current_owner_001 = copied("manual_baseline", "opaque_component_001_owner")
        repair_owner_001 = copied(
            "validated_closed_component_001_source",
            "opaque_component_001_owner",
        )
        owner_002 = copied("manual_baseline", "opaque_component_002_owner")
        ledge_base = copied("manual_baseline", "right_ledge_base")
        current_ledge_extension = copied(
            "manual_baseline", "right_ledge_extension"
        )
        approved_ledge_extension = copied(
            "approved_ledge_v2", "right_ledge_extension"
        )
        translucent_owners = {
            "below_mouth": copied(
                "manual_baseline", "below_mouth_translucent_owner"
            ),
            "nose_top": copied(
                "manual_baseline", "nose_top_translucent_owner"
            ),
            "outer_panel": copied(
                "manual_baseline", "outer_panel_translucent_owner"
            ),
        }
        source_tabs = {
            "below_mouth": {
                "opaque": copied(
                    "approved_connector_v2", "below_mouth_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "below_mouth_translucent_tab"
                ),
            },
            "nose_top": {
                "opaque": copied(
                    "approved_connector_v2", "nose_top_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "nose_top_translucent_tab"
                ),
            },
            "outer_panel": {
                "opaque": copied(
                    "approved_connector_v2", "outer_panel_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "outer_panel_translucent_tab"
                ),
            },
        }
    finally:
        for document in reversed(list(documents.values())):
            App.closeDocument(document.Name)

    owner_001, healing = heal_component_001(
        Part, repair_owner_001, contract["component_001_healing"]
    )
    signature = contract["component_001_healing"]["rejected_face_signature"]
    healing.update(
        {
            "source": v1.shape_record(repair_owner_001),
            "corrected": v1.shape_record(owner_001),
            "symmetric_difference": v1.symmetric_difference(
                repair_owner_001, owner_001
            ),
            "absolute_volume_delta_mm3": abs(
                float(repair_owner_001.Volume) - float(owner_001.Volume)
            ),
            "topology_delta": {
                "faces": len(owner_001.Faces) - len(repair_owner_001.Faces),
                "edges": len(owner_001.Edges) - len(repair_owner_001.Edges),
                "vertices": len(owner_001.Vertexes)
                - len(repair_owner_001.Vertexes),
            },
            "rejected_face_before": rejected_face_records(
                repair_owner_001, signature
            ),
            "rejected_face_after": rejected_face_records(owner_001, signature),
        }
    )

    nose_specification = contract["nose_top_trim"]
    source_depth = float(nose_specification["source_depth_mm"])
    corrected_depth = float(nose_specification["corrected_depth_mm"])
    nose_opaque_10, nose_translucent_10, _ = make_nose_pair(
        App, Part, nose_specification, source_depth
    )
    nose_opaque_8, nose_translucent_8, nose_dimensions = make_nose_pair(
        App, Part, nose_specification, corrected_depth
    )
    nose_evidence = {
        "source_reconstruction": {
            "opaque": v1.symmetric_difference(
                source_tabs["nose_top"]["opaque"], nose_opaque_10
            ),
            "translucent": v1.symmetric_difference(
                source_tabs["nose_top"]["translucent"],
                nose_translucent_10,
            ),
        },
        "source_depth_mm": source_depth,
        "corrected_depth_mm": corrected_depth,
        "removed_free_end_mm": source_depth - corrected_depth,
        "hole_center_depth_from_root_mm": nose_dimensions[
            "hole_center_depth_from_root_mm"
        ],
        "end_wall_mm": nose_dimensions["end_wall_mm"],
        "hole_center_mm": nose_dimensions["hole_center_mm"],
        "removed_source_volume_mm3": {
            "opaque": float(
                source_tabs["nose_top"]["opaque"].Volume
                - nose_opaque_8.Volume
            ),
            "translucent": float(
                source_tabs["nose_top"]["translucent"].Volume
                - nose_translucent_8.Volume
            ),
        },
        "corrected_source_shapes": {
            "opaque": v1.shape_record(nose_opaque_8),
            "translucent": v1.shape_record(nose_translucent_8),
        },
    }
    source_tabs["nose_top"] = {
        "opaque": nose_opaque_8,
        "translucent": nose_translucent_8,
    }

    opaque_owners = {
        "below_mouth": owner_001,
        "nose_top": owner_002,
        "outer_panel": owner_001,
    }
    conditioned_tabs: dict[str, dict[str, Any]] = {}
    station_records: dict[str, dict[str, Any]] = {}
    for station in ("below_mouth", "nose_top", "outer_panel"):
        opaque_owner = opaque_owners[station]
        translucent_owner = translucent_owners[station]
        opaque_source = source_tabs[station]["opaque"]
        translucent_source = source_tabs[station]["translucent"]
        opaque_tab = v1.condition_tab(opaque_source, translucent_owner)
        translucent_tab = v1.condition_tab(
            translucent_source, opaque_owner
        )
        conditioned_tabs[station] = {
            "opaque": opaque_tab,
            "translucent": translucent_tab,
        }
        station_records[station] = {
            "opaque_source_volume_mm3": float(opaque_source.Volume),
            "opaque_conditioned_volume_mm3": float(opaque_tab.Volume),
            "opaque_removed_cross_owner_mm3": max(
                0.0, float(opaque_source.Volume - opaque_tab.Volume)
            ),
            "translucent_source_volume_mm3": float(
                translucent_source.Volume
            ),
            "translucent_conditioned_volume_mm3": float(
                translucent_tab.Volume
            ),
            "translucent_removed_cross_owner_mm3": max(
                0.0,
                float(translucent_source.Volume - translucent_tab.Volume),
            ),
            "opaque_conditioned_to_opposite_owner_mm3": v1.common_volume(
                opaque_tab, translucent_owner
            ),
            "translucent_conditioned_to_opposite_owner_mm3": v1.common_volume(
                translucent_tab, opaque_owner
            ),
            "opaque_intended_owner_overlap_mm3": v1.common_volume(
                opaque_tab, opaque_owner
            ),
            "translucent_intended_owner_overlap_mm3": v1.common_volume(
                translucent_tab, translucent_owner
            ),
            "tab_pair_intersection_mm3": v1.common_volume(
                opaque_tab, translucent_tab
            ),
            "tab_pair_clearance_mm": float(
                opaque_tab.distToShape(translucent_tab)[0]
            ),
            "opaque_tab": v1.shape_record(opaque_tab),
            "translucent_tab": v1.shape_record(translucent_tab),
        }

    parts = {
        "opaque_component_001": v1.fuse_many(
            [
                owner_001,
                conditioned_tabs["below_mouth"]["opaque"],
                conditioned_tabs["outer_panel"]["opaque"],
            ]
        ),
        "opaque_component_002": v1.fuse_many(
            [owner_002, conditioned_tabs["nose_top"]["opaque"]]
        ),
        "opaque_right_ledge": v1.fuse_many(
            [ledge_base, approved_ledge_extension]
        ),
        "translucent_quad003_component_01": v1.fuse_many(
            [
                translucent_owners["below_mouth"],
                conditioned_tabs["below_mouth"]["translucent"],
            ]
        ),
        "translucent_central_component_03": v1.fuse_many(
            [
                translucent_owners["nose_top"],
                conditioned_tabs["nose_top"]["translucent"],
            ]
        ),
        "translucent_quad017_component_02": v1.fuse_many(
            [
                translucent_owners["outer_panel"],
                conditioned_tabs["outer_panel"]["translucent"],
            ]
        ),
    }

    final_pairs = {
        "below_mouth": (
            parts["opaque_component_001"],
            parts["translucent_quad003_component_01"],
        ),
        "nose_top": (
            parts["opaque_component_002"],
            parts["translucent_central_component_03"],
        ),
        "outer_panel": (
            parts["opaque_component_001"],
            parts["translucent_quad017_component_02"],
        ),
    }
    cross_owner_records: dict[str, dict[str, float]] = {}
    for station, (opaque_final, translucent_final) in final_pairs.items():
        baseline_common = v1.common_volume(
            opaque_owners[station], translucent_owners[station]
        )
        final_common = v1.common_volume(opaque_final, translucent_final)
        cross_owner_records[station] = {
            "baseline_common_mm3": baseline_common,
            "final_common_mm3": final_common,
            "added_common_mm3": final_common - baseline_common,
        }

    mesh_checker = load_module(
        project_path(
            str(contract["inputs"]["mesh_topology_checker"]["path"])
        ),
        "_lower_right_release_v2_mesh_checker",
    )
    meshes: dict[str, Any] = {}
    mesh_records: dict[str, dict[str, Any]] = {}
    for part_id, shape in parts.items():
        mesh, record = v1.mesh_record(
            part_id,
            shape,
            contract,
            Mesh,
            MeshPart,
            App,
            mesh_checker,
        )
        meshes[part_id] = mesh
        mesh_records[part_id] = record

    return {
        "App": App,
        "Mesh": Mesh,
        "MeshPart": MeshPart,
        "Part": Part,
        "v1": v1,
        "mesh_checker": mesh_checker,
        "contract": contract,
        "pins": pins,
        "parts": parts,
        "meshes": meshes,
        "mesh_records": mesh_records,
        "station_records": station_records,
        "cross_owner_records": cross_owner_records,
        "source_evidence": {
            "component_001_current": v1.shape_record(current_owner_001),
            "component_001_healing": healing,
            "ledge_extension_current": v1.shape_record(
                current_ledge_extension
            ),
            "ledge_extension_approved": v1.shape_record(
                approved_ledge_extension
            ),
            "ledge_extension_symmetric_difference": v1.symmetric_difference(
                current_ledge_extension, approved_ledge_extension
            ),
            "nose_top_trim": nose_evidence,
        },
    }


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    contract = bundle["contract"]
    v1 = bundle["v1"]
    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    source = bundle["source_evidence"]
    healing = source["component_001_healing"]
    nose = source["nose_top_trim"]
    stations = bundle["station_records"]
    part_records = {
        part_id: v1.shape_record(shape)
        for part_id, shape in bundle["parts"].items()
    }

    expected_topology = contract["component_001_healing"][
        "expected_topology"
    ]
    corrected_topology = healing["corrected"]["topology"]
    healing_pass = bool(
        healing["operation_result"]
        and healing["source"]["valid"]
        and healing["source"]["closed"]
        and healing["source"]["solid_count"] == 1
        and healing["corrected"]["valid"]
        and healing["corrected"]["closed"]
        and healing["corrected"]["solid_count"] == 1
        and corrected_topology["faces"] == int(expected_topology["faces"])
        and corrected_topology["edges"] == int(expected_topology["edges"])
        and corrected_topology["vertices"]
        == int(expected_topology["vertices"])
        and corrected_topology["solids"] == int(expected_topology["solids"])
        and len(healing["rejected_face_before"]) == 1
        and healing["rejected_face_before"][0]["face_index"]
        == int(
            contract["component_001_healing"]["rejected_face_signature"][
                "source_face_index"
            ]
        )
        and healing["rejected_face_after"] == []
        and healing["symmetric_difference"]["total_mm3"]
        <= float(
            gates[
                "component_001_maximum_symmetric_difference_mm3"
            ]
        )
        and healing["absolute_volume_delta_mm3"]
        <= float(gates["component_001_maximum_volume_delta_mm3"])
    )
    current_defect_evidence_pass = bool(
        not source["component_001_current"]["valid"]
        and not source["component_001_current"]["closed"]
    )
    final_artifact_absent = (
        rejected_face_records(
            bundle["parts"]["opaque_component_001"],
            contract["component_001_healing"]["rejected_face_signature"],
        )
        == []
    )
    ledge_identity_pass = bool(
        source["ledge_extension_symmetric_difference"]["total_mm3"] <= epsilon
    )

    nose_reconstruction_pass = all(
        nose["source_reconstruction"][side]["total_mm3"]
        <= float(
            gates[
                "nose_source_reconstruction_maximum_symmetric_difference_mm3"
            ]
        )
        for side in ("opaque", "translucent")
    )
    dimension_tolerance = float(gates["dimension_tolerance_mm"])
    trim_specification = contract["nose_top_trim"]
    nose_trim_pass = bool(
        abs(
            float(nose["source_depth_mm"])
            - float(trim_specification["source_depth_mm"])
        )
        <= dimension_tolerance
        and abs(
            float(nose["corrected_depth_mm"])
            - float(trim_specification["corrected_depth_mm"])
        )
        <= dimension_tolerance
        and abs(
            float(nose["removed_free_end_mm"])
            - float(trim_specification["removed_free_end_mm"])
        )
        <= dimension_tolerance
        and abs(
            float(nose["hole_center_depth_from_root_mm"])
            - float(trim_specification["hole_center_depth_from_root_mm"])
        )
        <= dimension_tolerance
        and float(nose["end_wall_mm"])
        >= float(trim_specification["minimum_end_wall_mm"])
        - dimension_tolerance
        and all(
            abs(
                float(nose["removed_source_volume_mm3"][side])
                - float(gates["nose_removed_volume_target_mm3"])
            )
            <= float(gates["nose_removed_volume_tolerance_mm3"])
            for side in ("opaque", "translucent")
        )
    )
    corrected_nose_sources_pass = all(
        record["valid"] and record["closed"] and record["solid_count"] == 1
        for record in nose["corrected_source_shapes"].values()
    )

    tab_shapes_pass = all(
        record[side]["valid"]
        and record[side]["closed"]
        and record[side]["solid_count"] == 1
        for record in stations.values()
        for side in ("opaque_tab", "translucent_tab")
    )
    root_overlap_pass = all(
        record[f"{side}_intended_owner_overlap_mm3"]
        >= float(gates["minimum_intended_owner_overlap_mm3"])
        for record in stations.values()
        for side in ("opaque", "translucent")
    )
    pair_clearance_pass = all(
        record["tab_pair_intersection_mm3"]
        <= float(gates["maximum_tab_pair_intersection_mm3"])
        and float(gates["minimum_tab_pair_clearance_mm"])
        <= record["tab_pair_clearance_mm"]
        <= float(gates["maximum_tab_pair_clearance_mm"])
        for record in stations.values()
    )
    opposite_owner_trim_pass = all(
        record["opaque_conditioned_to_opposite_owner_mm3"] <= epsilon
        and record["translucent_conditioned_to_opposite_owner_mm3"]
        <= epsilon
        for record in stations.values()
    )
    cross_collision_pass = all(
        record["added_common_mm3"]
        <= float(gates["maximum_added_fused_pair_intersection_mm3"])
        for record in bundle["cross_owner_records"].values()
    )
    bore_pass = all(
        any(
            abs(radius - float(gates["required_bore_radius_mm"]))
            <= float(gates["bore_radius_tolerance_mm"])
            for radius in record[side]["cylinder_radii_mm"]
        )
        for record in stations.values()
        for side in ("opaque_tab", "translucent_tab")
    )
    part_brep_pass = all(
        record["valid"] and record["closed"] and record["solid_count"] == 1
        for record in part_records.values()
    )
    mesh_pass = all(
        bool(record.get("clean"))
        for record in bundle["mesh_records"].values()
    )
    expected_conditioning = set(
        contract["mesh"]["deterministic_conditioning"]["parts"]
    )
    actual_conditioning = {
        part_id
        for part_id, record in bundle["mesh_records"].items()
        if record["conditioning_applied"]
    }
    conditioning_scope_pass = bool(
        actual_conditioning == expected_conditioning
        and all(
            all(record["conditioning_policy_checks"].values())
            for record in bundle["mesh_records"].values()
            if record["conditioning_applied"]
        )
        and all(
            record["raw"]["clean"]
            for part_id, record in bundle["mesh_records"].items()
            if part_id not in expected_conditioning
        )
    )

    output_directory = project_path(contract["outputs"]["directory"])
    checks = {
        "all_input_hashes_match_and_rejected_v1_is_immutable": True,
        "manual_component_001_defect_is_recorded": current_defect_evidence_pass,
        "native_component_001_healing_removes_rejected_face6_only_within_bound": healing_pass,
        "rejected_face6_signature_absent_from_final_opaque_part": final_artifact_absent,
        "approved_right_ledge_extension_shape_is_exact": ledge_identity_pass,
        "approved_10mm_nose_pair_reconstruction_is_exact": nose_reconstruction_pass,
        "nose_pair_free_end_is_trimmed_2mm_with_d4_and_1mm_wall": nose_trim_pass,
        "corrected_nose_source_tabs_are_valid_closed_one_solid": corrected_nose_sources_pass,
        "all_six_conditioned_tabs_are_valid_closed_one_solid": tab_shapes_pass,
        "all_six_conditioned_tabs_keep_positive_intended_owner_overlap": root_overlap_pass,
        "all_three_tab_pairs_keep_0p300_clearance_and_zero_intersection": pair_clearance_pass,
        "exact_opposite_owner_conditioning_removes_all_tab_cross_collision": opposite_owner_trim_pass,
        "final_fusions_add_no_cross_owner_collision": cross_collision_pass,
        "all_six_d4_bores_remain_in_conditioned_tabs": bore_pass,
        "all_six_print_parts_are_valid_closed_one_solid": part_brep_pass,
        "all_six_generated_meshes_are_clean_closed_manifold_single_components": mesh_pass,
        "only_two_named_raw_failures_receive_bounded_deterministic_conditioning": conditioning_scope_pass,
        "output_directory_is_fresh": not output_directory.exists(),
        "release_names_prohibit_3mf_and_gcode": all(
            not str(value).lower().endswith((".3mf", ".gcode"))
            for value in contract["outputs"]["parts"].values()
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-lower-right-connector-integration-preflight-v2",
        "status": PREFLIGHT_PASS if not failed else "PREFLIGHT_FAIL__NO_PRINT_OUTPUT",
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "source_evidence": source,
        "connector_station_evidence": stations,
        "cross_owner_collision_evidence": bundle["cross_owner_records"],
        "part_breps": part_records,
        "part_meshes": bundle["mesh_records"],
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
    obj.addProperty("App::PropertyString", "Integration", "PrintRelease")
    obj.Integration = (
        "USER_CORRECTED_V2__FACE6_NATIVE_HEAL__NOSE_FREE_END_TRIM__"
        "EXACT_OPPOSITE_OWNER_TRIM__OWNER_FUSION"
    )
    if part_id == "opaque_component_001":
        obj.addProperty(
            "App::PropertyString", "Component001Correction", "PrintRelease"
        )
        obj.Component001Correction = (
            "REJECTED_LONG_ZERO_AREA_FACE6_REMOVED__"
            "SHAPEFIX_SMALL_STRIP_TOLERANCE_0P00002_MM"
        )
    if part_id in (
        "opaque_component_002",
        "translucent_central_component_03",
    ):
        trim = contract["nose_top_trim"]
        obj.addProperty(
            "App::PropertyLength", "NoseTabDepth", "PrintRelease"
        )
        obj.NoseTabDepth = float(trim["corrected_depth_mm"])
        obj.addProperty(
            "App::PropertyLength", "NoseHoleCenterDepth", "PrintRelease"
        )
        obj.NoseHoleCenterDepth = float(
            trim["hole_center_depth_from_root_mm"]
        )
        obj.addProperty(
            "App::PropertyLength", "NoseMinimumEndWall", "PrintRelease"
        )
        obj.NoseMinimumEndWall = float(trim["minimum_end_wall_mm"])
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
    document = App.newDocument("LOWER_RIGHT_CONNECTOR_INTEGRATION_PRINT_PARTS_V2")
    try:
        opaque = document.addObject(
            "App::DocumentObjectGroup", "OPAQUE_RIGHT_LOWER_CHANGED_PRINT_PARTS"
        )
        translucent = document.addObject(
            "App::DocumentObjectGroup", "TRANSLUCENT_RIGHT_MATING_CHANGED_PRINT_PARTS"
        )
        for part_id in PART_IDS:
            group = (
                translucent if part_id.startswith("translucent_") else opaque
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
        metadata.Scope = "RIGHT_SIDE_ONLY__SIX_CHANGED_MODULAR_PARTS"
        metadata.addProperty(
            "App::PropertyString", "V1Disposition", "PrintRelease"
        )
        metadata.V1Disposition = (
            "REJECTED_BY_USER__PLANK_PROTRUSION_AND_ZERO_AREA_FACE6"
        )
        metadata.addProperty(
            "App::PropertyString", "CorrectionPolicy", "PrintRelease"
        )
        metadata.CorrectionPolicy = (
            "NOSE_PAIR_FREE_END_MINUS_2MM__D4_CENTER_PRESERVED__"
            "FACE6_NATIVE_SMALL_STRIP_HEAL"
        )
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
            records[part_id] = bundle["v1"].shape_record(obj.Shape)
            if not bundle["v1"].clean_single_solid(obj.Shape):
                raise RuntimeError(f"saved FCStd part is not clean: {part_id}")
        if rejected_face_records(
            reopened.getObject(
                PART_OBJECT_NAMES["opaque_component_001"]
            ).Shape,
            contract["component_001_healing"]["rejected_face_signature"],
        ):
            raise RuntimeError("saved FCStd reintroduced rejected Face6")
        return records
    finally:
        App.closeDocument(reopened.Name)


def write_readme(destination: Path, manifest: dict[str, Any]) -> None:
    destination.write_text(
        "# Lower-right connector integration print release V2\n\n"
        "This fresh V2 supersedes the visually rejected V1 package; V1 remains "
        "unchanged as evidence. V2 contains the same six separate right-side "
        "print parts.\n\n"
        "Corrections requested by the user:\n\n"
        "- Both nose-top mating tabs are shortened from 10.0 mm to 8.0 mm by "
        "removing only the last 2.0 mm of their free ends. The D4 center remains "
        "5.0 mm from the root, leaving a 1.0 mm end wall.\n"
        "- The long zero-area Face6 is removed from opaque component 001 using "
        "a fixed 0.00002 mm native OCCT small-strip heal. The saved owner remains "
        "one valid closed solid.\n\n"
        "All six STLs passed closed-manifold, single-component, outward-normal, "
        "zero-boundary-edge, zero-nonmanifold-edge, and zero-self-intersection "
        "checks. No 3MF, slicer profile, G-code, or printer-specific orientation "
        "is included.\n\n"
        f"Release status: {manifest['status']}\n",
        encoding="utf-8",
    )


def write_checkpoint(destination: Path, manifest: dict[str, Any]) -> None:
    nose = manifest["source_evidence"]["nose_top_trim"]
    healing = manifest["source_evidence"]["component_001_healing"]
    destination.write_text(
        "# Lower-right connector V2 print-release checkpoint — 2026-08-21\n\n"
        f"Status: {manifest['status']}\n\n"
        "V1 is preserved unchanged and rejected for the user-visible nose-tab "
        "plank and long zero-area Face6.\n\n"
        "V2 corrections:\n\n"
        f"- Nose pair depth: {nose['source_depth_mm']:.1f} -> "
        f"{nose['corrected_depth_mm']:.1f} mm; D4 center retained at "
        f"{nose['hole_center_depth_from_root_mm']:.6f} mm; end wall "
        f"{nose['end_wall_mm']:.6f} mm.\n"
        f"- Component 001: {healing['source']['topology']['faces']} -> "
        f"{healing['corrected']['topology']['faces']} faces; rejected Face6 "
        f"matches before={len(healing['rejected_face_before'])}, "
        f"after={len(healing['rejected_face_after'])}; valid/closed/one-solid "
        f"after={healing['corrected']['valid']}/"
        f"{healing['corrected']['closed']}/"
        f"{healing['corrected']['solid_count']}.\n\n"
        "Validation: every manifest check passed; six FCStd BReps are valid, "
        "closed one-solids; six reloaded STL meshes are clean closed manifold "
        "single components.\n\n"
        "Regeneration command (from the cat-head project root):\n\n"
        "    env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib "
        "/tmp/freecad-1.1.3-extract/squashfs-root/AppRun python "
        "source/cad-change-control/print-release/"
        "lower-right-connector-integration-v2/export_release.py "
        "--mode preflight --report /tmp/lower-right-v2-preflight.json\n\n"
        "Then invoke --mode release with that report and its exact SHA-256.\n\n"
        "Next physical step: choose printer/material/orientation in the slicer; "
        "no slicing or G-code was authorized here.\n",
        encoding="utf-8",
    )


def release(bundle: dict[str, Any], report: dict[str, Any]) -> Path:
    contract = bundle["contract"]
    output_dir = project_path(contract["outputs"]["directory"])
    if output_dir.exists():
        raise RuntimeError(f"release output already exists: {output_dir}")

    with tempfile.TemporaryDirectory(
        prefix="lower-right-connector-integration-v2-"
    ) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        stl_dir = stage / str(contract["outputs"]["stl_directory"])
        stl_dir.mkdir()
        fcstd = stage / str(contract["outputs"]["fcstd"])
        saved_fcstd_records = create_fcstd(bundle, fcstd)

        reloaded_mesh_records: dict[str, Any] = {}
        for part_id in PART_IDS:
            destination = stl_dir / str(
                contract["outputs"]["parts"][part_id]
            )
            bundle["meshes"][part_id].write(str(destination))
            reloaded = bundle["Mesh"].Mesh(str(destination))
            record = bundle["mesh_checker"].mesh_topology(reloaded)
            record["clean"] = bool(
                bundle["mesh_checker"].clean_manifold_mesh(record)
            )
            if not record["clean"]:
                raise RuntimeError(
                    f"reloaded STL mesh failed for {part_id}: {record}"
                )
            reloaded_mesh_records[part_id] = record

        manifest = dict(report)
        manifest["schema_version"] = (
            "cat-head-lower-right-connector-integration-release-manifest-v2"
        )
        manifest["status"] = RELEASE_PASS
        manifest["failed_checks"] = []
        manifest["saved_fcstd_part_breps"] = saved_fcstd_records
        manifest["reloaded_stl_meshes"] = reloaded_mesh_records
        manifest["io_trace"] = {
            "preflight_report_created": True,
            "fcstd_created": True,
            "stl_created": True,
            "stl_count": len(PART_IDS),
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
            raise RuntimeError(f"forbidden release files were staged: {forbidden}")

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, output_dir)

    if verify_pins(contract) != bundle["pins"]:
        raise RuntimeError("an input changed during V2 release")
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
    parser.add_argument("--mode", choices=("preflight", "release"), required=True)
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
                },
                sort_keys=True,
            )
        )
        return 0 if not report["failed_checks"] else 2

    if report["failed_checks"]:
        raise RuntimeError(
            "lower-right V2 release gates failed: "
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
        raise RuntimeError("preflight pins do not match the release invocation")
    expected_breps = {
        key: value["brep_sha256"]
        for key, value in preflight["part_breps"].items()
    }
    actual_breps = {
        key: value["brep_sha256"]
        for key, value in report["part_breps"].items()
    }
    if expected_breps != actual_breps:
        raise RuntimeError("release BReps differ from pinned preflight BReps")
    output = release(bundle, report)
    print(json.dumps({"status": RELEASE_PASS, "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
