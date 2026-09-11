#!/usr/bin/env python3
"""Timed, read-only validator revision for the held V6 attempt-002 candidate.

This module is additive.  It loads the byte-identical timed-out validator and
reuses its design-control checks, reference construction, metadata checks, and
exact G01-G12 evaluator.  Only execution of collision/clearance measurement is
revised:

* collision-only checks use cached immutable obstacle AABBs;
* AABB-disjoint pairs return zero collision without ``distToShape()``;
* AABB-overlapping pairs calculate exact OCCT common volume and no distance;
* clearance-only checks retain exact ``distToShape()`` measurements; and
* named stages, elapsed times, counters, and progress events are emitted.

Performance-preflight mode opens the exact held candidate read-only and may
write only timing/counter JSON below ``reports/generated/cat-head-cad-tooling``.
It never publishes a G01-G12 verdict.  Production mode additionally requires a
fresh, externally hash-pinned authorization record and refuses to overwrite its
one fresh validation output.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import hashlib
import importlib.util
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence


ORIGINAL_VALIDATOR_FILENAME = (
    "validate_right_eye_serviceable_fit_previsual_v6_attempt_002.py"
)
ORIGINAL_VALIDATOR_SHA256 = (
    "1d21d0815601bdcea7806a8215229a40bc2cb4190d93fcdcf7ab53b45f295ec9"
)
ORIGINAL_CONTRACT_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/"
    "right-eye-serviceable-fit-prototype-v6-attempt-002.json"
)
ORIGINAL_CONTRACT_SHA256 = (
    "90733fd0ec3cd1b56a1722c51dc087fcbcd877e525bdba65cbeceadc0cc69801"
)
BASELINE_MANIFEST_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/approved-baseline-v34.json"
)
BASELINE_MANIFEST_SHA256 = (
    "a4144cc60dd38a9b42768e167b85c54d2ce21a875d3915fe5fa95f3e2c434824"
)
HELD_CANDIDATE_RELATIVE = (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-serviceable-fit-prototype-v6-attempt-002/candidate.FCStd"
)
HELD_CANDIDATE_SHA256 = (
    "6cbe4e33419ff631d71d0932b157e2162bc4d8a79387c80ea66fa9ed4a62fcf9"
)
PRESERVATION_REPORT_RELATIVE = (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-serviceable-fit-prototype-v6-attempt-002/"
    "preservation-report.json"
)
PRESERVATION_REPORT_SHA256 = (
    "37c6e63c5183286d2eccd4ae26c418e1f72d5858e6ead569bef22f51875fa91b"
)
RUNTIME_MANIFEST_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/"
    "freecad-runtime-1.1.3-r20260725-occt-7.8.1.json"
)
RUNTIME_MANIFEST_SHA256 = (
    "0051cd65fc00f3270aadecd992ad7f571a327646054399e9ee17f39ae48c4bf1"
)
VALIDATOR_ID = (
    "independent-right-eye-serviceable-fit-previsual-v6-attempt-002-"
    "validator-revision-001"
)
VALIDATOR_REVISION = 1
PRODUCTION_TIMEOUT_SECONDS = 300.0
PERFORMANCE_TARGET_SECONDS = 180.0
REQUIRED_EYE_SAMPLES = 41
REQUIRED_REAR_CAP_SAMPLES = 31


def _load_original_validator() -> Any:
    path = Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
    name = "_cat_head_immutable_v6_attempt_002_validator"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load immutable validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


original = _load_original_validator()

# These aliases are intentionally the original function objects.  Synthetic
# regressions assert identity, not merely equivalent copied expressions.
evaluate_previsual_observations = original.evaluate_previsual_observations
preflight_design_control = original.preflight_design_control
preflight_independent_root_projection = (
    original.preflight_independent_root_projection
)
preflight_independent_signed_mount_frames = (
    original.preflight_independent_signed_mount_frames
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_event(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True), file=sys.stderr, flush=True)


class RunDiagnostics:
    """Collect bounded workload evidence and emit stage-aware progress."""

    def __init__(self, *, emit_progress: bool = True) -> None:
        self.started = time.monotonic()
        self.emit_progress = emit_progress
        self.current_stage = "startup"
        self.current_stage_started = self.started
        self.stage_timings: dict[str, dict[str, Any]] = {}
        self.counters: collections.Counter[str] = collections.Counter()
        self.last_progress = self.started

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started

    def snapshot_counters(self) -> dict[str, int]:
        return {key: int(value) for key, value in sorted(self.counters.items())}

    def progress(
        self,
        message: str,
        *,
        force: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        now = time.monotonic()
        if not force and now - self.last_progress < 5.0:
            return
        self.last_progress = now
        if not self.emit_progress:
            return
        _json_event(
            {
                "event": "validator_progress",
                "validator_revision": VALIDATOR_REVISION,
                "stage": self.current_stage,
                "message": message,
                "elapsed_seconds": round(now - self.started, 6),
                "stage_elapsed_seconds": round(
                    now - self.current_stage_started, 6
                ),
                "workload_counters": self.snapshot_counters(),
                "details": details or {},
            }
        )

    def increment(self, counter: str, amount: int = 1) -> None:
        self.counters[counter] += amount
        self.progress(f"workload:{counter}")

    @contextlib.contextmanager
    def stage(
        self,
        name: str,
        *,
        expected_work_items: int | None = None,
    ) -> Iterator[None]:
        if name in self.stage_timings:
            raise RuntimeError(f"duplicate diagnostic stage: {name}")
        self.current_stage = name
        self.current_stage_started = time.monotonic()
        counters_before = self.snapshot_counters()
        self.progress(
            "stage_started",
            force=True,
            details={"expected_work_items": expected_work_items},
        )
        try:
            yield
        finally:
            finished = time.monotonic()
            self.stage_timings[name] = {
                "elapsed_seconds": round(
                    finished - self.current_stage_started, 6
                ),
                "expected_work_items": expected_work_items,
                "counters_before": counters_before,
                "counters_after": self.snapshot_counters(),
            }
            self.progress("stage_completed", force=True)

    def report(self) -> dict[str, Any]:
        return {
            "total_elapsed_seconds": round(self.elapsed_seconds, 6),
            "current_or_last_stage": self.current_stage,
            "stage_timings": self.stage_timings,
            "workload_counters": self.snapshot_counters(),
            "progress_interval_seconds": 5.0,
        }


@dataclass(frozen=True)
class Bounds3D:
    minimum_mm: tuple[float, float, float]
    maximum_mm: tuple[float, float, float]


@dataclass(frozen=True)
class PreparedObstacle:
    key: str
    shape: Any | None
    bounds: Bounds3D
    source: str


def bounds_from_shape(shape: Any) -> Bounds3D:
    box = shape.BoundBox
    return Bounds3D(
        (float(box.XMin), float(box.YMin), float(box.ZMin)),
        (float(box.XMax), float(box.YMax), float(box.ZMax)),
    )


def bounds_from_limits(
    minimum_mm: Sequence[float], maximum_mm: Sequence[float]
) -> Bounds3D:
    return Bounds3D(
        tuple(float(value) for value in minimum_mm),  # type: ignore[arg-type]
        tuple(float(value) for value in maximum_mm),  # type: ignore[arg-type]
    )


def prepare_obstacles(
    components: Sequence[Any], diagnostics: RunDiagnostics
) -> tuple[PreparedObstacle, ...]:
    prepared = tuple(
        PreparedObstacle(
            key=component.key,
            shape=component.shape,
            bounds=bounds_from_limits(
                component.minimum_mm, component.maximum_mm
            ),
            source=component.source,
        )
        for component in components
    )
    diagnostics.increment("immutable_obstacle_bounds_precomputed", len(prepared))
    return prepared


def bounds_overlap(
    first: Bounds3D, second: Bounds3D, tolerance: float = 1.0e-9
) -> bool:
    return not any(
        first.maximum_mm[index] < second.minimum_mm[index] - tolerance
        or first.minimum_mm[index] > second.maximum_mm[index] + tolerance
        for index in range(3)
    )


def aabb_separation(first: Bounds3D, second: Bounds3D) -> float:
    gaps = [
        max(
            second.minimum_mm[index] - first.maximum_mm[index],
            first.minimum_mm[index] - second.maximum_mm[index],
            0.0,
        )
        for index in range(3)
    ]
    return math.sqrt(sum(value * value for value in gaps))


def collision_only_record(
    shape: Any,
    component: PreparedObstacle,
    epsilon: float,
    diagnostics: RunDiagnostics,
    *,
    shape_bounds: Bounds3D | None = None,
) -> dict[str, Any]:
    """Measure collision volume without ever requesting OCCT distance."""
    diagnostics.increment("collision_only_checks")
    if shape_bounds is None:
        shape_bounds = bounds_from_shape(shape)
        diagnostics.increment("subject_bounds_computed")
    if component.shape is None:
        separation = aabb_separation(shape_bounds, component.bounds)
        if separation > 0.0:
            diagnostics.increment("collision_aabb_disjoint_zero_returns")
            return {
                "intersection_volume_mm3": 0.0,
                "distance_lower_bound_mm": separation,
                "unresolved": False,
                "method": "strict_aabb_separation_for_nonsewn_frozen_obj",
            }
        diagnostics.increment("collision_unresolved_nonsewn_aabb_overlap")
        return {
            "intersection_volume_mm3": None,
            "distance_lower_bound_mm": 0.0,
            "unresolved": True,
            "method": "aabb_overlap_nonsewn_frozen_obj_unresolved",
        }
    if not bounds_overlap(shape_bounds, component.bounds):
        diagnostics.increment("collision_aabb_disjoint_zero_returns")
        return {
            "intersection_volume_mm3": 0.0,
            "distance_lower_bound_mm": aabb_separation(
                shape_bounds, component.bounds
            ),
            "unresolved": False,
            "method": "aabb_disjoint_zero_collision_no_distance",
        }
    diagnostics.increment("collision_aabb_overlaps")
    diagnostics.increment("exact_common_volume_calls")
    common = shape.common(component.shape)
    volume = float(common.Volume)
    return {
        "intersection_volume_mm3": volume,
        "intersection_bounds": original._bounds(common)
        if volume > epsilon
        else None,
        "unresolved": False,
        "method": "aabb_overlap_then_exact_occt_common_no_distance",
    }


def clearance_distance_record(
    shape: Any,
    component: PreparedObstacle,
    diagnostics: RunDiagnostics,
    *,
    shape_bounds: Bounds3D | None = None,
    minimum_required_mm: float | None = None,
) -> dict[str, Any]:
    """Retain the immutable validator's exact clearance semantics."""
    diagnostics.increment("clearance_distance_checks")
    if shape.isNull():
        diagnostics.increment("clearance_unresolved_null_subject")
        return {
            "distance_mm": None,
            "unresolved": True,
            "method": "null_trimmed_target",
        }
    if shape_bounds is None:
        shape_bounds = bounds_from_shape(shape)
        diagnostics.increment("subject_bounds_computed")
    if component.shape is None:
        separation = aabb_separation(shape_bounds, component.bounds)
        diagnostics.increment("clearance_nonsewn_aabb_lower_bounds")
        return {
            "distance_mm": separation if separation > 0.0 else None,
            "distance_lower_bound_mm": separation,
            "unresolved": separation <= 0.0,
            "method": "strict_aabb_lower_bound_for_nonsewn_frozen_obj",
        }
    if component.shape.isNull():
        diagnostics.increment("clearance_empty_components")
        return {
            "distance_mm": 1.0e300,
            "unresolved": False,
            "method": "no_component_material_outside_authorized_interface",
        }
    if minimum_required_mm is not None:
        lower_bound = aabb_separation(shape_bounds, component.bounds)
        if lower_bound >= float(minimum_required_mm):
            diagnostics.increment("clearance_aabb_gate_proofs")
            return {
                "distance_mm": lower_bound,
                "distance_lower_bound_mm": lower_bound,
                "required_minimum_mm": float(minimum_required_mm),
                "unresolved": False,
                "method": "aabb_lower_bound_proves_clearance_gate_no_distance",
            }
    diagnostics.increment("exact_distance_calls")
    return {
        "distance_mm": float(shape.distToShape(component.shape)[0]),
        "unresolved": False,
        "method": "exact_occt_distance",
    }


