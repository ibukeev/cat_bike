# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend`
- Current validation:
  `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10-validation.json`
- Full-head context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-full-head-context.png`
- Right user-marked relocation context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-user-marked-relocation-context.png`
- Left user-marked relocation context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-left-user-marked-relocation-context.png`
- Right translucent piece with both orange roots:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-translucent-piece-two-orange-roots.png`
- Right-side two-set isolated view:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-two-connector-sets-isolated.png`
- Left equivalents use the same names with `left` in place of `right`.
- M3 bore close-ups are named
  `ear-root-marked-relocation-m3-through-bolt-{left,right}-{a,b}-m3-hole-alignment.png`.
- Per-owner cutaways are named
  `ear-root-marked-relocation-m3-through-bolt-{left,right}-{a,b}-{orange,green}-owner-root.png`.

## Folder map

- `output/00-current-review/`: the single review currently awaiting user
  approval. Review files are placed directly here.
- `output/10-design-gates/`: Gate 1 through Gate 8 historical design outputs,
  test prints, shells, eye modules, and glow-panel work.
- `output/20-rear-cassette/current-baseline-v5/`: accepted lossless rear-cassette
  repartition used by later reinforcement work.
- `output/20-rear-cassette/history/`: rejected or superseded rear-cassette seam,
  cut, and repartition iterations.
- `output/30-reinforcement-baselines/`: accepted reinforcement baselines and
  their historical ownership/interface reviews.
- `output/40-prototypes/`: independent fabrication experiments.
- `output/50-eye-mount-reviews/`: completed, accepted, or superseded eye-mount
  reviews retained for traceability.
- `output/60-ear-root-reviews/`: isolated ear-root constraints and redesign
  reviews retained independently from eye and aluminum work.

## Current decision state

The requested reinforcement additions were reviewed as “much better” on
2026-08-05. That acceptance applies only to the reinforcement direction; it is
not authorization to print or modify aluminum.

The eye-mount V3 structural-layout baseline was accepted on 2026-08-06: four
broad-base flange candidates per side, covering outer head, outer eye, lower
head, and lower eye. It remains unintegrated review geometry, not a print
release.

The accepted ear-root V2 coverage and V3 fit envelope remain archived under
`output/60-ear-root-reviews/`. V3 preserves the accepted `13/9 mm` saddle
relief, `2.5/1.0 mm` body/cap clearances, and `0.4 mm` exact-ear clearance.

V4, V5, and V6 remain rejected. V6 is preserved at
`output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/`.

V7 established the accepted conceptual direction of two plain internal
rectangular tabs, but was incomplete: it contained only one connector set total
and its roots were too small. It is archived at
`output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots/`.

V8's two-set concept was accepted and is archived under
`output/60-ear-root-reviews/ear-root-dual-set-reinforced-rectangular-flange-review-v8-concept-accepted-spacing-superseded-before-holes/`.

V9's screw-hole concept was accepted, but its placement is archived under
`output/60-ear-root-reviews/ear-root-wide-spaced-m3-through-bolt-review-v9-screw-hole-concept-accepted-placement-superseded-by-marked-relocation/`.

The current V10 review implements the user's marked move: the unmarked set is
retained, while the crossed set is relocated to the adjacent forward seam on
both translucent pieces. It has four connector sets and eight plain
`22 × 12 × 4 mm` tabs total with a `0.3 mm` gap. The two centers are
`45.115 mm` apart on each side, versus `36.9166 mm` in V9 and `34.9211 mm` in
V8. The final point is `1.9 mm` inward from the exact corner-mark projection so
the weakest left shell root remains above the `80 mm³` gate.

Every orange/green pair now has one common `3.4 mm` M3 clearance axis: four
fastener paths and eight drilled tab holes total. A `3.2 mm` gauge clears all
four paths, and minimum modeled bore-to-edge material is `4.05 mm`. Intended
hardware is four internal M3 × 16 through-bolts, two 7 mm OD washers per bolt,
and one M3 nyloc per bolt. Hardware is specified but not modeled.

Every actual left/right owner root is proven by a direct Boolean intersection.
The minimum overlap volume is `80.1945 mm³`; all four green roots are
`106.7–112.4 mm³`. Both moving translucent-piece/two-tab composites are manifold.
Actual seated geometry and both 41-sample motion paths are clear. The
conservative `0.4 mm` expanded moving-tab envelopes touch the upper heads and
their intentionally mated green tabs at the seated sample, so tolerance and
physical tool access remain review holds.

Flat single-color exterior occupancy masks are pixel-identical from front,
left, right, and top. Exact Gate 8 meshes and the accepted V3 fit bodies remain
unchanged.

C006 and all aluminum plate/rail geometry remain deferred, preserved, and tied
to `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
