"""Curved, keel-embedded wire guard ribs for Gate 9 V4."""

from __future__ import annotations

from typing import Any

import bpy
from mathutils import Vector


def install(builder) -> None:
    def add_wire_channel(
        keel: bpy.types.Object,
        config: dict[str, Any],
        material: bpy.types.Material,
    ) -> dict[str, Any]:
        seam = config["seam_geometry"]
        channel = config["wire_channel"]
        rear = Vector(seam["rear_edge_center_head_mm"])
        forward = Vector(
            seam["rear_edge_toward_keel_head"]
        ).normalized()
        across = Vector(seam["rear_edge_across_head"]).normalized()
        inward = Vector(
            seam["bottom_inward_normal_head"]
        ).normalized()
        start = float(channel["start_from_rear_edge_mm"])
        end = float(channel["end_from_rear_edge_mm"])
        length = end - start
        rail_diameter = float(channel["rail_width_mm"])
        embed_center = 2.5
        centerline = (
            rear
            + forward * (start + length / 2.0)
            + inward * embed_center
        )
        for index, x_value in enumerate(
            channel["rail_center_x_head_mm"], start=1
        ):
            rib = builder.oriented_cylinder(
                f"v4__keel__cylindrical_wire_rib_{index}",
                centerline + across * float(x_value),
                forward,
                rail_diameter,
                length,
                material,
            )
            builder.union(
                keel,
                rib,
                f"keel cylindrical wire rib {index}",
            )
        actual_clear = (
            abs(
                float(channel["rail_center_x_head_mm"][1])
                - float(channel["rail_center_x_head_mm"][0])
            )
            - rail_diameter
        )
        return {
            "geometry": "two cylindrical ribs embedded into the inner keel wall",
            "start_from_rear_edge_mm": start,
            "end_from_rear_edge_mm": end,
            "rib_diameter_mm": rail_diameter,
            "rib_center_inward_mm": embed_center,
            "actual_clear_width_mm": round(actual_clear, 3),
            "minimum_clear_width_mm": float(
                channel["minimum_clear_width_mm"]
            ),
            "rear_exit_gap_width_mm": float(
                channel["rear_exit_gap_width_mm"]
            ),
            "provisional_bundle_envelope_mm": channel[
                "provisional_bundle_envelope_mm"
            ],
        }

    builder.add_wire_channel = add_wire_channel
