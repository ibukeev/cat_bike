# Cat-Head Return Review Queue — 2026-08-08

This is the shortest review queue after the unsupervised validation pass. It
does not authorize integration, mirroring, fabrication export, slicing, or
printing.

## 1. Selected legacy small-flange removal

Open:
`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/CAT_HEAD_RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1.FCStd`

Review only the old small projection selected as
`PROPOSED__RIGHT_UPPER_HEAD__VALIDATION_COMPOUND_V3.Face1668`.

- Clean context: `review/01-clean-context-isometric.png`.
- Internal before: `review/04-before-local-inside-left.png`.
- Internal after: `review/05-after-local-inside-left.png`.
- In FreeCAD, hide the complete proposal and alternate
  `VALIDATION_ONLY__FACE1668_C001_NEIGHBORHOOD_V1` and
  `REVIEW_ONLY__FACE1668_REMOVAL_LOCAL_CONTEXT_V1` in Left view.

Question to answer: does removing this one legacy internal projection look
correct while the exterior wall remains intact?

## 2. Right-A short-insert hardware contract

Open:
`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`

Question to answer: accept or reject the proposed M3 x 3 short heat-set insert
with a `4.25 mm x 3.0 mm` recessed cavity and the validated 25-degree
panel-side ball-end access path.

## Already accepted; do not re-review

- Right-B `1.9 mm` local-relief shape: visually approved.
- Right-A common M3 hole placement: approved as “Holes are OK.”
- Right translucent panel, right upper-head topology, and right-ear topology:
  approved references.
- Aluminum workstream: preserved at
  `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`, SHA-256
  `6326b211e4eef8c87a2b17687e2d68406682d21a6fa7c81ad52c8a1b9e713c79`.

## Front-loaded validation completed

- Legacy-removal FCStd archive: valid, `7,999,704` bytes.
- Proposal: `42` closed valid solids; no self-intersection.
- Bounding box unchanged.
- B head-root overlap after removal: `124.93 mm3`.
- B relieved panel-tab clearance after removal: `0.445 mm`.
- Translucent-panel clearance after removal: `0.0353 mm`.
- Focused print-topology tests: `9/9 PASS`.
- Full automated suite: `24/25 PASS`; the unchanged lighting-map test still
  errors because current Gate 1 panel-role data has no `glow_pairs` key.

## Work intentionally held

- B hole/fastener/access work depends on the selected-projection decision.
- Right-side production integration depends on both review items above.
- Left mirror depends on explicit right-side integration approval.
- Eye, central/front/side panel, and ear slot work require exact user-selected
  CAD faces or edges before geometry is changed.
- No structural ASA print should start from the current isolated review files.
