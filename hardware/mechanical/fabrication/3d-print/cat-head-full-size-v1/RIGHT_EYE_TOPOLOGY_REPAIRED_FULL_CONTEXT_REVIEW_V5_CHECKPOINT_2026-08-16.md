# Right Eye Topology-Repaired Full Context Review V5 Checkpoint — 2026-08-16

## Status

The hash-pinned, fully topology-repaired V4 right-eye STEP has been substituted
at zero transform into a deterministic copy of the frozen V18 one-sided
assembly context. The replacement is one valid closed `1178`-face solid. Every
previously approved mating gap and C046/C048 clearance is numerically unchanged.

This is a review-only one-sided assembly. It is not mirrored, production-unioned,
exported to STL, sliced, converted to G-code, or released for ASA printing. The
frozen V18 review and V4 STEP were opened read-only and were not overwritten.

## Current review and output files

- Current full-context review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-topology-repaired-full-context-review-v5/CAT_HEAD_RIGHT_EYE_TOPOLOGY_REPAIRED_FULL_CONTEXT_REVIEW_V5.FCStd`
- V5 validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-topology-repaired-full-context-review-v5/validation-v5.json`
- Exact repaired eye input:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/right_eye_v17_full_topology_repaired_review_v4.step`
- Frozen context input:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-full-context-review-v18/CAT_HEAD_RIGHT_EYE_FULL_CONTEXT_REVIEW_V18.FCStd`
- Deterministic generator and contract:
  `source/cad-change-control/generate_right_eye_topology_repaired_full_context_review.py` and
  `source/cad-change-control/pilot/right-eye-topology-repaired-full-context-review-v5.json`

## Artifact hashes

- V5 review FCStd SHA-256:
  `d58244f0073115ddae4e84b49a5ce0466191c0e7752f8d7fb854f6d6bc6396c0`
- V5 validation SHA-256:
  `f981b0f6e7a7aa3c7a11b699ac4994fd39ff0709b0aad42efa090d7afc9fc8df`
- Repaired V4 STEP SHA-256:
  `1ae9408d908edc9cf7e8d5ac2dd0c5bdd8a36f0f184d2bab3e05dafa1ef41258`
- Frozen V18 FCStd SHA-256:
  `8f5b3d65cdd635202d9986703e214e12d39d05c62eca4b96df9247866ba032c6`
- Frozen V18 validation SHA-256:
  `907c0e2dd7d66ffebaa608441e03c7c0dec217496a7aaf00e34564c39da86e70`

## Accepted decisions and dimensions

- Replace only the V18 exact-eye object with the repaired V4 STEP; retain all
  other V18 Part and Mesh objects at their original placements.
- The substitution uses zero transform and creates no new design geometry.
- Preserve the two approved head-side mating relationships and their actual
  exact gaps rather than rounding them to nominal values.
- Preserve the C046 and C048 minimum-clearance contract of at least `4.0 mm`.
- The topology repairs preserve all exterior bounds. Their maximum vertex
  displacement relative to the frozen V18 eye is `0.000004075425 mm`.
- The defective-versus-repaired solid volume comparison changes by
  `-0.006628559 mm3`; this is within the `0.01 mm3` evidence envelope and does
  not alter any exterior bound or measured neighbor clearance.

## Validation performed and results

- Input SHA-256 contract checks: PASS.
- Frozen context objects copied: `10/10`; only the eye object was substituted.
- Replacement eye: valid, closed, one solid, `1178` faces.
- Exterior bounds delta: zero on all six bounds.
- Maximum bidirectional vertex delta: `0.000004075425 mm`.
- Outer-head mating gap:
  - frozen V18: `0.299991616761 mm`;
  - repaired V5: `0.299991616761 mm`;
  - delta: `0.0 mm`.
- Lower-head mating gap:
  - frozen V18: `0.299987743725 mm`;
  - repaired V5: `0.299987743725 mm`;
  - delta: `0.0 mm`.
- C046 clearance:
  - frozen V18: `4.606316486735 mm`;
  - repaired V5: `4.606316486735 mm`;
  - delta: `0.0 mm`.
- C048 clearance:
  - frozen V18: `4.031667908786 mm`;
  - repaired V5: `4.031667908786 mm`;
  - delta: `0.0 mm`.
- FCStd archive integrity: PASS; all compressed members tested without error.
- Overall status: `PASS__REVIEW_ONLY_CONTEXT`.

## Rejected or unsafe variants

- The first execution used an over-strict nominal `0.300000 +/- 0.000010 mm`
  gate and an invalid cross-topology volume tolerance. It stopped before saving
  an FCStd. Its validation-only evidence was preserved under
  `/tmp/right-eye-topology-repaired-full-context-review-v5-overstrict-contract-20260816T0300`.
- Do not alter geometry to force the exact frozen gaps to round to `0.300000 mm`;
  the replacement already preserves them exactly.
- Do not compare volume across defective and repaired topology as if it were a
  placement or exterior-shape change; bounds, vertices, and neighbor distances
  are the controlling preservation evidence.
- Do not use frozen V18 as the current topology-clean eye context.
- Do not mirror, production-union, export STL, slice, generate G-code, or print
  from V5 without the next explicit release-stage approval and remaining gates.

## Exact regeneration command

Run from the repository root. The generator refuses to overwrite existing
review evidence.

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_eye_topology_repaired_full_context_review.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-topology-repaired-full-context-review-v5.json
```

## Next physical/visual review

No new face selection is required. If a visual check is desired, open the V5
FCStd and confirm that the repaired right eye occupies the same position as in
V18 and that no new external protrusion appears around either head-side flange.
The next independent design bucket is not a further eye-topology edit; it is
the remaining approved-context owner/integration work before bilateral mirror
or production export can be considered.
