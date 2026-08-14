# Right A/B Short-Insert Coupon V1 Checkpoint - 2026-08-14

## Status

The exact approved Right-A V4 and Right-B V2 tab geometries are packaged in an
editable PrusaSlicer project as two separately selectable and movable objects.
The user requested this handoff to choose the print orientation in PrusaSlicer.

This is an orientation-review project, not G-code and not a production shell
release. The imported displayed-V2 orientation leaves both standalone coupons
on an edge with 0.0 mm2 planar bed contact, so that starting orientation is not
print-approved.

## Frozen sources

- FreeCAD: output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-owner-integration-review-v1/CAT_HEAD_RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1.FCStd
- Right A object: PROPOSED__RIGHT_A__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V4_ref
- Right B object: PROPOSED__RIGHT_B__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V2_ref
- FreeCAD SHA-256: e9974661a5a0a71a12bcb6ab6d0d66ceae354fd8744486ff08ce72e20cf0376c
- Right A source STL SHA-256: 96fbf9754194400527560dd0e9ac51b985fc07612eabd9abde1de5ea02e50c23
- Right B source STL SHA-256: 2af4483cdf60b05e969e1a3ce8ce8c3917e4f6fcbf4b01913ac4b64947866ed7

No geometry or scale change is authorized. Only build-plate orientations and
positions are user-editable.

## Numeric contract and validation

- Geometry change: 0.0 mm; scale: 1.0.
- Initial displayed-V2 quaternion WXYZ: [0.463786364, -0.517753959, 0.496808916, 0.519628584].
- A: 28.2915 x 9.8352 x 18.4034 mm, 408 facets, manifold, one part.
- B: 28.2627 x 12.8231 x 24.0911 mm, 408 facets, manifold, one part.
- A/B volume: 1195.4868/1195.4857 mm3.
- Initial A/B planar bed contact: 0.0/0.0 mm2.
- 3MF manifest: two model objects and two printable build items.
- PrusaSlicer import: two separate manifold entries.
- 3MF SHA-256: c4fe5f6cbde678e7fd9d1267f7837ed039cc63a90eda910ab7648803782a78df.

## Current outputs

- Editable slicer project: output/40-prototypes/right-ab-short-insert-coupon-v1/CAT_HEAD_RIGHT_AB_SHORT_INSERT_COUPON_V1.3mf
- A STL: output/40-prototypes/right-ab-short-insert-coupon-v1/right-a-v4-short-insert-coupon-exact-orientation.stl
- B STL: output/40-prototypes/right-ab-short-insert-coupon-v1/right-b-v2-short-insert-coupon-exact-orientation.stl
- Blender scene: output/40-prototypes/right-ab-short-insert-coupon-v1/CAT_HEAD_RIGHT_AB_SHORT_INSERT_COUPON_V1.blend
- Validation: output/40-prototypes/right-ab-short-insert-coupon-v1/validation-v1.json
- Contract: config/right-ab-short-insert-coupon-v1.json
- Evidence: output/40-prototypes/right-ab-short-insert-coupon-v1/review/

## Rejected or unsafe variants

- The first CLI-built 3MF was rejected because PrusaSlicer silently overwrote A
  and retained only B. It was replaced and is not retained.
- The initial displayed-V2 orientation is not a printable coupon recommendation
  because both independent objects have zero planar bed contact.
- No supports, brim, print profile, G-code, or automatic reorientation are baked
  into this project.
- No full-head or full-shell body is exported by this workstream.

## Exact regeneration

From the repository root run:

    blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_ab_short_insert_coupon_v1.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-ab-short-insert-coupon-v1.json
    python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_ab_short_insert_slicer_project_v1.py --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-ab-short-insert-coupon-v1.json
    prusa-slicer --info hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/40-prototypes/right-ab-short-insert-coupon-v1/CAT_HEAD_RIGHT_AB_SHORT_INSERT_COUPON_V1.3mf

If the source STLs must be regenerated, export only the two named FreeCAD
objects with linear deflection 0.05 mm, angular deflection 0.261799 rad, no
scale, and no geometry edits. Confirm their stored hashes before generation.

## Next physical review

1. Open the 3MF in PrusaSlicer.
2. Select A or B independently in the object list; do not scale.
3. Rotate each to the intended print orientation.
4. Save as CAT_HEAD_RIGHT_AB_SHORT_INSERT_COUPON_USER_ORIENTED_V1.3mf.
5. Return that project or say it is saved. Then validate bed contact, supports,
   brim, cavity continuity, collision, printer envelope, and the final slice.
