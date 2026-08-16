# Cat-head deterministic CAD change control

This directory is the workflow boundary between an approved CAD baseline and
a proposed structural change. It exists to stop visual iteration from silently
changing unrelated geometry.

## Rules

1. FreeCAD remains the canonical BREP editor. OpenSCAD is not used to rebuild
   the faceted shell.
2. Every run starts from `pilot/baseline-manifest-v1.json`, or a later reviewed
   manifest, and verifies every declared SHA-256 digest.
3. Every run has one target owner and a machine-readable change contract.
4. Validation scripts are read-only. They do not heal, refine, fuse, cut, move,
   save, or export geometry.
5. Clearance is represented exactly once: either distance to actual geometry,
   or zero residual intersection against an explicitly inflated keepout. The two
   modes must never be combined.
6. A validation pass is evidence only. It never releases mirroring, STL export,
   slicing, G-code, or ASA printing.

## Commands

Validate the manifest and contract with standard Python:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_change_contract.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v1.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json \
  --verify-files
```

Run the BREP health audit through the checked-in script using a FreeCAD
installation whose `FreeCADCmd` supports documented script mode:

```bash
mkdir -p reports/generated/cat-head-cad-validation/v1
FreeCADCmd hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_freecad_shapes.py \
  --pass=--manifest \
  --pass=hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v1.json \
  --pass=--contract \
  --pass=hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json \
  --pass=--report \
  --pass=reports/generated/cat-head-cad-validation/v1/v17-eye-brep-report.json
```

The locally installed FreeCAD 1.1.1 Snap currently exits `freecad.cmd`
without entering Script mode, while its GUI launcher fails during Qt/PySide
initialization. Until that package is replaced or fixed, the standard-Python
contract/hash gate remains usable but the OCCT report must stay marked
`NOT_RUN_RUNTIME_BLOCKED`. Do not substitute a GUI macro, inline Python, or an
automatic mesh repair.

The pilot deliberately includes accepted, proposed, rejected, and diagnostic
artifacts. Their statuses prevent a rejected review from becoming a production
source just because its file still exists.

## Review loop after this pilot

For a future geometry change, first create a new immutable baseline manifest and
contract. Then create one isolated right-side proposal, validate it, and render
the six required static review views. Only explicit user approval may advance
that exact proposal to integration.
