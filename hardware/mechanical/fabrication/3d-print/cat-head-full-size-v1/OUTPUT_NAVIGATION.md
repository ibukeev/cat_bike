# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first

- Current Blender review:
  `output/00-current-review/c002-outer-flange-upper-head-review-v1.blend`
- Current validation:
  `output/00-current-review/c002-outer-flange-upper-head-review-v1-validation.json`
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
- `output/50-eye-mount-reviews/`: completed or superseded C002 eye-mount
  constraint/design reviews retained for traceability.

## Current decision state

The requested reinforcement additions were reviewed as “much better” on
2026-08-05. That acceptance applies only to the reinforcement direction; it is
not authorization to print or modify aluminum.

The current C002 review replaces each rejected floating outer mount with the
exact Gate 6 flange and M2.5 interface plus a compact tapered root that overlaps
the matching upper-head shell. This is visual-review geometry only. It has not
been Boolean-unioned into the production upper-head pieces, exported to STL, or
released for printing.

C006 and all aluminum plate/rail geometry remain deferred and unchanged.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
