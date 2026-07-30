# Gate 9 V7 M2 rear-interface coordination checkpoint — 2026-07-29

## Status

This is a resumable shell-workstream checkpoint, not a production-print or
metal-fabrication release.

### V0.5 post-coordination result

The aluminum workstream accepted the proposed bottom pair and issued
`CAT-HEAD-SHELL-ALUMINUM-V0.5` / `V0.5-M2`. The V7 config and generator now
consume X `+/-7.4`, V `-30` with `14 x 36 x 12 mm` bottom pads. Aluminum and
bottom-pad checks pass, but the full V7 candidate remains held on the four
non-bottom issues recorded in
`review/gate9-v7-v05-coordinated-interface-validation.json`. No fabrication or
final ASA print is authorized. The proposal discussion below is retained as
history and evidence for the accepted delta.

The shell workstream consumed the complete read-only
`CAT-HEAD-SHELL-ALUMINUM-V0.4-M2` review assembly. No aluminum-owned CAD and no
shared-interface file was changed.

The current six-hole pattern cannot satisfy the required combination of:

- complete preassembled M2 insertion/removal;
- a 10 mm washer;
- a large, well-rooted ASA pad; and
- the 14 mm shell-pad tool envelope.

The blocking holes are only the bottom pair at local X/V `(-10,-30)` and
`(10,-30)`. A coordinated two-hole revision is proposed at X/V `(-7.4,-30)`
and `(7.4,-30)`. It has not been applied to release CAD.

## Authoritative inputs

