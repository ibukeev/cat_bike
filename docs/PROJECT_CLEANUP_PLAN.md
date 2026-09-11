# Project cleanup record

Updated: 2026-09-10. Initial non-large-head cleanup completed on 2026-09-09.

## Permanent archive retirement — current status

The user subsequently authorized permanent deletion of both archive folders.
_archive_admin/ has now been deleted: 946 files, 5,399,146,082 regular-file bytes.
The active retained worktree was hash-verified unchanged before and after removal.
Its rejected generated outputs are gone; previously tracked source history remains.

.cleanup-recovery/ is still intact pending explicit GitHub backup authorization.
Git LFS is installed user-locally and configured for this repository. Selected
working files are staged, including all 167 retained large-head geometry files.
No commit or push occurred: permission review blocked the proposed GitHub write.

See [the retirement record](cleanup/2026-09-10/README.md) for the exact pending
backup scope and preserved inventories. Earlier sections below describe historical
cleanup snapshots, not the current availability of _archive_admin/. Their old
whole-repository verification commands should not be run after this retirement.

## Large-head rebuild cleanup — 2026-09-10

Completed after explicit authorization to clean the large head for a rebuild.
The active folder went from 2.2 GiB to about 506 MiB. Removed 2,956 obsolete
files/links: review iterations, copies, backups, staging, trial G-code and
unneeded one-off scripts/configs. Selected CAD/print bytes and shared tiny/midsize
dependencies are unchanged. Assets, templates and other packages were not pruned.

Start at the [curated rebuild index](../hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/README.md).
The [checkpoint](../hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/REBUILD_CHECKPOINT_2026-09-10.md)
records retained states, limitations, tests, recovery and next physical-review steps.
The retained geometry manifest records 167 file hashes; cleanup created no new release.

Recovery: `.cleanup-recovery/2026-09-10-large-head/retired-files.tar.gz`
(1,392,631,518 bytes, about 1.30 GiB), plus its verified manifest.
Every retired entry was SHA-verified before deletion. The ignored archive remains
on this disk, so active-folder reduction is not net disk saving.

Checks: 2,179 protected original entries unchanged; 17 final-head/tooling tests
and all 10 lighting patterns pass. The broad suite produces exactly the same
372-test result as before: 10 failures, 13 errors, 36 skips. Existing historical
failures were recorded, not fixed by changing design guards.

```bash
python3 -B .cleanup-recovery/2026-09-10-large-head/cleanup.py verify
```

Prepare/apply have completed and must not be repeated. Earlier verification
commands below are historical snapshots; use this verifier for the current repo.
No Git staging, commit, push or history rewrite was done. Templates and the
separate _archive_admin tree remain outside this cleanup.

## Reports and mounts — 2026-09-10

The user authorized emptying reports/ after retaining the selected lower-shell
print files, and retiring four obsolete head-mount concept files.

- reports/ is empty: no files, subfolders, or compatibility links.
- Eight unchanged files moved to cat-head-full-size-v1/working/right-lower/
  and working/left-lower/: STL, 3MF, input mesh and mesh-health JSON per side.
  Start at [the working index](../hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/README.md).
- Retired mount files: cat-head-mount-plan.md, cat-head-mvp-build-plan.md,
  and diagrams/cat-head-backplate-rail-concept.svg and .png.
- led-diffuser-mounting-plan.md is unchanged. Old project-plan and lighting
  links now point to retained build records and the later frame-fixed mount.
- Assets, templates, unrelated CAD/slicer files, and remaining large-head
  design history were preserved. No geometry or approval status changed.

Retained print files total 383,237,622 bytes (about 365 MiB). Another 288
original file/link entries were retired (about 219 MiB of regular-file data).
The verified recovery archive contains those entries plus 27 pre-edit files:

`.cleanup-recovery/2026-09-10-reports-mounts/retired-files.tar.gz`

Archive size: 121,888,304 bytes (about 116 MiB), 315 entries. It does not
duplicate the eight moved print files. Symlinks were archived without following
them; midsize release and validation targets remain. The adjacent manifest.json
records original hashes, old/new paths, allowed edits and verification results.

### Path migration and generation holds

Selected lower-print scripts and checkpoints now use working/right-lower/ and
working/left-lower/. Final midsize contracts and the evidence renderer use
existing curated release/validation paths. Only paths changed in contracts;
numeric values and source/artifact geometry hashes did not.

Original midsize preflight reports and authorization pins were not rewritten.
Both one-shot wrappers intentionally reject the changed contract hashes before
generation. Regeneration requires a new authorized preflight and reviewed pins;
cleanup does not create new PASS evidence or permit overwriting release files.

Old report-dependent large-head tools and regression fixtures are historical,
not currently runnable. Restore and verify required inputs before resuming them,
especially V34 six-view baseline images and C002 candidate evidence. Never
bypass missing-input/hash guards or reconstruct mixed geometry to compensate.

### Recovery and checks

Extract into a fresh directory for inspection, not over the cleaned project:

