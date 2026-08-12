# Right Eye Six-Source Rebuild Review V1 Checkpoint — 2026-08-12

## Status

Isolated right-side review is ready for visual inspection. The right eye bucket
was rebuilt from all six required source solids in a deterministic staged-fuse
sequence. This review does not authorize a left mirror, production integration,
STL export, slicing, ASA printing, or fabrication release.

## Review file

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-six-source-rebuild-review-v1/CAT_HEAD_RIGHT_EYE_SIX_SOURCE_REBUILD_REVIEW_V1.FCStd`
- Review objects to leave visible:
  - `PROPOSED__RIGHT_EYE_BUCKET__SIX_SOURCE_POST_CLEARANCE_V1`
  - `PROPOSED__RIGHT_EYE_REAR_CAP__ONE_BODY_V1_ref`
- Numeric ledger: `SIX_SOURCE_REBUILD_CONTRACT_V1`

## Frozen design contract

- Preserve the exact original placement of all six bucket source solids.
- Do not translate the upper rim, add cosmetic bridge blocks, alter the eye
  aperture, move connector axes, or change the removable rear cap.
- Preserve the accepted four rear-cap post-clearance pockets.
- Produce one valid, closed right bucket with no self-intersection.
- Preserve zero volumetric interference with the removable rear cap.
- Preserve the aluminum `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream unchanged.

## Deterministic staged union ledger

| Stage | Result volume |
| --- | ---: |
| Components 01 + 02 | `3501.06 mm3` |
| Components 03 + 04 | `2796.66 mm3` |
| Components 03 + 04 + 06 | `2990.87 mm3` |
| Five-source bucket union | `6453.63 mm3` |
| Six-source bucket union including moved-pair bucket boss | `6529.20 mm3` |
| Final bucket after the unchanged four post-clearance cuts | `6398.56 mm3` |

The staged volumes equal the source-volume sums minus the measured pairwise
overlaps. This avoids the rejected bulk `MultiFuse` behavior that silently
discarded component 04.

## Validation performed

- Final bucket: valid and closed.
- Final bucket: exactly `1` shell and `1` solid.
- Final bucket: `656` faces, `1197` edges, `530` vertices.
- Final bucket volume: `6398.56 mm3`.
- Final bucket bounds: X `27.49..103.84`, Y `50.23..102.80`,
  Z `118.48..178.89 mm`.
- OCCT self-intersection gate: PASS.
- Final bucket to unchanged rear cap: zero volumetric interference.
- Minimum bucket/cap clearance: `0.0239 mm`, the known unrelated near-contact
  retained from the prior review and still held for later fit correction.
- Saved FCStd ZIP integrity: PASS, `1,390,193` bytes at first validation.

## Rejected or unsafe variants

- Rejected: the prior bulk one-body fuse, because it reported one valid solid
  while retaining `0.00 mm3` of required component 04.
- Rejected: global `+0.5 mm` and diagonal `+0.35 mm` rim translations because
  they changed the intended exterior placement.
- Rejected: visible or tucked axis-aligned bridge blocks because they created
  artifacts or still left multiple solids.
- Do not use the prior structural-root V1 file as production source.

## Regeneration

The frozen connected-component inputs are regenerated with:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
```

The exact staged FreeCAD Boolean history is preserved parametrically in the
review FCStd. No arbitrary Python or macro was used for the CAD rebuild.

## Next physical review

1. Open the review file and leave only the two named review objects visible.
2. Orbit around the upper eye rim and confirm there is no floating strip or
   visible hole between the rim and the main bucket.
3. Hide the rear cap and inspect the inside of the bucket. Confirm the upper
   rim is rooted continuously and the four post-clearance pockets remain local.
4. Show the cap again and confirm its two connector regions and four posts have
   not moved.
5. Approve or reject this right-side rebuild before any mirror or integration.

