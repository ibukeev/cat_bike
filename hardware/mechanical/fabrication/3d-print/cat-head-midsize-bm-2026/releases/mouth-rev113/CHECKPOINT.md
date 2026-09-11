# Rev113 one-piece translucent mouth pane — resumable checkpoint

Completion date: 2026-08-28  
State: **CAD/STL validation passed; visual, slicer, and physical insertion review pending**

## Accepted decision and exact scope

The user requested that the two Rev112 translucent mouth panels be merged into
one single PETG print part. This Rev113 candidate is isolated from the accepted
Rev112 head package and is not promoted as a replacement final MVP release.

Frozen without geometric change:

- the Rev112 final head, including four user-cutter openings, twelve simple
  panel stops, and both 12 x 5 mm zip-tie slots;
- the Rev112 right and left translucent eye panes;
- every point and surface of the two Rev112 mouth panes outside their inward
  center-seam faces;
- the user-owned slicer project, profiles, 3MF files, and G-code.

Changed:

- `PRINT__MOUTH_TRI005_TRANSLUCENT_PANE_REV112.Face1` and
  `PRINT__MOUTH_TRI006_TRANSLUCENT_PANE_REV112.Face1` are connected by one
  ruled, closed solid bounded exactly by their existing outer wires;
- the original minimum center gap is `0.5949922084458888 mm`;
- added bridge volume is `28.95407782429441 mm3`;
- the resulting one-piece mouth volume is `792.5075282477266 mm3`;
- mouth thickness remains nominally `2.0 mm` and the panel remains hole-free.

## Current review and output files

Canonical generated directory:
`hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/mouth-rev113/`

- `CAT_HEAD_MEDIUM_ILYA_MERGED_MOUTH_REV113.FCStd`
  - SHA-256: `3b054f9019717d7a73e16915b4bbde809f6fbf550a10f16507219ae54f72a7b1`
- `CAT_HEAD_MEDIUM_ILYA_FINAL_HEAD_REV113.stl`
  - SHA-256: `eae4d27e8f18762e0deb6fe7bf95d62fb9a99a93ed8decc2eb8aad9af85891c6`
  - exact byte copy of the validated Rev112 head STL
- `CAT_HEAD_MEDIUM_RIGHT_EYE_TRANSLUCENT_PANE_REV113.stl`
  - SHA-256: `739f584563eb2797eaa72fd9d4d9ebbfa7df3ffe62080475511f21bf4b410ee5`
  - exact byte copy of the validated Rev112 right-eye STL
- `CAT_HEAD_MEDIUM_LEFT_EYE_TRANSLUCENT_PANE_REV113.stl`
  - SHA-256: `62380023c9379d2c1a1f984fa453a3187870f04ce150f745d9861e0060141d84`
  - exact byte copy of the validated Rev112 left-eye STL
- `CAT_HEAD_MEDIUM_MERGED_MOUTH_TRANSLUCENT_PANE_REV113.stl`
  - SHA-256: `9e9ec394be8bd70982ce7c015f4b3f006f0eb111b62577c02deb767228eca9fe`
- `REVIEW_ONLY__MOUTH_CENTER_SEAM_BRIDGE_REV113.stl`
  - SHA-256: `9533e6166acc691b581d8af745c49e71f9d3f3fc58eac00b2d59eb8ee5b52c50`
  - evidence only; do not print as a separate part
- `generation-report.json`
  - SHA-256: `311e482f0a018e7a7618293bedb3e81dac9609f4a60aa5c9468b108edadde636`
- `validation-report.json`
  - SHA-256: `ab06510c405ffdcc74765f97c35d866a38012ed38870358c77f8693f1e8c8c85`
- `occt-bop-check-report.json`
  - SHA-256: `0d167e49c784ac39012fa4e9cfdf78946dbdb78befa54eea9b56f38aee3c0d1c`
- `rev113-front-final-head-and-one-piece-mouth.png`
  - SHA-256: `cfe257269525c3d315fa1a52557bbfc0d4b2b57f4b646d71e043ebd972174378`
- `rev113-isometric-final-four-part-package.png`
  - SHA-256: `fa18cf0d3239c33460ff54b98675fa9cfd21d1ed148619c4b16c86f48b8ce32d`
- `rev113-isolated-mouth-halves-and-seam-only-bridge.png`
  - SHA-256: `541d8c77fb8fcbb2f5835ccb9532d65be81ef5c0feadfce63082d637cba541e4`
- `rev113-dimensioned-seam-contract.svg`
  - SHA-256: `3a57619e45e6219983c918ee4eb0a78368899d6041d09644468661d0e29d2c9a`

The current directory is a convenience review copy. The generated directory
above is canonical.

## Validation performed and results

- Rev113 contract tests: `7/7 PASS`.
- No-output preflight: `PASS`.
- Pinned source:
  `CAT_HEAD_MEDIUM_ILYA_FINAL_CUT_HOLES_REV112.FCStd`, SHA-256
  `4a0ae787902be81ecccfadedd46603064b4729de4b71231e17e63add87477e85`.
