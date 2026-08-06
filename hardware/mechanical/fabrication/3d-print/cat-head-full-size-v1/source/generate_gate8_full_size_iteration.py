#!/usr/bin/env python3
"""Generate the first full-size structural iteration after the 100 mm print."""

from __future__ import annotations

import copy
import json
import sys
from collections import defaultdict
from math import acos, degrees, radians
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/gate8-full-size-structural-iteration.json"
OUTPUT_DIR = PACKAGE_ROOT / "output/10-design-gates/gate8-full-size-structural-iteration"
STAGE5_DIR = OUTPUT_DIR / "_stage5-structural"
STAGE6_DIR = OUTPUT_DIR / "_stage6-eyes"
STAGE7_DIR = OUTPUT_DIR / "_stage7-glow"
SHELL_OUTPUT_DIR = OUTPUT_DIR / "shells"
INSERT_OUTPUT_DIR = OUTPUT_DIR / "glow-inserts"
EYE_OUTPUT_DIR = OUTPUT_DIR / "eye-modules"
PORTAL_OUTPUT_DIR = OUTPUT_DIR / "portal-clamps"
COUPON_OUTPUT_DIR = OUTPUT_DIR / "test-coupons"


def clear_stls(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("*.stl"):
        stale.unlink()


def configure_stage_outputs(config: dict[str, Any]) -> None:
    muzzle = config["opaque_muzzle_frame"]
    gate7.CONFIG = copy.deepcopy(gate7.CONFIG)
    gate7.CONFIG["opaque_reclassified_panels"] = list(
        muzzle["opaque_reclassified_panel_ids"]
    )
    gate7.CONFIG["central_group_name"] = muzzle["central_group_name"]
    gate7.CONFIG["combined_groups"].pop("central_12_panel_cluster", None)
    gate7.CONFIG["combined_groups"][muzzle["central_group_name"]] = list(
        muzzle["central_translucent_panel_ids"]
    )
    gate7.CONFIG["expected"]["approved_panel_count"] -= len(
        muzzle["opaque_reclassified_panel_ids"]
    )
    gate7.CONFIG["expected"]["central_panel_count"] = len(
        muzzle["central_translucent_panel_ids"]
    )
    gate7.CONFIG.setdefault("combined_mount_modes", {})[
        muzzle["central_group_name"]
    ] = "upper_shared_edges"
    gate7.CONFIG["review_notes"] = [
        note.replace(
            "The twelve connected centerline facets",
            "The six retained centerline facets",
        )
        for note in gate7.CONFIG["review_notes"]
    ]
    gate3_blend = gate3.OUTPUT_DIR / "gate3-structural-shells.blend"
    gate3_dependencies = [gate3.GATE3_CONFIG, Path(gate3.__file__)]
    if not gate3_blend.exists() or gate3_blend.stat().st_mtime < max(
        path.stat().st_mtime for path in gate3_dependencies
    ):
        print("Rebuilding Gate 3 for the current rear-base baseline")
        gate3.main()

    final_stage_blend = STAGE7_DIR / "gate7-glow-panel-inserts-review.blend"
    stage_dependencies = [
        CONFIG_PATH,
        *gate3_dependencies,
        gate3_blend,
        Path(gate5.__file__),
        Path(gate6.__file__),
        Path(gate7.__file__),
    ]
    if final_stage_blend.exists() and final_stage_blend.stat().st_mtime >= max(
        path.stat().st_mtime for path in stage_dependencies
    ):
        print(f"Reusing current staged assembly: {final_stage_blend}")
        bpy.ops.wm.open_mainfile(filepath=str(final_stage_blend))
        return

    gate5.CONFIG_PATH = CONFIG_PATH
    gate5.OUTPUT_DIR = STAGE5_DIR
    gate5.main()

    gate6.GATE5_BLEND = STAGE5_DIR / "gate5-internal-flange-tabs-review.blend"
    gate6.OUTPUT_DIR = STAGE6_DIR
    gate6.EYE_OUTPUT_DIR = STAGE6_DIR / "eyes"
    gate6.SHELL_OUTPUT_DIR = STAGE6_DIR / "shells"
    gate6.SMALL_OUTPUT_DIR = STAGE6_DIR / "small-model-100mm"
    gate6.main()

    gate7.GATE6_BLEND = STAGE6_DIR / "gate6-eye-modules-review.blend"
    gate7.OUTPUT_DIR = STAGE7_DIR
    gate7.INSERT_OUTPUT_DIR = STAGE7_DIR / "glow-inserts"
    gate7.SHELL_OUTPUT_DIR = STAGE7_DIR / "shells"
    gate7.SMALL_OUTPUT_DIR = STAGE7_DIR / "small-model-100mm"
    gate7.CONFIG["ear_root_interfaces"]["connector_clearance_mm"] = 1.2
    gate7.CONFIG["ear_root_interfaces"]["connector_corner_relief_depth_mm"] = 38.0
    gate7.CONFIG["ear_root_interfaces"]["connector_side_tip_setback_mm"] = 18.0
    gate7.CONFIG["mount"]["front_recess_mm"] = float(
        config["glow_panel_mounts"]["minimum_exterior_recess_mm"]
    )
    gate7.main()


def finish_prism(
    name: str,
    surface: list[Vector],
    inward: Vector,
    depth: float,
    material: bpy.types.Material,
    outward_start: float = 0.0,
) -> bpy.types.Object:
    outward = -inward
    front = [point + outward * outward_start for point in surface]
    back = [point + inward * depth for point in surface]
    vertices = front + back
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    return gate6.finish_mesh(name, vertices, faces, material)


def strip_surface(
    record: dict[str, Any],
    transformed: list[Vector],
    inside_width: float,
    outside_overlap: float,
) -> list[Vector]:
    first, second = record["edge"]
    p0, p1 = transformed[first], transformed[second]
    radial = record["radial"]
    return [
        p0 - radial * outside_overlap,
        p1 - radial * outside_overlap,
        p1 + radial * inside_width,
        p0 + radial * inside_width,
    ]


def add_opaque_muzzle_frame(
    config: dict[str, Any],
    shells: dict[str, bpy.types.Object],
    central_insert: bpy.types.Object,
    context: dict[str, Any],
) -> dict[str, Any]:
    values = config["opaque_muzzle_frame"]
    panel_groups = values["opaque_panel_groups"]
    configured_panels = {
        panel for panel_ids in panel_groups.values() for panel in panel_ids
    }
    if configured_panels != set(values["opaque_reclassified_panel_ids"]):
        raise ValueError("Opaque muzzle panel groups do not cover reclassified panels")
    thickness = float(values["opaque_panel_thickness_mm"])
    inside_panel = float(values["root_inside_panel_mm"])
    inside_shell = float(values["root_inside_shell_mm"])
    root_depth = float(values["root_depth_mm"])
    root_setback = float(values["root_surface_setback_mm"])
    transformed = context["transformed"]
    records = []
    insert_volume_before = gate5.mesh_volume(central_insert)
    for shell_name, panel_ids in panel_groups.items():
        shell = shells[shell_name]
        face_indices = [
            index
            for index, panel_id in enumerate(context["panel_by_face"])
            if panel_id in panel_ids
        ]
        group = {
            "name": f"gate8_opaque_{shell_name}",
            "panel_ids": sorted(panel_ids),
            "face_indices": face_indices,
            "combined": len(panel_ids) > 1,
        }
        surface_faces = gate7.group_surface_faces(group, context)
        used = sorted(
            {
                index
                for surface_face in surface_faces
                for index in surface_face["indices"]
            }
        )
        remap = {source: local for local, source in enumerate(used)}
        opaque_panel = gate7.finish_surface_insert(
            group["name"],
            [transformed[index] for index in used],
            [
                tuple(remap[index] for index in surface_face["indices"])
                for surface_face in surface_faces
            ],
            shell.data.materials[0],
            thickness_mm=thickness,
        )
        panel_volume = gate5.mesh_volume(opaque_panel)
        boundary = gate7.group_boundary(group, context)
        root_count = 0
        root_length = 0.0
        for edge_number, record in enumerate(boundary, start=1):
            if record["owner"] != shell_name:
                continue
            length = max(2.0, float(record["length"]) - 0.8)
            root = gate5.box(
                f"{group['name']}_structural_root_{edge_number}",
                record["midpoint"]
                + record["radial"] * ((inside_panel - inside_shell) / 2.0)
                + record["inward"] * (root_setback + root_depth / 2.0),
                (record["tangent"], record["inward"], record["radial"]),
                (length, root_depth, inside_panel + inside_shell),
                shell.data.materials[0],
            )
            gate5.join_closed_overlapping_mesh(shell, root)
            root_count += 1
            root_length += length
        if root_count == 0:
            raise ValueError(f"{group['name']} has no structural shell roots")
        gate5.join_closed_overlapping_mesh(shell, opaque_panel)
        records.append(
            {
                "owner_shell": shell_name,
                "panel_ids": sorted(panel_ids),
                "source_face_count": len(surface_faces),
                "panel_volume_mm3": round(panel_volume, 3),
                "structural_root_count": root_count,
                "structural_root_length_mm": round(root_length, 3),
            }
        )
    gate5.require_manifold(central_insert, "Gate 8 six-panel central insert")
    insert_volume_after = gate5.mesh_volume(central_insert)
    return {
        "opaque_panel_group_count": len(records),
        "opaque_reclassified_panel_count": len(configured_panels),
        "central_translucent_panel_count": len(
            values["central_translucent_panel_ids"]
        ),
        "opaque_panel_groups": records,
        "central_insert_volume_before_mm3": round(insert_volume_before, 3),
        "central_insert_volume_after_mm3": round(insert_volume_after, 3),
        "central_insert_retained_volume_ratio": round(
            insert_volume_after / insert_volume_before, 4
        ),
        "symmetric": len(records) == 4
        and sum(record["owner_shell"].startswith("right") for record in records)
        == sum(record["owner_shell"].startswith("left") for record in records)
        and sum(
            len(record["panel_ids"])
            for record in records
            if record["owner_shell"].startswith("right")
        )
        == sum(
            len(record["panel_ids"])
            for record in records
            if record["owner_shell"].startswith("left")
        ),
    }


def add_inter_shell_edge_rails(
    config: dict[str, Any],
    shells: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    values = config["inter_shell_edge_rails"]
    target_sections = set(values["target_sections"])
    model, assignments, scale, origin = gate5.transformed_source()
    points, segments = gate5.seam_segments(model, assignments, scale, origin)
    excluded = {
        tuple(value) for value in config.get("excluded_joint_face_pairs", [])
    }
    end_setback = float(values["end_setback_mm"])
    foot_width = float(values["foot_width_mm"])
    depth = float(values["inward_depth_mm"])
    overlap = float(values["shell_overlap_mm"])
    seam_inset = float(values["seam_inset_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    minimum = float(values["minimum_length_mm"])
    records = []
    counts: dict[str, int] = defaultdict(int)
    rail_material = gate5.material(
        "Gate8_continuous_inter_shell_edge_rails", (0.56, 0.08, 0.045, 1.0)
    )
    for segment in segments:
        if segment["length_mm"] < minimum:
            continue
        if tuple(segment["face_groups"]) in excluded:
            continue
        if "rear_base" in segment["sections"]:
            continue
        p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
        tangent = (p1 - p0).normalized()
        seam_point = p0.lerp(p1, 0.5)
        length = float(segment["length_mm"]) - 2.0 * end_setback
        if length <= 4.0:
            continue
        for section in segment["sections"]:
            if section not in target_sections:
                continue
            geometry = gate5.side_geometry(
                f"gate8_seam_rail_{section}",
                segment,
                section,
                seam_point,
                tangent,
                model,
                points,
            )
            face_offset = min(
                seam_inset + foot_width / 2.0,
                geometry["face_depth_mm"] * 0.72,
            )
            center = (
                seam_point
                + geometry["toward_face"] * face_offset
                - geometry["normal"] * (wall + depth / 2.0 - overlap)
            )
            counts[section] += 1
            rail = gate5.box(
                f"gate8_inter_shell_rail_{section}_{counts[section]:02d}",
                center,
                (tangent, geometry["toward_face"], geometry["normal"]),
                (length, foot_width, depth),
                rail_material,
            )
            rail_volume = gate5.mesh_volume(rail)
            gate5.join_closed_overlapping_mesh(shells[section], rail)
            records.append(
                {
                    "section": section,
                    "source_faces": list(segment["face_groups"]),
                    "length_mm": round(length, 3),
                    "foot_width_mm": foot_width,
                    "depth_mm": depth,
                    "volume_mm3": round(rail_volume, 3),
                }
            )
    if set(counts) != target_sections:
        raise ValueError(
            "Gate 8 seam rails missing requested sections: "
            f"{sorted(target_sections - set(counts))}"
        )
    return {
        "rail_count": len(records),
        "rails_by_section": dict(sorted(counts.items())),
        "total_length_mm": round(sum(record["length_mm"] for record in records), 3),
        "records": records,
    }


def rebuild_mesh_from_polygons(
    name: str,
    source: bpy.types.Object,
    polygons: list[tuple[tuple[int, ...], int]],
) -> bpy.types.Mesh:
    used = sorted({index for indices, _ in polygons for index in indices})
    remap = {source_index: local for local, source_index in enumerate(used)}
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [tuple(source.data.vertices[index].co) for index in used],
        [],
        [tuple(remap[index] for index in indices) for indices, _ in polygons],
    )
    mesh.update(calc_edges=True)
    for material in source.data.materials:
        mesh.materials.append(material)
    for polygon, (_, material_index) in zip(mesh.polygons, polygons):
        polygon.material_index = material_index
    return mesh


def separate_reinforcement_materials(
    shell: bpy.types.Object,
    target_materials: set[str],
) -> bpy.types.Object | None:
    material_names = [
        material.name if material is not None else None
        for material in shell.data.materials
    ]
    target_indices = {
        index
        for index, name in enumerate(material_names)
        if name in target_materials
    }
    if not target_indices:
        return None
    vertex_components = gate5.components(shell)
    vertex_component = {
        vertex_index: component_index
        for component_index, vertices in enumerate(vertex_components)
        for vertex_index in vertices
    }
    component_total_area: dict[int, float] = defaultdict(float)
    component_target_area: dict[int, float] = defaultdict(float)
    for polygon in shell.data.polygons:
        component_index = vertex_component[polygon.vertices[0]]
        component_total_area[component_index] += polygon.area
        if polygon.material_index in target_indices:
            component_target_area[component_index] += polygon.area
    target_components = {
        component_index
        for component_index, total_area in component_total_area.items()
        if total_area > 0.0
        and component_target_area[component_index] / total_area >= 0.5
    }
    target_polygons = []
    retained_polygons = []
    for polygon in shell.data.polygons:
        record = (tuple(polygon.vertices), polygon.material_index)
        if vertex_component[polygon.vertices[0]] in target_components:
            target_polygons.append(record)
        else:
            retained_polygons.append(record)
    if not target_polygons:
        return None
    old_mesh = shell.data
    retained_mesh = rebuild_mesh_from_polygons(
        f"{shell.name}_without_insert_conflict_reinforcement_mesh",
        shell,
        retained_polygons,
    )
    reinforcement_mesh = rebuild_mesh_from_polygons(
        f"{shell.name}_insert_clearance_reinforcement_mesh",
        shell,
        target_polygons,
    )
    shell.data = retained_mesh
    reinforcement = bpy.data.objects.new(
        f"{shell.name}_insert_clearance_reinforcement",
        reinforcement_mesh,
    )
    bpy.context.collection.objects.link(reinforcement)
    reinforcement.matrix_world = shell.matrix_world.copy()
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    gate5.require_manifold(shell, f"{shell.name} retained non-reinforcement geometry")
    gate5.require_manifold(
        reinforcement, f"{shell.name} separated reinforcement geometry"
    )
    return reinforcement


def expanded_insert_cutter(
    insert: bpy.types.Object,
    clearance: float,
    suffix: str,
) -> bpy.types.Object:
    cutter = insert.copy()
    cutter.data = insert.data.copy()
    cutter.name = f"{insert.name}_{suffix}"
    bpy.context.collection.objects.link(cutter)
    cutter.matrix_world = insert.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(cutter.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(cutter.data)
    bm.free()
    cutter.data.update(calc_edges=True)
    for vertex in cutter.data.vertices:
        normal = vertex.normal.copy()
        if normal.length > 0.001:
            vertex.co += normal.normalized() * clearance
    cutter.data.update(calc_edges=True)
    gate5.require_manifold(cutter, f"{insert.name} expanded clearance cutter")
    return cutter


def split_closed_components(
    source: bpy.types.Object,
) -> list[bpy.types.Object]:
    """Split a joined collection of closed solids into Boolean-safe objects."""
    vertex_components = gate5.components(source)
    vertex_component = {
        vertex_index: component_index
        for component_index, vertices in enumerate(vertex_components)
        for vertex_index in vertices
    }
    component_polygons: dict[int, list[tuple[tuple[int, ...], int]]] = defaultdict(
        list
    )
    for polygon in source.data.polygons:
        component_index = vertex_component[polygon.vertices[0]]
        if any(
            vertex_component[vertex_index] != component_index
            for vertex_index in polygon.vertices
        ):
            raise ValueError(f"{source.name} contains a polygon spanning components")
        component_polygons[component_index].append(
            (tuple(polygon.vertices), polygon.material_index)
        )

    output = []
    for component_index, polygons in sorted(component_polygons.items()):
        mesh = rebuild_mesh_from_polygons(
            f"{source.name}_component_{component_index:03d}_mesh",
            source,
            polygons,
        )
        component = bpy.data.objects.new(
            f"{source.name}_component_{component_index:03d}", mesh
        )
        bpy.context.collection.objects.link(component)
        component.matrix_world = source.matrix_world.copy()
        gate5.require_manifold(component, f"{source.name} separated component")
        output.append(component)

    bpy.data.objects.remove(source, do_unlink=True)
    return output


def triangle_intersection_count(
    first: bpy.types.Object, second: bpy.types.Object
) -> int:
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return len(
        BVHTree.FromObject(first, depsgraph).overlap(
            BVHTree.FromObject(second, depsgraph)
        )
    )


def bounding_boxes_overlap(
    first: bpy.types.Object, second: bpy.types.Object
) -> bool:
    first_points = [first.matrix_world @ Vector(corner) for corner in first.bound_box]
    second_points = [
        second.matrix_world @ Vector(corner) for corner in second.bound_box
    ]
    for axis in range(3):
        first_min = min(point[axis] for point in first_points)
        first_max = max(point[axis] for point in first_points)
        second_min = min(point[axis] for point in second_points)
        second_max = max(point[axis] for point in second_points)
        if first_max < second_min or second_max < first_min:
            return False
    return True


def trim_reinforcement_for_inserts(
    config: dict[str, Any],
    shells: dict[str, bpy.types.Object],
    inserts: list[bpy.types.Object],
) -> dict[str, Any]:
    values = config["insert_clearance_trimming"]
    clearance = float(values["clearance_mm"])
    boolean_overcut = float(values.get("boolean_overcut_mm", 0.25))
    target_materials = set(values["target_materials"])
    records = []
    for section in values["target_sections"]:
        shell = shells[section]
        reinforcement = separate_reinforcement_materials(shell, target_materials)
        if reinforcement is None:
            continue
        components = split_closed_components(reinforcement)
        volume_before = sum(gate5.mesh_volume(component) for component in components)
        before_intersections = 0
        trimmed_pairs: set[tuple[str, str]] = set()
        boolean_candidate_count = 0
        omitted_components = []
        retained_components = []
        for component in components:
            omit_component = False
            for insert in inserts:
                if len(component.data.polygons) == 0:
                    break
                check_cutter = expanded_insert_cutter(
                    insert, clearance, f"clearance_check_for_{section}"
                )
                intersections = triangle_intersection_count(
                    component, check_cutter
                )
                before_intersections += intersections
                bpy.data.objects.remove(check_cutter, do_unlink=True)
                trim_cutter = expanded_insert_cutter(
                    insert,
                    clearance + boolean_overcut,
                    f"clearance_trim_for_{section}",
                )
                if not bounding_boxes_overlap(component, trim_cutter):
                    bpy.data.objects.remove(trim_cutter, do_unlink=True)
                    continue
                trim_cutter_components = split_closed_components(trim_cutter)
                pair_trimmed = False
                for cutter_index, trim_cutter_component in enumerate(
                    trim_cutter_components
                ):
                    if not bounding_boxes_overlap(
                        component, trim_cutter_component
                    ):
                        bpy.data.objects.remove(
                            trim_cutter_component, do_unlink=True
                        )
                        continue
                    boolean_candidate_count += 1
                    gate5.apply_boolean(
                        component,
                        trim_cutter_component,
                        "DIFFERENCE",
                        solver="EXACT",
                    )
                    boundary, nonmanifold = gate5.topology_counts(component)
                    if boundary or nonmanifold:
                        omitted_components.append(
                            {
                                "component": component.name,
                                "reason": "boolean_would_not_remain_manifold",
                                "insert": insert.name,
                                "boundary_edges": boundary,
                                "nonmanifold_edges": nonmanifold,
                                "volume_mm3": round(
                                    gate5.mesh_volume(component), 3
                                ),
                            }
                        )
                        omit_component = True
                        for remaining_cutter in trim_cutter_components[
                            cutter_index + 1 :
                        ]:
                            bpy.data.objects.remove(
                                remaining_cutter, do_unlink=True
                            )
                        break
                    pair_trimmed = True
                if omit_component:
                    break
                if pair_trimmed:
                    trimmed_pairs.add((component.name, insert.name))
            if omit_component:
                bpy.data.objects.remove(component, do_unlink=True)
                continue
            if len(component.data.polygons) > 0:
                retained_components.append(component)
            else:
                bpy.data.objects.remove(component, do_unlink=True)
        components = retained_components
        volume_after = sum(gate5.mesh_volume(component) for component in components)
        after_clearance_intersections = 0
        after_insert_intersections = 0
        remaining_conflicts = []
        residual_conflict_component_names = set()
        for component in components:
            for insert in inserts:
                actual_count = triangle_intersection_count(component, insert)
                after_insert_intersections += actual_count
                cutter = expanded_insert_cutter(
                    insert, clearance, f"postcheck_for_{section}"
                )
                clearance_count = triangle_intersection_count(component, cutter)
                after_clearance_intersections += clearance_count
                bpy.data.objects.remove(cutter, do_unlink=True)
                if actual_count or clearance_count:
                    residual_conflict_component_names.add(component.name)
                    remaining_conflicts.append(
                        {
                            "component": component.name,
                            "insert": insert.name,
                            "actual": actual_count,
                            "clearance": clearance_count,
                        }
                    )
        if residual_conflict_component_names:
            residual_components = [
                component
                for component in components
                if component.name in residual_conflict_component_names
            ]
            retained_after_residual_check = [
                component
                for component in components
                if component.name not in residual_conflict_component_names
            ]
            for component in residual_components:
                omitted_components.append(
                    {
                        "component": component.name,
                        "reason": "residual_insert_envelope_contact",
                        "conflicts": [
                            conflict
                            for conflict in remaining_conflicts
                            if conflict["component"] == component.name
                        ],
                        "volume_mm3": round(gate5.mesh_volume(component), 3),
                    }
                )
                bpy.data.objects.remove(component, do_unlink=True)
            components = retained_after_residual_check
            after_insert_intersections = 0
            after_clearance_intersections = 0
            volume_after = sum(
                gate5.mesh_volume(component) for component in components
            )
        if after_insert_intersections or after_clearance_intersections:
            raise ValueError(
                f"{section} reinforcement still intersects glow inserts: "
                f"actual={after_insert_intersections}, "
                f"clearance={after_clearance_intersections}, "
                f"pairs={remaining_conflicts}"
            )
        for component in components:
            gate5.join_closed_overlapping_mesh(shell, component)
        gate5.require_manifold(shell, f"{section} trimmed reinforcement shell")
        records.append(
            {
                "section": section,
                "clearance_mm": clearance,
                "boolean_overcut_mm": boolean_overcut,
                "boolean_candidate_count": boolean_candidate_count,
                "trimmed_reinforcement_insert_pairs": len(trimmed_pairs),
                "omitted_conflicting_component_count": len(omitted_components),
                "omitted_conflicting_components": omitted_components,
                "triangle_intersections_before": before_intersections,
                "triangle_intersections_after_actual_insert": after_insert_intersections,
                "triangle_intersections_after_clearance_envelope": after_clearance_intersections,
                "reinforcement_volume_before_mm3": round(volume_before, 3),
                "reinforcement_volume_after_mm3": round(volume_after, 3),
                "reinforcement_volume_removed_mm3": round(
                    volume_before - volume_after, 3
                ),
            }
        )
    return {
        "clearance_mm": clearance,
        "target_materials": sorted(target_materials),
        "sections": records,
        "total_triangle_intersections_before": sum(
            record["triangle_intersections_before"] for record in records
        ),
        "total_triangle_intersections_after": sum(
            record["triangle_intersections_after_clearance_envelope"]
            for record in records
        ),
        "total_reinforcement_volume_before_mm3": round(
            sum(record["reinforcement_volume_before_mm3"] for record in records),
            3,
        ),
        "total_reinforcement_volume_removed_mm3": round(
            sum(record["reinforcement_volume_removed_mm3"] for record in records),
            3,
        ),
        "total_omitted_conflicting_component_count": sum(
            record["omitted_conflicting_component_count"] for record in records
        ),
        "total_omitted_conflicting_component_volume_mm3": round(
            sum(
                omitted["volume_mm3"]
                for record in records
                for omitted in record["omitted_conflicting_components"]
            ),
            3,
        ),
    }


def closest_opaque_face(
    context: dict[str, Any],
    section: str,
    target: Vector,
) -> tuple[Vector, Vector, str, list[Vector]]:
    candidates = []
    for index, assignment in enumerate(context["assignments"]):
        if assignment != section:
            continue
        face = context["model"].faces[index]
        indices, normal, center = gate7.oriented_face(
            face, context["transformed"]
        )
        distance = (center - target).length
        source_vertices = [context["transformed"][value] for value in indices]
        candidates.append(
            (distance, center, normal, face.group, source_vertices)
        )
    if not candidates:
        raise ValueError(f"No opaque source face found for {section}")
    _, center, normal, face_group, source_vertices = min(
        candidates, key=lambda value: value[0]
    )
    return center, normal, face_group, source_vertices


def integrated_tube_socket(
    name: str,
    center: Vector,
    axis: Vector,
    across: Vector,
    outward: Vector,
    values: dict[str, Any],
    material: bpy.types.Material,
    length: float | None = None,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    axis = axis.normalized()
    outward = (outward - axis * outward.dot(axis)).normalized()
    across = outward.cross(axis).normalized()
    inner = float(values["tube_outer_width_mm"]) + float(
        values["tube_design_clearance_mm"]
    )
    wall = float(values["clamp_wall_mm"])
    outer = inner + 2.0 * wall
    length = float(length or values["clamp_length_mm"])
    end_overlap = float(values["socket_end_overlap_mm"])
    side_span = inner + 2.0 * end_overlap
    parts = [
        gate5.box(
            f"{name}_back_wall",
            center + outward * (inner / 2.0 + wall / 2.0),
            (across, outward, axis),
            (outer, wall, length),
            material,
        ),
        gate5.box(
            f"{name}_front_wall",
            center - outward * (inner / 2.0 + wall / 2.0),
            (across, outward, axis),
            (outer, wall, length),
            material,
        ),
    ]
    for side in (-1.0, 1.0):
        parts.append(
            gate5.box(
                f"{name}_side_wall_{int(side)}",
                center + across * side * (inner / 2.0 + wall / 2.0),
                (across, outward, axis),
                (wall, side_span, length),
                material,
            )
        )
    parts.append(
        gate5.box(
            f"{name}_blind_end_stop",
            center + axis * (length / 2.0 + wall / 2.0 - end_overlap),
            (across, outward, axis),
            (outer, outer, wall),
            material,
        )
    )

    def manifold_union(
        union_name: str, parts: list[bpy.types.Object]
    ) -> bpy.types.Object:
        combined = parts[0]
        combined.name = union_name
        for tool in parts[1:]:
            gate5.apply_boolean(combined, tool, "UNION", solver="MANIFOLD")
            gate5.require_manifold(combined, f"{union_name} manifold union")
        return combined

    socket = manifold_union(f"{name}_integrated_socket", parts)
    cut_extension = 2.0
    hole_diameter = float(values["m4_clearance_diameter_mm"])
    bolt_offset = float(values["bolt_offset_from_open_end_mm"])
    if not wall < bolt_offset < length - wall:
        raise ValueError(f"{name}: transverse bolt position is outside socket")
    open_center = center - axis * (length / 2.0)
    bolt_center = open_center + axis * bolt_offset
    hole = gate5.cylinder(
        f"{name}_transverse_m4",
        bolt_center - across * (outer / 2.0 + cut_extension),
        bolt_center + across * (outer / 2.0 + cut_extension),
        hole_diameter,
    )
    gate5.apply_boolean(socket, hole, "DIFFERENCE", solver="MANIFOLD")
    gate5.require_manifold(socket, f"{name} transverse M4 clearance")
    return socket, {
        "integrated_with_shell": True,
        "removable_cap_count": 0,
        "inner_width_mm": inner,
        "outer_width_mm": outer,
        "length_mm": length,
        "blind_end_stop": True,
        "m4_fastener_count": 1,
        "bolt_offset_from_open_end_mm": bolt_offset,
        "bolt_center_mm": [round(value, 3) for value in bolt_center],
        "bolt_axis": [round(value, 5) for value in across],
    }


def add_aluminum_portals(
    config: dict[str, Any],
    shells: dict[str, bpy.types.Object],
    context: dict[str, Any],
) -> tuple[list[bpy.types.Object], list[bpy.types.Object], dict[str, Any]]:
    values = config["aluminum_upright_portals"]
    portal_material = gate5.material(
        "Gate8_aluminum_portal_clamps", (0.22, 0.48, 0.58, 1.0)
    )
    tube_material = gate5.material(
        "Gate8_aluminum_tube_reference", (0.58, 0.62, 0.64, 0.82)
    )
    shell_wall = float(config["shell_wall_thickness_mm"])
    pad_thickness = float(values["mount_pad_thickness_mm"])
    pad_overlap = float(values["mount_pad_shell_overlap_mm"])
    tube_references = []
    reports = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    horizontal = Vector((1.0, 0.0, 0.0))

    def socket_basis(axis: Vector, normal: Vector) -> tuple[Vector, Vector]:
        if values.get("socket_roll_reference") == "head_x_projected":
            across = (horizontal - axis * horizontal.dot(axis)).normalized()
            outward = axis.cross(across).normalized()
            return across, outward
        outward = (normal - axis * normal.dot(axis)).normalized()
        return outward.cross(axis).normalized(), outward

    for side in ("right", "left"):
        shell_name = f"{side}_upper_head"
        target = Vector(values[f"upper_target_{side}_mm"])
        lower = Vector(values[f"lower_route_{side}_mm"])
        surface, normal, face_group, source_vertices = closest_opaque_face(
            context, shell_name, target
        )
        axis = (surface - lower).normalized()
        across, outward = socket_basis(axis, normal)
        inner_surface = surface - normal * shell_wall
        clamp_length = float(values["clamp_length_mm"])
        minimum_exterior_recess = float(values["minimum_exterior_recess_mm"])
        open_center = inner_surface - axis * (clamp_length + 1.2)
        pad_face_scale = float(values["mount_pad_face_scale"])
        pad_front = [
            surface
            + (point - surface) * pad_face_scale
            - normal * (shell_wall - pad_overlap)
            for point in source_vertices
        ]
        pad = gate7.finish_surface_insert(
            f"gate8_{side}_portal_mount_pad",
            pad_front,
            [tuple(range(len(pad_front)))],
            portal_material,
            pad_thickness,
        )
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        pad_shell_intersections = len(
            BVHTree.FromObject(pad, depsgraph).overlap(
                BVHTree.FromObject(shells[shell_name], depsgraph)
            )
        )
        if pad_shell_intersections == 0:
            raise ValueError(f"{side} portal pad does not intersect {shell_name}")
        gate5.join_closed_overlapping_mesh(shells[shell_name], pad)

        socket = None
        socket_report = {}
        maximum_exterior_distance = 0.0
        total_inward_shift = 0.0
        placement_iterations = 0
        for placement_iterations in range(1, 6):
            axis = (open_center - lower).normalized()
            across, outward = socket_basis(axis, normal)
            clamp_center = open_center + axis * (clamp_length / 2.0)
            socket, socket_report = integrated_tube_socket(
                f"gate8_{side}_tube_portal",
                clamp_center,
                axis,
                across,
                outward,
                values,
                portal_material,
            )
            maximum_exterior_distance = max(
                (
                    (socket.matrix_world @ vertex.co) - surface
                ).dot(normal)
                for vertex in socket.data.vertices
            )
            if maximum_exterior_distance <= -minimum_exterior_recess + 1e-5:
                break
            inward_shift = (
                maximum_exterior_distance + minimum_exterior_recess + 0.02
            )
            bpy.data.objects.remove(socket, do_unlink=True)
            socket = None
            open_center -= normal * inward_shift
            total_inward_shift += inward_shift
        if socket is None or maximum_exterior_distance > -minimum_exterior_recess + 1e-5:
            raise ValueError(
                f"{side} portal cannot satisfy exterior recess: "
                f"{maximum_exterior_distance:.4f} mm"
            )
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        socket_shell_intersections = len(
            BVHTree.FromObject(socket, depsgraph).overlap(
                BVHTree.FromObject(shells[shell_name], depsgraph)
            )
        )
        if socket_shell_intersections == 0:
            raise ValueError(f"{side} integral socket misses {shell_name}")
        gate5.join_closed_overlapping_mesh(shells[shell_name], socket)

        stop = open_center + axis * (
            clamp_length - float(values["socket_end_overlap_mm"])
        )
        tube_vector = stop - lower
        tube = gate5.box(
            f"gate8_{side}_aluminum_tube_reference",
            (lower + stop) / 2.0,
            (across, outward, axis),
            (
                float(values["tube_outer_width_mm"]),
                float(values["tube_outer_width_mm"]),
                tube_vector.length,
            ),
            tube_material,
        )
        tube_references.append(tube)
        reports[side] = {
            "shell": shell_name,
            "source_face": face_group,
            "surface_anchor_mm": [round(value, 3) for value in surface],
            "lower_route_reference_mm": [round(value, 3) for value in lower],
            "tube_axis": [round(value, 5) for value in axis],
            "socket_roll_reference": values.get(
                "socket_roll_reference", "local_shell_normal"
            ),
            "cross_bolt_angle_from_head_x_deg": round(
                degrees(acos(min(1.0, abs(across.dot(horizontal))))), 3
            ),
            "tube_reference_length_mm": round(tube_vector.length, 3),
            "mount_pad_shell_triangle_intersections": pad_shell_intersections,
            "mount_pad_source_face_scale": pad_face_scale,
            "socket_shell_triangle_intersections": socket_shell_intersections,
            "socket_placement_iterations": placement_iterations,
            "socket_inward_shift_mm": round(total_inward_shift, 3),
            "maximum_exterior_plane_signed_distance_mm": round(
                maximum_exterior_distance, 3
            ),
            "minimum_exterior_recess_mm": round(-maximum_exterior_distance, 3),
            "outside_exterior_plane_vertex_count": 0,
            **socket_report,
        }
    return [], tube_references, reports


def add_fit_coupon(
    config: dict[str, Any],
) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    values = config["aluminum_upright_portals"]
    material = gate5.material(
        "Gate8_portal_fit_coupon", (0.92, 0.45, 0.08, 1.0)
    )
    socket, report = integrated_tube_socket(
        "gate8_portal_fit_coupon",
        Vector((0.0, 0.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
        Vector((1.0, 0.0, 0.0)),
        Vector((0.0, 1.0, 0.0)),
        values,
        material,
        length=float(values["fit_coupon_length_mm"]),
    )
    bpy.ops.object.select_all(action="DESELECT")
    socket.select_set(True)
    bpy.context.view_layer.objects.active = socket
    socket.rotation_euler.x = radians(90.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    socket.select_set(False)
    report["stl_orientation"] = "one outer socket wall flat on print bed"
    report["support_guidance"] = (
        "bridge the upper socket wall; no projecting clamp ears remain"
    )
    return [socket], report


def recalculate_outward_normals(obj: bpy.types.Object) -> None:
    """Make each disconnected closed solid consistently outward-facing."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)


def repair_legacy_left_upper_bridge(
    shell: bpy.types.Object,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    """Replace the inherited overlapping hidden bridge solids with one hull."""
    original_name = shell.name
    shell_material = shell.data.materials[0]
    parts = split_closed_components(shell)
    expected_center = Vector((-112.0, 127.0, 177.0))
    candidate_parts = []
    candidate_vertices = []
    volume_before = 0.0
    for part in parts:
        world_vertices = [part.matrix_world @ vertex.co for vertex in part.data.vertices]
        center = sum(world_vertices, Vector()) / len(world_vertices)
        if (center - expected_center).length < 8.0:
            candidate_parts.append(part)
            candidate_vertices.extend(world_vertices)
            volume_before += gate5.mesh_volume(part)
    if len(candidate_parts) < 2:
        raise ValueError(
            "Expected at least two overlapping legacy left-upper bridge solids "
            f"near {list(expected_center)}; found {len(candidate_parts)}"
        )
    center = sum(candidate_vertices, Vector()) / len(candidate_vertices)
    remaining = [part for part in parts if part not in candidate_parts]
    bridge = gate5.convex_hull_objects(
        "gate8_repaired_legacy_left_upper_bridge",
        candidate_parts,
        shell_material,
    )
    recalculate_outward_normals(bridge)
    gate5.require_manifold(bridge, "Gate 8 repaired legacy left-upper bridge")
    volume_after = gate5.mesh_volume(bridge)
    rebuilt_parts = [*remaining, bridge]
    combined = rebuilt_parts[0]
    for part in rebuilt_parts[1:]:
        gate5.join_closed_overlapping_mesh(combined, part)
    combined.name = original_name
    gate5.require_manifold(combined, "Gate 8 rebuilt left upper shell")
    return combined, {
        "expected_center_mm": [round(value, 3) for value in expected_center],
        "center_mm": [round(value, 3) for value in center],
        "merged_component_count": len(candidate_parts),
        "volume_before_mm3": round(volume_before, 3),
        "volume_after_mm3": round(volume_after, 3),
        "method": "location-targeted convex hull of overlapping hidden bridge solids",
    }


def export_gate8(
    config: dict[str, Any],
    shells: dict[str, bpy.types.Object],
    inserts: list[bpy.types.Object],
    portal_caps: list[bpy.types.Object],
    tube_references: list[bpy.types.Object],
    coupon_parts: list[bpy.types.Object],
    reports: dict[str, Any],
) -> None:
    for directory in (
        SHELL_OUTPUT_DIR,
        INSERT_OUTPUT_DIR,
        EYE_OUTPUT_DIR,
        PORTAL_OUTPUT_DIR,
        COUPON_OUTPUT_DIR,
    ):
        clear_stls(directory)
    left_upper_bridge_repair = None
    for name, shell in shells.items():
        if name == "left_upper_head":
            shell, left_upper_bridge_repair = repair_legacy_left_upper_bridge(
                shell
            )
            shells[name] = shell
        recalculate_outward_normals(shell)
        gate5.require_manifold(shell, f"Gate 8 shell {name}")
        gate5.export_stl(shell, SHELL_OUTPUT_DIR / f"{name}.stl")
    for insert in inserts:
        recalculate_outward_normals(insert)
        gate5.require_manifold(insert, f"Gate 8 insert {insert.name}")
        gate5.export_stl(insert, INSERT_OUTPUT_DIR / f"{insert.name}.stl")
    for cap in portal_caps:
        recalculate_outward_normals(cap)
        gate5.require_manifold(cap, f"Gate 8 portal cap {cap.name}")
        gate5.export_stl(cap, PORTAL_OUTPUT_DIR / f"{cap.name}.stl")
    for part in coupon_parts:
        recalculate_outward_normals(part)
        gate5.require_manifold(part, f"Gate 8 coupon {part.name}")
        gate5.export_stl(part, COUPON_OUTPUT_DIR / f"{part.name}.stl")

    stage6_report = json.loads(
        (STAGE6_DIR / "gate6-eye-module-validation.json").read_text(
            encoding="utf-8"
        )
    )
    eye_names = list(stage6_report["full_size_eye_part_metrics"])
    eye_parts = [bpy.data.objects[name] for name in eye_names]
    for part in eye_parts:
        gate5.export_stl(part, EYE_OUTPUT_DIR / f"{part.name}.stl")

    review_objects = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj not in coupon_parts
    ]
    gate6.export_selected(
        OUTPUT_DIR / "gate8-full-size-structural-review.stl",
        review_objects,
    )
    bpy.ops.object.select_all(action="DESELECT")
    for obj in review_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "gate8-full-size-structural-review.glb"),
        export_format="GLB",
        use_selection=True,
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "gate8-full-size-structural-review.blend")
    )
    backup = OUTPUT_DIR / "gate8-full-size-structural-review.blend1"
    if backup.exists():
        backup.unlink()

    shell_metrics = {
        name: gate7.part_metrics(shell) for name, shell in shells.items()
    }
    insert_metrics = {
        insert.name: gate7.part_metrics(insert) for insert in inserts
    }
    portal_metrics = {
        cap.name: gate7.part_metrics(cap) for cap in portal_caps
    }
    coupon_metrics = {
        part.name: gate7.part_metrics(part) for part in coupon_parts
    }
    stage5_report = json.loads(
        (STAGE5_DIR / "gate5-validation-report.json").read_text(
            encoding="utf-8"
        )
    )
    ear_modules = {
        pair: count
        for pair, count in stage5_report["flange_tab_modules_by_pair"].items()
        if "_ear" in pair
    }
    acceptance = {
        "all_shells_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in shell_metrics.values()
        ),
        "legacy_left_upper_bridge_rebuilt_as_manifold_solid": (
            left_upper_bridge_repair is not None
            and left_upper_bridge_repair["volume_after_mm3"] > 0.0
        ),
        "all_glow_inserts_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in insert_metrics.values()
        ),
        "all_portal_coupons_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in {**portal_metrics, **coupon_metrics}.values()
        ),
        "every_ear_has_broad_flange_saddle": bool(ear_modules)
        and all(count == 1 for count in ear_modules.values()),
        "every_flange_module_uses_configured_fastener_count": all(
            record["internal_m3_screws"]
            == (
                config["joint_system"]["ear_fastener_count_per_module"]
                if any(section.endswith("_ear") for section in record["sections"])
                else config["joint_system"]["body_fastener_count_per_module"]
            )
            for record in stage5_report["flange_tab_manifest"]
            if not record.get("procedural_rear_base_attachment", False)
        ),
        "every_matching_flange_tab_has_continuous_solid_root_base": all(
            record.get("flange_root_is_continuous_solid_base", False)
            for record in stage5_report["flange_tab_manifest"]
            if not record.get("procedural_rear_base_attachment", False)
        ),
        "opaque_muzzle_frame_is_symmetric": reports["muzzle"]["symmetric"],
        "central_insert_is_explicit_six_panel_cluster": reports["muzzle"]
        ["central_translucent_panel_count"]
        == 6,
        "six_side_panels_reclassified_opaque": reports["muzzle"]
        ["opaque_reclassified_panel_count"]
        == 6,
        "every_opaque_panel_group_has_structural_roots": all(
            record["structural_root_count"] > 0
            for record in reports["muzzle"]["opaque_panel_groups"]
        ),
        "inter_shell_rails_cover_six_structural_sections": len(
            reports["seam_rails"]["rails_by_section"]
        )
        == 6,
        "reinforcement_conflicts_were_detected_and_trimmed": reports[
            "insert_clearance"
        ]["total_triangle_intersections_before"]
        > 0,
        "reinforcement_clears_every_glow_insert_envelope": reports[
            "insert_clearance"
        ]["total_triangle_intersections_after"]
        == 0,
        "conservative_reinforcement_omission_is_under_one_percent": reports[
            "insert_clearance"
        ]["total_omitted_conflicting_component_volume_mm3"]
        / reports["insert_clearance"]["total_reinforcement_volume_before_mm3"]
        < 0.01,
        "two_aluminum_portals_created": set(reports["portals"]) == {
            "left",
            "right",
        },
        "aluminum_portals_are_integral_upper_shell_sockets": all(
            value["integrated_with_shell"]
            and value["removable_cap_count"] == 0
            for value in reports["portals"].values()
        ),
        "each_aluminum_socket_has_one_transverse_m4_path": all(
            value["m4_fastener_count"] == 1
            for value in reports["portals"].values()
        ),
        "portal_mount_pads_intersect_shells": all(
            value["mount_pad_shell_triangle_intersections"] > 0
            for value in reports["portals"].values()
        ),
        "portal_envelopes_stay_behind_exterior_shell_planes": all(
            value["outside_exterior_plane_vertex_count"] == 0
            and value["minimum_exterior_recess_mm"]
            >= float(
                config["aluminum_upright_portals"]["minimum_exterior_recess_mm"]
            )
            for value in reports["portals"].values()
        ),
        "nominal_tube_has_positive_fit_clearance": (
            reports["coupon"]["inner_width_mm"]
            > float(config["aluminum_upright_portals"]["tube_outer_width_mm"])
        ),
        "rear_base_has_six_intentional_rear_m5_paths": (
            stage5_report["rear_m5_screw_count"] == 6
            and stage5_report["exterior_fastener_hole_count"] == 6
        ),
        "all_shells_fit_printer_orientation_search": all(
            value["orientation_search"]["fits"]
            for value in shell_metrics.values()
        ),
    }
    if not all(acceptance.values()):
        failed = [name for name, passed in acceptance.items() if not passed]
        raise ValueError(f"Gate 8 validation failed: {failed}")
    report = {
        "gate": "Gate 8 full-size post-print structural iteration",
        "status": "review_required",
        "source_feedback": [
            "Opaque structural muzzle margins replace the eye-adjacent edges of the central diffuser.",
            "All matching flange modules use continuous solid shell-root bases; each ear retains one broad four-bolt saddle.",
            "Opaque shell seams gain continuous internal load-spreading rails.",
            "A shallow rear-loaded base replaces the 18 mm undercut frame; six M5 bolts clamp it to 28 x 36 x 10 mm shell-integrated pads with 14 mm nut and tool envelopes.",
            "Glow-panel shell mounts are recessed 2.0 mm behind their exterior source planes.",
            "Panel ribs and seam rails are trimmed to a 0.8 mm clearance envelope around every removable glow insert.",
            (
                "Two blind integral upper-shell sockets stay at least "
                f"{config['aluminum_upright_portals']['minimum_exterior_recess_mm']:.1f} mm "
                "behind the exterior shell planes, accept nominal 3/4 inch "
                "Everbilt 6605 square aluminum tube, and retain it with one "
                "transverse M4 bolt per side."
            ),
        ],
        "structural_flange_summary": {
            "module_length_mm": config["joint_system"]["module_length_mm"],
            "tab_thickness_mm": config["joint_system"][
                "flange_tab_thickness_mm"
            ],
            "tab_depth_mm": config["joint_system"]["flange_tab_depth_mm"],
            "body_fasteners_per_module": config["joint_system"][
                "body_fastener_count_per_module"
            ],
            "ear_fasteners_per_module": config["joint_system"][
                "ear_fastener_count_per_module"
            ],
            "ear_modules": ear_modules,
            "total_internal_m3_fasteners": stage5_report[
                "internal_m3_screw_count"
            ],
            "rear_loaded_m5_fasteners": stage5_report["rear_m5_screw_count"],
            "rear_pad_dimensions_mm": [28.0, 30.0, 10.0],
            "rear_nut_tool_envelope_diameter_mm": 14.0,
        },
        "opaque_muzzle_frame": reports["muzzle"],
        "inter_shell_edge_rails": reports["seam_rails"],
        "glow_insert_reinforcement_clearance": reports["insert_clearance"],
        "aluminum_portals": reports["portals"],
        "portal_fit_coupon": reports["coupon"],
        "shell_metrics": shell_metrics,
        "glow_insert_metrics": insert_metrics,
        "separate_portal_part_metrics": portal_metrics,
        "left_upper_legacy_bridge_repair": left_upper_bridge_repair,
        "coupon_metrics": coupon_metrics,
        "acceptance": acceptance,
        "review_notes": config["review_notes"],
    }
    (OUTPUT_DIR / "gate8-full-size-structural-validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_DIR.relative_to(REPO_ROOT)}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_stage_outputs(config)
    shells = {name: bpy.data.objects[name] for name in gate2.SECTION_ORDER}
    inserts = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.name.startswith("glow_insert_")
    ]
    central_insert = bpy.data.objects[
        f"glow_insert_{config['opaque_muzzle_frame']['central_group_name']}"
    ]
    context = gate7.source_context()
    muzzle_report = add_opaque_muzzle_frame(
        config, shells, central_insert, context
    )
    seam_report = add_inter_shell_edge_rails(config, shells)
    insert_clearance_report = trim_reinforcement_for_inserts(
        config, shells, inserts
    )
    portal_caps, tube_references, portal_report = add_aluminum_portals(
        config, shells, context
    )
    coupon_parts, coupon_report = add_fit_coupon(config)
    export_gate8(
        config,
        shells,
        inserts,
        portal_caps,
        tube_references,
        coupon_parts,
        {
            "muzzle": muzzle_report,
            "seam_rails": seam_report,
            "insert_clearance": insert_clearance_report,
            "portals": portal_report,
            "coupon": coupon_report,
        },
    )


if __name__ == "__main__":
    main()
