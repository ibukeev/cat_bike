# Right Eye V17 Full Topology Repair STEP Review V4 Checkpoint — 2026-08-16

## Status

The remaining outer-eye inward-root topology defect in the V2 repaired owner
has been corrected with one bounded topology-only operation. The V3 proposal
and its V4 exact STEP round trip pass all contracted solid, preservation, and
round-trip gates. A full exact pairwise face audit of the V4 STEP finds zero
non-adjacent crossing pairs.

This is a one-sided review owner. It is not mirrored, substituted into the
complete head, production-unioned, exported to STL, sliced, converted to
G-code, or released for ASA printing. The frozen V17 and V2 evidence were not
overwritten.

## Current review and output files

- Current review FCStd:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/CAT_HEAD_RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIR_STEP_REVIEW_V4.FCStd`
- Current exact review STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/right_eye_v17_full_topology_repaired_review_v4.step`
- V4 round-trip validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/validation-v4.json`
- Isolated V3 repair proposal and validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-outer-root-topology-repair-review-v3/CAT_HEAD_RIGHT_EYE_V17_OUTER_ROOT_TOPOLOGY_REPAIR_REVIEW_V3.FCStd` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-outer-root-topology-repair-review-v3/validation-v3.json`
- Exact all-face audit:
  `../../../../../reports/generated/cat-head-cad-validation/v17-full-topology-repaired-step-audit-v4/face-pairs-v4.json`
- Source scripts and contracts:
  `source/cad-change-control/analyze_v17_outer_root_topology.py`,
  `source/cad-change-control/generate_v17_outer_root_topology_repair_review.py`,
  `source/cad-change-control/export_v17_full_topology_repair_step_review.py`,
  `source/cad-change-control/pilot/right-eye-v17-outer-root-topology-repair-review-v3.json`,
  `source/cad-change-control/pilot/right-eye-v17-full-topology-repair-step-review-v4.json`, and
  `source/cad-change-control/pilot/read-only-v17-full-topology-repaired-step-audit-v4.json`.

## Artifact hashes

- V4 exact STEP SHA-256:
  `1ae9408d908edc9cf7e8d5ac2dd0c5bdd8a36f0f184d2bab3e05dafa1ef41258`
- V4 review FCStd SHA-256:
  `5132998db827fe45e9a4106ad646a4abc0348ce588afba10ed89d0c2e2f2ddf6`
- V4 validation SHA-256:
  `8f0f6e29774e8e6278b2fe6e05876844707876779db825102b69273750284bb1`
- V3 proposal FCStd SHA-256:
  `d486156de9fbf36683d87566d6315de599fcfa76a58dfbdf0ad223d43e4b7792`
- V3 validation SHA-256:
  `0bc3661add067491883c7b46568781557dbb9587572701836e16e94ee687c412`
- Exact V4 all-face audit SHA-256:
  `02ae813bfb742a63b0c1ced5108ce304151e6b236bccecfdfa1bc90d1aee2d99`
- Frozen V2 input STEP SHA-256:
  `18b8b11ea2b09b4bf306060ccf2c86d9e09feaca72f158cde9b6f187d720fc98`

## Accepted decisions and dimensions

- The defect was a microscopic folded sliver/T-junction in the outer-eye
  inward-root region, not a placement or flange-design error.
- The repair collapses the offending vertex from
  `(96.135855346680, 82.503360473633, 146.632829467770) mm` to its exact
  projection on the host edge at
  `(96.135858367255, 82.503363207665, 146.632829366393) mm`.
- Maximum source-vertex movement is `0.000004075424 mm`.
- Five defective source faces are replaced by four faces sharing exact edges;
  the owner changes from `1179` to `1178` faces.
- All `1174` untouched source faces are retained exactly.
- Exterior bounds, approved mating geometry, the clean second-eye root, the
  `1.5 mm` approved interior reach, rear cassette, C006, aluminum V0.5-M2,
  ears, lower-face owners, and unrelated workstreams remain unchanged.

## Validation performed

- V3 candidate: one valid closed solid, `1178` faces.
- V3 local BOP audit: zero diagnostics in the rebuilt patch.
- V3 preservation: `1174/1174` untouched faces retained; bounds unchanged.
- V3 volume delta: `0.000004607219 mm3`.
- V4 STEP re-import: one valid closed solid, `1178` faces.
- V4 bounds delta: zero on all six bounds.
- V4 absolute volume round-trip delta: `9.09e-11 mm3`.
- V4 maximum vertex round-trip error: `7.43e-12 mm`.
- Exact all-face audit:
  - face count `1178`;
  - bounding-box candidates `19133`;
  - touching candidates `7260`;
  - raw diagnostic pairs `66`;
  - global OCCT diagnostic messages `16`;
  - non-adjacent crossing pairs `0`.
- The raw diagnostics all share at least one topological/coordinate vertex and
  are adjacency checks, not disconnected-face crossings. No automatic healing
  or source-document save was used.

## Rejected or unsafe variants

- Do not relocate either flange or alter its approved mating leaf to repair
  this topology defect.
- Do not delete output facets, broadly fuse the overlapping historical copies,
  run automatic healing, or modify the clean second-eye root.
- Do not reuse the V2 owner as the current topology candidate; it retains the
  now-repaired `Face72 / Face489` defect and is evidence only.
- Do not mirror, integrate, export STL, slice, generate G-code, or release ASA
  from V3/V4 without the next explicit change-control approval.

## Exact regeneration commands

Run from the repository root. The generators and auditor refuse to overwrite
existing evidence directories/files.

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_v17_outer_root_topology_repair_review.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-v17-outer-root-topology-repair-review-v3.json

env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/export_v17_full_topology_repair_step_review.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-v17-full-topology-repair-step-review-v4.json

env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/localize_freecad_face_pair_intersections.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v3.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-full-topology-repaired-step-audit-v4.json \
  --report reports/generated/cat-head-cad-validation/v17-full-topology-repaired-step-audit-v4/face-pairs-v4.json
```

## Next physical/visual review

No additional face selection is needed for this closed topology bucket. If the
V4 owner is adopted for the next stage, open the V4 FCStd and confirm only that
the outer-eye flange root looks unchanged at normal assembly scale. The next
separate change-control stage is one-sided owner substitution/full-context
validation before any bilateral mirror or production export.
