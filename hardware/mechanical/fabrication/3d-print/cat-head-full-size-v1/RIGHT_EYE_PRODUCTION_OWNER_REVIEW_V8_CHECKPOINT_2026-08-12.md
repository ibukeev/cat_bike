# Right Eye Production Owner Review V8 — 2026-08-12

## Status

The user visually approved the V6 continuous-wall correction and the V7
rear-cap post/pocket cleanup. V8 promotes those exact approved right-side
solids into stable STEP production-owner inputs. It does not regenerate them
from the stale Gate 6 generator, which still contains the rejected posts and
obsolete connector layout.

No left mirror, production STL, slicing, ASA printing, or fabrication release
is authorized.

## Review file

Open:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-production-owner-review-v8/CAT_HEAD_RIGHT_EYE_PRODUCTION_OWNER_REVIEW_V8.FCStd`

The clean review contains exactly three objects. The two promoted owners are:

- `right_eye_bucket_production_owner_v8`
- `right_eye_rear_cap_production_owner_v8`

The unchanged Gate 6 diffuser is included only as frozen review context.

## Frozen numeric contract

- Preserve the V6 full-thickness upper and side wall continuations to the
  selected `Face55` plane.
- Preserve the exact right aperture, bezel, chamber, wire port, and the
  approved lower/upper M2.5 connector pair.
- Keep all four rejected rear-cap posts absent.
- Keep all four obsolete bucket post pockets filled.
- Do not add replacement stoppers in this change bucket.
- Preserve all head/ear owners, lower-face/rear-cassette ownership, C006,
  reinforcements, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` unchanged.

## Validation

| Gate | Bucket | Rear cap |
|---|---:|---:|
| Valid closed solid | PASS | PASS |
| Shells / solids | `1 / 1` | `1 / 1` |
| Faces / edges / vertices | `630 / 1120 / 481` | `424 / 722 / 294` |
| Volume | `6649.60 mm3` | `4212.35 mm3` |
| Self-intersection | PASS | PASS |

- Bucket/cap volumetric interference: none.
- Minimum separation: `0.0239 mm`, unchanged from the approved V7 near-contact.
- Both promoted STEP files were reimported into FreeCAD and reproduced the
  same topology, volumes, bounds, and zero-interference result.
- The saved FCStd archive passed ZIP validation and contains exactly the two
  owners plus one frozen diffuser reference; no inherited V7 construction
  objects are present.
- Detailed evidence: `right-eye-production-owner-review-v8/validation-v8.json`.

## Rejected or unsafe source path

Do not rerun the old `generate_gate6_eye_modules.py` and treat its eye output
as current. It still generates four rejected diffuser posts and the superseded
rear-cap connector placement. V8 intentionally promotes the approved B-Rep
owners without approximating or reconstructing their geometry.

## Exact regeneration / promotion command

```sh
bash hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/promote_right_eye_production_owners_v8.sh
```

This copies the validated STEP owner files into
`production/eye-modules-v8/right/` and records their SHA-256 hashes. It does
not create STL or authorize printing.

## Next physical review

1. Leave only the two promoted owner objects and frozen diffuser visible.
2. Confirm the exterior/aperture is identical to approved V7.
3. Hide the cap and confirm the bucket is one continuous body with no four
   post pockets or detached strips.
4. Hide the bucket and confirm the cap has its plate, wire port, and exactly
   the retained lower plus relocated upper connector features, with no posts.
5. After approval, exact-mirror these owners across `X = 0`, rerun all gates on
   both eyes, and show them in full-head context before HS-10 is closed.
