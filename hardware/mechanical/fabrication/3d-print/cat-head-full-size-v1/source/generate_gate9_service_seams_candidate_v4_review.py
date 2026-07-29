#!/usr/bin/env python3
"""Generate the Gate 9 V4 service-seam review candidate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate9_service_seams_candidate_v4 as builder  # noqa: E402
import gate9_service_seams_v4_continuous_spines as spines  # noqa: E402
import gate9_service_seams_v4_wire_ribs as wire_ribs  # noqa: E402


original_expanded_cutter = builder.v3.expanded_cutter
original_components = builder.gate5.components


def controlled_expanded_cutter(source, name, expansion_mm):
    """Relieve the shared keel edge without subtracting a complete shell."""
    if "_keel_clearance" not in name:
        return original_expanded_cutter(source, name, expansion_mm)
    config = json.loads(
        builder.requested_config_path().read_text(encoding="utf-8")
    )
    part = next(
        candidate
        for candidate in builder.LOWER_PARTS
        if candidate in name
    )
    seam = config["seam_geometry"]["lower_seams"][part]
    start = Vector(seam["start_head_mm"])
    end = Vector(seam["end_head_mm"])
    along = (end - start).normalized()
    toward_owner = Vector(seam["toward_owner_head"]).normalized()
    inward = Vector(
        config["seam_geometry"]["bottom_inward_normal_head"]
    ).normalized()
    width = float(expansion_mm) + 0.3
    depth = (
        float(config["seam_geometry"]["wall_thickness_mm"]) + 2.0
    )
    material = builder.comparison.create_material(
        f"{name}__material", "#D74949", alpha=0.3
    )
    return builder.oriented_box(
        name,
        (start + end) / 2.0
        - toward_owner * (width / 2.0 - 0.1)
        + inward
        * float(config["seam_geometry"]["wall_thickness_mm"])
        / 2.0,
        (along, toward_owner, inward),
        ((end - start).length + 4.0, width, depth),
        material,
    )


def validated_union(owner, feature, operation):
    use_manifold = operation.startswith(
        ("cassette continuous", "keel cylindrical wire rib")
    )
    builder.gate5.apply_boolean(
        owner,
        feature,
        "UNION",
        solver="MANIFOLD" if use_manifold else "EXACT",
    )
    builder.gate5.require_manifold(owner, operation)
    if len(original_components(owner)) != 1:
        raise ValueError(f"{operation}: union split {owner.name}")


def validated_difference(owner, cutter, operation, solver):
    cleanup_operation = operation.startswith(
        ("keel clearance from ", "cassette clearance from ")
    )
    selected_solver = (
        solver
        if cleanup_operation
        or "fastener hole" in operation
        or operation.startswith("keel drain")
        else "EXACT"
    )
    builder.gate5.apply_boolean(
        owner, cutter, "DIFFERENCE", solver=selected_solver
    )
    builder.gate5.require_manifold(owner, operation)
    cleanup = builder.gate5.keep_largest_component(owner)
    removed = float(cleanup["removed_component_volume_mm3"])
    limit = (
        350.0
        if operation.startswith("keel clearance from ")
        else 5.0
        if operation.startswith("cassette clearance from ")
        else 0.01
    )
    if removed > limit:
        raise ValueError(
            f"{operation}: discarded {removed:.3f} mm3 exceeds "
            f"the {limit:.3f} mm3 bound"
        )
    builder.gate5.require_manifold(owner, operation + " cleanup")
    if len(original_components(owner)) != 1:
        raise ValueError(f"{operation}: cleanup did not restore one part")
    owner["v4_last_cleanup_mm3"] = removed


builder.v3.expanded_cutter = controlled_expanded_cutter
builder.union = validated_union
builder.difference = validated_difference
builder.mesh_volume = builder.gate5.mesh_volume
spines.install(builder)
wire_ribs.install(builder)
builder.main()
