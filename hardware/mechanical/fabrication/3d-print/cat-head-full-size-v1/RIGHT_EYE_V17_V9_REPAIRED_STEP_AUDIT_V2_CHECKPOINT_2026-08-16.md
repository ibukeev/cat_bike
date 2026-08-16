# Right Eye V17/V9 Repaired STEP Audit V2 Checkpoint — 2026-08-16

## Status

The approved bounded V9-skin topology repair was exported to a new exact
review-only STEP, re-imported, and audited. All STEP round-trip gates pass.
Both former V9 non-adjacent defect pairs are gone. The only remaining
non-adjacent crossing is the already protected outer-inward-root pair
`Face72 / Face489`.

This is not a mirrored owner, production union, STL, G-code, slicer source, or
ASA print release. The frozen V17 source was not overwritten.

## Current review and output files

- Repaired review STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/right_eye_v17_v9_skin_topology_repaired_review_v2.step`
- STEP round-trip review FCStd:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_STEP_REVIEW_V2.FCStd`
- STEP validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/validation-v2.json`
- Exact face-pair audit:
  `../../../../../reports/generated/cat-head-cad-validation/v17-v9-repaired-step-audit-v2/face-pairs-v2.json`
- Exporter and contracts:
  `source/cad-change-control/export_v17_v9_skin_topology_repair_step_review.py`,
  `source/cad-change-control/pilot/right-eye-v17-v9-skin-topology-repair-step-review-v2.json`,
  `source/cad-change-control/pilot/baseline-manifest-v3.json`, and
  `source/cad-change-control/pilot/read-only-v17-v9-repaired-step-audit-v2.json`.

## Artifact hashes

- Repaired review STEP SHA-256:
  `18b8b11ea2b09b4bf306060ccf2c86d9e09feaca72f158cde9b6f187d720fc98`
- STEP round-trip FCStd SHA-256:
  `39ae92d158e23c0c81dbe33a492c7005da5898bd8f4ff9b570f4dd40b870c6de`
- STEP validation SHA-256:
  `21f2706bc602ed75b6f48352e3a2311bc5af861bfef97566a6785f05eba32b67`
- Exact face-pair audit SHA-256:
  `02af83763cbd9135124915b92fb47e2e1fef3020ea56746f8b22ae287685c608`
- Frozen V17 source STEP SHA-256:
  `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Frozen V17 lineage FCStd SHA-256:
  `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`

## Accepted decisions and dimensions

- The V9 repair preserves every approved exact anchor and all exterior vertex
  coordinates; it changes topology only.
- The exact review STEP remains one valid closed solid with `1179` faces,
  unchanged bounds, `7269.553009 mm3` volume, and maximum STEP round-trip
  vertex error `8.75e-12 mm`.
- The former V9 defect pairs `Face587 / Face263` and `Face587 / Face400` are
  absent after the repair.
- The one remaining non-adjacent pair is `Face72 / Face489`, localized entirely
  to the outer-eye inward-root region. It is a separate repair bucket.
- Preserve the clean second-eye root, both approved mating positions and gaps,
  the `1.5 mm` approved interior root reach, owner engagement, rear cassette,
  C006, aluminum V0.5-M2, ears, lower-face owners, and all unrelated sources.

## Validation performed

- Hash-pinned export contract and manifest validation: PASS.
- Repaired candidate: one solid, valid, closed, `1179` faces.
- STEP re-import: one solid, valid, closed, `1179` faces.
- Bounds delta: zero on all six bounds.
- Absolute volume round-trip delta: `1.38e-10 mm3`.
- Maximum vertex round-trip error: `8.75e-12 mm`.
- Exact pairwise audit:
  - face count `1179`;
  - bounding-box candidates `19154`;
  - touching candidates `7272`;
  - raw diagnostic pairs `69`;
  - global OCCT diagnostic messages `24`;
  - non-adjacent defect pairs `1`: `Face72 / Face489`.
- No automatic healing and no source document save occurred during the audit.

## Rejected or unsafe variants

- Three interrupted partial V2 export directories were moved outside the
  repository to `/tmp`; none is an accepted artifact.
- Do not use the old frozen V17 STEP as if its V9 skin were repaired.
- Do not delete facets, run broad automatic healing, fuse the two complete
  outer-root copies, move the mating leaf, or modify the clean second-eye root.
- Do not mirror, integrate, export STL, slice, generate G-code, or release ASA
  from this V2 review.

## Exact regeneration commands

Run from the repository root. Both workflows refuse to overwrite existing
evidence.

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/export_v17_v9_skin_topology_repair_step_review.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-v17-v9-skin-topology-repair-step-review-v2.json

env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/localize_freecad_face_pair_intersections.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v3.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-v9-repaired-step-audit-v2.json \
  --report reports/generated/cat-head-cad-validation/v17-v9-repaired-step-audit-v2/face-pairs-v2.json
```

## Next physical/visual review

No user action is required for this checkpoint. Continue with an isolated,
numeric, topology-only repair contract for outer-root `Face72 / Face489`.
Generate a new one-side review candidate and require zero non-adjacent crossing
pairs, unchanged exterior coordinates and mating geometry, positive root
engagement, and no change to any protected workstream before asking for visual
approval.
