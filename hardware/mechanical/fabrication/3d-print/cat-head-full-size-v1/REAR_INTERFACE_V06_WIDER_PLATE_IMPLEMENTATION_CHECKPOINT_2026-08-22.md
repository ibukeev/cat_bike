# Rear Interface V0.6 Wider-Plate Implementation Checkpoint — 2026-08-22

## Status

`PLAN_APPROVED__IMPLEMENTATION_NOT_STARTED__INTERACTIVE_FREECAD_HANDOFF`

The user approved the coordinated architecture and numeric first proposal in
this checkpoint. Continue interactively in the exact working FreeCAD document
listed below. No rear-interface geometry, mirroring, Boolean integration, STL,
G-code, or fabrication release was created in the planning chat.

The repository V2 recovery rules still require a six-view baseline pack and
explicit visual approval before geometry mutation. After that baseline is
approved, collect and approve structured right-side FreeCAD face/edge anchors
before creating the isolated proposal.

## Active interactive FreeCAD document

Full path:

`/home/bsk/Projects/BM_personal_LED-projects /cat_bike/hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd`

SHA-256 recorded on 2026-08-22:

`f58d0428fe75030820cfea14f29dcca4da13415b9bf10e626285f6fb7dcf4a86`

This hash supersedes the older V1 working-assembly checkpoint hash for this
interactive session. Recompute it before resuming; stop if it differs unless
the user confirms that the newer saved document is intentional.

Relevant editable/working objects already recorded in the document include:

- `RIGHT_LOWER_PRINT_SOURCE_COMPOUND`
- `LEFT_LOWER_PRINT_SOURCE_COMPOUND`
- the user's current right-upper working objects in the same assembly

Frozen context objects must remain unchanged. Do not reconstruct a baseline
by mixing objects from older review documents.

## Protected current print evidence

The active lower-shell physical print iteration remains unchanged until a
later V0.6 review is approved:

| Side | Artifact | SHA-256 |
| --- | --- | --- |
| Right | `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower/right-lower-final-review-voxel-union-025mm.stl` | `7b25103f37bdf5aba3c0a35cf866eab0622a60afaf73b28b82013a266893282f` |
| Left | `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower/left-lower-final-review-voxel-union-025mm.stl` | `572cb4c3c58cca2ca88e596e55b8b1263ad154108526ddecebd9c99dc20064a2` |

These are physical-print SOT artifacts for the current iteration, not
monolithic-solid or complete-head releases.

## Approved physical architecture

1. Preserve the existing visible rear ASA form.
2. The rear ASA piece installs last and remains removable for service.
3. The removable piece is a shear-stiffening cover only; it does not carry the
   aluminum/backplate primary load.
4. Add the structural ASA material to the hidden rear-facing side of the
   permanent upper/lower head shells as broad pads and webs.
5. All service fasteners are accessible from the exterior/rear.
6. Keep the complete rail system fixed. Do not move rail axes, `X +/-40` lower
   targets, sockets, upper M4 stations, angle bases, angle-base holes, compound
   rail datums, or rail lengths.
7. No rear-cover gasket, seal, or drainage geometry is in scope.
8. Reserve a later drillable cable route through the widened aluminum plate;
   the cable hole is not allowed to weaken a structural pad or enter a rail,
   adapter, angle, hardware, or tool envelope.

## Approved V0.6 numeric first proposal

Create a new coordinated interface revision. Preserve V0.5 as immutable
history.

### Aluminum plate

- material: `3.0 mm` 6061-T6 aluminum;
- rear plane center: unchanged from V0.5;
- rear plane outward normal: unchanged from V0.5;
- height: `79.663819 mm`;
- top width: `90.0 mm`;
- bottom width: `160.0 mm`.

The larger plate grows around the frozen rail system. It must not cause any
rail, socket, angle, adapter, or rear insertion datum to move.

### Frozen metal holes and datums

