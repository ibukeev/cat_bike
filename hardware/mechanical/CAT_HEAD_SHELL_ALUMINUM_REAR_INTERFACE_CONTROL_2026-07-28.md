# Cat Head Shell / Aluminum Rear Interface Control

**Date:** 2026-07-28
**Status:** Active cross-session coordination hold; no shared-interface CAD
regeneration or metal cutting release
**Integration authority:** User

## 1. Purpose

This document coordinates the separate cat-head shell and aluminum-mount work
sessions. It is the authority for geometry or behavior shared by those two
workstreams. It does not replace either workstream checkpoint:

- Shell defects and required validation:
  `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- Aluminum V0.2 design state:
  `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/V0_RESUME_CHECKPOINT.md`

The current aluminum directory is an untracked active work product. The shell
session must not edit its files. The aluminum session must not edit Gate 3,
Gate 5, or Gate 8 shell sources while their existing partial state is under
review.

## 2. Coordination rule

No session may independently change or release a shared-interface parameter.
A proposed change must be recorded here with its affected shell and metal
files, reviewed in both workstreams, and approved by the user before either
session regenerates shared geometry or releases material for fabrication.

This coordination freeze is not a fabrication approval. It preserves a common
reference while the physical-feedback pass remains open.

## 3. Workstream ownership

| Area | Primary workstream | Coordination requirement |
|---|---|---|
| Bike boss plate, side webs, compact adapter, metal tether | Aluminum mount | May not move the head rear plane without shared approval. |
| Aluminum head backplate and lower rail shoes | Aluminum mount | Backplate perimeter, rail-shoe, pass-through, and service details are shared and remain open. |
| Exterior head shape, shell partitioning, reinforcement, mirror-panel seats | Printed shell | Must preserve the coordinated rear plane and rail system unless a shared change is approved. |
| Upper/front printed rail sockets and M4 retention paths | Shared | Must be generated from the same rail-axis and socket-roll revision as the aluminum backplate and rails. |
| Rear ASA frame, rear shell facets, removable rear cassette | Printed shell | Proposed architecture only; attachment and load transfer are shared. |
| Backplate perimeter fasteners, rail pass-throughs, wiring, drainage, tool access | Shared | Neither session may finalize independently. |
| Final assembly and service sequence | Shared | Must be validated with complete shell, aluminum, rail, fastener, and tool envelopes. |

## 4. Provisional shared baseline

The following values are the current V0.2 coordination baseline. They are
frozen against unilateral changes but remain review-only and are not released
for cutting:

**Active aluminum integration review artifact:**
`hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/review-model/frame-fixed-mount-v02-review.blend`

The user is currently reviewing this BLEND and confirmed that the aluminum
work remains review-only. No physical backplate has been ordered or cut. The
parallel aluminum work began under the assumption that the printed ASA rear
structure would not be redesigned; that assumption is now explicitly open
because physical findings F-04 and F-29 require a rear-interface and
printability correction.

The user accepts the overall V0.2 aluminum architecture as the direction to
retain. This is concept acceptance, not a cutting release. The current printed
ASA rear base conflicts with that metal envelope and must be revised. Possible
movement of the lower rail targets toward center remains TBD.

| Interface parameter | Provisional baseline |
|---|---|
| Mount architecture | Frame-fixed, no weld, and no printed polymer in the primary bike-connector load path. |
| Head coordinate bounds | X `-151.915..151.915`, Y `0..269.345`, Z `0..330` mm. |
| Rear interface plane center | Head coordinates `[0, 264.01125, 171.74025]` mm. |
| Rear interface outward normal | `[0, 0.990996, 0.133894]`. |
| Rear-plane mating pitch | `-18.894665°` relative to the estimated boss plane. |
| Aluminum head backplate | 3 mm 6061 trapezoid; 60 mm top, 120 mm bottom, 79.663819 mm high. |
| Adapter-to-backplate pattern | Four 6.6 mm paths at X `±22` mm and local V `±20` mm. |
| Internal rail stock | Nominal 19.05 mm square aluminum tube. |
| Lower rail targets | Head coordinates `[-40, 267.336, 147.132]` and `[40, 267.336, 147.132]` mm. |
| Rail orientation | Pitch `17.662°`, yaw `5.595°`; upper M4 axes approximately `5.333°` from head-horizontal. |
| Upper retention | One transverse M4 bolt per blind printed upper socket. |

Any need to change one of these values must be raised here before either model
is edited.

### 4A. Lower rail-target inward-shift assessment

At the current lower target, local backplate V is approximately `-24.832` mm
and the trapezoid half-width is approximately `54.351` mm. With a 19.05 mm
tube centered at X `±40`, the nominal tube/pass-through envelope leaves about
`4.826` mm to the sloped plate edge. The nearest lower 6.6 mm adapter-hole
center is about `18.637` mm away.

Moving a rail center to X `±35` improves nominal edge clearance to about
`9.826` mm, but reduces center distance to the lower adapter hole to about
`13.869` mm. The raw tube half-width plus M6-hole radius already consume about
`12.825` mm of that distance, leaving only about `1.044` mm before accounting
for the rail shoe, bolt head, washer, nut, manufacturing tolerance, or tool
access.

Therefore a simple inward shift is not approved. The user accepted X `±40` as
the baseline for the first coordinated ASA rear-structure revision. If rail
movement is still needed after full collision review, optimize rail X/V
position, adapter holes, backplate outline, lower-shoe envelope, and upper
socket axes as one shared interface change.

## 5. Explicitly open shared interfaces

The following items are not defined and must remain open in both sessions:

1. aluminum-backplate perimeter hole count, positions, and edge distances;
2. lower rail-shoe geometry, solid plugs, anti-crush load path, and fasteners;
3. rail pass-through geometry through the printed rear structure;
4. rear ASA structure to aluminum-backplate attachment;
5. rear cassette seam location, overlap, alignment, sealing, and removal path;
6. cassette fastener, washer, nut, hand, and tool envelopes;
7. drainage and wiring routes through the rear assembly;
8. separation of structural load paths from cosmetic rear shell facets;
9. complete installation and removal sequence;
10. actual headlight housing, beam, steering, and cable clearance; and
11. physical fit, drilling, and retention of the actual 19.05 mm rails in the
    revised upper/front printed sockets.

Existing review-only DXF, SVG, STL, BLEND, GLB, and validation outputs do not
close these items.

## 6. Rear cassette proposal C-001

**Status:** Proposed for coordinated evaluation; not accepted and not modeled.

To correct physical-fit findings F-04 and F-29 without shrinking the complete
head, evaluate a removable rear cassette that:

- moves the lower-face shell seams forward and transfers the aft shell facets
  to a rear-loaded printed module;
- incorporates or attaches to the shallow printed rear frame around the
  aluminum backplate;
- preserves the current rear plane, adapter hole pattern, and rail targets if
  practical;
- installs and removes from behind after the front and side shells are joined;
- makes each lower-face STL comfortably printable with its required brim and
  supports;
- leaves the aluminum backplate and rail structure as the primary mount load
  path; and
- treats the exterior rear facets as replaceable shell/finish parts rather
  than primary bike-mount structure.

The preferred implementation is not a permanent fusion of cosmetic ASA to the
aluminum plate. It is a mechanically attached printed rear module that may be
removed with, or separately from, the aluminum backplate according to the
approved service sequence.

## 7. Required comparison before accepting C-001

After the user closes the feedback pass, compare at least these three variants
without releasing fabrication:

| Variant | Required evidence |
|---|---|
| Existing lower-face partition and difficult rotation | Saved PrusaSlicer orientation, brim/support footprint, support volume, print time, and surface-risk review. |
| Uniform head scale reduction | Smallest scale that creates an acceptable orientation, plus impact on every mount, fastener, eye, insert, panel, and rear-plane interface. |
| Rear cassette / moved seam | Lower-face and cassette bed margins, support volumes, complete assembly collision test, backplate/rail integration, and service sequence. |

Acceptance of a variant requires the user to review the exterior appearance,
assembly sequence, printer evidence, and aluminum-interface impact together.

## 8. Shared release gates

No rear-interface metal or replacement structural shell is released until:

1. the user declares the physical-feedback pass complete;
2. both workstreams use the same rear-plane and rail-target revision;
3. the full shell and aluminum assembly has zero collision through insertion,
   seated, fastened, and removal states;
4. the rear cassette or retained partition passes the complete build-plate test
   in A-37;
5. all backplate, shoe, cassette, washer, nut, and tool envelopes are validated;
6. a physical rear-interface and rail-shoe coupon passes;
7. actual headlight and steering clearance is validated;
8. an independent metal safety tether is specified; and
9. the stationary proof-load, vibration, and progressive ride-test plan is
   approved.

## 9. Cross-session change log

| ID | Date | Proposal or change | Status | Affected workstreams |
|---|---|---|---|---|
| C-001 | 2026-07-28 | Evaluate rear-loaded cassette incorporating aft shell facets to improve lower-face printability and rear service. | Proposed; no CAD action | Shell and aluminum |
| C-002 | 2026-07-28 | Use `frame-fixed-mount-v02-review.blend` as the active aluminum integration-review artifact. | User review in progress; no fabrication approval inferred | Shell and aluminum |
| C-005 | 2026-07-28 | Record aluminum fabrication commitment state: no plates ordered; only rectangular aluminum rail stock purchased. | Confirmed by user; rail dimensions still require physical verification | Shell and aluminum |
| C-003 | 2026-07-28 | Preserve the V0.2 aluminum rear-plane pose, plate outline, adapter pattern, and rail targets where practical while redesigning the printed ASA rear structure around that baseline. | Preferred coordination target; integrated validation required | Shell and aluminum |
| C-004 | 2026-07-28 | Rebuild the upper/front printed sockets to the coordinated V0.2 compound rail axes and socket roll; do not reuse pre-correction upper-shell G-code. | Required shared correction; regeneration held until feedback closes | Shell and aluminum |
| C-006 | 2026-07-28 | Retain the overall V0.2 aluminum architecture and redesign the conflicting printed ASA rear base/shell around its complete envelope. | Concept accepted by user; interface details and fabrication remain open | Shell and aluminum |
| C-007 | 2026-07-28 | Keep lower rail targets at X `±40` for the first ASA rear redesign; evaluate inward movement only if the complete collision review still requires it, including adapter-hole, backplate-edge, shoe/tool, upper-socket, and shell impacts. | Accepted baseline; conditional study deferred | Shell and aluminum |

## 10. Next synchronization action

The aluminum session is currently model-review only; no physical backplate is
ordered or cut. It must continue to report any transition to quoted, ordered,
cut, bent, drilled, or received before that transition occurs. In particular,
the 3 mm head backplate, its trapezoid perimeter, the four adapter holes, and
the rear-plane pose remain review geometry. The shell session must compare its
rear partition against that exact baseline before proposing any change to it.

Purchased-stock record: the user confirmed that only rectangular aluminum rail
stock has been purchased. Its actual outside dimensions, wall thickness,
alloy/temper if known, and available length remain to be physically verified.
No plate or plate hole pattern is physically committed.

Once both states are recorded, the user can either freeze the current V0.2
interface for the rear-cassette study or authorize a coordinated interface
revision.