def safe_common_volume(
    first: Any,
    second: Any,
    diagnostics: RunDiagnostics,
    *,
    first_bounds: Bounds3D | None = None,
    second_bounds: Bounds3D | None = None,
) -> float:
    diagnostics.increment("direct_collision_volume_checks")
    first_bounds = first_bounds or bounds_from_shape(first)
    second_bounds = second_bounds or bounds_from_shape(second)
    if not bounds_overlap(first_bounds, second_bounds):
        diagnostics.increment("direct_collision_aabb_disjoint_zero_returns")
        return 0.0
    diagnostics.increment("exact_common_volume_calls")
    return float(first.common(second).Volume)


def obstacle_identity(component: PreparedObstacle) -> tuple[Any, ...]:
    """Identify copied instances of one immutable baseline obstacle."""
    return (
        component.source,
        component.bounds.minimum_mm,
        component.bounds.maximum_mm,
        component.shape is None,
    )


def shell_collision_prerequisites_allow_clearance(
    shell_matrix: dict[str, Any], epsilon: float
) -> bool:
    """Return whether G03 can still pass before clearance is measured.

    This is the exact collision-only prefix of the immutable G03 expression.
    Clearance and distance cannot change G03 after any prefix term is false.
    """
    known_required = {
        "upper_C001",
        "lower_C001",
        "lower_C012",
        "lower_C013",
    }
    known = shell_matrix.get("known_f19_intersections_mm3", {})
    known_resolved = (
        isinstance(known, dict)
        and set(known) == known_required
        and all(float(value) <= epsilon for value in known.values())
    )
    return bool(
        shell_matrix.get("component_count") == 101
        and shell_matrix.get("unresolved_error_count") == 0
        and float(
            shell_matrix.get("maximum_positive_intersection_mm3", math.inf)
        )
        <= epsilon
        and known_resolved
    )


def batched_collision_gate_maximum(
    subject: Any,
    subject_bounds: Bounds3D,
    components: Sequence[PreparedObstacle],
    epsilon: float,
    diagnostics: RunDiagnostics,
    Part: Any,
    *,
    preferred_witness: PreparedObstacle | None = None,
) -> dict[str, Any]:
    """Prove the exact collision gate with one common before pair refinement.

    The compound common is an exact upper bound on every individual common.
    When that bound is at or below the gate epsilon, every pair passes without
    individual Booleans.  When it is above epsilon, individual exact commons
    are evaluated until either one exact gate failure is found or every pair is
    proven at or below epsilon.  This preserves the original Boolean gate for
    both clear and colliding cases, including sums of sub-epsilon contacts.
    """
    unresolved: list[str] = []
    overlapping: list[PreparedObstacle] = []
    seen: set[tuple[Any, ...]] = set()
    for component in components:
        diagnostics.increment("collision_only_checks")
        if component.shape is None:
            separation = aabb_separation(subject_bounds, component.bounds)
            if separation > 0.0:
                diagnostics.increment("collision_aabb_disjoint_zero_returns")
            else:
                diagnostics.increment(
                    "collision_unresolved_nonsewn_aabb_overlap"
                )
                unresolved.append(component.key)
            continue
        if not bounds_overlap(subject_bounds, component.bounds):
            diagnostics.increment("collision_aabb_disjoint_zero_returns")
            continue
        diagnostics.increment("collision_aabb_overlaps")
        identity = obstacle_identity(component)
        if identity in seen:
            diagnostics.increment("collision_duplicate_obstacle_reuses")
            continue
        seen.add(identity)
        overlapping.append(component)

    maximum = 0.0
    aggregate_upper_bound = 0.0
    refined_pairs = 0
    failure_witness: PreparedObstacle | None = None
    witness_reused = False
    if overlapping:
        overlapping_by_identity = {
            obstacle_identity(component): component for component in overlapping
        }
        if preferred_witness is not None:
            witness = overlapping_by_identity.get(
                obstacle_identity(preferred_witness)
            )
            if witness is not None:
                diagnostics.increment("exact_common_volume_calls")
                diagnostics.increment("collision_witness_reuse_calls")
                refined_pairs += 1
                witness_volume = float(subject.common(witness.shape).Volume)
                if witness_volume > epsilon:
                    diagnostics.increment("collision_witness_reuse_gate_failures")
                    maximum = witness_volume
                    aggregate_upper_bound = witness_volume
                    failure_witness = witness
                    witness_reused = True
                    return {
                        "maximum_collision_mm3": maximum,
                        "unresolved": unresolved,
                        "overlapping_unique_exact_obstacles": len(overlapping),
                        "aggregate_common_upper_bound_mm3": aggregate_upper_bound,
                        "refined_pair_count": refined_pairs,
                        "witness_reused": witness_reused,
                        "_failure_witness": failure_witness,
                    }
        compound = Part.makeCompound(
            [component.shape for component in overlapping]
        )
        diagnostics.increment("batched_common_volume_calls")
        diagnostics.increment("exact_common_volume_calls")
        aggregate_upper_bound = float(subject.common(compound).Volume)
        if aggregate_upper_bound <= epsilon:
            maximum = aggregate_upper_bound
            diagnostics.increment("batched_common_gate_passes")
        else:
            diagnostics.increment("batched_common_refinements")
            for component in overlapping:
                diagnostics.increment("exact_common_volume_calls")
                diagnostics.increment("batched_refinement_pair_calls")
                refined_pairs += 1
                volume = float(subject.common(component.shape).Volume)
                maximum = max(maximum, volume)
                if volume > epsilon:
                    failure_witness = component
                    diagnostics.increment(
                        "batched_refinement_gate_failure_short_circuits"
                    )
                    break
    return {
        "maximum_collision_mm3": maximum,
        "unresolved": unresolved,
        "overlapping_unique_exact_obstacles": len(overlapping),
        "aggregate_common_upper_bound_mm3": aggregate_upper_bound,
        "refined_pair_count": refined_pairs,
        "witness_reused": witness_reused,
        "_failure_witness": failure_witness,
    }


