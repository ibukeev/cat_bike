# Rejected Post-Feedback Cat-Head Work Archive

## Status and scope

Archived on 2026-08-04 at the user's direction. This archive contains the
cat-head work performed after the physical-print feedback checkpoint. It is
rejected for production use and must not be treated as print authorization.

- Physical-feedback baseline: commit `02053c4`
- Rejected tracked range: `9be375f` through `e4e8a88`
- Recoverable Git branch:
  `archive/rejected-post-feedback-2026-07-28-to-2026-07-31`
- Active `main` restores the rejected shell work to the tracked contents of
  `02053c4` by a new rollback commit, with the explicitly preserved aluminum
  plate/rail workstream documented below; Git history is not rewritten.

The tracked rejected range contains 121 changed paths and approximately
48,189 inserted lines. The archive branch is the authoritative record for all
tracked source, configuration, tests, checkpoints, and review summaries.

## Preserved active metal workstream

The aluminum plate/rail workstream was initially included in the broad
post-feedback rollback, then restored to active `main` at the user's direction.
The active preserved scope includes:

- V0.3/V0.4/V0.5 shared-interface definitions and helper code;
- V0.4/V0.5 aluminum plate, rail, ordered-angle, plug, spacer, and cheek
  generators/configuration;
- metal checkpoints and validation summaries;
- the shared-interface regression test; and
- generated `v04-finalized-interface`, `v04-m2-angle-stock`, and
  `v05-m2-coordinated-centers` outputs in the metal workstream.

The metal work remains a preserved design workstream, not fabrication
authorization. Five shell-side shared-interface contract/preflight artifacts
are retained in the active tree solely so the preserved metal regression test
remains reproducible: the interface preparation helper, two interface config
files, and two validation summaries. They are reference data, not active shell
geometry or design approval. All Gate 9 production geometry, candidate
generators, and generated head outputs remain quarantined. The interface
contracts must be explicitly reconciled with the next user-approved shell
baseline before regeneration, metal cutting, or drilling.

## Archived generated outputs

Ignored generated artifacts were moved out of the active fabrication tree:

- `generated-output/` — approximately 5.1 GB of Gate 9 review models, STLs,
  renders, and slicer reports.
- `metal-generated-output/` — temporary quarantine location used during the
  rollback; its V0.4/V0.5 contents were restored to the active metal
  workstream after the user clarified that this work must be preserved.

These directories remain ignored by Git through the adjacent `.gitignore`.
They are preserved locally for forensic comparison only.

The active full-size output tree retains only Gate 1 through Gate 8 and the
pre-feedback mirror-facet outputs.

## Accepted decisions retained at the rollback baseline

- The physical-print feedback document in commit `02053c4` is authoritative.
- The exact Gate 8 geometry that produced the physical print is the restart
  baseline.
- The previous physical print and its visible surfaces remain the visual
  authority until the user explicitly approves a later change.
- No post-feedback Gate 9 candidate is accepted for printing.

## Validation performed

- Confirmed the working tree was clean before archiving.
- Confirmed `02053c4` introduced the physical-feedback checkpoint.
- Created the archive branch at rejected commit `e4e8a88` before rollback.
- Confirmed all explicitly enumerated Gate 9 generated-output directories were
  moved into `generated-output/`.
- Confirmed the three post-feedback metal-output directories were preserved,
  then restored to the active metal output tree.
- Confirmed Gate 1 through Gate 8 generated outputs remain in the active output
  tree.
- Ran `python3 -m unittest tests.automated.test_cat_head_shared_interface` on
  the preserved metal/interface boundary: 9 tests passed.

No geometry, slicing, or physical validation is claimed by this archive
operation.

## Rejected or unsafe work

Rejected Gate 9 shell work after `02053c4` is quarantined from the active
design, including Gate 9 rear architecture, service seams, shell-side socket
coordination, body-seam revisions, the V10 exposed rectangular primary ear
interface, and the V11 under-ear insert/anti-flap candidate. The separate
aluminum plate/rail workstream is preserved actively as described above.

Specific observed reasons include:

- contaminated review scenes containing legacy duplicates and audit/tool
  envelopes;
- incomplete whole-head review handoff;
- visible primary-ear connector geometry;
- unacceptable under-ear transparent-region appearance;
- missing final cross-rib reinforcement integration; and
- automated digital passes that did not establish visual acceptability.

Do not regenerate, slice, print, or fabricate from the archive unless the user
explicitly requests forensic comparison.

## Exact recovery commands

To inspect the rejected tracked state without changing `main`:

```bash
git switch archive/rejected-post-feedback-2026-07-28-to-2026-07-31
```

Return to the active rollback:

```bash
git switch main
```

The original per-candidate regeneration commands remain in the checkpoint
files on the archive branch. Generated artifacts are already preserved locally
under this archive directory.

## Next review step

Do not resume by modifying Gate 9. First reconstruct one clean, unchanged,
orbitable assembly from the exact Gate 8 files that produced the physical
print. Compare that assembly with the physical prototype and the authoritative
feedback document. Make no geometry changes until the user approves that
baseline review artifact.
