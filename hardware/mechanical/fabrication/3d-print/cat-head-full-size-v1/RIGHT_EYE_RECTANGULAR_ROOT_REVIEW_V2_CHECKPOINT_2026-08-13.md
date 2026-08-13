# Right Eye Rectangular Internal-Base Review V2 — 2026-08-13

## Status

HS-11 has a validated **right-side V2 proposal ready for visual review**.
V1 is rejected because its `16 x 12 mm` tapered roots protruded outside the
shell. V2 preserves both accepted V3 flanges and adds only a simple straight
rectangular internal base to each one. No copied owner has been Booleaned, no
left mirror exists, and no STL, G-code, or print release exists.

## Review files

- FreeCAD exact review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-rectangular-root-review-v2/CAT_HEAD_RIGHT_EYE_RECTANGULAR_ROOT_REVIEW_V2.FCStd`
- Blender context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-rectangular-root-review-v2/CAT_HEAD_RIGHT_EYE_RECTANGULAR_ROOT_REVIEW_V2.blend`
- Validation and evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-rectangular-root-review-v2/validation-v2.json` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-rectangular-root-review-v2/review/`
- Numeric contract:
  `config/right-eye-rectangular-root-review-v2.json`

## Locked V2 construction

- Accepted eye flange is unchanged: `12 x 8 x 2.4 mm`, with its existing
  `2.8 mm` M2.5 clearance bore.
- Added base is straight rectangular, not tapered or wedge-shaped.
- Base footprint: `22 x 8 mm`.
- Base embeds `1.6 mm` into the receiving V9 eye body and overlaps the
  accepted flange by `0.4 mm`.
- The additional `10 mm` length extends to one side along the receiving
  interior surface, chosen by maximum exact owner engagement; it is not
  centered across the shell edge.
- Both approved mating axes, bore centers, and `0.3000 mm` pair gaps remain
  fixed.
- C048 keeps the prior `0.8 mm` localized far-end root; this review does not
  redesign it.

## Validation performed

- Outer base to V9 eye owner overlap: `59.1390 mm3` exact OCCT.
- Lower base to V9 eye owner overlap: `60.9575 mm3` exact OCCT.
- Outer and lower flange-to-head mating gaps: `0.3000 / 0.3000 mm`.
- Both exact accepted-flange-plus-base fuses are valid, one-solid, and
  self-intersection-free (`181 / 194` faces respectively).
- V9 bucket-to-rear-cap service gap remains `0.0239 mm`.
- FreeCAD archive validates as an intact `1,858,532` byte FCStd.
- No approved flange fingerprint changed in the generated Blender evidence.

## Rejected or unsafe variants

- V1 `16 x 12 mm` tapered roots: rejected for visible exterior protrusion.
- A same-footprint `12 x 8 x 0.8 mm` base: rejected because exact owner
  engagement was only about `17.25 mm3`.
- Centered `22 x 8 mm` base: rejected because it extends unnecessarily toward
  both sides and produced unreliable non-manifold Blender unions.
- Whole-owner Boolean, bilateral mirror, export, slicing, and printing remain
  held until this isolated right-side form is explicitly approved.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_internal_root_embed_review_v1.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_internal_root_embed_review_v1.py -- hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-eye-rectangular-root-review-v2.json
```

The FreeCAD file is rebuilt from the generated OBJ evidence with mesh-to-solid
conversion and exact fuses between each untouched accepted flange and its V2
base.

## Next physical review

Open the V2 FreeCAD review and inspect only the two objects ending in
`RECTANGULAR_BASE_V2__EXACT` together with the frozen V9 eye and shell context:

1. The mating faces and holes still match the two frozen head-side flanges.
2. The added bases are plain rectangular blocks with no taper or neck.
3. From the exterior, neither base projects past the shell/eye skin.
4. From the interior, each base has a broad continuous landing on the eye
   owner and no loose strip or disconnected component.

After explicit approval, fuse these features into copied right-side owners,
repeat exact exterior/clearance checks, then exact-mirror and validate the
left side.
