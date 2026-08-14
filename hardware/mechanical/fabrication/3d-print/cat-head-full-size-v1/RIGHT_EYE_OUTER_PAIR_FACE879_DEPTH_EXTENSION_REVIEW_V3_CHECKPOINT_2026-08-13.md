# Right Eye Outer Pair Face879 Depth Extension V3 — 2026-08-13

## Status

HS-11 has a new isolated right outer-pair proposal ready for visual review.
The V2 `22 x 8 mm` rectangular-base concept is rejected and is absent from
this review. V3 changes only the existing owner-end section: the eye-side
`Face879` and the corresponding head-side end face each extend `8.0 mm` into
their own owner. The lower flange pair is unchanged. No left mirror, STL,
G-code, or print release exists.

## Review files

- Exact FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-face879-depth-extension-review-v3/CAT_HEAD_RIGHT_EYE_OUTER_PAIR_FACE879_DEPTH_EXTENSION_REVIEW_V3.FCStd`
- Blender context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-face879-depth-extension-review-v3/CAT_HEAD_RIGHT_EYE_OUTER_PAIR_FACE879_DEPTH_EXTENSION_REVIEW_V3.blend`
- Numeric contract:
  `config/right-eye-outer-pair-face879-depth-extension-review-v3.json`
- Generated and exact validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-face879-depth-extension-review-v3/validation-v3.json` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-face879-depth-extension-review-v3/freecad-validation-v3.json`

## Locked construction

- User-selected owner/face: `FROZEN__RIGHT_EYE_BUCKET_V9_V2__SOLID.Face879`.
- Measured face: `28.8 mm2`, centroid `(99.28, 87.91, 146.48)`, normal
  `(-0.3637, 0.9097, -0.2003)`.
- Existing flange cross-section/depth: `12.0 x 2.4 mm`, `8.0 mm` deep.
- Added owner-side depth: `8.0 mm`; resulting owner-side depth: `16.0 mm`.
- Hidden Boolean overlap: `0.4 mm`.
- Apply the same `8.0 mm` owner-side extension to the corresponding outer
  head flange, along its opposite owner direction.
- Preserve hole axes, mating faces, and `0.3000 mm` pair clearance.
- Do not change the lower pair, C046/C048, shell panels, or eye placement.

## Validation performed

- Eye exact owner result: valid, closed, one solid, `918` faces,
  `6880.00 mm3`.
- Head exact flange result: valid, closed, one solid, `105` faces,
  `913.32 mm3`.
- Eye/head exact pair: no interference; minimum clearance `0.3000 mm`.
- Eye/head extension solids: zero mutual overlap.
- Owner engagement: `11.520 / 2.337 mm3` for eye/head respectively.
- Both generated extension solids are closed and manifold (`6` faces,
  `241.92 mm3` each).
- V2 rectangular base is absent; lower-pair fingerprints are unchanged.

## Rejected or unsafe variants

- V1 tapered roots: rejected for exterior protrusion.
- V2 broad `22 x 8 mm` rectangular bases: rejected by the user as unnecessary
  and geometrically intrusive.
- Draft V3 directions across the mating gap: rejected before handoff because
  they collided. The saved V3 runs each extension into its own owner.
- Production integration, mirror, slicing, and printing remain held pending
  visual approval.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_outer_pair_face879_depth_extension_review_v3.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_outer_pair_face879_depth_extension_review_v3.py
```

The FreeCAD review is then rebuilt from the generated OBJ evidence using
mesh-to-solid conversion and exact fuses for the eye owner and head flange.

## Next physical review

Open the V3 FreeCAD review and inspect the two visible exact objects:

1. The old V2 broad rectangular base is absent.
2. The eye-side extension is a direct continuation of `Face879`, not a new
   external block, wedge, or neck.
3. The corresponding head-side flange extends into the head owner by the same
   amount.
4. Neither extension protrudes through the exterior shell.
5. The two mating members retain their original location and gap.

After explicit approval, integrate only these exact V3 changes into copied
right-side production owners, revalidate the complete right side, then mirror
and validate the left side separately.
