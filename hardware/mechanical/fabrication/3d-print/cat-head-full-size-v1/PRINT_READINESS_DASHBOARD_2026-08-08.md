# Cat Head Print-Readiness Dashboard — 2026-08-08

The project is not print-ready. Most feedback directions have isolated review
results, but they have not been unified into one production CAD source and
validated as a complete printable assembly.

| Workstream | Current state | Print blocker |
|---|---|---|
| Feedback traceability | F-01 through F-29 mapped in `FEEDBACK_CLOSURE_MATRIX_2026-08-08.md` | Open geometry and physical gates are explicit; none may be silently skipped |
| Lower-face/rear-cassette repartition | User-reviewed direction accepted | Integrate with final owners and aluminum V0.5-M2 |
| Reinforcement | Requested additions accepted as much better | Union, clip to interior, and collision-test every seam |
| Eye mounting | Four broad-root flange layout per side accepted in review | Make eye bucket one printable body and pass insertion/access |
| Right panel, upper head, and ear topology | Right-side FreeCAD references approved | References are not production unions or shell exports |
| Right A connector | Approved hole preserved; isolated 25 degree ball-end plus M3 x 3 short-insert proposal passes geometry gates | Needs user hardware approval, ASA insert coupon, and production integration |
| Right B connector | Isolated 1.9 mm local-relief and selected legacy small upper-head projection removal are visually approved | Needs B hole, hardware, and access review, then controlled right-side integration |
| Left connectors | Not mirrored from controlled right-side solution | Mirror after right A/B approval and rerun bilateral checks |
| Rear aluminum interface | V0.5-M2 preserved and unchanged | Final ASA rear structure must consume complete metal envelopes |
| Complete head | No unified production source or full-head validation | Connected-body, exterior, seam, motion, hardware, and service checks |
| Production topology | Gate 3–8 hard-fail disconnected bodies | Current shells are 61/61/41/42 parts and eye buckets are 6/6; true owner unions required |
| Slicer/ASA release | No production release; strict nominal 10 mm XY reserve encoded | Current lower faces fail before brim/support; documented final slice required |
| Physical coupon | Existing Gate 8 socket coupon is one-body/manifold but obsolete | Replace its 20.50 mm fixed socket with an approved V0.5-M2 21.00 mm serviceable-socket coupon after measuring the rail |

## Shortest print-critical order

1. Approve the isolated right A short-insert hardware contract and validate an ASA insert coupon.
2. Drill and validate right B; its relief and the selected legacy-projection removal are approved.
3. Integrate only approved right-side A/B owner geometry and require one
   connected body.
4. Validate right-side topology, exterior, access, clearance, and insertion.
5. Mirror A/B only after explicit approval, then rerun bilateral checks.
6. Integrate accepted lower/rear, reinforcement, eye, and ear/panel changes
   into one production source while preserving aluminum V0.5-M2.
7. Run complete-head collision, insertion, exterior, connected-component, and
   service validation.
8. Export production STLs, slice documented orientations, and review the
   complete 3D head plus slicer previews before ASA printing.

Do not start the structural ASA head print from the current review outputs.