- `hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`
- `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/V04_M2_ORDERED_ANGLE_CHECKPOINT_2026-07-29.md`
- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v04.json`
- `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/review/frame-fixed-mount-v04-final-summary.json`
- `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/v04-m2-angle-stock/review-model/frame-fixed-mount-v04-m2-angle-stock-review.blend`
- aluminum handoff commit `3924f770a393f6a8d97dba29e540002a583540c7`

## Current review files

- V7 config:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json`
- V7 generator:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_m2_rear_interface_candidate_v7.py`
- machine-readable coordinated-change proposal:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review/gate9-v7-bottom-m5-center-revision-proposal.json`
- generated review model:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/gate9-m2-rear-interface-candidate-v7.blend`
- generated validation report:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/gate9-m2-rear-interface-candidate-v7.json`
- generated renders:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/renders/`

Generated V7 output is diagnostic and may be stale after later source edits.
Regenerate it before relying on any output file.

## Accepted shell-side decisions

1. Aluminum remains read-only in this workstream.
2. The accepted compound rail axes, X `+/-40` lower targets, 21 mm upper
   sockets, 30 mm insertion depth, M4 retention stations, rail stock, plugs,
   tapered spacers, cheeks, angle bases/uprights, and complete hardware/tool
   envelopes remain unchanged.
3. A rigid preassembled rail pair cannot enter or leave two blind divergent
   21 mm sockets. The divergence produces `2.7882 mm` lateral drift over the
   30 mm socket depth while only `1.0 mm` lateral clearance is available. The
   common-motion limit is `10.7596 mm`.
4. The shell-owned correction is a retained 21 mm U-cradle plus removable
   outboard socket cap on each side. The rail axis, cavity size, depth, lead-in,
   and M4 station remain unchanged.
5. The six structural attachments are owned by the four main shell sections,
   never by the removable rear bezel or bottom keel.
6. The top and middle hole centers can remain unchanged. The two X `+/-20`,
   V `0` middle pads use 21 mm circular bosses, the largest whole-millimeter
   diameter verified clear of the complete seated M2 assembly.
7. Reinforcement load paths route around the seated angle/rail envelopes. A
   seated complete-M2 collision run passed after this rerouting.
8. Generic repeated collision checks now use AABB broad phase followed by exact
   triangle-BVH overlap. This reduced the complete review run from more than
   ten minutes to roughly 13 seconds without weakening the intersection test.
9. Print-orientation search is deferred to the dedicated PrusaSlicer pass;
   the generator performs exact component, manifold, dimension, and volume
   checks.

## Blocking evidence at the current bottom centers

The complete M2 assembly must enter with both lower crossbolts, heads, washers,
and nylocs already installed. During common rail withdrawal, the crossbolt
envelopes sweep through the current bottom pads at X/V `(-10,-30)` and
`(10,-30)`.

Diameter sweep at the existing centers:

| Circular bottom boss | Complete M2 sweep |
|---|---|
| 8–11 mm | clear |
| 12 mm and larger | collision |

An 11 mm boss leaves only `0.5 mm` of ASA outside a 10 mm washer. That is
rejected as inadequate for the final structural print. The original
`19 x 36 x 12 mm` bottom pads also collide throughout the required service
motion.

The unmodified V6 shell edges themselves are clear of the moving crossbolts.
An attempted rear-aperture cutter was therefore rejected: the problem is the
pad location, not inherited aperture material.

## Coordinated center proposal

Change only the bottom shell-attachment pair:

| Hole | Current X/V (mm) | Proposed X/V (mm) |
|---|---:|---:|
| bottom left | `-10,-30` | `-7.4,-30` |
| bottom right | `10,-30` | `7.4,-30` |

Each center moves `2.6 mm` toward the head centerline. Use a
`14 x 36 x 12 mm` bottom ASA pad. This leaves `2.0 mm` of ASA beyond the 10 mm
washer on each narrow side and retains a broad 504 mm² pad face plus routed
load path to the 720 mm² shell root.

Validated proposal margins:

- bottom M5 hole-to-plate-edge margin: `7.0819 mm`;
- 10 mm washer-to-plate-edge margin: `4.8319 mm`;
- 14 mm tool-envelope-to-plate-edge margin: `2.8319 mm`;
- opposing 14 mm tool-envelope gap: `0.8 mm`;
- nearest adapter-hole to 14 mm tool-envelope clearance: `7.3963 mm`;
- side plate-edge to 14 mm tool-envelope margin at V `-30`: `41.8975 mm`;
- both proposed pads clear the complete seated M2 assembly; and
- both proposed pads clear every complete-M2 sample at common-withdrawal
  offsets `0`, `5`, `10`, `20`, and `31 mm`.

The detailed proposal is in
`review/gate9-v7-bottom-m5-center-revision-proposal.json`.

## Rejected or unsafe variants

- Keep the current bottom centers with the original `19 x 36 mm` pads:
  crossbolt sweep collision.
- Keep the current bottom centers with a round boss no larger than 11 mm:
  only `0.5 mm` washer-bearing edge.
- Cut broad service slots through the rear shell: unnecessary and one coarse
  version split a lower shell into two components.
- Treat the socket shells as two blind receivers: kinematically impossible for
  the rigid divergent rail pair.
- Move any shared center in shell CAD alone: prohibited by the interface
  control.
- Use the removable rear bezel or its cosmetic M3 hardware as a structural
  substitute for any of the six M5 load paths: prohibited.

## Exact regeneration command

From the repository root:

```bash
python3 -m py_compile \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_m2_rear_interface_candidate_v7.py

blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python-expr "import sys; sys.path.insert(0, 'hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source'); import generate_gate9_m2_rear_interface_candidate_v7 as candidate; candidate.v6.main=lambda: None; candidate.main()" \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json
```

The generator currently exits nonzero because the full V7 shell candidate remains held on middle-M5 tool access, preassembled lower-crossbolt service sweep, cap-to-receiver overlap, and the root-recess validator definition. The V0.5 bottom centers themselves pass.

## Required next shell step

The aluminum workstream accepted X `+/-7.4`, V `-30` and reran plate-edge, adapter-hole, angle-base, fastener,
washer, nut, tool-access, insertion, seated, fastened, and removal checks.

The V0.5 shared revision now exists and the shell generator consumes its centers. The next shell pass must resolve the four recorded non-bottom blockers without changing V0.5 centers or preserved rail/socket datums, rerun complete A-39, and only then perform the Prusa MK4 ASA slicing/bed-margin audit and produce final physical-review STLs.

## Next physical-review steps after digital release

1. Print only the revised rear-interface/pad and socket-cap coupons first.
2. Test the actual 10 mm washers, selected M5 locking hardware, M3 socket-cap
   inserts, and purchased 19 x 19 x 2 mm rail offcuts.
3. Confirm preassembled insertion, seating, M4 installation, six M5 fastening,
   cap installation, reverse removal, and tool access.
4. Do not start the final full ASA shell print until the ordered angle is
   measured and the physical rear-interface/angle coupon passes.
