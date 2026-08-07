# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-removable-clamp-review-v4.blend`
- Current validation:
  `output/00-current-review/ear-root-removable-clamp-review-v4-validation.json`
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

The current V4 review addresses F-10/F-11/F-12 without changing the accepted
yellow V3 bodies or exact Gate 8 source shells. Each side has three separated
interior joints: orange moving flange, green fixed owner-shell anchor, blue
removable two-plane clamp, and brass M3 heat-set hardware. The blue clamps and
screws are removed before the verified service motion. Both 41-sample paths,
the `0.4 mm` orange-flange margins, tool/finger corridors, seated shell
clearance, and exact-source fingerprint checks pass. Exterior renders show no
green or blue retention blocks. The green anchors are individually manifold
and broadly rooted, but both cavity-bearing and solid-first source-shell union
trials damaged right-shell topology. V4 therefore remains a concept review,
not a print release; coupons and a topology-safe shell-integration pass remain
required.

C006 and all aluminum plate/rail geometry remain deferred and unchanged.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
