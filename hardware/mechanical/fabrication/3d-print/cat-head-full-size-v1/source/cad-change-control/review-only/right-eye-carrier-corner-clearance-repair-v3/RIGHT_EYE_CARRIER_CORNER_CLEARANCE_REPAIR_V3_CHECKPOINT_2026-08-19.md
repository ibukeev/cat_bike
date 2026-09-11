# Right Eye Carrier Corner-Clearance Repair V3 Checkpoint — 2026-08-19

## Status

`REVIEW_ONLY_READY__AWAITING_CORNER_CLEARANCE_LGTM`

This is review evidence only. It is not a print source and no STL, 3MF, G-code,
mirror, production candidate, or canonical geometry was created or replaced.

## User-reported defect and disposition

The V2 full-depth outer seam visibly conflicted with the lower shell corner. V2
is withdrawn. An independent exact contact measurement confirmed that this was
not merely a display artifact:

- exact shell owner: `FROZEN_RIGHT_LOWER_MAIN_V34`
- V2 new-material distance: `0.0 mm`
- positive common volume: `0.0 mm3`
- contact section: `14 edges / 10 vertices`
- section AABB minimum: `[33.616827841961644, 50.10706152387267, 125.15017980822562] mm`
- section AABB maximum: `[34.97628050201239, 52.03217039868513, 126.15882478700713] mm`

Attribution showed that only the V2 outer spine contacted the shell. The V2
structural backing remained `0.5628441175178516 mm` clear, and the unchanged
source carrier remained `0.35665372063694045 mm` clear.

## V3 correction

V3 preserves the source carrier, user manual flange, and exact V2 structural
backing. It changes only the V2 outer spine by subtracting the measured contact
AABB expanded `1.50 mm` on all sides.

Two smaller tooling preflights were rejected before review output:

- `0.75 mm` padding -> `0.2501749889 mm` clearance: FAIL
- `1.10 mm` padding -> `0.3867824984 mm` clearance: FAIL
- `1.50 mm` padding -> `0.5628441175178516 mm` clearance: PASS

## Passing evidence

- new-material clearance to the corner owner: `0.5628441175178516 mm`
- minimum new-material clearance to every shell owner: `0.5628441175178516 mm`
- shell contact-section edges/vertices: `0 / 0`
- positive shell overlap: `0.0 mm3`
- source carrier removed: `0.0 mm3`
- V2 structural backing missing: `0.0 mm3`
- V2 outer-spine material removed by the notch: `12.209215069951282 mm3`
- global full-depth span retained: `4.200000017484356 mm`
- final carrier: valid, closed, one solid, deep-OCCT clean
- final mesh audit: one component; zero boundary, nonmanifold, degenerate,
  duplicate, and self-intersecting facets; outward normals
- lens, rear plate, screws, LEDs, and wire intersections from added material:
  all `0.0 mm3`

Positive structural roots remain:

- backing-to-transition: `27.027802073044768 mm3`
- backing-to-walls: `319.96119527609505 mm3`
- spine-to-backing: `180.60258687447262 mm3`
- spine-to-bezel: `58.95666393814595 mm3`
- spine-to-front-filler: `103.71263446972283 mm3`
- spine-to-lens-surround: `132.46014817716522 mm3`
- spine-to-opening-connector: `125.4632670382928 mm3`

## Pinned files

- contract SHA-256: `ce445a115941fd4ecb39633515a1eb5b126c7cadbd29a3ad3ca8c007e177b315`
- generator SHA-256: `a0a5e8c8ee55f889673ee7d412c37cd578fe28c52bbacdab572a9dce7bd35a29`
- contact-measurement script SHA-256: `1a19bda51ab4197ed4d1529c9885ae71cdf5f94c52576f47696b98733e04c5c8`
- feasibility report SHA-256: `f2fda661a0371820b8970e386f7b26ca3f213444218246e1bb07289cd67a2e70`
- review FCStd SHA-256: `22dca83ac335ad9277ec89bd248f65c3646af4c6d5945b1e28367dfcee7ba94f`
- validation SHA-256: `52170ecd6b2b0e8d3d299cb254eb997956c229c2462db645b24d44eb5d88108f`

## Review pack

Directory:

`output/70-freecad-pilots/review-only/right-eye-carrier-corner-clearance-repair-v3/`

Primary model:

`RIGHT_EYE_CARRIER_CORNER_CLEARANCE_REPAIR_REVIEW_ONLY_V3.FCStd`

Fixed views:

- `assembled-context.png`
- `corner-shell-clearance-closeup.png`
- `repair-only-corner-closeup.png`
- `left-seam.png`
- `right-seam.png`

All five fixed views were inspected. In the exact before/after corner view, the
withdrawn V2 repair touches the gray shell while V3 has a visible gap. The seam
views show a continuous replacement chain. The cyan box in the repair-only view
is a review reference for the clearance cut; it is not printable carrier material.

## Commands used

Feasibility:

```bash
timeout 300s env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python -B hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/review-only/right-eye-carrier-corner-clearance-repair-v3/generate_review.py --mode feasibility --report /tmp/right-eye-carrier-corner-clearance-repair-v3-feasibility.json
```

Review generation:

```bash
timeout 420s env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python -B hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/review-only/right-eye-carrier-corner-clearance-repair-v3/generate_review.py --mode review --feasibility-report /tmp/right-eye-carrier-corner-clearance-repair-v3-feasibility.json --feasibility-sha256 f2fda661a0371820b8970e386f7b26ca3f213444218246e1bb07289cd67a2e70
```

## Next authorized boundary

The user must visually review the exact corner in the V3 FCStd or
`corner-shell-clearance-closeup.png`. A separate explicit approval is required
before producing any print-authoritative model, mirror, STL, 3MF, or G-code.
