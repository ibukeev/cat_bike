# Right A Surface-Open Insert Correction V1 Checkpoint — 2026-08-09

## Status

The isolated right-A head-tab insert cavity has been corrected and digitally
validated. The earlier right-A hole axis, panel tab, panel-side washer,
low-profile M3 screw, and 25-degree ball-end driver path remain unchanged.

The corrected geometry received user visual approval (`LGTM`) on 2026-08-09.
Nothing is production-unioned, mirrored, exported for fabrication, sliced, or
print-released. Right-A is released only to the controlled right-side A/B
integration gate.

## Why the prior V3 is rejected

`PROPOSED__RIGHT_A__HEAD_TAB__M3X3_SHORT_INSERT_RECESSED_V3` starts its
4.25 mm-diameter cavity 0.2 mm behind the mating face. That leaves the cavity
trapped behind the existing 3.4 mm screw bore, so the assumed 4.20 mm insert
body cannot enter. The prior axis and tool-access approval remains useful, but
V3 is not physically installable and must not be integrated or printed.

## Current source and review files

- Frozen source review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`
  - SHA-256:
    `31b304cc9bf7de9dba330c5b1d70f3c30d969b72c12e836b3af6a2f0bbd511a3`
- Numeric contract and validation:
  `config/right-a-surface-open-insert-correction-v1.json`
- Current isolated review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-surface-open-insert-correction-v1/CAT_HEAD_RIGHT_A_SURFACE_OPEN_INSERT_CORRECTION_V1.FCStd`
  - SHA-256:
    `a362f5c51299067d792d4afb1dacda19aaa3067fd8e6dc6d80ef174668994b80`
  - size: `5,064,576` bytes
  - FCStd ZIP validation: PASS
- Review evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-surface-open-insert-correction-v1/review/`
  - `01-right-a-surface-open-cavity-and-seated-insert.png`
  - `02-right-a-mating-side-insertion-sweep.png`
  - `03-right-a-corrected-pair-owner-context.png`
  - `04-right-a-isolated-corrected-head-tab.png`
- Frozen whole-head context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-full-head-context.png`

## Accepted and frozen geometry

- Right-A common bore axis:
  `(104.4048820139, 120.3391366839, 178.2794638319) mm`.
- Bore diameter: `3.4 mm`.
- Pair gap: `0.3 mm`.
- Tab thickness: `4.0 mm`.
- Panel-side hardware:
  - M3 x 8 low-profile socket screw;
  - 7 mm OD x 0.8 mm washer;
  - 25-degree ball-end driver path.
- Head-side hardware: M3 x 3 mm short heat-set insert, assumed maximum
  4.20 mm body diameter.
- Frozen and unchanged: all panel, upper-head, and ear owner geometry; all
  right-B geometry; left side; lower-face/rear-cassette ownership;
  reinforcement; eyes; C006; frozen V10; and
  `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.

## Corrected V4 design contract

- Proposal:
  `PROPOSED__RIGHT_A__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V4`.
- Cavity diameter: `4.25 mm`.
- Effective cavity depth from mating face: `3.2 mm`.
- Insert length: `3.0 mm`.
- Insert seating recess below mating face: `0.2 mm`.
- Remaining exterior wall: `0.8 mm`.
- Cutter start:
  `(105.9132545549, 120.3014737059, 175.2884952579) mm`.
- Cutter height: `3.25 mm`, including 0.05 mm mating-face Boolean
  overshoot.
- Cutter rotations, applied in order:
  - X: `-0.721443726 deg`
  - Y: `-26.760396045 deg`
  - Z: `72.368343247 deg`
- Calculated M3 x 8 thread engagement: `2.7 mm`.
- Calculated unused insert depth: `0.3 mm`.

## Validation performed

- Corrected tab: closed, valid, one solid, no self-intersection.
- Topology: 9 faces, 18 edges, 12 vertices.
- Volume: `1195.34 mm3`.
- Exterior bounding box: unchanged.
- Effective surface-open cavity depth: `3.2000 mm`.
- Insert recess below mating face: `0.2000 mm`.
- Remaining exterior wall: `0.8000 mm`.
- Full radius-`5.625 mm` cavity edge envelope: geometrically contained in
  the original undrilled head tab.
- Upper-head owner root overlap: `164.5685 mm3`, above the `80 mm3`
  minimum.
- Pair gap: `0.3000 mm`.
- Cavity-to-upper-head clearance: `1.3536 mm`.
- Corrected-tab-to-ear clearance: `27.4965 mm`.
- Seated insert body: no tab interference; intentional zero-distance bottom
  contact.
- Mating-side insertion sweep: no tab interference.
- Insertion sweep clearance:
  - upper head: `1.3786 mm`;
  - ear: `43.4099 mm`.
- Existing 25-degree panel driver clearance:
  - upper head: `7.7887 mm`;
  - ear: `40.2087 mm`;
  - drilled panel tab: `1.4404 mm`;
  - corrected head tab: `5.7613 mm`.

## Exact recreation sequence

Use the official FreeCAD 1.1.1 GUI with the AICopilot bridge; do not run an
arbitrary FreeCAD Python console command or headless macro.

1. Open the frozen right-A source review and save a separate correction copy.
2. Insert a fresh copy of
   `PROPOSED__RIGHT_A__HEAD_TAB__M3_BORE_MINUS_4P5_V2`.
3. Create a radius-`2.125 mm`, height-`3.25 mm` cylinder at the cutter
   start above.
4. Apply the X, then Y, then Z rotations above.
5. Cut that cylinder from the fresh drilled head-tab copy and name the result
   `PROPOSED__RIGHT_A__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V4`.
6. Recreate the radius-`5.625 mm`, height-`3.10 mm` contained edge
   envelope starting at
   `(105.8907415319, 120.3020358399, 175.3331365799) mm`.
7. Recreate the radius-`2.10 mm`, height-`3.00 mm` seated insert and the
   radius-`2.10 mm`, height-`18.35 mm` mating-side installation sweep at
   the main cutter start.
8. Repeat every validation above, save the isolated review FCStd, and verify
   its ZIP integrity and SHA-256.

## Next physical review

1. Preserve the approved corrected right-A V4 objects and numeric contract.
2. Build the exact-orientation ASA insert coupon and retain the physical hold
   until installation, torque, and pull-out checks pass.
3. Integrate approved right-A and right-B tabs only into their right-side
   owners, then rerun topology, root, access, insertion, exterior, and
   mirror-landing checks.
4. Mirroring, production STL export, slicing, and ASA shell printing remain
   later gates.
