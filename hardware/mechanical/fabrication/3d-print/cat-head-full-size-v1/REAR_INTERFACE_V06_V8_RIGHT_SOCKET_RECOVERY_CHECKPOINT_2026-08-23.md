# Rear-interface V0.6 — V8 right rail-socket recovery checkpoint — 2026-08-23

## Current state

`V8_REVIEW_ONLY__UNSAVED__NOT_PRINT_RELEASED`

The prior V6 cleanup removed the V34 right rail-socket/root context from the
working document.  The earlier V7 right-top print trial must therefore remain
**on hold**: it was sliced but its physical print was stopped because this
socket/root geometry was missing.

The live V6 session now contains a replacement review package:

- `PROPOSED_TOP_RIGHT_PRINT_PACKAGE_V8_SOCKET_CONTEXT_COMPOUND`
- 70 valid solids total.
- It keeps the existing 63-solid V7 package unchanged and adds seven valid
  V34 socket-context solids (C002+C042 are locally joined as one solid).
- This is a compound for positional review only. It is not a globally fused
  solid, not exported, and not approved for slicing or printing.

## Files and preservation

- Active working file: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V6.FCStd`
- Preserved recovery source: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V5.FCStd`
- V5 SHA-256: `5c7de806142b1955c692def5717ed5b46a40ffcbe6db07fad078fbacca730c3e`
- The V8 proposal was created after the last manual V6 save and is **not yet
  saved**. V5 was opened read-only as a geometry source and was not changed.

## Recovered frozen V34 context

Each item was copied by exact V5 object name and validated as one closed solid
with matching volume and bounding box:

1. `WORKING_RIGHT_UPPER_C002_V34_BASELINE`
2. `WORKING_RIGHT_UPPER_C022_V34_BASELINE`
3. `WORKING_RIGHT_UPPER_C023_V34_BASELINE`
4. `WORKING_RIGHT_UPPER_C033_V34_BASELINE`
5. `WORKING_RIGHT_UPPER_C034_V34_BASELINE`
6. `WORKING_RIGHT_UPPER_C037_V34_BASELINE`
7. `WORKING_RIGHT_UPPER_C038_V34_BASELINE`
8. `WORKING_RIGHT_UPPER_C042_V34_BASELINE`

`C002` and its true V34 root `C042` overlap by `638.793197 mm3`; their local
fuse is valid. All rail datums remain frozen and untouched.

Explicit exclusions:

- `C020` — omitted at the user's instruction.
- `C032` — rejected: it has zero common volume with C002 and is not its root.

## Rejected implementation

`fuse_v6_right_top_v7_with_recovered_socket_context_v8_v2.py` attempted one
global Boolean fuse of the V7 compound plus every recovered member. FreeCAD
reported `V8 fusion produced an invalid shape`; do not use that output path.
The invalid fuse did not create a saved or released artifact.

## Exact regeneration command

With V6 as the active FreeCAD document:

```python
exec(compile(open(r"/home/bsk/Projects/BM_personal_LED-projects /cat_bike/hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/compose_v6_right_top_v7_with_recovered_socket_context_v8_v3.py", encoding="utf-8").read(), "compose_v6_right_top_v7_with_recovered_socket_context_v8_v3.py", "exec"))
```

The script directly reads V5 (no transient GUI selection), copies/validates
the eight named sources, locally fuses only C002+C042, then makes the valid
70-solid review compound. It never changes a rail datum, V5, V7, or any source
solid; it never saves, exports, or print-releases.

## Required next review

1. Inspect V8 at close range and confirm the recovered C002 socket and C042
   root meet the visible top-right shell exactly where expected.
2. Confirm the surrounding recovered C022/C023/C033/C034/C037/C038 context
   has no unintended duplicate or collision with the V7 trial geometry.
3. Only after explicit user approval, decide whether a slicer-safe union or a
   multi-body 3MF handoff is required. Do not restart `RIGHT_TOP_PRINT.3mf`
   from the earlier V7-only geometry.