def measure_sweep(
    moving: Any,
    translations: Sequence[Any],
    components: Sequence[PreparedObstacle],
    epsilon: float,
    diagnostics: RunDiagnostics,
    Part: Any,
    *,
    motion_name: str,
    group_size: int = 8,
) -> dict[str, Any]:
    """Measure one motion gate with exact chunk proofs and pair refinement.

    Each translation remains an explicit sample.  A common between a compound
    of sample shapes and a compound of their AABB-overlapping immutable
    obstacles is an exact upper bound on every pair in that chunk.  A bound at
    or below epsilon proves the whole chunk; a larger bound is refined through
    the existing exact per-sample collision path.  After one exact gate
    failure, later positions are still constructed and counted, but no further
    common volume can change the gate outcome.
    """
    if group_size < 1:
        raise ValueError("group_size must be positive")
    maximum = 0.0
    unresolved: list[str] = []
    samples: list[dict[str, Any]] = []
    preferred_witness: PreparedObstacle | None = None
    placed_samples: list[tuple[int, Any, Bounds3D]] = []
    for index, translation in enumerate(translations):
        placed = original._translated(moving, translation)
        diagnostics.increment("motion_shapes_translated")
        placed_bounds = bounds_from_shape(placed)
        diagnostics.increment("motion_sample_bounds_computed")
        placed_samples.append((index, placed, placed_bounds))

    gate_outcome_fixed = False
    for chunk_start in range(0, len(placed_samples), group_size):
        chunk = placed_samples[chunk_start : chunk_start + group_size]
        if gate_outcome_fixed:
            for index, _placed, _placed_bounds in chunk:
                samples.append(
                    {
                        "index": index,
                        "maximum_collision_mm3": None,
                        "measurement_method": (
                            "exact_gate_failure_already_witnessed"
                        ),
                        "gate_outcome_already_fixed": True,
                    }
                )
                diagnostics.increment(
                    "motion_gate_short_circuited_samples"
                )
                diagnostics.increment(f"{motion_name}_samples_completed")
                diagnostics.progress(
                    "motion_sample_completed",
                    force=True,
                    details={
                        "motion": motion_name,
                        "sample_index": index,
                        "sample_count": len(translations),
                        "exact_gate_outcome_already_fixed": True,
                    },
                )
            continue

        group_obstacles: list[PreparedObstacle] = []
        group_unresolved: list[str] = []
        seen: set[tuple[Any, ...]] = set()
        for index, _placed, placed_bounds in chunk:
            for component in components:
                diagnostics.increment("collision_only_checks")
                if component.shape is None:
                    if aabb_separation(placed_bounds, component.bounds) > 0.0:
                        diagnostics.increment(
                            "collision_aabb_disjoint_zero_returns"
                        )
                    else:
                        diagnostics.increment(
                            "collision_unresolved_nonsewn_aabb_overlap"
                        )
                        group_unresolved.append(
                            f"sample_{index}:{component.key}"
                        )
                    continue
                if not bounds_overlap(placed_bounds, component.bounds):
                    diagnostics.increment(
                        "collision_aabb_disjoint_zero_returns"
                    )
                    continue
                diagnostics.increment("collision_aabb_overlaps")
                identity = obstacle_identity(component)
                if identity in seen:
                    diagnostics.increment(
                        "collision_duplicate_obstacle_reuses"
                    )
                    continue
                seen.add(identity)
                group_obstacles.append(component)

        group_upper_bound = 0.0
        if group_obstacles:
            moving_compound = Part.makeCompound(
                [placed for _index, placed, _bounds in chunk]
            )
            obstacle_compound = Part.makeCompound(
                [component.shape for component in group_obstacles]
            )
            diagnostics.increment("sweep_group_upper_bound_calls")
            diagnostics.increment("exact_common_volume_calls")
            diagnostics.progress(
                "motion_group_exact_common_started",
                force=True,
                details={
                    "motion": motion_name,
                    "first_sample_index": chunk[0][0],
                    "last_sample_index": chunk[-1][0],
                    "unique_obstacle_count": len(group_obstacles),
                },
            )
            group_upper_bound = float(
                moving_compound.common(obstacle_compound).Volume
            )

        if not group_unresolved and group_upper_bound <= epsilon:
            diagnostics.increment("sweep_group_upper_bound_gate_passes")
            maximum = max(maximum, group_upper_bound)
            for index, _placed, _placed_bounds in chunk:
                samples.append(
                    {
                        "index": index,
                        "maximum_collision_mm3": group_upper_bound,
                        "aggregate_common_upper_bound_mm3": group_upper_bound,
                        "overlapping_unique_exact_obstacles": len(
                            group_obstacles
                        ),
                        "refined_pair_count": 0,
                        "witness_reused": False,
                        "measurement_method": "exact_chunk_upper_bound",
                    }
                )
                diagnostics.increment(f"{motion_name}_samples_completed")
                diagnostics.progress(
                    "motion_sample_completed",
                    force=True,
                    details={
                        "motion": motion_name,
                        "sample_index": index,
                        "sample_count": len(translations),
                        "exact_chunk_upper_bound_mm3": group_upper_bound,
                    },
                )
            continue

        diagnostics.increment("sweep_group_refinements")
        for index, placed, placed_bounds in chunk:
            if gate_outcome_fixed:
                samples.append(
                    {
                        "index": index,
                        "maximum_collision_mm3": None,
                        "measurement_method": (
                            "exact_gate_failure_already_witnessed"
                        ),
                        "gate_outcome_already_fixed": True,
                    }
                )
                diagnostics.increment(
                    "motion_gate_short_circuited_samples"
                )
            else:
                batch = batched_collision_gate_maximum(
                    placed,
                    placed_bounds,
                    components,
                    epsilon,
                    diagnostics,
                    Part,
                    preferred_witness=preferred_witness,
                )
                failure_witness = batch.pop("_failure_witness")
                if failure_witness is not None:
                    preferred_witness = failure_witness
                sample_unresolved = [
                    f"sample_{index}:{key}"
                    for key in batch["unresolved"]
                ]
                unresolved.extend(sample_unresolved)
                sample_max = float(batch["maximum_collision_mm3"])
                maximum = max(maximum, sample_max)
                batch["index"] = index
                batch["measurement_method"] = "exact_sample_refinement"
                samples.append(batch)
                gate_outcome_fixed = bool(
                    sample_unresolved or sample_max > epsilon
                )
                if gate_outcome_fixed:
                    diagnostics.increment(
                        "motion_exact_gate_failures_short_circuited"
                    )
            diagnostics.increment(f"{motion_name}_samples_completed")
            diagnostics.progress(
                "motion_sample_completed",
                force=True,
                details={
                    "motion": motion_name,
                    "sample_index": index,
                    "sample_count": len(translations),
                    "exact_gate_outcome_already_fixed": gate_outcome_fixed,
                },
            )
    return {
        "sample_count": len(samples),
        "complete_sample_set": not unresolved,
        "all_required_sample_positions_enumerated": (
            len(samples) == len(translations)
        ),
        "maximum_unintended_collision_mm3": maximum
        if not unresolved
        else math.inf,
        "unresolved": unresolved,
        "samples": samples,
    }


