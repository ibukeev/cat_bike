# Tiny single-shell prototype — 100 mm

This is the original one-piece proof print from the accepted faceted geometry.
The retained files are in [release/](release/).

- Editable model: `cat-head-100mm-shell-mk4s.blend`.
- Printable mesh: `cat-head-100mm-shell-mk4s.stl`; the OBJ is also retained.
- Evidence: `validation-report.json` and the front/orientation previews.
- Print history: both G-code files in `release/Printing/`, at 0.20 and 0.30 mm
  layer height. The exact physical job used has not been identified.

The saved validation reports 100 mm conceptual head height, 1.2 mm wall
thickness, one connected component, zero nonmanifold edges, and print-oriented
bounds of 92.07 × 100.00 × 74.62 mm. These are historical digital measurements.

## Source and regeneration

The generator reads the shared
`hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1/assembly/accepted-panels-3d.obj`.
That input and its approved wireframe design package remain at their original paths.

From the repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-tiny-prototypes/single-shell-100mm/generate_small_printable_head.py
```

New output goes to `output/`; the retained release files stay in `release/`.
The cleanup changed only the generator's repository-root lookup. No geometry
was regenerated.

The original starting profile was a 0.4 mm nozzle, PLA, 0.15–0.20 mm layers,
three perimeters, 0% infill, four top/bottom layers, a 5 mm brim, and build-plate
supports where needed. The flat rear opening lies on the bed. This is a
prototype record, not the midsize Burning Man print profile.
