# Right Eye V17 / V9 Skin Repair Anchor Review V1 Checkpoint

Date: 2026-08-15

## Status

This checkpoint records a **review-only exact anchor localization** for the
inherited V9 eye-skin defect inside the frozen V17 right-eye owner. It does not
change, repair, mirror, union, export, slice, or release production geometry.
ASA and G-code release remain held.

The user previously approved the V17 defect-localization view as a useful
visualization. This V1 artifact narrows that accepted defect region to the
exact BREP face and edge needed for a future bounded topology repair.

## Current review artifact

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-repair-anchor-review-v1/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_REPAIR_ANCHOR_REVIEW_V1.FCStd`
- FreeCAD size: `555891` bytes
- FreeCAD SHA-256:
  `427002bb2eb5949234ea4e68b51c4780134ff76bcc94e81b9fba7c035e9405cd`
- Generated validation:
  `../../../../../reports/generated/cat-head-cad-validation/v17-v9-skin-repair-anchor-review-v1/validation-v1.json`
- Validation status: `PASS__EXACT_REVIEW_ANCHORS_GENERATED`

The full frozen V17 context and the true edge-owner faces are hidden by
default so the localized anchors are easy to inspect.

## Frozen source

- V17 STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step`
- Source STEP SHA-256:
  `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Lineage FCStd SHA-256:
  `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`
- Frozen source remains valid, closed, and one solid.
- Source geometry changes in this review: `0`.

## Exact anchors

- Green host face: `Face587`
- Orange diagnostic partner: `Face263`
- Yellow diagnostic partner: `Face400`
- Magenta penetrating edge: `Edge1278`
- Cyan true edge-owner faces: `Face581` and `Face582`
- Imported edge endpoints, millimetres:
  - `(68.118020837, 91.430557092, 173.547905225)`
  - `(68.000558679, 91.415801843, 173.694160718)`
- Edge length: `0.188164144 mm`
- Endpoint-match error: `0.000017177824 mm`
- Host-intersection point:
  `(68.000558679, 91.415801843, 173.694160718)`

`Face587` does not own `Edge1278`; the edge belongs to `Face581/Face582` and
penetrates the host at the marked endpoint. No repair has been performed.

## Proposed repair contract — not yet authorized

The next bounded operation would be a local topological split-and-weld at the
exact anchors above, subject to all of these limits:

- zero vertex motion;
- zero exterior-face motion;
- frozen exterior bounds unchanged within `0.001 mm`;
- total volume delta no greater than `0.001 mm3`;
- one valid, closed, orientable solid after repair;
- zero exact non-adjacent crossing pairs in this V9 defect region;
- V17 flange mating gaps, engagement volumes, root positions, and `1.5 mm`
  root depth unchanged;
- no facet deletion, automatic repair, broad Boolean, or whole-owner remesh;
- the clean second-eye root remains untouched.

This contract is proposed for the next approval gate. It is not authorized by
this checkpoint.

## Rejected or unsafe variants

- deleting output facets;
- automatic mesh healing or broad self-union;
- moving the exterior surface to hide the crossing;
- touching the clean second-eye root;
- mirroring before the one-sided exact repair is validated;
- production union, STL export, slicing, G-code, or ASA printing from this
  review artifact.

## Validation performed

- FreeCAD archive validation: valid, `555891` bytes.
- Generator report: PASS.
- Frozen source hash, validity, closedness, and one-solid state: unchanged.
- Exact anchor identity and endpoint-match tolerance: PASS.
- Python compilation: PASS.
- `tests.automated.test_cat_head_cad_change_control`: 6/6 PASS.
- `tests.automated.test_cat_head_bop_diagnostics`: 1/1 PASS.
- `git diff --check`: PASS.

## Exact regeneration command

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_v17_v9_skin_repair_anchor_review.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v2.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-v9-skin-repair-anchor-review-v1.json
```

The FreeCAD AppRun wrapper can emit GUI/style shutdown warnings and return `1`
after the generator has completed. Accept regeneration only when the FCStd
exists, its archive validates, and the generated JSON reports PASS.

## Next physical/visual review

Open the review FCStd and inspect only this relationship:

1. the short magenta `Edge1278` terminates on and penetrates the green
   `Face587` at the marked corner;
2. the orange/yellow faces provide local crossing context;
3. toggle the hidden cyan `Face581/Face582` group only if edge ownership needs
   confirmation;
4. toggle the hidden frozen V17 context only to orient the defect within the
   eye.

Approval of that relationship authorizes drafting the numeric repair contract,
not the repair itself.
