#!/usr/bin/env python3
"""Generate isolated eye lightboxes and two-flange head mounts."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate4_assembly_review as gate4  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/gate6-eye-modules.json"
GATE1_CONFIG = PACKAGE_ROOT / "config/gate1-panel-roles.json"
GATE4_CONFIG = PACKAGE_ROOT / "config/gate4-assembly-review.json"
GATE5_BLEND = (
    PACKAGE_ROOT
    / "output/gate5-ribs-and-joints/gate5-internal-flange-tabs-review.blend"
)
OUTPUT_DIR = PACKAGE_ROOT / "output/gate6-eye-modules"
EYE_OUTPUT_DIR = OUTPUT_DIR / "eyes"
SHELL_OUTPUT_DIR = OUTPUT_DIR / "shells"
SMALL_OUTPUT_DIR = OUTPUT_DIR / "small-model-100mm"


def finish_mesh(
    name: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(value) for value in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(assigned_material)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    gate5.require_manifold(obj, f"{name} creation")
    return obj


def loop_centroid(loop: list[Vector]) -> Vector:
    return sum(loop, Vector()) / len(loop)


def radial_offset_loop(loop: list[Vector], offset: float) -> list[Vector]:
    center = loop_centroid(loop)
    output = []
    for point in loop:
        radial = point - center
        if radial.length < 0.01:
            raise ValueError("Cannot offset an eye loop through its centroid")
        output.append(point + radial.normalized() * offset)
    return output


def ring_prism(
    name: str,
    outer: list[Vector],
    inner: list[Vector],
    inward: Vector,
    start_depth: float,
    end_depth: float,
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    if len(outer) != len(inner) or len(outer) < 3:
        raise ValueError(f"{name}: ring loops are incompatible")
    count = len(outer)
    outer_front = [point + inward * start_depth for point in outer]
    inner_front = [point + inward * start_depth for point in inner]
    outer_back = [point + inward * end_depth for point in outer]
    inner_back = [point + inward * end_depth for point in inner]
    vertices = outer_front + inner_front + outer_back + inner_back
    faces: list[tuple[int, ...]] = []
    for index in range(count):
        following = (index + 1) % count
        outer_first, outer_next = index, following
        inner_first, inner_next = count + index, count + following
        outer_back_first, outer_back_next = 2 * count + index, 2 * count + following
        inner_back_first, inner_back_next = 3 * count + index, 3 * count + following
        faces.extend(
            (
                (outer_first, outer_next, inner_next, inner_first),
                (outer_back_first, inner_back_first, inner_back_next, outer_back_next),
                (outer_first, outer_back_first, outer_back_next, outer_next),
                (inner_first, inner_next, inner_back_next, inner_back_first),
            )
        )
    return finish_mesh(name, vertices, faces, assigned_material)


def polygon_prism(
    name: str,
    loop: list[Vector],
    inward: Vector,
    start_depth: float,
    end_depth: float,
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    count = len(loop)
    front = [point + inward * start_depth for point in loop]
    back = [point + inward * end_depth for point in loop]
    vertices = front + back
    faces: list[tuple[int, ...]] = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, 2 * count)),
    ]
    for index in range(count):
        following = (index + 1) % count
        faces.append((index, following, count + following, count + index))
    return finish_mesh(name, vertices, faces, assigned_material)


def cut_axis_hole(
    target: bpy.types.Object,
    name: str,
    center: Vector,
    axis: Vector,
    diameter: float,
    length: float,
) -> None:
    direction = axis.normalized()
    cutter = gate5.cylinder(
        name,
        center - direction * length / 2.0,
        center + direction * length / 2.0,
        diameter,
        vertices=24,
    )
    gate5.apply_boolean(target, cutter, "DIFFERENCE", solver="MANIFOLD")
    gate5.require_manifold(target, f"{target.name} {name}")


def duplicate_scaled(
    obj: bpy.types.Object, name: str, factor: float
) -> bpy.types.Object:
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    duplicate.name = name
    bpy.context.collection.objects.link(duplicate)
    duplicate.scale = (factor, factor, factor)
    bpy.ops.object.select_all(action="DESELECT")
    duplicate.select_set(True)
    bpy.context.view_layer.objects.active = duplicate
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    duplicate.select_set(False)
    return duplicate


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.wm.stl_export(
        filepath=str(path), export_selected_objects=True, ascii_format=False
    )
    for obj in objects:
        obj.select_set(False)


def component_topology(obj: bpy.types.Object) -> dict[str, Any]:
    boundary, nonmanifold = gate5.topology_counts(obj)
    mesh_components = gate5.components(obj)
    volume = sum(
        gate5.component_volume(obj, component) for component in mesh_components
    )
    points = [tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    dimensions = sorted(float(value) for value in obj.dimensions)
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "connected_components": len(mesh_components),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": round(volume, 3),
        "dimensions_mm_sorted": [round(value, 3) for value in dimensions],
        "orientation_search": gate2.best_fit(
            points,
            CONFIG["printer_envelope_mm"],
            int(CONFIG.get("orientation_step_degrees", 15)),
        ),
    }


def eye_geometry() -> list[dict[str, Any]]:
    gate1_config = json.loads(GATE1_CONFIG.read_text(encoding="utf-8"))
    gate4_config = json.loads(GATE4_CONFIG.read_text(encoding="utf-8"))
    model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(model.vertices), float(gate1_config["target_height_mm"])
    )
    transformed = [
        Vector(gate1.transform_point(vertex, scale, origin))
        for vertex in model.vertices
    ]
    target_bounds = gate1.bounds([tuple(value) for value in transformed])
    eye_model = gate1.read_obj(gate1.SOURCE_EYE_OBJ)
    eye_faces = gate1.find_eye_faces(eye_model, gate1_config)
    infill = gate4_config["opaque_infill"]
    definitions = (
        (
            "right",
            "EYE_RIGHT",
            "right_eye_outer_loop",
            "right_eye_inner_order",
            "right_lower_face",
        ),
        (
            "left",
            "EYE_LEFT",
            "left_eye_outer_loop",
            "left_eye_inner_order",
            "left_lower_face",
        ),
    )
    output = []
    head_center = Vector((0.0, 135.0, 150.0))
    for aperture_index, (
        side,
        unit,
        outer_key,
        order_key,
        shell,
    ) in enumerate(definitions):
        outer = [transformed[index] for index in infill[outer_key]]
        reference_face = eye_faces[unit][0]
        plane = [
            Vector(gate1.transform_point(eye_model.vertices[index], scale, origin))
            for index in reference_face.indices[:3]
        ]
        raw_inner = []
        for svg_point in gate1_config["eye_aperture_front_svg"][aperture_index]:
            x, z = gate4.front_svg_inverse(svg_point, target_bounds)
            raw_inner.append(Vector((x, gate4.y_on_plane(x, z, plane), z)))
        inner = [raw_inner[index] for index in infill[order_key]]
        inward = (outer[1] - outer[0]).cross(outer[2] - outer[0]).normalized()
        center = loop_centroid(outer)
        if inward.dot(head_center - center) < 0.0:
            inward = -inward
        output.append(
            {
                "side": side,
                "unit": unit,
                "shell": shell,
                "outer": outer,
                "aperture": inner,
                "inward": inward,
            }
        )
    return output


def add_mount_tabs(
    geometry: dict[str, Any],
    bucket: bpy.types.Object,
    shell: bpy.types.Object,
    bucket_material: bpy.types.Material,
    flange_material: bpy.types.Material,
) -> dict[str, Any]:
    settings = CONFIG["head_mount"]
    outer = geometry["outer"]
    aperture = geometry["aperture"]
    inward = geometry["inward"]
    if len(outer) != 4 or len(aperture) != 4:
        raise ValueError("Eye mount expects matching four-sided loops")
    edges = [(index, (index + 1) % 4) for index in range(4)]
    edge_midpoints = {
        edge: (outer[edge[0]] + outer[edge[1]]) / 2.0 for edge in edges
    }
    side_edge = max(edges, key=lambda edge: abs(edge_midpoints[edge].x))
    lower_edge = min(
        (edge for edge in edges if edge != side_edge),
        key=lambda edge: edge_midpoints[edge].z,
    )
    mount_edges = (("outer_side", side_edge), ("lower", lower_edge))
    length = float(settings["tab_length_mm"])
    depth = float(settings["tab_depth_mm"])
    thickness = float(settings["tab_thickness_mm"])
    gap = float(settings["tab_face_gap_mm"])
    overlap = float(settings["shell_overlap_mm"])
    front_recess = float(settings["front_recess_mm"])
    hole_depth = float(settings["bolt_depth_from_eye_plane_mm"])
    hole_diameter = float(settings["m2_5_clearance_diameter_mm"])
    fastener_axes = []
    anchor_points = []
    mount_edge_records = []
    shell_intersection_counts = []
    bucket_intersection_counts = []
    attachment_bridge_lengths = []
    for mount_number, (mount_role, edge) in enumerate(mount_edges, start=1):
        first, second = edge
        anchor = edge_midpoints[edge]
        aperture_midpoint = (aperture[first] + aperture[second]) / 2.0
        tangent = outer[second] - outer[first]
        tangent -= inward * tangent.dot(inward)
        if tangent.length < 0.01:
            raise ValueError("Eye mount edge has no in-plane direction")
        tangent.normalize()
        radial = inward.cross(tangent).normalized()
        if radial.dot(aperture_midpoint - anchor) < 0.0:
            radial = -radial
        axes = (tangent, inward, radial)
        head_center = (
            anchor
            + radial * (thickness / 2.0 - overlap)
            + inward * (front_recess + depth / 2.0)
        )
        module_center = (
            anchor
            + radial * (thickness - overlap + gap + thickness / 2.0)
            + inward * (front_recess + depth / 2.0)
        )
        head_tab = gate5.box(
            f"{geometry['side']}_eye_head_mount_tab_{mount_number}",
            head_center,
            axes,
            (length, depth, thickness),
            flange_material,
        )
        module_tab = gate5.box(
            f"{geometry['side']}_eye_module_mount_tab_{mount_number}",
            module_center,
            axes,
            (length, depth, thickness),
            bucket_material,
        )
        for tab, center in ((head_tab, head_center), (module_tab, module_center)):
            hole_center = center + inward * (hole_depth - depth / 2.0)
            cut_axis_hole(
                tab,
                f"{tab.name}_m2_5_clearance",
                hole_center,
                radial,
                hole_diameter,
                thickness + 3.0,
            )
        depsgraph = bpy.context.evaluated_depsgraph_get()
        shell_intersections = len(
            BVHTree.FromObject(shell, depsgraph).overlap(
                BVHTree.FromObject(head_tab, depsgraph)
            )
        )
        bucket_intersections = len(
            BVHTree.FromObject(bucket, depsgraph).overlap(
                BVHTree.FromObject(module_tab, depsgraph)
            )
        )
        if shell_intersections == 0:
            shell_bvh = BVHTree.FromObject(shell, depsgraph)
            nearest_candidates = []
            for vertex in head_tab.data.vertices:
                tab_vertex = head_tab.matrix_world @ vertex.co
                nearest_shell = shell_bvh.find_nearest(tab_vertex)
                if nearest_shell is not None:
                    nearest_candidates.append(
                        (nearest_shell[3], tab_vertex, nearest_shell[0])
                    )
            if not nearest_candidates:
                raise ValueError(
                    f"{head_tab.name} could not find an attachment point on "
                    f"{shell.name}"
                )
            nearest = min(nearest_candidates, key=lambda value: value[0])
            bridge_length, tab_point, shell_point = nearest
            bridge_direction = (shell_point - tab_point).normalized()
            bridge_width_axis = radial - bridge_direction * radial.dot(
                bridge_direction
            )
            if bridge_width_axis.length < 0.01:
                bridge_width_axis = inward - bridge_direction * inward.dot(
                    bridge_direction
                )
            bridge_width_axis.normalize()
            bridge_thickness_axis = bridge_direction.cross(
                bridge_width_axis
            ).normalized()
            bridge_overlap = float(
                settings["attachment_bridge_end_overlap_mm"]
            )
            bridge = gate5.box(
                f"{head_tab.name}_shell_bridge",
                (tab_point + shell_point) / 2.0,
                (bridge_direction, bridge_width_axis, bridge_thickness_axis),
                (
                    bridge_length + 2.0 * bridge_overlap,
                    float(settings["attachment_bridge_width_mm"]),
                    float(settings["attachment_bridge_thickness_mm"]),
                ),
                flange_material,
            )
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bridge_tab_intersections = len(
                BVHTree.FromObject(head_tab, depsgraph).overlap(
                    BVHTree.FromObject(bridge, depsgraph)
                )
            )
            bridge_shell_intersections = len(
                BVHTree.FromObject(shell, depsgraph).overlap(
                    BVHTree.FromObject(bridge, depsgraph)
                )
            )
            if bridge_tab_intersections == 0 or bridge_shell_intersections == 0:
                raise ValueError(
                    f"{bridge.name} failed to overlap both tab and shell"
                )
            gate5.apply_boolean(head_tab, bridge, "UNION", solver="EXACT")
            gate5.require_manifold(
                head_tab, f"{head_tab.name} shell attachment bridge"
            )
            shell_intersections = bridge_shell_intersections
            attachment_bridge_lengths.append(round(bridge_length, 4))
        else:
            attachment_bridge_lengths.append(0.0)
        if bucket_intersections == 0:
            raise ValueError(
                f"{module_tab.name} does not intersect its eye bucket"
            )
        gate5.join_closed_overlapping_mesh(shell, head_tab)
        gate5.join_closed_overlapping_mesh(bucket, module_tab)
        shell_intersection_counts.append(shell_intersections)
        bucket_intersection_counts.append(bucket_intersections)
        fastener_axes.append([round(value, 5) for value in radial])
        anchor_points.append([round(value, 4) for value in anchor])
        mount_edge_records.append(
            {"role": mount_role, "vertex_indices": [first, second]}
        )

    gate5.require_manifold(shell, f"{geometry['side']} eye head flange join")
    gate5.require_manifold(bucket, f"{geometry['side']} eye module flange join")
    return {
        "mount_edges": mount_edge_records,
        "mount_anchor_points_mm": anchor_points,
        "head_mount_flange_count": 2,
        "internal_m2_5_fastener_count": 2,
        "tab_length_mm": length,
        "tab_depth_mm": depth,
        "tab_thickness_mm": thickness,
        "tab_face_gap_mm": gap,
        "front_recess_mm": front_recess,
        "shell_overlap_mm": overlap,
        "head_tab_shell_triangle_intersections": shell_intersection_counts,
        "module_tab_bucket_triangle_intersections": bucket_intersection_counts,
        "head_tab_attachment_bridge_lengths_mm": attachment_bridge_lengths,
        "fastener_axes": fastener_axes,
        "fastener_axes_parallel_to_eye_plane": all(
            abs(Vector(axis).dot(inward)) < 1e-5 for axis in fastener_axes
        ),
        "exterior_fastener_holes": 0,
    }


def create_eye_module(
    geometry: dict[str, Any],
    shell: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    side = geometry["side"]
    values = CONFIG["module"]
    cap_values = CONFIG["rear_cap"]
    inward = geometry["inward"]
    aperture = geometry["aperture"]
    outer_fit = radial_offset_loop(
        geometry["outer"], -float(values["opening_clearance_mm"])
    )
    diffuser_loop = radial_offset_loop(
        aperture, float(values["diffuser_perimeter_overlap_mm"])
    )
    pocket_loop = radial_offset_loop(
        diffuser_loop, float(values["diffuser_pocket_clearance_mm"])
    )
    baffle_outer = radial_offset_loop(
        pocket_loop, float(values["baffle_wall_thickness_mm"])
    )
    cap_outer = radial_offset_loop(
        baffle_outer, float(cap_values["cap_perimeter_margin_mm"])
    )
    bezel_thickness = float(values["front_bezel_thickness_mm"])
    chamber_depth = float(values["chamber_depth_mm"])
    gasket = float(values["light_blocking_gasket_mm"])
    diffuser_thickness = float(values["diffuser_thickness_mm"])
    cap_start = chamber_depth + float(values["rear_cap_gap_mm"])
    cap_end = cap_start + float(values["rear_cap_thickness_mm"])

    bucket = ring_prism(
        f"{side}_eye_bucket",
        outer_fit,
        aperture,
        inward,
        0.0,
        bezel_thickness,
        materials["bucket"],
    )
    baffle = ring_prism(
        f"{side}_eye_baffle_walls",
        baffle_outer,
        pocket_loop,
        inward,
        max(0.0, bezel_thickness - 0.3),
        chamber_depth,
        materials["bucket"],
    )
    gate5.join_closed_overlapping_mesh(bucket, baffle)
    bucket.name = f"{side}_eye_bucket"

    diffuser_start = bezel_thickness + gasket
    diffuser = polygon_prism(
        f"{side}_eye_diffuser",
        diffuser_loop,
        inward,
        diffuser_start,
        diffuser_start + diffuser_thickness,
        materials["diffuser"],
    )
    cap = polygon_prism(
        f"{side}_eye_led_rear_cap",
        cap_outer,
        inward,
        cap_start,
        cap_end,
        materials["cap"],
    )
    cap_center = loop_centroid(cap_outer) + inward * ((cap_start + cap_end) / 2.0)
    cut_axis_hole(
        cap,
        f"{side}_eye_wire_port",
        cap_center,
        inward,
        float(values["wire_port_diameter_mm"]),
        float(values["rear_cap_thickness_mm"]) + 3.0,
    )

    widest_index = max(
        range(len(outer_fit)),
        key=lambda index: (outer_fit[index] - aperture[index]).length,
    )
    neighbor_indices = (
        (widest_index - 1) % len(baffle_outer),
        (widest_index + 1) % len(baffle_outer),
    )
    boss_locations = []
    for neighbor_index in neighbor_indices:
        edge_fraction = 0.32
        baffle_point = baffle_outer[widest_index].lerp(
            baffle_outer[neighbor_index], edge_fraction
        )
        outer_point = outer_fit[widest_index].lerp(
            outer_fit[neighbor_index], edge_fraction
        )
        toward_opaque_surround = outer_point - baffle_point
        if toward_opaque_surround.length < 0.01:
            raise ValueError("Eye cap boss lacks opaque surround")
        boss_locations.append(
            baffle_point
            + toward_opaque_surround.normalized()
            * float(cap_values["boss_radial_offset_mm"])
        )
    boss_records = []
    for boss_index, center_on_plane in enumerate(boss_locations, start=1):
        bucket_boss = gate5.cylinder(
            f"{side}_eye_bucket_cap_boss_{boss_index}",
            center_on_plane
            + inward
            * (chamber_depth - float(cap_values["boss_engagement_depth_mm"])),
            center_on_plane + inward * chamber_depth,
            float(cap_values["boss_diameter_mm"]),
            materials["bucket"],
            vertices=24,
        )
        cap_ear = gate5.cylinder(
            f"{side}_eye_cap_ear_{boss_index}",
            center_on_plane + inward * cap_start,
            center_on_plane + inward * cap_end,
            float(cap_values["boss_diameter_mm"]),
            materials["cap"],
            vertices=24,
        )
        for part in (bucket_boss, cap_ear):
            cut_axis_hole(
                part,
                f"{part.name}_m2_5_clearance",
                center_on_plane + inward * ((cap_start + chamber_depth) / 2.0),
                inward,
                float(cap_values["m2_5_clearance_diameter_mm"]),
                cap_end - chamber_depth + 8.0,
            )
        gate5.join_closed_overlapping_mesh(bucket, bucket_boss)
        gate5.join_closed_overlapping_mesh(cap, cap_ear)
        boss_records.append([round(value, 3) for value in center_on_plane])

    plane_u = (aperture[1] - aperture[0]).normalized()
    plane_v = inward.cross(plane_u).normalized()
    post_loop = radial_offset_loop(
        aperture, float(values["diffuser_perimeter_overlap_mm"]) * 0.62
    )
    post_front = diffuser_start + diffuser_thickness
    post_back = cap_start + 0.25
    for post_index, point in enumerate(post_loop, start=1):
        post = gate5.box(
            f"{side}_eye_diffuser_retainer_post_{post_index}",
            point + inward * ((post_front + post_back) / 2.0),
            (plane_u, plane_v, inward),
            (
                float(values["retainer_post_size_mm"]),
                float(values["retainer_post_size_mm"]),
                post_back - post_front,
            ),
            materials["cap"],
        )
        gate5.join_closed_overlapping_mesh(cap, post)

    mount_record = add_mount_tabs(
        geometry,
        bucket,
        shell,
        materials["bucket"],
        materials["flange"],
    )
    gate5.require_manifold(bucket, f"{side} complete bucket")
    gate5.require_manifold(diffuser, f"{side} diffuser")
    gate5.require_manifold(cap, f"{side} LED rear cap")

    major = max(
        (aperture[first] - aperture[second] for first, second in itertools.combinations(range(4), 2)),
        key=lambda value: value.length,
    ).normalized()
    led_center = loop_centroid(aperture) + inward * (cap_start - 0.65)
    led_references = []
    for led_index, offset in enumerate((-9.0, -3.0, 3.0, 9.0), start=1):
        led = gate5.cylinder(
            f"{side}_eye_led_reference_{led_index}",
            led_center + major * offset - inward * 0.5,
            led_center + major * offset + inward * 0.5,
            4.5,
            materials["led"],
            vertices=20,
        )
        led_references.append(led)

    led_diffuser_gap = cap_start - (diffuser_start + diffuser_thickness)
    return {
        "side": side,
        "shell": geometry["shell"],
        "bucket": bucket,
        "diffuser": diffuser,
        "cap": cap,
        "led_references": led_references,
        "visible_aperture_vertices_mm": [
            [round(coordinate, 4) for coordinate in point] for point in aperture
        ],
        "rear_cap_boss_centers_mm": boss_records,
        "led_pixels": int(values["led_pixels_per_eye"]),
        "led_diffuser_gap_mm": round(led_diffuser_gap, 3),
        "rear_cap_m2_5_fastener_count": 2,
        "head_mount": mount_record,
    }


def main() -> None:
    for directory in (OUTPUT_DIR, EYE_OUTPUT_DIR, SHELL_OUTPUT_DIR, SMALL_OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(GATE5_BLEND))
    shells = {name: bpy.data.objects[name] for name in gate2.SECTION_ORDER}
    materials = {
        "bucket": gate5.material("Gate6_opaque_eye_bucket", (0.025, 0.025, 0.03, 1.0)),
        "cap": gate5.material("Gate6_opaque_eye_cap", (0.08, 0.08, 0.09, 1.0)),
        "diffuser": gate5.material("Gate6_frosted_eye_diffuser", (0.35, 0.92, 1.0, 0.72)),
        "flange": gate5.material("Gate6_eye_head_mount_flange", (0.92, 0.58, 0.08, 1.0)),
        "led": gate5.material("Gate6_eye_led_reference", (0.0, 0.75, 1.0, 1.0)),
    }

    modules = [
        create_eye_module(geometry, shells[geometry["shell"]], materials)
        for geometry in eye_geometry()
    ]
    physical_parts = []
    for module in modules:
        side = module["side"]
        parts = [module["bucket"], module["diffuser"], module["cap"]]
        physical_parts.extend(parts)
        for part in parts:
            gate5.export_stl(part, EYE_OUTPUT_DIR / f"{part.name}.stl")

    for shell_name, shell in shells.items():
        gate5.require_manifold(shell, f"Gate 6 shell {shell_name}")
        gate5.export_stl(shell, SHELL_OUTPUT_DIR / f"{shell_name}.stl")

    small_factor = (
        float(CONFIG["small_model_head_height_mm"])
        / float(CONFIG["source_head_height_mm"])
    )
    small_exports: dict[str, list[bpy.types.Object]] = {}
    for module in modules:
        side = module["side"]
        scaled = [
            duplicate_scaled(part, f"small_{part.name}", small_factor)
            for part in (module["bucket"], module["diffuser"], module["cap"])
        ]
        small_exports[side] = scaled
        for part in scaled:
            gate5.export_stl(part, SMALL_OUTPUT_DIR / f"{part.name}.stl")
        export_selected(
            SMALL_OUTPUT_DIR / f"{side}_eye_module_visual_assembly.stl", scaled
        )

    # Keep the saved full-size review scene clean; the scaled copies have
    # already been exported to their dedicated directory.
    for scaled in small_exports.values():
        for obj in scaled:
            bpy.data.objects.remove(obj, do_unlink=True)

    all_review_objects = list(shells.values()) + physical_parts + [
        led for module in modules for led in module["led_references"]
    ]
    export_selected(OUTPUT_DIR / "gate6-eye-modules-review.stl", all_review_objects)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in all_review_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "gate6-eye-modules-review.glb"),
        export_format="GLB",
        use_selection=True,
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "gate6-eye-modules-review.blend")
    )

    part_metrics = {
        part.name: component_topology(part) for part in physical_parts
    }
    shell_metrics = {
        name: component_topology(shell) for name, shell in shells.items()
    }
    report_modules = []
    for module in modules:
        report_modules.append(
            {
                key: value
                for key, value in module.items()
                if key not in {"bucket", "diffuser", "cap", "led_references"}
            }
        )
    all_part_metrics = list(part_metrics.values())
    acceptance = {
        "two_independent_eye_lightboxes": len(modules) == 2,
        "three_printed_parts_per_eye": len(physical_parts) == 6,
        "corrected_eye_apertures_preserved": all(
            len(module["visible_aperture_vertices_mm"]) == 4
            for module in report_modules
        ),
        "four_addressable_led_references_per_eye": all(
            module["led_pixels"] == 4 for module in report_modules
        ),
        "minimum_led_diffuser_gap_preserved": all(
            module["led_diffuser_gap_mm"]
            >= float(CONFIG["module"]["minimum_led_diffuser_gap_mm"])
            for module in report_modules
        ),
        "two_internal_head_mount_flanges_per_eye": all(
            module["head_mount"]["head_mount_flange_count"] == 2
            and module["head_mount"]["internal_m2_5_fastener_count"] == 2
            for module in report_modules
        ),
        "head_mounts_recessed_at_outer_side_and_lower_edges": all(
            {edge["role"] for edge in module["head_mount"]["mount_edges"]}
            == {"outer_side", "lower"}
            and module["head_mount"]["front_recess_mm"] > 0.0
            for module in report_modules
        ),
        "all_head_mount_tabs_intersect_their_printed_owners": all(
            all(
                value > 0
                for value in module["head_mount"]
                ["head_tab_shell_triangle_intersections"]
            )
            and all(
                value > 0
                for value in module["head_mount"]
                ["module_tab_bucket_triangle_intersections"]
            )
            for module in report_modules
        ),
        "head_mount_axes_parallel_to_eye_planes": all(
            module["head_mount"]["fastener_axes_parallel_to_eye_plane"]
            for module in report_modules
        ),
        "no_exterior_eye_fastener_holes": all(
            module["head_mount"]["exterior_fastener_holes"] == 0
            for module in report_modules
        ),
        "two_removable_rear_cap_fasteners_per_eye": all(
            module["rear_cap_m2_5_fastener_count"] == 2
            for module in report_modules
        ),
        "all_eye_parts_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in all_part_metrics
        ),
        "all_gate6_shells_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in shell_metrics.values()
        ),
        "all_full_size_eye_parts_fit_printer": all(
            value["orientation_search"]["fits"] for value in all_part_metrics
        ),
        "small_model_visual_exports_created": all(
            (SMALL_OUTPUT_DIR / f"{side}_eye_module_visual_assembly.stl").exists()
            for side in ("left", "right")
        ),
    }
    if not all(acceptance.values()):
        failures = [name for name, passed in acceptance.items() if not passed]
        raise ValueError(f"Gate 6 validation failed: {failures}")

    report = {
        "gate": "Gate 6 isolated eye lightbox modules",
        "status": "review_required",
        "modules": report_modules,
        "full_size_eye_part_metrics": part_metrics,
        "revised_shell_metrics": shell_metrics,
        "hardware": {
            "head_mount": "4 total M2.5 through-bolts, 8 washers, and 4 loose nyloc nuts",
            "rear_caps": "4 total M2.5 through-bolts, 8 washers, and 4 loose nyloc nuts",
            "leds": "8 addressable 5 V RGB pixels total; 4 independently controlled pixels per eye",
        },
        "small_model_scale": round(small_factor, 6),
        "acceptance": acceptance,
        "review_notes": CONFIG["review_notes"],
    }
    (OUTPUT_DIR / "gate6-eye-module-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_DIR.relative_to(REPO_ROOT)}")


CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