- four adapter M6 paths remain at local `X +/-22`, `V +/-20`;
- right angle-base M5 centers remain `(36,-30)`, `(47.4,-30)`, `(38,-9)`;
- left angle-base centers remain their exact X mirror;
- all rail/socket/crossbolt geometry remains at V0.5-M2.

### Proposed shell-to-plate M5 pattern

Use six mirrored rear-normal M5 paths:

| Pair | Local plate coordinates, mm |
| --- | --- |
| Upper | `(-38,+30)`, `(+38,+30)` |
| Middle | `(-52,0)`, `(+52,0)` |
| Lower | `(-63,-30)`, `(+63,-30)` |

Hardware:

- `5.5 mm` aluminum clearance holes;
- rear-loaded `M5 x 20` bolts;
- `10 mm` OD washers;
- shell-side captive M5 nylocs;
- `14 mm` straight tool envelope.

Analytic first-pass margins that exact CAD must reproduce or improve:

- minimum M5 center-to-plate-edge distance: approximately `9.83 mm`;
- minimum 14 mm tool-to-plate-edge margin: approximately `2.83 mm`;
- minimum shell-tool to neighboring angle-hardware tool gap: approximately
  `2.6 mm`.

Fail closed below any of these gates:

- M5 cut-hole edge ligament: `5.0 mm`;
- tool-to-plate-edge clearance: `2.0 mm`;
- cut-hole-to-cut-hole ligament: `4.0 mm`;
- distinct hardware/tool-envelope clearance: `2.0 mm`.

### Permanent ASA pads and roots

- build the right side only for first review;
- upper and middle pads belong to the permanent right-upper shell owner;
- lower pad belongs to the permanent right-lower/rear shell owner;
- nominal pad: `24 x 36 x 12 mm`, rear-normal;
- current V7 captive-nyloc pocket basis: `8.2 mm` across flats,
  `9.47 mm` across corners, `5.5 mm` deep;
- connect every pad through two broad triangular webs;
- minimum continuous owner-root area: `720 mm2`;
- minimum true volumetric overlap into its owner: `1.0 mm`;
- no narrow single cantilever;
- zero outward change to the approved visible faceted exterior.

Do not place these pads or webs on the removable service cover.

### Removable rear shear cover

- preserve the current exterior and outline;
- rear-loaded locating-lip engagement: `3.0 mm`;
- mating clearance: `0.35 mm` per side;
- eight exterior M4 button-head screws;
- cover clearance bores: `4.5 mm`;
- captive brass inserts in fixed ASA bosses;
- locating lip carries shear; screws provide clamp;
- no gasket, sealing, or drainage features.

### Cable provision

- reserve mirrored drill zones near local `X +/-55`, `V -15`;
- keep both zones clear during structural design;
- select the actual side only after the bike cable/steering/lamp mockup;
- use the side with greater clearance, with right side as the tie-breaker;
- nominal final cable-only plate hole: `12 mm`, with split abrasion grommet;
- minimum cable bend radius: `12 mm`;
- provide strain relief within `25 mm` of the hole;
- if a complete connector rather than cable must pass through, stop and revise
  the contract before drilling.

## Required interactive implementation sequence

1. Verify the active FCStd hash and confirm it is the intended whole-head
   baseline candidate.
2. Capture opaque front, rear, left, right, top, and bottom screenshots with
   all intended production/working objects visible.
3. Save their paths and hashes in a V2 baseline manifest and obtain explicit
   user approval. Until then, geometry mutation remains blocked.
4. In FreeCAD, select the right-upper and right-lower rear-facing owner faces
   intended to receive the three right-side pad/web roots, plus the relevant
   rear-cover perimeter edges.
5. Record object internal name and label, sub-element ID, centroid, normal,
   bounding box, area/length, and owning part. Highlight the anchors and obtain
   explicit user approval.
