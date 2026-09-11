# Midsize cat head — Burning Man 2026

The user confirmed that this midsize head was printed for Burning Man. The
saved CAD is 190 mm tall. The saved pane project combines Rev112 eyes with the
Rev113 one-piece mouth.

## Current build files

| Purpose | Location |
| --- | --- |
| Head CAD, head/eye STLs, and head slicer projects | [Head Rev112](releases/head-rev112/) |
| CAD with the merged mouth, mouth STL, and its validation | [Mouth Rev113](releases/mouth-rev113/) |
| Combined eye and mouth slicer project | [Eyes_and_Mouth.3mf](releases/head-rev112/Eyes_and_Mouth.3mf) |
| User-edited source CAD and earlier manual inputs | [User final edits](source/user-final-edits/) |
| Original release manifest | [Rev112 manifest](releases/final-mvp-v2/release-manifest.json) |

The head folder contains both `CAT_HEAD_MEDIUM_ILYA_FINAL_HEAD_CUT_HOLES_REV112.3mf`
and `CAT_HEAD_MEDIUM_ILYA_FINAL_HEAD_CUT_HOLES_REV112_Build_plateOnly.3mf`.
They differ in support, perimeter, and infill settings; both are retained because
the exact job used for the physical print has not yet been identified.

Rev113's head and eye STL filenames link to the byte-identical Rev112 exports.
The original two mouth-pane STLs remain with Rev112 because its validator uses
them. The one-piece mouth is
`releases/mouth-rev113/CAT_HEAD_MEDIUM_MERGED_MOUTH_TRANSLUCENT_PANE_REV113.stl`.
The separate `REVIEW_ONLY__MOUTH_CENTER_SEAM_BRIDGE_REV113.stl` is validation
evidence and is not an assembly part.

## Source, validation, and regeneration

The final user-edited input is
`source/user-final-edits/CAT_HEAD_MEDIUM_Ilya_FINAL_EDITS.FCStd`.
Keep it with the final CAD and exports. The older `Final MVP.3mf`, `HEAD.stl`,
and `Cutter1.stl` beside it are preserved manual inputs.

[Head tooling](tooling/head-rev112/) and [mouth tooling](tooling/mouth-rev113/)
link to the original pinned scripts inside the excluded large-head directory.
Geometry, construction code, preflight reports in `validation/`, and the shared
FreeCAD runtime manifest retain their original bytes and hashes. Contracts in
`config/v2/` received filesystem-path-only edits on 2026-09-10. Their byte
hashes changed; original preflight evidence and authorization pins did not.

Historical generation/validation commands and fit observations remain in
the [head checkpoint](releases/head-rev112/CHECKPOINT.md) and
[mouth checkpoint](releases/mouth-rev113/CHECKPOINT.md). The one-shot generators
refuse existing output directories; no generator was run during cleanup.

Run the off-device final contract checks from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract
```

Legacy review links outside `reports/` remain. The reports folder is empty,
with no aliases; contracts and the evidence renderer use this package directly.

Generation hold: both one-shot wrappers intentionally reject their changed
contract hashes before generation. A fresh authorized no-output preflight and
reviewed pin update are required before regeneration. Do not rewrite old PASS
records or overwrite retained release folders. Design values, source geometry,
and historical release flags are unchanged.

Next physical documentation: identify the head slicer profile actually used
and record pane fit, mounting behavior, and Burning Man wear or failures.
