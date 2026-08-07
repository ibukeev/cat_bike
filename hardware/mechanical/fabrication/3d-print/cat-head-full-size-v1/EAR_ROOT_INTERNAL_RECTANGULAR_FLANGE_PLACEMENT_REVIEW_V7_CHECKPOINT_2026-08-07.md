# Ear-root internal rectangular-flange placement review V7 checkpoint — 2026-08-07

## Status

V7 is the current **placement-only** review for F-10/F-11/F-12. It contains one
right-side test location and exactly two plain parallel rectangular tabs: one
orange moving/insert-owner tab and one green fixed/head-owner tab.

This is not print released. Do not add holes or hardware, mirror or replicate
the pair, integrate it into source shells, export STL/G-code, or start ASA
parts until the user explicitly accepts this single placement.

## Current review files

- Blender review:
  `output/00-current-review/ear-root-internal-rectangular-flange-placement-review-v7.blend`
- Validation:
  `output/00-current-review/ear-root-internal-rectangular-flange-placement-review-v7-validation.json`
- Full-head context:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-full-head-context.png`
- Isolated two-tab view:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-pair-isolated.png`
- Orange/yellow owner-root cutaway:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-orange-owner-root.png`
- Green/gray owner-root cutaway:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-green-owner-root.png`
- Exterior baseline/candidate comparisons:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-exterior-{front,right,top}-{baseline,candidate}.png`

Useful Blender collections:

- `EAR7_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED`;
- `EAR7_EXACT_EARS_CYAN__UNCHANGED`;
- `EAR7_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED`;
- `EAR7_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE`;
- `EAR7_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED`;
- `EAR7_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN`.

The four cutaway objects are derived validation displays only. They split each
tab into the section inside its owner and the section outside its owner. They
are hidden in the default blend, are not connector parts, and are never used in
silhouette, topology, motion, or source-geometry validation.

## Source of truth and regeneration

- Generator:
  `source/generate_ear_root_internal_rectangular_flange_placement_review_v7.py`
- Config:
  `config/ear-root-internal-rectangular-flange-placement-review-v7.json`
- Accepted fit-body source remains V3:
  `config/ear-root-insertion-fit-review-v3.json`
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

Exact regeneration command from repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_internal_rectangular_flange_placement_review_v7.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-internal-rectangular-flange-placement-review-v7.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review
```

## Decisions and dimensions

- One right-side prototype at location A; zero left-side prototypes.
- Two equal, parallel, ordinary rectangular tabs in one shared frame.
- Each tab: `16 × 10 × 3.2 mm`.
- Measured mating gap: `0.3 mm`.
- Owner-root inset: first `1.0 mm` begins behind the exterior surface.
- No separate root object, broad base, wedge, trapezoid, bridge, convex hull,
  clamp, boss, screw hole, screw, washer, nut, insert, or access envelope.
- No modification to accepted V3 fit geometry or the exact Gate 8 source meshes.

## Validation performed and results

- Generator syntax and config JSON: pass.
- Exact Gate 8 source mesh count: 31; all fingerprints unchanged.
- One orange tab, one green tab, zero left prototypes, zero hardware, zero holes.
- Shared-frame axis dot products are effectively zero; both owner-frame
  alignments are `0.9724`.
- Orange/green measured gap: `0.3 mm`.
- Orange tab intersects its yellow owner: 15 triangle pairs.
- Green tab intersects its gray owner: 8 triangle pairs.
- Review-only Boolean cutaway volumes prove nonzero owner roots:
  orange `55.5905 mm³`, green `57.0315 mm³`.
- Moving yellow-body/orange-tab composite: one connected component, zero
  boundary edges, zero non-manifold edges, 42 faces.
- Seated actual structural hits: none. Green unintended-shell hits: none.
- Accepted V3 deep-body service path: clear for all 41 samples with a `0.4 mm`
  margin.
- Actual tab path conflicts: none.
- Conservative `0.4 mm` expanded orange-tab envelope: **not clear at the seated
  sample**; it reports 11 triangle pairs against `right_upper_head`. This is an
  explicit hold for the next dimensional iteration, not a print pass.
- Exterior baseline/candidate comparison: front, right, and top are exactly
  pixel-identical at 1100 × 1100; zero changed channels and zero maximum delta.
- No STL, G-code, slicer project, fabrication output, or print release created.

## Rejected or unsafe variants

- V4 loose clamp/bridge remains rejected.
- V5 compound bridge remains rejected.
- V6 broad/tapered exterior-normal bases and early hardware proposal are
  rejected and archived under
  `output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/`.
- Do not recreate an exterior horn, broad base, wedge, trapezoid, clamp,
  compound connector, or separate flying flange.
- Do not interpret the clear uninflated path as physical tolerance approval;
  the conservative `0.4 mm` flange envelope remains unresolved.

## Preserved workstreams

V7 does not modify the accepted V3 fit body, exact ears, exact upper-head source
geometry, eyes, lower-face/rear-cassette ownership, reinforcement direction,
C006, or the aluminum plate/rail `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.

## Next visual review

1. Open the V7 Blender file and confirm the full head remains intact.
2. Isolate the orange and green prototype collections; confirm there are exactly
   two equal, parallel rectangular tabs with a narrow gap and no outside horn.
3. Review the orange/yellow and green/gray cutaway renders. The narrow yellow or
   gray band is the Boolean-proven portion embedded in that owner; the remaining
   orange or green area is the tab extending into the head interior.
4. Compare each exterior candidate render with its baseline. They should be
   visually identical because the automated pixel comparison is exactly zero.
5. Approve or reject only the tab shape, internal direction, owner-root location,
   and `0.3 mm` gap. Hardware and replication are deliberately the next gate.
