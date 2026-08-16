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
- Five automated regression tests:
  - valid read-only contract passes;
  - rejected target fails closed;
  - double-counted clearance policy fails closed;
  - output outside the validation tree fails closed;
  - hash mismatch fails closed.
- Pilot manifest and contract validation: **PASS**.
- All five declared artifact hashes: **VERIFIED**.
- Geometry mutation: **NONE**.

The FreeCAD/OCCT V17 BREP health report is
`NOT_RUN_RUNTIME_BLOCKED`. The installed FreeCAD 1.1.1 Snap
`freecad.cmd` exits without entering Script mode, and its GUI launcher fails
during Qt/PySide initialization. No macro, inline Python, automatic healing, or
alternate geometry rewrite was used to manufacture a pass.

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

After installing or repairing a FreeCAD distribution whose `FreeCADCmd`
supports documented script mode, run the BREP command recorded in
`source/cad-change-control/README.md`.

## Next review and release state

The next CAD task must start by creating a new contract for exactly one owner
and one physical objective. It must produce an isolated right-side proposal,
machine-readable validation results, and the six fixed review views before the
user is asked to approve anything.

There is no physical-review action from this workflow-only checkpoint. Existing
physical-fit gates, production owner unification, STL export, slicing, G-code,
and structural ASA printing remain held.
