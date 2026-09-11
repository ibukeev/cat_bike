#!/usr/bin/env python3
"""Independent, read-only release validation for the approved C002 V2 candidate.

This verifier never imports or invokes either C002 generator. It opens the
hash-pinned no-op snapshot and candidate without saving them, reconstructs the
approved Route 2 result independently in memory, measures the candidate, and
writes only the contracted JSON report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import zipfile
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Part


VALIDATION_ID = "c002-rounded-terminal-profile-prototype-v2-release-validation-001"
TARGET_OBJECT = "RETAINED_RIGHT_UPPER_C002_V34"
PROTECTED_ROOT_OBJECT = "RETAINED_RIGHT_UPPER_C042_V34"
SHAPE_SUFFIX = ".Shape.brp"


class GateFailure(RuntimeError):
    def __init__(self, gate_id: str, actual: Any, expected: Any) -> None:
        super().__init__(gate_id)
        self.gate_id = gate_id
        self.actual = actual
        self.expected = expected

    def record(self) -> dict[str, Any]:
        return {
            "gate": self.gate_id,
            "actual": self.actual,
            "expected": self.expected,
        }


def require_gate(
    condition: bool,
    gate_id: str,
    actual: Any,
    expected: Any,
) -> None:
    if not condition:
        raise GateFailure(gate_id, actual, expected)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--freecad-appdir", type=Path, required=True)
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    resolved = start.resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"repository root not found from {start}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_repo_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise GateFailure(
            "INPUT_PATH_OUTSIDE_REPOSITORY",
            str(path),
            str(root),
        ) from exc
    return path


def verify_file_input(
    root: Path,
    label: str,
    spec: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    path = checked_repo_path(root, str(spec["path"]))
    require_gate(path.is_file(), f"{label.upper()}_MISSING", str(path), "existing file")
    observed = sha256_file(path)
    expected = str(spec["sha256"])
    require_gate(observed == expected, f"{label.upper()}_HASH", observed, expected)
    return path, {
        "path": str(path.relative_to(root)),
        "sha256": observed,
        "matches": True,
    }


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_shape_digests(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path, "r") as archive:
        names: set[str] = set()
        result: dict[str, str] = {}
        for info in archive.infolist():
            require_gate(
                info.filename not in names,
                "FCSTD_DUPLICATE_ARCHIVE_ENTRY",
                info.filename,
                "unique archive entry",
            )
            names.add(info.filename)
            if "/" in info.filename or not info.filename.endswith(SHAPE_SUFFIX):
                continue
            object_name = info.filename[: -len(SHAPE_SUFFIX)]
            result[object_name] = sha256_bytes(archive.read(info))
    return result


def vector(values: Sequence[float]) -> App.Vector:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def normalized(value: App.Vector, label: str) -> App.Vector:
    length = float(value.Length)
    require_gate(length > 0.0, f"{label.upper()}_ZERO_LENGTH", length, "> 0")
    return value / length


def vector_values(value: App.Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def angle_deg(first: App.Vector, second: App.Vector, unoriented: bool = False) -> float:
    first_n = normalized(first, "angle first vector")
    second_n = normalized(second, "angle second vector")
    dot = float(first_n.dot(second_n))
    if unoriented:
        dot = abs(dot)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def aligned(value: App.Vector, reference: App.Vector) -> App.Vector:
    current = normalized(value, "aligned vector")
    return -current if current.dot(reference) < 0.0 else current


def placement_record(placement: App.Placement) -> dict[str, Any]:
    return {
        "base": vector_values(placement.Base),
        "rotation_q": [float(item) for item in placement.Rotation.Q],
    }


def placements_match(first: App.Placement, second: App.Placement) -> bool:
    if float((first.Base - second.Base).Length) > 1.0e-12:
        return False
    return all(
        abs(float(a) - float(b)) <= 1.0e-12
        for a, b in zip(first.Rotation.Q, second.Rotation.Q)
    )


def runtime_record() -> dict[str, Any]:
    version = list(App.Version())
    return {
        "freecad_version": version,
        "freecad_program_version": f"{version[0]}.{version[1]}R{version[3]}",
        "occt_version": str(Part.OCC_VERSION),
        "python_version": platform.python_version(),
        "platform_machine": platform.machine(),
    }


def verify_runtime(
    appdir: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    expected = {
        "freecad_version": manifest["freecad"]["version_record"],
        "freecad_program_version": manifest["freecad"]["program_version"],
        "occt_version": manifest["occt"]["version"],
        "python_version": manifest["python"]["version"],
        "platform_machine": manifest["platform"]["machine"],
    }
    observed = runtime_record()
    require_gate(observed == expected, "RUNTIME_IDENTITY", observed, expected)

    artifact_records: list[dict[str, Any]] = []
    appdir = appdir.resolve()
    for item in manifest["artifacts"]:
        path = (appdir / str(item["path"])).resolve()
        require_gate(
            path.is_file(),
            "RUNTIME_ARTIFACT_MISSING",
            str(path),
            "existing pinned runtime artifact",
        )
        observed_hash = sha256_file(path)
        expected_hash = str(item["sha256"])
        require_gate(
            observed_hash == expected_hash,
            "RUNTIME_ARTIFACT_HASH",
            {"path": str(item["path"]), "sha256": observed_hash},
            {"path": str(item["path"]), "sha256": expected_hash},
        )
        artifact_records.append(
            {
                "path": str(item["path"]),
                "sha256": observed_hash,
                "matches": True,
            }
        )
    return {
        "observed": observed,
        "expected": expected,
        "artifacts": artifact_records,
        "status": "PASS",
    }


def shape_metrics(shape: Part.Shape) -> dict[str, Any]:
    messages: list[str] = []
    try:
        raw = shape.check(True)
        if raw:
            messages = [str(item) for item in raw]
    except Exception as exc:
        messages = [f"OCCT check raised: {exc}"]
    box = shape.BoundBox
    return {
        "null": bool(shape.isNull()),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "vertex_count": len(shape.Vertexes),
        "volume_mm3": float(shape.Volume),
        "surface_area_mm2": float(shape.Area),
        "bounding_box_mm": {
            "min": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "max": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        },
        "occt_check_messages": messages,
    }


def require_candidate_health(metrics: dict[str, Any]) -> None:
    require_gate(not metrics["null"], "TARGET_NULL", metrics["null"], False)
    require_gate(metrics["valid"], "TARGET_OCCT_VALID", metrics["valid"], True)
    require_gate(metrics["closed"], "TARGET_CLOSED", metrics["closed"], True)
    require_gate(
        metrics["solid_count"] == 1,
        "TARGET_SINGLE_SOLID",
        metrics["solid_count"],
        1,
    )
    require_gate(
        not metrics["occt_check_messages"],
        "TARGET_DEEP_OCCT_CHECK",
        metrics["occt_check_messages"],
        [],
    )


def point_from_local(
    local_u: float,
    local_v: float,
    local_t: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> App.Vector:
    return origin + axis_u * local_u + axis_v * local_v + axis_t * local_t


def closed_wire(points: Sequence[App.Vector]) -> Part.Wire:
    return Part.makePolygon([*points, points[0]])


def square_wire(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    half_width: float,
) -> Part.Wire:
    return closed_wire(
        [
            point_from_local(-half_width, -half_width, station_t, origin, axis_u, axis_v, axis_t),
            point_from_local(half_width, -half_width, station_t, origin, axis_u, axis_v, axis_t),
            point_from_local(half_width, half_width, station_t, origin, axis_u, axis_v, axis_t),
            point_from_local(-half_width, half_width, station_t, origin, axis_u, axis_v, axis_t),
        ]
    )


def corner_removal_wire(
    sign_u: float,
    sign_v: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    half_width: float,
    radius: float,
) -> Part.Wire:
    corner = point_from_local(
        sign_u * half_width,
        sign_v * half_width,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    tangent_v = point_from_local(
        sign_u * half_width,
        sign_v * (half_width - radius),
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    tangent_u = point_from_local(
        sign_u * (half_width - radius),
        sign_v * half_width,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    diagonal = half_width - radius + radius / math.sqrt(2.0)
    arc_midpoint = point_from_local(
        sign_u * diagonal,
        sign_v * diagonal,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    return Part.Wire(
        [
            Part.makeLine(corner, tangent_v),
            Part.Arc(tangent_v, arc_midpoint, tangent_u).toShape(),
            Part.makeLine(tangent_u, corner),
        ]
    )


def local_box(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
    t_min: float,
    t_max: float,
) -> Part.Shape:
    face = Part.Face(
        closed_wire(
            [
                point_from_local(u_min, v_min, t_min, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_max, t_min, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_max, t_max, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_min, t_max, origin, axis_u, axis_v, axis_t),
            ]
        )
    )
    return face.extrude(axis_u * (u_max - u_min))


def build_independent_expected_shape(
    snapshot_shape: Part.Shape,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> dict[str, Part.Shape]:
    profile = parameters["profile"]
    anchors = parameters["anchors"]
    mouth_t = float(profile["mouth_t_mm"])
    lead_transition_t = mouth_t + float(profile["lead_in_depth_mm"])
    stop_t = float(profile["stop_t_mm"])
    straight_half = float(profile["straight_across_flats_mm"]) / 2.0
    mouth_half = float(profile["mouth_across_flats_mm"]) / 2.0
    transition_start = float(profile["transition_start_t_mm"])
    stop_radius = float(profile["terminal_stop_radius_mm"])

    extension = 0.20
    target_void = Part.makeLoft(
        [
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                mouth_t - extension,
                mouth_half + extension,
            ),
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                lead_transition_t,
                straight_half,
            ),
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                stop_t,
                straight_half,
            ),
        ],
        True,
        True,
    )
    require_gate(
        not target_void.isNull() and target_void.isValid() and len(target_void.Solids) == 1,
        "INDEPENDENT_FULL_VOID_CONSTRUCTION",
        shape_metrics(target_void),
        "one valid solid",
    )

    for sign_u, sign_v in ((1.0, 1.0), (1.0, -1.0), (-1.0, -1.0), (-1.0, 1.0)):
        apex = Part.Vertex(
            point_from_local(
                sign_u * straight_half,
                sign_v * straight_half,
                transition_start,
                origin,
                axis_u,
                axis_v,
                axis_t,
            )
        )
        stop_wire = corner_removal_wire(
            sign_u,
            sign_v,
            origin,
            axis_u,
            axis_v,
            axis_t,
            stop_t,
            straight_half,
            stop_radius,
        )
        cutter = Part.makeLoft([apex, stop_wire], True, True)
        require_gate(
            not cutter.isNull() and cutter.isValid() and len(cutter.Solids) == 1,
            "INDEPENDENT_CORNER_CUTTER_CONSTRUCTION",
            shape_metrics(cutter),
            "one valid solid",
        )
        target_void = target_void.cut(cutter)

    require_gate(
        not target_void.isNull() and target_void.isValid() and len(target_void.Solids) == 1,
        "INDEPENDENT_ROUTE2_VOID_CONSTRUCTION",
        shape_metrics(target_void),
        "one valid solid",
    )

    current_half = float(profile["current_straight_across_flats_mm"]) / 2.0
    stop_face = Part.Face(
        square_wire(
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(anchors["stop_plane_t_mm"]),
            current_half,
        )
    )
    boolean_overlap = 0.02
    plug_face = stop_face.copy()
    plug_face.translate(axis_t * boolean_overlap)
    restoration_plug = plug_face.extrude(
        -axis_t
        * (float(profile["additive_infill_axial_length_mm"]) + boolean_overlap)
    )
    restored = snapshot_shape.fuse(restoration_plug)
    expected = restored.cut(target_void)
    require_gate(
        not expected.isNull() and expected.isValid() and expected.isClosed() and len(expected.Solids) == 1,
        "INDEPENDENT_EXPECTED_TARGET_CONSTRUCTION",
        shape_metrics(expected),
        "one valid closed solid",
    )

    old_void = stop_face.extrude(
        -axis_t * float(profile["exact_clear_depth_mm"])
    )
    review_clip = local_box(
        origin,
        axis_u,
        axis_v,
        axis_t,
        -20.0,
        20.0,
        -20.0,
        20.0,
        mouth_t,
        stop_t,
    )
    review_void = target_void.common(review_clip)
    return {
        "expected": expected,
        "target_void": target_void,
        "review_void": review_void,
        "old_void": old_void,
        "restoration_plug": restoration_plug,
    }


def difference_volume(first: Part.Shape, second: Part.Shape) -> float:
    result = first.cut(second)
    return 0.0 if result.isNull() else float(result.Volume)


def common_volume(first: Part.Shape, second: Part.Shape) -> float:
    result = first.common(second)
    return 0.0 if result.isNull() else float(result.Volume)


def face_normal(face: Part.Face) -> App.Vector:
    u_min, u_max, v_min, v_max = face.ParameterRange
    return normalized(
        face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0),
        "face normal",
    )


def local_coordinates(
    point: App.Vector,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> tuple[float, float, float]:
    delta = point - origin
    return (
        float(delta.dot(axis_u)),
        float(delta.dot(axis_v)),
        float(delta.dot(axis_t)),
    )


def measure_straight_cavity_frame(
    shape: Part.Shape,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    half_width: float,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {
        "u_negative": [],
        "u_positive": [],
        "v_negative": [],
        "v_positive": [],
    }
    for index, face in enumerate(shape.Faces, start=1):
        if "plane" not in type(face.Surface).__name__.lower():
            continue
        coordinates = [
            local_coordinates(vertex.Point, origin, axis_u, axis_v, axis_t)
            for vertex in face.Vertexes
        ]
        if not coordinates:
            continue
        values_u = [item[0] for item in coordinates]
        values_v = [item[1] for item in coordinates]
        values_t = [item[2] for item in coordinates]
        u_range = max(values_u) - min(values_u)
        v_range = max(values_v) - min(values_v)
        t_range = max(values_t) - min(values_t)
        mean_u = sum(values_u) / len(values_u)
        mean_v = sum(values_v) / len(values_v)
        normal = face_normal(face)

        record = {
            "face_identifier": f"Face{index}",
            "mean_u_mm": mean_u,
            "mean_v_mm": mean_v,
            "u_range_mm": u_range,
            "v_range_mm": v_range,
            "t_range_mm": t_range,
            "normal": vector_values(normal),
        }
        if (
            u_range <= 1.0e-4
            and v_range >= 5.0
            and t_range >= 5.0
            and abs(abs(mean_u) - half_width) <= 0.01
        ):
            groups["u_positive" if mean_u > 0.0 else "u_negative"].append(record)
        if (
            v_range <= 1.0e-4
            and u_range >= 5.0
            and t_range >= 5.0
            and abs(abs(mean_v) - half_width) <= 0.01
        ):
            groups["v_positive" if mean_v > 0.0 else "v_negative"].append(record)

    for name, records in groups.items():
        require_gate(
            bool(records),
            "CAVITY_STRAIGHT_PLANE_SIGNATURE",
            {"missing_group": name, "groups": groups},
            "at least one complete-signature face in every +/-u and +/-v group",
        )

    chosen = {
        name: sorted(
            records,
            key=lambda item: (
                abs(abs(item["mean_u_mm"] if name.startswith("u") else item["mean_v_mm"]) - half_width),
                -item["t_range_mm"],
                item["face_identifier"],
            ),
        )[0]
        for name, records in groups.items()
    }

    u_normal = aligned(vector(chosen["u_positive"]["normal"]), axis_u)
    v_normal = aligned(vector(chosen["v_positive"]["normal"]), axis_v)
    measured_t = normalized(u_normal.cross(v_normal), "measured cavity t")
    measured_t = aligned(measured_t, axis_t)
    width_u = (
        float(chosen["u_positive"]["mean_u_mm"])
        - float(chosen["u_negative"]["mean_u_mm"])
    )
    width_v = (
        float(chosen["v_positive"]["mean_v_mm"])
        - float(chosen["v_negative"]["mean_v_mm"])
    )
    return {
        "selected_faces": chosen,
        "across_flats_u_mm": width_u,
        "across_flats_v_mm": width_v,
        "measured_u_axis": vector_values(u_normal),
        "measured_v_axis": vector_values(v_normal),
        "measured_t_axis": vector_values(measured_t),
    }


def cylinder_surface_records(
    shape: Part.Shape,
    origin: App.Vector,
    expected_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    radius_mm: float,
    station_t_mm: float,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, face in enumerate(shape.Faces, start=1):
        surface = face.Surface
        if "cylinder" not in type(surface).__name__.lower():
            continue
        if not all(hasattr(surface, name) for name in ("Radius", "Axis", "Center")):
            continue
        radius = float(surface.Radius)
        center = surface.Center
        axis = aligned(surface.Axis, expected_u)
        _, local_v, local_t = local_coordinates(
            center,
            origin,
            expected_u,
            axis_v,
            axis_t,
        )
        if abs(radius - radius_mm) > 0.01:
            continue
        if abs(local_t - station_t_mm) > 0.01 or abs(local_v) > 0.01:
            continue
        records.append(
            {
                "face_identifier": f"Face{index}",
                "radius_mm": radius,
                "axis": vector_values(axis),
                "axis_line_v_mm": local_v,
                "axis_line_t_mm": local_t,
            }
        )
    return records


def averaged_axis(records: list[dict[str, Any]], reference: App.Vector) -> App.Vector:
    total = App.Vector(0.0, 0.0, 0.0)
    for item in records:
        total = total + aligned(vector(item["axis"]), reference)
    return aligned(normalized(total, "averaged cylinder axis"), reference)


def exact_route2_solution(evidence: dict[str, Any]) -> dict[str, Any]:
    for solution in evidence["route_2_terminal_radius"]["solutions"]:
        if abs(float(solution["required_gap_mm"]) - 2.4) <= 1.0e-12:
            return solution
    raise GateFailure(
        "ROUTE2_EVIDENCE_SOLUTION",
        evidence["route_2_terminal_radius"]["solutions"],
        "one 2.4 mm Route 2 solution",
    )


def verify_numeric_contract(
    iteration: dict[str, Any],
    evidence: dict[str, Any],
    interface: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_gate(
        iteration["iteration_id"] == "c002-rounded-terminal-profile-prototype-v2",
        "ITERATION_ID",
        iteration["iteration_id"],
        "c002-rounded-terminal-profile-prototype-v2",
    )
    require_gate(
        iteration["target_object"] == TARGET_OBJECT,
        "TARGET_OBJECT",
        iteration["target_object"],
        TARGET_OBJECT,
    )
    mutations = iteration["allowed_mutations"]
    require_gate(
        len(mutations) == 1
        and mutations[0]["kind"] == "replace_geometry"
        and mutations[0]["object"] == TARGET_OBJECT,
        "MUTATION_SCOPE",
        mutations,
        "one replace_geometry mutation on C002",
    )
    parameters = mutations[0]["parameters"]
    solution = exact_route2_solution(evidence)
    profile = parameters["profile"]
    root = parameters["protected_root"]
    rail = parameters["physical_prototype_rail"]
    exact_checks = {
        "terminal_stop_radius_mm": (
            profile["terminal_stop_radius_mm"],
            solution["stop_radius_mm"],
        ),
        "rounded_transition_length_mm": (
            profile["rounded_transition_length_mm"],
            solution["transition_length_mm"],
        ),
        "transition_start_t_mm": (
            profile["transition_start_t_mm"],
            solution["transition_start_t_mm"],
        ),
        "worst_insertion_path_radius_mm": (
            profile["worst_insertion_path_radius_mm"],
            solution["maximum_radius_encountered_by_seated_rail_mm"],
        ),
        "additive_infill_start_t_mm": (
            profile["additive_infill_start_t_mm"],
            solution["additive_infill_start_t_mm"],
        ),
        "additive_infill_axial_length_mm": (
            profile["additive_infill_axial_length_mm"],
            solution["additive_infill_axial_length_mm"],
        ),
        "protected_common_volume_mm3": (
            root["exact_common_volume_mm3"],
            evidence["protected_root"]["exact_volume_mm3"],
        ),
        "minimum_tube_corner_radius_mm": (
            rail["minimum_outside_corner_radius_mm"],
            solution["tube_radius_for_0_5mm_clearance_mm_for_19_00_to_19_05"][1],
        ),
    }
    for label, (actual, expected) in exact_checks.items():
        require_gate(
            abs(float(actual) - float(expected)) <= 1.0e-11,
            f"ROUTE2_NUMERIC_{label.upper()}",
            actual,
            expected,
        )

    require_gate(
        interface["metal_handoff_record"]["revision"]
        == "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
        "M2_INTERFACE_REVISION",
        interface["metal_handoff_record"]["revision"],
        "CAT-HEAD-SHELL-ALUMINUM-V0.5-M2",
    )
    interface_socket = interface["rail_system"]["socket"]
    interface_checks = {
        "straight_across_flats_mm": (
            profile["straight_across_flats_mm"],
            interface_socket["printed_opening_width_mm"],
        ),
        "mouth_across_flats_mm": (
            profile["mouth_across_flats_mm"],
            interface_socket["lead_in_mouth_width_mm"],
        ),
        "lead_in_depth_mm": (
            profile["lead_in_depth_mm"],
            interface_socket["lead_in_depth_mm"],
        ),
        "structural_length_mm": (
            profile["structural_length_attribution_mm"],
            interface_socket["insertion_depth_mm"],
        ),
    }
    for label, (actual, expected) in interface_checks.items():
        require_gate(
            abs(float(actual) - float(expected)) <= 1.0e-12,
            f"M2_SOCKET_{label.upper()}",
            actual,
            expected,
        )
    return parameters, {
        "route2_exact_checks": exact_checks,
        "m2_socket_checks": interface_checks,
        "interface_revision": interface["metal_handoff_record"]["revision"],
    }


def validate(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Path]]:
    root = repository_root(args.contract)
    contract_path = args.contract.resolve()
    contract = load_json(contract_path)
    require_gate(
        contract.get("validation_id") == VALIDATION_ID,
        "VALIDATION_ID",
        contract.get("validation_id"),
        VALIDATION_ID,
    )
    require_gate(
        contract.get("mode") == "read_only_independent_release_validation",
        "VALIDATION_MODE",
        contract.get("mode"),
        "read_only_independent_release_validation",
    )

    output_dir = checked_repo_path(root, contract["output"]["directory"])
    report_path = checked_repo_path(root, contract["output"]["report"])
    try:
        report_path.relative_to(output_dir)
    except ValueError as exc:
        raise GateFailure(
            "REPORT_PATH_SCOPE",
            str(report_path),
            f"inside {output_dir}",
        ) from exc
    require_gate(
        not output_dir.exists(),
        "RELEASE_VALIDATION_OUTPUT_MUST_BE_NEW",
        str(output_dir),
        "absent before the single pass",
    )

    input_records: dict[str, Any] = {}
    input_paths: dict[str, Path] = {}
    for label, spec in contract["inputs"].items():
        path, record = verify_file_input(root, label, spec)
        input_paths[label] = path
        input_records[label] = record

    validator_path, validator_record = verify_file_input(
        root,
        "validator",
        contract["validator"],
    )
    require_gate(
        validator_path == Path(__file__).resolve(),
        "VALIDATOR_PATH",
        str(Path(__file__).resolve()),
        str(validator_path),
    )

    candidate_path = input_paths["candidate"]
    candidate_hash = input_records["candidate"]["sha256"]
    require_gate(
        contract["visual_approval"]["candidate_sha256"] == candidate_hash,
        "VISUAL_APPROVAL_CANDIDATE_HASH",
        contract["visual_approval"]["candidate_sha256"],
        candidate_hash,
    )

    iteration = load_json(input_paths["iteration_contract"])
    evidence = load_json(input_paths["route2_evidence"])
    interface = load_json(input_paths["interface"])
    preservation = load_json(input_paths["preservation_report"])
    runner_result = load_json(input_paths["runner_result"])
    runtime_manifest = load_json(input_paths["runtime_manifest"])

    require_gate(
        runner_result.get("status")
        == "CANDIDATE_READY__RUN_PRESERVATION_GATE_AND_FIXED_VIEWS",
        "RUNNER_RESULT_STATUS",
        runner_result.get("status"),
        "CANDIDATE_READY__RUN_PRESERVATION_GATE_AND_FIXED_VIEWS",
    )
    require_gate(
        runner_result["candidate"]["sha256"] == candidate_hash,
        "RUNNER_CANDIDATE_HASH",
        runner_result["candidate"]["sha256"],
        candidate_hash,
    )
    require_gate(
        preservation.get("status") == "PASS__READY_FOR_FIXED_VIEW_REVIEW",
        "PRESERVATION_STATUS",
        preservation.get("status"),
        "PASS__READY_FOR_FIXED_VIEW_REVIEW",
    )
    require_gate(
        preservation["candidate"]["sha256"] == candidate_hash,
        "PRESERVATION_CANDIDATE_HASH",
        preservation["candidate"]["sha256"],
        candidate_hash,
    )
    require_gate(
        not preservation.get("errors")
        and not preservation.get("protected_differences")
        and not preservation.get("target_errors"),
        "PRESERVATION_ERRORS",
        {
            "errors": preservation.get("errors"),
            "protected_differences": preservation.get("protected_differences"),
            "target_errors": preservation.get("target_errors"),
        },
        "all empty",
    )

    parameters, numeric_record = verify_numeric_contract(iteration, evidence, interface)
    runtime = verify_runtime(args.freecad_appdir, runtime_manifest)

    frame = parameters["rail_frame"]
    origin = vector(frame["origin_head_mm"])
    axis_t = normalized(vector(frame["t_axis"]), "contract t axis")
    axis_u = normalized(vector(frame["u_axis"]), "contract u axis")
    axis_v = normalized(vector(frame["v_axis"]), "contract v axis")
    orthogonality = {
        "u_dot_v": float(axis_u.dot(axis_v)),
        "u_dot_t": float(axis_u.dot(axis_t)),
        "v_dot_t": float(axis_v.dot(axis_t)),
        "u_cross_v_minus_t_length": float((axis_u.cross(axis_v) - axis_t).Length),
    }
    require_gate(
        max(abs(value) for key, value in orthogonality.items() if "dot" in key)
        <= 1.0e-9
        and orthogonality["u_cross_v_minus_t_length"] <= 1.0e-9,
        "CONTRACT_FRAME_ORTHONORMAL",
        orthogonality,
        "orthogonal right-handed frame within 1e-9",
    )

    snapshot_path = input_paths["no_op_snapshot"]
    snapshot_shapes = raw_shape_digests(snapshot_path)
    candidate_shapes = raw_shape_digests(candidate_path)
    require_gate(
        set(snapshot_shapes) == set(candidate_shapes),
        "RAW_SHAPE_OBJECT_SET",
        {
            "missing": sorted(set(snapshot_shapes) - set(candidate_shapes)),
            "added": sorted(set(candidate_shapes) - set(snapshot_shapes)),
        },
        {"missing": [], "added": []},
    )
    protected_names = sorted(set(snapshot_shapes) - {TARGET_OBJECT})
    protected_mismatches = {
        name: {
            "snapshot": snapshot_shapes[name],
            "candidate": candidate_shapes[name],
        }
        for name in protected_names
        if snapshot_shapes[name] != candidate_shapes[name]
    }
    require_gate(
        not protected_mismatches,
        "PROTECTED_RAW_BREP_IDENTITY",
        protected_mismatches,
        {},
    )
    require_gate(
        snapshot_shapes[TARGET_OBJECT] != candidate_shapes[TARGET_OBJECT],
        "TARGET_RAW_BREP_CHANGED",
        {
            "snapshot": snapshot_shapes[TARGET_OBJECT],
            "candidate": candidate_shapes[TARGET_OBJECT],
        },
        "different target BREP digests",
    )

    snapshot_document = App.openDocument(str(snapshot_path))
    candidate_document = App.openDocument(str(candidate_path))
    try:
        snapshot_objects = {obj.Name: obj for obj in snapshot_document.Objects}
        candidate_objects = {obj.Name: obj for obj in candidate_document.Objects}
        require_gate(
            set(snapshot_objects) == set(candidate_objects),
            "FREECAD_OBJECT_SET",
            {
                "missing": sorted(set(snapshot_objects) - set(candidate_objects)),
                "added": sorted(set(candidate_objects) - set(snapshot_objects)),
            },
            {"missing": [], "added": []},
        )
        snapshot_target = snapshot_objects.get(TARGET_OBJECT)
        candidate_target = candidate_objects.get(TARGET_OBJECT)
        candidate_c042 = candidate_objects.get(PROTECTED_ROOT_OBJECT)
        snapshot_c042 = snapshot_objects.get(PROTECTED_ROOT_OBJECT)
        require_gate(
            all(item is not None for item in (snapshot_target, candidate_target, candidate_c042, snapshot_c042)),
            "REQUIRED_OBJECTS_PRESENT",
            {
                "snapshot_target": snapshot_target is not None,
                "candidate_target": candidate_target is not None,
                "snapshot_c042": snapshot_c042 is not None,
                "candidate_c042": candidate_c042 is not None,
            },
            "all true",
        )
        require_gate(
            candidate_target.TypeId == snapshot_target.TypeId == "Part::Feature",
            "TARGET_TYPE",
            {
                "snapshot": snapshot_target.TypeId,
                "candidate": candidate_target.TypeId,
            },
            "Part::Feature",
        )
        require_gate(
            candidate_target.Label == snapshot_target.Label,
            "TARGET_LABEL",
            candidate_target.Label,
            snapshot_target.Label,
        )
        require_gate(
            placements_match(candidate_target.Placement, snapshot_target.Placement),
            "TARGET_PLACEMENT",
            placement_record(candidate_target.Placement),
            placement_record(snapshot_target.Placement),
        )

        target_shape = candidate_target.Shape.copy()
        snapshot_shape = snapshot_target.Shape.copy()
        c042_shape = candidate_c042.Shape.copy()
        candidate_metrics = shape_metrics(target_shape)
        require_candidate_health(candidate_metrics)

        construction = build_independent_expected_shape(
            snapshot_shape,
            parameters,
            origin,
            axis_u,
            axis_v,
            axis_t,
        )
        tolerances = contract["tolerances"]
        missing_volume = difference_volume(construction["expected"], target_shape)
        extra_volume = difference_volume(target_shape, construction["expected"])
        shape_tolerance = float(tolerances["shape_symmetric_difference_volume_mm3_max"])
        require_gate(
            missing_volume <= shape_tolerance and extra_volume <= shape_tolerance,
            "EXACT_ROUTE2_EXPECTED_GEOMETRY",
            {
                "expected_minus_candidate_mm3": missing_volume,
                "candidate_minus_expected_mm3": extra_volume,
            },
            {
                "each_mm3_max": shape_tolerance,
                "construction": "independent in-memory Route 2 reconstruction",
            },
        )

        added = target_shape.cut(snapshot_shape)
        removed = snapshot_shape.cut(target_shape)
        added_volume = 0.0 if added.isNull() else float(added.Volume)
        removed_volume = 0.0 if removed.isNull() else float(removed.Volume)
        added_outside_old_void = difference_volume(added, construction["old_void"])
        removed_outside_target_void = difference_volume(
            removed,
            construction["target_void"],
        )
        exterior_tolerance = float(
            tolerances["change_outside_authorized_socket_envelope_mm3_max"]
        )
        require_gate(
            added_outside_old_void <= exterior_tolerance
            and removed_outside_target_void <= exterior_tolerance,
            "ZERO_EXTERIOR_DEVIATION",
            {
                "added_outside_old_void_mm3": added_outside_old_void,
                "removed_outside_target_void_mm3": removed_outside_target_void,
            },
            {"each_mm3_max": exterior_tolerance},
        )

        candidate_common = target_shape.common(c042_shape)
        snapshot_common = snapshot_shape.common(snapshot_c042.Shape)
        expected_common_volume = float(
            parameters["protected_root"]["exact_common_volume_mm3"]
        )
        common_tolerance = float(tolerances["protected_common_volume_mm3"])
        candidate_common_volume = (
            0.0 if candidate_common.isNull() else float(candidate_common.Volume)
        )
        snapshot_common_volume = (
            0.0 if snapshot_common.isNull() else float(snapshot_common.Volume)
        )
        require_gate(
            abs(candidate_common_volume - expected_common_volume) <= common_tolerance,
            "C002_C042_COMMON_VOLUME",
            candidate_common_volume,
            {
                "value_mm3": expected_common_volume,
                "tolerance_mm3": common_tolerance,
            },
        )
        require_gate(
            abs(candidate_common_volume - snapshot_common_volume) <= common_tolerance,
            "C002_C042_COMMON_PRESERVATION",
            candidate_common_volume,
            {
                "snapshot_mm3": snapshot_common_volume,
                "tolerance_mm3": common_tolerance,
            },
        )

        ligament_distance = float(
            construction["review_void"].distToShape(candidate_common)[0]
        )
        ligament_minimum = float(
            parameters["profile"]["finished_minimum_cavity_to_root_ligament_mm"]
        )
        ligament_epsilon = float(tolerances["distance_numeric_epsilon_mm"])
        require_gate(
            ligament_distance + ligament_epsilon >= ligament_minimum,
            "CAVITY_TO_ROOT_LIGAMENT",
            ligament_distance,
            {
                "minimum_mm": ligament_minimum,
                "numeric_epsilon_mm": ligament_epsilon,
            },
        )

        m4 = parameters["m4_tunnel"]
        m4_radius = float(m4["nominal_clearance_diameter_mm"]) / 2.0
        m4_station = float(m4["station_t_mm"])
        m4_gauge = Part.makeCylinder(
            m4_radius,
            120.0,
            origin + axis_t * m4_station - axis_u * 60.0,
            axis_u,
        )
        m4_added_change = common_volume(added, m4_gauge)
        m4_removed_change = common_volume(removed, m4_gauge)
        m4_volume_tolerance = float(tolerances["m4_changed_volume_mm3_max"])
        require_gate(
            m4_added_change <= m4_volume_tolerance
            and m4_removed_change <= m4_volume_tolerance,
            "M4_TUNNEL_UNCHANGED_VOLUME",
            {
                "added_change_inside_m4_mm3": m4_added_change,
                "removed_change_inside_m4_mm3": m4_removed_change,
            },
            {"each_mm3_max": m4_volume_tolerance},
        )

        measured_frame = measure_straight_cavity_frame(
            target_shape,
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(parameters["profile"]["straight_across_flats_mm"]) / 2.0,
        )
        snapshot_measured_frame = measure_straight_cavity_frame(
            snapshot_shape,
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(parameters["profile"]["current_straight_across_flats_mm"]) / 2.0,
        )
        profile_tolerance = float(tolerances["profile_across_flats_mm"])
        for key in ("across_flats_u_mm", "across_flats_v_mm"):
            require_gate(
                abs(
                    float(measured_frame[key])
                    - float(parameters["profile"]["straight_across_flats_mm"])
                )
                <= profile_tolerance,
                "STRAIGHT_PROFILE_ACROSS_FLATS",
                {key: measured_frame[key]},
                {
                    "value_mm": parameters["profile"]["straight_across_flats_mm"],
                    "tolerance_mm": profile_tolerance,
                },
            )

        measured_t = vector(measured_frame["measured_t_axis"])
        measured_u = vector(measured_frame["measured_u_axis"])
        snapshot_measured_t = vector(snapshot_measured_frame["measured_t_axis"])
        snapshot_measured_u = vector(snapshot_measured_frame["measured_u_axis"])
        frame_axis_delta = angle_deg(measured_t, snapshot_measured_t)
        frame_roll_delta = angle_deg(measured_u, snapshot_measured_u)
        frame_preservation_limit = float(
            tolerances["socket_frame_preservation_angular_error_deg_max"]
        )
        require_gate(
            frame_axis_delta <= frame_preservation_limit
            and frame_roll_delta <= frame_preservation_limit,
            "SOCKET_AXIS_AND_ROLL_PRESERVATION",
            {
                "axis_delta_deg": frame_axis_delta,
                "roll_delta_deg": frame_roll_delta,
            },
            {"each_maximum_deg": frame_preservation_limit},
        )
        m2_t = normalized(
            vector(interface["rail_system"]["accepted_axes_head"]["right"]),
            "M2 right rail axis",
        )
        head_x = App.Vector(1.0, 0.0, 0.0)
        m2_roll_u = normalized(
            head_x - m2_t * float(head_x.dot(m2_t)),
            "M2 head-x-projected roll",
        )
        axis_limit = float(
            interface["validation_tolerances"]["rail_axis_angular_error_deg_max"]
        )
        roll_limit = float(tolerances["socket_roll_angular_error_deg_max"])
        contract_to_m2_axis = angle_deg(axis_t, m2_t)
        measured_to_m2_axis = angle_deg(measured_t, m2_t)
        measured_roll_to_m2 = angle_deg(measured_u, m2_roll_u)
        expected_cross_bolt_angle = float(
            interface["rail_system"]["socket"][
                "expected_cross_bolt_angle_from_head_x_deg"
            ]
        )
        measured_cross_bolt_angle = angle_deg(measured_u, head_x)
        cross_bolt_error = abs(measured_cross_bolt_angle - expected_cross_bolt_angle)
        require_gate(
            contract_to_m2_axis <= axis_limit,
            "CONTRACT_AXIS_MATCHES_M2",
            contract_to_m2_axis,
            {"maximum_deg": axis_limit},
        )
        require_gate(
            measured_to_m2_axis <= axis_limit,
            "CANDIDATE_SOCKET_AXIS_MATCHES_M2",
            measured_to_m2_axis,
            {"maximum_deg": axis_limit},
        )
        require_gate(
            parameters["rail_frame"]["roll_reference"]
            == interface["rail_system"]["socket"]["roll_reference"]
            == "head_x_projected",
            "ROLL_REFERENCE_MATCHES_M2",
            {
                "contract": parameters["rail_frame"]["roll_reference"],
                "interface": interface["rail_system"]["socket"]["roll_reference"],
            },
            "head_x_projected",
        )
        require_gate(
            measured_roll_to_m2 <= roll_limit,
            "CANDIDATE_SOCKET_ROLL_MATCHES_M2",
            {
                "cavity_u_to_m2_roll_deg": measured_roll_to_m2,
            },
            {"maximum_deg": roll_limit},
        )
        require_gate(
            cross_bolt_error <= roll_limit,
            "M4_CROSS_BOLT_ANGLE_MATCHES_M2",
            {
                "measured_deg": measured_cross_bolt_angle,
                "expected_deg": expected_cross_bolt_angle,
                "error_deg": cross_bolt_error,
            },
            {"maximum_error_deg": roll_limit},
        )

        immutable_after: dict[str, str] = {}
        for label in (
            "candidate",
            "no_op_snapshot",
            "baseline_fcstd",
            "iteration_contract",
            "interface",
            "route2_evidence",
            "runtime_manifest",
        ):
            observed_hash = sha256_file(input_paths[label])
            expected_hash = contract["inputs"][label]["sha256"]
            require_gate(
                observed_hash == expected_hash,
                f"{label.upper()}_CHANGED_DURING_VALIDATION",
                observed_hash,
                expected_hash,
            )
            immutable_after[label] = observed_hash

        metrics = {
            "input_integrity": input_records,
            "validator": validator_record,
            "contract_sha256": sha256_file(contract_path),
            "runtime": runtime,
            "numeric_contract": numeric_record,
            "raw_shape_preservation": {
                "snapshot_shape_count": len(snapshot_shapes),
                "candidate_shape_count": len(candidate_shapes),
                "protected_checked_count": len(protected_names),
                "protected_mismatches": protected_mismatches,
                "target_snapshot_sha256": snapshot_shapes[TARGET_OBJECT],
                "target_candidate_sha256": candidate_shapes[TARGET_OBJECT],
                "status": "PASS",
            },
            "target": {
                "object": TARGET_OBJECT,
                "health": candidate_metrics,
                "placement": placement_record(candidate_target.Placement),
            },
            "route2_geometry": {
                "expected_minus_candidate_mm3": missing_volume,
                "candidate_minus_expected_mm3": extra_volume,
                "tolerance_each_mm3": shape_tolerance,
                "straight_profile_measurement": measured_frame,
                "approved_profile": parameters["profile"],
                "status": "PASS",
            },
            "localized_change": {
                "added_material_mm3": added_volume,
                "removed_material_mm3": removed_volume,
                "added_outside_old_void_mm3": added_outside_old_void,
                "removed_outside_target_void_mm3": removed_outside_target_void,
                "zero_exterior_deviation": True,
                "status": "PASS",
            },
            "protected_root": {
                "object": PROTECTED_ROOT_OBJECT,
                "snapshot_common_volume_mm3": snapshot_common_volume,
                "candidate_common_volume_mm3": candidate_common_volume,
                "expected_common_volume_mm3": expected_common_volume,
                "common_volume_tolerance_mm3": common_tolerance,
                "cavity_to_root_ligament_mm": ligament_distance,
                "minimum_ligament_mm": ligament_minimum,
                "status": "PASS",
            },
            "m4_tunnel": {
                "geometry_kind": "unchanged 4.50 mm faceted tunnel",
                "gauge_axis": vector_values(axis_u),
                "gauge_station_t_mm": m4_station,
                "gauge_diameter_mm": 2.0 * m4_radius,
                "added_change_inside_tunnel_mm3": m4_added_change,
                "removed_change_inside_tunnel_mm3": m4_removed_change,
                "preservation_evidence": "zero candidate/snapshot material change inside the complete frozen tunnel gauge plus exact expected-target equivalence",
                "status": "PASS",
            },
            "m2_axis_and_roll": {
                "interface_revision": interface["metal_handoff_record"]["revision"],
                "frozen_m2_axis": vector_values(m2_t),
                "contract_axis": vector_values(axis_t),
                "measured_candidate_axis": vector_values(measured_t),
                "frozen_m2_roll_axis": vector_values(m2_roll_u),
                "measured_candidate_cavity_u_axis": vector_values(measured_u),
                "measured_snapshot_axis": vector_values(snapshot_measured_t),
                "measured_snapshot_cavity_u_axis": vector_values(snapshot_measured_u),
                "candidate_snapshot_axis_delta_deg": frame_axis_delta,
                "candidate_snapshot_roll_delta_deg": frame_roll_delta,
                "contract_to_m2_axis_error_deg": contract_to_m2_axis,
                "candidate_to_m2_axis_error_deg": measured_to_m2_axis,
                "candidate_cavity_roll_error_deg": measured_roll_to_m2,
                "measured_cross_bolt_angle_from_head_x_deg": measured_cross_bolt_angle,
                "expected_cross_bolt_angle_from_head_x_deg": expected_cross_bolt_angle,
                "cross_bolt_angle_error_deg": cross_bolt_error,
                "axis_limit_deg": axis_limit,
                "roll_limit_deg": roll_limit,
                "axis_changed": False,
                "roll_changed": False,
                "status": "PASS",
            },
            "immutable_hashes_after": immutable_after,
        }
        return metrics, {
            "root": root,
            "output_dir": output_dir,
            "report_path": report_path,
        }
    finally:
        App.closeDocument(candidate_document.Name)
        App.closeDocument(snapshot_document.Name)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.contract)
    contract = load_json(args.contract.resolve())
    output_dir = checked_repo_path(root, contract["output"]["directory"])
    report_path = checked_repo_path(root, contract["output"]["report"])
    require_gate(
        not output_dir.exists(),
        "RELEASE_VALIDATION_OUTPUT_MUST_BE_NEW",
        str(output_dir),
        "absent before the single pass",
    )

    result: dict[str, Any] = {
        "schema_version": "1.0",
        "validation_id": VALIDATION_ID,
        "mode": "read_only_independent_release_validation",
        "candidate_modified": False,
        "generator_invoked": False,
        "automatic_retry": False,
        "automatic_healing_used": False,
        "full_system_release": False,
        "release_holds": contract["release_holds"],
    }
    exit_code = 1
    try:
        metrics, paths = validate(args)
        require_gate(
            paths["output_dir"] == output_dir and paths["report_path"] == report_path,
            "OUTPUT_PATH_STABILITY",
            {
                "output_dir": str(paths["output_dir"]),
                "report_path": str(paths["report_path"]),
            },
            {
                "output_dir": str(output_dir),
                "report_path": str(report_path),
            },
        )
        result.update(
            {
                "status": "PASS",
                "failed_gate": None,
                "metrics": metrics,
            }
        )
        exit_code = 0
    except GateFailure as exc:
        result.update(
            {
                "status": "FAIL",
                "failed_gate": exc.record(),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "FAIL",
                "failed_gate": {
                    "gate": "VALIDATOR_EXCEPTION",
                    "actual": f"{type(exc).__name__}: {exc}",
                    "expected": "validator completes without exception",
                },
            }
        )

    output_dir.mkdir(parents=True, exist_ok=False)
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
