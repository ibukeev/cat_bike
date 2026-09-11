#!/usr/bin/env python3
"""Shared FreeCAD kernel for the isolated Rev113 merged-mouth candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import FreeCAD as App
import MeshPart
import Part


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


REPO_ROOT = _find_repo_root()
CONTRACT_PATH = REPO_ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-merged-mouth-pane-rev113.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _vector(value) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def _bbox(shape) -> dict:
    bounds = shape.BoundBox
    return {
        "min_mm": [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)],
        "max_mm": [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)],
        "size_mm": [float(bounds.XLength), float(bounds.YLength), float(bounds.ZLength)],
    }


def _center_of_mass(shape):
    if hasattr(shape, "CenterOfMass"):
        return shape.CenterOfMass
    if shape.Solids:
        total_volume = sum(float(solid.Volume) for solid in shape.Solids)
        if total_volume > 0.0:
            return App.Vector(
                sum(float(solid.CenterOfMass.x) * float(solid.Volume) for solid in shape.Solids) / total_volume,
                sum(float(solid.CenterOfMass.y) * float(solid.Volume) for solid in shape.Solids) / total_volume,
                sum(float(solid.CenterOfMass.z) * float(solid.Volume) for solid in shape.Solids) / total_volume,
            )
    raise RuntimeError(f"Cannot derive center of mass for {shape.ShapeType}")


def brep_sha256(shape) -> str:
    payload = shape.exportBrepToString()
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def shape_record(shape) -> dict:
    return {
        "shape_type": str(shape.ShapeType),
        "is_null": bool(shape.isNull()),
        "is_valid": bool(shape.isValid()),
        "is_closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "vertex_count": len(shape.Vertexes),
        "volume_mm3": float(shape.Volume),
        "surface_area_mm2": float(shape.Area),
        "center_of_mass_mm": _vector(_center_of_mass(shape)),
        "bbox": _bbox(shape),
        "brep_sha256": brep_sha256(shape),
    }


def require_closed_solids(shape, label: str, expected_count: int = 1) -> dict:
    record = shape_record(shape)
    if record["is_null"]:
        raise RuntimeError(f"{label} is null")
    if not record["is_valid"]:
        raise RuntimeError(f"{label} is invalid")
    if record["solid_count"] != expected_count:
        raise RuntimeError(f"{label} has {record['solid_count']} solids; expected {expected_count}")
    if any(not solid.isClosed() for solid in shape.Solids):
        raise RuntimeError(f"{label} contains an open solid")
    return record


def symmetric_difference(first, second) -> dict:
    return {
        "first_minus_second_mm3": float(first.cut(second).Volume),
        "second_minus_first_mm3": float(second.cut(first).Volume),
    }


def bbox_residual(shape, expected_min: list[float], expected_max: list[float]) -> float:
    actual = _bbox(shape)["min_mm"] + _bbox(shape)["max_mm"]
    expected = list(expected_min) + list(expected_max)
    return max(abs(a - b) for a, b in zip(actual, expected))


def _required_object(document, name: str):
    obj = document.getObject(name)
    if obj is None:
        raise RuntimeError(f"Required Rev112 object is absent: {name}")
    return obj


def _face_normal(face) -> list[float]:
    u_min, u_max, v_min, v_max = face.ParameterRange
    return _vector(face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0))


def _max_vector_residual(actual: list[float], expected: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(actual, expected))


def _mesh_record(shape, contract: dict) -> dict:
    validation = contract["validation"]
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=validation["mesh_linear_deflection_mm"],
        AngularDeflection=validation["mesh_angular_deflection_rad"],
        Relative=False,
    )
    if mesh.CountFacets <= 0:
        raise RuntimeError("In-memory mesh preflight generated no facets")
    return {
        "facets": int(mesh.CountFacets),
        "points": int(mesh.CountPoints),
        "volume_mm3": float(mesh.Volume),
    }


def _require_authority(contract: dict) -> None:
    approval = contract["approval"]
    for key in (
        "merge_exact_two_rev112_mouth_panes_authorized",
        "create_isolated_rev113_candidate_fcstd_authorized",
        "export_rev113_review_candidate_print_parts_authorized",
    ):
        if not approval[key]:
            raise RuntimeError(f"Rev113 lacks authority for {key}")
    for key in (
        "overwrite_rev112_authorized",
        "change_head_authorized",
        "change_eye_panes_authorized",
        "change_stops_cutters_or_zip_tie_slots_authorized",
        "change_mouth_outer_surfaces_authorized",
        "promote_final_release_authorized",
        "slicer_profile_3mf_or_gcode_authorized",
        "unrelated_geometry_authorized",
    ):
        if approval[key]:
            raise RuntimeError(f"Rev113 forbidden authority unexpectedly enabled: {key}")
    if contract["operation"]["method"] != "RULED_SOLID_LOFT_BETWEEN_PINNED_CENTER_SEAM_FACES_THEN_FUSE":
        raise RuntimeError("Rev113 merge method changed")


def construct_package(contract: dict) -> dict:
    """Copy frozen Rev112 print parts and bridge only the two pinned seam faces."""
    _require_authority(contract)
    source = contract["source"]
    operation = contract["operation"]
    validation = contract["validation"]
    source_path = REPO_ROOT / source["path"]
    source_hash_before = sha256(source_path)
    if source_hash_before != source["sha256"]:
        raise RuntimeError("Pinned Rev112 source FCStd hash mismatch")

    print("Rev113 stage 1 of 6: open the hash-pinned Rev112 print package read-only", flush=True)
    document = App.openDocument(str(source_path))
    try:
        source_shapes = {
            "head": _required_object(document, source["head_object"]).Shape,
            "right_eye": _required_object(document, source["right_eye_object"]).Shape,
            "left_eye": _required_object(document, source["left_eye_object"]).Shape,
            "mouth_tri005": _required_object(document, source["mouth_tri005_object"]).Shape,
            "mouth_tri006": _required_object(document, source["mouth_tri006_object"]).Shape,
        }
        shapes = {key: shape.copy() for key, shape in source_shapes.items()}
        zip_corridors = {
            "right": _required_object(document, source["right_zip_tie_corridor_object"]).Shape.copy(),
            "left": _required_object(document, source["left_zip_tie_corridor_object"]).Shape.copy(),
        }

        print("Rev113 stage 2 of 6: prove every frozen Rev112 shape fingerprint", flush=True)
        source_records = {}
        for key, shape in source_shapes.items():
            source_records[key] = require_closed_solids(shape, f"Rev113 source {key}", 1)
            if source_records[key]["brep_sha256"] != source["expected_brep_sha256"][key]:
                raise RuntimeError(f"Rev112 {key} BREP fingerprint changed")
            require_closed_solids(shapes[key], f"Rev113 copied {key}", 1)
        for side, corridor in zip_corridors.items():
            require_closed_solids(corridor, f"Rev112 {side} zip-tie corridor", 1)
            if float(shapes["head"].common(corridor).Volume) > validation["zip_tie_corridor_residual_volume_maximum_mm3"]:
                raise RuntimeError(f"Rev112 {side} zip-tie slot is not through-open")

        first = shapes["mouth_tri005"]
        second = shapes["mouth_tri006"]
        seam_distance = float(first.distToShape(second)[0])
        if abs(seam_distance - operation["measured_minimum_seam_gap_mm"]) > validation["distance_tolerance_mm"]:
            raise RuntimeError("Rev112 mouth center-seam distance changed")

        print("Rev113 stage 3 of 6: validate the two selected center-seam Face1 anchors", flush=True)
        anchors = {}
        for key, shape, anchor_contract in (
            ("mouth_tri005", first, operation["first_anchor"]),
            ("mouth_tri006", second, operation["second_anchor"]),
        ):
            face = shape.Faces[anchor_contract["face_index"] - 1]
            area_residual = abs(float(face.Area) - anchor_contract["area_mm2"])
            normal = _face_normal(face)
            normal_residual = _max_vector_residual(normal, anchor_contract["normal"])
            if area_residual > validation["face_area_tolerance_mm2"]:
                raise RuntimeError(f"Rev113 {key} seam-face area changed")
            if normal_residual > validation["normal_component_tolerance"]:
                raise RuntimeError(f"Rev113 {key} seam-face normal changed")
            anchors[key] = {
                "object": anchor_contract["object"],
                "face_name": anchor_contract["face"],
                "area_mm2": float(face.Area),
                "area_residual_mm2": area_residual,
                "normal": normal,
                "normal_component_residual": normal_residual,
                "face_shape": face,
            }

        print("Rev113 stage 4 of 6: loft the exact seam-only bridge and fuse both pane halves", flush=True)
        bridge = Part.makeLoft(
            [anchors["mouth_tri005"]["face_shape"].OuterWire, anchors["mouth_tri006"]["face_shape"].OuterWire],
            True,
            True,
        )
        bridge_record = require_closed_solids(bridge, "Rev113 center-seam bridge", 1)
        if abs(bridge_record["volume_mm3"] - operation["expected_bridge_volume_mm3"]) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Rev113 center bridge volume changed")
        merged = first.fuse(bridge).fuse(second).removeSplitter()
        merged_record = require_closed_solids(
            merged,
            "Rev113 merged mouth pane",
            operation["expected_merged_mouth_solid_count"],
        )
        if abs(merged_record["volume_mm3"] - operation["expected_merged_volume_mm3"]) > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Rev113 merged mouth volume changed")
        merged_bbox_residual = bbox_residual(
            merged,
            operation["expected_merged_bbox_min_mm"],
            operation["expected_merged_bbox_max_mm"],
        )
        if merged_bbox_residual > validation["bbox_tolerance_mm"]:
            raise RuntimeError("Rev113 bridge changed the combined mouth outer bounds")

        print("Rev113 stage 5 of 6: prove both pane halves are preserved and the bridge clears the head", flush=True)
        preservation = {
            "mouth_tri005_minus_merged_mm3": float(first.cut(merged).Volume),
            "mouth_tri006_minus_merged_mm3": float(second.cut(merged).Volume),
        }
        if max(preservation.values()) > validation["boolean_residual_volume_maximum_mm3"]:
            raise RuntimeError("Rev113 merged pane does not preserve both Rev112 mouth halves")
        original_compound = Part.makeCompound([first, second])
        addition_outside_originals = float(merged.cut(original_compound).Volume)
        addition_residual = abs(addition_outside_originals - float(bridge.Volume))
        if addition_residual > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Rev113 added material is not exactly the seam bridge")
        merged_head_overlap = float(merged.common(shapes["head"]).Volume)
        bridge_head_overlap = float(bridge.common(shapes["head"]).Volume)
        if max(merged_head_overlap, bridge_head_overlap) > validation["pane_head_overlap_maximum_mm3"]:
            raise RuntimeError("Rev113 merged mouth pane collides with the frozen head")

        print("Rev113 stage 6 of 6: tessellate the four proposed print parts in memory", flush=True)
        mesh_preflight = {
            "head": _mesh_record(shapes["head"], contract),
            "right_eye": _mesh_record(shapes["right_eye"], contract),
            "left_eye": _mesh_record(shapes["left_eye"], contract),
            "merged_mouth": _mesh_record(merged, contract),
            "review_only_bridge": _mesh_record(bridge, contract),
        }
    finally:
        App.closeDocument(document.Name)

    source_hash_after = sha256(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Rev112 source FCStd changed during Rev113 construction")

    anchor_evidence = {}
    for key, record in anchors.items():
        anchor_evidence[key] = {name: value for name, value in record.items() if name != "face_shape"}
    return {
        "head": shapes["head"],
        "right_eye": shapes["right_eye"],
        "left_eye": shapes["left_eye"],
        "mouth_tri005": first,
        "mouth_tri006": second,
        "bridge": bridge,
        "merged_mouth": merged,
        "zip_corridors": zip_corridors,
        "evidence": {
            "construction_method": operation["method"],
            "source_sha256_before": source_hash_before,
            "source_sha256_after": source_hash_after,
            "source_records": source_records,
            "seam_distance_mm": seam_distance,
            "anchors": anchor_evidence,
            "bridge": bridge_record,
            "merged_mouth": merged_record,
            "merged_bbox_residual_mm": merged_bbox_residual,
            "original_halves_preservation": preservation,
            "addition_outside_originals_mm3": addition_outside_originals,
            "addition_vs_bridge_volume_residual_mm3": addition_residual,
            "merged_head_overlap_mm3": merged_head_overlap,
            "bridge_head_overlap_mm3": bridge_head_overlap,
            "zip_tie_corridor_residuals_mm3": {
                side: float(shapes["head"].common(corridor).Volume)
                for side, corridor in zip_corridors.items()
            },
            "mesh_preflight": mesh_preflight,
            "final_print_part_count": 4,
            "slicer_project_created_or_changed": False,
            "gcode_created": False,
        },
    }


def set_property(obj, property_type: str, name: str, value, group: str = "Revision 113") -> None:
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, group)
    setattr(obj, name, value)


def finalize_document(document, package: dict, contract: dict) -> dict:
    """Assign Rev113 candidate shapes to a clean unsaved document."""
    print_group = document.addObject("App::DocumentObjectGroup", "PRINT_PARTS__REV113")
    print_group.Label = "PRINT PARTS — Rev113 frozen head, two eyes, and one merged mouth pane"

    head_body = document.addObject("PartDesign::Body", "FINAL_HEAD_BODY_REV113")
    head_body.Label = "PRINT — FINAL HEAD BODY REV113; geometry frozen from Rev112"
    head = head_body.newObject("PartDesign::Feature", "PRINT__CAT_HEAD_FINAL_REV113")
    head.Label = "PRINT — unchanged Rev112 head; 4 cutter holes; 12 stops; 2 zip slots"
    head.Shape = package["head"].copy()
    set_property(head, "App::PropertyString", "DesignId", contract["design_id"])
    set_property(head, "App::PropertyString", "FrozenSourceSha256", contract["source"]["sha256"])
    set_property(head, "App::PropertyBool", "GeometryFrozenFromRev112", True)
    set_property(head, "App::PropertyInteger", "UserCutterHoleCount", 4)
    set_property(head, "App::PropertyInteger", "IntegratedStopCount", 12)
    set_property(head, "App::PropertyInteger", "ZipTieThroughSlotCount", 2)
    set_property(head, "App::PropertyBool", "PrintableReviewCandidate", True)
    print_group.addObject(head_body)

    eye_objects = {}
    for key, name, label in (
        ("right_eye", "PRINT__RIGHT_EYE_TRANSLUCENT_PANE_REV113", "PRINT — unchanged right-eye translucent pane"),
        ("left_eye", "PRINT__LEFT_EYE_TRANSLUCENT_PANE_REV113", "PRINT — unchanged left-eye translucent pane"),
    ):
        obj = document.addObject("Part::Feature", name)
        obj.Label = label
        obj.Shape = package[key].copy()
        set_property(obj, "App::PropertyLength", "PETGThickness", 2.0)
        set_property(obj, "App::PropertyInteger", "HoleCount", 0)
        set_property(obj, "App::PropertyBool", "GeometryFrozenFromRev112", True)
        set_property(obj, "App::PropertyBool", "PrintableReviewCandidate", True)
        print_group.addObject(obj)
        eye_objects[key] = obj

    mouth = document.addObject("Part::Feature", "PRINT__MERGED_MOUTH_TRANSLUCENT_PANE_REV113")
    mouth.Label = "PRINT — one-piece faceted mouth pane; Rev112 halves plus seam-only bridge"
    mouth.Shape = package["merged_mouth"].copy()
    set_property(mouth, "App::PropertyLength", "PETGThickness", 2.0)
    set_property(mouth, "App::PropertyInteger", "HoleCount", 0)
    set_property(mouth, "App::PropertyInteger", "MergedSourcePaneCount", 2)
    set_property(mouth, "App::PropertyLength", "OriginalCenterSeamGap", contract["operation"]["measured_minimum_seam_gap_mm"])
    set_property(mouth, "App::PropertyBool", "OuterPaneSurfacesFrozenFromRev112", True)
    set_property(mouth, "App::PropertyBool", "PrintableReviewCandidate", True)
    print_group.addObject(mouth)

    evidence_group = document.addObject("App::DocumentObjectGroup", "REVIEW_EVIDENCE__REV113")
    evidence_group.Label = "REVIEW EVIDENCE — original mouth halves, bridge, anchors, and zip corridors"
    evidence_shapes = {
        "REFERENCE__MOUTH_TRI005_REV112": package["mouth_tri005"],
        "REFERENCE__MOUTH_TRI006_REV112": package["mouth_tri006"],
        "PROPOSED__MOUTH_CENTER_SEAM_BRIDGE_REV113": package["bridge"],
        "REVIEW_ONLY__TRI005_SEAM_FACE1_REV113": package["mouth_tri005"].Faces[0],
        "REVIEW_ONLY__TRI006_SEAM_FACE1_REV113": package["mouth_tri006"].Faces[0],
        "REVIEW_ONLY__RIGHT_ZIP_TIE_CORRIDOR_REV113": package["zip_corridors"]["right"],
        "REVIEW_ONLY__LEFT_ZIP_TIE_CORRIDOR_REV113": package["zip_corridors"]["left"],
    }
    evidence_objects = {}
    for name, shape in evidence_shapes.items():
        obj = document.addObject("Part::Feature", name)
        obj.Label = name.replace("__", " — ").replace("_", " ")
        obj.Shape = shape.copy()
        evidence_group.addObject(obj)
        evidence_objects[name] = obj

    parameters = document.addObject("Spreadsheet::Sheet", "Rev113MergedMouthParameters")
    values = (
        ("A1", "Parameter"), ("B1", "Value"),
        ("A2", "SourceRevision"), ("B2", "REV112 final MVP candidate"),
        ("A3", "MergeMethod"), ("B3", "ruled solid loft between both Face1 seam wires"),
        ("A4", "OriginalSeamGapMm"), ("B4", str(contract["operation"]["measured_minimum_seam_gap_mm"])),
        ("A5", "BridgeVolumeMm3"), ("B5", str(contract["operation"]["expected_bridge_volume_mm3"])),
        ("A6", "MergedMouthSolidCount"), ("B6", "1"),
        ("A7", "FinalPrintPartCount"), ("B7", "4"),
        ("A8", "FinalReleasePromoted"), ("B8", "NO"),
        ("A9", "SlicerProjectChanged"), ("B9", "NO"),
    )
    for cell, value in values:
        parameters.set(cell, value)
    document.recompute()

    require_closed_solids(head.Shape, "Finalized Rev113 head", 1)
    for key, obj in eye_objects.items():
        require_closed_solids(obj.Shape, f"Finalized Rev113 {key}", 1)
    require_closed_solids(mouth.Shape, "Finalized Rev113 merged mouth", 1)
    if head.Placement != App.Placement() or mouth.Placement != App.Placement():
        raise RuntimeError("Rev113 head or mouth placement is not identity")
    if any(obj.Placement != App.Placement() for obj in eye_objects.values()):
        raise RuntimeError("A Rev113 eye placement is not identity")

    return {
        "print_group": print_group.Name,
        "head_body": head_body.Name,
        "head_object": head.Name,
        "eye_objects": {key: obj.Name for key, obj in eye_objects.items()},
        "merged_mouth_object": mouth.Name,
        "review_evidence_group": evidence_group.Name,
        "review_evidence_objects": list(evidence_objects),
        "bridge_object": evidence_objects["PROPOSED__MOUTH_CENTER_SEAM_BRIDGE_REV113"].Name,
        "parameter_sheet": parameters.Name,
        "target_assignment_performed": True,
        "typed_metadata_assignment_performed": True,
        "recompute_performed": True,
        "final_assertions_performed": True,
    }
