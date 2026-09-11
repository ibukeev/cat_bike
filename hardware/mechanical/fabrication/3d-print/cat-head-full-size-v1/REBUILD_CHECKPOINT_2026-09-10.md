# Large-head rebuild checkpoint — 2026-09-10

Subsequent archive retirement: _archive_admin/ was permanently removed after
hash verification. .cleanup-recovery/ remains intact pending explicit GitHub
backup approval. Current state and inventories are in
[the retirement record](../../../../../docs/cleanup/2026-09-10/README.md).
The cleanup verifiers below describe earlier snapshots and are not current
whole-repository verification commands after that later deletion.

The user authorized maximum large-head cleanup because it will be rebuilt.
This was filesystem cleanup only. No CAD, geometry generation, rendering,
slicing, geometry dimensions, contract pins or print approvals changed.

## Retained state

Use [the rebuild index](README.md) and [167 geometry hashes](RETAINED_FILES.json).
V6 is the latest documented working snapshot; V5 is missing-socket recovery;
V2 is the editable lower-print source. Manual lower-front states/masters, the
bilateral V3 eye release, V34/V10 context, accepted ear-fit V3 and rear-cassette
V5 remain. None collectively establishes a new baseline or whole-head release.

The tiny modular 100 mm package and its Gate 1–7 inputs remain. Final midsize
Rev112/113 tooling and its existing fail-closed guards are unchanged.
Lower-print voxel size remains 0.25 mm, with 27 right and 16 left connected
shells; the old right slicer handoff reported eight auto-repaired errors.
No new structural or physical validation was performed.

## Removed and recoverable

Removed 2,956 obsolete files/links: old review trees, staging, caches, backups,
unnamed copies, withheld lower V1–V3 prints, trial G-code and one-off tooling.
Active disk usage fell from 2.2 GiB to about 506 MiB, roughly 77%.
Assets, templates, electrical/lighting files, sibling CAD packages and the
separate historical _archive_admin tree were not pruned.

RIGHT_TOP_PRINT.3mf was the stopped missing-socket trial: do not resume it.
RIGHT_TOP_PRINT_2.3mf and assembly.3mf are user records with unconfirmed print
status. Existing output names and validation files do not approve later edits.

Recovery archive:
`.cleanup-recovery/2026-09-10-large-head/retired-files.tar.gz`
(1,392,631,518 bytes, about 1.30 GiB). The adjacent manifest contains the
archive SHA-256, original hashes, exact keep/remove list and verification.
Each archived entry was read back and verified before deletion.
The archive remains on this disk and is ignored by Git; active-folder reduction
is not the same as net disk space freed.

Extract into a fresh directory, never over the cleaned files:

```bash
large_head_recovery="$(mktemp -d /tmp/cat-bike-large-head-recovery.XXXXXX)"
tar -xzf .cleanup-recovery/2026-09-10-large-head/retired-files.tar.gz -C "$large_head_recovery"
```

## Verification

- 2,179 protected original repository files/links unchanged; all retired paths absent.
- Broad suite: 372 tests; identical 10 failures, 13 errors and 36 skips before/after.
  Failing test IDs, error types and persistent large-head inputs read match.
- Existing failures include stale/rejected CAD contracts, retired report fixtures,
  two missing-FreeCAD imports, and the old lighting-map test expecting glow_pairs.
  No contracts, validation pins or safety guards were changed to mask failures.
- The 17 final-head/tooling tests pass. Mapper and all 10 lighting patterns pass.

Commands from repository root:

```bash
python3 -B .cleanup-recovery/2026-09-10-large-head/cleanup.py verify
env -u CAT_HEAD_FREECAD_APPDIR PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/automated
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract tests.automated.test_cat_head_visible_freecad_review_copy
node tests/automated/validate_mvp_bike_patterns.js
```

The broad-suite command still exits nonzero. Matching its earlier result proves
cleanup preservation, not all-green CAD tooling. Prepare/apply are one-time phases:
do not repeat them. Earlier cleanup manifests describe earlier repository snapshots;
use this large-head manifest for current whole-repository verification.

## Regeneration and next physical review

There is no single regeneration command for manually edited V6/V5/V2 or the
manual lower masters. Begin a rebuild in a new, user-approved design document.
Historical lower-mesh commands remain in [the working record](working/README.md);
the exact tiny command is in [GATE7_SMALL_TEST_PRINT.md](GATE7_SMALL_TEST_PRINT.md).
Do not run them to overwrite retained evidence. Midsize regeneration still needs
a fresh authorized preflight and reviewed pins after the earlier path migration.

Review actual BM parts, record fit/failures, confirm which shell, eyes, ears,
rail and aluminum dimensions carry forward, then ask the user to select one
canonical source and a bounded numeric design contract before CAD work.

## GitHub backup — awaiting explicit approval

Git LFS 3.8.0 is installed user-locally and configured only for this repository.
Root .gitattributes defines the mechanical large-file policy. Selected source,
docs, tests and retained build packages are staged, including all 167 geometry
files in RETAINED_FILES.json; their LFS SHA-256 values match the original bytes.
The complete staged LFS selection has 209 paths / 187 unique objects.
Archive payloads, tmp diagnostics and unselected historical tests are excluded.

Permission review blocked committing/pushing that payload to ibukeev/cat_bike
main until the user explicitly approves the destination and files. No commit,
push or history rewrite occurred. The large-head cleanup recovery archive is
still available; finish and verify the remote backup before deleting it.
