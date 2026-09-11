# Large head — rebuild references

Cleaned on 2026-09-10 at the user's request: the large head will be rebuilt.
Only selected working states, physical-print records, frozen shape references,
and shared/tested tooling remain. Retention is not approval to print or a choice
of the next canonical CAD baseline. No geometry was opened, resaved, or regenerated.

## Start here

| Need | Retained files |
| --- | --- |
| Latest documented working snapshot | [Working assembly V6](output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V6.FCStd) |
| Missing-socket recovery source | [Working assembly V5](output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V5.FCStd) |
| Editable source for selected lower prints | [Working assembly V2](output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd) |
| Selected left/right lower STL and 3MF packages | [Working print records](working/README.md) |
| Eye release and manual lower masters | [Selected print set](output/FINAL_PRINT_SET/README.md) |
| Separate manual lower-front states and sector recovery | [User-edited lower-front files](output/70-freecad-pilots/review-only/lower-front-bilateral-feedback-cleanup-review-v4/) |
| Latest right-upper slicer setup | [10 mm brim layout](output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/README.md) |
| Frozen original whole-head visual reference | [Blender V10](output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend) |
| Accepted fit-body reference | [Ear fit V3](output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/ear-root-insertion-fit-review-v3.blend) |
| Rear-cassette ownership reference | [Rear cassette V5](output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.blend) |
| Earlier frozen recovery context | [FreeCAD V34](output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-deletion-review-v34/CAT_HEAD_RIGHT_UPPER_C009_DELETION_REVIEW_V34.FCStd) |

Original filenames and retained output paths are intentional: shared inputs,
existing contracts and tiny/midsize links depend on them. The old review trees
are not being retained as another active archive.

## Rebuild cautions

- V6 is unfinished working CAD, not a print-ready whole head. V5 is important
  because a prior V6 cleanup lost the right socket/root; see the
  [recovery checkpoint](REAR_INTERFACE_V06_V8_RIGHT_SOCKET_RECOVERY_CHECKPOINT_2026-08-23.md).
- RIGHT_TOP_PRINT.3mf was the stopped missing-socket trial and has been retired.
  RIGHT_TOP_PRINT_2.3mf and assembly.3mf remain as user records with unconfirmed status.
- The selected lower meshes retain their recorded multi-shell and slicer-repair
  limitations. Do not infer structural validation from a saved STL or 3MF.
- Reuse the measured fit feedback and aluminum interface records; do not
  reconstruct a new baseline by mixing objects from these historical versions.

## Shared dependencies and recovery

Gate 1–7 inputs and the modular 100 mm prototype remain under output/10-design-gates/
because the separate [tiny prototype package](../cat-head-tiny-prototypes/README.md)
uses them. Final midsize Rev112/113 tooling and its runtime manifest remain at
their pinned paths. Existing generation holds were not changed or bypassed.

One-off scripts/configs, intermediate reviews, caches, backups, rejected print
versions and trial G-code were archived. Remaining source includes reusable
checks and code still read by existing tests; old generators may require archived
inputs and are not a supported one-command rebuild pipeline.

See [the checkpoint](REBUILD_CHECKPOINT_2026-09-10.md),
[retained geometry hashes](RETAINED_FILES.json), and
[project cleanup record](../../../../../docs/PROJECT_CLEANUP_PLAN.md).
