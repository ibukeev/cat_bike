#!/usr/bin/env python3
"""Create the approved non-fused RIGHT-upper as-printed working assembly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).with_name("contract.json"),
    )
    return parser.parse_args()


def resolve(repo_root: Path, relative: str) -> Path:
    path = (repo_root / relative).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def source_pins(contract: dict[str, Any]) -> list[tuple[str, str, str]]:
    pins = [
        (
            "right_upper_fcstd",
            contract["right_upper"]["path"],
            contract["right_upper"]["sha256"],
        ),
        (
            "right_lower_fcstd",
            contract["frozen_lowers"]["right"]["fcstd_path"],
            contract["frozen_lowers"]["right"]["fcstd_sha256"],
        ),
        (
            "right_lower_3mf",
            contract["frozen_lowers"]["right"]["three_mf_path"],
            contract["frozen_lowers"]["right"]["three_mf_sha256"],
        ),
        (
            "left_lower_fcstd",
            contract["frozen_lowers"]["left"]["fcstd_path"],
            contract["frozen_lowers"]["left"]["fcstd_sha256"],
        ),
        (
            "left_lower_3mf",
            contract["frozen_lowers"]["left"]["three_mf_path"],
            contract["frozen_lowers"]["left"]["three_mf_sha256"],
        ),
        (
            "right_eye_fcstd",
            contract["eyes"]["right"]["fcstd_path"],
            contract["eyes"]["right"]["fcstd_sha256"],
        ),
        (
            "left_eye_fcstd",
            contract["eyes"]["left"]["fcstd_path"],
            contract["eyes"]["left"]["fcstd_sha256"],
        ),
        (
            "opaque_eye_3mf",
            contract["eyes"]["opaque_print_project"]["path"],
            contract["eyes"]["opaque_print_project"]["sha256"],
        ),
        (
            "approved_ears_fcstd",
            contract["approved_ears"]["fcstd_path"],
            contract["approved_ears"]["fcstd_sha256"],
        ),
        (
            "aluminum_interface",
            contract["aluminum_context"]["interface_path"],
            contract["aluminum_context"]["interface_sha256"],
        ),
        (
            "aluminum_metal_config",
            contract["aluminum_context"]["metal_config_path"],
            contract["aluminum_context"]["metal_config_sha256"],
        ),
    ]
    return pins


def verify_pins(repo_root: Path, pins: list[tuple[str, str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for role, relative, expected in pins:
        path = resolve(repo_root, relative)
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"Source pin mismatch for {role}: expected {expected}, received {actual}"
            )
        result[role] = {
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": True,
        }
    return result


def vector_unit(App: Any, value: Any) -> Any:
    length = value.Length
    if length <= 0.0:
        raise ValueError("Cannot normalize a zero vector")
    return App.Vector(value.x / length, value.y / length, value.z / length)


def polyhedron(Part: Any, vertices: list[Any], faces: list[tuple[int, ...]]) -> Any:
    face_shapes = []
    for indices in faces:
        points = [vertices[index] for index in indices]
        wire = Part.makePolygon(points + [points[0]])
        face_shapes.append(Part.Face(wire))
    shell = Part.makeShell(face_shapes)
    solid = Part.makeSolid(shell)
    if solid.isNull() or not solid.isClosed():
        raise RuntimeError("Failed to construct a closed context polyhedron")
    return solid


def oriented_square_prism(
    App: Any,
    Part: Any,
    lower: Any,
    axis: Any,
    across: Any,
    other: Any,
    half_width: float,
    half_height: float,
    start_t: float,
    end_t: float,
) -> Any:
    offsets = [
        across * -half_width + other * -half_height,
        across * half_width + other * -half_height,
        across * half_width + other * half_height,
        across * -half_width + other * half_height,
    ]
    vertices = [lower + offset + axis * start_t for offset in offsets]
    vertices += [lower + offset + axis * end_t for offset in offsets]
    return polyhedron(
        Part,
        vertices,
        [
            (3, 2, 1, 0),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
    )


def compound_rail(
    App: Any,
    Part: Any,
    lower: Any,
    axis: Any,
    across: Any,
    other: Any,
    center: Any,
    normal: Any,
    width: float,
    upper_t: float,
    bearing_offset: float,
) -> tuple[Any, float]:
    half = width / 2.0
    offsets = [
        across * -half + other * -half,
        across * half + other * -half,
        across * half + other * half,
        across * -half + other * half,
    ]
    denominator = axis.dot(normal)
    lower_vertices = []
    for offset in offsets:
        t_value = (
            bearing_offset - (lower + offset - center).dot(normal)
        ) / denominator
        lower_vertices.append(lower + offset + axis * t_value)
    upper_vertices = [lower + offset + axis * upper_t for offset in offsets]
    bearing_t = (
        bearing_offset - (lower - center).dot(normal)
    ) / denominator
    shape = polyhedron(
        Part,
        lower_vertices + upper_vertices,
        [
            (3, 2, 1, 0),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
    )
    return shape, bearing_t


def shape_stats(shape: Any) -> dict[str, Any]:
    bounds = shape.BoundBox
    return {
        "shape_type": shape.ShapeType,
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "bounds_mm": [
            float(bounds.XMin),
            float(bounds.YMin),
            float(bounds.ZMin),
            float(bounds.XMax),
            float(bounds.YMax),
            float(bounds.ZMax),
        ],
    }


def add_provenance(
    obj: Any,
    role: str,
    source_path: str,
    source_sha256: str,
    source_object: str,
    edit_policy: str,
    physical_status: str,
) -> None:
    values = {
        "AssemblyRole": role,
        "SourcePath": source_path,
        "SourceSHA256": source_sha256,
        "SourceObject": source_object,
        "EditPolicy": edit_policy,
        "PhysicalStatus": physical_status,
    }
    for name, value in values.items():
        obj.addProperty("App::PropertyString", name, "Provenance")
        setattr(obj, name, value)
        obj.setEditorMode(name, 1)
    obj.addProperty("App::PropertyBool", "FrozenContext", "Provenance")
    obj.FrozenContext = edit_policy != "WORKING_RIGHT_UPPER_OWNER_COPY"
    obj.setEditorMode("FrozenContext", 1)
    if obj.FrozenContext:
        obj.setEditorMode("Shape", 1)


def style(obj: Any, color: tuple[float, float, float], transparency: int) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    view.ShapeColor = color
    view.LineColor = color
    view.Transparency = transparency
    view.DisplayMode = "Flat Lines"


def copy_shape(
    target_doc: Any,
    target_group: Any,
    source_obj: Any,
    target_name: str,
    label: str,
    role: str,
    source_path: str,
    source_sha256: str,
    edit_policy: str,
    physical_status: str,
    color: tuple[float, float, float],
    transparency: int,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    if not hasattr(source_obj, "Shape") or source_obj.Shape.isNull():
        raise RuntimeError(f"Missing source shape: {source_obj.Name}")
    source_stats = shape_stats(source_obj.Shape)
    target = target_doc.addObject("Part::Feature", target_name)
    target.Label = label
    target.Shape = source_obj.Shape.copy()
    add_provenance(
        target,
        role,
        source_path,
        source_sha256,
        source_obj.Name,
        edit_policy,
        physical_status,
    )
    style(target, color, transparency)
    target_group.addObject(target)
    copied_stats = shape_stats(target.Shape)
    if copied_stats != source_stats:
        raise RuntimeError(f"Shape-copy signature drift for {target_name}")
    return target, source_stats, copied_stats


def add_context_shape(
    doc: Any,
    group: Any,
    name: str,
    label: str,
    shape: Any,
    role: str,
    source_path: str,
    source_sha256: str,
    source_object: str,
    color: tuple[float, float, float],
    transparency: int,
) -> Any:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    add_provenance(
        obj,
        role,
        source_path,
        source_sha256,
        source_object,
        "FROZEN_COORDINATION_CONTEXT__DO_NOT_EDIT",
        "DIGITAL_CONTEXT__NOT_FABRICATION_RELEASED",
    )
    style(obj, color, transparency)
    group.addObject(obj)
    return obj


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    output_dir = repo_root / contract["output"]["directory"]
    output_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_path.exists() or validation_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing working-assembly output: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    pins = source_pins(contract)
    pins_before = verify_pins(repo_root, pins)

    try:
        import FreeCAD as App
        import Part
    except ImportError as error:
        raise RuntimeError("Run with the pinned FreeCAD Python runtime") from error

    opened_docs: list[str] = []
    source_docs: dict[str, Any] = {}

    def open_source(role: str, relative: str) -> Any:
        source = App.openDocument(str(resolve(repo_root, relative)))
        opened_docs.append(source.Name)
        source_docs[role] = source
        return source

    upper_cfg = contract["right_upper"]
    right_lower_cfg = contract["frozen_lowers"]["right"]
    left_lower_cfg = contract["frozen_lowers"]["left"]
    right_eye_cfg = contract["eyes"]["right"]
    left_eye_cfg = contract["eyes"]["left"]
    ears_cfg = contract["approved_ears"]

    upper_src = open_source("right_upper", upper_cfg["path"])
    right_lower_src = open_source("right_lower", right_lower_cfg["fcstd_path"])
    left_lower_src = open_source("left_lower", left_lower_cfg["fcstd_path"])
    right_eye_src = open_source("right_eye", right_eye_cfg["fcstd_path"])
    left_eye_src = open_source("left_eye", left_eye_cfg["fcstd_path"])
    ears_src = open_source("approved_ears", ears_cfg["fcstd_path"])

    work = App.newDocument("RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V1")
    work.Label = "WORK FROM THIS — RIGHT UPPER AS-PRINTED ASSEMBLY V1 — NOT PRINT APPROVED"

    root_group = work.addObject("App::DocumentObjectGroup", "GRP_ASSEMBLY_ROOT")
    root_group.Label = "RIGHT UPPER WORKING ASSEMBLY — NON-FUSED — NOT PRINT APPROVED"
    metadata_group = work.addObject("App::DocumentObjectGroup", "GRP_00_RELEASE_METADATA")
    metadata_group.Label = "00 — RELEASE METADATA"
    upper_group = work.addObject("App::DocumentObjectGroup", "GRP_10_RIGHT_UPPER_OWNER")
    upper_group.Label = "10 — APPROVED RIGHT-UPPER V34 OWNER COPY — 41 COMPONENTS"
    lower_group = work.addObject("App::DocumentObjectGroup", "GRP_20_PRINTED_LOWER_CONTEXT")
    lower_group.Label = "20 — PRINTED LOWER CONTEXT — FROZEN"
    opaque_eye_group = work.addObject("App::DocumentObjectGroup", "GRP_30_PRINTED_OPAQUE_EYES")
    opaque_eye_group.Label = "30 — PRINTED OPAQUE EYE PARTS — FROZEN CONTEXT"
    lens_group = work.addObject("App::DocumentObjectGroup", "GRP_40_UNPRINTED_TRANSLUCENT_LENSES")
    lens_group.Label = "40 — UNPRINTED TRANSLUCENT LENSES — APPROVED CONTEXT"
    ear_group = work.addObject("App::DocumentObjectGroup", "GRP_50_APPROVED_EARS")
    ear_group.Label = "50 — APPROVED EARS — SEPARATE CONTEXT"
    aluminum_group = work.addObject("App::DocumentObjectGroup", "GRP_60_ALUMINUM_V05_CONTEXT")
    aluminum_group.Label = "60 — ALUMINUM V0.5-M2 COORDINATION — NOT FAB RELEASED"
    absence_group = work.addObject("App::DocumentObjectGroup", "GRP_90_INTENTIONAL_ABSENCES")
    absence_group.Label = "90 — INTENTIONAL ABSENCES AND OPEN WORK"
    for group in (
        metadata_group,
        upper_group,
        lower_group,
        opaque_eye_group,
        lens_group,
        ear_group,
        aluminum_group,
        absence_group,
    ):
        root_group.addObject(group)

    metadata = work.addObject("App::FeaturePython", "ASSEMBLY_RELEASE_METADATA")
    metadata.Label = "READ FIRST — USER-APPROVED V34 WORKING ASSEMBLY — NOT PRINT APPROVED"
    metadata.addProperty("App::PropertyString", "Status", "Release")
    metadata.Status = contract["status"]
    metadata.addProperty("App::PropertyString", "ApprovalDate", "Release")
    metadata.ApprovalDate = contract["approval"]["date"]
    metadata.addProperty("App::PropertyString", "ApprovedBaselineSHA256", "Release")
    metadata.ApprovedBaselineSHA256 = upper_cfg["sha256"]
    metadata.addProperty("App::PropertyStringList", "SourcePins", "Release")
    metadata.SourcePins = [
        f"{role}|{expected}|{relative}" for role, relative, expected in pins
    ]
    metadata.addProperty("App::PropertyStringList", "Policies", "Release")
    metadata.Policies = [
        f"{key}={value}" for key, value in contract["policies"].items()
    ]
    metadata.addProperty("App::PropertyString", "NextGate", "Release")
    metadata.NextGate = (
        "Classify exact right-upper intersections and aluminum/service envelopes; "
        "no export or print release from this file."
    )
    for prop in (
        "Status",
        "ApprovalDate",
        "ApprovedBaselineSHA256",
        "SourcePins",
        "Policies",
        "NextGate",
    ):
        metadata.setEditorMode(prop, 1)
    metadata_group.addObject(metadata)

    absence = work.addObject("App::FeaturePython", "LEFT_UPPER_OWNER_INTENTIONALLY_ABSENT")
    absence.Label = "LEFT UPPER OWNER ABSENT — NO TRUSTED BASELINE — DO NOT MIRROR AUTOMATICALLY"
    absence.addProperty("App::PropertyString", "Reason", "Gate")
    absence.Reason = (
        "Current left complete-owner FCStd has uncheckpointed real geometry drift. "
        "This file is the approved RIGHT-upper workstream only."
    )
    absence.setEditorMode("Reason", 1)
    absence_group.addObject(absence)

    copied: dict[str, Any] = {}
    upper_pattern = re.compile(r"RETAINED_RIGHT_UPPER_C(\d{3})_V34$")
    upper_components = []
    for source_obj in upper_src.Objects:
        match = upper_pattern.fullmatch(source_obj.Name)
        if match and hasattr(source_obj, "Shape") and not source_obj.Shape.isNull():
            upper_components.append((int(match.group(1)), source_obj))
    upper_components.sort(key=lambda item: item[0])
    actual_ids = [component_id for component_id, _ in upper_components]
    if actual_ids != upper_cfg["expected_component_ids"]:
        raise RuntimeError(f"Unexpected V34 component IDs: {actual_ids}")
    for component_id, source_obj in upper_components:
        role = f"WORKING_RIGHT_UPPER_OWNER_C{component_id:03d}"
        target, source_stats, target_stats = copy_shape(
            work,
            upper_group,
            source_obj,
            f"WORKING_RIGHT_UPPER_C{component_id:03d}_V34_BASELINE",
            f"WORKING RIGHT UPPER C{component_id:03d} — V34 BASELINE COPY",
            role,
            upper_cfg["path"],
            upper_cfg["sha256"],
            "WORKING_RIGHT_UPPER_OWNER_COPY",
            "DIGITAL_BASELINE__NOT_PRINTED__NOT_PRINT_APPROVED",
            (0.24, 0.42, 0.64),
            0,
        )
        copied[role] = {"source": source_stats, "copy": target_stats}

    for side, source_doc, cfg, color in (
        ("RIGHT", right_lower_src, right_lower_cfg, (0.32, 0.34, 0.38)),
        ("LEFT", left_lower_src, left_lower_cfg, (0.42, 0.44, 0.48)),
    ):
        source_obj = source_doc.getObject(cfg["object"])
        if source_obj is None:
            raise RuntimeError(f"Missing {side} lower object {cfg['object']}")
        role = f"PRINTED_{side}_LOWER_FROZEN_DATUM"
        _, source_stats, target_stats = copy_shape(
            work,
            lower_group,
            source_obj,
            f"CTX_PRINTED_{side}_LOWER_COMPOUND",
            f"PRINTED {side} LOWER — EXACT COMPOUND CONTEXT — DO NOT EDIT",
            role,
            cfg["fcstd_path"],
            cfg["fcstd_sha256"],
            "FROZEN_PRINTED_DATUM__DO_NOT_EDIT",
            cfg["physical_status"],
            color,
            65,
        )
        copied[role] = {"source": source_stats, "copy": target_stats}

    for side, source_doc, cfg in (
        ("RIGHT", right_eye_src, right_eye_cfg),
        ("LEFT", left_eye_src, left_eye_cfg),
    ):
        for part_name in ("carrier", "rear_plate", "lens"):
            source_name = cfg["objects"][part_name]
            source_obj = source_doc.getObject(source_name)
            if source_obj is None:
                raise RuntimeError(f"Missing {side} eye object {source_name}")
            is_lens = part_name == "lens"
            group = lens_group if is_lens else opaque_eye_group
            role = (
                f"UNPRINTED_{side}_TRANSLUCENT_LENS_CONTEXT"
                if is_lens
                else f"PRINTED_{side}_OPAQUE_EYE_{part_name.upper()}_DATUM"
            )
            physical_status = (
                contract["eyes"]["translucent_lens_physical_status"]
                if is_lens
                else contract["eyes"]["opaque_physical_status"]
            )
            target_name = f"CTX_{side}_EYE_{part_name.upper()}"
            _, source_stats, target_stats = copy_shape(
                work,
                group,
                source_obj,
                target_name,
                (
                    f"UNPRINTED {side} TRANSLUCENT LENS — FIT CONTEXT"
                    if is_lens
                    else f"PRINTED {side} OPAQUE EYE {part_name.upper()} — DO NOT EDIT"
                ),
                role,
                cfg["fcstd_path"],
                cfg["fcstd_sha256"],
                "APPROVED_UNPRINTED_CONTEXT__DO_NOT_EDIT"
                if is_lens
                else "FROZEN_PRINTED_DATUM__DO_NOT_EDIT",
                physical_status,
                (0.20, 0.82, 0.92) if is_lens else (0.10, 0.11, 0.13),
                72 if is_lens else 0,
            )
            copied[role] = {"source": source_stats, "copy": target_stats}

    for side, source_name in (
        ("RIGHT", ears_cfg["right_object"]),
        ("LEFT", ears_cfg["left_object"]),
    ):
        source_obj = ears_src.getObject(source_name)
        if source_obj is None:
            raise RuntimeError(f"Missing approved {side} ear object {source_name}")
        role = f"APPROVED_{side}_EAR_CONTEXT"
        _, source_stats, target_stats = copy_shape(
            work,
            ear_group,
            source_obj,
            f"CTX_APPROVED_{side}_EAR",
            f"APPROVED {side} EAR — SEPARATE FIT CONTEXT",
            role,
            ears_cfg["fcstd_path"],
            ears_cfg["fcstd_sha256"],
            "APPROVED_SEPARATE_CONTEXT__DO_NOT_EDIT",
            ears_cfg["physical_status"],
            (0.94, 0.48, 0.12),
            38,
        )
        copied[role] = {"source": source_stats, "copy": target_stats}

    aluminum_cfg = contract["aluminum_context"]
    interface = json.loads(
        resolve(repo_root, aluminum_cfg["interface_path"]).read_text(encoding="utf-8")
    )
    metal_config = json.loads(
        resolve(repo_root, aluminum_cfg["metal_config_path"]).read_text(encoding="utf-8")
    )
    plane = interface["rear_interface_plane"]
    center = App.Vector(*[float(value) for value in plane["center_head_mm"]])
    normal = vector_unit(
        App,
        App.Vector(*[float(value) for value in plane["outward_normal_head"]]),
    )
    across_plate = App.Vector(1.0, 0.0, 0.0)
    vertical = vector_unit(App, across_plate.cross(normal))

    def local_point(x_value: float, v_value: float, n_value: float = 0.0) -> Any:
        return center + across_plate * x_value + vertical * v_value + normal * n_value

    plate = interface["aluminum_backplate"]
    half_height = float(plate["height_mm"]) / 2.0
    polygon = [
        (-float(plate["outer_bottom_width_mm"]) / 2.0, -half_height),
        (float(plate["outer_bottom_width_mm"]) / 2.0, -half_height),
        (float(plate["outer_top_width_mm"]) / 2.0, half_height),
        (-float(plate["outer_top_width_mm"]) / 2.0, half_height),
    ]
    half_thickness = float(plate["thickness_mm"]) / 2.0
    lower_vertices = [local_point(x, v, -half_thickness) for x, v in polygon]
    upper_vertices = [local_point(x, v, half_thickness) for x, v in polygon]
    plate_shape = polyhedron(
        Part,
        lower_vertices + upper_vertices,
        [
            (3, 2, 1, 0),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
    )
    add_context_shape(
        work,
        aluminum_group,
        "AL_V05_BACKPLATE_OUTER_ENVELOPE",
        "AL V0.5 BACKPLATE OUTER ENVELOPE — 3 mm — HOLE TARGETS SHOWN SEPARATELY",
        plate_shape,
        "ALUMINUM_V05_BACKPLATE_COORDINATION_ENVELOPE",
        aluminum_cfg["interface_path"],
        aluminum_cfg["interface_sha256"],
        "aluminum_backplate",
        (0.58, 0.65, 0.72),
        58,
    )

    tool_diameter = float(
        plate["shell_attachment_hole_pattern"]["shell_pad_tool_envelope_diameter_mm"]
    )
    for index, (x_value, v_value) in enumerate(
        plate["shell_attachment_hole_pattern"]["local_x_v_centers_mm"], start=1
    ):
        point = local_point(float(x_value), float(v_value), -12.0)
        shape = Part.makeCylinder(tool_diameter / 2.0, 24.0, point, normal)
        add_context_shape(
            work,
            aluminum_group,
            f"AL_V05_SHELL_M5_TOOL_ENVELOPE_{index:02d}",
            f"AL V0.5 SHELL M5 TOOL ENVELOPE {index:02d} — 14 mm",
            shape,
            "ALUMINUM_V05_SHELL_FASTENER_TOOL_ENVELOPE",
            aluminum_cfg["interface_path"],
            aluminum_cfg["interface_sha256"],
            f"shell_attachment_hole_pattern[{index - 1}]",
            (0.96, 0.20, 0.20),
            72,
        )

    rail_system = interface["rail_system"]
    rail_values = metal_config["rails"]
    connector = metal_config["lower_shoe"]
    tube_size = float(rail_system["profile"]["outside_width_mm"])
    upper_t = float(rail_values["socket_stop_reference_length_mm"]) - float(
        rail_values["upper_seated_end_clearance_mm"]
    )
    bearing_offset = float(
        connector["compound_bearing"]["angle_bearing_face_offset_mm"]
    )
    socket = rail_system["socket"]
    socket_depth = float(socket["insertion_depth_mm"])
    socket_width = float(socket["printed_opening_width_mm"])
    for side in ("left", "right"):
        lower = App.Vector(
            *[float(value) for value in rail_system["lower_targets_head_mm"][side]]
        )
        axis = vector_unit(
            App,
            App.Vector(
                *[float(value) for value in rail_system["accepted_axes_head"][side]]
            ),
        )
        across = vector_unit(
            App,
            App.Vector(1.0, 0.0, 0.0)
            - axis * App.Vector(1.0, 0.0, 0.0).dot(axis),
        )
        other = vector_unit(App, axis.cross(across))
        rail_shape, bearing_t = compound_rail(
            App,
            Part,
            lower,
            axis,
            across,
            other,
            center,
            normal,
            tube_size,
            upper_t,
            bearing_offset,
        )
        add_context_shape(
            work,
            aluminum_group,
            f"AL_V05_{side.upper()}_RAIL_OUTER_ENVELOPE",
            f"AL V0.5 {side.upper()} 19 mm RAIL OUTER ENVELOPE — COMPOUND LOWER END",
            rail_shape,
            "ALUMINUM_V05_NOMINAL_RAIL_OUTER_ENVELOPE",
            aluminum_cfg["interface_path"],
            aluminum_cfg["interface_sha256"],
            f"rail_system.{side}",
            (0.12, 0.40, 0.82),
            28,
        )
        axis_shape = Part.makeCylinder(
            0.45,
            upper_t - bearing_t,
            lower + axis * bearing_t,
            axis,
        )
        add_context_shape(
            work,
            aluminum_group,
            f"AL_V05_{side.upper()}_RAIL_AXIS",
            f"AL V0.5 {side.upper()} ACCEPTED RAIL AXIS",
            axis_shape,
            "ALUMINUM_V05_ACCEPTED_RAIL_AXIS",
            aluminum_cfg["interface_path"],
            aluminum_cfg["interface_sha256"],
            f"accepted_axes_head.{side}",
            (1.0, 0.86, 0.12),
            0,
        )
        socket_shape = oriented_square_prism(
            App,
            Part,
            lower,
            axis,
            across,
            other,
            socket_width / 2.0,
            socket_width / 2.0,
            upper_t - socket_depth,
            upper_t,
        )
        socket_obj = add_context_shape(
            work,
            aluminum_group,
            f"AL_V05_{side.upper()}_SOCKET_CLEARANCE_TARGET",
            f"AL V0.5 {side.upper()} 21 x 21 x 30 mm SOCKET CLEARANCE TARGET — NO BODY",
            socket_shape,
            "ALUMINUM_V05_SOCKET_CLEARANCE_TARGET__NOT_SOCKET_BODY",
            aluminum_cfg["interface_path"],
            aluminum_cfg["interface_sha256"],
            f"rail_system.socket.{side}",
            (0.88, 0.18, 0.78),
            78,
        )
        socket_obj.addProperty("App::PropertyString", "Limitation", "Coordination")
        socket_obj.Limitation = (
            "Clearance volume derived from the controlled 21 mm opening and 30 mm "
            "insertion depth; no production receiver wall is asserted."
        )
        socket_obj.setEditorMode("Limitation", 1)
        target = App.Vector(
            *[
                float(value)
                for value in rail_system["upper_shell_search_targets_head_mm"][side]
            ]
        )
        marker_shape = Part.makeSphere(2.5, target)
        add_context_shape(
            work,
            aluminum_group,
            f"AL_V05_{side.upper()}_UPPER_SEARCH_TARGET",
            f"AL V0.5 {side.upper()} UPPER-SHELL SEARCH TARGET",
            marker_shape,
            "ALUMINUM_V05_UPPER_SHELL_SEARCH_TARGET",
            aluminum_cfg["interface_path"],
            aluminum_cfg["interface_sha256"],
            f"upper_shell_search_targets_head_mm.{side}",
            (0.96, 0.86, 0.12),
            0,
        )

    for source_name in opened_docs:
        App.closeDocument(source_name)
    opened_docs.clear()

    work.recompute()
    all_shape_objects = [
        obj for obj in work.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()
    ]
    fused_types = [
        obj.Name
        for obj in work.Objects
        if obj.TypeId in {"Part::Fuse", "Part::MultiFuse", "Part::Cut", "Part::Common"}
    ]
    if fused_types:
        raise RuntimeError(f"Forbidden Boolean feature objects: {fused_types}")
    if len(upper_components) != 41:
        raise RuntimeError("Working assembly does not contain exactly 41 upper owners")

    work.saveAs(str(output_path))
    App.closeDocument(work.Name)

    reopened = App.openDocument(str(output_path))
    reopened_upper = [
        obj
        for obj in reopened.Objects
        if hasattr(obj, "AssemblyRole")
        and str(obj.AssemblyRole).startswith("WORKING_RIGHT_UPPER_OWNER_C")
    ]
    reopened_shapes = [
        obj
        for obj in reopened.Objects
        if hasattr(obj, "Shape") and not obj.Shape.isNull()
    ]
    if len(reopened_upper) != 41:
        raise RuntimeError(
            f"Reopened assembly has {len(reopened_upper)} upper owners, expected 41"
        )
    reopened_summary = {
        "object_count": len(reopened.Objects),
        "shape_object_count": len(reopened_shapes),
        "right_upper_owner_count": len(reopened_upper),
        "document_label": reopened.Label,
    }
    App.closeDocument(reopened.Name)

    pins_after = verify_pins(repo_root, pins)
    validation = {
        "schema_version": "cat-head-right-upper-as-printed-working-assembly-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__WORKING_ASSEMBLY_CREATED__NOT_PRINT_APPROVED",
        "freecad_version": App.Version(),
        "contract_path": str(contract_path.relative_to(repo_root)),
        "contract_sha256": sha256(contract_path),
        "generator_path": str(Path(__file__).resolve().relative_to(repo_root)),
        "generator_sha256": sha256(Path(__file__).resolve()),
        "output_fcstd": str(output_path.relative_to(repo_root)),
        "output_fcstd_sha256": sha256(output_path),
        "source_pins_before": pins_before,
        "source_pins_after": pins_after,
        "source_hashes_unchanged": pins_before == pins_after,
        "source_documents_saved": False,
        "source_geometry_modified": False,
        "assembly_fused": False,
        "geometry_exported": False,
        "sliced": False,
        "left_upper_owner_present": False,
        "right_upper_component_ids": actual_ids,
        "right_upper_component_count": len(actual_ids),
        "copied_shape_signatures": copied,
        "created_shape_object_count_before_save": len(all_shape_objects),
        "reopened": reopened_summary,
        "limitations": [
            "This is a non-fused working assembly, not a print release.",
            "The lower masters and printed eye parts are frozen context copies.",
            "The translucent lenses are approved but not yet physically printed.",
            "No trusted LEFT-upper owner is present.",
            "The aluminum socket shapes are clearance targets, not production receiver bodies.",
            "Exact collision classification remains the next gate."
        ],
    }
    validation_path.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": validation["status"],
        "output_fcstd": validation["output_fcstd"],
        "output_fcstd_sha256": validation["output_fcstd_sha256"],
        "right_upper_component_count": len(actual_ids),
        "shape_object_count": reopened_summary["shape_object_count"],
        "source_hashes_unchanged": validation["source_hashes_unchanged"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
