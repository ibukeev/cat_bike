# Rev112 final user-cutter holes — resumable checkpoint

Date: 2026-08-27  
State: **CAD and STL validation passed; user slicer/physical fit pending**

## Accepted decision and exact scope

The user selected `CAT_HEAD_MEDIUM_Ilya_FINAL_EDITS.FCStd` and explicitly
requested that the objects in its `Cutters` body be used to cut the head, then
requested a final FreeCAD head body and printable STL exports.

The integrated operation is deliberately narrow:

- immutable source SHA-256:
  `8114b71e27ff0e90a68d21bfc0b77f894bcfb8800760dd74a7e9a8a6cccfeb24`;
- target: `PRINT__CAT_HEAD_WITH_INTEGRATED_STOPS_REV108`;
- tool owner: `Body`, label `Cutters`;
- cumulative tool tip: `Pad003`, label `Cutter4`;
- tool compound: exactly four closed solids;
- Boolean: source head minus the cumulative four-solid tool, exactly once;
- final owner: `FINAL_HEAD_BODY_REV112` (`PartDesign::Body`);
- final tip: `PRINT__CAT_HEAD_FINAL_CUT_HOLES_REV112`;
- the four translucent panes are copied without geometric changes;
- the two approved 12 x 5 mm rear zip-tie corridors remain through-open;
- the user-owned `Final MVP.3mf` was not used as geometry, changed, or
  included; its final read-only SHA-256 check was
  `e5b30a5b8b9c52f020ae52738be3aadeeac34b4ba3d422ee8924e7f9883099b1`.

Each user cutter pad has a signed FreeCAD pad length of `-10.0 mm`. The four
measured source-head intersections are:

1. Cutter1: `1405.8654821155703 mm3`
2. Cutter2: `1400.500520861807 mm3`
3. Cutter3: `1600.3535521786196 mm3`
4. Cutter4: `1600.3535521786123 mm3`

The final subtraction removes `6007.073107457836 mm3`.

## Canonical generated outputs

Directory:
`hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/head-rev112/`

- `CAT_HEAD_MEDIUM_ILYA_FINAL_CUT_HOLES_REV112.FCStd`
  - SHA-256: `4a0ae787902be81ecccfadedd46603064b4729de4b71231e17e63add87477e85`
- `CAT_HEAD_MEDIUM_ILYA_FINAL_HEAD_CUT_HOLES_REV112.stl`
  - SHA-256: `eae4d27e8f18762e0deb6fe7bf95d62fb9a99a93ed8decc2eb8aad9af85891c6`
- `CAT_HEAD_MEDIUM_RIGHT_EYE_TRANSLUCENT_PANE_REV112.stl`
  - SHA-256: `739f584563eb2797eaa72fd9d4d9ebbfa7df3ffe62080475511f21bf4b410ee5`
- `CAT_HEAD_MEDIUM_LEFT_EYE_TRANSLUCENT_PANE_REV112.stl`
  - SHA-256: `62380023c9379d2c1a1f984fa453a3187870f04ce150f745d9861e0060141d84`
- `CAT_HEAD_MEDIUM_MOUTH_TRI005_TRANSLUCENT_PANE_REV112.stl`
  - SHA-256: `3279a271f8d3d86f94466e256732d4541b9ead051dfe10b8596ab8f877ac3356`
- `CAT_HEAD_MEDIUM_MOUTH_TRI006_TRANSLUCENT_PANE_REV112.stl`
  - SHA-256: `b9c7a36e377b50da2704a41aca8d81b018764a718b4c00a9361283a0e82061df`
- `generation-report.json`
  - SHA-256: `249f40c16c61f74cad011389c3a6929ca4b86a39b9448b1d0ccc6ee28f727716`
- `validation-report.json`
  - SHA-256: `7442b92525ea709b706de98681d581cdba7428e09869a0303bd2b54a9d6ca9c9`
- `occt-bop-check-report.json`
  - SHA-256: `18911b21a8dc4b98e93509d838e87ce567e520d2a7692e072296b12104f40b45`
- `rev112-front-final-head-cut-holes.png`
  - SHA-256: `cd0c6d4bf6eae5f98bf8a01c4c66bbc4f198e06db718d931b88fe99f1659ac4f`
- `rev112-isometric-final-head-and-panes.png`
  - SHA-256: `83f719a824d33d52bf6f4ecc4fe271fa0d7437ddd2426484182c7f526074eb3b`

This review directory contains convenience copies of those artifacts. The
canonical immutable references are recorded in:
`hardware/mechanical/fabrication/3d-print/cat-head-small-v1/releases/final-mvp-v2/release-manifest.json`.

