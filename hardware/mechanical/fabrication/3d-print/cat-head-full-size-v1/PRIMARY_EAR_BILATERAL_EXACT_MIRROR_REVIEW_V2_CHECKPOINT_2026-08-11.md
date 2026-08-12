# Primary-ear bilateral exact-mirror review V2 — 2026-08-11

## Status

Digital pass and user visual approval on 2026-08-11 (`LGTM`). HS-09 is closed.
This is the frozen bilateral primary-ear source, not a print release.

Bilateral V1 is rejected because it reused a stale left C001/A/B owner containing
the obsolete four-hole lattice/pin connector. No geometry from that left owner is
present in V2.

## Current source and review files

- Approved immutable source:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-integrated-through-channel-review-v3/CAT_HEAD_RIGHT_PRIMARY_EAR_INTEGRATED_THROUGH_CHANNEL_REVIEW_V3.FCStd`
- Review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/primary-ear-bilateral-exact-mirror-review-v2/CAT_HEAD_PRIMARY_EAR_BILATERAL_EXACT_MIRROR_REVIEW_V2.FCStd`
- Numeric contract and validation:
  `config/primary-ear-bilateral-exact-mirror-review-v2.json`

## Construction

The new FreeCAD document contains exactly four independent final solids:

1. copied approved right integrated upper-head owner;
2. copied approved right integrated ear owner;
3. exact YZ-plane mirror of item 1 at `X = 0`;
4. exact YZ-plane mirror of item 2 at `X = 0`.

The source document's dependency graph was not copied. No legacy left owner,
four-hole flange, lattice, pin, proof shaft, cutter, or audit object was inserted.

## Accepted dimensions retained unchanged

- mirror plane: YZ at `X = 0`;
- flange body: `21.5 x 10.4 x 4.0 mm`;
- owner embed: `1.2 mm`;
- pair gap: `0.35 mm`;
- two bolt centers: nominal `9.5 mm` apart;
- head channels: two round `3.4 mm` channels;
- ear channels: one round `3.4 mm` channel and one `3.4 x 5.0 mm` slot.

## Validation performed

FreeCAD `check_solid`, `verify_no_self_intersection`, bounding-box, volume,
surface-area, and element-count checks were run on all four objects.

| Solid | Faces | Solids | Volume (mm3) | Closed/valid | Self-intersection |
|---|---:|---:|---:|---|---|
| Right head | 1680 | 1 | 76127.47 | pass | none |
| Left head exact mirror | 1680 | 1 | 76127.47 | pass | none |
| Right ear | 57 | 1 | 17567.11 | pass | none |
| Left ear exact mirror | 57 | 1 | 17567.11 | pass | none |

The left and right topology, volume, surface area, Y/Z bounds, and sign-reversed
X bounds match exactly at the reported FreeCAD precision.

## Frozen and absent

- The approved right V3 source was not edited.
- Aluminum interface `CAT-HEAD-SHELL-ALUMINUM-V0.5` is unchanged.
- Eyes, lower faces, rear cassette, C006, reinforcement, and all other head
  components are unchanged and absent from this focused review.
- No STL, slicer project, G-code, or ASA print release was created.

## Rejected variants

- `primary-ear-bilateral-through-channel-review-v1` is rejected: it combined the
  approved right work with a stale left owner containing obsolete connector
  residue.
- Repairing that stale left owner face-by-face is rejected: the approved right
  final solids are the only bilateral source of truth.

## Exact resume command

`FreeCAD hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/primary-ear-bilateral-exact-mirror-review-v2/CAT_HEAD_PRIMARY_EAR_BILATERAL_EXACT_MIRROR_REVIEW_V2.FCStd`

## Next physical review

Open the V2 review file and confirm:

1. both sides show the same approved two-hole interface;
2. the opposite side contains no four-hole lattice, pins, cylinders, or residue;
3. each ear and head flange meet in the same way on both sides;
4. nothing protrudes from the exterior ear surface.

The next controlled work item is HS-10: build the right eye bucket and rear cap
as one serviceable module and correct the F-21 upper/lower connector layout.
Printing remains blocked by the other open shell gates.
