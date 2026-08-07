#!/usr/bin/env python3
"""Audit immediate world-space escape directions for the accepted V3 body."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as c002_v2  # noqa: E402
import generate_ear_root_insertion_fit_review_v3 as ear_v3  # noqa: E402
import generate_ear_root_restored_coverage_review_v2 as ear_v2  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/ear-root-insertion-fit-review-v3.json"


def directions() -> list[Vector]:
    values: list[Vector] = []
    for polar_degrees in range(0, 181, 15):
        polar = math.radians(polar_degrees)
        azimuths = (0,) if polar_degrees in (0, 180) else range(0, 360, 15)
        for azimuth_degrees in azimuths:
            azimuth = math.radians(azimuth_degrees)
            values.append(
                Vector(
                    (
                        math.sin(polar) * math.cos(azimuth),
                        math.sin(polar) * math.sin(azimuth),
                        math.cos(polar),
                    )
                )
            )
    return values


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payloads, _, _ = ear_v3.generate_source_payloads(
        config, ear_v3.repo_path(config["source_gate6_blend"])
    )
    bpy.ops.wm.open_mainfile(
        filepath=str(ear_v3.repo_path(config["source_gate8_blend"]))
    )
    body = ear_v2.deserialize_mesh("ESCAPE_AUDIT__right_body", payloads["full"])
    bpy.context.scene.collection.objects.link(body)
    ear_v3.apply_exact_ear_clearance(
        body,
        bpy.data.objects["right_ear"],
        float(config["fit_clearance"]["exact_ear_local_clearance_mm"]),
    )
    structural_targets = [
        c002_v2.require_object(name)
        for name in gate2.SECTION_ORDER
        if name != "right_ear"
    ]
    initial_distances = (0.5, 1.0, 2.0, 3.0, 5.0)
    full_distances = tuple(float(value) for value in range(1, 61))
    records = []
    for direction in directions():
        counts = []
        clear = True
        for distance in initial_distances:
            body.matrix_world = Matrix.Translation(direction * distance)
            hits = ear_v3.collision_hits(body, structural_targets)
            count = sum(hits.values())
            counts.append(count)
            if count:
                clear = False
                break
        body.matrix_world = Matrix.Identity(4)
        records.append(
            {
                "direction": [round(float(value), 6) for value in direction],
                "initial_counts": counts,
                "initial_clear": clear,
                "initial_clear_distance_mm": (
                    initial_distances[len(counts) - 1]
                    if clear
                    else initial_distances[max(0, len(counts) - 2)]
                ),
                "score": sum(counts),
            }
        )
    initial_clear = [record for record in records if record["initial_clear"]]
    full_clear = []
    for record in initial_clear:
        direction = Vector(record["direction"])
        maximum = 0
        first_conflict = None
        for distance in full_distances:
            body.matrix_world = Matrix.Translation(direction * distance)
            hits = ear_v3.collision_hits(body, structural_targets)
            maximum = max(maximum, sum(hits.values()))
            if hits:
                first_conflict = {"distance_mm": distance, "hits": hits}
                break
        body.matrix_world = Matrix.Identity(4)
        record["full_first_conflict"] = first_conflict
        record["full_maximum_intersection_pairs"] = maximum
        if first_conflict is None:
            full_clear.append(record)
    ranked = sorted(
        records,
        key=lambda record: (
            not record["initial_clear"],
            record["score"],
            -record["initial_clear_distance_mm"],
        ),
    )
    report = {
        "direction_count": len(records),
        "initial_distances_mm": initial_distances,
        "initial_clear_direction_count": len(initial_clear),
        "full_clear_to_60mm_direction_count": len(full_clear),
        "full_clear_directions": full_clear,
        "best_twenty": ranked[:20],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
