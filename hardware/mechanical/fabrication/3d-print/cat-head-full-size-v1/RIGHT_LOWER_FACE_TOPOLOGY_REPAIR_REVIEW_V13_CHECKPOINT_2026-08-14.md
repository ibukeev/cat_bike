# Right Lower-Face Topology Repair V13 Checkpoint — 2026-08-14

## Status

V13 is the current isolated HS-11 topology proposal and is awaiting explicit visual approval. It repairs only lower-face component 001. No owner integration, mirroring, STL, G-code, slicing, or print release was performed. The head-shell tracker remains 9 of 20 gates complete.

## Review/output files

- FreeCAD review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13.FCStd`
- Blender audit: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13.blend`
- Repaired component OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/right_lower_face_component_001_topology_repaired_v13.obj`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/validation-v13.json`
- Contract: `config/right-lower-face-topology-repair-review-v13.json`
- Generator: `source/generate_right_lower_face_topology_repair_review_v13.py`

FCStd SHA-256: `9ba404c8a7bed0ff9879eae95f06166093d308168679f3b44255261d785fe46c`

OBJ SHA-256: `f0424c49c7ee4166fc306066be24c07787e885dd9d56e598cc2e94f86131730d`

## Accepted/frozen design contract

- Source: frozen V12 component-001 OBJ, SHA-256 `f5c58d135bc347d79bcbb9350cc67eb64e6fd90552f7d8353217fcd46c51ea26`.
- Scope: only the 21 mapped legacy seam/slot face pairs responsible for 41 source intersections.
- The three small internal exact-union regions contain 10 faces total and are removed; the 1486-face exterior region is retained.
- One Boolean-only corner vertex is snapped `0.0459405 mm` to the exact frozen source corner. No frozen source vertex is moved.
- Exterior deviation must remain at most `0.01 mm`; achieved `0.00654787 mm`.
- Bounding-box deviation must remain at most `0.001 mm`; achieved `0.0 mm`.
- The other 59 lower-face components, eye bucket/rear cap, all eye flanges, C046/C048, upper head, rear cassette, C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen.

## Validation performed

- Blender: 713 vertices, 2229 edges, 1486 faces; zero boundary edges, zero non-manifold edges, zero BVH self-intersections; PASS.
- FreeCAD/OCCT conversion: one solid, one shell, 1027 faces, 1747 edges, 706 vertices, volume `78628.23 mm3`.
- FreeCAD `check_solid`, OCCT no-self-intersection verification, and `check_geometry`: valid, closed, watertight, exactly one solid; PASS.
- FCStd ZIP integrity: PASS.
- FreeCAD mesh validator conservatively reports intersections on the triangulated OBJ. This conflicts with Blender BVH and the valid OCCT one-solid result and is retained explicitly in `validation-v13.json`; it was not silently ignored.

## Rejected/unsafe variants

- FreeCAD automatic mesh repair removed faces and left the result open/non-manifold.
- FreeCAD self-fusion destroyed the envelope and produced two tiny solids.
- Unfiltered Blender EXACT self-union retained three small internal regions and seven non-manifold edges.
- No smoothing, remeshing, decimation, freehand remodeling, owner Boolean, or bilateral propagation is authorized.

## Exact regeneration command

From `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background --python source/generate_right_lower_face_topology_repair_review_v13.py -- --config config/right-lower-face-topology-repair-review-v13.json
```

The FreeCAD review file is then rebuilt by importing the generated OBJ, converting it to a solid with `0.001 mm` sewing tolerance, and saving it as the FCStd path above.

## Next physical/visual review

Open the V13 FCStd and inspect the isolated repaired lower-face component from exterior and interior views. Confirm that the silhouette is unchanged, the component is complete, and no hole, slot, seam, protrusion, or disconnected residue appeared. If approved, the next bounded step is to substitute this component into a copied V11 right-side owner assembly and re-run all eye/flange/C046/C048 clearance and ownership checks before any mirror or print export.
