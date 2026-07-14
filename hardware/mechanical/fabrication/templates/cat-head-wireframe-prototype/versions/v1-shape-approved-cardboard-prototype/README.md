# Cat Head V1 Shape-Approved Cardboard Prototype

This folder freezes the current wireframe as the V1 baseline for cardboard prototype work.

## Status

- Shape/topology baseline approved for next-step cardboard prototyping.
- Main model scale is in millimeters.
- Current model count at snapshot time: 72 nodes, 166 rods.
- Node spheres and rods are visually slimmed for inspection: node radius 1.6 mm, rod radius 0.9 mm.

## Folder Contents

- `cad/`: inspectable geometry exports, including OBJ/STL/HTML.
- `data/`: generated node, rod, residual, skipped-edge, part-map, and report CSV/MD files.
- `source/`: generator scripts and input trace/mapping CSVs needed to reproduce this V1 snapshot.

## Main Files

- `cad/gemini-3d-plus-symmetry-wireframe.obj`: primary file to inspect/import.
- `data/gemini_3d_plus_symmetry_nodes.csv`: physical node coordinates.
- `data/gemini_3d_plus_symmetry_rods.csv`: rod centerline graph.
- `source/generate_3d_plus_symmetry_model.py`: generator state used for this V1.
- `panel-candidates/candidate-panel-review.html`: interactive 3D review of automatically detected triangle/quad panel candidates.
- `panel-candidates/candidate-panel-review-multiview.html`: front/side/top/iso review for checking each candidate panel from multiple projections.
- `panel-candidates/candidate-panels-3d.obj`: CAD-importable review mesh with each candidate panel as a separate OBJ object.
- `panel-candidates/candidate-panels-3d.mtl`: materials for the candidate panel OBJ.
- `panel-candidates/candidate_panels.csv`: candidate cardboard panel list.

## Next Intended Step

Review the generated candidate panels, accept/reject the panels that should become the cardboard shell, then generate printable/cuttable panel templates.
