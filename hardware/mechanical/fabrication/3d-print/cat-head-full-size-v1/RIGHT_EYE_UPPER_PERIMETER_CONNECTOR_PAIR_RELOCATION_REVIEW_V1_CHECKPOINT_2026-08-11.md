# Right Eye Upper-Perimeter Connector Pair Relocation V1 Checkpoint

## Current review

Open:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-perimeter-connector-pair-relocation-review-v1/CAT_HEAD_RIGHT_EYE_UPPER_PERIMETER_CONNECTOR_PAIR_RELOCATION_REVIEW_V1.FCStd`

This is an isolated right-side proposal. It does not alter the frozen Gate 6
source and is not a fabrication release.

## Accepted decisions and numeric contract

- Retain the complete lower existing connector pair.
- Relocate the other complete pair, both mating halves together.
- Preserve the existing cylindrical M2.5 design.
- User-selected anchor:
  `AUDIT__RIGHT_EYE_REAR_CAP_COMPONENT_SOLIDS.Edge74`, length `69.4377 mm`.
- Approved axis on the frozen eye plane:
  `(72.2476, 78.1286, 175.5293) mm`.
- Rigid translation applied to both halves:
  `(-16.8524, +1.4636, +23.8713) mm`.
- Span from retained lower connector axis: `44.0291 mm`.
- Mating clearance remains `0.3000 mm`.

## Validation

- Relocated bucket boss: one valid closed solid, `87.46 mm3`.
- Relocated cap ear: one valid closed solid, `39.36 mm3`.
- Bucket-owner overlap: `11.8904 mm3`.
- Rear-cap-owner overlap: `10.2392 mm3`.
- Pair-to-pair clearance: `0.3000 mm`.
- FCStd archive validation: pass, `521189` bytes at validation time.

The frozen audit compounds still contain the old candidate position. The
relocated halves are separate objects named `PROPOSED__MOVE_PAIR__...__SOLID`.
They must not be described as integrated. Exact subtraction from the
disconnected audit compounds returned an invalid result, so no broad cutter or
owner-gouging workaround was used.

## Frozen and rejected work

Frozen: visible aperture, diffuser, eye/head mounting flanges, head and ear
owners, lower-face/rear-cassette ownership, reinforcement direction, C006, and
`CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.

Rejected: the earlier broad-face sphere datum and any new connector design.
No mirror, owner union, STL, G-code, slicer, ASA, or print release is approved.

## Exact source regeneration command

Frozen Gate 6 baseline only:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
```

This command regenerates the disconnected source baseline, not this FreeCAD
proposal and not a print release.

## Next physical review

In the open FreeCAD review, inspect the two
`PROPOSED__MOVE_PAIR__...__SOLID` objects with both owners visible. Confirm that
the pair sits on the selected upper perimeter and that neither half is on the
broad rear-cap face. After explicit approval, create owner-clean production
copies, integrate on the right only, and rerun topology and service-access
validation before any mirror.
