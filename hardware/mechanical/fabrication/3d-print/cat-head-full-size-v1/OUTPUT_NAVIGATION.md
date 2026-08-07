# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-internal-rectangular-flange-placement-review-v7.blend`
- Current validation:
  `output/00-current-review/ear-root-internal-rectangular-flange-placement-review-v7-validation.json`
- Full-head context:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-full-head-context.png`
- Two-tab isolated view:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-pair-isolated.png`
- Owner-root cutaways:
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-orange-owner-root.png`
  and
  `output/00-current-review/renders/ear-root-internal-rectangular-placement-right-green-owner-root.png`

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
- `output/40-prototypes/`: independent fabrication experiments, currently the
  mirror-facet cap prototypes.
- `output/50-eye-mount-reviews/`: completed, accepted, or superseded eye-mount
  constraint/design reviews retained for traceability.
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

The accepted ear-root V2 coverage baseline is archived under
`output/60-ear-root-reviews/ear-root-restored-coverage-review-v2/`.

The accepted ear-root V3 fit envelope is archived under
`output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/`. It preserves
the accepted `13/9 mm` saddle relief, `2.5/1.0 mm` body/cap clearances, and
`0.4 mm` exact-ear clearance. Its corrected 41-sample, 60 mm outward/upward
service path is clear in world space with a `0.4 mm` deep-body margin.

V4 and V5 remain rejected. V6 is also rejected: its broad/tapered bases were
placed on the wrong exterior-normal interpretation, the orange geometry visibly
protruded outside the head, and the green owner relationship was obscured. V6
is preserved intact at
`output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/`.

The current V7 review contains exactly one right-side location with two plain,
parallel, equal rectangular tabs. Each is `16 × 10 × 3.2 mm`, the mating gap is
`0.3 mm`, and the first `1.0 mm` is embedded in its owner as a compact
rectangular root. It contains no separate base, wedge, trapezoid, bridge, clamp,
hole, fastener, or access envelope. The cutaway proof collection is review-only,
hidden by default, and does not alter connector geometry.

Front, right, and top exterior baseline/candidate renders are pixel-identical:
zero changed channels and zero maximum channel delta. The actual 41-sample
motion has no collision, but the conservative `0.4 mm` expanded flange envelope
touches `right_upper_head` at the seated sample. V7 therefore remains a
placement-only visual review. Do not mirror, replicate, add hardware, integrate
with source shells, export for fabrication, or print it yet.

C006 and all aluminum plate/rail geometry remain deferred, preserved, and tied
to `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
