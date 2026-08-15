# Right Upper Approved C027/C012 Context Review V25 Checkpoint

Date: 2026-08-15

Status: **COMPLETE RIGHT-UPPER REVIEW CONTEXT — RESIDUAL LEGACY COLLISIONS REMAIN — NOT A PRINT SOURCE**

## Purpose

Substitute the approved V19 C027 and V24 upper-C012 components into the full frozen V3 right-upper set. This checkpoint proves those two accepted changes coexist in their real context without silently retaining the old C012 or C027.

## Current review files

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-approved-c027-c012-context-review-v25/CAT_HEAD_RIGHT_UPPER_APPROVED_C027_C012_CONTEXT_REVIEW_V25.FCStd`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-approved-c027-c012-context-review-v25/validation-v25.json`
- Structured replay: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-approved-c027-c012-context-review-v25/operation-recipe-v25.json`

## Exact manifest

- Forty-two right-upper solids are present: V3 C001-C042, except original C012 and original C027 are omitted.
- The approved V19 C027 and V24 C012 replacements occupy those two slots.
- The exact V17 right-eye owner is present only as the collision/clearance reference.
- The review compound is deliberately not fused; this is not HS-18 production topology.

## Validation

| Gate | Result |
|---|---|
| Manifest | PASS — 42 deliberate upper solids; no old C012/C027 coexistence |
| Review geometry | PASS — valid closed 42-solid compound |
| Compound topology | PASS — 2750 faces, 4304 edges, 1590 vertices |
| Compound volume | PASS — `150445.14 mm3` |
| Approved C012 / eye | PASS — no intersection; `4.0000 mm` clearance |
| Approved C027 / eye | PASS — no intersection; `5.3208 mm` clearance |
| Complete upper / eye | HOLD — `128.3273 mm3` aggregate legacy interference remains |
| C001 / eye | HOLD — exact `100.5990 mm3` interference |
| FCStd integrity | PASS — valid ZIP; `2587308` bytes |

The remaining interference bounds are X `[55.12, 103.74]`, Y `[70.78, 96.88]`, Z `[118.48, 178.66]` mm. C012 and C027 do not contribute. Prior V21 evidence assigns the remaining legacy set to C001, C009, and a degenerate near-zero C019 touch.

## Accepted and held decisions

- Preserve the user-approved V19 C027 and V24 C012 exactly.
- Resolve C001 next under its separately approved V22 anchor evidence and a numeric clearance contract.
- Hold C009: the audited `13.98 mm` trim would remove about `96.85%` of the component and is not structurally acceptable without a replacement/ownership decision.
- Treat C019 as a diagnostic topology touch unless exact revalidation proves positive volume.
- Preserve C006, ears, lower face, rear cassette, reinforcement ownership, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.
- No mirror, production union, STL, G-code, slicing, or structural ASA release is authorized.

## Exact regeneration

Replay `operation-recipe-v25.json` through the structured FreeCAD GUI tools. No arbitrary Python, macro, CAM, or headless FreeCAD operation was used.

## Next physical review

No new visual decision is required for C012 or C027; they were already approved and remain clear. The next user-visible review should be an isolated C001 correction shown together with the exact V17 eye and its retained owner connection. Do not ask the user to select FreeCAD face numbers again; use the approved V22 evidence and own the BREP mapping.
