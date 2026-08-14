# Right Eye All-Four-Flange Local Skin Clip V7 - 2026-08-13

## Status

V6 still showed pieces of the right-eye flange pairs outside the adjacent
angled head skins. V7 starts from the approved V6 positions and clips all four
flange leaves against the local frozen owner-skin half-spaces. The retained
candidate uses a 0.03 mm inward exterior recess.

This is an isolated right-side review. No owner Boolean, left mirror, STL,
G-code, slicing, ASA release, or print release has occurred.

## Current review and output files

- Exact FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.FCStd`
- Blender review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend`
- Review images and OBJ sources:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/review/`
- Contract:
  `config/right-eye-all-four-flange-local-skin-clip-review-v7.json`
- Generator:
  `source/generate_right_eye_all_four_flange_local_skin_clip_review_v7.py`
- Blender validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/validation-v7.json`
- Exact FreeCAD validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/freecad-validation-v7.json`

## Accepted decisions and dimensions

- Preserve the four V6 flange roles: outer-head, outer-eye, lower-head, and
  lower-eye.
- Preserve the nominal 12.0 x 8.0 x 4.8 mm flange envelope before local
  clipping.
- Preserve both mating planes, all M2.5 axes and bore centers, and the 2.8 mm
  through-hole diameter.
- Preserve 0.3000 mm gaps for the outer and lower flange pairs.
- Exterior recess: 0.03 mm. This is the largest tested value that preserves
  positive direct attachment of the lower head flange.
- Frozen V9 eye bucket, upper head, lower face, C046, C048, C006, rear
  cassette, panels, and aluminum workstream remain unchanged.

## Validation performed and results

| Exact flange | Volume | Valid | Watertight | One solid | Direct owner overlap |
|---|---:|---|---|---|---:|
| Outer head | 323.18 mm3 | PASS | PASS | PASS | 122.5160 mm3 |
| Outer eye | 431.66 mm3 | PASS | PASS | PASS | 247.0317 mm3 |
| Lower head | 421.49 mm3 | PASS | PASS | PASS | 26.2422 mm3 |
| Lower eye | 394.76 mm3 | PASS | PASS | PASS | 211.3736 mm3 |

- OCCT self-intersection checks: PASS for all four exact solids.
- Outer exact pair clearance: 0.3000 mm.
- Lower exact pair clearance: 0.3000 mm.
- Pair interference: zero.
- Frozen owner geometry modified: no.
- Saved FCStd archive validation: PASS.

## Rejected or unsafe variants

- V6: rejected for this exterior-visibility issue; portions of the flange
  leaves remained visible outside the angled skins.
- Early V7 internal-parallel-plane trial: rejected because it selected an
  inward parallel wall and removed required owner attachment.
- 0.04 mm exterior recess: rejected; lower-head direct owner overlap became
  0.0 mm3.
- 0.06, 0.12, 0.25, and 0.50 mm recess trials: rejected for the same loss of
  lower-head attachment.
- Do not use any rejected trial as a print or integration source.

## Structural holds

- Lower-head direct owner overlap is positive but remains below the prior
  80 mm3 structural release gate.
- The prior bore-to-trim-edge ligament holds remain unresolved: outer head
  1.6155 mm and lower head 3.1294 mm versus the 3.5 mm gate.
- V7 is therefore for exterior-envelope review only, not print release.

## Exact regeneration command

    python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_all_four_flange_local_skin_clip_review_v7.py
    blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-head-flange-exterior-clip-review-v6/CAT_HEAD_RIGHT_EYE_HEAD_FLANGE_EXTERIOR_CLIP_REVIEW_V6.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_all_four_flange_local_skin_clip_review_v7.py

The FCStd is then rebuilt from the seven OBJ files in the V7 `review/`
directory, and the four flange meshes are converted to exact solids.

## Next physical review

Open the V7 FreeCAD file.

1. From outside the right upper-head shell, confirm no outer-head or outer-eye
   flange fragment crosses the shell skin.
2. From outside the right lower-face shell, confirm no lower-head or lower-eye
   flange fragment crosses the shell skin.
3. From inside, confirm all four flange leaves remain continuous with their
   intended owners and retain useful inward thickness.
4. Confirm the bolt holes remain visually coaxial across both 0.3000 mm gaps.

After exterior approval, address the structural holds as a separate isolated
proposal; do not alter this approved exterior envelope.
