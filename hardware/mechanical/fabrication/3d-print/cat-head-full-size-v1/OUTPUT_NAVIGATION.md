# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-standard-paired-flange-review-v6.blend`
- Current validation:
  `output/00-current-review/ear-root-standard-paired-flange-review-v6-validation.json`
- Current renders: `output/00-current-review/renders/`

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

The V1 outer connector positions were accepted on 2026-08-06. V2 was rejected
because its narrow end roots reinforced only the two outer head-side flanges;
it did not add owner-side mass to the matching eye-bucket flanges or either
lower flange pair.

V3 was accepted by the user on 2026-08-06 as the eye-mount structural-layout
baseline: four broad-base flange candidates per side, covering outer head,
outer eye, lower head, and lower eye. It remains unintegrated review geometry,
not a print release.

The accepted ear-root V2 coverage baseline is archived under
`output/60-ear-root-reviews/ear-root-restored-coverage-review-v2/`.

The accepted ear-root V3 fit envelope is archived under
`output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/`. It preserves
the accepted `13/9 mm` saddle relief, `2.5/1.0 mm` body/cap clearances, and
`0.4 mm` exact-ear clearance. Its corrected 41-sample, 60 mm outward/upward
service path is clear in world space with a `0.4 mm` deep-body margin. The
earlier transform-local rotate/slide proof is retained separately under
`ear-root-insertion-fit-review-v3-rejected-local-bvh-path/` and is rejected.

V5 is rejected because its fused orange parts still contained compound bridge
geometry between nonparallel frames. It is preserved at
`output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge/`.
Rejected V4 remains at
`output/60-ear-root-reviews/ear-root-removable-clamp-review-v4/`.

The current V6 review addresses F-10/F-11/F-12 with exactly one right-side
prototype. It copies the accepted eye-mount recipe: one orange rectangular tab
and one green parallel rectangular tab, each with one tapered broad owner base,
plus one coaxial M3 screw/washer/heat-set proposal. There is no left copy and no
bridge, convex-hull transition, or clamp geometry. Both owners are intersected,
the 0.3 mm mating gap and 0.0 mm axis error validate, the actual 41-sample path
has no conflicts, and the source geometry is unchanged. The conservative 0.4 mm
expanded flange envelope touches at the seated sample, and conservative driver
and finger envelopes touch the yellow owner body; those results remain explicit
review holds. V6 is a single-interface visual review, not a print release and
not authorization to replicate the other five locations.

C006 and all aluminum plate/rail geometry remain deferred and unchanged.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
