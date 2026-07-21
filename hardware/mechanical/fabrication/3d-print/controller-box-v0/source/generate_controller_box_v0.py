#!/usr/bin/env python3
"""Generate the review-first controller enclosure V0 in Blender."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PACKAGE_ROOT / "config/controller-box-v0.json"
OUTPUT_DIR = PACKAGE_ROOT / "output"
CONFIG: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def activate(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    result = bpy.data.materials.get(name)
    if result is None:
        result = bpy.data.materials.new(name)
    result.diffuse_color = color
    return result


def box(
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name="printable_edge_radius", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        modifier.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def cylinder(
    name: str,
    diameter: float,
    depth: float,
    location: tuple[float, float, float],
    axis: str = "Z",
    vertices: int = 48,
) -> bpy.types.Object:
    rotation = (0.0, 0.0, 0.0)
    if axis == "X":
        rotation = (0.0, math.radians(90.0), 0.0)
    elif axis == "Y":
        rotation = (math.radians(90.0), 0.0, 0.0)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=diameter / 2.0,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    return obj


def boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    activate(target)
    modifier = target.modifiers.new(name=f"{operation}_{tool.name}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def clean_mesh(obj: bpy.types.Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.001)
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def union(target: bpy.types.Object, addition: bpy.types.Object) -> None:
    boolean(target, addition, "UNION")


def subtract_box(
    target: bpy.types.Object,
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    bevel: float = 0.0,
) -> None:
    boolean(target, box(name, size, location, bevel), "DIFFERENCE")


def subtract_hole(
    target: bpy.types.Object,
    name: str,
    diameter: float,
    depth: float,
    location: tuple[float, float, float],
    axis: str = "Z",
    vertices: int = 48,
) -> None:
    boolean(target, cylinder(name, diameter, depth, location, axis, vertices), "DIFFERENCE")


def capsule_tool(
    name: str,
    length: float,
    width: float,
    depth: float,
    location: tuple[float, float, float],
) -> bpy.types.Object:
    straight = max(length - width, 0.1)
    tool = box(name, (straight, width, depth), location)
    end_offset = straight / 2.0
    for index, sign in enumerate((-1.0, 1.0), start=1):
        cap = cylinder(
            f"{name}_cap_{index}",
            width,
            depth,
            (location[0] + sign * end_offset, location[1], location[2]),
        )
        union(tool, cap)
    return tool


def frame(
    name: str,
    outer: tuple[float, float, float],
    inner: tuple[float, float],
    location: tuple[float, float, float],
    bevel: float = 0.0,
) -> bpy.types.Object:
    result = box(name, outer, location, bevel)
    subtract_box(
        result,
        f"{name}_opening",
        (inner[0], inner[1], outer[2] + 1.0),
        location,
        min(bevel, 1.0),
    )
    return result


def add_boss(
    target: bpy.types.Object,
    name: str,
    diameter: float,
    depth: float,
    location: tuple[float, float, float],
    axis: str = "Z",
) -> None:
    union(target, cylinder(name, diameter, depth, location, axis))


def build_base() -> bpy.types.Object:
    cfg = CONFIG["enclosure"]
    panel_cfg = CONFIG["connector_panel"]
    tray_cfg = CONFIG["tray"]
    length = float(cfg["outer_length_mm"])
    width = float(cfg["outer_width_mm"])
    height = float(cfg["base_height_mm"])
    wall = float(cfg["wall_mm"])
    floor = float(cfg["floor_mm"])
    radius = float(cfg["corner_radius_mm"])

    base = box("PRINT_base", (length, width, height), (0.0, 0.0, height / 2.0), radius)
    subtract_box(
        base,
        "base_inner_cavity",
        (length - 2.0 * wall, width - 2.0 * wall, height + 2.0),
        (0.0, 0.0, floor + (height + 2.0) / 2.0),
        max(radius - wall, 1.0),
    )

    boss_x = float(cfg["lid_screw_x_mm"])
    boss_y = float(cfg["lid_screw_y_mm"])
    for index, (x, y) in enumerate(
        [(-boss_x, -boss_y), (-boss_x, boss_y), (boss_x, -boss_y), (boss_x, boss_y)],
        start=1,
    ):
        add_boss(base, f"lid_boss_{index}", 9.0, height - floor - 1.5, (x, y, floor + (height - floor - 1.5) / 2.0))
        subtract_hole(
            base,
            f"lid_insert_pilot_{index}",
            float(cfg["m3_insert_pilot_mm"]),
            7.0,
            (x, y, height - 4.5),
        )

    ear_x = float(cfg["mounting_ear_x_mm"])
    ear_y = float(cfg["mounting_ear_y_mm"])
    ear_length = float(cfg["mounting_ear_length_mm"])
    ear_width = float(cfg["mounting_ear_width_mm"])
    ear_thickness = float(cfg["mounting_ear_thickness_mm"])
    for index, (x, y) in enumerate(
        [(-ear_x, -ear_y), (-ear_x, ear_y), (ear_x, -ear_y), (ear_x, ear_y)],
        start=1,
    ):
        ear = box(
            f"mounting_ear_{index}",
            (ear_length, ear_width, ear_thickness),
            (x, y, ear_thickness / 2.0),
            3.0,
        )
        union(base, ear)
        slot = capsule_tool(
            f"mounting_slot_{index}",
            float(cfg["mounting_slot_length_mm"]),
            float(cfg["mounting_slot_width_mm"]),
            ear_thickness + 2.0,
            (x, y, ear_thickness / 2.0),
        )
        boolean(base, slot, "DIFFERENCE")

    panel_center_z = float(panel_cfg["center_z_mm"])
    subtract_box(
        base,
        "connector_panel_opening",
        (
            wall + 6.0,
            float(panel_cfg["opening_width_mm"]),
            float(panel_cfg["opening_height_mm"]),
        ),
        (length / 2.0, 0.0, panel_center_z),
        1.5,
    )
    for index, (y, z) in enumerate(
        [
            (-float(panel_cfg["screw_y_mm"]), panel_center_z - float(panel_cfg["screw_z_offset_mm"])),
            (-float(panel_cfg["screw_y_mm"]), panel_center_z + float(panel_cfg["screw_z_offset_mm"])),
            (float(panel_cfg["screw_y_mm"]), panel_center_z - float(panel_cfg["screw_z_offset_mm"])),
            (float(panel_cfg["screw_y_mm"]), panel_center_z + float(panel_cfg["screw_z_offset_mm"])),
        ],
        start=1,
    ):
        subtract_hole(
            base,
            f"panel_clearance_{index}",
            float(panel_cfg["m3_clearance_mm"]),
            wall + 2.0,
            (length / 2.0, y, z),
            "X",
        )

    support_height = float(tray_cfg["support_height_mm"])
    support_z = floor + support_height / 2.0
    for index, (x, y) in enumerate(
        [
            (-float(tray_cfg["screw_x_mm"]), -float(tray_cfg["screw_y_mm"])),
            (-float(tray_cfg["screw_x_mm"]), float(tray_cfg["screw_y_mm"])),
            (float(tray_cfg["screw_x_mm"]), -float(tray_cfg["screw_y_mm"])),
            (float(tray_cfg["screw_x_mm"]), float(tray_cfg["screw_y_mm"])),
        ],
        start=1,
    ):
        add_boss(base, f"tray_support_{index}", 8.0, support_height, (x, y, support_z))
        subtract_hole(
            base,
            f"tray_pilot_{index}",
            float(tray_cfg["m3_pilot_mm"]),
            support_height + 2.0,
            (x, y, support_z),
        )
    return base


def build_lid() -> bpy.types.Object:
    cfg = CONFIG["enclosure"]
    switch_cfg = CONFIG["switch"]
    base_height = float(cfg["base_height_mm"])
    lid_height = float(cfg["lid_height_mm"])
    overlap = float(cfg["lid_overlap_mm"])
    lid_bottom = base_height - overlap
    lid = box(
        "PRINT_lid",
        (float(cfg["lid_outer_length_mm"]), float(cfg["lid_outer_width_mm"]), lid_height),
        (0.0, 0.0, lid_bottom + lid_height / 2.0),
        float(cfg["corner_radius_mm"]) + 1.0,
    )
    clearance = float(CONFIG["printer"]["fit_clearance_per_side_mm"])
    cavity_height = lid_height - float(cfg["lid_top_mm"]) + 0.3
    subtract_box(
        lid,
        "lid_overlap_cavity",
        (
            float(cfg["outer_length_mm"]) + 2.0 * clearance,
            float(cfg["outer_width_mm"]) + 2.0 * clearance,
            cavity_height,
        ),
        (0.0, 0.0, lid_bottom + cavity_height / 2.0 - 0.1),
        float(cfg["corner_radius_mm"]) + clearance,
    )
    for index, (x, y) in enumerate(
        [
            (-float(cfg["lid_screw_x_mm"]), -float(cfg["lid_screw_y_mm"])),
            (-float(cfg["lid_screw_x_mm"]), float(cfg["lid_screw_y_mm"])),
            (float(cfg["lid_screw_x_mm"]), -float(cfg["lid_screw_y_mm"])),
            (float(cfg["lid_screw_x_mm"]), float(cfg["lid_screw_y_mm"])),
        ],
        start=1,
    ):
        subtract_hole(lid, f"lid_clearance_{index}", float(cfg["m3_clearance_mm"]), lid_height + 2.0, (x, y, lid_bottom + lid_height / 2.0))
        subtract_hole(lid, f"lid_counterbore_{index}", float(cfg["m3_head_clearance_mm"]), 2.0, (x, y, lid_bottom + lid_height - 0.9))

    switch_x = float(switch_cfg["center_x_mm"])
    switch_y = float(switch_cfg["center_y_mm"])
    subtract_box(
        lid,
        "switch_membrane_opening",
        (
            float(switch_cfg["lid_opening_length_mm"]),
            float(switch_cfg["lid_opening_width_mm"]),
            lid_height + 2.0,
        ),
        (switch_x, switch_y, lid_bottom + lid_height / 2.0),
        2.0,
    )
    for index, (x, y) in enumerate(switch_fastener_centers(), start=1):
        subtract_hole(lid, f"switch_bezel_lid_hole_{index}", float(switch_cfg["m2_clearance_mm"]), lid_height + 2.0, (x, y, lid_bottom + lid_height / 2.0), vertices=32)
    return lid


def switch_fastener_centers() -> list[tuple[float, float]]:
    cfg = CONFIG["switch"]
    cx = float(cfg["center_x_mm"])
    cy = float(cfg["center_y_mm"])
    dx = float(cfg["bezel_screw_x_mm"])
    dy = float(cfg["bezel_screw_y_mm"])
    return [(cx - dx, cy - dy), (cx - dx, cy + dy), (cx + dx, cy - dy), (cx + dx, cy + dy)]


def build_tray() -> bpy.types.Object:
    cfg = CONFIG["tray"]
    enclosure = CONFIG["enclosure"]
    converter = CONFIG["converter_reference"]
    pcb = CONFIG["pixelblaze_reference"]
    z0 = float(enclosure["floor_mm"]) + float(cfg["support_height_mm"])
    thickness = float(cfg["thickness_mm"])
    tray = box(
        "PRINT_electronics_tray",
        (float(cfg["length_mm"]), float(cfg["width_mm"]), thickness),
        (0.0, 0.0, z0 + thickness / 2.0),
        2.0,
    )
    for index, (x, y) in enumerate(
        [
            (-float(cfg["screw_x_mm"]), -float(cfg["screw_y_mm"])),
            (-float(cfg["screw_x_mm"]), float(cfg["screw_y_mm"])),
            (float(cfg["screw_x_mm"]), -float(cfg["screw_y_mm"])),
            (float(cfg["screw_x_mm"]), float(cfg["screw_y_mm"])),
        ],
        start=1,
    ):
        subtract_hole(tray, f"tray_clearance_{index}", float(cfg["m3_clearance_mm"]), thickness + 2.0, (x, y, z0 + thickness / 2.0))

    converter_cx = float(converter["center_x_mm"])
    converter_cy = float(converter["center_y_mm"])
    converter_length = float(converter["length_mm"])
    converter_width = float(converter["width_mm"])
    tray_top = z0 + thickness
    for index, x in enumerate((converter_cx - converter_length * 0.27, converter_cx + converter_length * 0.27), start=1):
        for side, y in enumerate((converter_cy - converter_width / 2.0 - 4.0, converter_cy + converter_width / 2.0 + 4.0), start=1):
            subtract_box(tray, f"converter_tie_slot_{index}_{side}", (8.0, 3.2, thickness + 2.0), (x, y, z0 + thickness / 2.0), 0.8)
    for index, y in enumerate((converter_cy - converter_width / 2.0 - 1.3, converter_cy + converter_width / 2.0 + 1.3), start=1):
        rail = box(
            f"converter_guide_rail_{index}",
            (converter_length + 4.0, 2.0, 3.0),
            (converter_cx, y, tray_top + 1.5),
            0.7,
        )
        union(tray, rail)

    pcb_cx = float(pcb["center_x_mm"])
    pcb_cy = float(pcb["center_y_mm"])
    pcb_length = float(pcb["length_mm"])
    pcb_width = float(pcb["width_mm"])
    for index, (x, y) in enumerate(
        [
            (pcb_cx - pcb_length / 2.0 - 1.4, pcb_cy - pcb_width / 2.0 - 1.4),
            (pcb_cx - pcb_length / 2.0 - 1.4, pcb_cy + pcb_width / 2.0 + 1.4),
            (pcb_cx + pcb_length / 2.0 + 1.4, pcb_cy - pcb_width / 2.0 - 1.4),
            (pcb_cx + pcb_length / 2.0 + 1.4, pcb_cy + pcb_width / 2.0 + 1.4),
        ],
        start=1,
    ):
        stop = box(f"pixelblaze_corner_stop_{index}", (3.0, 3.0, 3.2), (x, y, tray_top + 1.6), 0.6)
        union(tray, stop)
    return tray


def build_connector_panel() -> bpy.types.Object:
    cfg = CONFIG["connector_panel"]
    enclosure = CONFIG["enclosure"]
    x = (
        float(enclosure["outer_length_mm"]) / 2.0
        + float(cfg["panel_thickness_mm"]) / 2.0
    )
    panel = box(
        "PRINT_blank_connector_panel",
        (float(cfg["panel_thickness_mm"]), float(cfg["panel_width_mm"]), float(cfg["panel_height_mm"])),
        (x, 0.0, float(cfg["center_z_mm"])),
        1.8,
    )
    for index, (y, z) in enumerate(
        [
            (-float(cfg["screw_y_mm"]), float(cfg["center_z_mm"]) - float(cfg["screw_z_offset_mm"])),
            (-float(cfg["screw_y_mm"]), float(cfg["center_z_mm"]) + float(cfg["screw_z_offset_mm"])),
            (float(cfg["screw_y_mm"]), float(cfg["center_z_mm"]) - float(cfg["screw_z_offset_mm"])),
            (float(cfg["screw_y_mm"]), float(cfg["center_z_mm"]) + float(cfg["screw_z_offset_mm"])),
        ],
        start=1,
    ):
        subtract_hole(panel, f"panel_clearance_{index}", float(cfg["m3_clearance_mm"]), float(cfg["panel_thickness_mm"]) + 2.0, (x, y, z), "X")
    return panel


def build_switch_bezel(lid_top: float) -> bpy.types.Object:
    cfg = CONFIG["switch"]
    cx = float(cfg["center_x_mm"])
    cy = float(cfg["center_y_mm"])
    thickness = float(cfg["bezel_thickness_mm"])
    bezel = frame(
        "PRINT_switch_bezel",
        (float(cfg["bezel_length_mm"]), float(cfg["bezel_width_mm"]), thickness),
        (float(cfg["bezel_opening_length_mm"]), float(cfg["bezel_opening_width_mm"])),
        (cx, cy, lid_top + thickness / 2.0 + 2.4),
        2.0,
    )
    for index, (x, y) in enumerate(switch_fastener_centers(), start=1):
        subtract_hole(bezel, f"bezel_clearance_{index}", float(cfg["m2_clearance_mm"]), thickness + 2.0, (x, y, lid_top + thickness / 2.0 + 2.4), vertices=32)
    return bezel


def build_tpu_membrane(lid_top: float) -> bpy.types.Object:
    cfg = CONFIG["switch"]
    cx = float(cfg["center_x_mm"])
    cy = float(cfg["center_y_mm"])
    flange_length = float(cfg["tpu_flange_length_mm"])
    flange_width = float(cfg["tpu_flange_width_mm"])
    flange_t = float(cfg["tpu_flange_thickness_mm"])
    flex_length = float(cfg["tpu_membrane_length_mm"])
    flex_width = float(cfg["tpu_membrane_width_mm"])
    membrane_t = float(cfg["tpu_membrane_thickness_mm"])
    base_z = lid_top + 0.6
    membrane = box(
        "PRINT_TPU_switch_membrane",
        (flange_length, flange_width, membrane_t),
        (cx, cy, base_z + membrane_t / 2.0),
        1.8,
    )

    rim_extra = flange_t - membrane_t + 0.1
    rim_z = base_z + membrane_t + rim_extra / 2.0 - 0.05
    side_width = (flange_length - flex_length) / 2.0
    for index, x in enumerate(
        (cx - flex_length / 2.0 - side_width / 2.0, cx + flex_length / 2.0 + side_width / 2.0),
        start=1,
    ):
        rim_bar = box(
            f"tpu_side_compression_bar_{index}",
            (side_width + 0.2, flange_width, rim_extra),
            (x, cy, rim_z),
            0.5,
        )
        union(membrane, rim_bar)
    top_width = (flange_width - flex_width) / 2.0
    for index, y in enumerate(
        (cy - flex_width / 2.0 - top_width / 2.0, cy + flex_width / 2.0 + top_width / 2.0),
        start=1,
    ):
        rim_bar = box(
            f"tpu_top_bottom_compression_bar_{index}",
            (flex_length + 0.4, top_width + 0.2, rim_extra),
            (cx, y, rim_z),
            0.5,
        )
        union(membrane, rim_bar)

    pusher_height = float(cfg["tpu_pusher_height_mm"])
    pusher = cylinder(
        "tpu_external_pusher",
        float(cfg["tpu_pusher_diameter_mm"]),
        pusher_height + 0.1,
        (cx, cy, base_z + membrane_t + pusher_height / 2.0 - 0.05),
        vertices=48,
    )
    union(membrane, pusher)
    return membrane


def build_switch_carrier(lid_bottom: float) -> bpy.types.Object:
    cfg = CONFIG["switch"]
    cx = float(cfg["center_x_mm"])
    cy = float(cfg["center_y_mm"])
    plate_t = float(cfg["carrier_plate_mm"])
    carrier = frame(
        "PRINT_switch_carrier",
        (float(cfg["carrier_length_mm"]), float(cfg["carrier_width_mm"]), plate_t),
        (float(cfg["lid_opening_length_mm"]), float(cfg["lid_opening_width_mm"])),
        (cx, cy, lid_bottom - plate_t / 2.0 - 2.4),
        1.5,
    )
    body_width = float(cfg["body_width_mm"])
    rail_height = float(cfg["carrier_rail_height_mm"])
    for index, y in enumerate((cy - body_width / 2.0 - 1.5, cy + body_width / 2.0 + 1.5), start=1):
        rail = box(
            f"switch_carrier_rail_{index}",
            (float(cfg["body_length_mm"]) + 4.0, 2.4, rail_height),
            (cx, y, lid_bottom - plate_t - rail_height / 2.0 - 2.4),
            0.8,
        )
        union(carrier, rail)
    for index, (x, y) in enumerate(switch_fastener_centers(), start=1):
        subtract_hole(carrier, f"carrier_pilot_{index}", float(cfg["m2_pilot_mm"]), plate_t + 2.0, (x, y, lid_bottom - plate_t / 2.0 - 2.4), vertices=32)
    return carrier


def build_references(tray_top: float, lid_bottom: float) -> list[bpy.types.Object]:
    pcb_cfg = CONFIG["pixelblaze_reference"]
    converter_cfg = CONFIG["converter_reference"]
    switch_cfg = CONFIG["switch"]
    references: list[bpy.types.Object] = []

    pcb = box(
        "REFERENCE_Pixelblaze_V3_Standard",
        (float(pcb_cfg["length_mm"]), float(pcb_cfg["width_mm"]), float(pcb_cfg["pcb_thickness_mm"])),
        (float(pcb_cfg["center_x_mm"]), float(pcb_cfg["center_y_mm"]), tray_top + float(pcb_cfg["pcb_thickness_mm"]) / 2.0),
        0.8,
    )
    references.append(pcb)
    antenna = box(
        "REFERENCE_Pixelblaze_antenna_keepout",
        (15.0, float(pcb_cfg["width_mm"]), float(pcb_cfg["maximum_reference_height_mm"])),
        (float(pcb_cfg["center_x_mm"]) + float(pcb_cfg["length_mm"]) / 2.0 - 7.5, float(pcb_cfg["center_y_mm"]), tray_top + float(pcb_cfg["maximum_reference_height_mm"]) / 2.0),
        1.0,
    )
    antenna.display_type = "WIRE"
    references.append(antenna)

    converter = box(
        "REFERENCE_Magnolora_converter_PROVISIONAL",
        (float(converter_cfg["length_mm"]), float(converter_cfg["width_mm"]), float(converter_cfg["height_mm"])),
        (float(converter_cfg["center_x_mm"]), float(converter_cfg["center_y_mm"]), tray_top + float(converter_cfg["height_mm"]) / 2.0),
        2.0,
    )
    references.append(converter)
    for index, sign in enumerate((-1.0, 1.0), start=1):
        wire = cylinder(
            f"REFERENCE_converter_wire_exit_{index}",
            4.0,
            float(converter_cfg["rigid_wire_exit_allowance_each_end_mm"]),
            (
                float(converter_cfg["center_x_mm"]) + sign * (float(converter_cfg["length_mm"]) / 2.0 + float(converter_cfg["rigid_wire_exit_allowance_each_end_mm"]) / 2.0),
                float(converter_cfg["center_y_mm"]),
                tray_top + float(converter_cfg["height_mm"]) / 2.0,
            ),
            "X",
            24,
        )
        references.append(wire)

    switch_body = box(
        "REFERENCE_KAN28_body",
        (float(switch_cfg["body_length_mm"]), float(switch_cfg["body_width_mm"]), float(switch_cfg["body_height_mm"])),
        (float(switch_cfg["center_x_mm"]), float(switch_cfg["center_y_mm"]), lid_bottom - float(switch_cfg["body_height_mm"]) / 2.0 - 3.0),
        1.2,
    )
    references.append(switch_body)
    button = cylinder(
        "REFERENCE_KAN28_button",
        float(switch_cfg["button_diameter_mm"]),
        float(switch_cfg["button_height_mm"]),
        (float(switch_cfg["center_x_mm"]), float(switch_cfg["center_y_mm"]), lid_bottom - 1.0),
        vertices=32,
    )
    references.append(button)
    return references


def mesh_report(obj: bpy.types.Object) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(bm.calc_volume(signed=True)) if nonmanifold == 0 else None
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": round(volume, 2) if volume is not None else None,
        "dimensions_mm": [round(float(value), 3) for value in obj.dimensions],
    }
    bm.free()
    return result


def world_bbox_min_z(obj: bpy.types.Object) -> float:
    return min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box)


def export_stl(
    obj: bpy.types.Object,
    filename: str,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(duplicate)
    duplicate.name = f"EXPORT_{obj.name}"
    duplicate.matrix_world = obj.matrix_world.copy()
    activate(duplicate)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    duplicate.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    duplicate.location.z -= world_bbox_min_z(duplicate)
    activate(duplicate)
    bpy.ops.wm.stl_export(
        filepath=str(OUTPUT_DIR / filename),
        export_selected_objects=True,
        ascii_format=False,
    )
    bpy.data.objects.remove(duplicate, do_unlink=True)


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_review(parts: list[bpy.types.Object], references: list[bpy.types.Object]) -> None:
    print_collection = collection("PRINT_PARTS")
    reference_collection = collection("REFERENCE_COMPONENTS_PROVISIONAL")
    for obj in parts:
        move_to_collection(obj, print_collection)
    for obj in references:
        move_to_collection(obj, reference_collection)

    rigid = material("PETG_Rigid_Gold", (0.55, 0.26, 0.04, 1.0))
    lid_material = material("PETG_Lid_Dark", (0.08, 0.11, 0.14, 1.0))
    tpu = material("TPU_Membrane_Cyan", (0.0, 0.55, 0.72, 1.0))
    pcb = material("Pixelblaze_PCB", (0.03, 0.28, 0.12, 1.0))
    converter = material("Converter_Provisional", (0.06, 0.07, 0.08, 1.0))
    switch = material("Switch_Reference", (0.12, 0.12, 0.13, 1.0))
    wire = material("Wire_Reference", (0.65, 0.10, 0.08, 1.0))
    for obj in parts:
        if "TPU" in obj.name:
            obj.data.materials.append(tpu)
        elif "lid" in obj.name or "bezel" in obj.name:
            obj.data.materials.append(lid_material)
        else:
            obj.data.materials.append(rigid)
    for obj in references:
        if "Pixelblaze" in obj.name:
            obj.data.materials.append(pcb)
        elif "converter_wire" in obj.name:
            obj.data.materials.append(wire)
        elif "Magnolora" in obj.name:
            obj.data.materials.append(converter)
        else:
            obj.data.materials.append(switch)

    bpy.ops.object.camera_add(location=(235.0, -270.0, 220.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 235.0
    point_at(camera, (0.0, 28.0, 36.0))
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_object_outline = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.93, 0.94, 0.95)
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1050
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT_DIR / "controller-box-v0-review.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "controller-box-v0-review.blend"))
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "controller-box-v0-review.glb"),
        export_format="GLB",
        use_selection=False,
    )


def explode_for_review(
    lid: bpy.types.Object,
    panel: bpy.types.Object,
    bezel: bpy.types.Object,
    membrane: bpy.types.Object,
    carrier: bpy.types.Object,
    references: list[bpy.types.Object],
) -> None:
    lid_group = [lid, bezel, membrane, carrier]
    lid_group.extend(obj for obj in references if "KAN28" in obj.name)
    for obj in lid_group:
        obj.location.y += 72.0
        obj.location.z += 34.0
    panel.location.x += 18.0


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_scene()
    enclosure = CONFIG["enclosure"]
    tray_cfg = CONFIG["tray"]
    lid_bottom = float(enclosure["base_height_mm"]) - float(enclosure["lid_overlap_mm"])
    lid_top = lid_bottom + float(enclosure["lid_height_mm"])
    tray_top = float(enclosure["floor_mm"]) + float(tray_cfg["support_height_mm"]) + float(tray_cfg["thickness_mm"])

    base = build_base()
    lid = build_lid()
    tray = build_tray()
    panel = build_connector_panel()
    bezel = build_switch_bezel(lid_top)
    membrane = build_tpu_membrane(lid_top)
    carrier = build_switch_carrier(lid_bottom)
    parts = [base, lid, tray, panel, bezel, membrane, carrier]
    references = build_references(tray_top, lid_bottom)

    for obj in parts:
        clean_mesh(obj)

    exports = [
        (base, "controller-box-v0-base.stl", (0.0, 0.0, 0.0)),
        (lid, "controller-box-v0-lid.stl", (math.pi, 0.0, 0.0)),
        (tray, "controller-box-v0-electronics-tray.stl", (0.0, 0.0, 0.0)),
        (panel, "controller-box-v0-blank-connector-panel.stl", (0.0, math.pi / 2.0, 0.0)),
        (bezel, "controller-box-v0-switch-bezel.stl", (0.0, 0.0, 0.0)),
        (membrane, "controller-box-v0-tpu-switch-membrane.stl", (0.0, 0.0, 0.0)),
        (carrier, "controller-box-v0-switch-carrier.stl", (math.pi, 0.0, 0.0)),
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "design_status": CONFIG["design_status"],
        "parts": {},
        "checks": {},
        "provisional_inputs": {
            "converter_dimensions": CONFIG["converter_reference"],
            "pixelblaze_height": CONFIG["pixelblaze_reference"]["maximum_reference_height_mm"],
            "connector_panel": CONFIG["connector_panel"]["status"],
        },
    }
    for obj, filename, rotation in exports:
        export_stl(obj, filename, rotation)
        report["parts"][filename] = mesh_report(obj)

    part_reports = list(report["parts"].values())
    report["checks"] = {
        "seven_printable_parts": len(exports) == 7,
        "all_parts_closed_manifold": all(item["nonmanifold_edges"] == 0 for item in part_reports),
        "all_parts_positive_volume": all(item["volume_mm3"] is not None and item["volume_mm3"] > 0 for item in part_reports),
        "converter_has_vertical_clearance": (
            float(CONFIG["converter_reference"]["height_mm"]) + tray_top
            < float(enclosure["base_height_mm"]) - 1.0
        ),
        "pixelblaze_reference_fits_tray": (
            float(CONFIG["pixelblaze_reference"]["length_mm"]) < float(tray_cfg["length_mm"])
            and float(CONFIG["pixelblaze_reference"]["width_mm"]) < float(tray_cfg["width_mm"])
        ),
        "lid_overlap_has_clearance": float(CONFIG["printer"]["fit_clearance_per_side_mm"]) >= 0.25,
        "tpu_membrane_at_least_three_layers": float(CONFIG["switch"]["tpu_membrane_thickness_mm"]) >= 3.0 * float(CONFIG["printer"]["layer_height_mm"]),
        "pro_expander_excluded": "Pixelblaze Pro Output Expander" in CONFIG["electrical_scope"]["excluded"],
    }
    report["checks"]["pass"] = all(report["checks"].values())
    (OUTPUT_DIR / "controller-box-v0-validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    explode_for_review(lid, panel, bezel, membrane, carrier, references)
    setup_review(parts, references)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
