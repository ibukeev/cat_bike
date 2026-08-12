# Right Eye One-Body Serviceable Module Review V1 Checkpoint

Open `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-one-body-serviceable-module-review-v1/CAT_HEAD_RIGHT_EYE_ONE_BODY_SERVICEABLE_MODULE_REVIEW_V1.FCStd`.

Review only these two visible proposal objects:

- `PROPOSED__RIGHT_EYE_BUCKET__ONE_BODY_POST_CLEARANCE_V3`
- `PROPOSED__RIGHT_EYE_REAR_CAP__ONE_BODY_V1`

## Scope and accepted inputs

This is the next isolated right-side `HS-10` proposal. It uses the visually
approved two-pair owner geometry from
`CAT_HEAD_RIGHT_EYE_UPPER_PERIMETER_CONNECTOR_PAIR_CLEAN_REVIEW_V2` without
moving the aperture, bezel, chamber, head-mount features, connector axes, wire
port, or four diffuser-retainer posts.

The retained lower connector axis and approved upper connector axis remain
separated by `44.0291 mm`. Both use the frozen M2.5 contract: `6.0 mm` boss
outside diameter, `2.8 mm` through channel, `4.0 mm` engagement, and `0.30 mm`
pair-face gap.

## Change made

The six accepted bucket components were Boolean-fused into one owner. The
seven accepted rear-cap components were separately Boolean-fused into one
owner so the cap remains removable.

The first fusion-only assembly was rejected because the bucket and cap
intersected by `69.8036 mm3`. The four existing rear-cap retainer posts were
the interfering parts. V3 preserves the exact posts and removes only four
post-shaped bucket clearance pockets. Each pocket uses a `1.25x` centered
envelope, equivalent to approximately `0.79 mm` total X clearance,
`1.44 mm` total Y clearance, and `0.59 mm` total Z clearance around each
unchanged post bounding box.

## Validation

Right bucket V3:

- valid, closed, watertight;
- exactly `1` shell and `1` solid;
- `656` faces, `1197` edges, `530` vertices;
- volume `6398.56 mm3`;
- no self-intersections.

Right rear cap V1:

- valid, closed, watertight;
- exactly `1` shell and `1` solid;
- `471` faces, `858` edges, `384` vertices;
- volume `4388.09 mm3`;
- no self-intersections.

Owner-to-owner validation reports zero intersection. The absolute minimum
clearance is `0.0239 mm` at a separate non-post near-contact location. The two
M2.5 connector face gaps independently remain `0.3000 mm`; the main cap-to-
bucket interface remains `0.2987 mm`. The very small global minimum is therefore
flagged for visual and physical fit review rather than treated as print-ready.

## Rejected or held work

- Rejected: fusion-only V1, because bucket and cap overlap by `69.8036 mm3`.
- Rejected: V2 `1.10x` post envelopes, because they left the same unrelated
  `0.0239 mm` global near-contact and did not provide robust post pockets.
- Held: left-side mirror, production-generator integration, STL export, and
  print release until the right-side proposal is visually approved.

## Exact regeneration source

The accepted clean components are reproduced with:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
```

That command writes temporary source components under
`/tmp/right-eye-owner-components-v1`. The Boolean fusion and clearance-pocket
operations are currently preserved parametrically in the FCStd review file.

## Next physical-review steps

1. In FreeCAD, leave only the two proposal objects visible and orbit around the
   full eye module. Confirm the exterior bezel and aperture did not change.
2. Hide the rear-cap proposal. Inspect the bucket interior and confirm four
   localized post pockets are present without breaking the chamber wall.
3. Hide the bucket and show the cap. Confirm all four retainer posts, the wire
   port, and both connector ears remain.
4. After visual approval, integrate these exact right-side operations into the
   production generator, regenerate, and repeat the topology/interference gates
   before any left mirror or print export.
