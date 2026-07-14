# Cat Head Phase 1: 100 mm Printable Shell

This package generates a small one-piece proof print from the approved V1 faceted cat-head geometry.

## Source of Truth

- Approved design package: `templates/cat-head-wireframe-prototype/versions/v1-shape-approved-cardboard-prototype/`
- Coherent faceted input: `templates/cat-head-cardboard-fabrication-v1/assembly/accepted-panels-3d.obj`

The original panel IDs and rod graph remain in those frozen sources for the later full-size split model.

## Phase-1 Model

- Conceptual head height: 100 mm
- One-piece hollow shell
- 1.2 mm modeled wall thickness
- Flat rear opening placed on printer Z=0
- Approved facets retained
- Eye and non-ear shell gaps closed; two intended inner-ear openings retained
- No rods, mounts, detachable panels, pins, or fasteners yet

Generated files are under `output/`:

- `cat-head-100mm-shell-mk4s.stl`: print this file
- `cat-head-100mm-shell-mk4s.obj`: inspectable mesh
- `cat-head-100mm-shell-mk4s.blend`: editable Blender source
- `validation-report.json`: dimensions and mesh checks
- `cat-head-100mm-shell-print-orientation.png`: bed-orientation preview
- `cat-head-100mm-shell-front.png`: front-shape preview

## Generate

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-small-v1/generate_small_printable_head.py
```

## Prusa MK4S Starting Profile

- Material: PLA
- Nozzle: 0.4 mm
- Layer height: 0.15 or 0.20 mm
- Perimeters: 3
- Infill: 0%
- Top/bottom solid layers: 4
- Orientation: keep the STL orientation; flat rear opening goes on the bed
- Brim: 5 mm recommended
- Supports: organic, build plate only, only where PrusaSlicer flags unsupported areas
- Scale: 100%; do not use automatic build-volume scaling

Inspect the sliced preview before printing, especially the ears, eye region, and rear opening.

## Future Full-Size Version

The full-size design will be split along deliberate facet/rod boundaries. Sections will receive keyed alignment pins and assembly joints; selected panels can then become removable translucent or reflective inserts. Do not segment the phase-1 STL directly because it no longer carries panel identity metadata.
