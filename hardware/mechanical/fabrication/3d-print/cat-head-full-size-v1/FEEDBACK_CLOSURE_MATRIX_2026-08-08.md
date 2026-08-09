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
| F-10 | V10/A-B uses seated datums and separated retention points; right-B relief and selected legacy-projection removal are visually approved. | Layout accepted; right A/B hardware and production hold. | Review A hardware, drill B, then integrate right side only after approval. |
| F-11 | Two widely separated sets replace the continuous connector. | Accepted layout; production hold. | Finish right A/B; mirror only after approval. |
| F-12 | Broad roots are accepted; right A has a short-insert proposal. | Partial digital pass; hardware/physical hold. | Approve hardware and test access/pull-out coupon. |
| F-13 | Widely separated A/B points target outer-root flapping. | Accepted layout; production/physical hold. | Integrate one side and perform anti-flap hand test. |
| F-14 | Outer grounding uses the under-ear owner pair, not an exterior stick. | Accepted layout; production/physical hold. | Same one-side integration and test as F-13. |
| F-15 | Old central back-skirt is uncorrected against final reinforcement. | Open. | Select exact collision faces for a one-panel proposal. |
| F-16 | Old two-top-flange central-panel layout is uncorrected. | Open. | Select the lower vertical nose owner for a third broad point. |
| F-17 | Front nose skirt/connector has no accepted corrected review. | Open. | Identify the exact part and collision faces. |
| F-18 | Side-panel side/STL and collision faces are not confirmed. | Open. | Identify the side and two owner regions. |
| F-19 | Eye insertion against final reinforcement/skirts has not passed. | Open integration test. | Rebuild right eye as one body, then test in full context. |
| F-20 | Eye broad-base V3 separated pairs were accepted. | Accepted review; production/access hold. | Union one right eye pair into owners and validate access. |
| F-21 | One rear-cap connector has not moved from lower to upper. | Open. | Select cap/bucket faces and review one-side relocation. |
| F-22 | Pin-to-pin ear interface lacks an accepted hole/slot rebuild. | Open. | Select flange pair; review 3.4 mm hole plus 3.4 x 5 mm slot. |
| F-23 | Current eye buckets still contain six slicer parts. | Open geometry; hard validator active. | True-union right bezel/chamber/features; require one part. |
| F-24 | C002 remains rejected; broad-base V3 was accepted. | Accepted review; production/insertion hold. | Integrate one right pair without restoring C002. |
| F-25 | Clean references exist; final reinforcement is not clipped/unioned. | Partial; production hold. | Add exterior-deviation gate during unified integration. |
| F-26 | Shells report 61/61/41/42 slicer parts. | FAIL; hard Gate 3–8 validator added. | Replace append/join export with approved true owner unions. |
| F-27 | Requested rail/tie direction was accepted as “much better.” | Accepted review; seam integration open. | Assign complementary seam ownership and collision-test pairs. |
| F-28 | Eye bezel/chamber remains weak and disconnected. | Open geometry; hard validator active. | Add broad right-eye shoulder and prove one-body topology. |
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

1. Review the right-A short-insert contract; right-B relief and the selected
   legacy-projection removal are visually approved.
2. After approval, drill B, integrate only approved right A/B, and rerun topology, clearance,
   access, exterior, and insertion checks.
3. Build the right eye as the next one-body proposal only after selecting its
   bezel/chamber owner faces and numeric shoulder contract.
4. Hold central/front/side panels until exact parts and collision faces are
   identified.
5. Do not export production STL or start structural ASA printing until the
   unified bodies pass the listed acceptance gates.
