# Right Upper C001 Preserved Rail Root Review V27 Checkpoint

Status: **one-side review candidate only; not approved for mirroring, production integration, STL export, slicing, G-code, or ASA printing**.

## Current review file

- FreeCAD review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-preserved-rail-root-review-v27/CAT_HEAD_RIGHT_UPPER_C001_PRESERVED_RAIL_ROOT_REVIEW_V27.FCStd`
- Candidate object: `REVIEW_ONLY__C001__PRESERVED_RAIL_PLANK_ROOT__V27`
- Frozen eye: `FROZEN__EXACT_RIGHT_EYE__V17__V27`
- Frozen upper-head context excluding C001: `FROZEN__RIGHT_UPPER_CONTEXT_EXCL_C001__V27`

## Frozen inputs and accepted decisions

- Exact V17 right eye remains unchanged.
- Right upper exterior remains unchanged.
- C006, ears, lower/rear ownership, and aluminum V0.5-M2 remain unchanged.
- User-approved V22 C001 review anchors remain `Face382`, `Face324`, `Face536`, and `Face554`.
- The exact eye-opening/mating boundary is intentionally allowed to remain at zero gap; the `4.0 mm` clearance rule applies to internal reinforcement material, not the intended opening boundary.
- The real `174.42 mm^3` tapered reinforcement rail is preserved and moved by the accepted diagnostic offset `(+2.1930, -5.7405, +1.9350) mm`.
- The broad V26 top/side clearance envelope is rejected as production geometry because its exact decomposition contains a main body, a real rail, and five fragments/slivers.
- The rail is reconnected to the main C001 owner with rectangular plank material, not round rods.

## V27 numeric design contract

- Two rectangular root legs use a `4 x 4 mm` section.
- The junction is a `5 x 5 x 5 mm` rectangular block centered at `(65, 65, 184) mm`.
- Rail-side leg follows the reviewed line from approximately `(66.2250, 66.9141, 172.5592)` toward the junction and is extended/translated only enough to create positive rail overlap.
- Main-side leg follows the reviewed line from approximately `(61.0428, 75.4833, 180.5129)` toward the junction and is extended only enough to create positive main-owner overlap.
- Minimum measured internal-plank clearance to the exact V17 eye:
  - rail-side plank: `8.1940 mm`;
  - main-side plank: `4.3376 mm`;
  - junction block: `11.4409 mm`.
- Positive connections before union:
  - rail-side plank to preserved rail: `0.0413 mm^3` overlap;
  - main-side plank to main C001 owner: `27.6829 mm^3` overlap;
  - rail-side plank to junction: `5.8127 mm^3` overlap;
  - main-side plank to junction: `41.5816 mm^3` overlap.

## Exact validation performed

The final review candidate was built by sequential structured FreeCAD fusions: rectangular root, preserved offset rail, then the clean C001 main owner.

- Closed solid: pass.
- OCCT shape validity: pass.
- Self-intersection check: pass.
- Shells: `1`.
- Solids: `1`.
- Faces: `2069`.
- Edges: `3526`.
- Vertices: `1420`.
- Volume: `76143.13 mm^3`.
- Positive-volume interference with exact V17 eye: none.
- Minimum final C001/eye distance reports `0.0000 mm` at the intentional eye-opening/mating boundary; the internal root components separately satisfy the `4.0 mm` clearance contract above.

## Rejected or unsafe variants

- Reject the round-cylinder Y-root prototype even though it was topologically valid; it reads as unexplained sticks and does not match the approved reinforcement-plank language.
- Reject the V26 broad envelope and all five detached/sliver solids.
- Reject both prior cube-root attempts documented in the V26 checkpoint.
- Do not delete the preserved tapered rail.
- Do not mirror, owner-integrate, export STL, slice, generate G-code, or print this V27 review candidate without explicit user approval.

## Resume procedure

No standalone macro or headless regeneration command is authorized. Resume by opening the saved structured FreeCAD review:

```bash
FreeCAD hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-preserved-rail-root-review-v27/CAT_HEAD_RIGHT_UPPER_C001_PRESERVED_RAIL_ROOT_REVIEW_V27.FCStd
```

Use only structured FreeCAD operations. The saved candidate and all frozen context objects are sufficient for review and continuation.

## Next user review

Review the full right upper-head/eye context and the isolated interior root. Confirm only:

1. the original tapered rail remains present;
2. the rail is visibly connected to C001 by rectangular reinforcement planks;
3. no root material protrudes through the exterior;
4. no round stick, horn, loose block, or floating residue is visible;
5. the eye opening and service region remain unobstructed.

After explicit approval, the next controlled operation is one-side owner integration and exact revalidation. Bilateral mirroring remains a later gate.
