# Cat Bike LED Installation

Hardware project for a Burning Man electric bike LED installation.

## Getting the retained CAD and print files

Install [Git LFS](https://git-lfs.com/) before cloning this repository, then run:

```bash
git lfs install --local
git lfs pull
```

Selected mechanical CAD, meshes and slicer projects are stored with Git LFS.
Most generated output stays ignored; the curated build milestones are explicitly
tracked. A pointer-only checkout is not a usable CAD backup. Git history was not
rewritten when LFS was introduced, and retained working-file bytes are unchanged.

The repository tracks electrical design, Pixelblaze controller patterns, LED layout, battery/power notes, wiring, mechanical mounting ideas, and build documentation.

## Structure

- `hardware/electrical/` - battery, Pixelblaze controller, LEDs, and wiring.
- `hardware/mechanical/` - mounts, enclosures, and bike attachment parts.
- `software/pixelblaze-patterns/` - exported or source Pixelblaze patterns.
- `software/tools/` - helper scripts for mapping, validation, or exports.
- `docs/` - assembly notes, BOM, safety notes, and design logs.
- `assets/` - photos, diagrams, references, and visual documentation.
- `tests/` - manual and automated checks.

## Current build records

- [Lighting: mapper, patterns, setup, and validation](software/pixelblaze-patterns/mvp-bike/README.md).
- [Retained fabrication packages](hardware/mechanical/fabrication/3d-print/README.md): tiny prototypes, midsize Burning Man head, and controller enclosure.
- [Cleanup record and recovery instructions](docs/PROJECT_CLEANUP_PLAN.md).
- [Large-head working print files](hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/README.md): selected left/right lower-shell STL and slicer packages.

The large head has been reduced to [selected rebuild references](hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/README.md).
Old iterations and diagnostics are in ignored local recovery; no new whole-head
print release was approved.
The reports folder was emptied on 2026-09-10. Retired reports and early
head-mount concepts are recoverable through the cleanup record.