```bash
recovery_dest="$(mktemp -d /tmp/cat-bike-reports-recovery.XXXXXX)"
tar -xzf .cleanup-recovery/2026-09-10-reports-mounts/retired-files.tar.gz -C "$recovery_dest"
printf '%s\n' "$recovery_dest"
```

The eight moved print files remain at the manifest's mapped working paths.

```bash
python3 -B .cleanup-recovery/2026-09-10-reports-mounts/cleanup.py verify
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract tests.automated.test_cat_head_visible_freecad_review_copy
node tests/automated/validate_mvp_bike_patterns.js
```

The one-time prepare/apply phases have run; do not repeat them. No CAD generator,
geometry validation, render, slicing or fabrication was performed. Next:
separately review large-head history and agree template retention; templates
have not been changed.

## Initial cleanup — 2026-09-09

Before the initial-cleanup history below: on 2026-09-10 the user separately
deleted controller-box-v0 and controller-box-v1-complete-enclosure-proposal.
Those deletions were not performed or reversed by the cleanup script and are
excluded explicitly from its protected-file verification.

At the user's request controller-box-v1-flat-base-proposal was renamed to
controller-box-v1-printed-base. All 13 files matched their pre-rename hashes;
only README and the checkpoint were subsequently edited. Their originals are
in .cleanup-recovery/2026-09-10-reports-mounts/controller-rename-before.tar.gz.
The main cleanup manifest records the rename, file hashes and user-deleted
roots. The printed CAD and 3MF remain intact; its historical generator cannot
run without the deleted V0 source/configuration/base STL. Do not silently
restore those user-deleted folders.

The user has now requested the separate large-head cleanup review. The bulk
of that geometry has not yet been pruned; identify important working states
before discarding iterations. Templates remain unchanged pending agreement.

The old fabrication/cat-head-paper-prototype-instructions.md also disappeared
outside this cleanup after the initial inventory. It was not removed by our
script and was not restored; its original hash and the external removal are
recorded separately in the manifest.

Completed off-device checks: 17 final-head/tooling tests, the mapper and all
10 lighting patterns, 104 documentation links, and whitespace checks passed.
Eleven source/configuration files matched the originals after applying only
the declared path substitutions. Both midsize wrappers preserved five other
input pins and rejected the migrated contract before generation, as intended.

Final preservation check passed: 5,097 protected original entries were
unchanged, all eight moved print files matched their original hashes, and all
296 retired/moved source paths were absent. The controller's 11 non-document
files were unchanged. The recovery archive hash passed. The recovery manifest
is COMPLETE for reports, mounts and the controller rename; this does not mark
the newly requested large-head review complete.

## Next review: large-head working history

Read-only inventory: output/70-freecad-pilots is about 924 MiB,
output/20-rear-cassette/history about 256 MiB, and the slicer tilt-search
directory about 82 MiB (mostly four diagnostic G-code files). Three hidden
staging directories total about 37 MiB. Across the large-head folder, the
original hash inventory identifies 124 groups of byte-identical files with
59,073,924 redundant bytes; no duplicate files were removed in this pass.

The latest documented active assembly is RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V6.FCStd.
Keep V5 as the recorded recovery source and V2 as the selected lower-print
source, pending user confirmation of the final working states. V5 matches its
recorded SHA-256; current V6 is
ef8d8bc5cddb949583787bcc1e9453105dd9bc93bdc2fef0f784866b1362b599.
All are in output/70-freecad-pilots/opposite-side-flange-pilot-v1/
right-upper-as-printed-working-assembly-v1/.

Also protect the retained lower working packages, manual/final print sets,
user-edited lower-front files, and Gate 7 tiny-prototype files and dependencies.
Do not infer that the newest filename is complete or print-approved.

The remaining sections record the earlier cleanup. Descriptions of reports
compatibility links below are superseded by the 2026-09-10 section above.

## Where to start

- [Retained fabrication packages](../hardware/mechanical/fabrication/3d-print/README.md).
- [Tiny prototypes](../hardware/mechanical/fabrication/3d-print/cat-head-tiny-prototypes/README.md):
  single-shell and modular versions, both 100 mm.
- [Midsize Burning Man head](../hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/README.md):
  190 mm head, Rev112 eyes, Rev113 merged mouth, source CAD, and print projects.
- [Lighting collection](../software/pixelblaze-patterns/mvp-bike/README.md):
  111-pixel mapper, ten patterns, layout reference/generator, and validations.

## Preserved scope

`assets/` stays exactly as it was. Existing documentation and
`hardware/electrical/` were retained; this cleanup record and navigation
documentation were updated.

All large-head files remain unchanged, including its full-size directory,
rejected-work archive, metal/interfaces, shared templates, scale projections,
whisker work, and large-head generated reports. The eye-containment probes left
in `tmp/` and the root eye-audit marker also belong to that deferred review.

For the controller box, the successful V1 base and latest complete-enclosure
proposal remain, together with the V0 source/configuration and baseline base STL
required by the V1 generator. Its four explicitly rejected V0 STL exports and
backup files were archived. The V1 base README now reflects its recorded
successful physical print.