## Validation performed and results

- Rev112 contract tests: `8/8 PASS`.
- Source FCStd SHA-256 before/after preflight, generation, and validation:
  unchanged.
- No-output preflight: `PASS`.
- Pinned FreeCAD runtime: FreeCAD `1.1.3`, OCCT `7.8.1`.
- Saved FCStd ZIP/archive test: no errors.
- Reopened final head:
  - valid: yes;
  - closed: yes;
  - solids: `1`;
  - shells: `1`;
  - faces: `39723`;
  - volume: `348673.5134495925 mm3`;
  - bounds: `174.932998657 x 141.777130127 x 190.0 mm`.
- Full OCCT BOP/self-intersection check: `PASS`, zero reported errors.
- Final-head intersection with cumulative cutter compound: `0.0 mm3`.
- Material added outside Rev108: `0.0 mm3`.
- Right zip-tie corridor residual: `0.0 mm3`.
- Left zip-tie corridor residual: `0.0 mm3`.
- All four pane symmetric-difference residuals: `0.0 mm3`.
- All four Rev112 pane STL hashes exactly match their Rev108 STL hashes.
- PrusaSlicer inspection:
  - head: manifold yes, one part, `43518` facets;
  - each eye pane: manifold yes, one part, `12` facets;
  - each mouth pane: manifold yes, one part, `8` facets.

## Rejected or unsafe variants

- Do not subtract `Pad`, `Pad001`, `Pad002`, and `Pad003` sequentially. Their
  ordinary `Shape` properties are cumulative; doing this obscures the intended
  four-solid tool definition and repeats earlier cuts. Rev112 subtracts the
  complete `Body.Shape`/`Pad003` tip exactly once and uses each pad's
  `AddSubShape` only for validation.
- Do not overwrite `CAT_HEAD_MEDIUM_Ilya_FINAL_EDITS.FCStd`. It is the pinned
  design input and remains the recovery source.
- Do not modify or adopt `Final MVP.3mf`; it is user-owned slicer work from the
  earlier revision.
- Do not return to the screw/boss/washer proposal or full-eye backing steps.
  The accepted retention design remains the twelve simple 1 mm projection,
  3 mm total-depth stops.
- Do not run dense OCCT BOP checks through the interactive FreeCAD bridge. That
  check crashed the live GUI. The final BOP check passed in an isolated
  FreeCADCmd process and is hash-bound in `occt-bop-check-report.json`.
- A redundant Boolean comparison of the saved Body against its identical tip
  was rejected after proving too slow. The released validator uses the actual
  Body/Tip relationship plus exact topology, volume, and bounds comparisons.

## Exact regeneration commands

The generator is one-shot and refuses to overwrite an existing Rev112 output.
Run these commands only in a clean checkout or after moving the existing output
directory to a clearly named archive.

First run the deterministic contract tests:

```bash
python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract
```

Start the installed FreeCAD AppImage once, or keep `freecad --appimage-mount`
running in another terminal, then locate its console executable:

```bash
FREECADCMD="$(find /tmp/.mount_freeca*/usr/bin -maxdepth 1 -name freecadcmd -print -quit)"
test -x "$FREECADCMD"
```

Run the no-output preflight:

```bash
SCRIPT_DIR="$PWD/hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/print-release/small-v1-final-user-cutter-holes-rev112"
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/preflight.py', run_name='__main__')" | "$FREECADCMD" -c
```

After updating only the hash pins in `run_pinned.py` to the passed preflight,
run the one-shot generator and independent saved-artifact validator:

```bash
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/run_pinned.py', run_name='__main__')" | "$FREECADCMD" -c
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/validate.py', run_name='__main__')" | "$FREECADCMD" -c
blender --background --python "$SCRIPT_DIR/render_evidence.py"
```

## Next physical-review steps

1. Import only `CAT_HEAD_MEDIUM_ILYA_FINAL_HEAD_CUT_HOLES_REV112.stl` into a new
   slicer project or a copy of the prior project; do not overwrite the prior
   `Final MVP.3mf` during comparison.
2. Confirm one connected part, no automatic mesh repair, and no filled eye,
   mouth, or rear zip-tie openings.
3. Inspect the four new cutter openings layer-by-layer at their thinnest wall
   transitions and confirm supports do not bridge them closed.
4. Print a low-height or local aperture test if desired, then dry-fit the two
   eye panes and two mouth panes against the twelve stops.
5. Physically pass the intended zip ties through both rear 12 x 5 mm slots.
6. Record slicer orientation/profile, pane fit, zip-tie fit, and any physical
   interference before promoting this from slicer-fit-pending to fabrication
   release.
