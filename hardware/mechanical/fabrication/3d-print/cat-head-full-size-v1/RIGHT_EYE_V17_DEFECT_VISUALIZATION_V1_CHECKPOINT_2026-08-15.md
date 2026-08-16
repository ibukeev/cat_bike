# Right Eye V17 Defect Visualization V1 Checkpoint — 2026-08-15

## Status

Review-only visualization generated and independently validated. This work
does not alter, heal, cut, move, fuse, mirror, or replace any production
geometry. It is not an STL, G-code, ASA print release, or repair approval.

## Current review and output files

- FreeCAD review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-defect-visualization-v1/CAT_HEAD_RIGHT_EYE_V17_DEFECT_VISUALIZATION_V1.FCStd`
- Validation report:
  `../../../../../reports/generated/cat-head-cad-validation/v17-defect-visualization-v1/validation-v1.json`
- Generator:
  `source/cad-change-control/generate_v17_eye_defect_visualization.py`
- Approved read-only contract:
  `source/cad-change-control/pilot/read-only-v17-eye-defect-visualization-v1.json`
- Frozen exact V17 source STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step`
- Frozen V17 lineage FCStd:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/CAT_HEAD_RIGHT_EYE_EXACT_OWNER_INTEGRATION_REVIEW_V17.FCStd`

## Accepted decisions and exact review mapping

- The grey translucent object is the unchanged exact V17 right-eye owner.
- `DEFECT_REGION__V9_SKIN` contains:
  - red `Face587`, the shared V9 skin face;
  - orange `Face263`, the first intersecting V9 skin partner;
  - yellow `Face400`, the second intersecting V9 skin partner.
- `DEFECT_REGION__OUTER_INWARD_ROOT` contains:
  - purple `Face72`;
  - cyan `Face489`.
- The second-eye root is clean and must not be modified.
- These are localized defect faces only. They are not selected repair anchors
  and do not authorize an automatic or manual repair.

## Frozen constraints

- Exact V17 source STEP SHA-256:
  `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Exact V17 lineage FCStd SHA-256:
  `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`
- Review FCStd SHA-256:
  `da2199da57e77d3ffe2d33845e65623c1dcc6b31455ef7a43b4cc5675776bbf6`
- Preserve the V17 exterior, both approved mating gaps, approved interior root
  reach, owner positions, and engagement volumes.
- Preserve rear cassette, C006, aluminum V0.5-M2, ears, lower-face owners, and
  every unrelated workstream.

## Validation performed

- Contract preflight with file verification: PASS.
- Generator syntax compilation: PASS.
- `tests.automated.test_cat_head_bop_diagnostics`: PASS.
- Frozen source and lineage SHA-256 before/after comparison: unchanged.
- Source exact STEP: 1178 faces, one solid, valid, and closed.
- Generated document: five exact source-face objects plus one frozen-context
  object; zero geometry changes.
- FreeCAD FCStd validation: valid, 547205 bytes.
- Independent ZIP integrity test: PASS with no errors.
- `GuiDocument.xml` inspection: all view providers, colors, line widths, and
  visibility states persisted.

The extracted FreeCAD 1.1.3 `AppRun python` wrapper returned a non-zero status
during GUI teardown after writing the complete PASS report. The saved artifact
was therefore not accepted on that process result alone; it was independently
reopened/validated and its archive, view providers, and frozen hashes were
checked as listed above.

## Rejected or unsafe variants

- Do not pass the generator `.py` file directly to the FreeCAD GUI command;
  that opens it as an editor document instead of executing it.
- Do not generate the review document without initializing GUI view providers;
  the face colors will not persist in the FCStd.
- Do not heal, delete facets, move faces, fuse overlapping roots, or rebuild the
  clean second-eye root.
- Do not save over either frozen V17 source artifact.
- Do not use this review document as print or repair geometry.

## Exact regeneration command

Run from the repository root. The output paths must not already exist because
the generator deliberately refuses to overwrite review evidence.

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_v17_eye_defect_visualization.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v2.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-defect-visualization-v1.json
```

## Next physical/visual review

1. Open `CAT_HEAD_RIGHT_EYE_V17_DEFECT_VISUALIZATION_V1.FCStd`.
2. Toggle `DEFECT_REGION__V9_SKIN`: confirm the red/orange/yellow overlays are
   confined to the small V9 eye-skin defect region.
3. Toggle `DEFECT_REGION__OUTER_INWARD_ROOT`: confirm the purple/cyan overlays
   are confined to the outer inward-root defect region.
4. Confirm no overlay or proposed work exists at the clean second-eye root.
5. Review only localization. Do not approve repair geometry from this file.

After that visual confirmation, the next controlled step is a separate numeric
repair contract for each localized region followed by a new candidate generated
from frozen V17 sources. V17 itself must remain untouched.
