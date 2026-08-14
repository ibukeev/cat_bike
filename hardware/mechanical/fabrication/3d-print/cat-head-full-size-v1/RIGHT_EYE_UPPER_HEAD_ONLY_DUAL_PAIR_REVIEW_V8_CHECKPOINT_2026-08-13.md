# Right-eye upper-head-only dual-pair V8 checkpoint — 2026-08-13

## State

V8 is the current isolated right-side HS-11 review. It corrects the V7
ownership error: the right lower face owns **zero** eye-flange geometry, and
there is no pole, neck, bridge, or cantilever between that lower face and an
eye flange. Both head-side flange leaves are proposed additions to the frozen
`right_upper_head` shell only. They remain separate review solids until visual
approval; no owner Boolean has been performed.

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

## Accepted/frozen decisions and dimensions

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

## Validation performed

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

## Next physical/visual review

Open the V8 FreeCAD file. It defaults to the exact V9 bucket plus four exact
proposal leaves, with both shell contexts hidden.

1. Show `FROZEN__RIGHT_UPPER_HEAD_CONTEXT_V8`: confirm both objects whose names
   contain `HEAD__UPPER_HEAD_ONLY_V8__EXACT` lie inside and directly root into
   the upper-head shell, with no exterior protrusion.
2. Hide the upper-head context and show
   `FROZEN__RIGHT_LOWER_FACE_CONTEXT_ONLY_V8`: confirm the lower face has no eye
   flange, pole, neck, or bridge.
3. Confirm the two pairs are widely separated, each pair has aligned holes,
   and neither pair collides with the V9 eye bucket.
4. Only after explicit visual approval may the copied right owners be
   integrated and revalidated. Mirroring and print release remain later gates.
