#!/usr/bin/env python3
"""Generate an isolated, review-only flat-bottom controller-box base proposal."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
V0_ROOT = PACKAGE_ROOT.parent / "controller-box-v0"
V0_SOURCE = V0_ROOT / "source/generate_controller_box_v0.py"
V0_CONFIG = V0_ROOT / "config/controller-box-v0.json"
CONTRACT_PATH = PACKAGE_ROOT / "config/controller-box-v1-flat-base-proposal.json"
OUTPUT_DIR = PACKAGE_ROOT / "output"
TEMP_OFF = Path("/tmp/controller-box-v1-flat-base-proposal.off")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v0_module():
    spec = importlib.util.spec_from_file_location("controller_box_v0_frozen", V0_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load frozen V0 generator: {V0_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V0 = load_v0_module()
BASE_CONFIG: dict[str, Any] = json.loads(V0_CONFIG.read_text(encoding="utf-8"))
CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def verify_frozen_baseline() -> None:
    frozen = CONTRACT["frozen_v0_baseline"]
    checks = {
        "generator_sha256": sha256(V0_SOURCE),
        "config_sha256": sha256(V0_CONFIG),
        "base_stl_sha256": sha256(V0_ROOT / "output/controller-box-v0-base.stl"),
    }
    mismatches = {
        key: {"expected": frozen[key], "actual": actual}
        for key, actual in checks.items()
        if actual != frozen[key]
    }
    if mismatches:
        raise RuntimeError(f"Frozen V0 baseline mismatch: {json.dumps(mismatches, indent=2)}")


def rounded_rect_prism(
    name: str,
    length: float,
    width: float,
    height: float,
    radius: float,
    location: tuple[float, float, float],
    segments_per_corner: int = 12,
) -> bpy.types.Object:
    """Extrude an XY rounded rectangle with perfectly flat Z faces."""
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError("Rounded prism dimensions must be positive")
    if radius < 0 or radius > min(length, width) / 2.0:
        raise ValueError("Rounded prism radius is outside the valid range")

    cx, cy, cz = location
    half_x = length / 2.0
    half_y = width / 2.0
    if radius == 0.0:
        outline = [
            (cx - half_x, cy - half_y),
            (cx + half_x, cy - half_y),
            (cx + half_x, cy + half_y),
            (cx - half_x, cy + half_y),
        ]
    else:
        outline: list[tuple[float, float]] = []
        corners = [
            (cx + half_x - radius, cy + half_y - radius, 0.0),
            (cx - half_x + radius, cy + half_y - radius, 90.0),
            (cx - half_x + radius, cy - half_y + radius, 180.0),
            (cx + half_x - radius, cy - half_y + radius, 270.0),
        ]
        for corner_x, corner_y, start_degrees in corners:
            for step in range(segments_per_corner + 1):
                angle = math.radians(start_degrees + 90.0 * step / segments_per_corner)
                point = (corner_x + radius * math.cos(angle), corner_y + radius * math.sin(angle))
                if not outline or Vector(point).xy != Vector(outline[-1]).xy:
                    outline.append(point)

    z_bottom = cz - height / 2.0
    z_top = cz + height / 2.0
    vertices = [(x, y, z_bottom) for x, y in outline] + [(x, y, z_top) for x, y in outline]
    count = len(outline)
    faces: list[list[int]] = [list(reversed(range(count))), list(range(count, 2 * count))]
    for index in range(count):
        following = (index + 1) % count
        faces.append([index, following, count + following, count + index])

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def rounded_ear(name: str, center_x: float, center_y: float, cfg: dict[str, Any]) -> bpy.types.Object:
    return rounded_rect_prism(
        name,
        float(cfg["mounting_ear_length_mm"]),
        float(cfg["mounting_ear_width_mm"]),
        float(cfg["mounting_ear_thickness_mm"]),
        float(CONTRACT["approved_contract"]["mounting_ear_xy_corner_radius_mm"]),
        (center_x, center_y, float(cfg["mounting_ear_thickness_mm"]) / 2.0),
    )


def build_flat_base() -> bpy.types.Object:
    cfg = BASE_CONFIG["enclosure"]
    panel_cfg = BASE_CONFIG["connector_panel"]
    tray_cfg = BASE_CONFIG["tray"]
    length = float(cfg["outer_length_mm"])
    width = float(cfg["outer_width_mm"])
    height = float(cfg["base_height_mm"])
    wall = float(cfg["wall_mm"])
    floor = float(cfg["floor_mm"])
    radius = float(CONTRACT["approved_contract"]["base_xy_corner_radius_mm"])

    base = rounded_rect_prism(
        "PROPOSED__FlatBottomBase",
        length,
        width,
        height,
        radius,
        (0.0, 0.0, height / 2.0),
    )
    cavity = rounded_rect_prism(
        "TOOL__BaseInnerCavity",
        length - 2.0 * wall,
        width - 2.0 * wall,
        height + 2.0,
        max(radius - wall, 0.0),
        (0.0, 0.0, floor + (height + 2.0) / 2.0),
    )
    V0.boolean(base, cavity, "DIFFERENCE")

    boss_x = float(cfg["lid_screw_x_mm"])
    boss_y = float(cfg["lid_screw_y_mm"])
    for index, (x, y) in enumerate(
        [(-boss_x, -boss_y), (-boss_x, boss_y), (boss_x, -boss_y), (boss_x, boss_y)],
        start=1,
    ):
        V0.add_boss(base, f"lid_boss_{index}", 9.0, height - floor - 1.5, (x, y, floor + (height - floor - 1.5) / 2.0))
        V0.subtract_hole(base, f"lid_insert_pilot_{index}", float(cfg["m3_insert_pilot_mm"]), 7.0, (x, y, height - 4.5))

    ear_x = float(cfg["mounting_ear_x_mm"])
    ear_y = float(cfg["mounting_ear_y_mm"])
    ear_thickness = float(cfg["mounting_ear_thickness_mm"])
    for index, (x, y) in enumerate(
        [(-ear_x, -ear_y), (-ear_x, ear_y), (ear_x, -ear_y), (ear_x, ear_y)],
        start=1,
    ):
        V0.union(base, rounded_ear(f"mounting_ear_{index}", x, y, cfg))
        slot = V0.capsule_tool(
            f"mounting_slot_{index}",
            float(cfg["mounting_slot_length_mm"]),
            float(cfg["mounting_slot_width_mm"]),
            ear_thickness + 2.0,
            (x, y, ear_thickness / 2.0),
        )
        V0.boolean(base, slot, "DIFFERENCE")

    panel_center_z = float(panel_cfg["center_z_mm"])
    V0.subtract_box(
        base,
        "connector_panel_opening",
        (wall + 6.0, float(panel_cfg["opening_width_mm"]), float(panel_cfg["opening_height_mm"])),
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
        V0.subtract_hole(base, f"panel_clearance_{index}", float(panel_cfg["m3_clearance_mm"]), wall + 2.0, (length / 2.0, y, z), "X")

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
        V0.add_boss(base, f"tray_support_{index}", 8.0, support_height, (x, y, support_z))
        V0.subtract_hole(base, f"tray_pilot_{index}", float(tray_cfg["m3_pilot_mm"]), support_height + 2.0, (x, y, support_z))
    return base


def bottom_contact_area(obj: bpy.types.Object, tolerance: float = 0.0001) -> float:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    area = sum(
        face.calc_area()
        for face in bm.faces
        if all(abs(vertex.co.z) <= tolerance for vertex in face.verts) and face.normal.z < -0.9
    )
    bm.free()
    return float(area)


def bbox(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "minimum_mm": [round(min(point[index] for point in points), 6) for index in range(3)],
        "maximum_mm": [round(max(point[index] for point in points), 6) for index in range(3)],
    }


def export_off(obj: bpy.types.Object, path: Path) -> None:
    """Write a connectivity-preserving, non-print-release mesh for FreeCAD."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    lines = ["OFF", f"{len(bm.verts)} {len(bm.faces)} 0"]
    lines.extend(f"{vertex.co.x:.9f} {vertex.co.y:.9f} {vertex.co.z:.9f}" for vertex in bm.verts)
    lines.extend(
        "3 " + " ".join(str(vertex.index) for vertex in face.verts)
        for face in bm.faces
    )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    bm.free()


