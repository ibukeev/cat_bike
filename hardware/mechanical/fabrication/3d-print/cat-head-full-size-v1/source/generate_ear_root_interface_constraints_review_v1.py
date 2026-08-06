#!/usr/bin/env python3
"""Generate a read-only isolated review of both ear-root interfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as v2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/ear-root-interface-constraints-review-v1.json"
DEFAULT_OUTPUT = (
    PACKAGE_ROOT
    / "output/60-ear-root-reviews/ear-root-interface-constraints-review-v1"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def configure_scene(
    output_dir: Path, resolution_px: int
) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Ear_Root_Interface_Constraints_Review_V1"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("EAR1_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR1_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = "SOLID"
            space.shading.color_type = "OBJECT"
            space.region_3d.view_perspective = "CAMERA"
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_view(
    camera: bpy.types.Object,
    output_dir: Path,
    name: str,
    location: Vector,
    target: Vector,
    visible: set[bpy.types.Object],
) -> str:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    camera.location = location
    point_at(camera, target)
    path = output_dir / "renders" / f"ear-root-interface-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def require_single_ear_record(
    manifest: dict[str, Any], joint_pair: str
) -> dict[str, Any]:
    matches = [
        record
        for record in manifest["flange_tab_manifest"]
        if record["name"].startswith(
            f"internal_flange_tab_{joint_pair}_"
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one integrated saddle record for {joint_pair}, "
            f"found {len(matches)}"
        )
    return matches[0]


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_gate8_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(f"Open the configured Gate 8 blend: {source_blend}")
    interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    gate8_report = json.loads(
        repo_path(config["gate8_validation"]).read_text(encoding="utf-8")
    )
    stage5_report = json.loads(
        repo_path(config["stage5_validation"]).read_text(encoding="utf-8")
    )
    gate7_config = json.loads(
        repo_path(config["gate7_insert_config"]).read_text(encoding="utf-8")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    collection_names = (
        "EAR1_EXACT_EARS_CYAN",
        "EAR1_EXACT_UPPER_HEADS_GRAY",
        "EAR1_CURRENT_REJECTED_RELIEF_INSERTS_PURPLE",
        "EAR1_OTHER_SOURCE_GEOMETRY_HIDDEN",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    core_objects: set[bpy.types.Object] = set()
    side_visible: dict[str, set[bpy.types.Object]] = {}
    insert_objects: set[bpy.types.Object] = set()
    saddle_records = []
    side_records = []
    for side, names in config["sides"].items():
        ear = v2.require_object(names["ear"])
        upper = v2.require_object(names["upper_head"])
        insert = v2.require_object(names["insert"])
        ear.color = v2.hex_color(config["display"]["ear_color"])
        upper.color = v2.hex_color(config["display"]["upper_head_color"])
        insert.color = v2.hex_color(config["display"]["insert_color"])
        ear.show_wire = True
        upper.show_wire = True
        insert.show_in_front = True
        for obj in (ear, upper, insert):
            obj.hide_viewport = False
            obj.hide_render = False
            obj.hide_set(False)
        v2.link_reference(ear, collections["EAR1_EXACT_EARS_CYAN"])
        v2.link_reference(
            upper, collections["EAR1_EXACT_UPPER_HEADS_GRAY"]
        )
        v2.link_reference(
            insert,
            collections[
                "EAR1_CURRENT_REJECTED_RELIEF_INSERTS_PURPLE"
            ],
        )
        saddle = require_single_ear_record(
            stage5_report, names["joint_pair"]
        )
        if saddle["internal_m3_screws"] != 4:
            raise ValueError(f"{side} ear saddle no longer has four M3 paths")
        if saddle["alignment_dowels"] != 0:
            raise ValueError(f"{side} ear saddle unexpectedly has dowels")
        if saddle["exterior_fastener_holes"] != 0:
            raise ValueError(
                f"{side} ear saddle unexpectedly has exterior holes"
            )
        saddle_records.append(saddle)
        side_set = {ear, upper, insert}
        side_visible[side] = side_set
        core_objects |= side_set
        insert_objects.add(insert)
        side_records.append(
            {
                "side": side,
                "ear": ear.name,
                "upper_head": upper.name,
                "insert": insert.name,
                "joint_pair": names["joint_pair"],
                "saddle_name": saddle["name"],
                "saddle_module_length_mm": saddle["module_length_mm"],
                "saddle_tab_depth_mm": saddle["flange_tab_depth_mm"],
                "saddle_tab_thickness_mm": saddle[
                    "flange_tab_thickness_mm"
                ],
                "saddle_face_clearance_mm": saddle[
                    "flange_face_clearance_mm"
                ],
                "internal_m3_screws": saddle["internal_m3_screws"],
                "alignment_dowels": saddle["alignment_dowels"],
                "exterior_fastener_holes": saddle[
                    "exterior_fastener_holes"
                ],
                "minimum_tab_exterior_recess_mm": saddle[
                    "minimum_tab_exterior_recess_mm"
                ],
                "minimum_root_web_exterior_recess_mm": saddle[
                    "minimum_root_web_exterior_recess_mm"
                ],
                "root_web_count_per_tab": saddle[
                    "flange_root_web_count_per_tab"
                ],
                "root_web_length_mm": saddle[
                    "flange_root_web_length_mm"
                ],
                "root_web_thickness_mm": saddle[
                    "flange_root_web_thickness_mm"
                ],
                "continuous_solid_root_base": saddle[
                    "flange_root_is_continuous_solid_base"
                ],
                "insert_topology": {
                    "boundary_edges": gate5.topology_counts(insert)[0],
                    "nonmanifold_edges": gate5.topology_counts(insert)[1],
                },
            }
        )

    artifact_tokens = tuple(
        value.lower() for value in config["artifact_name_tokens"]
    )
    named_artifact_meshes = sorted(
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj not in core_objects
        and any(token in obj.name.lower() for token in artifact_tokens)
    )
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj not in core_objects:
            v2.link_reference(
                obj, collections["EAR1_OTHER_SOURCE_GEOMETRY_HIDDEN"]
            )
            obj.hide_viewport = True
            obj.hide_render = True
            obj.hide_set(True)

    all_visible = side_visible["left"] | side_visible["right"]
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in all_visible
            obj.hide_render = True

    camera = configure_scene(
        output_dir, int(config["display"]["render_resolution_px"])
    )
    renders = [
        render_view(
            camera,
            output_dir,
            "both-interior",
            Vector((0.0, 430.0, 270.0)),
            Vector((0.0, 166.0, 222.0)),
            all_visible,
        ),
        render_view(
            camera,
            output_dir,
            "left-interior",
            Vector((-285.0, 365.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-interior",
            Vector((285.0, 365.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-exterior",
            Vector((-285.0, -100.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-exterior",
            Vector((285.0, -100.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "current-inserts-only",
            Vector((0.0, 430.0, 250.0)),
            Vector((0.0, 168.0, 214.0)),
            insert_objects,
        ),
    ]

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in all_visible
            obj.hide_render = obj not in all_visible
    camera.location = Vector((0.0, 430.0, 270.0))
    point_at(camera, Vector((0.0, 166.0, 222.0)))

    protected_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_before
    }
    if protected_before != protected_after:
        raise ValueError("Read-only constraints review changed source geometry")
    base_relief = gate7_config["ear_root_interfaces"]
    effective_relief = config["gate8_effective_insert_relief"]
    if effective_relief["connector_corner_relief_depth_mm"] <= base_relief[
        "connector_corner_relief_depth_mm"
    ]:
        raise ValueError("Expected Gate 8 to enlarge ear-root corner relief")
    if effective_relief["connector_side_tip_setback_mm"] <= base_relief[
        "connector_side_tip_setback_mm"
    ]:
        raise ValueError("Expected Gate 8 to enlarge ear-root side setback")

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["geometry_changed"] = False
    scene["ear_saddle_count"] = len(saddle_records)
    scene["ear_saddle_m3_paths_per_side"] = 4
    scene["alignment_dowel_count"] = 0
    scene["named_round_stick_artifact_count"] = len(
        named_artifact_meshes
    )
    scene["gate8_corner_relief_depth_mm"] = effective_relief[
        "connector_corner_relief_depth_mm"
    ]
    scene["gate8_side_tip_setback_mm"] = effective_relief[
        "connector_side_tip_setback_mm"
    ]
    blend_path = output_dir / "ear-root-interface-constraints-review-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_gate8_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "geometry_changed": False,
        "side_records": side_records,
        "ear_saddle_count": len(saddle_records),
        "one_integrated_four_m3_saddle_per_side": (
            len(saddle_records) == 2
            and all(record["internal_m3_screws"] == 4 for record in saddle_records)
        ),
        "alignment_dowel_count": sum(
            record["alignment_dowels"] for record in saddle_records
        ),
        "exterior_fastener_hole_count": sum(
            record["exterior_fastener_holes"]
            for record in saddle_records
        ),
        "named_round_stick_or_dowel_artifact_meshes": named_artifact_meshes,
        "round_sticks_are_not_production_ear_geometry": (
            not named_artifact_meshes
            and all(record["alignment_dowels"] == 0 for record in saddle_records)
        ),
        "gate7_base_insert_relief": {
            "connector_clearance_mm": base_relief[
                "connector_clearance_mm"
            ],
            "connector_corner_relief_depth_mm": base_relief[
                "connector_corner_relief_depth_mm"
            ],
            "connector_side_tip_setback_mm": base_relief[
                "connector_side_tip_setback_mm"
            ],
        },
        "gate8_effective_insert_relief": effective_relief,
        "gate8_relief_is_larger_than_gate7_base": True,
        "current_insert_variant_rejected_for_missing_coverage": True,
        "preserved_source_mesh_count": len(protected_before),
        "preserved_source_mesh_geometry_unchanged": (
            protected_before == protected_after
        ),
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = (
        output_dir
        / "ear-root-interface-constraints-review-v1-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