## Retained head packages

| Milestone | Current package |
| --- | --- |
| Tiny single shell, 100 mm | `hardware/mechanical/fabrication/3d-print/cat-head-tiny-prototypes/single-shell-100mm/` |
| Tiny modular model, 100 mm | `hardware/mechanical/fabrication/3d-print/cat-head-tiny-prototypes/modular-100mm/` |
| Midsize Burning Man head, 190 mm | `hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/` |

The modular entry links to its original Gate 7 files in the excluded large-head
tree. Its Blender assembly, 20 part STLs, three slicer projects, and generator
dependencies remain there unchanged.

The midsize package keeps:

- `source/user-final-edits/CAT_HEAD_MEDIUM_Ilya_FINAL_EDITS.FCStd` and the
  earlier manual STL/3MF inputs;
- the full Rev112 head package and Rev113 merged-mouth package under `releases/`;
- all three current slicer projects, including both head support profiles;
- original contracts, validation/evidence, release manifest, and final tooling links.

The head and two eye STLs in Rev113 link to the byte-identical Rev112 files.
The two original mouth panes remain as Rev112 validation inputs. Both head
slicer profiles and both tiny single-shell print jobs remain because their
exact physical-use history is not yet known.

The old `cat-head-small-v1/` directory is now a compatibility entry point.
Final small-head iteration/tooling paths under `reports/generated/` also link
to the midsize package. These preserve the existing pinned generator inputs and
historical final-review references without keeping the discarded iterations.

The only generator code change is the tiny single-shell script's repository-root
lookup, needed at its new directory depth. Its construction code and numeric
values are unchanged. New tiny generation writes to `output/`; retained files
are in `release/`. No geometry was regenerated, resaved, repaired, or re-exported.

## Removed from active folders

The cleanup retired 448 original file entries, including superseded tiny/midsize
iterations, duplicate reviews, obsolete experiment tests, backups, Python cache
files, four rejected controller STL exports, the midsize support-comparison
G-code files, and `tmp.txt`.

Fifty selected files were carried into the retained packages, with identical
exports linked instead of duplicated. About 631 MiB was removed from active
folders. This is active-tree reduction, not net disk-space savings: the recovery
archive remains locally.

## Recovery

The verified archive is
`.cleanup-recovery/2026-09-09/previous-files.tar.gz` (about 529 MiB).
It contains all 498 removed/relocated original file entries plus six original
documentation/configuration files, including uncommitted user changes.

`.cleanup-recovery/2026-09-09/manifest.json` records original paths and hashes,
retained copies, protected-file hashes, the archive hash, and verification
results. This local recovery directory is ignored by Git.

To inspect or recover an old file without overwriting the cleaned project,
extract the archive into a fresh temporary directory:

```bash
recovery_dest="$(mktemp -d /tmp/cat-bike-recovery.XXXXXX)"
tar -xzf .cleanup-recovery/2026-09-09/previous-files.tar.gz -C "$recovery_dest"
printf '%s\n' "$recovery_dest"
```

## Validation and reproducibility

- All 5,382 protected file entries matched their original hashes after cleanup.
- All 49 retained non-generator files matched their original bytes.
- All 12 Rev112 source/artifact release pins passed.
- All six pins in each final Rev112/Rev113 generator wrapper passed.
- The tiny generator differs from its archived original only in repository lookup;
  its Python syntax passed.
- All 18 checked compatibility links resolve inside this repository.
- Seventeen final-head/tooling unit tests passed.
- The lighting validator passed the mapper and all ten patterns.
- All 39 checked documentation links resolve.

Commands used for the cleanup:

```bash
python3 -B .cleanup-recovery/2026-09-09/cleanup_non_large_head.py prepare
python3 -B .cleanup-recovery/2026-09-09/cleanup_non_large_head.py apply
python3 -B .cleanup-recovery/2026-09-09/cleanup_non_large_head.py verify
```

The prepare/apply phases intentionally refuse a repeated cleanup. The verify
phase can be rerun to check protected files and retained artifacts.

Validation commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract tests.automated.test_cat_head_visible_freecad_review_copy
node tests/automated/validate_mvp_bike_patterns.js
```

Head regeneration commands remain in the
[single-shell guide](../hardware/mechanical/fabrication/3d-print/cat-head-tiny-prototypes/single-shell-100mm/README.md),
[modular guide](../hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/GATE7_SMALL_TEST_PRINT.md),
[Rev112 checkpoint](../hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/head-rev112/CHECKPOINT.md),
and [Rev113 checkpoint](../hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/mouth-rev113/CHECKPOINT.md).
Final one-shot generators still refuse existing outputs.

## Next separate review

Identify the important large-head states and evaluate that history on its own.
For the Burning Man recap, record the midsize head's actual slicer profile,
pane fit, mounting behavior, and field wear/failures. Historical geometry-release
flags remain unchanged; retaining a build record does not rewrite those flags.
