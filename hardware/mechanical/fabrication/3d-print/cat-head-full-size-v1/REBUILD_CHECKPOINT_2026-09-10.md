# Large-head rebuild checkpoint — 2026-09-10

Subsequent archive retirement: both _archive_admin/ and .cleanup-recovery/ were
permanently deleted. Retained tracked files were independently downloaded from
GitHub and hash-verified before the final recovery deletion. Current proof is in
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

## Removed history — recovery subsequently deleted

Removed 2,956 obsolete files/links: old review trees, staging, caches, backups,
unnamed copies, withheld lower V1–V3 prints, trial G-code and one-off tooling.
Active disk usage fell from 2.2 GiB to about 506 MiB, roughly 77%.
Assets, templates, electrical/lighting files, sibling CAD packages and the
separate historical _archive_admin tree were not pruned.

RIGHT_TOP_PRINT.3mf was the stopped missing-socket trial: do not resume it.
RIGHT_TOP_PRINT_2.3mf and assembly.3mf are user records with unconfirmed print
status. Existing output names and validation files do not approve later edits.

The former large-head recovery archive (1,392,631,518 bytes) was permanently
deleted after verifying the retained-file GitHub backup. It is no longer a
restore source. Its original manifest is preserved byte-for-byte as
docs/cleanup/2026-09-10/large-head-manifest.json at repository root, alongside
the final retirement proof. Inventories cannot recreate deleted geometry.

## Verification

- 2,179 protected original repository files/links unchanged; all retired paths absent.
- Broad suite: 372 tests; identical 10 failures, 13 errors and 36 skips before/after.
  Failing test IDs, error types and persistent large-head inputs read match.
- Existing failures include stale/rejected CAD contracts, retired report fixtures,
  two missing-FreeCAD imports, and the old lighting-map test expecting glow_pairs.
  No contracts, validation pins or safety guards were changed to mask failures.
- The 17 final-head/tooling tests pass. Mapper and all 10 lighting patterns pass.

Retained-file checks from repository root:

```bash
git lfs pull
git lfs fsck --dry-run HEAD
env -u CAT_HEAD_FREECAD_APPDIR PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/automated
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract tests.automated.test_cat_head_visible_freecad_review_copy
node tests/automated/validate_mvp_bike_patterns.js
```

The broad-suite command still exits nonzero. Its historical before/after match
proved cleanup preservation, not all-green CAD tooling. The old cleanup scripts
were permanently deleted; do not try to rerun prepare/apply/verify from recovery.
Earlier manifests describe historical snapshots. The final retirement proof records
the later independent GitHub download and retained-file hash checks.

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

## GitHub backup — verified before final recovery deletion

Git LFS 3.8.0 is installed user-locally and configured only for this repository.
Root .gitattributes defines the mechanical large-file policy. Selected source,
docs, tests and retained build packages are committed and pushed, including all 167 geometry
files in RETAINED_FILES.json; their LFS SHA-256 values match the original bytes.
The complete LFS selection has 209 paths / 187 unique objects.
Archive payloads, tmp diagnostics and unselected historical tests are excluded.

The user explicitly approved ibukeev/cat_bike main and the selected payload.
Backup commit bd84d8449205c2828a92f32adfedc204fe48b4f8 was independently
downloaded; all 952 tracked files/links matched local bytes, Git LFS fsck passed,
and the 17 focused tests plus all 10 lighting patterns passed in that checkout.
Only then was .cleanup-recovery/ permanently deleted. Existing history was not
rewritten. The backup protects retained work, not deleted archive payloads.
Workflow revision is still pending user alignment; no CAD rules or approvals
were relaxed by this filesystem cleanup and backup.