def measure_previsual(
    root: Path,
    baseline: dict[str, Any],
    contract: dict[str, Any],
    preservation_report: dict[str, Any],
    root_projection_preflight: dict[str, Any],
    signed_frame_preflight: dict[str, Any],
    candidate_path: Path,
    App: Any,
    Mesh: Any,
    Part: Any,
    diagnostics: RunDiagnostics,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the unchanged measurements with optimized collision execution."""
    parameters = contract["allowed_mutations"][0]["parameters"]
    validation = parameters["validation_contract"]
    limits = validation["limits"]
    epsilon = float(limits["maximum_unintended_positive_intersection_mm3"])
    baseline_path = root / baseline["assembly"]["path"]

    with diagnostics.stage("S01_REFERENCE_GEOMETRY"):
        references = original._reference_geometry(parameters, App, Part)

    with diagnostics.stage("S02_LOAD_101_SHELL_COMPONENTS", expected_work_items=101):
        components, component_load = original._load_shell_components(
            root, baseline_path, validation, App, Mesh, Part
        )
        prepared_components = prepare_obstacles(components, diagnostics)
        diagnostics.counters["shell_components_loaded"] = len(components)

    with diagnostics.stage("S03_LOAD_PROTECTED_OBSTACLES"):
        protected_obstacles = original._load_protected_obstacles(
            baseline_path, App
        )
        prepared_protected = prepare_obstacles(
            protected_obstacles, diagnostics
        )
        diagnostics.counters["protected_obstacles_loaded"] = len(
            protected_obstacles
        )
        collision_obstacles = (
            *prepared_components,
            *prepared_protected,
        )
        diagnostics.counters["collision_obstacles_total"] = len(
            collision_obstacles
        )

    with diagnostics.stage("S04_OPEN_HELD_CANDIDATE_READ_ONLY"):
        candidate_document = App.openDocument(str(candidate_path))
        try:
            target = candidate_document.getObject(original.TARGET_OBJECT)
            if (
                target is None
                or not hasattr(target, "Shape")
                or target.Shape.isNull()
            ):
                raise RuntimeError("candidate target is missing or null")
            target_shape = target.Shape.copy()
            metadata = original._metadata_exact(target, parameters, App)
        finally:
            App.closeDocument(candidate_document.Name)
        target_bounds = bounds_from_shape(target_shape)

    with diagnostics.stage("S05_TOPOLOGY_AND_PRESERVATION"):
        try:
            raw_check = target_shape.check(True)
            check_records = [str(item) for item in (raw_check or [])]
        except Exception as exc:
            check_records = [f"{type(exc).__name__}: {exc}"]
        topology = {
            "valid": bool(target_shape.isValid()),
            "closed": bool(target_shape.isClosed()),
            "solid_count": len(target_shape.Solids),
            "connected_component_count": len(target_shape.Solids),
            "self_intersection_count": len(check_records),
            "occt_check_records": check_records,
            "volume_mm3": float(target_shape.Volume),
            "bounds": original._bounds(target_shape),
        }
        candidate_sha = sha256_file(candidate_path)
        preservation = {
            "status": preservation_report.get("status"),
            "candidate_hash_matches": preservation_report.get(
                "candidate", {}
            ).get("sha256")
            == candidate_sha,
            "protected_difference_count": len(
                preservation_report.get("protected_differences", {})
            ),
            "candidate_sha256": candidate_sha,
        }

    with diagnostics.stage(
        "S06_SHELL_COLLISION_MATRIX", expected_work_items=len(components)
    ):
        shell_results: dict[str, Any] = {}
        maximum_intersection = 0.0
        unresolved = list(component_load["load_errors"])
        for component in prepared_components:
            record = collision_only_record(
                target_shape,
                component,
                epsilon,
                diagnostics,
                shape_bounds=target_bounds,
            )
            shell_results[component.key] = record
            if record["unresolved"]:
                unresolved.append(component.key)
            else:
                maximum_intersection = max(
                    maximum_intersection,
                    float(record["intersection_volume_mm3"]),
                )
            diagnostics.increment("shell_collision_components_completed")
        known = {
            "upper_C001": shell_results.get("upper_C001", {}).get(
                "intersection_volume_mm3", math.inf
            ),
            "lower_C001": shell_results.get("lower_C001", {}).get(
                "intersection_volume_mm3", math.inf
            ),
            "lower_C012": shell_results.get("lower_C012", {}).get(
                "intersection_volume_mm3", math.inf
            ),
            "lower_C013": shell_results.get("lower_C013", {}).get(
                "intersection_volume_mm3", math.inf
            ),
        }
        shell_matrix = {
            "component_count": len(shell_results),
            "unresolved_error_count": len(unresolved),
            "unresolved_errors": unresolved,
            "maximum_positive_intersection_mm3": maximum_intersection,
            "known_f19_intersections_mm3": known,
            "results": shell_results,
        }

    with diagnostics.stage(
        "S07_SHELL_CLEARANCE_DISTANCE", expected_work_items=len(components) + 1
    ):
        clearance_required = shell_collision_prerequisites_allow_clearance(
            shell_matrix, epsilon
        )
        if clearance_required:
            authorized_masks = original._authorized_interface_masks(
                parameters, references, Part
            )
            all_authorized = original._fuse(list(authorized_masks.values()))
            all_authorized_bounds = bounds_from_shape(all_authorized)
            non_mating_target = target_shape.cut(
                all_authorized
            ).removeSplitter()
            non_mating_target_bounds = bounds_from_shape(non_mating_target)
            components_for_clearance = components
        else:
            # The immutable G03 predicate has already failed on an exact
            # collision-only term. Distance cannot alter that verdict.
            authorized_masks = {}
            all_authorized = None
            all_authorized_bounds = target_bounds
            non_mating_target = target_shape
            non_mating_target_bounds = target_bounds
            components_for_clearance = ()
            diagnostics.increment(
                "clearance_stage_short_circuited_after_collision_failure"
            )
            diagnostics.progress(
                "clearance_distance_skipped_exact_g03_prefix_failure",
                force=True,
                details={
                    "maximum_positive_intersection_mm3": shell_matrix[
                        "maximum_positive_intersection_mm3"
                    ],
                    "collision_epsilon_mm3": epsilon,
                },
            )
        clearance_results: dict[str, Any] = {}
        clearance_unresolved: list[str] = []
        minimum_non_mating_clearance = (
            math.inf if clearance_required else -math.inf
        )
        trimmed_components: dict[str, PreparedObstacle] = {}
        shell_clearance_requirement = float(
            limits["minimum_non_mating_shell_clearance_mm"]
        )
        for component in components_for_clearance:
            component_bounds = bounds_from_limits(
                component.minimum_mm, component.maximum_mm
            )
            if component.shape is None:
                trimmed = PreparedObstacle(
                    component.key,
                    None,
                    component_bounds,
                    component.source,
                )
            elif not bounds_overlap(component_bounds, all_authorized_bounds):
                trimmed = PreparedObstacle(
                    component.key,
                    component.shape,
                    component_bounds,
                    component.source,
                )
                diagnostics.increment("authorized_mask_component_cuts_avoided")
            else:
                trimmed_shape = component.shape.cut(
                    all_authorized
                ).removeSplitter()
                trimmed = PreparedObstacle(
                    component.key,
                    trimmed_shape,
                    component_bounds,
                    component.source,
                )
                diagnostics.increment("authorized_mask_component_cuts_performed")
            trimmed_components[component.key] = trimmed
            record = clearance_distance_record(
                non_mating_target,
                trimmed,
                diagnostics,
                shape_bounds=non_mating_target_bounds,
                minimum_required_mm=shell_clearance_requirement,
            )
            clearance_results[component.key] = record
            if record["unresolved"]:
                clearance_unresolved.append(component.key)
            else:
                minimum_non_mating_clearance = min(
                    minimum_non_mating_clearance,
                    float(record["distance_mm"]),
                )
            diagnostics.increment("shell_clearance_components_completed")

        upper_component = next(
            (
                component
                for component in components_for_clearance
                if component.key == "upper_C001"
            ),
            None,
        )
        if upper_component is None or upper_component.shape is None:
            upper_c001_record = {
                "distance_mm": -math.inf,
                "unresolved": True,
                "method": (
                    "gate_already_failed_by_exact_shell_collision"
                    if not clearance_required
                    else "missing_exact_upper_C001"
                ),
            }
        else:
            upper_authorized = original._fuse(
                [
                    authorized_masks["aperture_bezel"],
                    authorized_masks["upper"],
                ]
            )
            upper_requirement = float(
                limits[
                    "minimum_upper_c001_clearance_outside_authorized_mount_mm"
                ]
            )
            lower_mask_bounds = bounds_from_shape(authorized_masks["lower"])
            upper_component_bounds = bounds_from_limits(
                upper_component.minimum_mm, upper_component.maximum_mm
            )
            lower_mask_separation = aabb_separation(
                lower_mask_bounds, upper_component_bounds
            )
            if lower_mask_separation >= upper_requirement:
                # Removing the distant lower authorized mask cannot affect the
                # upper-C001 threshold. Reuse the already-trimmed exact pair.
                upper_c001_record = clearance_distance_record(
                    non_mating_target,
                    trimmed_components["upper_C001"],
                    diagnostics,
                    shape_bounds=non_mating_target_bounds,
                    minimum_required_mm=upper_requirement,
                )
                upper_c001_record["distant_lower_mask_reuse_proof"] = {
                    "aabb_separation_mm": lower_mask_separation,
                    "required_minimum_mm": upper_requirement,
                    "reused_non_mating_target": True,
                }
                diagnostics.increment("upper_c001_redundant_boolean_pairs_avoided")
            else:
                upper_target = target_shape.cut(
                    upper_authorized
                ).removeSplitter()
                upper_shape = upper_component.shape.cut(
                    upper_authorized
                ).removeSplitter()
                upper_c001_record = clearance_distance_record(
                    upper_target,
                    PreparedObstacle(
                        "upper_C001",
                        upper_shape,
                        bounds_from_shape(upper_shape),
                        upper_component.source,
                    ),
                    diagnostics,
                    shape_bounds=bounds_from_shape(upper_target),
                    minimum_required_mm=upper_requirement,
                )
                upper_c001_record["distant_lower_mask_reuse_proof"] = {
                    "aabb_separation_mm": lower_mask_separation,
                    "required_minimum_mm": upper_requirement,
                    "reused_non_mating_target": False,
                }
        shell_matrix.update(
            {
                "authorized_interface_masks": sorted(authorized_masks),
                "clearance_measurement_required_for_g03": clearance_required,
                "clearance_measurement_skipped_after_exact_collision_failure": (
                    not clearance_required
                ),
                "clearance_unresolved_error_count": len(
                    clearance_unresolved
                )
                + int(upper_c001_record["unresolved"]),
                "clearance_unresolved_errors": clearance_unresolved,
                "minimum_non_mating_clearance_mm": (
                    minimum_non_mating_clearance
                ),
                "upper_c001_clearance_outside_authorized_interfaces_mm": (
                    upper_c001_record.get("distance_mm")
                ),
                "upper_c001_clearance_record": upper_c001_record,
                "clearance_results": clearance_results,
            }
        )

    with diagnostics.stage(
        "S08_CONTAINMENT_AND_MOUNT_COLLISION",
        expected_work_items=2 * len(components),
    ):
        outside = target_shape.cut(
            references["permitted_envelope"]
        ).removeSplitter()
        mount_shell_max = 0.0
        for mount in references["mounts"].values():
            mount_bounds = bounds_from_shape(mount["drilled"])
            for component in prepared_components:
                record = collision_only_record(
                    mount["drilled"],
                    component,
                    epsilon,
                    diagnostics,
                    shape_bounds=mount_bounds,
                )
                if not record["unresolved"]:
                    mount_shell_max = max(
                        mount_shell_max,
                        float(record["intersection_volume_mm3"]),
                    )
                diagnostics.increment("mount_collision_components_completed")
        containment = {
            "outside_permitted_envelope_mm3": float(outside.Volume),
            "outside_bounds": original._bounds(outside),
            "mount_related_outside_volume_mm3": mount_shell_max,
        }

    with diagnostics.stage("S09_EXTERIOR_OCCUPANCY"):
        exterior_loop = [
            (-160.0, -160.0),
            (160.0, -160.0),
            (160.0, 160.0),
            (-160.0, 160.0),
        ]
        exterior_points = [
            original._from_local(
                u,
                v,
                -50.0,
                references["origin"],
                references["axis_u"],
                references["axis_v"],
                references["axis_n"],
            )
            for u, v in exterior_loop
        ]
        exterior_halfspace = original._face(
            Part, exterior_points
        ).extrude(references["axis_n"] * 50.0)
        exterior_target = target_shape.common(exterior_halfspace)
        diagnostics.increment("exact_common_volume_calls")
        non_bezel_exterior = exterior_target.cut(
            references["bezel"]
        ).removeSplitter()
        exterior_aperture = {
            "target_exterior_volume_mm3": float(exterior_target.Volume),
            "non_bezel_exterior_volume_mm3": float(
                non_bezel_exterior.Volume
            ),
        }

    with diagnostics.stage("S10_VIEW_FRUSTUM"):
        frustum_values = validation["aperture_view_frustum"]
        depth = float(frustum_values["depth_mm"])
        expansion = depth * math.tan(
            math.radians(float(frustum_values["half_angle_deg"]))
        )
        far_loop = original._radial_offset(
            App,
            references["aperture"],
            expansion,
            references["axis_n"],
        )
        far_depth = original._at_depth(
            far_loop, depth, references["axis_n"]
        )
        frustum = Part.makeLoft(
            [
                Part.makePolygon(
                    [
                        *references["aperture"],
                        references["aperture"][0],
                    ]
                ),
                Part.makePolygon([*far_depth, far_depth[0]]),
            ],
            True,
            False,
        )
        hidden_features = original._fuse(
            [
                references["chamber"],
                references["cap_feature"],
                *[
                    record["drilled"]
                    for record in references["mounts"].values()
                ],
            ]
        )
        frustum_overlap = hidden_features.common(frustum)
        diagnostics.increment("exact_common_volume_calls")
        view_frustum = {
            "half_angle_deg": float(frustum_values["half_angle_deg"]),
            "mount_chamber_cap_volume_mm3": float(frustum_overlap.Volume),
            "overlap_bounds": original._bounds(frustum_overlap),
        }

    with diagnostics.stage("S11_LOAD_HASH_PINNED_FIT_REFERENCES"):
        fit_refs = parameters["fit_references"]
        for name, spec in fit_refs.items():
            path = root / spec["path"]
            if sha256_file(path) != spec["sha256"]:
                raise RuntimeError(f"fit reference hash mismatch: {name}")
        cap = original._read_step(
            Part, root / fit_refs["exact_v9_cap"]["path"]
        )
        diffuser = original._read_mesh_solid(
            Mesh,
            Part,
            root / fit_refs["exact_diffuser"]["path"],
            float(validation["mesh_to_occt_tolerance_mm"]),
        )

    motion = validation["motion"]
    eye_steps = int(motion["eye_sweep_samples"])
    eye_distance = float(motion["eye_sweep_distance_mm"])
    if eye_steps != REQUIRED_EYE_SAMPLES:
        raise RuntimeError("eye motion sample count changed")
    eye_translations = [
        -references["axis_n"]
        * eye_distance
        * (1.0 - index / (eye_steps - 1))
        for index in range(eye_steps)
    ]
    moving_eye = original._fuse([target_shape, diffuser])
    with diagnostics.stage(
        "S12_EYE_MOTION_41_SAMPLES",
        expected_work_items=eye_steps * len(collision_obstacles),
    ):
        eye_sweep = measure_sweep(
            moving_eye,
            eye_translations,
            collision_obstacles,
            epsilon,
            diagnostics,
            Part,
            motion_name="eye_motion",
        )
        eye_sweep["insertion_sample_count"] = eye_steps
        eye_sweep["removal_is_exact_reverse"] = True
        eye_sweep["shell_component_count"] = len(components)
        eye_sweep["protected_obstacle_count"] = len(protected_obstacles)

    cap_steps = int(motion["rear_cap_sweep_samples"])
    cap_distance = float(motion["rear_cap_sweep_distance_mm"])
    if cap_steps != REQUIRED_REAR_CAP_SAMPLES:
        raise RuntimeError("rear-cap motion sample count changed")
    seated_offset = float(
        parameters["geometry"]["rear_cap_connector"][
            "reference_seating_translation_mm"
        ]
    )
    cap_translations = [
        references["axis_n"]
        * (seated_offset + cap_distance * index / (cap_steps - 1))
        for index in range(cap_steps)
    ]
    with diagnostics.stage(
        "S13_REAR_CAP_MOTION_31_SAMPLES",
        expected_work_items=cap_steps * (len(collision_obstacles) + 1),
    ):
        cap_collision_obstacles = (
            *collision_obstacles,
            PreparedObstacle(
                "held_candidate_target",
                target_shape,
                target_bounds,
                "held_candidate_read_only_copy",
            ),
        )
        cap_sweep = measure_sweep(
            cap,
            cap_translations,
            cap_collision_obstacles,
            epsilon,
            diagnostics,
            Part,
            motion_name="rear_cap_motion",
        )
        cap_sweep["held_candidate_included_as_collision_obstacle"] = True
        cap_sweep["removal_is_exact_reverse"] = True
        cap_sweep["shell_component_count"] = len(components)
        cap_sweep["protected_obstacle_count"] = len(protected_obstacles)

    with diagnostics.stage(
        "S14_HARDWARE_ACCESS",
        expected_work_items=2 * 5 * len(collision_obstacles),
    ):
        hardware_shapes = original._hardware_envelopes(
            parameters, references, App, Part
        )
        hardware_contract = validation["hardware_envelopes"]
        hardware_records: dict[str, Any] = {}
        all_cap_positions = [
            original._translated(cap, translation)
            for translation in cap_translations
        ]
        diagnostics.increment("hardware_cap_positions_constructed", cap_steps)
        for role, shapes in hardware_shapes.items():
            current_mount = references["mounts"][role]["drilled"]
            opposite_role = "lower" if role == "upper" else "upper"
            opposite_mount = references["mounts"][opposite_role]["drilled"]
            max_collision = 0.0
            collision_details: dict[str, float] = {}
            subjects = {
                "target": target_shape,
                "opposite_mount": opposite_mount,
                "chamber": references["chamber"],
                "rear_cap_seated": all_cap_positions[0],
            }
            subject_bounds = {
                name: bounds_from_shape(subject)
                for name, subject in subjects.items()
            }
            for name, envelope in shapes.items():
                envelope_bounds = bounds_from_shape(envelope)
                for subject_name, subject in subjects.items():
                    volume = safe_common_volume(
                        envelope,
                        subject,
                        diagnostics,
                        first_bounds=envelope_bounds,
                        second_bounds=subject_bounds[subject_name],
                    )
                    collision_details[f"{name}_vs_{subject_name}"] = volume
                    max_collision = max(max_collision, volume)
                for component in collision_obstacles:
                    record = collision_only_record(
                        envelope,
                        component,
                        epsilon,
                        diagnostics,
                        shape_bounds=envelope_bounds,
                    )
                    if record["unresolved"]:
                        max_collision = math.inf
                    else:
                        max_collision = max(
                            max_collision,
                            float(record["intersection_volume_mm3"]),
                        )
                    diagnostics.increment("hardware_obstacle_checks_completed")
            hardware_records[role] = {
                "bolt_length_range_mm": [
                    float(hardware_contract["bolt_min_length_mm"]),
                    float(hardware_contract["bolt_max_length_mm"]),
                ],
                "washer_count": 2,
                "washer_od_mm": float(
                    hardware_contract["washer_outer_diameter_mm"]
                ),
                "washer_thickness_mm": float(
                    hardware_contract["washer_thickness_mm"]
                ),
                "nyloc_od_mm": float(
                    hardware_contract["nyloc_outer_diameter_mm"]
                ),
                "nyloc_length_mm": float(
                    hardware_contract["nyloc_length_mm"]
                ),
                "tool_diameter_mm": float(
                    hardware_contract["tool_approach_diameter_mm"]
                ),
                "tool_length_mm": float(
                    hardware_contract["tool_approach_length_mm"]
                ),
                "max_path_collision_mm3": max_collision,
                "max_prohibited_intersection_mm3": max_collision,
                "behind_flange_blocking_volume_mm3": max(
                    collision_details.get(
                        "head_washer_vs_target", math.inf
                    ),
                    collision_details.get("nyloc_vs_target", math.inf),
                    collision_details.get("tool_vs_target", math.inf),
                ),
                "collision_details": collision_details,
                "current_mount_reference_volume_mm3": float(
                    current_mount.Volume
                ),
            }

    with diagnostics.stage("S15_MOUNT_INTEGRITY"):
        integrity: dict[str, Any] = {}
        mount_face_offset = float(
            parameters["geometry"]["head_mount"][
                "bore_center_to_mating_face_mm"
            ]
        )
        for role, mount in references["mounts"].items():
            engagement = safe_common_volume(
                mount["uncut"], references["chamber"], diagnostics
            )
            missing_ligament = mount["required_ligament_annulus"].cut(
                target_shape
            )
            measured_mating_gap = (
                (mount["eye_bore"] - mount["head_bore"]).dot(
                    mount["bore_axis_vector"]
                )
                - 2.0 * mount_face_offset
            )
            integrity[role] = {
                "direct_owner_root_engagement_mm3": engagement,
                "required_ligament_missing_volume_mm3": float(
                    missing_ligament.Volume
                ),
                "head_mount_mating_gap_mm": float(measured_mating_gap),
                "bore_to_edge_material_mm": float(
                    limits["minimum_bore_to_edge_material_mm"]
                )
                if float(missing_ligament.Volume) <= epsilon
                else 0.0,
            }

    with diagnostics.stage("S16_DATUM_INTERFACE_AND_WALL"):
        expected_difference = target_shape.cut(references["expected_target"])
        expected_missing = references["expected_target"].cut(target_shape)
        cap_seated = original._translated(
            cap, references["axis_n"] * seated_offset
        )
        cap_intersection = safe_common_volume(
            target_shape,
            cap_seated,
            diagnostics,
            first_bounds=target_bounds,
            second_bounds=bounds_from_shape(cap_seated),
        )
        diagnostics.increment("exact_distance_calls")
        cap_clearance = float(target_shape.distToShape(cap_seated)[0])
        diffuser_intersection = safe_common_volume(
            target_shape,
            diffuser,
            diagnostics,
            first_bounds=target_bounds,
            second_bounds=bounds_from_shape(diffuser),
        )
        datum_interface = {
            **metadata,
            "signed_mount_frame_pass": signed_frame_preflight.get("status")
            == "PASS__INDEPENDENT_SIGNED_AXIS_FRAMES"
            and all(
                record.get("passed") is True
                for record in signed_frame_preflight.get(
                    "frames", {}
                ).values()
            ),
            "signed_mount_frame_preflight": signed_frame_preflight,
            "rear_cap_root_projection_pass": root_projection_preflight.get(
                "status"
            )
            == "PASS__INDEPENDENT_EDGE_PROJECTIONS"
            and all(
                record.get("passed") is True
                for record in root_projection_preflight.get(
                    "roots", {}
                ).values()
            ),
            "rear_cap_root_projection": root_projection_preflight,
            "reconstructed_cap_roots": references["cap_roots"],
            "rear_cap_interface_pass": cap_intersection <= epsilon
            and abs(
                cap_clearance
                - float(
                    parameters["geometry"]["rear_cap_connector"][
                        "mating_gap_mm"
                    ]
                )
            )
            <= float(limits["maximum_dimensional_deviation_mm"]),
            "diffuser_interface_pass": diffuser_intersection <= epsilon,
            "minimum_wall_pass": float(expected_difference.Volume) <= epsilon
            and float(expected_missing.Volume) <= epsilon,
            "target_outside_expected_reference_mm3": float(
                expected_difference.Volume
            ),
            "expected_reference_missing_from_target_mm3": float(
                expected_missing.Volume
            ),
            "rear_cap_intersection_mm3": cap_intersection,
            "rear_cap_minimum_clearance_mm": cap_clearance,
            "diffuser_intersection_mm3": diffuser_intersection,
        }

    observations = {
        "topology": topology,
        "preservation": preservation,
        "shell_matrix": shell_matrix,
        "containment": containment,
        "exterior_aperture": exterior_aperture,
        "view_frustum": view_frustum,
        "eye_insertion_removal": eye_sweep,
        "rear_cap_sweep": cap_sweep,
        "hardware_access": hardware_records,
        "mount_integrity": integrity,
        "datum_and_interface_preservation": datum_interface,
    }
    with diagnostics.stage("S17_EXACT_ORIGINAL_G01_G12_EVALUATOR"):
        evaluation = evaluate_previsual_observations(observations, limits)
    return observations, evaluation


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preservation-report", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--authorization-sha256")
    parser.add_argument("--performance-preflight", action="store_true")
    parser.add_argument("--timing-report", type=Path)
    parser.add_argument("--verify-authorization-only", action="store_true")
    return parser.parse_args(argv)


def resolve_input(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def require_exact_path(
    actual: Path, expected: Path, label: str
) -> None:
    if actual.resolve() != expected.resolve():
        raise RuntimeError(f"{label} path mismatch: {actual}")


def file_state(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "sha256": sha256_file(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mode": oct(stat.st_mode & 0o777),
    }


def validate_held_inputs(
    root: Path, args: argparse.Namespace
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    Path,
    Path,
    Path,
]:
    contract_path = resolve_input(root, args.contract)
    baseline_path = resolve_input(root, args.baseline)
    preservation_path = resolve_input(root, args.preservation_report)
    require_exact_path(
        contract_path, root / ORIGINAL_CONTRACT_RELATIVE, "contract"
    )
    require_exact_path(
        baseline_path, root / BASELINE_MANIFEST_RELATIVE, "baseline manifest"
    )
    require_exact_path(
        preservation_path,
        root / PRESERVATION_REPORT_RELATIVE,
        "preservation report",
    )
    if sha256_file(contract_path) != ORIGINAL_CONTRACT_SHA256:
        raise RuntimeError("immutable candidate contract hash mismatch")
    if sha256_file(baseline_path) != BASELINE_MANIFEST_SHA256:
        raise RuntimeError("approved baseline manifest hash mismatch")
    if sha256_file(preservation_path) != PRESERVATION_REPORT_SHA256:
        raise RuntimeError("preservation report hash mismatch")
    original_path = Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
    if sha256_file(original_path) != ORIGINAL_VALIDATOR_SHA256:
        raise RuntimeError("immutable timed-out validator hash mismatch")
    runtime_path = root / RUNTIME_MANIFEST_RELATIVE
    if sha256_file(runtime_path) != RUNTIME_MANIFEST_SHA256:
        raise RuntimeError("pinned runtime manifest hash mismatch")

    baseline = original.load_json(baseline_path)
    contract = original.load_json(contract_path)
    preservation = original.load_json(preservation_path)
    candidate_path = root / HELD_CANDIDATE_RELATIVE
    if sha256_file(candidate_path) != HELD_CANDIDATE_SHA256:
        raise RuntimeError("held candidate hash mismatch")
    if preservation.get("status") != "PASS__READY_FOR_FIXED_VIEW_REVIEW":
        raise RuntimeError("held preservation status changed")
    if preservation.get("candidate", {}).get("sha256") != HELD_CANDIDATE_SHA256:
        raise RuntimeError("preservation candidate pin mismatch")
    parameters = contract["allowed_mutations"][0]["parameters"]
    motion = parameters["validation_contract"]["motion"]
    if int(motion["eye_sweep_samples"]) != REQUIRED_EYE_SAMPLES:
        raise RuntimeError("held eye-motion sample count changed")
    if int(motion["rear_cap_sweep_samples"]) != REQUIRED_REAR_CAP_SAMPLES:
        raise RuntimeError("held rear-cap sample count changed")
    if contract.get("iteration_id") != original.ITERATION_ID:
        raise RuntimeError("held iteration identity changed")
    return (
        baseline,
        contract,
        preservation,
        candidate_path,
        baseline_path,
        preservation_path,
    )


def validate_authorization(
    root: Path,
    authorization_path: Path,
    authorization_sha256: str,
) -> tuple[dict[str, Any], str]:
    authorization_path = resolve_input(root, authorization_path)
    if len(authorization_sha256) != 64:
        raise RuntimeError("authorization SHA-256 must be explicit")
    actual_authorization_hash = sha256_file(authorization_path)
    if actual_authorization_hash != authorization_sha256:
        raise RuntimeError("authorization record hash mismatch")
    authorization = original.load_json(authorization_path)
    if authorization.get("schema_version") != "1.0":
        raise RuntimeError("validator authorization schema mismatch")
    if authorization.get("state") != "AUTHORIZED__NOT_INVOKED":
        raise RuntimeError("validator authorization is not fresh")
    if authorization.get("classification") != (
        "VALIDATOR_HOLD__CANDIDATE_IMMUTABLE"
    ):
        raise RuntimeError("validator authorization hold classification changed")
    pins = authorization.get("immutable_pins", {})
    expected_pins = {
        "candidate_sha256": HELD_CANDIDATE_SHA256,
        "preservation_report_sha256": PRESERVATION_REPORT_SHA256,
        "original_contract_sha256": ORIGINAL_CONTRACT_SHA256,
        "timed_out_validator_sha256": ORIGINAL_VALIDATOR_SHA256,
        "baseline_manifest_sha256": BASELINE_MANIFEST_SHA256,
        "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
    }
    for key, expected in expected_pins.items():
        if pins.get(key) != expected:
            raise RuntimeError(f"authorization immutable pin mismatch: {key}")
    validator = authorization.get("validator_revision", {})
    if validator.get("id") != VALIDATOR_ID:
        raise RuntimeError("authorization validator ID mismatch")
    if int(validator.get("revision", -1)) != VALIDATOR_REVISION:
        raise RuntimeError("authorization validator revision mismatch")
    validator_path = root / validator.get("path", "")
    if validator_path.resolve() != Path(__file__).resolve():
        raise RuntimeError("authorization validator path mismatch")
    if sha256_file(validator_path) != validator.get("sha256"):
        raise RuntimeError("authorization validator hash mismatch")
    if validator.get("sha256") != sha256_file(Path(__file__)):
        raise RuntimeError("running validator differs from authorization")
    performance = authorization.get("performance_preflight", {})
    performance_path = root / performance.get("path", "")
    if sha256_file(performance_path) != performance.get("sha256"):
        raise RuntimeError("authorization performance report hash mismatch")
    performance_report = original.load_json(performance_path)
    if performance_report.get("status") != (
        "PASS__PERFORMANCE_PREFLIGHT_WITH_300_SECOND_MARGIN"
    ):
        raise RuntimeError("performance preflight did not authorize production")
    if performance_report.get("gate_verdict_publication_suppressed") is not True:
        raise RuntimeError("performance preflight published a gate verdict")
    if float(performance_report["budget"]["elapsed_seconds"]) > (
        PERFORMANCE_TARGET_SECONDS
    ):
        raise RuntimeError("performance preflight exceeded 180-second target")
    regression = authorization.get("regression", {})
    regression_path = root / regression.get("test_path", "")
    if sha256_file(regression_path) != regression.get("test_sha256"):
        raise RuntimeError("authorization regression test hash mismatch")
    if regression.get("status") != "PASS" or regression.get("failures") != 0:
        raise RuntimeError("authorization regression result is not PASS")
    if regression.get("gate_count") != 12:
        raise RuntimeError("authorization does not preserve all twelve gates")
    samples = authorization.get("unchanged_workload", {})
    if samples.get("eye_motion_samples") != REQUIRED_EYE_SAMPLES:
        raise RuntimeError("authorization eye sample count changed")
    if samples.get("rear_cap_samples") != REQUIRED_REAR_CAP_SAMPLES:
        raise RuntimeError("authorization rear-cap sample count changed")
    output = authorization.get("fresh_output", {})
    report_path = root / output.get("report_path", "")
    expected_parent = root / (
        "reports/generated/cat-head-cad-iterations/"
        "right-eye-serviceable-fit-prototype-v6-attempt-002"
    )
    if report_path.parent.resolve() != expected_parent.resolve():
        raise RuntimeError("authorization output is not in the held iteration")
    if report_path.name == "previsual-validation.json":
        raise RuntimeError("authorization must use a fresh revision output name")
    if report_path.exists():
        raise FileExistsError("fresh authorized verifier output already exists")
    if authorization.get("max_invocations") != 1:
        raise RuntimeError("authorization must permit exactly one invocation")
    if authorization.get("production_timeout_seconds") != 300:
        raise RuntimeError("authorization production timeout changed")
    return authorization, actual_authorization_hash


def run_measurement(
    root: Path,
    baseline: dict[str, Any],
    contract: dict[str, Any],
    preservation: dict[str, Any],
    candidate_path: Path,
    diagnostics: RunDiagnostics,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    parameters = contract["allowed_mutations"][0]["parameters"]
    registry_spec = parameters["design_control"][
        "rejected_signature_registry"
    ]
    registry_path = root / registry_spec["path"]
    if sha256_file(registry_path) != registry_spec["sha256"]:
        raise original.DesignControlError(
            "rejected-design registry hash mismatch"
        )
    registry = original.load_json(registry_path)
    with diagnostics.stage("S00_CONTRACT_AND_DATUM_PREFLIGHT"):
        design_preflight = preflight_design_control(
            contract, registry, require_approval=True
        )
        root_projection_preflight = preflight_independent_root_projection(
            parameters
        )
        signed_frame_preflight = (
            preflight_independent_signed_mount_frames(parameters)
        )
    canonical_path = root / baseline["assembly"]["path"]
    if sha256_file(canonical_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")

    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    observations, evaluation = measure_previsual(
        root,
        baseline,
        contract,
        preservation,
        root_projection_preflight,
        signed_frame_preflight,
        candidate_path,
        App,
        Mesh,
        Part,
        diagnostics,
    )
    return (
        observations,
        evaluation,
        design_preflight,
        root_projection_preflight,
        signed_frame_preflight,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.performance_preflight and args.verify_authorization_only:
        raise RuntimeError("validator modes are mutually exclusive")
    root = original.repository_root(args.contract)
    (
        baseline,
        contract,
        preservation,
        candidate_path,
        baseline_manifest_path,
        preservation_path,
    ) = validate_held_inputs(root, args)

    if args.verify_authorization_only:
        if args.authorization is None or args.authorization_sha256 is None:
            raise RuntimeError("authorization path and hash are required")
        authorization, authorization_hash = validate_authorization(
            root, args.authorization, args.authorization_sha256
        )
        result = {
            "status": "VALIDATOR_AUTHORIZATION_READY__NOT_INVOKED",
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": authorization_hash,
            "held_candidate_sha256": HELD_CANDIDATE_SHA256,
            "fresh_output": authorization["fresh_output"],
            "freecad_imported": False,
            "candidate_opened": False,
            "validator_invoked": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    candidate_before = file_state(candidate_path)
    baseline_cad_path = root / baseline["assembly"]["path"]
    baseline_before = file_state(baseline_cad_path)
    original_before = file_state(
        Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
    )
    diagnostics = RunDiagnostics(emit_progress=True)

    if args.performance_preflight:
        if args.timing_report is None or args.report is not None:
            raise RuntimeError(
                "performance preflight requires --timing-report and forbids --report"
            )
        timing_path = resolve_input(root, args.timing_report)
        tooling_root = root / "reports/generated/cat-head-cad-tooling"
        try:
            timing_path.resolve().relative_to(tooling_root.resolve())
        except ValueError as exc:
            raise RuntimeError(
                "timing report must be under cat-head-cad-tooling"
            ) from exc
        if timing_path.exists():
            raise FileExistsError("refusing to overwrite performance evidence")
        if not timing_path.parent.is_dir():
            raise RuntimeError("timing report parent directory is missing")
        observations, evaluation, design, root_projection, signed_frames = (
            run_measurement(
                root,
                baseline,
                contract,
                preservation,
                candidate_path,
                diagnostics,
            )
        )
        # Deliberately discard all physical observations and the verdict.  Only
        # completion, execution diagnostics, and immutable input evidence may
        # be persisted from this tooling preflight.
        del observations, evaluation, design, root_projection, signed_frames
        candidate_after = file_state(candidate_path)
        baseline_after = file_state(baseline_cad_path)
        original_after = file_state(
            Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
        )
        elapsed = diagnostics.elapsed_seconds
        within_target = elapsed <= PERFORMANCE_TARGET_SECONDS
        unchanged = (
            candidate_before == candidate_after
            and baseline_before == baseline_after
            and original_before == original_after
        )
        status = (
            "PASS__PERFORMANCE_PREFLIGHT_WITH_300_SECOND_MARGIN"
            if within_target and unchanged
            else "FAIL__PERFORMANCE_PREFLIGHT__AUTHORIZATION_BLOCKED"
        )
        result = {
            "schema_version": "1.0",
            "status": status,
            "validator_id": VALIDATOR_ID,
            "validator_revision": VALIDATOR_REVISION,
            "mode": "READ_ONLY_PERFORMANCE_PREFLIGHT",
            "classification": "VALIDATOR_HOLD__CANDIDATE_IMMUTABLE",
            "gate_verdict_publication_suppressed": True,
            "published_gate_fields": [],
            "measurement_completed": True,
            "budget": {
                "elapsed_seconds": round(elapsed, 6),
                "target_seconds": PERFORMANCE_TARGET_SECONDS,
                "production_limit_seconds": PRODUCTION_TIMEOUT_SECONDS,
                "margin_below_target_seconds": round(
                    PERFORMANCE_TARGET_SECONDS - elapsed, 6
                ),
                "margin_below_production_limit_seconds": round(
                    PRODUCTION_TIMEOUT_SECONDS - elapsed, 6
                ),
                "within_target": within_target,
            },
            "inputs": {
                "candidate": {
                    "path": HELD_CANDIDATE_RELATIVE,
                    "before": candidate_before,
                    "after": candidate_after,
                    "unchanged": candidate_before == candidate_after,
                },
                "preservation_report": {
                    "path": PRESERVATION_REPORT_RELATIVE,
                    "sha256": sha256_file(preservation_path),
                },
                "contract": {
                    "path": ORIGINAL_CONTRACT_RELATIVE,
                    "sha256": sha256_file(root / ORIGINAL_CONTRACT_RELATIVE),
                },
                "baseline_manifest": {
                    "path": BASELINE_MANIFEST_RELATIVE,
                    "sha256": sha256_file(baseline_manifest_path),
                },
                "canonical_baseline": {
                    "path": baseline["assembly"]["path"],
                    "before": baseline_before,
                    "after": baseline_after,
                    "unchanged": baseline_before == baseline_after,
                },
                "timed_out_validator": {
                    "path": str(
                        Path(__file__)
                        .with_name(ORIGINAL_VALIDATOR_FILENAME)
                        .relative_to(root)
                    ),
                    "before": original_before,
                    "after": original_after,
                    "unchanged": original_before == original_after,
                },
                "runtime_manifest": {
                    "path": RUNTIME_MANIFEST_RELATIVE,
                    "sha256": sha256_file(root / RUNTIME_MANIFEST_RELATIVE),
                },
            },
            "unchanged_workload": {
                "gates": [f"G{index:02d}" for index in range(1, 13)],
                "eye_motion_samples": REQUIRED_EYE_SAMPLES,
                "rear_cap_samples": REQUIRED_REAR_CAP_SAMPLES,
            },
            "diagnostics": diagnostics.report(),
            "read_only_guards": {
                "candidate_unchanged": candidate_before == candidate_after,
                "canonical_baseline_unchanged": baseline_before
                == baseline_after,
                "timed_out_validator_unchanged": original_before
                == original_after,
                "save_as_called": False,
                "document_save_called": False,
                "geometry_modified": False,
                "geometry_export_created": False,
                "candidate_replaced": False,
                "candidate_resaved": False,
            },
        }
        timing_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if status.startswith("PASS__") else 1

    if args.authorization is None or args.authorization_sha256 is None:
        raise RuntimeError("production validation requires hash-pinned authorization")
    if args.report is None or args.timing_report is not None:
        raise RuntimeError("production validation requires only --report")
    authorization, authorization_hash = validate_authorization(
        root, args.authorization, args.authorization_sha256
    )
    report_path = resolve_input(root, args.report)
    authorized_report = root / authorization["fresh_output"]["report_path"]
    require_exact_path(report_path, authorized_report, "production report")
    observations, evaluation, design, root_projection, signed_frames = (
        run_measurement(
            root,
            baseline,
            contract,
            preservation,
            candidate_path,
            diagnostics,
        )
    )
    candidate_after = file_state(candidate_path)
    baseline_after = file_state(baseline_cad_path)
    original_after = file_state(
        Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
    )
    if candidate_after != candidate_before:
        raise RuntimeError("held candidate changed during read-only validation")
    if baseline_after != baseline_before:
        raise RuntimeError("canonical baseline changed during validation")
    if original_after != original_before:
        raise RuntimeError("timed-out validator changed during validation")
    result = {
        "schema_version": "1.0",
        "iteration_id": original.ITERATION_ID,
        "design_id": original.DESIGN_ID,
        "candidate_tooling_revision": original.TOOLING_REVISION,
        "validator_id": VALIDATOR_ID,
        "validator_revision": VALIDATOR_REVISION,
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": authorization_hash,
        "validator_sha256": sha256_file(Path(__file__)),
        "timed_out_validator_sha256": ORIGINAL_VALIDATOR_SHA256,
        "design_preflight": design,
        "root_projection_preflight": root_projection,
        "signed_frame_preflight": signed_frames,
        "status": evaluation["status"],
        "evaluation": evaluation,
        "observations": observations,
        "execution_diagnostics": diagnostics.report(),
        "deep_release_validation_run": False,
        "visual_approval_status": "PENDING"
        if evaluation["passed"]
        else "NOT_ELIGIBLE",
        "geometry_modified": False,
        "geometry_artifact_created": False,
        "approval_presentation_allowed": evaluation[
            "approval_presentation_allowed"
        ],
        "read_only_guards": {
            "candidate_before": candidate_before,
            "candidate_after": candidate_after,
            "candidate_unchanged": True,
            "canonical_baseline_unchanged": True,
            "timed_out_validator_unchanged": True,
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
        },
    }
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if evaluation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
