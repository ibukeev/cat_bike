# Right Eye All-Four Plain Flange Thickness V5 — 2026-08-13

## Status

V4 is rejected because its eye-side layer was wholly contained by the eye
bucket and did not change the actual eye-flange solid. V5 rebuilds all four
right-side flange leaves as real standalone plain rectangular solids:
outer-eye, outer-head, lower-eye, and lower-head. Each flange is visibly
4.8 mm thick. This is an isolated right-side review only.

The shape and pair-clearance checks pass. Production integration remains held
because the outer-head flange overlaps its receiving upper-head owner by only
56.2443 mm3, below the controlled 80 mm3 direct-root gate.

## Review files

- Exact FreeCAD review:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.FCStd
- Blender review:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.blend
- Contract and generator:
  config/right-eye-all-four-plain-flange-thickness-review-v5.json and
  source/generate_right_eye_all_four_plain_flange_thickness_review_v5.py
- Generated and exact validation:
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/validation-v5.json and
  output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/freecad-validation-v5.json

## Locked construction

- Four flange leaves: outer-eye, outer-head, lower-eye, lower-head.
- Plain rectangular dimensions: 12.0 x 8.0 x 4.8 mm.
- Original thickness: 2.4 mm.
- Added owner-side thickness: 2.4 mm.
- Original mating faces remain fixed: 0.0 mm shift.
- Original M2.5 axes and bore centers remain fixed: 0.0 mm shift.
- Through-channel diameter: 2.8 mm.
- Both pair gaps remain 0.3000 mm.
- The V9 bucket, upper head, lower face, C046/C048, C006, rear cassette,
  panels, and aluminum workstream are frozen.

## Validation performed

| Flange | Exact volume | Owner overlap | 80 mm3 gate |
|---|---:|---:|---|
| Outer head | 431.8158 mm3 | 56.2443 mm3 | FAIL |
| Outer eye | 431.8714 mm3 | 247.0647 mm3 | PASS |
| Lower head | 431.8105 mm3 | 431.8112 mm3 | PASS |
| Lower eye | 431.7853 mm3 | 248.3147 mm3 | PASS |

- All four exact FreeCAD objects are valid, self-intersection-free one-solids.
- Outer and lower flange pairs have zero interference.
- Outer and lower minimum clearances are both exactly 0.3000 mm.
- Every generated flange is a standalone thickened solid; V4's contained
  eye-layer construction is absent.
- No broad base, wedge, taper, neck, bridge, or boss exists.
- The FCStd archive is valid.

## Rejected or unsafe variants

- V1 tapered roots: exterior protrusion.
- V2 broad bases: unnecessary and visually wrong.
- V3 wrong-axis extension: tall wall and retained malformed head geometry.
- V4 radial layer: only the head flange changed visibly; the eye-side layer
  disappeared inside the bucket owner.
- V5 is not structurally releasable until the outer-head direct owner root is
  at least 80 mm3.

## Exact regeneration command

    python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_all_four_plain_flange_thickness_review_v5.py
    blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_all_four_plain_flange_thickness_review_v5.py

## Next physical review

Open the V5 FreeCAD file. The four source meshes are hidden and the four exact
flange solids are visible with the three receiving-owner contexts.

1. Confirm both eye-side flanges are genuinely as thick as their head-side
   mates.
2. Confirm both pairs remain on the correct existing faces.
3. Confirm no member protrudes through the exterior shell.
4. Confirm the plain rectangular form is acceptable.

After shape approval, increase only the outer-head owner engagement to pass
the 80 mm3 gate without moving the mating face or adding a broad base.
