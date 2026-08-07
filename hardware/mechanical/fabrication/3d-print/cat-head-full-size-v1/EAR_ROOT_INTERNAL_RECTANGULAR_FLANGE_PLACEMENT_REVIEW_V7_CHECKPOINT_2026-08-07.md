# Ear-root internal rectangular-flange placement review V7 checkpoint — 2026-08-07

## Status

**Conceptual direction accepted, then superseded by V8 on 2026-08-07.** V7
proved that the ear-root connection should use two plain internal rectangular
tabs rather than the rejected V6 exterior broad-base/hardware construction.
It is not the current review and is not print released.

V7 was incomplete as a final attachment layout: it contained one connector set
on the right side only, no second anti-rotation set, and no left replication.
Its approximately `56 mm³` owner roots were also judged visually too small.

## Archived files

- Blender:
  `output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots/ear-root-internal-rectangular-flange-placement-review-v7.blend`
- Validation:
  `output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots/ear-root-internal-rectangular-flange-placement-review-v7-validation.json`
- Renders:
  `output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots/renders/`

## Source and archival regeneration

- Generator:
  `source/generate_ear_root_internal_rectangular_flange_placement_review_v7.py`
- Config:
  `config/ear-root-internal-rectangular-flange-placement-review-v7.json`
- Required aluminum interface: `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_internal_rectangular_flange_placement_review_v7.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-internal-rectangular-flange-placement-review-v7.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots
```

## Preserved decisions

- Keep ordinary parallel internal rectangular tabs.
- Keep the connector invisible in the exterior occupancy mask.
- Do not recreate V4/V5 clamps or bridges or the V6 exterior broad bases.
- Do not add holes/hardware before geometry placement is accepted.
- Preserve the accepted V3 fit body, exact ears and source heads, eyes,
  lower/rear ownership, reinforcements, C006, and aluminum V0.5.

V8 carries these decisions forward with two sets per translucent piece,
`22 × 12 × 4 mm` tabs, and direct owner-overlap validation.
