# Cat Head Wireframe and Cardboard Prototype Plan

## Current Status

The cat head wireframe has moved from source-reconstruction work into a shape-approved prototype baseline.

Completed:

- Manual projection/node mapping workflow established from the Gemini ORX reference material.
- Iterative 3D wireframe edited in Onshape/OBJ review until the cat-head proportions looked acceptable.
- Side-only and mirrored backside nodes added where projection constraints were weak.
- Review rods were added/removed by mapped physical node IDs after visual inspection.
- Main node/rod geometry was slimmed for inspection: node radius 1.6 mm, rod radius 0.9 mm.
- Active workspace was renamed to:
  - `hardware/mechanical/fabrication/templates/cat-head-wireframe-prototype/`
- V1 baseline was frozen at:
  - `hardware/mechanical/fabrication/templates/cat-head-wireframe-prototype/versions/v1-shape-approved-cardboard-prototype/`

V1 snapshot contents:

- `cad/`: OBJ, STL, HTML preview, PNG, and review marker exports.
- `data/`: node CSV, rod CSV, residual/skipped-edge reports, part map, and generated report.
- `source/`: generator scripts and trace/mapping CSVs needed to reproduce the V1 model.

Current V1 model count:

- 72 nodes
- 166 rods

## Current Fabrication Direction

The next build should be a fast cardboard prototype, not final material fabrication.

Preferred near-term approach:

1. Use the V1 wireframe as the shape/topology baseline.
2. Define flat triangular/quadrilateral panel faces from the rod graph.
3. Generate labeled cardboard panel templates.
4. Cut/tape a faceted shell prototype to validate silhouette, scale, and assembly logic.
5. Only after the cardboard shell looks right, choose final panel materials and mounting details.

Preferred final-direction options remain open:

- Rod skeleton plus panels.
- Rod skeleton plus 3D-printed hubs.
- Flat cut panels with tabs.
- Full 3D-printed shell, only if later worth the complexity.

For now, the rod skeleton plus flat panels path preserves the most optionality.

## Material Direction Captured

Likely main finish:

- Thin flat panels wrapped in gold mirror vinyl.
- Alternative: gold mirrored acrylic/polycarbonate/PETG if durability and sourcing work out.

Likely glow/translucent areas:

- Frosted or smoked acrylic/polycarbonate panels.
- Optional two-way mirror or reflective film over clear/frosted plastic for panels that look reflective when off and glow when lit.

## Next Implementation Steps

1. Create a panel-face definition file.
   - Input: V1 `data/gemini_3d_plus_symmetry_nodes.csv` and `data/gemini_3d_plus_symmetry_rods.csv`.
   - Output: a CSV or JSON listing panel IDs and corner node IDs.

2. Start with a small number of high-confidence visible faces.
   - Prioritize large front/cheek/forehead facets.
   - Avoid dense/uncertain backside details until the main silhouette is validated.

3. Generate panel templates.
   - For each panel, output edge lengths and a flat 2D polygon.
   - Label every panel and every edge with adjacent node IDs.
   - Add simple assembly notes and neighbor references.

4. Build a taped cardboard prototype.
   - Use cardstock/cereal-box cardboard first if small scale.
   - Use foamcore or corrugated cardboard if full-scale stiffness is needed.
   - Tape first; glue only after shape is visually accepted.

5. Review prototype against desired cat-head read.
   - Check front silhouette.
   - Check side depth and muzzle/ear proportions.
   - Check whether rods/panel seams support the intended low-poly visual.
   - Mark edits as node moves, rod changes, or panel-face changes.

6. Branch after cardboard validation.
   - If shape is good: create final panel material plan and mount integration.
   - If shape is close: edit the V1 graph and freeze V2.
   - If assembly is confusing: simplify panel topology before final material work.

## Verification Gates

- Gate A: V1 wireframe snapshot exists and can be reopened in Onshape/FreeCAD.
- Gate B: panel-face list covers the main visible shell without obvious gaps.
- Gate C: generated cardboard templates have labels, edge lengths, and neighbor references.
- Gate D: cardboard prototype is physically assembled and photographed from front/side/back.
- Gate E: steering/mount envelope is checked against the bike before final material fabrication.

## Notes

- V1 is a shape-approved prototype baseline, not a final fabrication CAD model.
- Weakly constrained nodes are acceptable for cardboard testing as long as they are visibly marked in the source data.
- Do not generate final cut lengths, hub sockets, or production panel tabs until the cardboard prototype confirms the shape.
