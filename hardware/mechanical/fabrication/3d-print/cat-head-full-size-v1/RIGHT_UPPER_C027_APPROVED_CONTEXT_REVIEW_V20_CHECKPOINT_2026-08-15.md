# Right Upper Approved-C027 Context Review V20 Checkpoint

Status: the user-approved V19 C027 is substituted into a complete right-upper
review compound and passes its repeated eye-clearance check. Four other upper
components remain unresolved. This is not a production union, mirror, STL,
G-code, or print release.

## Current review files

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-approved-context-review-v20/CAT_HEAD_RIGHT_UPPER_C027_APPROVED_CONTEXT_REVIEW_V20.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-approved-context-review-v20/validation-v20.json`
- Approved isolated source: `RIGHT_UPPER_C027_EYE_CLEARANCE_REVIEW_V19_CHECKPOINT_2026-08-15.md`

The saved document opens with the exact V17 eye and the complete 42-solid upper
context compound visible. The 41 unchanged V3 components and approved V19 C027
remain as hidden traceable source objects. The compound is display/audit context,
not an owner Boolean.

## Accepted decisions and dimensions

- V19 C027 was visually approved by the user on 2026-08-15.
- Only original C027 is replaced by
  `PROPOSED__RIGHT_UPPER_C027_TRIMMED_EYE_CLEARANCE_V19_T2`.
- Approved C027 clearance remains `5.3208 mm`, above the `4.0 mm` contract.
- Preserve all non-C027 upper component coordinates, exact V17 eye, C006,
  lower/rear ownership, exact ears, and aluminum V0.5-M2.

## Validation performed

- V20 context geometry is valid and closed as a 42-solid compound:
  `2756` faces, `4305` edges, `1585` vertices, `150495.11 mm3` volume.
- Context bounds: `(-30.00, 42.84, 109.76)` to
  `(126.94, 269.34, 268.15) mm`.
- Complete context versus eye aggregate intersection: `114.9193 mm3`.
- Component-level residuals:
  - C001: `100.5990 mm3`.
  - C009: `27.7283 mm3`.
  - upper-head C012: `0.0366 mm3`.
  - C019: touching near-zero sliver, reported `0.0000 mm3`.
  - approved C027: `0.0 mm3`, `5.3208 mm` clearance.
- Saved FCStd ZIP validation passes (`2,574,757` bytes).

Upper-head C012 is not the same object as lower member
`V11_LOWER_COMPONENT_012`. The latter has a separate read-only 5.452 mm trim
contract and was not edited here.

## Rejected or unsafe actions

- Do not infer whole-upper collision closure from the approved C027 result.
- Do not union this 42-solid compound into a production shell.
- Do not trim C001, C009, upper C012, C019, or lower C012 without approved
  structured anchors and a component-specific numeric contract.
- Do not mirror, export, slice, or release ASA from V20.

## Exact regeneration procedure

This review was produced through FreeCAD MCP operations, not a macro or
headless script:

1. Create document `CAT_HEAD_RIGHT_UPPER_C027_APPROVED_CONTEXT_REVIEW_V20`.
2. Insert the exact V17 eye, all V3 upper solids except original C027, and the
   approved V19 C027 at zero transform.
3. Create a non-fused compound from the 41 unchanged upper components plus the
   approved C027.
4. Run exact eye interference and clearance checks against C001, C009, upper
   C012, C019, approved C027, and the complete compound.
5. Run compound element count, bounds, volume, and geometry checks.
6. Save the FCStd path above and validate the archive.

## Next physical/visual review

No user action is required for the approved C027 bucket. Next, prepare
review-only structured anchor packs for C001, C009, upper C012, and C019. Each
must remain a separate change bucket and require explicit anchor/contract
approval before geometry changes. The lower C012 numeric audit is also ready
for an anchor review but remains unexecuted.
