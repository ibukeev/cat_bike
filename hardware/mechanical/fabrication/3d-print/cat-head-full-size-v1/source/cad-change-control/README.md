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

Run the BREP health audit through the checked-in script using the verified
FreeCAD 1.1.3 AppImage runtime extracted under `/tmp`:

```bash
mkdir -p reports/generated/cat-head-cad-validation/v1
CAT_HEAD_FREECAD_APPDIR=/path/to/FreeCAD-1.1.3-AppDir
env PYTHONPATH="$CAT_HEAD_FREECAD_APPDIR/usr/lib" \
  "$CAT_HEAD_FREECAD_APPDIR/AppRun" python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_freecad_shapes.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v1.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json \
  --report reports/generated/cat-head-cad-validation/v1/v17-eye-brep-report-v2.json
```

The portable runtime is the official x86_64 FreeCAD 1.1.3 AppImage with
SHA-256 `3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef`.
Do not launch the GUI with `--manifest`; the GUI treats that validator option
as its own and fails before the audit starts. Do not substitute a GUI macro,
inline Python, or automatic mesh repair.

The V17 pilot currently fails the mandatory deep OCCT check with 38 BOP
self-intersection diagnostics. Being closed, `isValid()`, and a single solid
is not sufficient for a pass.

The pilot deliberately includes accepted, proposed, rejected, and diagnostic
artifacts. Their statuses prevent a rejected review from becoming a production
source just because its file still exists.

## Review loop after this pilot

For a future geometry change, first create a new immutable baseline manifest and
contract. Then create one isolated right-side proposal, validate it, and render
the six required static review views. Only explicit user approval may advance
that exact proposal to integration.
