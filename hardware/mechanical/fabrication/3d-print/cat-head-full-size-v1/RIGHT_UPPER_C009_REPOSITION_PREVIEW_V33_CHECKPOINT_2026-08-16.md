# Right Upper C009 Reposition Preview V33 Checkpoint

Date: 2026-08-16

## Status

Review-only one-sided FreeCAD preview generated successfully.

Overall result: `PASS__REVIEW_ONLY_ONE_SIDED_PREVIEW`.

This file implements only the V32-authorized rigid translation of the exact
existing C009 member. It does not add a bridge, root, plank, rib, rail, or any
other support geometry. It is not mirrored, production-unioned, exported to
STL, sliced, converted to G-code, or released for structural ASA printing.

## Current review/output files

- Review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-reposition-preview-v33/CAT_HEAD_RIGHT_UPPER_C009_REPOSITION_PREVIEW_V33.FCStd`
- Authoritative validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-reposition-preview-v33/validation-v33.json`
- Controlled generator:
  `source/cad-change-control/generate_right_upper_c009_reposition_preview_v33.py`
- Numeric contract:
  `source/cad-change-control/pilot/right-upper-c009-reposition-preview-v33.json`

SHA-256:

- generator:
  `45f377d480df4172b94e82d70b20bb3fe0e02e4617f10f32fd32b532abff06a3`
- contract:
  `935d37d4a37f9a2d701af984172c87f4b359d9671e9251100870601443571cb9`
- review FCStd:
  `63665f07d8f1a4a67d487249c3ad83090e7fa0867094cc0b391cbed48c7ff887`
- validation:
  `aa96ca46482da1e3cdcb253a66fb15de89966e124f6b6a546eb0aa0744688cb8`

Hash-pinned frozen inputs:

- accepted V25 right-upper context:
  `ef3f1668f9c55e8c3744b1bac98c7f599a98251929aaed46c549db3b1214a775`
- accepted V25 validation:
  `26bcaff8685fa8983dd961a1f3953ca5301afb0e6d83e09bc8739185053e8b6c`
- topology-repaired V4 eye STEP:
  `1ae9408d908edc9cf7e8d5ac2dd0c5bdd8a36f0f184d2bab3e05dafa1ef41258`
- V32 full-context route validation:
  `eb95f2c742266b5bc2910d3b6f6dfe98d5a6e2d2758e420b2d77d5eec2ac4f65`

## Accepted and preserved design contract

- Move only the exact existing C009 member.
- Translation: `[1.825092, 10.446536, 8.290829] mm`.
- Rotation: zero.
- Scaling, trimming, deformation, replacement, and added material: prohibited.
- Preserve all other C001-C042 components from the accepted V25 context.
- Substitute only the topology-repaired V4 eye at the frozen zero transform.
- Keep the separate C001/rail correction unresolved and outside this preview.

Review colors:

- orange: moved existing C009;
- green: frozen C001 owner;
- cyan: frozen topology-repaired eye;
- gray: all other frozen right-upper components.

## Validation performed and results

The moved C009 is one valid closed solid with:

- `38` faces;
- `1` solid;
- volume `227.9211976005 mm3`;
- preserved source face count and volume.

Primary relationship gates:

- repaired-eye clearance: `4.4763410511 mm`;
- C001 owner engagement: `5.1278418525 mm3`;
- positive collisions with the other 40 right-upper components: zero.

The review document contains exactly `43` shape objects: all `42` upper
components plus the repaired eye. Added support geometry count is exactly
zero. The V32 clearance and engagement values reproduce within the controlled
`0.000001 mm` / `0.000001 mm3` tolerances.

## Rejected or unsafe variants

- Do not reuse V27's visible bridge, Y-root, planks, or other added material.
- Do not move the exact V26 tapered rail; V31 rejected that route.
- Do not apply the destructive C009 cap trim; it removes about `96.85%` of the
  member.
- Do not delete C009; this route retains positive C001 engagement.
- Do not treat this visual preview as the separate C001 correction.
- Do not mirror, production-union, export, slice, generate G-code, or release
  structural ASA from V33.

## Exact regeneration command

    python3 -m py_compile \
      hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_upper_c009_reposition_preview_v33.py

    env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
      /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
      hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_upper_c009_reposition_preview_v33.py \
      --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-c009-reposition-preview-v33.json

## Next physical/visual review step

Open the V33 FCStd and inspect only two spatial facts:

1. The orange C009 is visually unobtrusive and remains inside the intended
   head volume rather than appearing in front of the eye.
2. The orange C009 visibly roots into the green C001 owner and is not floating.

The cyan eye and gray context are frozen references, not review candidates.
After explicit visual acceptance or rejection, update this checkpoint. If
accepted, preserve this exact one-sided C009 position while resolving the
separate non-visible C001/rail strategy. Bilateral validation remains held
until both right-side issues are closed.