- Pinned runtime: FreeCAD `1.1.3`, OCCT `7.8.1`.
- Saved FCStd archive validation: `PASS`, size `7,699,112 bytes`.
- Merged mouth:
  - valid: yes;
  - closed: yes;
  - solids: `1`;
  - shells: `1`;
  - faces: `12`;
  - edges: `22`;
  - vertices: `12`;
  - volume: `792.5075282477266 mm3`.
- Both original mouth halves minus the merged result: `0.0 mm3`.
- Material added outside the original halves versus bridge-volume residual:
  `0.0 mm3` within the `0.000001 mm3` contract tolerance.
- Merged mouth versus frozen head overlap: `0.0 mm3`.
- Right and left zip-tie corridor residuals: `0.0 / 0.0 mm3`.
- OCCT BOP/self-intersection check of changed mouth: `PASS`.
- PrusaSlicer mesh inspection:
  - head: manifold yes, one part;
  - right eye: manifold yes, one part;
  - left eye: manifold yes, one part;
  - merged mouth: manifold yes, one part, `24` facets;
  - review-only bridge: manifold yes, one part, `16` facets.
- Visual evidence review: front, isometric, isolated bridge, and numeric seam
  contract all show a continuous faceted mouth with no central gap.

## PETG support starting point

Use **supports on build plate only**, not supports everywhere.

- For the head, supports everywhere can create trapped PETG support inside the
  eye and mouth openings, behind the twelve stops, or around the rear zip-tie
  holes. Use build-plate-only snug/organic support and inspect every opening in
  layer preview.
- For the eye panes, use no support when a broad non-visible face can sit on the
  bed.
- For the one-piece mouth, first try one triangular pane face on the bed with
  the visible exterior faces kept away from support contact. If the raised
  facet needs help, use build-plate-only support under it.
- PETG can bond aggressively to support interfaces. At `0.20 mm` layer height,
  start around `0.25–0.30 mm` top contact distance and verify the preview and a
  small test before committing the visible part.
- No slicer profile, 3MF, orientation project, or G-code was generated here.

## Rejected or unsafe variants

- `hardware/mechanical/fabrication/3d-print/cat-head-midsize-bm-2026/releases/mouth-rev113-rejected-r1-head-remesh/`
  is the preserved tooling-revision-1 package. Its CAD head geometry and facet
  count were unchanged, but FreeCAD re-tessellated the frozen head STL and
  changed its byte hash to
  `6555f95bac740fe63f20de230a3990cd8d13c737ffca7a05902384ed4dfc796f`.
  It is rejected for packaging, not for a detected geometric defect. Do not
  use it; Rev113 tooling revision 2 copies the Rev112 head and eye STLs
  byte-for-byte.
- Do not flatten the two mouth facets into one plane. The accepted candidate
  preserves their seated faceted geometry and bridges only the center seam.
- Do not widen the center bridge, change the exterior pane perimeter, add
  holes, or alter the head stops without a new isolated contract and review.
- Do not print `REVIEW_ONLY__MOUTH_CENTER_SEAM_BRIDGE_REV113.stl` by itself.
- Do not enable supports everywhere without verifying that every generated
  support island is accessible for removal.

## Exact regeneration commands

The generator is one-shot and refuses to overwrite an existing Rev113 output.
Run only in a clean checkout or after moving the existing candidate directory
to an explicitly named archive.

```bash
python3 -m unittest tests.automated.test_small_v1_merged_mouth_pane_rev113_contract
```

Start or mount the approved FreeCAD AppImage, then locate its console:

```bash
freecad --appimage-mount
FREECADCMD="$(find /tmp/.mount_freeca*/usr/bin -maxdepth 1 -name freecadcmd -print -quit)"
test -x "$FREECADCMD"
```

```bash
SCRIPT_DIR="$PWD/hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/print-release/small-v1-merged-mouth-pane-rev113"
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/preflight.py', run_name='__main__')" | "$FREECADCMD" -c
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/run_pinned.py', run_name='__main__')" | "$FREECADCMD" -c
printf '%s\n' "import sys, runpy; sys.path.insert(0, r'$SCRIPT_DIR'); runpy.run_path(r'$SCRIPT_DIR/validate.py', run_name='__main__')" | "$FREECADCMD" -c
blender --background --python "$SCRIPT_DIR/render_evidence.py"
```

## Next physical-review steps

1. Open `CAT_HEAD_MEDIUM_MERGED_MOUTH_TRANSLUCENT_PANE_REV113.stl` by itself
   and confirm the slicer reports one part and performs no automatic repair.
2. Orient one triangular face on the bed. Try no supports first; otherwise use
   build-plate-only supports beneath the raised facet and keep support away
   from the exterior face.
3. Print the merged mouth before the full head and dry-fit it against all four
   mouth stops. Confirm it can enter the opening as one rigid piece without
   flexing, cutting, or scraping.
4. Check that both exterior facets sit flush, the center bridge is visually
   acceptable, and the panel cannot slide inward.
5. Only after that fit test, import the unchanged Rev112/Rev113 head and eye
   STLs into the intended slicer project. Keep the existing project as a
   recovery copy rather than overwriting it.
