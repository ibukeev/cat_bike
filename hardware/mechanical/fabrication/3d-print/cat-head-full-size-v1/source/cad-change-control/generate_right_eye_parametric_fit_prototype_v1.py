#!/usr/bin/env python3
"""Generate the single V2 right-eye parametric fit prototype.

This generator opens the hash-pinned canonical V34 FCStd, saves a candidate
copy, and replaces only FROZEN_REPAIRED_RIGHT_EYE_V4_V34.Shape.  Construction
uses the approved module LCS, visible aperture, shell-opening boundary, and
fixed V5/V17 mounting datums.  The old eye shape is never inspected, split,
healed, recovered, or reused.

The saved candidate contains no cap, diffuser, conflict helper, section helper,
axis helper, added document object, validation report, mesh export, or release
artifact.  Review PNGs are rendered deterministically from in-memory
tessellations with a standard-library rasterizer so the generator does not
depend on a GUI or mutate document visibility.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Iterable, Sequence

import FreeCAD as App
import Mesh
import Part


ITERATION_ID = "right-eye-parametric-fit-prototype-v1"
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
IMAGE_WIDTH = 1000
IMAGE_HEIGHT = 750


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vector(values: Sequence[float]) -> App.Vector:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def normalized(value: App.Vector, label: str) -> App.Vector:
    result = App.Vector(value)
    if result.Length <= 1.0e-9:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def average(points: Sequence[App.Vector]) -> App.Vector:
    result = App.Vector()
    for point in points:
        result += point
    return result / float(len(points))


def local_coordinates(
    point: App.Vector,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> tuple[float, float, float]:
    delta = point - origin
    return delta.dot(axis_u), delta.dot(axis_v), delta.dot(axis_n)


def point_from_local(
    local_u: float,
    local_v: float,
    depth: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> App.Vector:
    return origin + axis_u * local_u + axis_v * local_v + axis_n * depth


def planar_loop(
    points: Sequence[App.Vector],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> list[App.Vector]:
    output = []
    for point in points:
        local_u, local_v, _ = local_coordinates(
            point, origin, axis_u, axis_v, axis_n
        )
        output.append(
            point_from_local(local_u, local_v, 0.0, origin, axis_u, axis_v, axis_n)
        )
    return output


def radial_offset_loop(
    loop: Sequence[App.Vector],
    offset: float,
    axis_n: App.Vector,
) -> list[App.Vector]:
    """Use the approved Gate-6 centroid-radial offset convention."""
    center = average(loop)
    output = []
    for point in loop:
        radial = point - center
        radial -= axis_n * radial.dot(axis_n)
        radial = normalized(radial, "eye-loop radial")
        output.append(point + radial * float(offset))
    return output


def closed_wire(loop: Sequence[App.Vector]) -> Part.Wire:
    return Part.makePolygon([*loop, loop[0]])


def polygon_face(loop: Sequence[App.Vector]) -> Part.Face:
    face = Part.Face(closed_wire(loop))
    if face.isNull():
        raise RuntimeError("polygon face construction returned a null face")
    return face


def at_depth(loop: Sequence[App.Vector], depth: float, axis_n: App.Vector) -> list[App.Vector]:
    return [point + axis_n * float(depth) for point in loop]


def ring_prism(
    outer: Sequence[App.Vector],
    inner: Sequence[App.Vector],
    start_depth: float,
    end_depth: float,
    axis_n: App.Vector,
    label: str,
) -> Part.Shape:
    if end_depth <= start_depth:
        raise RuntimeError(f"{label}: non-positive axial extent")
    outer_face = polygon_face(at_depth(outer, start_depth, axis_n))
    inner_face = polygon_face(at_depth(inner, start_depth, axis_n))
    ring_face = outer_face.cut(inner_face)
    solid = ring_face.extrude(axis_n * (end_depth - start_depth)).removeSplitter()
    require_single_solid(solid, label)
    return solid


def polygon_prism_uv(
    loop_uv: Sequence[tuple[float, float]],
    start_depth: float,
    end_depth: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
    label: str,
) -> Part.Shape:
    loop = [
        point_from_local(u_value, v_value, 0.0, origin, axis_u, axis_v, axis_n)
        for u_value, v_value in loop_uv
    ]
    face = polygon_face(at_depth(loop, start_depth, axis_n))
    solid = face.extrude(axis_n * (end_depth - start_depth)).removeSplitter()
    require_single_solid(solid, label)
    return solid


def loft_ring(
    outer_start: Sequence[App.Vector],
    inner_start: Sequence[App.Vector],
    outer_end: Sequence[App.Vector],
    inner_end: Sequence[App.Vector],
    start_depth: float,
    end_depth: float,
    axis_n: App.Vector,
    label: str,
) -> Part.Shape:
    outer_solid = Part.makeLoft(
        [
            closed_wire(at_depth(outer_start, start_depth, axis_n)),
            closed_wire(at_depth(outer_end, end_depth, axis_n)),
        ],
        True,
        False,
    )
    inner_solid = Part.makeLoft(
        [
            closed_wire(at_depth(inner_start, start_depth - 0.01, axis_n)),
            closed_wire(at_depth(inner_end, end_depth + 0.01, axis_n)),
        ],
        True,
        False,
    )
    result = outer_solid.cut(inner_solid).removeSplitter()
    require_single_solid(result, label)
    return result


def fuse_shapes(shapes: Sequence[Part.Shape], label: str) -> Part.Shape:
    if not shapes:
        raise RuntimeError(f"{label}: no shapes to fuse")
    result = shapes[0].multiFuse(list(shapes[1:])).removeSplitter()
    if result.isNull():
        raise RuntimeError(f"{label}: Boolean union returned a null shape")
    return result


def require_single_solid(shape: Part.Shape, label: str) -> None:
    if shape.isNull():
        raise RuntimeError(f"{label}: null shape")
    if not shape.isValid():
        raise RuntimeError(f"{label}: invalid shape")
    if not shape.isClosed():
        raise RuntimeError(f"{label}: open shape")
    if len(shape.Solids) != 1:
        raise RuntimeError(f"{label}: expected one solid, found {len(shape.Solids)}")


def points_match(first: App.Vector, second: App.Vector, tolerance: float = 1.0e-5) -> bool:
    return (first - second).Length <= tolerance


def inner_front_edges(
    shape: Part.Shape,
    inner_loop: Sequence[App.Vector],
    depth: float,
    axis_n: App.Vector,
) -> list[Part.Edge]:
    desired = at_depth(inner_loop, depth, axis_n)
    segments = [
        (desired[index], desired[(index + 1) % len(desired)])
        for index in range(len(desired))
    ]
    selected = []
    for edge in shape.Edges:
        if len(edge.Vertexes) != 2:
            continue
        first = edge.Vertexes[0].Point
        second = edge.Vertexes[1].Point
        if any(
            (points_match(first, start) and points_match(second, end))
            or (points_match(first, end) and points_match(second, start))
            for start, end in segments
        ):
            selected.append(edge)
    if len(selected) != len(inner_loop):
        raise RuntimeError(
            f"diffuser-seat fillet expected {len(inner_loop)} inner edges, found {len(selected)}"
        )
    return selected


def closest_point_on_polygon(
    point: tuple[float, float],
    polygon: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    best: tuple[float, float] | None = None
    best_distance = math.inf
    px, py = point
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        denominator = dx * dx + dy * dy
        ratio = 0.0 if denominator <= 1.0e-12 else (
            (px - start[0]) * dx + (py - start[1]) * dy
        ) / denominator
        ratio = max(0.0, min(1.0, ratio))
        candidate = (start[0] + ratio * dx, start[1] + ratio * dy)
        distance = math.hypot(candidate[0] - px, candidate[1] - py)
        if distance < best_distance:
            best = candidate
            best_distance = distance
    if best is None:
        raise RuntimeError("cannot resolve closest polygon point")
    return best


def segment_web_uv(
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    end_overlap: float,
) -> list[tuple[float, float]]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 1.0e-6:
        raise RuntimeError("mounting web has zero length")
    along = (dx / length, dy / length)
    across = (-along[1], along[0])
    first = (start[0] - along[0] * end_overlap, start[1] - along[1] * end_overlap)
    second = (end[0] + along[0] * end_overlap, end[1] + along[1] * end_overlap)
    half = width / 2.0
    return [
        (first[0] - across[0] * half, first[1] - across[1] * half),
        (second[0] - across[0] * half, second[1] - across[1] * half),
        (second[0] + across[0] * half, second[1] + across[1] * half),
        (first[0] + across[0] * half, first[1] + across[1] * half),
    ]


def oriented_root_plate(
    bore_center: App.Vector,
    bore_axis: App.Vector,
    tangent_width: float,
    front_depth: float,
    rear_depth: float,
    radial_thickness: float,
    origin: App.Vector,
    axis_n: App.Vector,
    label: str,
) -> Part.Shape:
    axis = normalized(bore_axis, f"{label} bore axis")
    plate_radial = axis - axis_n * axis.dot(axis_n)
    plate_radial = normalized(plate_radial, f"{label} in-plane bore axis")
    tangent = normalized(plate_radial.cross(axis_n), f"{label} tangent")
    _, _, bore_depth = local_coordinates(
        bore_center, origin, tangent, plate_radial, axis_n
    )
    base_center = bore_center + axis_n * (front_depth - bore_depth)
    half_width = tangent_width / 2.0
    half_thickness = radial_thickness / 2.0
    loop = [
        base_center - tangent * half_width - plate_radial * half_thickness,
        base_center + tangent * half_width - plate_radial * half_thickness,
        base_center + tangent * half_width + plate_radial * half_thickness,
        base_center - tangent * half_width + plate_radial * half_thickness,
    ]
    plate = polygon_face(loop).extrude(axis_n * (rear_depth - front_depth)).removeSplitter()
    require_single_solid(plate, label)
    return plate


def add_property(obj: Any, property_type: str, name: str, group: str) -> None:
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, group)


def attach_parametric_history(
    target: Any,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
    aperture_exact: Sequence[App.Vector],
) -> None:
    add_property(target, "App::PropertyString", "PrototypeIterationId", "ParametricPrototype")
    add_property(target, "App::PropertyStringList", "ConstructionFeatures", "ParametricPrototype")
    add_property(target, "App::PropertyString", "FinalBooleanUnion", "ParametricPrototype")
    add_property(target, "App::PropertyString", "PrototypeState", "ParametricPrototype")
    target.PrototypeIterationId = ITERATION_ID
    target.ConstructionFeatures = [
        "01_CONTINUOUS_FRONT_BEZEL",
        "02_CONTINUOUS_DIFFUSER_SEAT_RETAINING_SHOULDER",
        "03_HIDDEN_TAPERED_CHAMBER",
        "04_REAR_CAP_SEAT_AND_TWO_BUCKET_SIDE_CONNECTOR_BOSSES",
        "05_BROAD_UPPER_AND_LOWER_EYE_TO_HEAD_MOUNTING_ROOTS",
        "06_FINAL_TRUE_BOOLEAN_UNION",
    ]
    target.FinalBooleanUnion = "OCCT multiFuse of all five constructed feature families; removeSplitter; one saved solid"
    target.PrototypeState = "DISPOSABLE__AWAITING_USER_VISUAL_APPROVAL"

    add_property(target, "App::PropertyVector", "ModuleLCSOrigin", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "ModuleLCSU", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "ModuleLCSV", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "ModuleLCSInwardN", "ApprovedDatums")
    add_property(target, "App::PropertyVectorList", "ProtectedVisibleAperture", "ApprovedDatums")
    target.ModuleLCSOrigin = origin
    target.ModuleLCSU = axis_u
    target.ModuleLCSV = axis_v
    target.ModuleLCSInwardN = axis_n
    target.ProtectedVisibleAperture = list(aperture_exact)

    dimension_names = {
        "ShellOpeningClearance": "shell_opening_clearance_mm",
        "BezelThickness": "bezel_thickness_mm",
        "DiffuserThickness": "diffuser_thickness_mm",
        "DiffuserOverlap": "diffuser_overlap_mm",
        "DiffuserPocketClearance": "diffuser_pocket_clearance_mm",
        "GasketAllowance": "gasket_allowance_mm",
        "ChamberWallThickness": "chamber_wall_thickness_mm",
        "ChamberDepth": "chamber_depth_mm",
        "BezelChamberAxialOverlap": "bezel_chamber_axial_overlap_mm",
        "BezelChamberInternalFillet": "bezel_chamber_internal_fillet_mm",
        "LedToDiffuserGap": "led_to_diffuser_gap_mm",
        "CapNominalClearance": "cap_nominal_clearance_mm",
        "MountClearanceDiameter": "m2_5_clearance_diameter_mm",
        "MountRootThickness": "mount_root_thickness_mm",
        "MountBoreToEdgeMinimum": "bore_to_edge_minimum_mm",
        "MountMatingGap": "mount_mating_gap_mm",
    }
    for property_name, source_name in dimension_names.items():
        add_property(target, "App::PropertyLength", property_name, "PrototypeDimensions")
        setattr(target, property_name, float(parameters[source_name]))

    mounts = parameters["head_mounts"]
    add_property(target, "App::PropertyVector", "UpperMountBoreCenter", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "UpperMountBoreAxis", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "LowerMountBoreCenter", "ApprovedDatums")
    add_property(target, "App::PropertyVector", "LowerMountBoreAxis", "ApprovedDatums")
    target.UpperMountBoreCenter = vector(mounts["upper"]["bore_center_mm"])
    target.UpperMountBoreAxis = vector(mounts["upper"]["bore_axis"])
    target.LowerMountBoreCenter = vector(mounts["lower"]["bore_center_mm"])
    target.LowerMountBoreAxis = vector(mounts["lower"]["bore_axis"])


def build_mount_root(
    role: str,
    spec: dict[str, Any],
    parameters: dict[str, Any],
    aperture_uv: Sequence[tuple[float, float]],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> tuple[Part.Shape, Part.Shape]:
    center = vector(spec["bore_center_mm"])
    bore_axis = normalized(vector(spec["bore_axis"]), f"{role} bore axis")
    _, _, bore_depth = local_coordinates(center, origin, axis_u, axis_v, axis_n)
    front_depth = float(parameters["mount_root_front_depth_mm"])
    rear_depth = front_depth + float(parameters["mount_root_depth_mm"])
    bore_radius = float(parameters["m2_5_clearance_diameter_mm"]) / 2.0
    tangent_material = float(parameters["mount_root_length_mm"]) / 2.0 - bore_radius
    axial_material = min(bore_depth - front_depth, rear_depth - bore_depth) - bore_radius
    required_material = float(parameters["bore_to_edge_minimum_mm"])
    if min(tangent_material, axial_material) + 1.0e-9 < required_material:
        raise RuntimeError(f"{role} mounting root cannot retain 3.50 mm bore-edge material")

    plate = oriented_root_plate(
        center,
        bore_axis,
        float(parameters["mount_root_length_mm"]),
        front_depth,
        rear_depth,
        float(parameters["mount_root_thickness_mm"]),
        origin,
        axis_n,
        f"{role} mounting flange",
    )
    center_u, center_v, _ = local_coordinates(center, origin, axis_u, axis_v, axis_n)
    nearest = closest_point_on_polygon((center_u, center_v), aperture_uv)
    centroid = (
        sum(point[0] for point in aperture_uv) / len(aperture_uv),
        sum(point[1] for point in aperture_uv) / len(aperture_uv),
    )
    inward_dx = centroid[0] - nearest[0]
    inward_dy = centroid[1] - nearest[1]
    inward_length = math.hypot(inward_dx, inward_dy)
    if inward_length <= 1.0e-6:
        raise RuntimeError(f"{role} mounting web lacks an inward landing direction")
    landing = (
        nearest[0] + inward_dx / inward_length * float(parameters["mount_web_landing_inset_mm"]),
        nearest[1] + inward_dy / inward_length * float(parameters["mount_web_landing_inset_mm"]),
    )
    web_loop = segment_web_uv(
        (center_u, center_v),
        landing,
        float(parameters["mount_web_width_mm"]),
        float(parameters["mount_web_end_overlap_mm"]),
    )
    web = polygon_prism_uv(
        web_loop,
        float(parameters["mount_web_front_depth_mm"]),
        float(parameters["mount_web_rear_depth_mm"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
        f"{role} broad mounting web",
    )
    root_uncut = fuse_shapes([plate, web], f"{role} broad mounting root")
    cutter_length = float(parameters["mount_bore_cutter_length_mm"])
    cutter = Part.makeCylinder(
        bore_radius,
        cutter_length,
        center - bore_axis * (cutter_length / 2.0),
        bore_axis,
    )
    root = root_uncut.cut(cutter).removeSplitter()
    require_single_solid(root, f"{role} drilled mounting root")
    return root, cutter


def build_rear_cap_feature(
    parameters: dict[str, Any],
    aperture_uv: Sequence[tuple[float, float]],
    rear_outer: Sequence[App.Vector],
    rear_inner: Sequence[App.Vector],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> tuple[Part.Shape, list[Part.Shape]]:
    seat = ring_prism(
        rear_outer,
        rear_inner,
        float(parameters["rear_cap_seat_front_depth_mm"]),
        float(parameters["chamber_depth_mm"]),
        axis_n,
        "rear-cap perimeter seat",
    )
    boss_start = float(parameters["chamber_depth_mm"]) - float(
        parameters["cap_boss_engagement_depth_mm"]
    )
    boss_end = float(parameters["chamber_depth_mm"])
    boss_radius = float(parameters["cap_boss_outer_diameter_mm"]) / 2.0
    bore_radius = float(parameters["m2_5_clearance_diameter_mm"]) / 2.0
    shapes: list[Part.Shape] = [seat]
    cutters: list[Part.Shape] = []
    aperture_centroid = (
        sum(point[0] for point in aperture_uv) / len(aperture_uv),
        sum(point[1] for point in aperture_uv) / len(aperture_uv),
    )
    rear_inner_uv = [
        local_coordinates(point, origin, axis_u, axis_v, axis_n)[:2]
        for point in rear_inner
    ]
    for role, center_values in parameters["rear_cap_boss_centers_mm"].items():
        axis_point = vector(center_values)
        center_u, center_v, _ = local_coordinates(
            axis_point, origin, axis_u, axis_v, axis_n
        )
        base = point_from_local(
            center_u, center_v, boss_start, origin, axis_u, axis_v, axis_n
        )
        boss = Part.makeCylinder(boss_radius, boss_end - boss_start, base, axis_n)
        nearest = closest_point_on_polygon((center_u, center_v), rear_inner_uv)
        outward_dx = nearest[0] - aperture_centroid[0]
        outward_dy = nearest[1] - aperture_centroid[1]
        outward_length = math.hypot(outward_dx, outward_dy)
        if outward_length <= 1.0e-6:
            raise RuntimeError(f"{role} cap boss lacks a wall-support direction")
        wall_landing = (
            nearest[0] + outward_dx / outward_length * float(parameters["cap_boss_web_wall_overlap_mm"]),
            nearest[1] + outward_dy / outward_length * float(parameters["cap_boss_web_wall_overlap_mm"]),
        )
        web_loop = segment_web_uv(
            (center_u, center_v),
            wall_landing,
            float(parameters["cap_boss_web_width_mm"]),
            float(parameters["cap_boss_web_end_overlap_mm"]),
        )
        web = polygon_prism_uv(
            web_loop,
            boss_start,
            boss_end,
            origin,
            axis_u,
            axis_v,
            axis_n,
            f"{role} cap-boss broad support",
        )
        shapes.extend((boss, web))
        cutter_length = float(parameters["cap_boss_bore_cutter_length_mm"])
        cutters.append(
            Part.makeCylinder(
                bore_radius,
                cutter_length,
                point_from_local(
                    center_u,
                    center_v,
                    boss_start - 1.0,
                    origin,
                    axis_u,
                    axis_v,
                    axis_n,
                ),
                axis_n,
            )
        )
    uncut = fuse_shapes(shapes, "rear-cap seat and connector bosses")
    result = uncut.cut(Part.makeCompound(cutters)).removeSplitter()
    require_single_solid(result, "drilled rear-cap seat and connector bosses")
    return result, cutters


def build_candidate_shape(
    parameters: dict[str, Any]
) -> tuple[Part.Shape, dict[str, Any]]:
    lcs = parameters["module_lcs"]
    origin = vector(lcs["origin_mm"])
    axis_u = normalized(vector(lcs["u"]), "module LCS u")
    axis_v = normalized(vector(lcs["v"]), "module LCS v")
    axis_n = normalized(vector(lcs["inward_n"]), "module LCS inward n")
    if max(abs(axis_u.dot(axis_v)), abs(axis_u.dot(axis_n)), abs(axis_v.dot(axis_n))) > 1.0e-6:
        raise RuntimeError("module LCS is not orthogonal")

    aperture_exact = [vector(point) for point in parameters["visible_aperture_mm"]]
    aperture = planar_loop(aperture_exact, origin, axis_u, axis_v, axis_n)
    max_plane_closure = max(
        abs(local_coordinates(point, origin, axis_u, axis_v, axis_n)[2])
        for point in aperture_exact
    )
    if max_plane_closure > float(parameters["aperture_input_rounding_tolerance_mm"]):
        raise RuntimeError("protected aperture coordinates exceed their declared plane-rounding tolerance")

    opening_raw = [vector(point) for point in parameters["approved_shell_opening_boundary_mm"]]
    opening = []
    for index, point in enumerate(opening_raw):
        local_u, local_v, _ = local_coordinates(point, origin, axis_u, axis_v, axis_n)
        opening.append(
            point_from_local(local_u, local_v, 0.0, origin, axis_u, axis_v, axis_n)
        )
    outer_fit = radial_offset_loop(
        opening, -float(parameters["shell_opening_clearance_mm"]), axis_n
    )

    diffuser_loop = radial_offset_loop(
        aperture, float(parameters["diffuser_overlap_mm"]), axis_n
    )
    pocket_loop = radial_offset_loop(
        diffuser_loop, float(parameters["diffuser_pocket_clearance_mm"]), axis_n
    )
    bezel_collar_outer = radial_offset_loop(
        aperture, float(parameters["bezel_collar_outer_offset_mm"]), axis_n
    )
    bezel_collar_inner = radial_offset_loop(
        aperture, float(parameters["bezel_collar_front_inner_offset_mm"]), axis_n
    )
    chamber_front_outer = radial_offset_loop(
        pocket_loop, float(parameters["chamber_wall_thickness_mm"]), axis_n
    )
    chamber_front_inner = pocket_loop
    chamber_rear_inner = radial_offset_loop(
        aperture, float(parameters["chamber_rear_inner_offset_mm"]), axis_n
    )
    chamber_rear_outer = radial_offset_loop(
        chamber_rear_inner, float(parameters["chamber_wall_thickness_mm"]), axis_n
    )

    front_bezel_face = ring_prism(
        outer_fit,
        aperture,
        0.0,
        float(parameters["bezel_thickness_mm"]),
        axis_n,
        "continuous front bezel face",
    )
    bezel_collar = ring_prism(
        bezel_collar_outer,
        bezel_collar_inner,
        float(parameters["bezel_collar_start_depth_mm"]),
        float(parameters["bezel_collar_end_depth_mm"]),
        axis_n,
        "continuous front bezel collar",
    )
    pocket_cutter = polygon_face(
        at_depth(pocket_loop, float(parameters["bezel_thickness_mm"]), axis_n)
    ).extrude(
        axis_n
        * (
            float(parameters["bezel_collar_end_depth_mm"])
            - float(parameters["bezel_thickness_mm"])
            + 0.02
        )
    )
    bezel_collar = bezel_collar.cut(pocket_cutter).removeSplitter()
    continuous_front_bezel = fuse_shapes(
        [front_bezel_face, bezel_collar], "continuous front bezel"
    )
    require_single_solid(continuous_front_bezel, "continuous front bezel")

    baffle = ring_prism(
        chamber_front_outer,
        chamber_front_inner,
        float(parameters["bezel_collar_start_depth_mm"]),
        float(parameters["chamber_taper_start_depth_mm"]) + 0.3,
        axis_n,
        "front chamber wall",
    )
    taper = loft_ring(
        chamber_front_outer,
        chamber_front_inner,
        chamber_rear_outer,
        chamber_rear_inner,
        float(parameters["chamber_taper_start_depth_mm"]),
        float(parameters["chamber_taper_end_depth_mm"]),
        axis_n,
        "structured hidden chamber taper",
    )
    rear_wall = ring_prism(
        chamber_rear_outer,
        chamber_rear_inner,
        float(parameters["chamber_taper_end_depth_mm"]) - 0.3,
        float(parameters["chamber_depth_mm"]),
        axis_n,
        "rear hidden chamber wall",
    )
    hidden_chamber = fuse_shapes(
        [baffle, taper, rear_wall], "continuous hidden chamber"
    )
    require_single_solid(hidden_chamber, "continuous hidden chamber")

    seat_raw = ring_prism(
        chamber_front_outer,
        chamber_rear_inner,
        float(parameters["diffuser_seat_start_depth_mm"]),
        float(parameters["diffuser_seat_end_depth_mm"]),
        axis_n,
        "diffuser retaining shoulder before fillet",
    )
    fillet_edges = inner_front_edges(
        seat_raw,
        chamber_rear_inner,
        float(parameters["diffuser_seat_start_depth_mm"]),
        axis_n,
    )
    diffuser_seat = seat_raw.makeFillet(
        float(parameters["bezel_chamber_internal_fillet_mm"]), fillet_edges
    ).removeSplitter()
    require_single_solid(diffuser_seat, "continuous filleted diffuser retaining shoulder")

    aperture_uv = [
        local_coordinates(point, origin, axis_u, axis_v, axis_n)[:2]
        for point in aperture
    ]
    cap_feature, cap_cutters = build_rear_cap_feature(
        parameters,
        aperture_uv,
        chamber_rear_outer,
        chamber_rear_inner,
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    upper_root, upper_cutter = build_mount_root(
        "upper",
        parameters["head_mounts"]["upper"],
        parameters,
        aperture_uv,
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    lower_root, lower_cutter = build_mount_root(
        "lower",
        parameters["head_mounts"]["lower"],
        parameters,
        aperture_uv,
        origin,
        axis_u,
        axis_v,
        axis_n,
    )

    final_union = fuse_shapes(
        [
            continuous_front_bezel,
            diffuser_seat,
            hidden_chamber,
            cap_feature,
            upper_root,
            lower_root,
        ],
        "final true Boolean union",
    )
    require_single_solid(final_union, "final true Boolean union")
    if len(final_union.Compounds) > 0 and len(final_union.Solids) != 1:
        raise RuntimeError("final union retained disconnected compounds")

    construction = {
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "aperture_exact": aperture_exact,
        "aperture_planar": aperture,
        "outer_fit": outer_fit,
        "diffuser_loop": diffuser_loop,
        "pocket_loop": pocket_loop,
        "chamber_rear_outer": chamber_rear_outer,
        "chamber_rear_inner": chamber_rear_inner,
        "upper_bore_cutter": upper_cutter,
        "lower_bore_cutter": lower_cutter,
        "cap_bore_cutters": cap_cutters,
        "aperture_plane_closure_mm": max_plane_closure,
    }
    return final_union, construction


def tuple3(value: Any) -> tuple[float, float, float]:
    if isinstance(value, App.Vector):
        return float(value.x), float(value.y), float(value.z)
    return float(value[0]), float(value[1]), float(value[2])


def transform_point(placement: App.Placement, value: Any) -> tuple[float, float, float]:
    transformed = placement.multVec(vector(tuple3(value)))
    return transformed.x, transformed.y, transformed.z


def shape_record(
    shape: Part.Shape,
    color: tuple[int, int, int],
    alpha: int = 255,
    edge: bool = False,
    deflection: float = 1.4,
    placement: App.Placement | None = None,
) -> dict[str, Any]:
    points, facets = shape.tessellate(deflection)
    active_placement = placement or App.Placement()
    vertices = [transform_point(active_placement, point) for point in points]
    triangles = [tuple(int(index) for index in facet[:3]) for facet in facets]
    return {
        "vertices": vertices,
        "triangles": triangles,
        "color": color,
        "alpha": int(alpha),
        "edge": bool(edge),
    }


def mesh_record(
    mesh: Mesh.Mesh,
    color: tuple[int, int, int],
    alpha: int = 255,
    edge: bool = False,
    placement: App.Placement | None = None,
) -> dict[str, Any]:
    points, facets = mesh.Topology
    active_placement = placement or App.Placement()
    vertices = [transform_point(active_placement, point) for point in points]
    triangles = [tuple(int(index) for index in facet[:3]) for facet in facets]
    return {
        "vertices": vertices,
        "triangles": triangles,
        "color": color,
        "alpha": int(alpha),
        "edge": bool(edge),
    }


def object_color(name: str, target: str) -> tuple[int, int, int]:
    if name == target:
        return 32, 187, 225
    if "EAR" in name:
        return 180, 150, 108
    if "PANEL" in name:
        return 242, 154, 55
    if "LOWER" in name:
        return 105, 112, 121
    if "C001" in name:
        return 82, 151, 102
    return 165, 171, 180


def document_records(document: Any, target_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for obj in document.Objects:
        placement = obj.Placement if hasattr(obj, "Placement") else App.Placement()
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            records.append(
                shape_record(
                    obj.Shape,
                    object_color(obj.Name, target_name),
                    255,
                    obj.Name == target_name,
                    1.7 if obj.Name != target_name else 0.9,
                    placement,
                )
            )
        elif hasattr(obj, "Mesh") and obj.Mesh.CountFacets > 0:
            records.append(
                mesh_record(
                    obj.Mesh,
                    object_color(obj.Name, target_name),
                    255,
                    False,
                    placement,
                )
            )
    return records


def dot_tuple(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return sum(first[index] * second[index] for index in range(3))


def subtract_tuple(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(first[index] - second[index] for index in range(3))  # type: ignore[return-value]


def cross_tuple(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def normalize_tuple(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(dot_tuple(value, value))
    if length <= 1.0e-12:
        raise RuntimeError("render camera vector has zero length")
    return tuple(component / length for component in value)  # type: ignore[return-value]


def blend_pixel(
    pixels: bytearray,
    width: int,
    x_value: int,
    y_value: int,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    if not (0 <= x_value < width and 0 <= y_value < len(pixels) // (width * 3)):
        return
    offset = (y_value * width + x_value) * 3
    if alpha >= 255:
        pixels[offset : offset + 3] = bytes(color)
        return
    inverse = 255 - alpha
    for channel in range(3):
        pixels[offset + channel] = (
            color[channel] * alpha + pixels[offset + channel] * inverse
        ) // 255


def draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    x0, y0 = int(round(start[0])), int(round(start[1]))
    x1, y1 = int(round(end[0])), int(round(end[1]))
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        if 0 <= x0 < width and 0 <= y0 < height:
            blend_pixel(pixels, width, x0, y0, color, alpha)
        if x0 == x1 and y0 == y1:
            break
        twice = 2 * error
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def fill_triangle(
    pixels: bytearray,
    width: int,
    height: int,
    points: Sequence[tuple[float, float]],
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    minimum_y = max(0, int(math.floor(min(point[1] for point in points))))
    maximum_y = min(height - 1, int(math.ceil(max(point[1] for point in points))))
    for y_value in range(minimum_y, maximum_y + 1):
        scan_y = y_value + 0.5
        intersections = []
        for index, first in enumerate(points):
            second = points[(index + 1) % 3]
            low = min(first[1], second[1])
            high = max(first[1], second[1])
            if high - low <= 1.0e-9 or not (low <= scan_y < high):
                continue
            ratio = (scan_y - first[1]) / (second[1] - first[1])
            intersections.append(first[0] + ratio * (second[0] - first[0]))
        if len(intersections) < 2:
            continue
        start_x = max(0, int(math.ceil(min(intersections))))
        end_x = min(width - 1, int(math.floor(max(intersections))))
        if end_x < start_x:
            continue
        if alpha >= 255:
            offset = (y_value * width + start_x) * 3
            pixels[offset : offset + (end_x - start_x + 1) * 3] = bytes(color) * (
                end_x - start_x + 1
            )
        else:
            for x_value in range(start_x, end_x + 1):
                blend_pixel(pixels, width, x_value, y_value, color, alpha)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = []
    stride = width * 3
    for y_value in range(height):
        start = y_value * stride
        rows.append(b"\x00" + bytes(pixels[start : start + stride]))
    payload = zlib.compress(b"".join(rows), 7)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", payload)
        + png_chunk(b"IEND", b"")
    )


def render_scene(
    path: Path,
    records: Sequence[dict[str, Any]],
    view_direction: tuple[float, float, float],
    up_hint: tuple[float, float, float],
    margin: int = 46,
) -> None:
    view = normalize_tuple(view_direction)
    up_seed = normalize_tuple(up_hint)
    right = normalize_tuple(cross_tuple(view, up_seed))
    up = normalize_tuple(cross_tuple(right, view))
    projected_records = []
    all_x: list[float] = []
    all_y: list[float] = []
    for record in records:
        projected = []
        for point in record["vertices"]:
            projected_point = (
                dot_tuple(point, right),
                dot_tuple(point, up),
                dot_tuple(point, view),
            )
            projected.append(projected_point)
            all_x.append(projected_point[0])
            all_y.append(projected_point[1])
        projected_records.append((record, projected))
    if not all_x or not all_y:
        raise RuntimeError(f"{path}: no renderable geometry")
    span_x = max(max(all_x) - min(all_x), 1.0)
    span_y = max(max(all_y) - min(all_y), 1.0)
    scale = min(
        (IMAGE_WIDTH - 2 * margin) / span_x,
        (IMAGE_HEIGHT - 2 * margin) / span_y,
    )
    center_x = (min(all_x) + max(all_x)) / 2.0
    center_y = (min(all_y) + max(all_y)) / 2.0

    triangles = []
    for record, projected in projected_records:
        for indices in record["triangles"]:
            p3d = [record["vertices"][index] for index in indices]
            p2d = [
                (
                    IMAGE_WIDTH / 2.0 + (projected[index][0] - center_x) * scale,
                    IMAGE_HEIGHT / 2.0 - (projected[index][1] - center_y) * scale,
                )
                for index in indices
            ]
            first_edge = subtract_tuple(p3d[1], p3d[0])
            second_edge = subtract_tuple(p3d[2], p3d[0])
            normal = cross_tuple(first_edge, second_edge)
            normal_length = math.sqrt(dot_tuple(normal, normal))
            if normal_length <= 1.0e-12:
                continue
            light = normalize_tuple(
                (
                    -view[0] + up[0] * 0.35 - right[0] * 0.20,
                    -view[1] + up[1] * 0.35 - right[1] * 0.20,
                    -view[2] + up[2] * 0.35 - right[2] * 0.20,
                )
            )
            lighting = 0.58 + 0.42 * abs(dot_tuple(normalize_tuple(normal), light))
            base = record["color"]
            shaded = tuple(max(0, min(255, int(channel * lighting))) for channel in base)
            depth = sum(projected[index][2] for index in indices) / 3.0
            triangles.append(
                (depth, p2d, shaded, int(record["alpha"]), bool(record["edge"]))
            )
    triangles.sort(key=lambda item: item[0], reverse=True)
    pixels = bytearray((246, 247, 249) * (IMAGE_WIDTH * IMAGE_HEIGHT))
    edge_queue = []
    for _, points, color, alpha, edge in triangles:
        fill_triangle(pixels, IMAGE_WIDTH, IMAGE_HEIGHT, points, color, alpha)
        if edge:
            edge_queue.append(points)
    for points in edge_queue:
        for index in range(3):
            draw_line(
                pixels,
                IMAGE_WIDTH,
                IMAGE_HEIGHT,
                points[index],
                points[(index + 1) % 3],
                (20, 55, 68),
                105,
            )
    write_png(path, IMAGE_WIDTH, IMAGE_HEIGHT, pixels)


def make_halfspace(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_n: App.Vector,
) -> Part.Shape:
    loop = [(-120.0, -120.0), (120.0, -120.0), (120.0, 0.0), (-120.0, 0.0)]
    return polygon_prism_uv(
        loop, -30.0, 45.0, origin, axis_u, axis_v, axis_n, "longitudinal halfspace"
    )


def make_axis_arrow(origin: App.Vector, axis_n: App.Vector) -> Part.Shape:
    start = origin - axis_n * 24.0
    shaft = Part.makeCylinder(0.85, 43.0, start, axis_n)
    head = Part.makeCone(2.7, 0.0, 7.0, start + axis_n * 43.0, axis_n)
    return shaft.fuse(head).removeSplitter()


def reference_shape(path: Path) -> Part.Shape:
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise RuntimeError(f"reference STEP imported null: {path}")
    return shape


def verify_reference_hashes(root: Path, references: dict[str, Any]) -> None:
    for name, spec in references.items():
        path = root / spec["path"]
        if not path.is_file():
            raise RuntimeError(f"missing pinned reference {name}: {path}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise RuntimeError(f"hash mismatch for pinned reference {name}")


def render_review_pack(
    document: Any,
    target: Any,
    parameters: dict[str, Any],
    construction: dict[str, Any],
    root: Path,
    contract: dict[str, Any],
) -> None:
    output = contract["output"]
    fixed = output["review_files"]
    whole_records = document_records(document, TARGET_OBJECT)
    fixed_views = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    for name in ("front", "rear", "left", "right", "top", "bottom"):
        direction, up = fixed_views[name]
        render_scene(root / fixed[name], whole_records, direction, up)

    axis_u = construction["axis_u"]
    axis_v = construction["axis_v"]
    axis_n = construction["axis_n"]
    origin = construction["origin"]
    extra = parameters["review_artifacts"]
    isolated = [shape_record(target.Shape, (28, 188, 225), 255, True, 0.65)]
    render_scene(root / extra["isolated_front"], isolated, tuple3(axis_n), tuple3(axis_u))
    render_scene(root / extra["isolated_rear"], isolated, tuple3(-axis_n), tuple3(axis_u))

    section = target.Shape.common(make_halfspace(origin, axis_u, axis_v, axis_n)).removeSplitter()
    if section.isNull():
        raise RuntimeError("longitudinal section produced no geometry")
    section_records = [shape_record(section, (230, 132, 38), 255, True, 0.55)]
    render_scene(root / extra["longitudinal_section"], section_records, tuple3(axis_v), tuple3(axis_u))

    references = parameters["fit_references"]
    cap = reference_shape(root / references["exact_v9_cap"]["path"])
    cap.translate(axis_n * float(parameters["cap_reference_seating_translation_mm"]))
    diffuser = Mesh.Mesh(str(root / references["exact_diffuser"]["path"]))
    fit_records = [
        shape_record(target.Shape, (32, 187, 225), 125, True, 0.8),
        shape_record(cap, (68, 73, 82), 215, True, 0.8),
        mesh_record(diffuser, (64, 220, 238), 225, True),
    ]
    fit_direction = normalize_tuple(
        tuple3(axis_n * 0.72 + axis_v * 0.55 - axis_u * 0.28)
    )
    render_scene(root / extra["cap_diffuser_fit"], fit_records, fit_direction, tuple3(axis_u))

    upper = document.getObject(parameters["conflict_references"]["upper_c001_object"])
    lower = document.getObject(parameters["conflict_references"]["lower_c001_object"])
    if upper is None or lower is None:
        raise RuntimeError("required V34 conflict object is missing")
    c012 = Mesh.Mesh(str(root / references["lower_c012_obj"]["path"]))
    c013 = Mesh.Mesh(str(root / references["lower_c013_obj"]["path"]))
    conflict_records = [
        shape_record(target.Shape, (36, 190, 226), 135, True, 0.7),
        shape_record(upper.Shape, (225, 52, 48), 205, True, 1.0, upper.Placement),
        shape_record(lower.Shape, (255, 139, 35), 205, True, 1.0, lower.Placement),
        mesh_record(c012, (178, 65, 205), 225, True),
        mesh_record(c013, (244, 211, 61), 225, True),
    ]
    render_scene(root / extra["four_conflict_overlay"], conflict_records, tuple3(axis_n), tuple3(axis_u))

    arrow = make_axis_arrow(origin, axis_n)
    insertion_records = [
        shape_record(target.Shape, (35, 187, 222), 210, True, 0.75),
        shape_record(arrow, (32, 205, 100), 255, True, 0.35),
    ]
    render_scene(root / extra["insertion_axis"], insertion_records, tuple3(axis_v), tuple3(axis_u))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.contract)
    baseline = load_json(args.baseline)
    contract = load_json(args.contract)
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    if contract.get("target_object") != TARGET_OBJECT:
        raise RuntimeError("target object mismatch")
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or mutations[0].get("kind") != "replace_geometry":
        raise RuntimeError("generator requires exactly one replace_geometry mutation")
    parameters = mutations[0]["parameters"]
    verify_reference_hashes(root, parameters["fit_references"])

    baseline_path = root / baseline["assembly"]["path"]
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    output_dir.mkdir(parents=True, exist_ok=False)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)

    print("STAGE 1/6 pinned inputs verified", flush=True)
    document = App.openDocument(str(baseline_path))
    try:
        document.saveAs(str(candidate_path))
        target = document.getObject(TARGET_OBJECT)
        if target is None:
            raise RuntimeError(f"canonical V34 lacks target {TARGET_OBJECT}")
        if target.TypeId != "Part::Feature":
            raise RuntimeError(f"unexpected target type {target.TypeId}")
        original_name = target.Name
        original_label = target.Label
        original_placement = App.Placement(target.Placement)

        candidate_shape, construction = build_candidate_shape(parameters)
        print("STAGE 2/6 five named feature families constructed", flush=True)
        target.Shape = candidate_shape
        attach_parametric_history(
            target,
            parameters,
            construction["origin"],
            construction["axis_u"],
            construction["axis_v"],
            construction["axis_n"],
            construction["aperture_exact"],
        )
        document.recompute()
        if target.Name != original_name or target.Label != original_label:
            raise RuntimeError("target identity changed during replacement")
        if target.Placement != original_placement:
            raise RuntimeError("target placement changed during replacement")
        require_single_solid(target.Shape, "saved target replacement")
        document.save()
        print("STAGE 3/6 candidate saved with only target shape replaced", flush=True)

        render_review_pack(document, target, parameters, construction, root, contract)
        print("STAGE 4/6 six fixed whole-head views rendered", flush=True)
        print("STAGE 5/6 six requested focused review views rendered", flush=True)
    finally:
        App.closeDocument(document.Name)

    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 6/6 canonical V34 remains hash-identical", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
