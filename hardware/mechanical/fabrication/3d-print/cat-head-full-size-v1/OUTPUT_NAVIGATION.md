# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-dual-set-reinforced-rectangular-flange-review-v8.blend`
- Current validation:
  `output/00-current-review/ear-root-dual-set-reinforced-rectangular-flange-review-v8-validation.json`
- Full-head context:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-full-head-context.png`
- Right translucent piece with both orange roots:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-right-translucent-piece-two-orange-roots.png`
- Right-side two-set isolated view:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-right-two-connector-sets-isolated.png`
- Left equivalents use the same names with `left` in place of `right`.
- Per-owner cutaways are named
  `ear-root-dual-set-reinforced-rectangular-{left,right}-{a,b}-{orange,green}-owner-root.png`.

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

The current V8 review contains two connector sets on each translucent ear piece:
four connector sets and eight tabs total. Every tab is a plain
`22 × 12 × 4 mm` rectangle with a `0.3 mm` gap. The two locations on each piece
are `34.9211 mm` apart. No separate base, wedge, trapezoid, bridge, clamp, hole,
fastener, or access envelope exists.

Every actual left/right owner root is proven by a direct Boolean cutaway. The
minimum overlap volume is `80.1946 mm³`; the green roots are approximately
`105–107 mm³`. Both moving translucent-piece/two-tab composites are manifold.
Actual seated geometry and both 41-sample motion paths are clear. The
conservative `0.4 mm` expanded moving-tab envelopes touch the upper heads only
at the seated sample, so tolerance clearance remains a review hold.

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
