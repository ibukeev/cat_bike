# Right Eye Bucket/Cap Anchor Audit V1 Checkpoint

## State

- Work item: `HS-10`.
- Status: anchor review required; no production geometry has been changed.
- Current FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-bucket-cap-anchor-audit-v1/CAT_HEAD_RIGHT_EYE_BUCKET_CAP_ANCHOR_AUDIT_V1.FCStd`
- Numeric contract:
  `config/right-eye-bucket-cap-anchor-audit-v1.json`
- Validation record:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-bucket-cap-anchor-audit-v1/validation-v1.json`

## Source audit

- The Gate 6 right bucket contains six connected components/shells.
- The Gate 6 right rear cap contains seven connected components/shells.
- The right diffuser is one component and remains frozen.
- The existing generator appends overlapping meshes instead of producing true
  bucket and cap unions. This is the cause of the disconnected slicer bodies.

## Anchor contract awaiting approval

| Role | FreeCAD object | Center (mm) |
|---|---|---|
| Retained lower connector | `REVIEW_ONLY__RIGHT_EYE_CAP_LOWER_RETAINED_CENTER_V1` | `(66.305, 63.709, 134.355)` |
| Proposed upper connector | `REVIEW_ONLY__RIGHT_EYE_CAP_UPPER_CANDIDATE_CENTER_V3` | `(65.600, 73.121, 166.400)` |

- Center separation: `33.406 mm`.
- Common inward M2.5 axis: `(-0.309374371, +0.910543024, -0.274224178)`.
- Hardware remains two M2.5 through-bolts, 2.8 mm clearance bores, 6.0 mm
  connector OD, 4.0 mm engagement, and a 0.3 mm removable-cap gap.
- V1 `(75.770, 79.790, 177.060)` and V2
  `(74.280, 78.410, 173.970)` upper candidates were rejected because they sat
  outside the cap perimeter. Neither remains in the review document.

## Frozen workstreams

The visible eye aperture and diffuser, approved eye-to-head flange locations,
upper head, ears, lower/rear ownership, reinforcement direction, C006, and
`CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` are unchanged. HS-11 flange integration is a
separate later bucket.

## Validation performed

- FreeCAD confirmed both surviving sphere centers numerically.
- The V3 upper candidate is inside the cap footprint in the front evidence
  view and is separated from the retained lower candidate.
- The imported source bucket/cap are unsuitable for production union evidence:
  they preserve six/seven shells and report topology errors after conversion.
- No mirror, production union, owner cut, export, or print release was made.

## Exact regeneration command for the frozen Gate 6 baseline

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
```

Do not run this command as a production release; it regenerates the known
disconnected baseline.

## Next physical/CAD review

Open the FCStd above. Confirm the upper sphere is a suitable upper rear-cap
fastener center and the lower sphere remains in the accepted lower location.
After explicit approval, build one isolated right-only proposal: one connected
bucket body plus one connected removable cap body, then validate cap removal,
M2.5 tool access, vibration support, and eye insertion before any mirror.
