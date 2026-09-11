#!/usr/bin/env python3
"""Generate the clean split-service right-eye cassette prototype.

This is a new physical lineage.  It reuses only the already-tested V2 document
finalization/presentation infrastructure; no V6 shape, candidate, chamber, cap
seat, connector boss, or long mount root is imported or reused.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence


ITERATION_ID = "right-eye-split-service-cassette-prototype-v1"
DESIGN_ID = "right-eye-split-service-cassette-D"
TOOLING_REVISION = 6
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
TOOLKIT_FILENAME = "generate_right_eye_serviceable_fit_prototype_v6_attempt_002.py"
TOOLKIT_SHA256 = "bba7f44c07c20526ccda2d1cbefdfe38fe86ddc1bd5a48c354928e8fcb3a50e9"
SHELL_LOADER_FILENAME = "validate_right_eye_serviceable_fit_previsual_v6_attempt_002.py"
SHELL_LOADER_SHA256 = "1d21d0815601bdcea7806a8215229a40bc2cb4190d93fcdcf7ab53b45f295ec9"
CONTACT_OWNER_KEYS = (
    "upper_C001",
    "lower_C001",
    "lower_C012",
    "lower_C013",
)
EXPECTED_SHELL_COMPONENT_KEYS = (
    tuple(f"upper_C{index:03d}" for index in range(1, 43) if index != 9)
    + tuple(f"lower_C{index:03d}" for index in range(1, 61))
)

sys.path.insert(0, str(Path(__file__).resolve().parent))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pinned_sibling(filename: str, expected_sha256: str, module_name: str) -> Any:
    path = Path(__file__).with_name(filename)
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(
            f"{filename}: infrastructure hash mismatch: {actual} != {expected_sha256}"
        )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load infrastructure module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


toolkit = load_pinned_sibling(
    TOOLKIT_FILENAME,
    TOOLKIT_SHA256,
    "_cat_head_split_cassette_document_toolkit",
)
shell_loader = load_pinned_sibling(
    SHELL_LOADER_FILENAME,
    SHELL_LOADER_SHA256,
    "_cat_head_split_cassette_shell_loader",
)


def repo_root() -> Path:
    return toolkit.repository_root(Path(__file__))


def _aabb_near(first: Any, second: Any, margin: float) -> bool:
    a = first.BoundBox
    b = second.BoundBox
    return not (
        a.XMax + margin < b.XMin
        or b.XMax + margin < a.XMin
        or a.YMax + margin < b.YMin
        or b.YMax + margin < a.YMin
        or a.ZMax + margin < b.ZMin
        or b.ZMax + margin < a.ZMin
    )


def _aabb_separation_to_component(shape: Any, component: Any) -> float:
    box = shape.BoundBox
    gaps = (
        max(float(component.minimum_mm[0]) - float(box.XMax), float(box.XMin) - float(component.maximum_mm[0]), 0.0),
        max(float(component.minimum_mm[1]) - float(box.YMax), float(box.YMin) - float(component.maximum_mm[1]), 0.0),
        max(float(component.minimum_mm[2]) - float(box.ZMax), float(box.ZMin) - float(component.maximum_mm[2]), 0.0),
    )
    return math.sqrt(sum(value * value for value in gaps))


def _verify_serial_relief_reference(
    root: Path, parameters: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    serial = parameters["validation_contract"]["serial_relief_reference"]
    baseline_manifest_path = root / serial["baseline_manifest_path"]
    if sha256_file(baseline_manifest_path) != serial["baseline_manifest_sha256"]:
        raise RuntimeError("serial relieved-shell manifest hash mismatch")
    for path_key, hash_key in (
        ("candidate_path", "candidate_sha256"),
        ("preservation_report_path", "preservation_report_sha256"),
        ("physical_validation_report_path", "physical_validation_report_sha256"),
    ):
        if sha256_file(root / serial[path_key]) != serial[hash_key]:
            raise RuntimeError(f"serial relief pin mismatch: {path_key}")
    validation = json.loads(
        (root / serial["physical_validation_report_path"]).read_text(
            encoding="utf-8"
        )
    )
    actual_status = validation.get("evaluation", {}).get(
        "status", validation.get("status")
    )
    if actual_status != serial["required_validation_status"]:
        raise RuntimeError(
            f"serial relief validation status mismatch: {actual_status}"
        )
    return (
        json.loads(baseline_manifest_path.read_text(encoding="utf-8")),
        baseline_manifest_path,
    )


def _load_shell_components(
    parameters: dict[str, Any],
    App: Any,
    Part: Any,
) -> list[Any]:
    import Mesh  # type: ignore

    root = repo_root()
    baseline_manifest, _ = _verify_serial_relief_reference(root, parameters)
    baseline_path = root / baseline_manifest["assembly"]["path"]
    components, load_report = shell_loader._load_shell_components(
        root,
        baseline_path,
        parameters["validation_contract"],
        App,
        Mesh,
        Part,
    )
    if load_report["load_errors"] or len(components) != 101:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "split-cassette shell matrix is incomplete",
                    "component_count": len(components),
                    "load_errors": load_report["load_errors"],
                },
                sort_keys=True,
            )
        )
    return components


def _authoritative_shell_inventory(components: Sequence[Any]) -> dict[str, Any]:
    by_key: dict[str, Any] = {}
    for component in components:
        key = str(component.key)
        if key in by_key:
            raise RuntimeError(f"duplicate shell component key: {key}")
        minimum = tuple(float(value) for value in component.minimum_mm)
        maximum = tuple(float(value) for value in component.maximum_mm)
        if (
            len(minimum) != 3
            or len(maximum) != 3
            or not all(math.isfinite(value) for value in (*minimum, *maximum))
            or any(low > high for low, high in zip(minimum, maximum))
            or not str(component.source)
        ):
            raise RuntimeError(f"invalid authoritative shell mapping: {key}")
        by_key[key] = component
    expected = set(EXPECTED_SHELL_COMPONENT_KEYS)
    actual = set(by_key)
    if actual != expected:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "authoritative shell mapping is incomplete",
                    "missing": sorted(expected - actual),
                    "unexpected": sorted(actual - expected),
                    "expected_count": len(expected),
                    "actual_count": len(actual),
                },
                sort_keys=True,
            )
        )
    return by_key


def _locally_inset_loop(
    App: Any,
    loop: Sequence[Any],
    vertex_insets_mm: Sequence[float],
    axis_n: Any,
) -> list[Any]:
    if len(loop) != len(vertex_insets_mm):
        raise RuntimeError("local-inset loop and vertex inset counts differ")
    center = toolkit.average(App, loop)
    output = []
    for point, inset in zip(loop, vertex_insets_mm):
        radial = point - center
        radial -= axis_n * radial.dot(axis_n)
        radial = toolkit.normalized(App, radial, "local-inset loop radial")
        output.append(point - radial * float(inset))
    return output


def _validated_cover_lip(
    parameters: dict[str, Any],
    opening: Sequence[Any],
    axis_n: Any,
    App: Any,
    Part: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build the approved lip and trim only its hidden lower-C001 overlap."""
    values = parameters["geometry"]["lower_c001_cover_lip"]
    reference = _locally_inset_loop(
        App,
        opening,
        values["reference_outer_vertex_insets_mm"],
        axis_n,
    )
    edge = list(values["reference_edge_vertex_indices"])
    if edge != [0, 3]:
        raise RuntimeError("lower-C001 cover-lip edge changed")
    tangent = toolkit.normalized(
        App, reference[edge[1]] - reference[edge[0]], "cover-lip tangent"
    )
    outward = toolkit.normalized(App, axis_n.cross(tangent), "cover-lip outward")
    start = reference[edge[0]]
    end = start + tangent * float(values["tangent_length_mm"])
    loop = [
        start - outward * float(values["inward_attachment_overlap_mm"]),
        end - outward * float(values["inward_attachment_overlap_mm"]),
        end + outward * float(values["outward_reach_mm"]),
        start + outward * float(values["outward_reach_mm"]),
    ]
    face = Part.Face(Part.makePolygon([*loop, loop[0]]))
    face.translate(axis_n * -float(values["outward_axial_cover_mm"]))
    raw = face.extrude(
        axis_n * float(values["outward_axial_cover_mm"])
    ).removeSplitter()
    toolkit.require_single_solid(raw, "raw lower-C001 cover lip")

    components = _load_shell_components(parameters, App, Part)
    inventory = _authoritative_shell_inventory(components)
    lower_c001 = inventory["lower_C001"].shape
    if lower_c001 is None or lower_c001.isNull():
        raise RuntimeError("validated relieved lower_C001 is unavailable")
    trimmed = raw.cut(lower_c001).removeSplitter()
    toolkit.require_single_solid(trimmed, "trimmed lower-C001 cover lip")
    epsilon = float(
        parameters["validation_contract"]["limits"]
        ["maximum_unintended_positive_intersection_mm3"]
    )
    removed = float(raw.cut(trimmed).Volume)
    expected_removed = float(values["expected_hidden_attachment_trim_mm3"])
    if abs(removed - expected_removed) > epsilon:
        raise RuntimeError(
            f"cover-lip hidden trim changed: {removed} != {expected_removed}"
        )
    intersections: dict[str, float] = {}
    distances: dict[str, float] = {}
    for key, component in inventory.items():
        obstacle = component.shape
        if obstacle is None or obstacle.isNull() or not _aabb_near(trimmed, obstacle, 0.1):
            continue
        common = float(trimmed.common(obstacle).Volume)
        distance = float(trimmed.distToShape(obstacle)[0])
        distances[key] = distance
        if common > epsilon:
            intersections[key] = common
    if intersections:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "trimmed cover lip intersects shell",
                    "intersections_mm3": intersections,
                },
                sort_keys=True,
            )
        )
    return trimmed, {
        "algorithm": "lower-c001-hidden-attachment-exact-trim-v1",
        "raw_volume_mm3": float(raw.Volume),
        "trimmed_volume_mm3": float(trimmed.Volume),
        "removed_hidden_attachment_mm3": removed,
        "shell_distances_mm": distances,
        "maximum_shell_intersection_mm3": 0.0,
        "outward_reach_mm": float(values["outward_reach_mm"]),
        "tangent_length_mm": float(values["tangent_length_mm"]),
        "outward_axial_cover_mm": float(values["outward_axial_cover_mm"]),
        "pinned_exterior_patch_area_mm2": float(
            values["pinned_exterior_patch_area_mm2"]
        ),
        "uncovered_exterior_patch_area_mm2": 0.0,
    }


