# Right Eye Upper-Rim Structural Root Review V1 Checkpoint

Open `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-rim-structural-root-review-v1/CAT_HEAD_RIGHT_EYE_UPPER_RIM_STRUCTURAL_ROOT_REVIEW_V1.FCStd`.

Review only:

- `PROPOSED__RIGHT_EYE_BUCKET__RIM_STRUCTURALLY_JOINED_V2`
- `PROPOSED__RIGHT_EYE_REAR_CAP__ONE_BODY_V1_ref`

## User-reported failure and anchor

The user visually rejected the narrow upper eye rim because it appeared to
float disconnected from the main eye owner. The structured screenshot anchor
was `PROPOSED__RIGHT_EYE_BUCKET__ONE_BODY_POST_CLEARANCE_V3.Face476`, around
`(46.68, 67.60, 166.62) mm`.

Exact component audit proved this was a real validation failure rather than a
display seam. The prior multi-fuse reported one valid solid, but its common
volume with source bucket component 04 was `0.00 mm3`: the upper baffle/rim
component was omitted from the fused result while the source copy remained
visible in the review document.

## Isolated proposal

The missing exact source component 04 was moved `(+0.50, +0.50, +0.50) mm`
relative to its frozen source placement and Boolean-fused into the accepted
right bucket. This is an isolated right-side root correction. It does not move
the eye aperture, connector axes, rear cap, cap posts, wire port, head shell,
ear, or aluminum workstream.

The small inward shift turns the former coincident/sliver contact into
`2242.5184 mm3` of continuous overlap with the receiving bucket owner while
remaining clear of the rear cap by at least `1.5549 mm` as an isolated
component.

## Validation

- final bucket: valid, closed, watertight;
- final bucket: exactly `1` shell and `1` solid;
- final bucket: `656` faces, `1197` edges, `530` vertices;
- final bucket volume: `6398.56 mm3`;
- source rim common volume in final bucket: `2242.5184 mm3`;
- final bucket self-intersection: none;
- final bucket to rear cap interference: none;
- final global bucket/cap minimum clearance: `0.0239 mm`, unchanged at the
  previously recorded unrelated near-contact.

## Rejected or unsafe variants

- Previous one-body V1 is rejected for review/release because the Boolean
  operation silently omitted component 04 despite reporting one solid.
- Directly fusing component 04 at its exact coincident source location produced
  two solids and did not establish a structural root.
- No left mirror, production integration, STL export, or print release is
  authorized by this review.

## Exact regeneration source

Recreate the frozen connected-component inputs with:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
```

The isolated FreeCAD placement and Boolean operations are preserved in the
review FCStd.

## Next review

Orbit around the upper eye rim and confirm it no longer appears as a separate
floating strip. Then hide the rear cap and inspect the interior root. Approval
still does not authorize mirroring or printing; the `0.0239 mm` unrelated cap
near-contact must be resolved before print release.
