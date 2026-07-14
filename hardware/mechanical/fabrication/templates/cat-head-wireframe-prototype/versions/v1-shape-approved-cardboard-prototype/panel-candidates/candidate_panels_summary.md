# V1 Candidate Cardboard Panels

Generated from the frozen V1 node/rod graph.

## Counts

- Candidate cardboard panels: 95
- Triangles: 61
- Chordless quads/manual quads: 34
- Protected eye cutouts: 2
- Translucent eye insert panels: 2
- Reviewer-removed panel node sets: 11
- Panels touching heavy-estimate nodes: 56
- Manual reviewer-added panels: 6

## Review Files

- `candidate_panels.csv`: candidate cardboard panel list with node IDs, rod IDs, edge lengths, area, risk, and planarity.
- `eye_cutouts.csv`: protected 4-edge eye openings that should not be filled by ordinary cardboard panels.
- `eye_insert_panels.csv`: translucent insert panels that fill those eye openings as separate material pieces.
- `suppressed_eye_fill_panels.csv`: auto-generated candidates suppressed because they would fill the eye openings.
- `suppressed_reviewer_removed_panels.csv`: candidate panels explicitly removed by reviewer feedback.
- `candidate-panel-review.html`: interactive 3D visual review UI for accepting/rejecting candidate panels.
- `candidate-panel-review-multiview.html`: front/side/top/iso panel review UI.
- `candidate-panels-3d.obj`: main cardboard/skin review mesh with eye openings preserved and cutout boundary loops shown.
- `eye-insert-panels.obj`: separate translucent insert faces for the eye openings; import alongside the main OBJ when needed.
- `candidate-panels-combined.obj`: combined all-pieces review mesh with skin panels and translucent eye insert panels as separate objects/materials.

## Review Guidance

Use the multiview HTML or OBJ to inspect panels in 3D, not a single projection.
Start by accepting large visible front/cheek/forehead facets and rejecting internal-looking or confusing crossings.
The accepted panel list should be smaller than this candidate set.
The eye cutout loops are intentionally not cardboard panels in the main OBJ; they are filled by separate translucent eye insert panels.