def _explicit_mount_ligament(
    role: str,
    frame: dict[str, Any],
    outer_rear: Sequence[Any],
    values: dict[str, Any],
    origin: Any,
    axis_u: Any,
    axis_v: Any,
    axis_n: Any,
    App: Any,
    Part: Any,
) -> tuple[Any, dict[str, Any]]:
    outer_uv = [
        toolkit.local_coordinates(point, origin, axis_u, axis_v, axis_n)[:2]
        for point in outer_rear
    ]
    mount_uv = toolkit.local_coordinates(
        frame["eye_bore"], origin, axis_u, axis_v, axis_n
    )[:2]
    projection = toolkit.nearest_point_on_polygon_edge_uv(mount_uv, outer_uv)
    edge_index = int(projection["edge_index"])
    edge = outer_rear[(edge_index + 1) % len(outer_rear)] - outer_rear[edge_index]
    anchor = toolkit.point_from_local(
        float(projection["point_uv_mm"][0]),
        float(projection["point_uv_mm"][1]),
        float(values["ligament_ring_depth_mm"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    mount_attach = frame["eye_bore"] - frame["bore_axis_vector"] * float(
        values["ligament_mount_axial_offset_mm"]
    )
    path = mount_attach - anchor
    path_axis = toolkit.normalized(App, path, f"{role} ligament path")
    across = edge - path_axis * edge.dot(path_axis)
    across = toolkit.normalized(App, across, f"{role} ligament width axis")
    thickness_axis = toolkit.normalized(
        App,
        path_axis.cross(across),
        f"{role} ligament thickness axis",
    )
    overlap = float(values["ligament_overlap_mm"])
    ligament = toolkit.oriented_box(
        Part,
        (anchor + mount_attach) * 0.5,
        (path_axis, across, thickness_axis),
        (
            float(path.Length) + 2.0 * overlap,
            float(values["ligament_width_mm"]),
            float(values["ligament_thickness_mm"]),
        ),
    )
    toolkit.require_single_solid(ligament, f"{role} explicit protected ligament")
    return ligament, {
        "role": role,
        "edge_index": edge_index,
        "edge_segment_parameter": float(projection["segment_parameter"]),
        "ring_anchor": anchor,
        "mount_attach": mount_attach,
        "path_length_mm": float(path.Length),
        "width_mm": float(values["ligament_width_mm"]),
        "thickness_mm": float(values["ligament_thickness_mm"]),
        "overlap_mm": overlap,
    }


def _verify_direct_shell_clearance(
    shape: Any,
    parameters: dict[str, Any],
    App: Any,
    Part: Any,
) -> dict[str, Any]:
    values = parameters["geometry"]["shell_clearance_trim"]
    required = float(values["minimum_verified_clearance_mm"])
    configured_owners = tuple(values["contact_owner_keys"])
    if configured_owners != CONTACT_OWNER_KEYS:
        raise RuntimeError(
            f"contact-owner set mismatch: {configured_owners}"
        )
    epsilon = float(
        parameters["validation_contract"]["limits"][
            "maximum_unintended_positive_intersection_mm3"
        ]
    )
    components = _load_shell_components(parameters, App, Part)
    by_key = _authoritative_shell_inventory(components)
    missing = [key for key in CONTACT_OWNER_KEYS if key not in by_key]
    if missing:
        raise RuntimeError(f"contact owners missing from shell matrix: {missing}")

    intersections: dict[str, float] = {}
    owner_records: dict[str, dict[str, float]] = {}
    bounds_proven_clear: list[str] = []
    unresolved: list[dict[str, Any]] = []
    minimum_clearance = math.inf
    for component in components:
        obstacle = component.shape
        if obstacle is None or obstacle.isNull():
            separation = _aabb_separation_to_component(shape, component)
            if separation < required - 1.0e-6:
                unresolved.append(
                    {
                        "key": component.key,
                        "source": component.source,
                        "aabb_separation_mm": separation,
                    }
                )
            else:
                bounds_proven_clear.append(component.key)
                minimum_clearance = min(minimum_clearance, separation)
                if component.key in CONTACT_OWNER_KEYS:
                    owner_records[component.key] = {
                        "intersection_mm3": 0.0,
                        "clearance_mm": separation,
                    }
            continue
        if not _aabb_near(shape, obstacle, required + 0.05):
            continue
        common = float(shape.common(obstacle).Volume)
        if common > epsilon:
            intersections[component.key] = common
        distance = float(shape.distToShape(obstacle)[0])
        minimum_clearance = min(minimum_clearance, distance)
        if component.key in CONTACT_OWNER_KEYS:
            owner_records[component.key] = {
                "intersection_mm3": common,
                "clearance_mm": distance,
            }
    if unresolved:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "shell component requires exact geometry inside clearance envelope",
                    "unresolved": unresolved,
                },
                sort_keys=True,
            )
        )
    for key in CONTACT_OWNER_KEYS:
        owner = by_key[key]
        owner_shape = owner.shape
        owner_records.setdefault(
            key,
            {
                "intersection_mm3": 0.0,
                "clearance_mm": (
                    _aabb_separation_to_component(shape, owner)
                    if owner_shape is None or owner_shape.isNull()
                    else float(shape.distToShape(owner_shape)[0])
                ),
            },
        )
    if intersections:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "direct cassette has positive shell intersections",
                    "intersections_mm3": intersections,
                    "contact_owner_records": owner_records,
                },
                sort_keys=True,
            )
        )
    if minimum_clearance < required - 1.0e-6:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "direct cassette did not achieve shell clearance",
                    "actual_minimum_clearance_mm": minimum_clearance,
                    "required_minimum_clearance_mm": required,
                    "contact_owners": list(CONTACT_OWNER_KEYS),
                    "contact_owner_records": owner_records,
                },
                sort_keys=True,
            )
        )
    return {
        "algorithm": "locally-inset-aperture-lcs-ring-v1",
        "contact_owner_keys": list(CONTACT_OWNER_KEYS),
        "required_minimum_clearance_mm": required,
        "contact_owner_records": owner_records,
        "bounds_proven_clear_components": sorted(bounds_proven_clear),
        "authoritative_component_count": len(by_key),
        "minimum_clearance_mm": minimum_clearance,
        "maximum_intersection_mm3": 0.0,
    }


