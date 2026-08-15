# Right Upper C027 Eye-Clearance Review V19 Checkpoint

Status: isolated right-side proposal passes numeric CAD checks and was visually
approved by the user on 2026-08-15. It is not a production union, mirror, STL,
G-code, or print release. V20 supersedes this file for complete upper-head
context review.

## Current review files

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-eye-clearance-review-v19/CAT_HEAD_RIGHT_UPPER_C027_EYE_CLEARANCE_REVIEW_V19.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-eye-clearance-review-v19/validation-v19.json`

The saved document opens with the exact V17 eye and final C027 proposal visible.
The rejected first trial, cutting tool, original C027, and every other frozen V3
upper-head component remain in the document but are hidden for traceability and
context review.

## Accepted scope and numeric contract

- Change only right upper-head component C027 at the eye-side end.
- User-approved source anchors: coplanar `Face1` and `Face2`.
- Preserve the V17 eye, all non-C027 upper components, exterior shell, lower
  owner, C006, ear, rear cassette, and aluminum V0.5-M2 interface.
- Minimum eye clearance: `4.0 mm`.
- Final measured eye clearance: `5.3208 mm`.
- Final trim direction: `(-0.0718, +0.2910, +0.9540)`.
- Final cut face: proposal `Face4`, normal approximately
  `(+0.07, -0.29, -0.95)`, centroid `(41.46, 67.41, 174.06) mm`, area
  `16.80 mm2`.

## Validation performed

- Original C027/eye interference: `12.5907 mm3`.
- Rejected trial 1 interference: `1.0489 mm3`.
- Final trial 2 interference: `0.0 mm3`.
- Final C027 is one valid closed solid with zero self-intersections:
  `8` faces, `16` edges, `10` vertices, `646.004824 mm3` volume.
- Final bounding box: `(35.96, 64.80, 173.34)` to
  `(44.21, 81.19, 211.46) mm`.
- Structural/root overlap remains positive:
  - C001: `60.0948 -> 47.5120 mm3`.
  - C032: `184.0444 -> 146.9368 mm3`.
- Nearby C004/C019/C020 clearances remain unchanged at
  `0.6568/2.8643/2.2570 mm`; no new interference was introduced.
- Saved FCStd is a valid ZIP archive (`1,620,934` bytes).

## Rejected or unsafe variants

- `PROPOSED__RIGHT_UPPER_C027_TRIMMED_EYE_CLEARANCE_V19` is rejected because it
  leaves `1.0489 mm3` eye interference.
- V18 is not proof that the full eye/upper context is collision-free; the later
  audit found eye contact at C001, C009, C012, C019, and C027.
- Do not mirror, owner-union, export, slice, or print this isolated proposal.

## Exact regeneration procedure

This review was produced through the FreeCAD MCP change-control workflow, not
an arbitrary macro or headless script:

1. Insert the exact V3 C027 solid and exact V17 eye at zero transform.
2. Create a `100 x 100 x 100 mm` half-space box; rotate X `-16.92 deg` and Y
   `-4.30 deg`.
3. Place the trim plane from the approved C027 eye-side face pair and advance
   it to the effective `15.0 mm` position along
   `(-0.0718, +0.2910, +0.9540)`.
4. Boolean-cut the half-space from C027 and refine the result.
5. Insert every other exact V3 upper component at zero transform.
6. Re-run the eye interference/clearance, OCCT validity, topology, and neighbor
   contact checks recorded in `validation-v19.json`.

## Visual approval and next review

1. The user visually approved the isolated C027 proposal on 2026-08-15.
2. V20 substitutes only this approved C027 into a complete 42-component upper
   context compound and repeats the full eye collision audit.
3. C001, C009, upper-head C012, and C019 remain separate unresolved buckets.

## Ready next bucket: lower C012 numeric audit

The separate read-only audit identified lower member `V11_LOWER_COMPONENT_012`
and supplied an exact, unexecuted contract: freeze root `Face6` and its four
vertices, move eye-side `Face4` by `5.452 mm` along
`(-0.043395594, -0.667635441, -0.743222594)`. Predicted results are zero eye
interference, `4.000054 mm` clearance, and `47.527867 mm3` retained component-001
engagement. This is planning evidence only and does not authorize the C012 edit.
