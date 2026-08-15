# Right Upper Eye C001 Exact-Anchor Review V22 Checkpoint

Date: 2026-08-15

Status: **REVIEW ONLY — NO GEOMETRY CHANGE; NOT A PRINT SOURCE**

## Purpose

V21 localized a positive-volume collision between the exact V17 right-eye
owner and upper-head component C001. V22 identifies the exact C001 BREP faces
that bound that collision so the user can approve the correct source-owner
anchors before any trim is generated.

The earlier visual guesses `Face364` and `Face385` are rejected. Their selected
locations were outside the V21 diagnostic bounds. They were never used for a
cut.

## Current review files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c001-exact-anchor-review-v22/CAT_HEAD_RIGHT_UPPER_EYE_C001_EXACT_ANCHOR_REVIEW_V22.FCStd`
- Validation/contract:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c001-exact-anchor-review-v22/validation-v22.json`

## Exact candidate anchors

| Region | Source face | Area | Common area with V21 diagnostic | Centroid XYZ |
|---|---:|---:|---:|---|
| Top | `Face382` | `1499.8509 mm2` | `49.4685 mm2` | `(61.7498, 77.8402, 184.2889) mm` |
| Side | `Face324` | `55.3251 mm2` | `37.0994 mm2` | `(102.4310, 83.5109, 157.8600) mm` |
| Side | `Face536` | `55.3262 mm2` | `52.8389 mm2` | `(102.4539, 78.0427, 138.0662) mm` |
| Side | `Face554` | `149.3889 mm2` | `37.9746 mm2` | `(102.6720, 80.2460, 139.5449) mm` |

V21 C001-eye diagnostic bounds are
`(55.1221, 70.7837, 118.4773)` to
`(103.7368, 94.6894, 178.6570) mm`.

## Frozen numeric contract

- Resulting exact C001-to-eye clearance must be at least `4.0 mm`.
- Preserve the exact V17 eye owner unchanged.
- Preserve all visible exterior coordinates unchanged.
- Preserve C006, ears, lower-face/rear-cassette ownership, and the
  `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` interface unchanged.
- No left mirror, production union, STL, G-code, or ASA print release is
  authorized by this review.

## Validation performed

- The V22 `.FCStd` archive was validated after its GUI save: valid ZIP,
  `1,286,635` bytes.
- The review contains the unchanged C001 source, unchanged exact V17 eye,
  unchanged V21 Boolean-common diagnostic, four isolated exact candidate
  faces, and two hidden rejected-face references.
- `validation-v22.json` records `authorized_geometry_change: false` and
  `status: REVIEW_ONLY__NO_GEOMETRY_CHANGE`.
- No source geometry was cut, moved, mirrored, joined, or exported.

## Residual-contact planning evidence

The separate read-only C009/upper-C012 audit is incorporated only as a hold
decision:

- **C009: HOLD.** Its proposed `>=13.98 mm` cap trim would leave only
  `7.189814 mm3` (about `3.15%`) of the component and only `3.093939 mm3`
  engagement with C001. Structural adequacy is unresolved, so this trim is not
  authorized.
- **Upper C012: potentially viable but still unapproved.** The proposed
  `>=5.21 mm` shortening reaches `4.000010 mm` clearance and retains positive
  owner engagement, but its reported anchor is an STL triangle ID rather than
  a user-approved FreeCAD BREP face. No trim is authorized.
- C019 remains a zero-volume/degenerate diagnostic and is not a trim target.

## Regeneration

Run the following with FreeCAD's command-line Python environment from the
repository root:

```sh
freecadcmd hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/run_right_upper_eye_c001_anchor_localization_review_v22_headless.py
```

The read-only exact-face audit can be repeated with:

```sh
freecadcmd hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/audit_v21_c001_collision_faces.py
```

## Next physical/visual review

1. Open the V22 FreeCAD file.
2. Review `REVIEW_ONLY__C001__TOP__FACE382__V22` with the diagnostic visible.
3. Review the three side candidates `Face324`, `Face536`, and `Face554` with
   the diagnostic visible.
4. Approve or reject those corrected source faces. Only then may an isolated
   one-side C001 correction be generated and measured against the `4.0 mm`
   contract.
