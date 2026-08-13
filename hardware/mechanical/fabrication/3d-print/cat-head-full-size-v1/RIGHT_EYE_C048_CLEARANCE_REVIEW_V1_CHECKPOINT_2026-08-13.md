# Right Eye C048 Clearance Review V1 Checkpoint — 2026-08-13

## Status

HS-11 right-side reinforcement-clearance proposal ready for visual review.
The user approved the V1 locations of the four right eye flanges on 2026-08-13
and then identified a reinforcement plank colliding with the eye. Exact BVH
testing identifies that plank as `R1_RET__R__C048__rib`. No eye, flange, shell,
aluminum, or other reinforcement geometry was changed.

## Review files

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-c048-clearance-review-v1/CAT_HEAD_RIGHT_EYE_C048_CLEARANCE_REVIEW_V1.FCStd`
- Blender: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-c048-clearance-review-v1/CAT_HEAD_RIGHT_EYE_C048_CLEARANCE_REVIEW_V1.blend`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-c048-clearance-review-v1/validation-v1.json`
- Evidence: adjacent `review/` directory. The rejected original is red and the
  proposed trimmed rib is cyan in the rendered comparisons.

## Selected anchors and locked numeric contract

- Object: `R1_RET__R__C048__rib` only.
- Eye-side triangular end: vertices `0, 1, 2`; centroid
  `(37.2865, 54.3104, 125.1719) mm`.
- Preserved far triangular end: vertices `3, 4, 5`; centroid
  `(80.3938, 57.0350, 88.8931) mm`.
- Original axis unit vector: `(0.764211, 0.048302, -0.643155)`.
- Trim only along that original axis; no scaling, rotation, or cross-section
  change.
- Minimum clearance from the current V9 eye and removable lower eye flange:
  `2.0 mm`.
- Minimum retained length: `20.0 mm`.
- Keep one closed manifold rib rooted in `right_lower_face`.
- Hold the accepted V3 flanges, promoted V9 eye, shell exterior, C006, and
  `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` unchanged.

## Validation performed and results

- Exact source collision audit: original C048 intersects the V9 bucket.
- Eye-side axial trim: `5.0767 mm` (`0.09` of the original length).
- Original length: `56.4076 mm`; retained length: `51.3309 mm`.
- V9 eye clearance: `2.0140 mm`; V9 overlap: false.
- Accepted lower eye flange clearance: `13.6708 mm`; overlap: false.
- Far end is preserved exactly and the proposal still overlaps the accepted
  lower-face owner.
- Proposal topology: `6` vertices, `9` edges, `5` polygon faces, zero boundary
  edges, and zero non-manifold edges. The triangulated FreeCAD derivative also
  passes mesh validation with `6` points and `8` facets.
- FreeCAD archive passes ZIP validation (`79,904` bytes).
- The inherited V9 bucket derivative still reports its previously known mesh
  self-intersection warning; it was not auto-repaired or changed here.
- The lower-face context is an intentionally broad triangulated assembly
  reference and is not treated as a production solid in this review.
- No production Boolean, mirror, STL, G-code, or print release was produced.

## Rejected or unsafe variants

- The untrimmed C048 is rejected at this location because it physically
  intersects the V9 eye.
- Do not move the eye or the approved V3 flange datums to accommodate C048.
- Do not delete C048 completely; the far end and lower-face reinforcement root
  remain required.
- Do not mirror or union this proposal before right-side visual approval.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_c048_clearance_review_v1.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_c048_clearance_review_v1.py
```

The `.FCStd` is assembled through the FreeCAD MCP from the generated review
OBJ derivatives; it is review geometry, not a production owner file.

## Next physical review

1. Open the FreeCAD file and leave
   `REJECTED_COLLIDING_C048_ORIGINAL` hidden.
2. Inspect `PROPOSED_TRIMMED_C048_CLEARANCE_V1` at the eye-side end. Confirm it
   no longer enters the V9 bucket or either accepted lower flange.
3. Follow the cyan rib toward its opposite end and confirm it still visibly
   roots into the lower-face context; it must not appear floating.
4. Optionally toggle the rejected original on to compare the removed red
   segment against the cyan proposal.
5. After explicit approval, use the same exact trim on a copied right owner,
   re-run all reinforcement/eye/tool clearances, and only then mirror.
