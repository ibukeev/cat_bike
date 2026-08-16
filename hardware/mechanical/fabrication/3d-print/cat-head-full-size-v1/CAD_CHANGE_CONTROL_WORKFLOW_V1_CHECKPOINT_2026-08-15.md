# Cat-head CAD change-control workflow V1 checkpoint — 2026-08-15

## Outcome

The two deep-research reports in
`/home/bsk/Projects/AI Agents/openclaw-setup/tmp` were reviewed and converted
into a repository-owned workflow. FreeCAD remains the canonical BREP editor.
OpenSCAD is not used to rebuild the existing faceted shell.

No CAD document, STEP, mesh, owner body, reinforcement, flange, connector,
mirror surface, slicer project, STL, G-code, or print geometry changed in this
work item.

## Current control files

- Workflow:
  `source/cad-change-control/README.md`
- Baseline schema:
  `source/cad-change-control/baseline-manifest.schema.json`
- Change-contract schema:
  `source/cad-change-control/change-contract.schema.json`
- Pilot baseline:
  `source/cad-change-control/pilot/baseline-manifest-v1.json`
- Pilot contract:
  `source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json`
- Standard-Python preflight:
  `source/cad-change-control/validate_change_contract.py`
- Read-only FreeCAD/OCCT validator:
  `source/cad-change-control/validate_freecad_shapes.py`
- Regression tests:
  `../../../../../tests/automated/test_cat_head_cad_change_control.py`

## Frozen and excluded evidence

The pilot manifest pins these exact artifacts:

- Frozen accepted right eye V17 STEP:
  `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Approved isolated, non-production C027 V19 review:
  `126233487030a0606d74380ba1d6bd263bc067bafc7f8dc3410e8bb76f676b65`
- Proposed, not reconciled C012 V24 review:
  `f7a410a097daad4f6e2e93ca6877120540ac1e202627effa35ff0792b431b355`
- User-rejected C001 V27 review:
  `e31d8b1167122f14d188ea6cff70a512c1913965ba0ac25224fd8e44c1a4e849`
- Known-bad V16 eye mesh with 30 verified crossings:
  `4df70cc1bf0cb08e57529823c1cff09e5f17b231ad6b7a27e18beb1d6f8fe781`

Rejected and known-bad artifacts are retained only as negative regression
evidence. The validator refuses to promote either status to a target.

## Accepted workflow decisions

1. One immutable baseline manifest, one target owner, and one numeric contract
   per run.
2. Every declared input is verified by SHA-256 before CAD inspection.
3. Validation scripts are read-only: no save, heal, refine, fuse, cut, move,
   rename, overwrite, or export.
4. Clearance is encoded once per pair: actual-geometry distance or inflated
   keepout intersection, never both.
5. One right-side isolated proposal is reviewed before integration or mirroring.
6. A passing validation report is evidence only; it does not authorize a
   production union, mirror, STL, slicing, G-code, or ASA print.
7. Review uses a fixed static review pack. The user should not have to discover
   hidden geometry by navigating a large live FreeCAD tree.

## Validation performed

The following completed successfully:

- Python syntax compilation for both validators and the regression test.
- Six automated regression tests:
  - valid read-only contract passes;
  - rejected target fails closed;
  - double-counted clearance policy fails closed;
  - output outside the validation tree fails closed;
  - hash mismatch fails closed.
  - disabling the mandatory deep OCCT check fails closed.
- Pilot manifest and contract validation: **PASS**.
- All five declared artifact hashes: **VERIFIED**.
- Geometry mutation: **NONE**.

The official FreeCAD 1.1.3 x86_64 AppImage was downloaded and its SHA-256
verified as
`3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef`.
The bundled Python/OCCT audit now runs without GUI automation.

The first runtime report exposed a fail-open validator defect: V17 was closed,
`isValid()`, and one solid, but `shape.check(True)` raised BOP self-intersection
errors. That report's `PASS` status is superseded. The corrected replacement
report is `v17-eye-brep-report-v2.json`; it exits nonzero with **FAIL** and
records 38 BOP self-intersection diagnostics. The inspected V17 metrics are
1,178 faces, 2,342 edges, 1,156 vertices, one shell, one solid, and
7,269.553010791169 mm³ volume. No geometry was changed or healed.

## Exact regeneration commands

From the repository root:

```bash
python3 -m py_compile \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_change_contract.py \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_freecad_shapes.py \
  tests/automated/test_cat_head_cad_change_control.py

python3 -m unittest tests.automated.test_cat_head_cad_change_control -v

python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_change_contract.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v1.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json \
  --verify-files
```

CAT_HEAD_FREECAD_APPDIR=/path/to/FreeCAD-1.1.3-AppDir
env PYTHONPATH="$CAT_HEAD_FREECAD_APPDIR/usr/lib" \
  "$CAT_HEAD_FREECAD_APPDIR/AppRun" python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_freecad_shapes.py \
  --manifest hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/baseline-manifest-v1.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/read-only-v17-eye-audit-v1.json \
  --report reports/generated/cat-head-cad-validation/v1/v17-eye-brep-report-v2.json

## Next review and release state

The next CAD task is a contract-bound localization of the V17 right-eye
self-intersections. Do not resume C001 work, mirror, unite production owners,
or export print geometry until V17 passes the mandatory OCCT deep check. Any
subsequent repair must target only the right-eye owner, preserve its exterior
and approved mating positions, and produce the six fixed review views before
the user is asked to approve it.

There is no physical-review action from this workflow-only checkpoint. Existing
physical-fit gates, production owner unification, STL export, slicing, G-code,
and structural ASA printing remain held.
