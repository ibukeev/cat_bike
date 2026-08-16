# Right Upper C009 Deletion Review V34 Checkpoint — 2026-08-16

## Status

`PASS__REVIEW_ONLY_ONE_SIDED_C009_DELETION`

V34 is ready for visual review. It is not a production owner, STL, slicer
project, G-code, or ASA print release.

## Approved scope

- Start from the accepted pre-V33 V25 right-upper component manifest.
- Delete/exclude only the separate right-upper C009 component.
- Do not move or resize C009.
- Add no replacement member, support, reinforcement, or filler.
- Do not mirror, production-union, export, slice, or release ASA geometry.
- Show the retained right upper head with the repaired right eye, right lower
  face, right primary ear, and translucent under-ear A/B panel.

The rejected V33 reposition remains historical evidence only. It placed C009
through the translucent under-ear panel region; V34 intentionally uses the
simpler approved deletion instead.

## Current review files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-deletion-review-v34/CAT_HEAD_RIGHT_UPPER_C009_DELETION_REVIEW_V34.FCStd`
- Validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-deletion-review-v34/validation-v34.json`
- Change contract:
  `source/cad-change-control/pilot/right-upper-c009-deletion-review-v34.json`
- Generator:
  `source/cad-change-control/generate_right_upper_c009_deletion_review_v34.py`

## Output hashes

- FreeCAD review SHA-256:
  `2ff90641bf13ecebbd5ab7b5d388dd511b2577b0cc38df73030c7c77b83fad2b`
- Validation SHA-256:
  `c2e49a2c6f448a5690ba600cb3c27ca1e210d36d165236031fdc5c732ce56d4b`
- Contract SHA-256:
  `d4c4c91ccf9df5d26c0866f25f7be50da54f8fff0ebbc10b1c09de2d0064d2a2`
- Generator SHA-256:
  `05f9316136efc605fecbe104aba8bf0e6b08a7788687a23a485aa16a634a67ba`

## Validation performed

| Gate | Result |
| --- | --- |
| All hash-pinned inputs match | PASS |
| Source manifest is exactly C001 through C042 | PASS |
| Retained manifest is exactly V25 minus C009 | PASS |
| Retained component count | PASS — 41 |
| Every retained component copy is exact | PASS |
| Retained compound | PASS — valid, closed, 41 solids |
| C009 objects in review | PASS — 0 |
| Added/replacement/support geometry | PASS — 0 |
| Subtractive cut | PASS — none |
| Full-context copies are exact | PASS |
| Repaired eye | PASS — valid, closed, one solid |
| Mirror, production union, or export | PASS — none performed |

The removed C009 volume is `227.92119760049138 mm3`; its recorded repaired-eye
intersection was `27.728296869034583 mm3`. The retained source component sum is
`150217.21686335685 mm3`. The review compound contains all 41 retained solids.

FreeCAD 1.1.1 was used once after headless generation to show both review groups
and save the presentation state. That save changed no geometry. The final
FreeCAD hash above is the post-presentation file.

Two fail-closed preflight attempts produced no saved CAD: the first exposed an
exact V25 status-string mismatch; the second exposed a harmless approximately
`0.002 mm3` OCCT compound-order volume difference. The final preservation gate
compares the exact sum of the 41 individually copied components.

## Exact regeneration command

From the repository root:

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_upper_c009_deletion_review_v34.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-c009-deletion-review-v34.json \
  --overwrite-review-output
```

After regeneration, open the generated FCStd in FreeCAD, show
`RETAINED_RIGHT_UPPER_V34` and `FROZEN_FULL_CONTEXT_V34`, and save only the GUI
visibility state. Recompute the FCStd and validation hashes if that presentation
save changes the archive bytes.

## Next physical/visual review

Open the V34 FreeCAD review and confirm:

1. C009 is completely absent; there is no orange member, remnant, or replacement.
2. Deleting it did not create an unintended exterior hole, disconnected shell
   residue, or unsupported visible fragment.
3. The repaired eye, primary ear, and translucent under-ear A/B panel remain
   unobstructed in full right-side context.

Do not use V34 to judge or approve the separate residual C001-to-eye
intersection (`100.59904449678196 mm3`). That remains a held follow-up. Bilateral
validation, production-owner unification, STL export, slicing, G-code, and ASA
printing remain blocked pending later gates.
