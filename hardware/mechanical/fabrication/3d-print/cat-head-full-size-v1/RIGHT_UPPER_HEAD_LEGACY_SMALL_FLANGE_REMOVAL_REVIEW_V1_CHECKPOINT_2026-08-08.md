# Right Upper-Head Legacy Small-Flange Removal Review V1 — 2026-08-08

## State

An isolated right-side proposal removes only the small legacy internal
projection selected by the user on
`PROPOSED__RIGHT_UPPER_HEAD__VALIDATION_COMPOUND_V3.Face1668`. The accepted V3
upper-head object is preserved and hidden for comparison. Nothing is
integrated, mirrored, exported, sliced, or released for printing.

On 2026-08-09 the user visually approved this isolated removal with
“lgtm go next.” Approval applies only to the selected Face1668 projection
removal; it does not authorize integration or mirroring.

The preceding right-B `1.9 mm` panel-tab relief was visually approved by the
user before this bucket started.

## Review files

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/CAT_HEAD_RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1.FCStd`
- Numeric contract:
  `config/right-upper-head-legacy-small-flange-removal-review-v1.json`
- Clean context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/review/01-clean-context-isometric.png`
- Internal before/after:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/review/04-before-local-inside-left.png`
  and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/review/05-after-local-inside-left.png`

The FCStd SHA-256 is
`9d18d60dc7db24c97fd7931fdda24c87bea546309d68eef325f62bae9ad4731e`;
ZIP validation passes at `7,999,704` bytes.

## Accepted anchor and contract

- User-selected subelement: `Face1668`, owned by C001.
- Face centroid: `(95.14, 205.01, 188.54) mm`.
- Face normal: `(-0.72, -0.24, -0.65)`; area: `24.00 mm2`.
- Nominal projection face: `12 x 2 mm`.
- Cutter profile: `12.4 x 2.4 mm`, providing `0.2 mm` clearance per side.
- Opposing-face separation: `7.0 mm`.
- Inward removal: `5.2 mm`, with `0.1 mm` outside overcut.
- Preserved exterior wall: `1.8 mm`.
- Changed owner: a separate copy of C001 only.
- Frozen: B tabs and anchor, A work, translucent panel, ear, left side,
  lower/rear, reinforcement, eyes, C006, and aluminum V0.5-M2.

## Validation

- Complete proposal: valid, closed, no self-intersection, `42` solids and
  `42` shells.
- Complete volume: `150534.60 mm3` versus `150643.54 mm3` before.
- C001 volume: `75860.78 mm3` versus `75969.39 mm3` before.
- Full bounding box is unchanged:
  `X -30.00..126.94`, `Y 42.84..269.34`, `Z 109.76..268.15 mm`.
- Approved B head-root overlap after removal: `124.93 mm3`.
- Approved relieved B panel-tab clearance: `0.445 mm`, no interference.
- Translucent-panel clearance: `0.0353 mm`, no interference.
- Ear remains at its inherited accepted touching owner seams.

## Rejected or held variants

- No direct edit of the accepted V3 upper-head source.
- No through-cut of the exterior wall.
- No change to the approved B tab shapes or anchor.
- No left-side mirror, production union, aluminum edit, STL, G-code, or print
  release.
- Preliminary exterior views that did not expose the internal change were
  moved to `_diagnostic/`; use the internal left before/after images for
  shape review.

## Exact regeneration sequence

Use only the official FreeCAD GUI and allowlisted operations:

1. Open the approved right-B review and save an isolated copy.
2. Create a datum from
   `PROPOSED__RIGHT_UPPER_HEAD__VALIDATION_COMPOUND_V3.Face1668`.
3. Create the `12.4 x 2.4 x 5.3 mm` box at
   `(91.5063813236, 209.7144845913, 190.6741602665) mm` using the local frame
   and rotations recorded in the JSON contract.
4. Insert a separate C001 shape copy and subtract only that box.
5. Compound the modified C001 with unchanged C002 through C042.
6. Re-run geometry, solid, self-intersection, volume, bounding-box, B-root,
   B-clearance, panel-clearance, and ear-context checks.
7. Save checkpoint `legacy_small_flange_removal_review_v1_validated`.

## Approval and next review

The local removal review is complete. The next controlled review is the
existing right-A short heat-set-insert and 25-degree tool-access contract:
`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`.
The approved removal remains held from integration until the right-side
connector package receives explicit integration approval.