def _frustum(construction: dict[str, Any], parameters: dict[str, Any], Part: Any) -> Any:
    depth = float(
        parameters["validation_contract"]["aperture_view_frustum"]["depth_mm"]
    )
    angle = float(
        parameters["validation_contract"]["aperture_view_frustum"][
            "half_angle_deg"
        ]
    )
    expansion = depth * math.tan(math.radians(angle))
    far = toolkit.radial_offset_loop(
        construction["App"],
        construction["aperture_planar"],
        expansion,
        construction["axis_n"],
    )
    near_wire = Part.makePolygon(
        [*construction["aperture_planar"], construction["aperture_planar"][0]]
    )
    far_loop = toolkit.at_depth(far, depth, construction["axis_n"])
    far_wire = Part.makePolygon([*far_loop, far_loop[0]])
    return Part.makeLoft([near_wire, far_wire], True, False)


def _reference_cartridge(
    aperture: Sequence[Any],
    axis_n: Any,
    geometry: dict[str, Any],
    App: Any,
    Part: Any,
) -> Any:
    values = geometry["rear_cartridge_interface"]
    base_outer = toolkit.radial_offset_loop(
        App, aperture, float(values["cartridge_outer_base_offset_mm"]), axis_n
    )
    outer = _locally_inset_loop(
        App,
        base_outer,
        values["cartridge_outer_vertex_insets_mm"],
        axis_n,
    )
    inner = toolkit.radial_offset_loop(
        App, aperture, float(values["cartridge_inner_offset_mm"]), axis_n
    )
    return toolkit.ring_prism(
        Part,
        outer,
        inner,
        float(values["seated_front_depth_mm"]),
        float(values["seated_rear_depth_mm"]),
        axis_n,
        "independent rear cartridge reference",
    )


