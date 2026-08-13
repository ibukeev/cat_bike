# Right Eye Flange Owner Alignment Review V1 Checkpoint — 2026-08-13

## Status

HS-11 right-side proposal ready for visual review. The exact four accepted V3
broad-base flange meshes are shown against the current V9 right-eye bucket and
the frozen current right upper-head/lower-face context. No flange has been
Boolean-fused into an owner. No mirror or fabrication export was made.

## Review files

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-alignment-review-v1/CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_ALIGNMENT_REVIEW_V1.FCStd`
- Blender: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-alignment-review-v1/CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_ALIGNMENT_REVIEW_V1.blend`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-alignment-review-v1/validation-v1.json`
- Evidence: adjacent `review/` directory.

## Locked design contract

- Right side only; exactly four physical flange candidates:
  outer head, outer eye, lower head, and lower eye.
- Preserve the accepted V3 centers and axes without movement.
- Tab envelope: `12.0 x 8.0 x 2.4 mm`.
- M2.5 clearance bore: `2.8 mm`.
- Mating gap: `0.3 mm`; front recess: `0.6 mm`.
- Broad base: `4.0 mm` total depth, `0.8 mm` overlap, `12 x 8 mm`
  flange footprint, and `16 x 12 mm` owner footprint.
- Current eye owner: promoted V9 right bucket.
- Head context: frozen V10 right upper head and accepted V5 lower-face
  ownership. C006 and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain untouched.

## Validation performed

- Exactly four candidates exist on the right side.
- All four accepted V3 meshes are closed and manifold in the Blender audit.
- All four broad roots intersect their intended current owner:
  upper head, lower face, or V9 eye bucket.
- Rejected `R1_UNCL__R__C002__eye_mount` and superseded
  `R1_RET__R__C004__eye_mount` are absent.
- FreeCAD review archive passes ZIP validation.
- The FreeCAD file contains three owner-context meshes, four flange meshes,
  and one locked-contract spreadsheet; it is review geometry, not production
  CAD.
- FreeCAD's secondary mesh checker reports self-intersection warnings on two
  imported triangulated review derivatives. The unchanged source V3 flange
  meshes remain closed/manifold and are not modified or auto-repaired here.
- No production Boolean, mirror, STL, G-code, or print release was produced.

## Rejected or unsafe variants

- Do not replace the V9 bucket with the stale Gate 6 bucket.
- Do not reuse C002/C004 source mounts.
- Do not repair or reshape the accepted flange meshes while resolving an OBJ
  import warning; the accepted V3 topology and numeric datums are frozen.
- Do not mirror or fuse before the right-side visual review is approved.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_flange_owner_alignment_review_v1.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_flange_owner_alignment_review_v1.py
```

The `.FCStd` is assembled through the FreeCAD MCP from the generated
review-only OBJ derivatives; it is not a production owner file.

## Next physical review

1. Open the FreeCAD file and confirm there are exactly four colored flange
   candidates: two mating flanges at the outer interface and two at the lower
   interface.
2. Confirm the orange eye-side flanges visibly root into the blue V9 bucket.
3. Confirm the purple head-side flanges root into the upper-head and lower-face
   context without exterior protrusion or a floating base.
4. Confirm the paired bores remain coaxial and the two interfaces retain a
   visible assembly gap.
5. After explicit approval, build copied right production owners, union the
   four flanges, and validate screw/tool access and reinforcement clearance.
