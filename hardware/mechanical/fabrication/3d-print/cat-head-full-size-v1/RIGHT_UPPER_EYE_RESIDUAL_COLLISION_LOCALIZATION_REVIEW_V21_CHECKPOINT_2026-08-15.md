# Right Upper/Eye Residual Collision Localization V21 Checkpoint

Status: review-only exact-intersection localization is complete for the four
right-upper contacts remaining after the approved C027 substitution. No source
owner geometry was changed. No face or edge is approved as a modification
anchor. This is not a production union, mirror, STL, G-code, or print release.

## Current review files

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-residual-collision-localization-review-v21/CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-residual-collision-localization-review-v21/validation-v21.json`
- Approved complete-context predecessor:
  `RIGHT_UPPER_C027_APPROVED_CONTEXT_REVIEW_V20_CHECKPOINT_2026-08-15.md`

The saved FreeCAD document contains exact zero-transform references to the V17
eye and unchanged V3 C001, C009, upper C012, and C019 components. Each source
has a separately toggleable exact Boolean-common diagnostic. The approved C027
reference is retained hidden for traceability.

## Accepted decisions and dimensions

- V19 C027 remains approved and collision-free; it was not changed here.
- Required eye/reinforcement clearance remains `4.0 mm` for any future
  component-specific correction.
- Preserve the exact V17 eye, all exterior shell coordinates not explicitly
  approved for a later correction, C006, lower/rear ownership, exact ears, and
  aluminum V0.5-M2.
- Upper-head C012 is distinct from lower member
  `V11_LOWER_COMPONENT_012`; the lower member's separate `5.452 mm` trim
  contract was not executed.

## Validation performed

Exact FreeCAD Boolean-common diagnostics and OCCT geometry checks report:

- C001: `100.60 mm3`; valid and watertight; `2` solids, `72` faces,
  `183` edges, `115` vertices; bounds `(55.12, 70.78, 118.48)` to
  `(103.74, 94.69, 178.66) mm`.
- C009: `27.73 mm3`; valid and watertight; `2` solids, `36` faces,
  `88` edges, `56` vertices; bounds `(94.64, 89.73, 172.29)` to
  `(100.75, 96.88, 177.70) mm`.
- Upper C012: `0.04 mm3`; valid and watertight; `1` solid, `6` faces,
  `10` edges, `6` vertices; bounds `(98.29, 95.46, 173.65)` to
  `(99.00, 96.40, 174.26) mm`.
- C019: displayed as `0.00 mm3`; one closed shell but invalid degenerate
  intersection topology (`6` faces, `8` edges, `4` vertices). Its bounds
  are only `(94.59, 91.14, 176.83)` to `(94.61, 91.17, 176.83) mm`.

C019 is therefore classified as a zero-volume touch/diagnostic sliver, not an
authorized trim target. The saved FCStd archive validates and is `1,352,146`
bytes.

## Rejected or unsafe actions

- Do not infer a trim direction or modification face from an intersection body.
- Do not modify C001, C009, upper C012, or C019 until the user selects the
  intended source-owner face or edge and approves a numeric contract.
- Do not treat the C019 invalid diagnostic as a source-owner defect.
- Do not confuse upper C012 with lower `V11_LOWER_COMPONENT_012`.
- Do not union the review objects, mirror them, export STL, slice, or release
  structural ASA from V21.

## Exact regeneration procedure

This review was produced through sequential FreeCAD MCP operations, not a macro
or headless script:

1. Open V20 and create
   `CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21`.
2. Insert exact zero-transform references to the V17 eye, V3 C001, C009,
   upper C012, C019, and approved V19 C027.
3. Create exact Boolean-common diagnostics between the V17 eye and each of
   C001, C009, upper C012, and C019.
4. Run element counts, volume, bounds, and `check_geometry` on each diagnostic.
5. Hide approved C027, keep all source/diagnostic objects toggleable, fit the
   isometric view, and save the FCStd path above.
6. Validate the saved FCStd archive.

## Next physical/visual review

Open V21 and inspect one source plus its matching diagnostic at a time. Start
with C001 because it contains the largest interference volume, then C009. If a
correction is desired, select the intended source-owner face or edge in
FreeCAD; a separate numeric movement/trim contract must then be prepared and
approved before geometry changes. Upper C012 follows as its own bucket. C019
needs no correction unless later production-solid validation proves a real
positive-volume conflict.
