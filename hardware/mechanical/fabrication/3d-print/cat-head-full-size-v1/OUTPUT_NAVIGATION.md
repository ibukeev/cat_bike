# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the current
review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/requested-reinforcement-additions-review-v1.blend`
- Current validation:
  `output/00-current-review/requested-reinforcement-additions-review-v1-validation.json`
- Current renders: `output/00-current-review/renders/`

## Folder map

- `output/00-current-review/`: the single review currently awaiting or most
  recently receiving user review. Review files are placed directly here.
- `output/10-design-gates/`: Gate 1 through Gate 8 historical design outputs,
  test prints, shells, eye modules, and glow-panel work.
- `output/20-rear-cassette/current-baseline-v5/`: accepted lossless rear-cassette
  repartition used by later reinforcement work.
- `output/20-rear-cassette/history/`: rejected or superseded rear-cassette seam,
  cut, and repartition iterations.
- `output/30-reinforcement-baselines/`: the lower-reinforcement ownership and
  approved horizontal-seam review files used to generate the current review.
- `output/40-prototypes/`: independent fabrication experiments, currently the
  mirror-facet cap prototypes.

## Current decision state

The requested reinforcement additions were reviewed as “much better” on
2026-08-05, and work may move to the next task bucket. This is acceptance of
the reinforcement direction only; it is not authorization to print or to
modify aluminum.

The next independent task bucket is the rejected C002 eye-mount redesign. The
C006 replacement connector remains deferred until it can be coordinated with
the aluminum plate/rail workstream.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
