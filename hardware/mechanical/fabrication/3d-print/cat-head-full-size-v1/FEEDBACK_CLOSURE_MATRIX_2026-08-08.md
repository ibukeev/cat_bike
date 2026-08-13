# Cat-Head Physical-Feedback Closure Matrix — 2026-08-08

This is the working traceability ledger for
`CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`. It does not
replace that source-of-truth feedback or authorize printing.

**Release state: HOLD.** There is no unified production CAD source or approved
ASA STL set. “Accepted review” means the user accepted an isolated direction
or appearance; it does not mean integrated, mirrored, sliced, or physically
proven.

## Status legend

- **Accepted review:** isolated direction was visually accepted.
- **Digital pass:** stated numerical geometry checks passed.
- **Production hold:** accepted geometry is not one integrated printable body.
- **Physical hold:** coupon, hardware, hand-fit, or bike test remains.
- **Open:** no accepted corrective geometry exists yet.

## Current production-artifact audit

`prusa-slicer --info` was rerun on the current Gate 8 exports on 2026-08-08.
All six files report manifold, but none is one printable body:

| Current Gate 8 artifact | Reported parts | Result |
|---|---:|---|
| `left_lower_face.stl` | 61 | FAIL F-26/A-34 |
| `right_lower_face.stl` | 61 | FAIL F-26/A-34 |
| `left_upper_head.stl` | 41 | FAIL F-26/A-34 |
| `right_upper_head.stl` | 42 | FAIL F-26/A-34 |
| `left_eye_bucket.stl` | 6 | FAIL F-23/A-28 |
| `right_eye_bucket.stl` | 6 | FAIL F-23/A-28 |

The old lower-face orientation search leaves only `7.798/6.216 mm` total
clearance on the right limiting axes and `7.798/6.471 mm` on the left. The
required reserve is `20 mm` total for `10 mm` per side, before brim/support.

## Feedback-item closure