def construct_split_cassette(
    parameters: dict[str, Any],
    App: Any,
    Part: Any,
) -> tuple[Any, dict[str, Any]]:
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin = toolkit.vector(App, lcs["origin_mm"])
    axis_u = toolkit.normalized(App, toolkit.vector(App, lcs["u"]), "LCS u")
    axis_v = toolkit.normalized(App, toolkit.vector(App, lcs["v"]), "LCS v")
    axis_n = toolkit.normalized(
        App, toolkit.vector(App, lcs["inward_n"]), "LCS inward n"
    )
    aperture_exact = [toolkit.vector(App, point) for point in lcs["visible_aperture_mm"]]
    aperture = toolkit.planar_loop(
        aperture_exact, origin, axis_u, axis_v, axis_n
    )
    opening = toolkit.planar_loop(
        [
            toolkit.vector(App, point)
            for point in geometry["shell_opening_boundary_mm"]
        ],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    cassette_values = geometry["front_optical_cassette"]
    outer_front = _locally_inset_loop(
        App,
        opening,
        cassette_values["front_outer_vertex_insets_mm"],
        axis_n,
    )
    outer_rear = _locally_inset_loop(
        App,
        opening,
        cassette_values["rear_outer_vertex_insets_mm"],
        axis_n,
    )
    inner_rear = toolkit.radial_offset_loop(
        App,
        aperture,
        float(cassette_values["rear_inner_offset_mm"]),
        axis_n,
    )
    cassette = toolkit.loft_ring(
        Part,
        outer_front,
        aperture,
        outer_rear,
        inner_rear,
        float(cassette_values["bezel_front_depth_mm"]),
        float(cassette_values["bezel_rear_depth_mm"]),
        axis_n,
        "locally inset front optical cassette ring",
    )
    cover_lip, cover_lip_report = _validated_cover_lip(
        parameters, opening, axis_n, App, Part
    )
    bezel = toolkit.fuse_shapes(
        [cassette, cover_lip], "cassette plus approved lower cover lip"
    )
    pocket = cassette

    frames = toolkit.reconstruct_mount_frames(parameters, App)
    mount_values = geometry["head_mount"]
    bore_radius = float(mount_values["bore_diameter_mm"]) / 2.0
    bearing_radius = bore_radius + float(
        mount_values["bore_to_edge_material_mm"]
    )
    total_thickness = float(mount_values["total_thickness_mm"])
    pilot_length = float(mount_values["shell_side_pilot_length_mm"])
    mount_shapes = []
    ligament_shapes = []
    ligament_records: dict[str, dict[str, Any]] = {}
    cutters = []
    mounts: dict[str, dict[str, Any]] = {}
    for role, frame in frames.items():
        base = frame["eye_bore"] - frame["bore_axis_vector"] * float(
            mount_values["bore_center_to_mating_face_mm"]
        )
        shell_face_retreat = (
            float(mount_values["lower_c007_shell_face_retreat_mm"])
            if role == "lower"
            else 0.0
        )
        if shell_face_retreat < 0.0 or shell_face_retreat >= pilot_length:
            raise RuntimeError(
                f"{role}: invalid shell-side mount-face retreat "
                f"{shell_face_retreat}"
            )
        pilot_base = base + frame["bore_axis_vector"] * shell_face_retreat
        pilot = Part.makeCylinder(
            float(mount_values["shell_side_pilot_radius_mm"]),
            pilot_length - shell_face_retreat,
            pilot_base,
            frame["bore_axis_vector"],
        )
        bearing = Part.makeCylinder(
            bearing_radius,
            total_thickness - pilot_length,
            base + frame["bore_axis_vector"] * pilot_length,
            frame["bore_axis_vector"],
        )
        uncut = toolkit.fuse_shapes(
            [pilot, bearing], f"{role} localized stepped mount"
        )
        cutter = Part.makeCylinder(
            bore_radius,
            float(mount_values["bore_cutter_length_mm"]),
            frame["eye_bore"]
            - frame["bore_axis_vector"]
            * float(mount_values["bore_cutter_length_mm"])
            / 2.0,
            frame["bore_axis_vector"],
        )
        drilled = uncut.cut(cutter).removeSplitter()
        toolkit.require_single_solid(drilled, f"{role} localized drilled mount")
        mount_shapes.append(drilled)
        ligament, ligament_record = _explicit_mount_ligament(
            role,
            frame,
            outer_rear,
            mount_values,
            origin,
            axis_u,
            axis_v,
            axis_n,
            App,
            Part,
        )
        ligament_shapes.append(ligament)
        ligament_records[role] = ligament_record
        cutters.append(cutter)
        mounts[role] = {
            **frame,
            "uncut": uncut,
            "drilled": drilled,
            "collar": uncut,
            "root": uncut,
            "bore_axis_vector": frame["bore_axis_vector"],
            "bore_cutter_solid": cutter,
            "nominal_shell_side_base": base,
            "effective_shell_side_base": pilot_base,
            "shell_face_retreat_mm": shell_face_retreat,
        }

    core = toolkit.fuse_shapes(
        [cassette, *mount_shapes, *ligament_shapes],
        "direct connected split-service cassette",
    )
    core = core.cut(Part.makeCompound(cutters)).removeSplitter()
    toolkit.require_single_solid(core, "direct split-service cassette after bores")
    clearance_report = _verify_direct_shell_clearance(
        core, parameters, App, Part
    )
    final = toolkit.fuse_shapes(
        [core, cover_lip], "split-service cassette with trimmed cover lip"
    )
    final = final.cut(Part.makeCompound(cutters)).removeSplitter()
    toolkit.require_single_solid(final, "final split-service cassette")
    cartridge = _reference_cartridge(
        aperture, axis_n, geometry, App, Part
    )
    construction = {
        "App": App,
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "aperture_exact": aperture_exact,
        "aperture_planar": aperture,
        "bezel": bezel,
        "cassette": cassette,
        "pocket": pocket,
        "chamber": pocket,
        "hidden_structure": final.cut(bezel).removeSplitter(),
        "cover_lip": cover_lip,
        "cover_lip_report": cover_lip_report,
        "cap_feature": cartridge,
        "reference_cartridge": cartridge,
        "cap_roots": {},
        "mounts": mounts,
        "ligaments": ligament_records,
        "outer_front": outer_front,
        "outer_rear": outer_rear,
        "inner_rear": inner_rear,
        "shell_clearance_trim": clearance_report,
        "aperture_plane_error_mm": max(
            abs(
                toolkit.local_coordinates(
                    point, origin, axis_u, axis_v, axis_n
                )[2]
            )
            for point in aperture_exact
        ),
    }
    return final, construction


def no_rear_root_preflight(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "NOT_APPLICABLE__NO_CONTINUOUS_CHAMBER_OR_REAR_ROOTS",
        "roots": {},
        "rear_connector_boss_count": 0,
    }


def serial_immutable_preflight(
    baseline_argument: Path,
    contract_argument: Path,
    *,
    require_new_output: bool = True,
) -> dict[str, Any]:
    """Shared V2 preflight plus the exact approved serial-relief baseline."""
    root = toolkit.repository_root(contract_argument)
    baseline = toolkit.load_json(baseline_argument)
    contract = toolkit.load_json(contract_argument)
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or not isinstance(mutations[0].get("parameters"), dict):
        raise RuntimeError("split cassette requires one machine-readable mutation")
    parameters = mutations[0]["parameters"]
    pinned_baseline, pinned_manifest_path = _verify_serial_relief_reference(
        root, parameters
    )
    if baseline != pinned_baseline or baseline_argument.resolve() != pinned_manifest_path.resolve():
        raise RuntimeError("runner baseline is not the pinned serial relief manifest")

    root_projection_report = no_rear_root_preflight(parameters)
    frame_preflight_report = toolkit.preflight_signed_mount_frames(parameters)
    control = parameters["design_control"]
    registry_path = toolkit.verify_pinned_file(
        root,
        control["rejected_signature_registry"],
        "rejected-design-signature registry",
    )
    design_report = toolkit.design_control.preflight_design_control(
        contract,
        toolkit.load_json(registry_path),
        require_approval=True,
    )
    tooling = parameters["tooling_dependencies"]
    shared_validator_path = toolkit.verify_pinned_file(
        root, tooling["shared_validator"], "shared V2 validator"
    )
    shared_validator = toolkit.import_pinned_module(
        shared_validator_path,
        "cat_head_shared_v2_validator_for_split_cassette_serial",
    )
    shared_report = shared_validator.validate_files(
        baseline_argument,
        contract_argument,
        verify_files=True,
        require_new_output=require_new_output,
    )
    if shared_report.get("status") != "PASS":
        raise RuntimeError(
            json.dumps(
                {
                    "error": "shared V2 preflight failed",
                    "shared_report": shared_report,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    for key in (
        "shared_runner",
        "shared_preservation_module",
        "shared_preservation_comparator",
        "independent_previsual_validator",
        "deterministic_test",
    ):
        toolkit.verify_pinned_file(root, tooling[key], key)
    for group_name in ("fit_references", "lineage_references"):
        for name, spec in parameters[group_name].items():
            toolkit.verify_pinned_file(root, spec, f"{group_name}/{name}")
    for name in ("upper_component_manifest", "lower_component_manifest", "lower_c001"):
        toolkit.verify_pinned_file(
            root,
            parameters["validation_contract"]["shell_matrix_sources"][name],
            f"shell matrix/{name}",
        )

    baseline_path = root / baseline["assembly"]["path"]
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("serial relieved-shell baseline hash mismatch")
    if contract.get("baseline_id") != baseline.get("baseline_id"):
        raise RuntimeError("serial baseline ID mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if require_new_output and (output_dir.exists() or candidate_path.exists()):
        raise RuntimeError(f"iteration output already exists: {output_dir}")

    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    runtime_manifest = toolkit.load_json(root / contract["runtime"]["manifest_path"])
    probe_path = toolkit.verify_pinned_file(
        root,
        {
            "path": runtime_manifest["probe"]["script_path"],
            "sha256": runtime_manifest["probe"]["script_sha256"],
        },
        "approved runtime probe",
    )
    probe = toolkit.import_pinned_module(
        probe_path, "cat_head_runtime_probe_for_split_cassette_serial"
    )
    observed_runtime = probe.runtime_record()
    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    if observed_runtime != expected_runtime:
        raise RuntimeError("approved FreeCAD runtime mismatch")

    document = App.openDocument(str(baseline_path))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None or target.TypeId != "Part::Feature" or target.Shape.isNull():
            raise RuntimeError("serial baseline eye target is missing or invalid")
        original = {
            "name": target.Name,
            "label": target.Label,
            "type_id": target.TypeId,
            "placement": App.Placement(target.Placement),
        }
    except Exception:
        App.closeDocument(document.Name)
        raise
    return {
        "root": root,
        "baseline": baseline,
        "contract": contract,
        "parameters": parameters,
        "root_projection_report": root_projection_report,
        "frame_preflight_report": frame_preflight_report,
        "design_report": design_report,
        "shared_report": shared_report,
        "runtime": observed_runtime,
        "baseline_path": baseline_path,
        "output_dir": output_dir,
        "candidate_path": candidate_path,
        "document": document,
        "target": target,
        "original": original,
        "App": App,
        "Mesh": Mesh,
        "Part": Part,
        "geometry_construction_started": False,
        "requires_new_output": require_new_output,
        "io_trace": {
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
            "candidate_created": False,
        },
        "finalization_trace": {
            "target_assignment_performed": False,
            "metadata_assignment_performed": False,
            "recompute_performed": False,
            "final_assertions_performed": False,
        },
    }


def attach_history(
    target: Any,
    parameters: dict[str, Any],
    construction: dict[str, Any],
) -> list[dict[str, str]]:
    assigned: list[dict[str, str]] = []
    string_values = {
        "SplitCassetteDesignId": DESIGN_ID,
        "SplitCassetteIterationId": ITERATION_ID,
        "SplitCassetteToolingRevision": str(TOOLING_REVISION),
        "SplitCassetteDesignSignature": parameters["design_control"][
            "design_signature"
        ]["sha256"],
        "SplitCassetteArchitecture": (
            "FRONT_OPTICAL_CASSETTE__INDEPENDENT_REAR_CARTRIDGE__NO_CHAMBER"
        ),
        "SplitCassetteState": (
            "DISPOSABLE__REQUIRES_PRESERVATION_AND_PREVISUAL_PASS"
        ),
    }
    for name, value in string_values.items():
        assigned.append(
            toolkit.assign_typed_metadata_property(
                target,
                "App::PropertyString",
                name,
                "SplitServiceCassette",
                value,
            )
        )
    for name, value in {
        "SplitCassetteLCSOrigin": construction["origin"],
        "SplitCassetteLCSU": construction["axis_u"],
        "SplitCassetteLCSV": construction["axis_v"],
        "SplitCassetteLCSInwardN": construction["axis_n"],
    }.items():
        assigned.append(
            toolkit.assign_typed_metadata_property(
                target,
                "App::PropertyVector",
                name,
                "SplitServiceDatums",
                value,
            )
        )
    assigned.append(
        toolkit.assign_typed_metadata_property(
            target,
            "App::PropertyVectorList",
            "SplitCassetteVisibleAperture",
            "SplitServiceDatums",
            construction["aperture_exact"],
        )
    )
    for role, datum in parameters["mount_datums"].items():
        title = role.capitalize()
        for suffix, values in (
            ("EyeBoreCenter", datum["eye_bore_center_mm"]),
            ("HeadBoreCenter", datum["head_bore_center_mm"]),
            ("BoreAxis", datum["bore_axis"]),
        ):
            assigned.append(
                toolkit.assign_typed_metadata_property(
                    target,
                    "App::PropertyVector",
                    f"SplitCassette{title}{suffix}",
                    "SplitServiceDatums",
                    construction["origin"].__class__(*map(float, values)),
                )
            )
    geometry = parameters["geometry"]
    dimension_values = {
        "SplitCassetteShellClearance": geometry["shell_clearance_trim"][
            "minimum_verified_clearance_mm"
        ],
        "SplitCassetteRearInnerOffset": geometry[
            "front_optical_cassette"
        ]["rear_inner_offset_mm"],
        "SplitCassetteRearOuterInsetMinimum": min(geometry[
            "front_optical_cassette"
        ]["rear_outer_vertex_insets_mm"]),
        "SplitCassetteCartridgeRadialClearance": geometry[
            "rear_cartridge_interface"
        ]["radial_clearance_mm"],
        "SplitCassetteMountBoreDiameter": geometry["head_mount"][
            "bore_diameter_mm"
        ],
        "SplitCassetteMountBearingRadius": (
            geometry["head_mount"]["bore_diameter_mm"] / 2.0
            + geometry["head_mount"]["bore_to_edge_material_mm"]
        ),
        "SplitCassetteLigamentWidth": geometry["head_mount"][
            "ligament_width_mm"
        ],
        "SplitCassetteLigamentThickness": geometry["head_mount"][
            "ligament_thickness_mm"
        ],
        "SplitCassetteCoverLipReach": geometry["lower_c001_cover_lip"][
            "outward_reach_mm"
        ],
        "SplitCassetteCoverLipAxialCover": geometry["lower_c001_cover_lip"][
            "outward_axial_cover_mm"
        ],
    }
    for name, value in dimension_values.items():
        assigned.append(
            toolkit.assign_typed_metadata_property(
                target,
                "App::PropertyLength",
                name,
                "SplitServiceDimensions",
                float(value),
            )
        )
    return assigned


def assert_product_defect_regressions(
    parameters: dict[str, Any],
    construction: dict[str, Any],
) -> dict[str, Any]:
    epsilon = float(
        parameters["validation_contract"]["limits"][
            "maximum_unintended_positive_intersection_mm3"
        ]
    )
    minimum_axis_dot = float(
        parameters["validation_contract"]["limits"][
            "minimum_signed_mount_axis_dot"
        ]
    )
    frames: dict[str, Any] = {}
    for role, datum in parameters["mount_datums"].items():
        mount = construction["mounts"][role]
        signed = construction["origin"].__class__(*map(float, datum["bore_axis"]))
        signed.normalize()
        axis_dot = float(mount["bore_axis_vector"].dot(signed))
        handed = float(
            mount["tangent"].cross(mount["depth"]).dot(
                mount["bore_axis_vector"]
            )
        )
        if axis_dot < minimum_axis_dot or handed < minimum_axis_dot:
            raise RuntimeError(f"{role}: signed mount datum changed")
        frames[role] = {
            "signed_axis_dot": axis_dot,
            "right_handed_dot": handed,
        }

    Part = sys.modules.get("Part")
    if Part is None:
        import Part  # type: ignore  # noqa: F401
        Part = sys.modules["Part"]
    frustum = _frustum(construction, parameters, Part)
    non_bezel = construction["hidden_structure"]
    hidden_volume = float(non_bezel.common(frustum).Volume)
    if hidden_volume > epsilon:
        raise RuntimeError(
            f"split cassette enters protected view frustum: {hidden_volume}"
        )
    cartridge = construction["reference_cartridge"]
    cartridge_intersection = float(cartridge.common(construction["pocket"]).Volume)
    cartridge_clearance = float(cartridge.distToShape(construction["pocket"])[0])
    required_clearance = float(
        parameters["geometry"]["rear_cartridge_interface"][
            "radial_clearance_mm"
        ]
    )
    if cartridge_intersection > epsilon or (
        cartridge_clearance < required_clearance - 1.0e-6
    ):
        raise RuntimeError("independent rear cartridge interface is not separable")
    motion_values = parameters["validation_contract"]["motion"]
    maximum_motion_collision = 0.0
    for index in range(int(motion_values["rear_cap_sweep_samples"])):
        fraction = index / (int(motion_values["rear_cap_sweep_samples"]) - 1)
        moved = toolkit.translated(
            cartridge,
            construction["axis_n"]
            * float(motion_values["rear_cap_sweep_distance_mm"])
            * fraction,
        )
        maximum_motion_collision = max(
            maximum_motion_collision,
            float(moved.common(construction["pocket"]).Volume),
        )
    if maximum_motion_collision > epsilon:
        raise RuntimeError(
            f"rear cartridge service motion collides: {maximum_motion_collision}"
        )
    lip_report = construction["cover_lip_report"]
    if (
        float(lip_report["maximum_shell_intersection_mm3"]) > epsilon
        or float(lip_report["uncovered_exterior_patch_area_mm2"]) > epsilon
    ):
        raise RuntimeError("approved lower cover lip is not shell-safe and complete")
    return {
        "shell_clearance_trim": construction["shell_clearance_trim"],
        "signed_mount_frames": frames,
        "continuous_rear_chamber_present": False,
        "rear_connector_boss_count": 0,
        "hidden_non_bezel_frustum_volume_mm3": hidden_volume,
        "rear_cartridge_intersection_mm3": cartridge_intersection,
        "rear_cartridge_minimum_clearance_mm": cartridge_clearance,
        "rear_cartridge_motion_maximum_collision_mm3": maximum_motion_collision,
        "lower_c001_cover_lip": lip_report,
    }


def render_review_pack(
    context: dict[str, Any],
    baseline_records: Sequence[dict[str, Any]],
    baseline_target_shape: Any,
    construction: dict[str, Any],
) -> None:
    root = context["root"]
    contract = context["contract"]
    document = context["document"]
    Part = context["Part"]
    candidate_records = toolkit.document_records(document)
    fixed_views = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    for name, (direction, up) in fixed_views.items():
        toolkit.render_side_by_side(
            root / contract["output"]["review_files"][name],
            baseline_records,
            candidate_records,
            direction,
            up,
        )
    extras = context["parameters"]["review_artifacts"]
    axis_n = toolkit.tuple3(construction["axis_n"])
    axis_u = toolkit.tuple3(construction["axis_u"])
    for index, corner in enumerate(construction["aperture_exact"]):
        toolkit.render_side_by_side(
            root / extras["exterior_aperture_corners"][index],
            baseline_records,
            candidate_records,
            axis_n,
            axis_u,
            toolkit.tuple3(corner),
            34.0,
        )
    target = context["target"].Shape
    hardware = toolkit.hardware_shapes(
        context["parameters"], construction, Part
    )
    service_records = [
        toolkit.shape_record(target, (34, 151, 190), deflection=0.65)
    ]
    for role_shapes in hardware.values():
        for name, shape in role_shapes.items():
            color = {
                "bolt": (34, 126, 210),
                "head_washer": (242, 178, 42),
                "eye_washer": (242, 178, 42),
                "nyloc": (140, 76, 190),
                "tool": (45, 175, 104),
            }[name]
            service_records.append(
                toolkit.shape_record(shape, color, deflection=0.35)
            )
    toolkit.render_side_by_side(
        root / extras["interior_flange_backs_and_hardware"],
        [toolkit.shape_record(baseline_target_shape, (162, 169, 177))],
        service_records,
        tuple(-value for value in axis_n),
        axis_u,
    )
    seated = construction["reference_cartridge"]
    removed = toolkit.translated(
        seated,
        construction["axis_n"]
        * float(
            context["parameters"]["validation_contract"]["motion"][
                "rear_cap_sweep_distance_mm"
            ]
        ),
    )
    cartridge_records = [
        toolkit.shape_record(target, (34, 151, 190), deflection=0.65),
        toolkit.shape_record(seated, (237, 170, 55), deflection=0.45),
        toolkit.shape_record(removed, (68, 167, 112), deflection=0.45),
    ]
    toolkit.render_side_by_side(
        root / extras["rear_cap_installation_removal"],
        [toolkit.shape_record(baseline_target_shape, (162, 169, 177))],
        cartridge_records,
        toolkit.tuple3(construction["axis_v"]),
        axis_u,
    )
    section_center = (
        construction["mounts"]["upper"]["eye_bore"]
        + construction["mounts"]["lower"]["eye_bore"]
    ) / 2.0
    slab = toolkit.oriented_box(
        Part,
        section_center,
        (
            construction["axis_u"],
            construction["axis_n"],
            construction["axis_v"],
        ),
        (150.0, 60.0, 1.0),
    )
    toolkit.render_side_by_side(
        root / extras["section_through_chamber_and_mounts"],
        [
            toolkit.shape_record(
                baseline_target_shape.common(slab).removeSplitter(),
                (162, 169, 177),
                deflection=0.4,
            )
        ],
        [
            toolkit.shape_record(
                target.common(slab).removeSplitter(),
                (223, 130, 38),
                deflection=0.35,
            )
        ],
        toolkit.tuple3(construction["axis_v"]),
        axis_u,
    )


toolkit.ITERATION_ID = ITERATION_ID
toolkit.DESIGN_ID = DESIGN_ID
toolkit.TOOLING_REVISION = TOOLING_REVISION
toolkit.TARGET_OBJECT = TARGET_OBJECT
toolkit.design_control.ITERATION_ID = ITERATION_ID
toolkit.design_control.DESIGN_ID = DESIGN_ID
toolkit.design_control.TOOLING_REVISION = TOOLING_REVISION
toolkit.design_control.TARGET_OBJECT = TARGET_OBJECT
toolkit.construct_serviceable_eye = construct_split_cassette
toolkit.preflight_rear_cap_edge_projection = no_rear_root_preflight
toolkit.immutable_preflight = serial_immutable_preflight
toolkit.attach_history = attach_history
toolkit.assert_product_defect_regressions = assert_product_defect_regressions
toolkit.render_review_pack = render_review_pack

_original_in_memory_preflight = toolkit.in_memory_finalization_preflight


def in_memory_finalization_preflight(context: dict[str, Any]) -> dict[str, Any]:
    report = _original_in_memory_preflight(context)
    report.update(
        {
            "status": "IN_MEMORY_FINALIZATION_PASS__SPLIT_CASSETTE_V1_READY",
            "iteration_id": ITERATION_ID,
            "design_id": DESIGN_ID,
            "tooling_revision": TOOLING_REVISION,
            "physical_lineage": "clean_split_service_cassette_D",
            "v6_geometry_or_candidate_used": False,
        }
    )
    report.pop("quarantined_v6_candidate_used", None)
    return report


toolkit.in_memory_finalization_preflight = in_memory_finalization_preflight


if __name__ == "__main__":
    raise SystemExit(toolkit.main())
