# Output Folder Archive View Checkpoint — 2026-08-16

## Scope and result

The `opposite-side-flange-pilot-v1` output root now has a clean, recoverable
navigation layer. This operation changed no CAD geometry, deleted no artifact,
and moved no canonical review directory.

- `00-current/README.md` states the active working set and next CAD bucket.
- `.hidden` hides 76 superseded/rejected directory names from Nautilus.
- `90-archive/2026-08-16/` categorizes those 76 directories using verified
  relative symlinks back to their unchanged canonical paths.
- The archive covers 742 files and 292,275,854 bytes without copying or moving
  their contents.
- Thirty-two accepted/current or deliberately preserved directories remain
  visible at the pilot root.

## Accepted decisions and constraints

- V33 C009 repositioning is rejected because the member floats in the
  translucent under-ear panel region.
- The next structural proposal must start from the accepted pre-V33 right-upper
  baseline, delete C009, add no replacement member, and remain one-sided until
  full-context review.
- Existing canonical paths, regeneration configs, checkpoints, hashes, metal
  workstream data, rear-cassette data, C006 data, and local user changes remain
  untouched.
- The locally modified `right-eye-one-body-serviceable-module-review-v1` and
  `right-eye-upper-rim-structural-root-review-v1` directories are explicitly
  kept visible and were not included in this cleanup change set.

## Current files

- Navigation: `OUTPUT_NAVIGATION.md`
- Current pointer: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/00-current/README.md`
- Nautilus visibility index: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/.hidden`
- Archive guide: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/90-archive/2026-08-16/README.md`
- Verification manifest: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/90-archive/2026-08-16/ARCHIVE_MANIFEST_2026-08-16.json`
- Organizer: `source/organize_opposite_side_flange_pilot_archive.py`

## Validation performed

- Python byte-code compilation passed.
- Dry run reported 76 archive candidates and 32 preserved directories.
- Applied view reported 76 manifest entries, 76 unique `.hidden` entries, and
  76 archive links.
- All 76 archive links resolve to existing canonical directories; zero are
  broken.
- Category counts: legacy/duplicate 1, panel/AB 7, upper head 14, lower face 1,
  eye 35, and ear 18.
- `00-current` and both known locally modified directories remain visible.

## Rejected or unsafe variants

- Do not physically move the 76 canonical directories. Many are referenced by
  regeneration configs and checkpoints; moving them would break traceability.
- Do not delete rejected variants. They remain immutable historical evidence.
- Do not use V33 as a print source.

## Exact regeneration command

From the repository root:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/organize_opposite_side_flange_pilot_archive.py --apply
```

The command is idempotent: existing verified links are retained and the
manifest plus `.hidden` index are regenerated from the current directory set.

## Next review

Refresh or reopen the pilot root in Nautilus to load `.hidden`, then open
`00-current/README.md`. The next physical/CAD review is the one-sided full
head, repaired eye, and translucent under-ear context after C009 is deleted.
Mirror, production union, STL export, slicing, G-code, and final ASA release
remain held.