| ID | Current evidence | Honest status | Next release action |
|---|---|---|---|
| F-01 | V0.5-M2 shared rail/socket route is frozen. | Digital direction preserved; production hold. | Rebuild final shell sockets and run full insertion. |
| F-02 | Frozen targets/axes/roll are in the shell/aluminum interface control; the only existing coupon is obsolete (`20.50 mm` fixed socket versus current `21.00 mm` serviceable socket). | Digital interface lock; physical hold. | Measure the actual rail, approve, then print a V0.5-M2 socket/cap coupon. |
| F-03 | No measured final lamp/cable/beam/steering envelope exists. | Open. | Capture the 3D envelope and run the complete sweep. |
| F-04 | Lossless rear-cassette V5 ownership was visually accepted. | Accepted review; production/aluminum hold. | Build one cassette around V0.5-M2 and validate insertion/removal. |
| F-05 | M2 moved lower shell centers inward and passed digital edge/tool checks. | Digital pass; physical hold. | Verify real hardware, fingers, and tool on the coupon. |
| F-06 | Legacy Gate 8 pads are invalid for the repartitioned cassette. | Open production design. | Integrate cassette-owned M5 pads around real envelopes. |
| F-07 | Ear-root insertion-fit V3 includes 13 mm corner relief. | Accepted review/digital pass; physical hold. | Print the fit coupon. |
| F-08 | V3 lower-center relief and 41-sample path per side clear digitally. | Accepted review/digital pass; physical hold. | Include the lower center in the fit/service test. |
| F-09 | V3 has 2.5 mm deep-body and 1.0 mm cap clearance. | Accepted review/digital pass; physical hold. | Confirm real ASA tolerance by hand fit. |
| F-10 | V10/A-B uses seated datums and separated retention points. Right and mirrored-left owner integrations, including repaired C001/C003, passed bilateral digital validation and visual review by 2026-08-10. | Bilateral integrated review accepted; production and physical holds remain. | Preserve the accepted owners; freeze exact print orientation and qualify the insert joint physically before print release. |
| F-11 | Two widely separated sets replace the continuous connector. | Accepted layout; production hold. | Finish right A/B; mirror only after approval. |
| F-12 | Broad roots and both 25-degree tool paths pass. A V4 and B V2 surface-open cavities are approved and remain valid after right-side owner union. | Integrated digital pass; physical coupon and production hold. | Freeze the upper-head print orientation, then print the exact-orientation ASA insert coupon and test installation, torque, and pull-out. |
| F-13 | Widely separated A/B points target outer-root flapping. | Accepted layout; production/physical hold. | Integrate one side and perform anti-flap hand test. |
| F-14 | Outer grounding uses the under-ear owner pair, not an exterior stick. | Accepted layout; production/physical hold. | Same one-side integration and test as F-13. |
| F-15 | Old central back-skirt is uncorrected against final reinforcement. | Open. | Select exact collision faces for a one-panel proposal. |
| F-16 | Old two-top-flange central-panel layout is uncorrected. | Open. | Select the lower vertical nose owner for a third broad point. |
| F-17 | Front nose skirt/connector has no accepted corrected review. | Open. | Identify the exact part and collision faces. |
| F-18 | Side-panel side/STL and collision faces are not confirmed. | Open. | Identify the side and two owner regions. |
| F-19 | V9 preserves the valid V8 right bucket/cap and adds exact valid left mirrors; both owner pairs have zero interference. Final reinforcement/skirts are not yet in the same integrated review. | Bilateral eye-owner digital pass; final integration hold. | Visually approve V9, then test insertion/removal against final reinforcement and skirts during HS-11. |
| F-20 | The accepted connector owners are present in both single-solid bucket/cap pairs; bilateral topology and owner-to-owner clearance pass. Head-owner flange integration and final tool access remain HS-11. | Bilateral eye-owner digital pass; head-owner/access hold. | Approve V9, then union all eight eye/head flanges in HS-11. |
| F-21 | The accepted lower and relocated upper M2.5 connector features are present on both exact-mirrored sides; each side has exactly one bucket and one cap solid. | Bilateral digital pass; visual approval hold. | Visually approve V9, then promote the validated left owners. |
| F-22 | The original broad right-side pair has exactly two M3 paths. Ear flush-cut V2 removes 656.3880 mm3 including the 33.38 mm3 V1 root residue. Recovery V1 was then rejected because stale upper-head context resurrected a separate four-aperture lattice. Clean-owner recovery V2 removes only that additional 8.09 mm3; both owners remain valid closed solids, bounds are unchanged, and original pair engagement remains 524.2914/511.0390 mm3 on head/ear. | Clean-owner recovery V2 digitally valid; visual approval and owner integration open. | Approve clean-owner V2; integrate/review the exact two-bolt pair in copied right owners before any mirror. |
| F-23 | Both V9 buckets are valid closed one-solid owners (`630` faces, `6649.60 mm3` each); exact mirrored bounds and left STEP round-trip pass. | Bilateral digital pass; visual/promotion hold. | Visually approve V9 and promote the validated left owner. |
| F-24 | C002 remains rejected; broad-base V3 was accepted. | Accepted review; production/insertion hold. | Integrate one right pair without restoring C002. |
| F-25 | Clean references exist; final reinforcement is not clipped/unioned. | Partial; production hold. | Add exterior-deviation gate during unified integration. |
| F-26 | Shells report 61/61/41/42 slicer parts. | FAIL; hard Gate 3–8 validator added. | Replace append/join export with approved true owner unions. |
| F-27 | Requested rail/tie direction was accepted as “much better.” | Accepted review; seam integration open. | Assign complementary seam ownership and collision-test pairs. |
| F-28 | User-approved V6 full-thickness wall continuations are preserved in both V9 buckets; both are one valid solid and detached strips are absent. Full-head bilateral context was generated. | Bilateral digital pass; visual approval hold. | Visually approve the V9 full-head context, then preserve these exact owners through HS-11. |
| F-29 | V5 seam accepted; current lower parts fail 10 mm margin. | Accepted direction; hard margin gate added. | Complete bodies, slice with brim/support, verify 10 mm margins. |

## Acceptance-test grouping

| Acceptance tests | State |
|---|---|
| A-01–A-06 | Rear/rail direction exists; insertion, hardware, lamp, and steering remain open. |
| A-07–A-12 | V3 fit and A/B retention are advanced; physical fit/access/anti-flap remain. |
| A-13–A-22 | Central/front/side glow-panel corrections remain open. |
| A-23–A-26 | Eye flange layout accepted; eye insertion and cap distribution open. |
| A-27 | Primary ear round-hole/slot interface remains open. |
| A-28–A-32 | Current eye exports fail topology; geometry/physical tests remain. |
| A-33–A-36 | Clean references exist; unified shell/collision validation remains. |
| A-37 | Strict 10 mm pre-brim/support margin gate encoded; lower faces fail. |
| A-38 | V0.5-M2 digital lock preserved; actual tube/socket coupon remains. |
| A-39 | Complete aluminum/cassette insertion, tools, and removal remain open. |

## Next controlled sequence

1. Visually review bilateral V9: exact left/right exterior/aperture,
   continuous bucket walls, removable post-free caps, and the retained lower
   plus relocated upper M2.5 connector pair on both sides.
2. After explicit V9 approval, promote the validated left STEP owners without
   changing the approved right V8 sources.
3. Complete HS-11 by integrating all eight already-approved eye/head flange
   roots and verifying the final tool paths; do not restore C002.
4. Hold central/front/side panels until exact parts and collision faces are
   identified.
5. Do not export production STL or start structural ASA printing until the
   unified bodies pass the listed acceptance gates.
