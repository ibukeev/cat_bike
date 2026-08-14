# Right eye second-pair neck removal — V9 checkpoint

## Scope

- Preserve both existing right-eye flange pairs in their current locations and geometry.
- Delete only the obsolete lower-head neck/residue beneath the retained second head-side flange.
- Do not mirror, owner-boolean, export STL/G-code, or release for printing.

## Current review files

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-second-pair-neck-removal-review-v9/CAT_HEAD_RIGHT_EYE_SECOND_PAIR_NECK_REMOVAL_REVIEW_V9.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-second-pair-neck-removal-review-v9/CAT_HEAD_RIGHT_EYE_SECOND_PAIR_NECK_REMOVAL_REVIEW_V9.blend`
- Before/after evidence: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-second-pair-neck-removal-review-v9/review/01-v9-before-neck-removal.png` and `02-v9-after-neck-removal.png`
- Numeric results: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-second-pair-neck-removal-review-v9/validation-v9.json`

## Locked decisions and dimensions

- Second eye mating face: `RETAINED__RIGHT_EXISTING_SECOND_EYE__V7__EXACT.Face77`.
- Second head mating face: `RETAINED__RIGHT_EXISTING_SECOND_HEAD__V7__EXACT.Face2`.
- Pair gap remains `0.3000 mm`; interference remains `0.0000 mm^3`.
- No flange translation, rotation, reshaping, hole change, or gap change.
- Removed component only: 65 vertices, 32 faces, bbox `14.16837 x 11.98367 x 5.34364 mm`.

## Validation

- Lower-face connected-component count: 63 before, 62 after.
- Lower-face delta: exactly -65 vertices and -32 faces.
- All four flange fingerprints are unchanged.
- All four flange solids are valid and closed in FreeCAD.
- The saved FCStd archive is valid.
- The inherited revised lower-face OBJ remains a non-watertight/self-intersecting review mesh in FreeCAD; it is intentionally not represented as an exact Part solid and is not print-ready.

## Rejected or unsafe variants

- Relocating either flange pair.
- Rebuilding replacement flanges.
- Keeping the lower-head pole/neck.
- Treating the inherited lower-face mesh as a validated printable solid.

## Regeneration

```bash
blender --background output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend --python source/generate_right_eye_second_pair_neck_removal_review_v9.py
```

## Next physical review

1. Open the V9 FCStd.
2. Confirm the retained second flange pair has not moved.
3. Confirm the lower-head neck/pole beneath the head-side flange is gone.
4. Confirm there is no new cut elsewhere in the lower shell.
5. Keep print release blocked until the inherited lower-face mesh is repaired and the accepted change is integrated into the production owner.
