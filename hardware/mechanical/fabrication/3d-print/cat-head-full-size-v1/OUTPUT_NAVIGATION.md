# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/ear-root-insertion-fit-review-v3.blend`
- Current validation:
  `output/00-current-review/ear-root-insertion-fit-review-v3-validation.json`
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

The current ear-root V3 review addresses physical feedback F-07/F-08/F-09.
It preserves the accepted `13/9 mm` saddle relief, uses `2.5 mm` deep-body and
`1.0 mm` shallow-cap perimeter clearances, and adds `0.4 mm` local exact-ear
clearance. Both bodies are connected manifold mirrors with zero seated
intersections. Their 41-sample rotate-then-slide paths are clear, including a
`0.4 mm` expanded hidden-body margin. Old capture pads and the M2.5 retainer
are absent; retention/datums remain the next F-10/F-11/F-12 iteration. V3 is
not a finished part or print release. The user visually accepted the yellow
seated fit-body geometry on 2026-08-06.

C006 and all aluminum plate/rail geometry remain deferred and unchanged.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
