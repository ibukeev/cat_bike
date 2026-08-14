# Right Eye Outer Pair Radial Thickness V4 — 2026-08-13

## Status

V3 is rejected: it incorrectly treated the `8.0 mm` flange depth as the
dimension to double and extended along the flange-depth axis, producing a tall
wall. V4 instead doubles only the `2.4 mm` radial thickness toward each
member's shell interior. The head member is rebuilt from a plain flange bar;
no broad base, wedge, or tapered root is present. This remains an isolated
right-side review with no mirror or print release.

## Review files

- Exact FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-radial-thickness-review-v4/CAT_HEAD_RIGHT_EYE_OUTER_PAIR_RADIAL_THICKNESS_REVIEW_V4.FCStd`
- Blender review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-radial-thickness-review-v4/CAT_HEAD_RIGHT_EYE_OUTER_PAIR_RADIAL_THICKNESS_REVIEW_V4.blend`
- Contract and generator:
  `config/right-eye-outer-pair-radial-thickness-review-v4.json` and
  `source/generate_right_eye_outer_pair_radial_thickness_review_v4.py`
- Generated/exact validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-radial-thickness-review-v4/validation-v4.json` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-radial-thickness-review-v4/freecad-validation-v4.json`

## Locked construction

- Existing flange dimensions: `12.0 x 8.0 x 2.4 mm`.
- Added shell-interior radial thickness: `2.4 mm`.
- Total radial thickness: `4.8 mm`.
- Hidden union overlap: `0.4 mm`.
- M2.5 clearance channel: `2.8 mm`, continued through the added material on
  the unchanged original axis.
- Original mating faces and `0.3000 mm` gap stay fixed.
- Eye side uses the existing V9 bucket owner.
- Head side starts from a newly reconstructed plain flange bar. No object from
  the broad-base source is used in the result.
- Lower pair, C046/C048, panels, eye placement, and metal workstream remain
  untouched.

## Validation performed

- Generated eye/head layers engage their owners by `67.1725 / 68.0886 mm3`.
- Added layers have zero mutual interference.
- Generated plain head bar and both layers are closed/manifold.
- Exact eye result: valid, watertight, one solid, `924` faces.
- Exact head result: valid, watertight, one solid, `160` faces.
- Exact pair: no interference; minimum clearance `0.3000 mm`.
- The eye-side addition lies inside existing owner material, so it does not
  create a new exterior bump. The head-side result visibly becomes a simple
  rectangular `4.8 mm`-thick flange.
- V2 broad bases and V3 depth extensions are absent.

## Rejected or unsafe variants

- V1 tapered roots: exterior protrusion.
- V2 broad rectangular bases: unnecessarily large and visually wrong.
- V3 `8.0 mm` depth extensions: wrong axis, tall wall, and retained broad-base
  head geometry.
- Production integration, left mirror, export, slicing, and printing remain
  held until explicit V4 approval.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_outer_pair_radial_thickness_review_v4.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_outer_pair_radial_thickness_review_v4.py
```

The FreeCAD review is rebuilt from the generated OBJ evidence with exact
mesh-to-solid conversion and pair fuses.

## Next physical review

Open the V4 FreeCAD file and inspect the two visible exact objects:

1. No tall wall extends along the flange-depth axis.
2. The head-side member is a plain rectangular flange, with no triangular,
   tapered, or broad-base residue.
3. Both additions are behind the mating faces toward their owners.
4. Both M2.5 channels remain visible and coaxial.
5. Neither member protrudes through the exterior shell.

After explicit approval, integrate this V4 outer pair into copied production
owners and validate it before touching the lower pair or mirroring left.
