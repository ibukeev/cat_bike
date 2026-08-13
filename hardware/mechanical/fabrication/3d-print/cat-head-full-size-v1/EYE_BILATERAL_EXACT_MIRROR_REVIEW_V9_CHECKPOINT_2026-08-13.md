# Eye Bilateral Exact-Mirror Review V9 — 2026-08-13

## Status

The user approved the clean right-eye V8 production owners and authorized the
next step. V9 mirrors those exact owners across `X = 0` into a review-only left
bucket and removable rear cap. No right-side geometry, head shell, ear,
lower-face/rear-cassette, reinforcement, or aluminum-interface geometry was
changed.

V9 passes all bilateral digital gates and is awaiting visual approval. It is
not a production integration, STL, slicer project, ASA recommendation, or
fabrication release.

## Current review files

Open the exact four-owner FreeCAD review:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.FCStd`

Open the full-head visual review:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.blend`

Evidence renders are in the adjacent `review/` directory. Orange is the
unchanged approved right eye; blue is its exact `X=0` mirror. Gray is frozen
full-head context.

## Accepted decisions and numeric contract

- Right source: user-approved V8 bucket and rear cap.
- Mirror datum: global YZ plane, `X = 0`.
- Coordinate rule: `(x, y, z) -> (-x, y, z)`.
- Right-owner geometric change: exactly `0 mm`.
- Each owner must remain one valid closed solid and one shell.
- Mirrored pairs must have identical topology and volume, identical Y/Z
  bounds, and sign-reversed X bounds.
- Unintended owner interference and self-intersection are forbidden.
- Preserve V6 continuous full-thickness bucket walls, the V7 post-free rear
  cap, and the accepted lower/relocated-upper M2.5 connector pair.
- Preserve `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`, C006, exact upper-head/ear
  owners, and lower-face/rear-cassette ownership.

## Validation performed

| Owner | Valid / watertight | Solids / shells | Faces / edges / vertices | Volume |
|---|---|---:|---:|---:|
| Right bucket | PASS | `1 / 1` | `630 / 1120 / 481` | `6649.60 mm3` |
| Left bucket | PASS | `1 / 1` | `630 / 1120 / 481` | `6649.60 mm3` |
| Right rear cap | PASS | `1 / 1` | `424 / 722 / 294` | `4212.35 mm3` |
| Left rear cap | PASS | `1 / 1` | `424 / 722 / 294` | `4212.35 mm3` |

- All four owners pass OCCT self-intersection verification.
- Right bucket/cap: no intersection; minimum clearance `0.0239 mm`.
- Left bucket/cap: no intersection; minimum clearance `0.0239 mm`.
- Right/left bucket centerline clearance: `54.9791 mm`, no interference.
- Right/left cap centerline clearance: `51.8270 mm`, no interference.
- Left STEP round-trip reproduces the same topology and volumes; both imported
  owners remain valid closed solids and retain the `0.0239 mm` gap.
- The FCStd archive passes ZIP validation and contains exactly four owners.
- Detailed machine-readable results: `validation-v9.json`.

## Rejected or unsafe variants

- Do not regenerate from stale Gate 6 eye sources. They restore the rejected
  cap posts, obsolete bucket pockets, and superseded connector arrangement.
- Do not mirror any earlier flying-strip, additive-wall, or diagnostic review.
- Do not integrate review OBJ meshes into production; they exist only for the
  Blender evidence pack.
- Do not start ASA shell printing from V9. HS-11 and later shell integration
  gates remain open.

## Exact regeneration command

The FreeCAD owners are the saved structured result of Part Mirror across the
global YZ plane from the exact V8 owners. After exporting the four review-only
OBJ meshes, regenerate the visual pack with:

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_eye_bilateral_exact_mirror_review_v9.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_eye_bilateral_exact_mirror_review_v9.py -- hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/review hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.blend
```

## Next physical review

1. Open the V9 FCStd and confirm there are exactly four owner objects.
2. Compare left and right from front and rear: the aperture, full-thickness
   wall continuations, cap outline, wire port, and connector details must be
   exact bilateral counterparts.
3. Open the Blender review and confirm both eye assemblies occupy the intended
   full-head locations with no detached strips, posts, pockets, or unexplained
   geometry.
4. If V9 is visually approved, mark HS-10 complete, promote the left STEP
   owners, then start HS-11: integrate and validate the already accepted four
   eye/head flange roots per side.
