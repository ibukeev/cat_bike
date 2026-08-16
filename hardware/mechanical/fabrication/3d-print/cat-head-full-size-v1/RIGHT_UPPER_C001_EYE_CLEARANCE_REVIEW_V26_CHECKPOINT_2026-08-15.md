# Right Upper C001 Eye Clearance Review V26 Checkpoint

Status: **diagnostic only; rejected for integration, mirroring, STL export, slicing, or printing**.

## Current review files

- FreeCAD diagnostic: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-eye-clearance-review-v26/CAT_HEAD_RIGHT_UPPER_C001_EYE_CLEARANCE_REVIEW_V26.FCStd`
- Automatic backup: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-eye-clearance-review-v26/CAT_HEAD_RIGHT_UPPER_C001_EYE_CLEARANCE_REVIEW_V26.20260815-143314.FCBak`
- Temporary exact-solid audit used during this review: `/tmp/TMP_C001_STAGE1_SOLIDS_AUDIT_V26.FCStd` (not authoritative and not versioned)

## Frozen inputs and approved constraints

- Exact right eye: V17, unchanged.
- Right upper exterior: unchanged.
- C006, ears, lower/rear ownership, and aluminum V0.5-M2: unchanged.
- User-approved C001 review anchors remain the V22 faces:
  - top `Face382`;
  - side `Face324`;
  - side `Face536`;
  - side `Face554`.
- Required eye clearance: at least `4.0 mm`.
- Required topology: intentional structural material must remain positively owner-connected; no detached rail may be accepted.

## Exact validation performed

The V26 top-clearance result was exported to STEP and decomposed into exact solids. It contains four solids:

1. Boolean sliver: `1.00 mm^3`.
2. Boolean sliver: `0.55 mm^3`.
3. Real tapered reinforcement rail: `174.42 mm^3`, bounding box approximately `X 43.35..102.12`, `Y 63.10..90.98`, `Z 165.35..178.33 mm` before offset.
4. Main C001 owner: `75587.32 mm^3`.

The rail is structural and must not be deleted merely to obtain a one-solid result.

### Rejected far-root bridge

- Test bridge: axis-aligned `6 x 6 x 6 mm` block at `(41.0, 61.5, 163.5) mm`.
- Rail overlap: `13.2930 mm^3`.
- Main-owner overlap: `0.7086 mm^3`.
- Fused result: one exact solid, but bridge-to-eye interference is `25.1105 mm^3`.
- Decision: **rejected**.

### Diagnostic rail offset

- Applied diagnostic offset from the decomposed V26 rail:
  - `(+2.1930, -5.7405, +1.9350) mm` total.
- Resulting exact rail-to-eye clearance: `4.2616 mm`.
- Resulting rail-to-main minimum gap: `4.4614 mm`.
- V25 complete upper-owner batch audit found no positive overlap between the offset rail and any adjacent approved upper-head component.
- Therefore the rail is not automatically captured by another owner and still needs an intentional root to C001.

### Rejected shifted cube root

- Test bridge: axis-aligned `6 x 6 x 6 mm` block at `(43.193, 55.7595, 165.435) mm`.
- Rail overlap: `13.2930 mm^3`.
- Main-owner gap: `2.3481 mm`.
- Eye clearance: only `3.1479 mm`.
- Decision: **rejected**.

## Rejected or unsafe variants

- Do not delete the `174.42 mm^3` reinforcement rail.
- Do not use either tested cube bridge.
- Do not accept the top-only clearance result as a production owner: it has four solids.
- Do not mirror, owner-union, export STL, slice, or print V26.
- Do not use the broad side/top envelope candidate until its exact seven-solid decomposition is reviewed; connectedness alone must not be inferred from tessellated display.

## Resume procedure

No deterministic regeneration command exists yet because V26 remains a rejected structured-FreeCAD diagnostic. To resume without changing frozen geometry, open the saved review directly:

```bash
FreeCAD hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-eye-clearance-review-v26/CAT_HEAD_RIGHT_UPPER_C001_EYE_CLEARANCE_REVIEW_V26.FCStd
```

Then continue only with structured FreeCAD operations. First decompose the complete top-plus-side clearance candidate, classify its real structural solids versus Boolean slivers, and design the minimum root from the offset rail to the final `4.0 mm` C001 clearance boundary. Validate the root against the exact V17 eye before any owner union.

## Next physical/user review

When a one-solid candidate exists, show the user the full right-eye/upper-head context plus an isolated interior view of the reconnected rail. The user should review only:

1. the rail remains present and is visibly rooted to C001;
2. the root does not protrude through the exterior;
3. the eye has visible service clearance;
4. no new stick, horn, loose block, or floating residue appears.

Only after that visual approval may the candidate proceed to exact owner integration and bilateral work.