def configure_review(base: bpy.types.Object) -> None:
    proposal_collection = V0.collection("PROPOSED__FLAT_BASE")
    V0.move_to_collection(base, proposal_collection)
    base.data.materials.append(V0.material("Proposal_ASA_Orange", (0.72, 0.23, 0.04, 1.0)))

    bed = V0.box("REVIEW_ONLY__BedDatum_Z0", (150.0, 134.0, 0.4), (0.0, 0.0, -0.2))
    bed.data.materials.append(V0.material("Bed_Datum_Blue", (0.05, 0.22, 0.62, 0.25)))
    V0.move_to_collection(bed, V0.collection("REVIEW_EVIDENCE__NOT_PRINTABLE"))

    bpy.ops.object.camera_add(location=(205.0, -235.0, 175.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 190.0
    V0.point_at(camera, (0.0, 0.0, 19.0))
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
    scene.render.filepath = str(OUTPUT_DIR / "controller-box-v1-flat-base-proposal-isometric.png")
    bpy.ops.render.render(write_still=True)

    camera.location = (0.0, 0.0, -210.0)
    V0.point_at(camera, (0.0, 0.0, 0.0))
    camera.data.ortho_scale = 155.0
    scene.render.filepath = str(OUTPUT_DIR / "controller-box-v1-flat-base-proposal-bottom.png")
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "controller-box-v1-flat-base-proposal.blend"))
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "controller-box-v1-flat-base-proposal.glb"),
        export_format="GLB",
        use_selection=False,
    )

    bed.hide_render = True
    bed.hide_viewport = True
    export_off(base, TEMP_OFF)


