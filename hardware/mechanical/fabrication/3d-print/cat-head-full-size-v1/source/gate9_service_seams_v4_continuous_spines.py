"""Continuous one-piece gasket and insert spines for Gate 9 V4."""

from __future__ import annotations

from typing import Any

import bpy
from mathutils import Vector


def install(builder) -> None:
    def stepped_spine(
        name,
        center,
        along,
        toward_owner,
        inward,
        length,
        root_width,
        tongue_width,
        config,
        material,
    ):
        """Extrude one stepped cross-section with no internal Booleans."""
        seal = config["seal_system"]
        fasteners = config["fastener_system"]
        root_bottom = float(seal["root_bottom_inward_mm"])
        lip_bottom = (
            float(config["seam_geometry"]["wall_thickness_mm"])
            + float(seal["seated_gap_mm"])
        )
        top = max(
            float(fasteners["lower_pad"]["top_inward_mm"]),
            float(fasteners["rear_pad"]["top_inward_mm"]),
        )
        owner_overlap = 2.5
        keel_extent = tongue_width - owner_overlap
        cross_section = (
            (0.0, root_bottom),
            (root_width, root_bottom),
            (root_width, top),
            (-keel_extent, top),
            (-keel_extent, lip_bottom),
            (0.0, lip_bottom),
        )
        along = along.normalized()
        toward_owner = toward_owner.normalized()
        inward = inward.normalized()
        half = length / 2.0
        vertices = []
        for along_offset in (-half, half):
            for owner_offset, inward_offset in cross_section:
                vertices.append(
                    center
                    + along * along_offset
                    + toward_owner * owner_offset
                    + inward * inward_offset
                )
        count = len(cross_section)
        faces = [
            tuple(reversed(range(count))),
            tuple(range(count, count * 2)),
        ]
        for index in range(count):
            following = (index + 1) % count
            faces.append(
                (
                    index,
                    following,
                    count + following,
                    count + index,
                )
            )
        mesh = bpy.data.meshes.new(name + "__mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material)
        builder.gate5.require_manifold(obj, name + " raw stepped spine")
        if len(builder.gate5.components(obj)) != 1:
            raise ValueError(f"{name}: raw spine is not one component")
        return obj, lip_bottom, top

    def pocket_spine(
        spine,
        name,
        bolt_center,
        inward,
        lip_bottom,
        config,
        cutter_material,
    ):
        fasteners = config["fastener_system"]
        diameter = float(
            fasteners["heat_set_insert_pocket_diameter_mm"]
        )
        depth = float(
            fasteners["heat_set_insert_pocket_depth_mm"]
        )
        cutter = builder.oriented_cylinder(
            name,
            bolt_center + inward * (lip_bottom + depth / 2.0),
            inward,
            diameter,
            depth + 0.2,
            cutter_material,
        )
        builder.gate5.apply_boolean(
            spine, cutter, "DIFFERENCE", solver="EXACT"
        )
        builder.gate5.require_manifold(spine, name + " cut")
        if len(builder.gate5.components(spine)) != 1:
            raise ValueError(f"{name}: cut split the spine")
        return diameter, depth

    def add_lower(
        part: str,
        owner: bpy.types.Object,
        keel: bpy.types.Object,
        config: dict[str, Any],
        material: bpy.types.Material,
        cutter_material: bpy.types.Material,
    ) -> list[dict[str, Any]]:
        seam = config["seam_geometry"]["lower_seams"][part]
        start = Vector(seam["start_head_mm"])
        end = Vector(seam["end_head_mm"])
        along = (end - start).normalized()
        toward_owner = Vector(seam["toward_owner_head"]).normalized()
        inward = Vector(
            config["seam_geometry"]["bottom_inward_normal_head"]
        ).normalized()
        seal = config["seal_system"]
        fasteners = config["fastener_system"]
        values = fasteners["lower_pad"]
        front = float(seal["lower_front_drainage_break_mm"])
        rear = float(seal["lower_rear_corner_break_mm"])
        length = (end - start).length - front - rear
        center = start + along * (front + length / 2.0)
        spine, lip_bottom, _ = stepped_spine(
            f"v4__{part}__continuous_service_spine",
            center,
            along,
            toward_owner,
            inward,
            length,
            float(values["root_width_owner_side_mm"]),
            float(values["tongue_width_keel_side_mm"]),
            config,
            material,
        )
        records = []
        pending_holes = []
        for index, (fraction, hole_type) in enumerate(
            zip(
                values["fractions_along_seam"],
                fasteners["lower_hole_types"][part],
            ),
            start=1,
        ):
            seam_point = start + (end - start) * float(fraction)
            bolt_center = (
                seam_point
                - toward_owner
                * float(values["bolt_center_into_keel_mm"])
            )
            diameter, depth = pocket_spine(
                spine,
                f"v4__{part}__insert_pocket_{index}",
                bolt_center,
                inward,
                lip_bottom,
                config,
                cutter_material,
            )
            pending_holes.append((index, hole_type, bolt_center))
            records.append(
                {
                    "owner": part,
                    "index": index,
                    "fraction_along_seam": float(fraction),
                    "hole_type": hole_type,
                    "bolt_center_head_mm": [
                        round(value, 4) for value in bolt_center
                    ],
                    "insert_pocket_diameter_mm": diameter,
                    "insert_pocket_depth_mm": depth,
                    "continuous_service_spine": True,
                }
            )
        builder.union(
            owner, spine, f"{part} continuous service-spine union"
        )
        wall = float(config["seam_geometry"]["wall_thickness_mm"])
        for index, hole_type, bolt_center in pending_holes:
            cutter = builder.make_hole_cutter(
                f"v4__keel__{part}__hole_{index}",
                hole_type,
                bolt_center + inward * wall / 2.0,
                along,
                toward_owner,
                inward,
                config,
                cutter_material,
            )
            builder.difference(
                keel,
                cutter,
                f"keel {part} fastener hole {index}",
                "MANIFOLD",
            )
        return records

    def add_rear(
        cassette: bpy.types.Object,
        keel: bpy.types.Object,
        config: dict[str, Any],
        material: bpy.types.Material,
        cutter_material: bpy.types.Material,
    ) -> list[dict[str, Any]]:
        seam = config["seam_geometry"]
        seal = config["seal_system"]
        fasteners = config["fastener_system"]
        values = fasteners["rear_pad"]
        center = Vector(seam["rear_edge_center_head_mm"])
        across = Vector(seam["rear_edge_across_head"]).normalized()
        toward_keel = Vector(
            seam["rear_edge_toward_keel_head"]
        ).normalized()
        toward_owner = -toward_keel
        inward = Vector(seam["bottom_inward_normal_head"]).normalized()
        half_span = float(seal["rear_span_half_width_mm"])
        exit_half = float(seal["rear_wire_exit_half_width_mm"])
        records = []
        pending_holes = []
        for index, (side, low, high, x_value, hole_type) in enumerate(
            (
                (
                    "left",
                    -half_span,
                    -exit_half,
                    float(values["x_head_mm"][0]),
                    fasteners["rear_hole_types"][0],
                ),
                (
                    "right",
                    exit_half,
                    half_span,
                    float(values["x_head_mm"][1]),
                    fasteners["rear_hole_types"][1],
                ),
            ),
            start=1,
        ):
            spine, lip_bottom, _ = stepped_spine(
                f"v4__cassette__continuous_service_spine_{side}",
                center + across * ((low + high) / 2.0),
                across,
                toward_owner,
                inward,
                high - low,
                float(values["root_width_cassette_side_mm"]),
                float(values["tongue_width_keel_side_mm"]),
                config,
                material,
            )
            seam_point = center + across * x_value
            bolt_center = (
                seam_point
                - toward_owner
                * float(values["bolt_center_into_keel_mm"])
            )
            diameter, depth = pocket_spine(
                spine,
                f"v4__cassette__insert_pocket_{index}",
                bolt_center,
                inward,
                lip_bottom,
                config,
                cutter_material,
            )
            builder.union(
                cassette,
                spine,
                f"cassette continuous service-spine union {side}",
            )
            pending_holes.append((index, hole_type, bolt_center))
            records.append(
                {
                    "owner": "rear_cassette",
                    "index": index,
                    "x_head_mm": x_value,
                    "hole_type": hole_type,
                    "bolt_center_head_mm": [
                        round(value, 4) for value in bolt_center
                    ],
                    "insert_pocket_diameter_mm": diameter,
                    "insert_pocket_depth_mm": depth,
                    "continuous_service_spine": True,
                }
            )
        wall = float(seam["wall_thickness_mm"])
        for index, hole_type, bolt_center in pending_holes:
            cutter = builder.make_hole_cutter(
                f"v4__keel__cassette_hole_{index}",
                hole_type,
                bolt_center + inward * wall / 2.0,
                across,
                toward_keel,
                inward,
                config,
                cutter_material,
            )
            builder.difference(
                keel,
                cutter,
                f"keel cassette fastener hole {index}",
                "MANIFOLD",
            )
        return records

    builder.add_lower_seal_and_pads = add_lower
    builder.add_rear_seal_and_pads = add_rear
