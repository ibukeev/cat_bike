# Right eye outer-neck removal / upper-head owner — V10 checkpoint

## Scope

- Correct rejected V9 by rebuilding the review from frozen V7 geometry.
- Remove only the actual long lower-face neck touching the retained outer head-side flange.
- Keep the existing outer flange pair at its accepted coordinates; the head-side flange is directly supported by and assigned to the upper-head shell.
- Restore and preserve the second/lower flange pair material that V9 deleted by mistake.
- Do not add a bridge, pole, replacement flange, owner Boolean, mirror, STL, G-code, or print release.

## Current review files

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-neck-removal-upper-head-owner-review-v10/CAT_HEAD_RIGHT_EYE_OUTER_NECK_REMOVAL_UPPER_HEAD_OWNER_REVIEW_V10.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-neck-removal-upper-head-owner-review-v10/CAT_HEAD_RIGHT_EYE_OUTER_NECK_REMOVAL_UPPER_HEAD_OWNER_REVIEW_V10.blend`
- Evidence: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-neck-removal-upper-head-owner-review-v10/review/`
- Numeric results: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-neck-removal-upper-head-owner-review-v10/validation-v10.json`

## Structured anchor and numeric contract

- User-selected reference object: `RETAINED__OUTER_HEAD__UNCHANGED_V9__EXACT`.
- Selected flange bounding box: X `100.67–106.82 mm`, Y `79.88–91.44 mm`, Z `140.13–153.75 mm`.
- Actual removed neck: 81 vertices / 41 faces; bbox min `(99.2661, 79.8783, 117.5763)`, max `(105.8241, 90.5880, 153.8223)`.
- Removed-neck distance to the selected outer head flange: `0.0000 mm`.
- V9-wrongly-deleted material restored: 65 vertices / 32 faces.
- Selected outer head flange overlap with upper head: `122.5160 mm^3`.
- Selected outer head flange overlap with corrected lower face: `0.0000 mm^3`.
- Outer pair gap: `0.3000 mm`; interference: `0.0000 mm^3`.
- Second pair gap: `0.3000 mm`; interference: `0.0000 mm^3`.
- No flange translation, rotation, reshaping, hole, or gap change.

## Validation

- Lower-face connected-component count: 63 before, 62 after.
- Lower-face delta: exactly -81 vertices and -41 faces.
- The 65-vertex / 32-face second-pair component is present again.
- All four flange fingerprints match frozen V7.
- All four exact retained flange objects are valid closed solids in FreeCAD.
- FreeCAD confirms both pair distances are `0.3000 mm`.
- Saved FCStd archive is valid (`298890` bytes).
- The inherited corrected lower-face mesh remains multi-component review geometry and is not print-ready.

## Rejected or unsafe variants

- V9: deleted the wrong 65-vertex / 32-face component and left the actual long outer neck.
- Moving either flange pair: unnecessary; the outer head flange already has a direct upper-head root.
- Adding another neck, pole, bridge, or replacement flange.
- Treating owner assignment or overlap validation as a production owner Boolean.

## Regeneration

```bash
blender --background output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend --python source/generate_right_eye_outer_neck_removal_upper_head_owner_review_v10.py
```

## Next physical review

Open the V10 FCStd and verify only these points:

1. The long lower-face neck to the outer head flange is gone.
2. The outer flange pair remains in its accepted position against the upper head.
3. The second/lower flange pair and its nearby material are restored and unchanged.
4. No new pole, bridge, flange, shell cut, or external protrusion was introduced.
