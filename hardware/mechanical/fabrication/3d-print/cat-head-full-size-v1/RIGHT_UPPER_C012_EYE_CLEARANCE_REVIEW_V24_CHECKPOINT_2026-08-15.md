# Right Upper C012 Eye-Clearance Review V24 Checkpoint

Date: 2026-08-15

Status: **PROPOSED ONE-SIDE CHANGE — AWAITING VISUAL APPROVAL — NOT A PRINT SOURCE**

## Purpose and authorization

Apply only the user-authorized `5.21 mm` eye-side shortening to the frozen V3 right-upper C012 component. The user approved the V23 upper-C012 anchor and asked Codex to own the exact BREP mapping. C009 remains unchanged and held.

## Current review files

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/CAT_HEAD_RIGHT_UPPER_C012_EYE_CLEARANCE_REVIEW_V24.FCStd`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/validation-v24.json`
- Structured replay: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/operation-recipe-v24.json`
- Evidence: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/review/`

## Frozen baseline and contract

- Source: V23 `FROZEN__UPPER_C012_SOURCE__V23_ref`; moving anchor `Face4`; fixed root `Face18`.
- Shorten `5.21 mm`; retain half-space `n dot p <= 93.624912`, `n=(-0.317684,-0.284581,0.904484)`.
- Exact V17 eye clearance at least `4.0 mm`.
- Preserve C009, visible exterior, C006, ears, lower/rear ownership, rear cassette, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.
- No mirror, production union, STL, G-code, or ASA release.

## Validation

| Gate | Result |
|---|---|
| Eye interference / clearance | PASS — none / `4.0000 mm` |
| Geometry | PASS — valid watertight single solid, no self-intersection |
| Topology / volume | PASS — 22 faces, 41 edges, 21 vertices / `606.54 mm3` |
| C001 engagement | PASS — `150.5311 mm3` |
| C014 / C024 ties | PASS — `0.0099 / 2.1533 mm3` |
| C009 interference / gap | PASS — none / `0.2049 mm` |
| FCStd integrity | PASS — `2258619` bytes |

The exact OCC V3 C008 reference has zero positive overlap and zero gap with both original and trimmed C012. This contradicts the external tessellation audit's `41.554887 mm3`; V24 records the OCC result. C001 remains the substantial root owner.

## Rejected variants

The first cutter placement rotated about the wrong origin and retained the old eye collision; it was deleted before saving V24. C009's audited trim remains held because it would remove about `96.85%` of C009. No automatic repair or facet deletion was used.

## Exact regeneration

Replay `operation-recipe-v24.json` through the allowlisted structured FreeCAD tools in GUI FreeCAD. No arbitrary Python, macro, CAM, or headless FreeCAD was used for the CAD operation.

## Next review

Open V24 and check only: visible eye gap, intact opposite/root attachment, and no missing or displaced surrounding upper-head geometry. After explicit visual approval, substitute V24 into the complete right-upper context and rerun the full eye-collision audit.
