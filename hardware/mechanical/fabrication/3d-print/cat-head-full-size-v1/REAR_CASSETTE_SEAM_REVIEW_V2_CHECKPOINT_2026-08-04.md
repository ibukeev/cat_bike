# Rear-Cassette Seam Review V2 Checkpoint — 2026-08-04

## Status

Review-only ownership candidate awaiting user approval. V2 supersedes V1 for
the proposed cut because V1 incorrectly transferred upper-head facets into the
rear cassette. V2 changes no production mesh and authorizes no STL generation,
slicing, printing, aluminum cutting, hole placement, or drilling.

## User-approved scope carried into V2

- Keep `left_upper_head` and `right_upper_head` completely unchanged.
- Keep both ears completely unchanged.
- Transfer only rear-facing existing facets from `left_lower_face` and
  `right_lower_face`.
- Include the existing `rear_base` in future rear-cassette ownership.
- Update the future connected cassette and rear-base-derived structure to work
  with the preserved aluminum components in a later, separately reviewed step.
- Do not move the aluminum datums independently.

## Current review files

Open:

`output/20-rear-cassette/history/rear-cassette-seam-review-v2/rear-cassette-seam-review-v2.blend`

Additional local generated review artifacts:

- `output/20-rear-cassette/history/rear-cassette-seam-review-v2/rear-cassette-seam-review-v2.glb`
- `output/20-rear-cassette/history/rear-cassette-seam-review-v2/rear-cassette-seam-review-v2-validation.json`
- `output/20-rear-cassette/history/rear-cassette-seam-review-v2/renders/`

Tracked inputs:

- `config/rear-cassette-seam-review-v2.json`
- `source/generate_rear_cassette_seam_review_v2.py`
- the unchanged Gate 8 review blend;
- the Gate 2 facet-ownership configuration; and
- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json`.

## Review display

- Orange lower-face facets are proposed cassette ownership.
- The orange rear-base object is an unchanged copy of the existing
  `rear_base`, included only to show ownership.
- Yellow lines are the two proposed new lower-face cut edges.
- The exact lower-face selection remains hidden as
  `REVIEW_ONLY__rear_cassette_exact_surface`.
- The original `rear_base` remains present but hidden.
- The orange lower-face display surface is offset outward `0.45 mm` only to
  prevent z-fighting.

## Validation performed

- Actual selected source sections are exactly `left_lower_face` and
  `right_lower_face`.
- Selected 10 source faces representing 10 canonical source panel IDs.
- Proposed new cut boundary contains 2 source edges.
- Exact selected lower-face surface measures approximately
  `253.878 x 81.006 x 88.130 mm`.
- Confirmed zero selected upper-head facets.
- Confirmed all 20 Gate 8 production objects remain present and their mesh
  vertex and polygon counts are unchanged.
- Direct original-versus-V2 upper-head geometry fingerprints match exactly:
  - left: `0ea3291fd43bb6d3bea544030f142df674abefef12795e5ed2c1c04a9e364429`;
  - right: `ef92601736efe41e4b2a9ceb4825968aa177aaff127f0fb8faf9c3154f6897b5`.
- Confirmed the existing rear base is included in cassette ownership through an
  unchanged orange review duplicate.
- Removed the same 11 Gate 8 review-only tube, coupon, and LED-reference
  objects from the V2 scene.
- Generated six whole-head views and three isolated cassette-ownership views.
- Confirmed no STL or G-code exists in the V2 output directory.
- The 9 shared shell/aluminum interface tests pass.
- Python compilation, JSON parsing, Blender scene assertions, and
  `git diff --check` pass.

## Required honesty about current geometry

The selected lower-face surfaces and the unchanged rear base are separate
review objects. They do not yet form one connected, closed, printable body.
The isolated renders show this separation deliberately.

This V2 review approves only ownership and cut location. The future connection,
rear opening, flange, reinforcement, sealing, drainage, fasteners, and aluminum
clearance remain unmodeled.

## Aluminum workstream hold

The active V0.5 aluminum plate/rail workstream remains preserved and unchanged.
After ownership approval, the next review must place its complete backplate,
rails, lower shoes, hardware, tool, wiring, insertion, and removal envelopes
against this V2 ownership group. The rear cassette must be designed around
those envelopes. No shell-only session may silently relocate metal datums.

## Rejected or unsafe actions

- Do not transfer any upper-head or ear facet into the cassette.
- Do not treat the orange ownership objects as one connected printable part.
- Do not add bridges or reshape `rear_base` before the V2 cut is approved.
- Do not restore rejected Gate 9 V3–V11 geometry.
- Do not generate production STLs or print ASA from this review.
- Do not cut or drill aluminum from this review.

## Exact regeneration command

From the repository root:

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_rear_cassette_seam_review_v2.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/rear-cassette-seam-review-v2.json \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/20-rear-cassette/history/rear-cassette-seam-review-v2
```

## Next review step

Review only whether the two lower-face cut edges and orange lower-face facet
ownership are correct. Use the isolated views to confirm that the existing
rear base belongs in the future cassette even though it is not yet connected.

After explicit approval, create a separate combined rear-only review containing
this ownership group and the unchanged V0.5 aluminum envelopes. Only then
design the connected cassette and revised rear-base structure around the
approved metal interface.
