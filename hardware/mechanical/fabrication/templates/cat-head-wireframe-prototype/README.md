# Cat Head Wireframe Prototype

This is the active working folder for the cat-head wireframe and cardboard prototype path.

The folder started from the Gemini ORX reference image, but it is no longer just a Gemini import. It now contains the manually reviewed node/rod graph used as the current cat-head shape baseline.

## Current Status

- Active model: `gemini-3d-plus-symmetry-wireframe.obj`
- Current V1-approved snapshot: `versions/v1-shape-approved-cardboard-prototype/`
- Current direction: use the V1 wireframe graph to define cardboard panel faces and generate cut/tape templates.

## Key Active Files

- `generate_3d_plus_symmetry_model.py`: current generator for the active wireframe.
- `gemini-3d-plus-symmetry-wireframe.obj`: current OBJ for CAD/viewer inspection.
- `gemini_3d_plus_symmetry_nodes.csv`: current physical node coordinates.
- `gemini_3d_plus_symmetry_rods.csv`: current rod graph.
- `gemini_3d_plus_symmetry_report.md`: current generated model report.

## Versioned Baseline

Use this folder when a stable rollback point is needed:

`versions/v1-shape-approved-cardboard-prototype/`

That snapshot contains the V1 CAD exports, generated data, and source scripts/CSV inputs used to reproduce the approved model.

## Next Step

Define panel faces from the V1 rod graph, then generate labeled cardboard templates for a fast taped prototype.
