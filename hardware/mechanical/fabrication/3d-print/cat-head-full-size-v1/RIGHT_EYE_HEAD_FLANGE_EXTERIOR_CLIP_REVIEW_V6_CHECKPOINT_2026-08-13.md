# Right Eye Head-Flange Exterior Clip V6  -  2026-08-13

## Status

V5 thickness and placement were visually accepted, but the two head-side
flanges crossed the angled exterior shell skins. V6 preserves both V5 eye-side
flanges, all four mating planes, all M2.5 axes and bore centers, and both
0.3000 mm gaps. It trims only the outward corners of the outer-head and
lower-head flange leaves against the frozen owner skins.

This is an isolated right-side review. No production owner Boolean, left
mirror, STL, G-code, slicing, ASA release, or print release has occurred.

## Review files

- Exact FreeCAD review:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-head-flange-exterior-clip-review-v6/CAT_HEAD_RIGHT_EYE_HEAD_FLANGE_EXTERIOR_CLIP_REVIEW_V6.FCStd
- Blender review:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-head-flange-exterior-clip-review-v6/CAT_HEAD_RIGHT_EYE_HEAD_FLANGE_EXTERIOR_CLIP_REVIEW_V6.blend
- Contract and generator:
  config/right-eye-head-flange-exterior-clip-review-v6.json and
  source/generate_right_eye_head_flange_exterior_clip_review_v6.py
- Validation:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-head-flange-exterior-clip-review-v6/validation-v6.json and
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-head-flange-exterior-clip-review-v6/freecad-validation-v6.json

## Locked construction

- Four flange roles remain: outer-eye, outer-head, lower-eye, lower-head.
- V5 nominal envelope remains 12.0 x 8.0 x 4.8 mm before the two exterior
  corner trims.
- Both eye-side flange solids are geometrically unchanged from V5.
- Mating-face shift: 0.0 mm.
- Hole-axis and bore-center shift: 0.0 mm.
- M2.5 through diameter: 2.8 mm.
- Outer and lower pair gaps: 0.3000 mm.
- Frozen owner geometry is not cut or otherwise modified.
- The V9 eye bucket, upper head, lower face, C046/C048, C006, rear cassette,
  panels, and aluminum workstream remain frozen.

## Exterior-plane control

The rejected nearest-facet method selected internal mount geometry. V6 instead
requires a large owner-skin face, the flange center on its interior side, and
only an outward flange corner crossing the plane.

| Role | Frozen owner face (0-based) | Face area | Pre-trim outward breach | Final positive deviation |
|---|---:|---:|---:|---:|
| Outer head | 11 | 1225.0516 mm2 | 3.293950 mm | -0.000013 mm |
| Lower head | 1041 | 225.6302 mm2 | 0.702294 mm | -0.000014 mm |

## Validation performed

| Flange | FreeCAD exact volume | Valid | Watertight | One solid |
|---|---:|---|---|---|
| Outer head, clipped | 323.18 mm3 | PASS | PASS | PASS |
| Outer eye, unchanged | 431.87 mm3 | PASS | PASS | PASS |
| Lower head, clipped | 421.49 mm3 | PASS | PASS | PASS |
| Lower eye, unchanged | 431.79 mm3 | PASS | PASS | PASS |

- Outer exact pair clearance: 0.3000 mm.
- Lower exact pair clearance: 0.3000 mm.
- Pair interference: zero.
- Exterior positive deviation gate (maximum 0.02 mm): PASS for both head
  flanges.
- Frozen owners modified: no.
- Broad base, wedge, taper, neck, bridge, or boss added: no.

## Structural holds

Shape review is ready, but print release remains blocked:

- Outer-head bore-to-trim-edge ligament is 1.6155 mm versus the 3.5 mm gate.
- Lower-head bore-to-trim-edge ligament is 3.1294 mm versus the 3.5 mm gate.
- The automated lower-head direct-owner overlap result is 26.2422 mm3 versus
  the 80 mm3 gate.
- Do not move a hole, change the pair gap, or enlarge a root until the V6 shape
  is visually approved and a separate numeric contract is accepted.

## Rejected or unsafe variants

- V1 tapered roots: exterior protrusion.
- V2 broad bases: unnecessary and visually wrong.
- V3 wrong-axis extension: tall wall and retained malformed geometry.
- V4 contained layer: eye-side thickness did not change.
- V5 plain 4.8 mm flanges: accepted thickness, but angled head-side corners
  crossed the exterior shell.
- Early V6 nearest-facet diagnostic: rejected because it selected internal
  mount facets and did not remove the exterior breach.

## Exact regeneration command

    python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_head_flange_exterior_clip_review_v6.py
    blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_head_flange_exterior_clip_review_v6.py

The FCStd is then rebuilt from the seven generated review OBJ files and all
four flange meshes are converted to exact one-solid objects.

## Next physical review

Open the V6 FreeCAD file.

1. Inspect the outer-head flange from outside the upper-head shell. Confirm its
   angled trimmed edge is flush/recessed and no corner crosses the skin.
2. Inspect the lower-head flange from outside the lower-face shell. Confirm the
   small angled trim is flush/recessed.
3. Inspect from inside and confirm both head flanges still have useful inward
   thickness and both eye-side mates are unchanged.
4. Confirm both bolt holes remain aligned through each 0.3000 mm pair gap.

After visual approval, address the three structural holds in a separate
one-side proposal without changing this accepted exterior envelope.
