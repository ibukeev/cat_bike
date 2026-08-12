# Primary-ear bilateral through-channel review V1 — 2026-08-11

## Status

Digital pass; awaiting bilateral visual approval. The right V3 source was
approved by the user on 2026-08-11 with "OK good enough". This review is not a
fabrication or print release.

## Review file

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/primary-ear-bilateral-through-channel-review-v1/CAT_HEAD_PRIMARY_EAR_BILATERAL_THROUGH_CHANNEL_REVIEW_V1.FCStd`

The default view shows both integrated ears/head interfaces, the accepted left
A/B translucent-panel context, frozen remaining left upper-head context, and
four selected 3.0 mm proof shafts.

## Operation and frozen scope

- Mirror plane: YZ at `X=0`.
- Dimensions unchanged: `21.5 x 10.4 x 4.0 mm` flange envelopes, `1.20 mm`
  embed, `9.5 mm` bolt spacing, `3.4 mm` round channels, one ear-side
  `3.4 x 5.0 mm` slot, and `0.3500 mm` pair gap.
- Only copied left C001+A/B receives the mirrored channels and head flange.
- The accepted left C002, repaired C003, and C004-C041 remain separate frozen
  assembly context. They are not fused or repartitioned.
- Right V3, C006, eyes, lower face, rear cassette, reinforcement, and aluminum
  V0.5-M2 remain unchanged.

## Validation

- left C001+A/B interface: valid closed one-solid, 1986 faces, no
  self-intersections;
- left ear: valid closed one-solid, 57 faces, `17567.11 mm3`, no
  self-intersections;
- shaft clearances: A head/ear `0.1955/0.1956 mm`; B head/ear
  `0.1946/0.1962 mm`;
- left/right ear volumes and mirrored bounds match exactly;
- left/right head-flange volumes and mirrored bounds match exactly;
- left C001+A/B bounds are unchanged by the interface;
- aluminum interface SHA-256 remains
  `6326b211e4eef8c87a2b17687e2d68406682d21a6fa7c81ad52c8a1b9e713c79`;
- saved FCStd is valid, `10140583` bytes, SHA-256
  `3b70d35842f41c844d6e43a1ba676a1334eac5c5cd0e01d275dd09507af9abde`.

## Rejected and unsafe work

- Rejected mirroring the entire right upper head because that would replace
  the approved left A/B owner.
- Rejected treating the deliberate 41-part owner compound as one production
  solid.
- A heavy whole-C001 shaft-clearance query crashed FreeCAD; the review was
  rebuilt from frozen sources and validated against the local mirrored flange
  and ear interface instead.
- No production union of C001 with C002-C041, no STL/G-code, and no ASA release.

## Exact resume command

`FreeCAD hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/primary-ear-bilateral-through-channel-review-v1/CAT_HEAD_PRIMARY_EAR_BILATERAL_THROUGH_CHANNEL_REVIEW_V1.FCStd`

## User review

1. Confirm both sides look symmetrical and no flange protrudes outside either
   ear.
2. Confirm the four selected shaft proofs pass through the paired interfaces.
3. Hide the four `REVIEW_ONLY__*SHAFT*` objects and confirm the apertures
   remain visible.
4. Confirm the accepted left A/B translucent-panel connectors look unchanged.
5. Inspect from inside for washer, nut, driver, and bolt-removal access.

Approval closes the primary-ear mirroring portion of HS-09. Structural shell
printing remains blocked by the remaining gates.
