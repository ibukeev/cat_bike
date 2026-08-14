# Right-eye V10 neck removal + V2 clearance regression fix — V11 checkpoint

## Status and scope

- The user visually accepted the V10 actual outer-neck removal.
- V10 nevertheless regressed the previously approved eye clearance because it rebuilt the lower-face review from V7 and carried the original C046/C048 reinforcement components.
- V11 preserves the accepted V10 lower-face result, removes only those two stale components, and restores the exact user-approved V2 C046/C048 geometry.
- The V9 eye bucket, both flange pairs, upper-head shell, all other reinforcement, rear cassette, C006, and aluminum V0.5-M2 remain frozen.
- This is an isolated right-side review. No production owner Boolean, left mirror, STL, G-code, slicing, ASA printing, or print release was performed.

## Current review files

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.FCStd`
- Blender: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.blend`
- Evidence: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/review/`
- Numeric validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/validation-v11.json`
- Contract: `config/right-eye-neck-removal-clearance-regression-fix-review-v11.json`

## Locked geometry contract

- Preserve the V10 neck-removed lower-face source fingerprint `caaef27fe09c33b557407060a7af0ea665aa0d92f7175ef8c79d1002daca95e5` before replacing stale reinforcement.
- Remove stale C046 only by its locked 6-vertex / 7-face component and bbox `(29.92491, 47.50568, 115.37617)` to `(42.46059, 58.61190, 123.47581) mm`.
- Remove stale C048 only by its locked 6-vertex / 5-face component and bbox `(36.37653, 51.42321, 87.59510)` to `(81.74683, 61.09498, 126.69158) mm`.
- Restore C046 by the accepted V2 rigid translation: `4.2290 mm` along `(0.206134, -0.131130, -0.969698)`.
- Restore C048 by the accepted V2 eye-side trim fraction `0.15`; its far end is preserved exactly.
- Preserve both accepted flange-pair gaps at `0.3000 mm`.

## Validation performed and results

- The accepted V10 actual-neck deletion remains represented by the exact locked 81-vertex / 41-face removed component; the V9-wrongly-deleted 65-vertex / 32-face material remains restored.
- Only two additional lower-face connected components were removed in V11: stale C046 and stale C048. The lower-face delta from V10 is exactly `-12` vertices, `-20` edges, and `-12` faces.
- Restored C046 is closed/manifold and clears the unchanged V9 eye by `4.6063 mm`.
- Restored C048 is closed/manifold and clears the unchanged V9 eye by `4.0317 mm`.
- Neither restored rib intersects the eye; both retain lower-face contact and mutual structural contact.
- All four flange fingerprints are unchanged from V10. Both pair gaps remain `0.3000 mm` with zero interference.
- FreeCAD validates both restored rib meshes as valid (`6` points / `8` facets each).
- The combined lower-face review retains the same inherited FreeCAD aggregate mesh warnings as V10: non-manifold edges, self-intersections, and open boundaries. V11 did not introduce or auto-repair those baseline conditions; production integration remains held.
- The V11 FCStd archive passes ZIP validation.

## Rejected or unsafe variants

- V10 as a combined neck-plus-clearance review is superseded because it resurrected the original C046/C048 positions. Its neck deletion itself is accepted and preserved exactly in V11.
- Do not move the eye or either flange pair to create clearance.
- Do not delete C046 or C048; they remain structural and must retain their V2 owner and mutual contacts.
- Do not auto-repair or Boolean the aggregate lower-face mesh inside this regression-fix review.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_neck_removal_clearance_regression_fix_review_v11.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-neck-removal-upper-head-owner-review-v10/CAT_HEAD_RIGHT_EYE_OUTER_NECK_REMOVAL_UPPER_HEAD_OWNER_REVIEW_V10.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_neck_removal_clearance_regression_fix_review_v11.py
```

The `.FCStd` is assembled from the generated review OBJs through the FreeCAD bridge. It is review geometry, not a production owner file.

## Next physical review

Open the V11 FreeCAD file and check only:

1. The accepted long outer neck is still absent.
2. C046 and C048 no longer collide or crowd the eye; visible gaps should match the previously approved V2 arrangement.
3. Both restored ribs still meet the lower-face structure and each other.
4. Both flange pairs remain in the accepted locations, with no new bridge, pole, shell cut, or exterior protrusion.
