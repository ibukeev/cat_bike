# Right Upper Eye C009/C012 Exact-Anchor Review V23 Checkpoint

Date: 2026-08-15

Status: **REVIEW ONLY — NO GEOMETRY CHANGE; NOT A PRINT SOURCE**

## Purpose

Convert the external STL-triangle handoff for C009 and upper C012 into exact
FreeCAD BREP-face identities. V23 copies the frozen V21 context and exposes the
cap/root faces only. It performs no trim, cut, fuse, mirror, owner transfer, or
production export.

## Current review files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c009-c012-exact-anchor-review-v23/CAT_HEAD_RIGHT_UPPER_EYE_C009_C012_EXACT_ANCHOR_REVIEW_V23.FCStd`
- Validation/contract:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c009-c012-exact-anchor-review-v23/validation-v23.json`

## Exact BREP anchors

| Component | Role | Exact source face | Area | Centroid XYZ |
|---|---|---:|---:|---|
| C009 | eye-side cap | `Face17` | `11.6000079 mm2` | `(93.738182, 91.736567, 181.775263) mm` |
| C009 | fixed root cap | `Face13` | `11.6000043 mm2` | `(103.196065, 95.340810, 169.981761) mm` |
| upper C012 | eye-side cap | `Face4` | `5.2042591 mm2` | `(100.506727, 94.666280, 174.352966) mm` |
| upper C012 | fixed root cap | `Face18` | `6.5077906 mm2` | `(119.155955, 110.994342, 122.093857) mm` |

These BREP faces reproduce the STL-cap areas, centroids, and normals in the
independent read-only audit. Upper C012 is the V3 upper-head component; it is
not lower `V11_LOWER_COMPONENT_012`.

## Frozen numeric evidence

- Clearance target: at least `4.0 mm` from the unchanged exact V17 eye.
- C009 audited travel: at least `13.98 mm`; predicted clearance
  `4.000005 mm`; predicted retained volume `7.189814 mm3`; predicted C001
  engagement `3.093939 mm3`.
- Upper C012 audited travel: at least `5.21 mm`; predicted clearance
  `4.000010 mm`; predicted retained volume `606.537827 mm3` with positive
  engagement to its existing neighbors.
- Preserve the V17 eye, visible exterior, C006, ears, lower/rear ownership, and
  `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` unchanged.

## Decisions and holds

- **C009 remains HOLD.** The audited cap trim would remove about `96.85%` of
  the component. Exact BREP identification does not resolve structural
  adequacy and does not authorize the trim.
- **Upper C012 remains CANDIDATE ONLY.** `Face4` is now the exact eye-side BREP
  cap and `Face18` the fixed root reference, but the user has not yet approved
  `Face4` as a modification anchor.
- No left mirror, production union, STL, G-code, or ASA print release is
  authorized by V23.

## Validation performed

- Both source owners and their V21 Boolean-common diagnostics were opened from
  the saved V21 review and audited in FreeCAD/OCC.
- C009 exact faces: `Face17` eye cap and `Face13` fixed root cap.
- Upper-C012 exact faces: `Face4` eye cap and `Face18` fixed root cap.
- `validation-v23.json` records `authorized_geometry_change: false` and
  `status: REVIEW_ONLY__NO_GEOMETRY_CHANGE`.
- The two audit/generator scripts passed Python bytecode compilation.
- No source or protected geometry was changed.

## Exact regeneration

Start a FreeCAD console from the repository root:

```sh
/snap/bin/freecad -c
```

Then run:

```python
q = "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_upper_eye_c009_c012_exact_anchor_review_v23.py"
exec(compile(open(q).read(), q, "exec"), {"__file__": q, "__name__": "__main__"})
```

The read-only face audit is:

```python
q = "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/audit_v21_c009_upper_c012_collision_faces.py"
exec(compile(open(q).read(), q, "exec"), {"__file__": q, "__name__": "__main__"})
```

## Next visual review

1. Open the V23 FreeCAD review.
2. For upper C012, show its frozen source, diagnostic, `Face4`, and `Face18`;
   approve or reject only `Face4` as the eye-side shortening anchor.
3. For C009, inspect `Face17` and `Face13` only for identity. Do not approve a
   trim until a structurally acceptable replacement or retained-volume/root
   contract exists.
