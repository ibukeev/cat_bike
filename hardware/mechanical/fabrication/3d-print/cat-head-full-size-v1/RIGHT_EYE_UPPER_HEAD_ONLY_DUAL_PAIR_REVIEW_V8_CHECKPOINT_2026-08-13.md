# Right-eye upper-head-only dual-pair V8 checkpoint — 2026-08-13

## State

**REJECTED on visual review.** The fabricated `INNER_UPPER` pair was not the
existing second connector pair and must not be integrated, mirrored, exported,
or printed. The interactive FreeCAD review has been cleaned to remove those
four duplicate mesh/exact objects and to restore the unchanged validated V7
second pair for identification only.

The restored second pair is geometrically valid, but its head-side leaf has
`0.0 mm3` overlap with `right_upper_head`, `26.2422 mm3` overlap with
`right_lower_face`, and a measured shortest distance of `25.4458 mm` to the
upper-head shell. Therefore it is not an upper-head-owned production solution.
Renaming it or joining it with a pole/bridge is explicitly disallowed. HS-11
remains open.

This is **not** a print release. No left mirror, STL, G-code, slicing, or ASA
printing is authorized from V8.

## Review/output files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/CAT_HEAD_RIGHT_EYE_UPPER_HEAD_ONLY_DUAL_PAIR_REVIEW_V8.FCStd`
- Blender source review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/CAT_HEAD_RIGHT_EYE_UPPER_HEAD_ONLY_DUAL_PAIR_REVIEW_V8.blend`
- Numeric validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/validation-v8.json`
- Review meshes/renders:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/review/`
- Locked contract:
  `config/right-eye-upper-head-only-dual-pair-review-v8.json`
- Generator:
  `source/generate_right_eye_upper_head_only_dual_pair_review_v8.py`
- Ownership audit:
  `source/audit_right_eye_upper_head_owner_edges_v8.py`

## Historical rejected V8 contract

- Preserve the validated outer pair on eye edge `[2,3]` unchanged:
  `12 x 8 x 4.8 mm`, one `2.8 mm` M2.5 through-hole per leaf.
- Replace the rejected lower-face-owned pair with an upper-head-owned pair on
  eye edge `[0,1]`, at `+0.30` of the edge length from its midpoint toward
  vertex 1.
- Replacement leaves: `18 x 18 x 4.8 mm`, one `2.8 mm` M2.5 through-hole per
  leaf.
- Both mating gaps: `0.300 mm`.
- Head-leaf exterior recess: `0.03 mm`; permitted positive exterior deviation:
  at most `0.02 mm`.
- Pair-center separation: `65.3136 mm` (minimum contract: `35 mm`).
- Freeze the V9 eye bucket, C046, C048, C006, lower face, rear cassette, shell
  panels, and aluminum workstream `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.

## Historical validation of the rejected fabricated pair

- FreeCAD/OCCT exact conversion: the V9 bucket and all four proposal leaves
  are valid, self-intersection-free, one-solid shapes.
- Each flange mesh is one connected watertight component with zero boundary
  and zero nonmanifold edges.
- Direct owner overlap:
  - outer head / upper head: `122.5160 mm3`
  - outer eye / V9 bucket: `247.0317 mm3`
  - inner-upper head / upper head: `1525.8565 mm3`
  - inner-upper eye / V9 bucket: `166.6481 mm3`
- Pair interference: `0.0 mm3` for both pairs.
- Minimum pair clearance: `0.3000 mm` for both pairs.
- Inner-upper head exterior deviation after clipping: `-0.000015 mm`.
- Lower-face flange count: `0`.
- Pole/neck/bridge count: `0`.
- Frozen-owner geometry modified: `false`.
- Owner Boolean, mirror, STL, and G-code export: all `false`.

## Rejected/unsafe variants

- The V8 `INNER_UPPER` head/eye additions: rejected as duplicate geometry at
  the wrong interface. They have been removed from the interactive FCStd.
- V7 lower-face-owned head flange and its pole/neck connector: rejected for
  wrong ownership and exterior protrusion.
- Eye edge `[1,2]` as a replacement mount: rejected because the bucket and
  upper-head owners lie on the same side of that edge; it necessarily creates
  a bridge/pole instead of two direct roots.
- A smaller `14 x 10 mm` candidate: rejected after exterior clipping left only
  about `4.487 mm3` of direct upper-head overlap.
- Multi-facet exterior clipping: rejected because it produced a nonmanifold
  proposal.

## Exact regeneration commands

Run from `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend --python source/generate_right_eye_upper_head_only_dual_pair_review_v8.py
blender --background output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-flange-local-skin-clip-review-v7/CAT_HEAD_RIGHT_EYE_ALL_FOUR_FLANGE_LOCAL_SKIN_CLIP_REVIEW_V7.blend --python source/audit_right_eye_upper_head_owner_edges_v8.py
```

## Current cleaned-review validation

- FCStd archive integrity: PASS (`449705` bytes).
- Restored existing second head leaf: valid one-solid, `421.49 mm3`.
- Restored existing second eye leaf: valid one-solid, `394.76 mm3`.
- Restored pair clearance: `0.3000 mm`; interference: none.
- Default review presentation: upper-head context, lower-face context, exact
  V9 eye bucket, accepted outer pair, and restored existing second pair in
  standard isometric view.
- No shell geometry, owner Boolean, mirror, STL, G-code, or print release was
  created by this cleanup.

## Next physical/visual review

Open the cleaned V8 FreeCAD file only to confirm identification: the fabricated
inner pair is absent and the restored existing second pair is the intended
pair. The next structural proposal must resolve the mutually incompatible
current facts—retain that location, require direct upper-head ownership, and
forbid a 25.4458 mm bridge—before any owner geometry is changed.
