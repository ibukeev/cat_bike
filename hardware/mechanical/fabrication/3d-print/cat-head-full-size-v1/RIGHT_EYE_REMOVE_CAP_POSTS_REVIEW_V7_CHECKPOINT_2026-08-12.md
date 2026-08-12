# Right Eye Remove Rear-Cap Posts Review V7 — 2026-08-12

## Status

Isolated right-side review ready. The user approved the V6 continuous-wall
result and explicitly rejected the four long diffuser-retaining posts as
flimsy rear-cap/door features. V7 removes those four posts and restores the
four corresponding bucket clearance pockets. No replacement stopper is added
in this iteration; any later stopper must grow directly from the bucket wall.

No left mirror, production integration, STL export, slicing, ASA printing, or
fabrication release is authorized.

## Review file

Open:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-remove-cap-posts-review-v7/CAT_HEAD_RIGHT_EYE_REMOVE_CAP_POSTS_REVIEW_V7.FCStd`

Leave visible:

- `PROPOSED__RIGHT_EYE_BUCKET__DELETE_STRIPS_EXTEND_WALLS_PRE_CLEARANCE_V6_ref_ref`
- `PROPOSED__RIGHT_EYE_REAR_CAP__POSTS_REMOVED_V7`

## Numeric design contract

- Preserve the approved V6 right-eye outer geometry and complete wall
  extensions to the `Face55` plane.
- Remove all four legacy rear-cap diffuser-retaining posts.
- Each removed post has a nominal `2.0 x 2.0 mm` cross-section.
- Restore the four post-shaped bucket clearance pockets because they no
  longer serve any physical feature.
- Preserve the rear-cap plate, wire port, and both M2.5 fastener ears.
- Preserve all eye/head connectors and the
  `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.
- Do not add detached or rear-cap-mounted replacement stops.
- If diffuser stops are later required, make them direct wall-grown features
  in a separate reviewed change bucket.

## Validation

Bucket with post pockets restored:

- valid closed solid; one shell and one solid;
- `630` faces, `1120` edges, `481` vertices;
- volume `6649.60 mm3`;
- restored material relative to V6: `130.63 mm3`;
- OCCT self-intersection: PASS.

Rear cap with posts removed:

- valid closed solid; one shell and one solid;
- `424` faces, `722` edges, `294` vertices;
- volume `4212.35 mm3`;
- removed material relative to V6: `175.74 mm3`;
- four posts absent; plate and two fastener ears retained;
- OCCT self-intersection: PASS.

Assembly:

- bucket/cap volumetric interference: `0.0000 mm3`;
- known unrelated minimum clearance: `0.0239 mm`, unchanged;
- saved FCStd integrity: PASS; `1,784,806` bytes.

The complete validation ledger is:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-remove-cap-posts-review-v7/validation-v7.json`

## Rejected or unsafe variants

- Do not retain the four long rear-cap posts: they are slender, make the
  removable door fragile, and forced four unnecessary cavities into the
  bucket.
- Do not replace them with new detached rods or posts.
- Do not add wall-grown stops without a separate anchor and clearance review.
- V5 remains rejected because it retained detached strips and added separate
  bridge material.

## Exact regeneration inputs

V7 is an isolated FreeCAD structured-object proposal derived from the frozen
V6 review and the accepted connected-component source review. Reproduce the
connected owner inputs with:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_delete_strips_extend_walls_review_v6.py
```

Then in FreeCAD retain V6's pre-clearance bucket body and fuse only rear-cap
component `03`, rear-cap component `04`, and the moved-pair cap ear. Components
`01`, `02`, `05`, and `07` are the four rejected posts and must remain absent.

## Next physical review

1. Orbit around the eye and confirm the V6 exterior and continuous walls did
   not change.
2. Hide the bucket and inspect the rear cap: confirm all four long posts are
   gone while the plate and two fastener ears remain.
3. Hide the cap and inspect the bucket interior: confirm the four obsolete
   post pockets are gone.
4. Confirm no replacement stop was introduced in this review.
5. Approve or reject this right-side cleanup before mirroring or production
   integration.