6. Write one V2 mutation contract for one right-side working target. Keep the
   proposed plate, pads, hardware, and tool envelopes in separate
   `PROPOSED__` review objects; do not union them to working owners.
7. Prove the shared construction/finalization tooling with deterministic tests
   and a pinned-runtime, disposable, unsaved FreeCAD construction preflight.
8. In a fresh candidate chat, generate exactly one persisted right-side
   candidate through `run_iteration_v2.py`, then run preservation and bounded
   pre-visual validation.
9. Present the complete opaque six-view pack, anchor view, dimensions,
   interior/section hardware view, isolated proposal, insertion sweep, and
   validation table. Stop for explicit approval.
10. Mirror, integrate, export, slice, fabricate, and promote only after their
    separate approvals.

## Validation contract

The isolated proposal must prove:

- exact preservation of every frozen object and all rail/metal datums;
- widened plate valid and contained behind the preserved rear ASA form;
- complete metal/rail insertion, seating, fastening, and removal sweeps;
- all M5 and M4 hardware, washer, nut/insert, driver, and straight-tool paths;
- each pad and web is a valid closed solid with the required owner engagement;
- zero collision with frozen shells, rails, angles, crossbolts, adapter,
  sockets, eyes, ears, lighting, and reserved cable zones;
- zero unintended exterior protrusion;
- rear cover installs and removes by rear translation without cutting,
  bending, or separating the permanent shells;
- removing the cover exposes all six structural M5 fasteners;
- modified owner parts remain one connected printable component;
- Prusa MK4S support/brim orientation retains at least `10 mm` XY margin.

Physical release remains gated by:

- one right-side pad/root/captive-nut coupon;
- one M4 insert/locating-lip coupon;
- at least 20 cover service cycles without cracking, insert rotation, or
  looseness;
- a 60-second stationary proof load in forward, rearward, upward, downward,
  lateral, and torsional directions to the greater of `60 N` or five times
  completed-head weight;
- zero slip, cracking, creep, permanent deformation, or fastener movement;
- independent metal safety tether, vibration inspection, steering/lamp/cable
  clearance, and progressive low-speed ride tests.

## Rejected or prohibited variants

- moving either rail, its target, socket, cap station, or crossbolt datum;
- attaching the primary aluminum load path to the removable cover;
- deep rear undercut flanges that block insertion or removal;
- inaccessible loose internal nuts;
- placing new M5 paths at the old concentrated V0.5 centers;
- cutting accepted exterior skin to recover pad placement;
- adding a cable hole before its zone clears every structural and tool
  envelope;
- mirroring or integrating the right-side proposal before explicit approval;
- treating a successful slicer repair or overlapping compound as proof of a
  monolithic structural solid.

## Current validation performed

- Read-only FreeCAD connection check passed on 2026-08-22:
  FreeCAD `1.1.3`, GUI instance available.
- Current working FCStd and active lower STL hashes were recorded above.
- V0.5 shared-interface SHA-256:
  `6326b211e4eef8c87a2b17687e2d68406682d21a6fa7c81ad52c8a1b9e713c79`.
- The plate/hole margins above are analytic preflight values only; exact CAD,
  insertion, owner engagement, and hardware access remain unvalidated.

## Exact next user action

Start a clear Codex chat in the repository and provide this checkpoint path.
Keep `RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd` open. The new chat must
verify the file hash, capture the six opaque baseline views, and ask for their
explicit approval before requesting the right-side rear owner-face selections.

Suggested starter prompt:

```text
Resume the approved rear-interface V0.6 plan from
hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/REAR_INTERFACE_V06_WIDER_PLATE_IMPLEMENTATION_CHECKPOINT_2026-08-22.md.
Work interactively in the exact RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd
listed there. Keep every rail datum frozen. First verify the FCStd hash and
capture the six-view opaque V2 baseline pack; do not create geometry until I
approve that baseline and the selected right-side rear owner faces.
```
