# Right Eye / Shell Conflict Correction Review V40 Checkpoint

**Date:** 2026-08-16  
**State:** One-sided review geometry passes the complete right-shell collision gate. Exterior containment remains a visual hold. This is not a production, mirror, STL, slicing, G-code, or ASA print release.

## Current review artifacts

- FreeCAD review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-shell-conflict-correction-review-v40/CAT_HEAD_RIGHT_EYE_SHELL_CONFLICT_CORRECTION_REVIEW_V40.FCStd`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-shell-conflict-correction-review-v40/validation-v40.json`
- Generator: `source/cad-change-control/generate_right_eye_shell_conflict_correction_review_v40.py`
- Contract: `source/cad-change-control/pilot/right-eye-shell-conflict-correction-review-v40.json`
- Review FCStd SHA-256: `8048b549b716181bc05825fc197530b298edcc202f5f7b00a454760499d486d1`

## Frozen decisions and numeric contract

- The topology-repaired V4 right eye remains fixed and unchanged.
- C009 remains deleted. No replacement, repositioned plank, bridge, rail, rib, flange, or support is added.
- Upper C001 retains only the largest valid closed body from the already-reviewed V26 candidate; detached rail/sliver solids are omitted.
- Lower C001 receives only a `0.30 mm` eye-side relief along `[0.0723083508, -0.4850092939, -0.8715144791]`.
- Lower C012 is shortened `5.452 mm` at its eye-side end.
- Lower C013 is shortened `45.090 mm` at its eye-side end.
- Required minimum C012/C013 eye clearance is `4.0 mm`.
- Ears, translucent panels, rear cassette, C006, and aluminum interface `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen.

## Validation performed

The deterministic V40 run tested the repaired eye against all `41` right-upper and all `60` right-lower shell components.

- Positive eye intersections: `0 / 101`
- Repaired eye: valid, closed, one solid, unchanged
- All four corrected owners: valid, closed, one solid
- Lower C012 eye clearance: `4.0000479501 mm`
- Lower C013 eye clearance: `4.0007755497 mm`
- Lower C012 to lower C001 retained engagement: `47.5279705254 mm3`
- Lower C013 retained engagements:
  - to lower C002: `24.5826503715 mm3`
  - to lower C011: `70.8307823796 mm3`
  - to lower C012: `216.9556554992 mm3`
- Unwanted lower C013 to upper C032 overlap: `0.0 mm3`
- All `59` unchanged lower-component source hashes match.
- FreeCAD container validation: intact ZIP archive.

Validation status: `PASS__COLLISION_FREE_REVIEW__EXTERIOR_CONTAINMENT_VISUAL_HOLD`.

## Rejected and unsafe variants

- V33 C009 relocation is rejected because it floated in the translucent under-ear panel region.
- Adding or reconnecting a replacement C009 plank is rejected; the user explicitly approved deletion instead.
- Global eye subtraction from upper C001 produced invalid/open or multi-solid results and is not used.
- The detached V26 rail/sliver pieces are not structural owner material and are omitted rather than reconnected.
- Collision-free status alone is not a print release. The current shell assembly is not one closed containment solid, so the exterior breach check remains visual.

## Exact regeneration command

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  LD_LIBRARY_PATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/usr/bin/python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_eye_shell_conflict_correction_review_v40.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-shell-conflict-correction-review-v40.json
```

## Required visual review

Open the V40 FreeCAD review and check only:

1. From outside the head, the repaired eye does not appear through any opaque shell surface; it is visible only through the intended eye aperture.
2. From inside, there is no shell material touching the eye and no floating rail, sliver, replacement plank, or support.
3. The under-ear opening, primary ear, and translucent under-ear panel remain unchanged and unobstructed.

After explicit visual approval, create a separate bilateral/integration contract and rerun the complete collision gate on both sides. The eye socket still requires a separate internal lens-retainer design and validation before final socket printing.
