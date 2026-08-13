# Right Eye Internal Root Embed Review V1 — 2026-08-13

## Status

HS-11 has a validated **right-side proposal ready for visual review**. The
proposal changes only hidden owner-side roots. It does not move or reshape any
approved mating tab, mating face, bore center, bore axis, shell/eye exterior,
or the `0.3000 mm` flange-pair gaps. No owner Boolean, left mirror, STL,
G-code, or print release has occurred.

## Review files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-internal-root-embed-review-v1/CAT_HEAD_RIGHT_EYE_INTERNAL_ROOT_EMBED_REVIEW_V1.FCStd`
- Blender context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-internal-root-embed-review-v1/CAT_HEAD_RIGHT_EYE_INTERNAL_ROOT_EMBED_REVIEW_V1.blend`
- Validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-internal-root-embed-review-v1/validation-v1.json`
- Evidence renders:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-internal-root-embed-review-v1/review/`
- Numeric contract:
  `config/right-eye-internal-root-embed-review-v1.json`

## Accepted inputs preserved

- Four right V3 flange locations, axes, mating faces, `2.8 mm` bores, and
  `0.3000 mm` pair gaps.
- C046 V2 rigid offset and `4.6063 mm` eye clearance.
- C048 V2 eye-side trim and `4.0317 mm` eye clearance.
- V9 bucket and separate rear cap; cap service gap remains `0.0239 mm`.
- V10 exterior, C006, aluminum V0.5-M2, and the complete left side.

## Proposed dimensions

- Eye-flange hidden owner embed: `0.8 mm`.
- Overlap with each accepted eye flange: `0.4 mm`.
- Root footprint: `16 x 12 mm`, retaining the existing `2.8 mm` bore.
- C048 root: localized to the far-end `25%` of side face 3, `0.8 mm`
  inward along `(-0.565750, -0.428613, -0.704427)`, with `0.4 mm`
  overlap into the accepted rib.

## Validation performed

- Blender:
  - eye-root owner overlaps: `28.7707` and `28.8000 mm3`;
  - both mating gaps: `0.3000 mm`;
  - C048 eye clearance: `4.0317 mm`;
  - all three root additions and resulting proposal meshes are closed and
    manifold;
  - V9 rear-cap service gap remains `0.0239 mm`.
- FreeCAD/OCCT exact checks:
  - outer eye root to V9 bucket: `28.7708 mm3`;
  - lower eye root to V9 bucket: `28.8000 mm3`;
  - C048 root to right lower face: `50.1816 mm3`;
  - C048 proposal to V9 eye: no interference, `4.0317 mm` clearance;
  - outer/lower flange mating gaps: `0.3000 / 0.3000 mm`;
  - exact fuses of each accepted eye flange plus its root are valid,
    one-solid, and self-intersection-free;
  - C048 proposal and all three root solids are valid and
    self-intersection-free.
- The FreeCAD review archive is valid and `1,314,202` bytes.

## Rejected or unsafe variants

- Full-face C048 root extensions were rejected: they reduced eye clearance to
  `3.71 mm` or less.
- C048 triangular end-cap extensions were rejected: the only positive owner
  overlap reduced eye clearance below `4.0 mm`.
- Blender's combined outer flange mesh was rejected after FreeCAD reported
  self-intersecting/unorientable topology. The review file instead contains a
  valid exact FreeCAD fuse of the untouched accepted flange and root addition.
- Whole-owner Booleans remain forbidden because the source containers hold
  many disconnected solids and can silently discard unrelated geometry.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_internal_root_embed_review_v1.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_internal_root_embed_review_v1.py
```

The FreeCAD file is then rebuilt from the generated review OBJ files using
mesh-to-solid conversion and exact fuses for the two eye-flange proposals.

## Next physical review

Open the FreeCAD review and inspect:

1. The two eye-side flanges look identical to approved V3 from the mating side.
2. Their added roots remain entirely inside the V9 bucket and do not create
   an exterior protrusion.
3. The small C048 root is at the far end, away from the eye; the eye-side
   reinforcement shape remains unchanged.
4. No new loose strip, rod, flange remnant, or blocked service-cap path appears.

After explicit visual approval, perform component-local copied-owner fuses on
the right, validate every original owner solid is preserved, then exact-mirror
and repeat bilaterally.
