# Right-eye V17 deep OCCT localization checkpoint — 2026-08-15

Status: **localized; geometry unchanged; structural ASA release remains held**.

This checkpoint supersedes any earlier interpretation that the V17 right-eye
STEP is self-intersection-free. It is a read-only diagnostic checkpoint, not a
geometry approval.

## Frozen target and lineage

- Exact target STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step`
  - SHA-256: `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Protected V17 lineage document:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/CAT_HEAD_RIGHT_EYE_EXACT_OWNER_INTEGRATION_REVIEW_V17.FCStd`
  - SHA-256: `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`
- Baseline manifest:
  `source/cad-change-control/pilot/baseline-manifest-v2.json`
- Read-only contract:
  `source/cad-change-control/pilot/read-only-v17-eye-self-intersection-localization-v1.json`

No target or lineage CAD file was saved, healed, cut, fused, or exported by
this work.

## Current reports

Generated reports remain under the ignored validation-report tree:

- Stage/subshape report:
  `reports/generated/cat-head-cad-validation/v17-self-intersection-localization-v1/report-v1.json`
  - SHA-256: `f61791a49e8a5db8e6d1861a15276df341c44ec8e4777cd40d7fcb09559c9e65`
- Exact STEP face-pair report:
  `reports/generated/cat-head-cad-validation/v17-self-intersection-localization-v1/face-pairs-v1.json`
  - SHA-256: `441ad94e5534ba06c3633c7f336b8241f3a2a1ae57b99a2ccf98b822d23a5716`

## Validation performed and results

FreeCAD 1.1.3 loaded the pinned exact STEP and reported:

- 1 solid and 1 shell;
- 1,178 faces;
- 38 global deep OCCT self-intersection diagnostics;
- 19,091 face pairs after bounding-box pruning;
- 7,263 touching/contact candidates;
- 73 diagnostic face pairs.

The 73 raw pair diagnostics are not 73 independent design defects:

- 37 pairs share two vertices;
- 33 pairs share one vertex;
- 3 pairs share no vertices and are the true non-adjacent defect pairs.

Exact non-adjacent pairs in the imported STEP:

| Pair | Owner classification | Bounds summary | Decision |
|---|---|---|---|
| `Face587` / `Face263` | V9 eye bucket / V9 eye bucket | Around X 68.00–69.94, Y 87.78–91.98, Z 171.96–174.50 mm | Repair inherited V9 topology only after a numeric contract is frozen. |
| `Face587` / `Face400` | V9 eye bucket / V9 eye bucket | Around X 68.00–69.94, Y 87.78–92.08, Z 172.72–174.50 mm | Same inherited V9 defect region; treat with the first pair as one localized repair region. |
| `Face72` / `Face489` | Outer-eye inward-root region | Around X 96.13–100.62, Y 78.25–84.22, Z 142.14–146.92 mm | Rebuild only the outer-eye root topology while preserving the approved mating leaf and owner position. |

The saved FCStd stage audit additionally established:

- the inherited V9 eye stage already contains 20 deep OCCT diagnostics;
- the outer-eye root stage contains 8 diagnostics;
- the second-eye root stage contains 0 diagnostics.

Therefore the second-eye root is clean and is explicitly outside the repair
scope. Blind bilateral/root-wide rebuilding is prohibited.

## Accepted constraints and dimensions

- Preserve all approved exterior coordinates and eye-owner positions.
- Preserve both approved mating gaps at 0.29 mm.
- Preserve the approved 1.5 mm interior root reach.
- Preserve engagement-volume targets: 127.2767 mm3 outer and 92.6241 mm3 second.
- Preserve rear cassette, C006, aluminum V0.5-M2, and HS-11 scope.
- The repair acceptance target is zero exact non-adjacent crossing pairs and
  zero deep OCCT self-intersection diagnostics in the final exact STEP.
- Final owner must remain one closed, orientable OCCT solid.

## Rejected or unsafe variants

- Do not run automatic healing on the production owner.
- Do not delete output facets to make the checker pass.
- Do not rebuild or move the clean second-eye root.
- Do not replace both roots with duplicated, completely overlapping flange
  bodies.
- Do not treat the generated reports or this checkpoint as print release.

## Exact regeneration commands

From the repository root, with the verified FreeCAD 1.1.3 AppImage extracted
at `/tmp/freecad-1.1.3-extract/squashfs-root`:

```bash
python3 -m unittest \
  tests.automated.test_cat_head_bop_diagnostics \
  tests.automated.test_cat_head_cad_change_control

env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/localize_freecad_self_intersections.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v2.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-self-intersection-localization-v1.json \
  --report reports/generated/cat-head-cad-validation/v17-self-intersection-localization-v1/report-v1.json

env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/localize_freecad_face_pair_intersections.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v2.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-self-intersection-localization-v1.json \
  --report reports/generated/cat-head-cad-validation/v17-self-intersection-localization-v1/face-pairs-v1.json
```

The manifest is an argument to the checked-in Python scripts. It must not be
passed directly to `FreeCAD` or `AppRun`.

## Next review and implementation steps

1. Create a read-only review document that highlights only the two V9 defect
   faces/region and the outer-root defect pair in full eye context.
2. Freeze one numeric repair contract per localized region. No whole-eye or
   second-root modification is permitted.
3. Generate a new candidate from the frozen V17 sources; never overwrite V17.
4. Re-run deep OCCT validation, exact pair localization, source-retention,
   exterior-deviation, mating-gap, root-reach, and engagement checks.
5. Present the clean candidate in full head context for visual approval before
   it can enter a production-owner union or slicer project.