def main() -> None:
    verify_frozen_baseline()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    V0.clean_scene()
    base = build_flat_base()
    V0.clean_mesh(base)

    mesh = V0.mesh_report(base)
    bounds = bbox(base)
    contact_area = bottom_contact_area(base)
    gates = CONTRACT["validation_gates"]
    bbox_tol = float(gates["bbox_tolerance_mm"])
    z_tol = float(gates["bed_datum_tolerance_mm"])
    checks = {
        "closed_manifold": mesh["nonmanifold_edges"] == 0,
        "positive_volume": mesh["volume_mm3"] is not None and mesh["volume_mm3"] > 0,
        "bed_datum_z0": abs(bounds["minimum_mm"][2]) <= z_tol,
        "preserved_bbox": all(
            abs(actual - expected) <= bbox_tol
            for actual, expected in zip(
                bounds["minimum_mm"] + bounds["maximum_mm"],
                [-66.0, -58.0, 0.0, 66.0, 58.0, 42.0],
            )
        ),
        "bottom_contact_area": contact_area >= float(gates["minimum_bottom_contact_area_mm2"]),
        "no_bottom_edge_radius": float(CONTRACT["approved_contract"]["bed_edge_radius_mm"]) == 0.0,
    }
    checks["pass"] = all(checks.values())
    report = {
        "schema_version": 1,
        "design_status": CONTRACT["design_status"],
        "source": "generate_controller_box_v1_flat_base_proposal.py",
        "temporary_freecad_import_off": str(TEMP_OFF),
        "approved_contract": CONTRACT["approved_contract"],
        "frozen_v0_baseline": CONTRACT["frozen_v0_baseline"],
        "mesh": mesh,
        "bounding_box": bounds,
        "bottom_contact_area_mm2": round(contact_area, 3),
        "checks": checks,
        "exports": {
            "printable_stl": False,
            "gcode": False,
            "review_blend": True,
            "review_glb": True,
            "review_png": True
        }
    }
    (OUTPUT_DIR / "controller-box-v1-flat-base-proposal-validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if not checks["pass"]:
        raise RuntimeError(f"Proposal validation failed: {json.dumps(checks, indent=2)}")
    configure_review(base)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
