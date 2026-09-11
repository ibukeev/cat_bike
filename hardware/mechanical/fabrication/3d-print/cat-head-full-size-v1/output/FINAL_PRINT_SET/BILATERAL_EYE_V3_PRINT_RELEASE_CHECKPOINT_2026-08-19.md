# Bilateral Eye V3 Print Release Checkpoint — 2026-08-19

## Release decision

The user visually approved the right-eye V3 corner-clearance repair and explicitly authorized final right/left FreeCAD and STL output. This release supersedes the physically failed V1 carrier meshes. The old V1 files remain present only for traceability and must not be printed.

## Printable output

Directory:

`01-eye-modules/v3-corner-repair-release-v1/`

Each side contains:

- one FreeCAD assembly with the carrier, translucent lens, and removable rear plate;
- one repaired-carrier STL, including the preserved user manual mounting flange;
- one translucent-lens STL with the approved integral hidden side flanges;
- one removable LED rear-plate STL.

No 3MF or G-code was created. The user will orient and slice the parts.

## Physical repair evidence

- Source carrier removed: `0.0 mm3`
- User manual flange missing: `0.0 mm3`
- V2 structural backing missing: `0.0 mm3`
- Minimum new-material clearance to every shell owner: `0.5628441175178516 mm`
- Right repaired carrier: valid, closed, one solid, deep-OCCT clean
- Left repaired carrier: exact X=0 / YZ mirror of the right carrier

## Bilateral validation

All six BReps are valid, closed, deep-clean single solids. All six generated and reloaded STLs are one-component, closed, manifold, outward-facing meshes with zero boundary edges, nonmanifold edges, degenerate facets, duplicate facets, or self-intersections.

The mirrored carrier, lens, and rear plate each have:

- topology match: PASS
- bounds error: `0.0 mm`
- vertex Hausdorff error: `0.0 mm`
- volume difference: below `0.00001 mm3`

PrusaSlicer 2.7.4 independently reports all six STLs as `manifold = yes` and `number_of_parts = 1`.

## Immutable evidence

- Release contract SHA-256: `5243cbf9436e6a1f69fdd04b98eca72268cb28f59cca1e1f9c781532dfdb332e`
- Exporter SHA-256: `a3054ebb332fccd0f019cacf2636cc809c12578e591a870246aa60671dad750a`
- Focused test SHA-256: `7e71efd9dabf12ce027d42ab1d85ac86ccfc518a365871865283e2660b572c95`
- Preflight SHA-256: `645728372dbae06a8a5fb1fcbe850b9af8b5a6743f3131542ee01aafb78d28a2`
- Release manifest SHA-256: `dec2a6f4864b2826f3c791e1c1aeeb1b3deb2f4eb7841ef0d39a54c0a2524996`

Focused pure-Python tests: `9/9 PASS`.

## Commands

Preflight:

```bash
timeout 420s env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python -B source/cad-change-control/print-release/bilateral-eye-carrier-corner-clearance-v3-release-v1/export_release.py --mode preflight --report /tmp/bilateral-eye-v3-corner-repair-print-release-preflight-20260819.json
```

Release:

```bash
timeout 480s env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python -B source/cad-change-control/print-release/bilateral-eye-carrier-corner-clearance-v3-release-v1/export_release.py --mode release --preflight-report /tmp/bilateral-eye-v3-corner-repair-print-release-preflight-20260819.json --preflight-sha256 645728372dbae06a8a5fb1fcbe850b9af8b5a6743f3131542ee01aafb78d28a2
```

## Next work

The bilateral eye modules are released. Continue serially with the previously accepted lower-head rear repartition; no head part is print-approved by this eye release.
