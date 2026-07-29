# Gate 9 V4 Service-Seam Checkpoint — 2026-07-28

## Status

V4 is a useful but rejected review candidate. It proves that the service-seam
hardware can be represented as six watertight printed parts and that all eight
actual parts still fit the Prusa MK4/MK4S envelope. It does **not** pass the
seated collision, frozen-metal clearance, service-sweep, or drainage gates and
must not be printed as the final ASA head.

The authoritative requirements remain:

- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- Findings F-01 through F-29
- Acceptance tests A-01 through A-39

The tracked machine-readable result is:

- `review/gate9-service-seams-v4-summary.json`

Generated review outputs are ignored by Git and live under:

- `output/gate9-service-seams-candidate-v4/`
- `output/gate9-service-seams-candidate-v4/slicer-review/`

## Accepted decisions and dimensions

- Preserve the 330 mm full-scale head and aluminum interface
  `CAT-HEAD-SHELL-ALUMINUM-V0.3`.
- Keep the full-size rear cassette datum at -70 mm and lower rails at
  X = -40 mm and +40 mm for comparison; the legacy cassette solid itself is
  not accepted.
- Use a removable bottom keel installed from below.
- Use eight M3x8 button-head stainless screws into short brass heat-set
  inserts:
  - three per lower-shell/keel seam
  - two at the rear-cassette/keel seam
- Keep one right-center round primary datum, one left-center lateral
  secondary slot, and longitudinal relief slots at the remaining lower-seam
  points.
- Use 3.6 mm keel clearance holes, 4.6 mm insert pockets, and 4.2 mm pocket
  depth as coupon dimensions.
- Use shell-owned continuous stepped service spines instead of discrete pads.
  The continuous geometry eliminated the fragile/floating-pad Boolean failure.
- Keep 1.0 mm closed-cell EPDM foam as the seal coupon material, targeting
  0.3 mm compression. This seal has not been physically qualified.
- Keep two 3.0 mm cylindrical, keel-embedded wire ribs at X = -8 mm and
  X = +8 mm. They leave exactly 13.0 mm clear width and feed a 20 mm split
  rear exit.
- Service order is keel first, rear cassette second. The cassette cannot be
  validated against the keel as a simultaneously installed removal obstacle.

## Validation performed

The canonical V4 review generator reports one closed manifold component, zero
boundary edges, and zero nonmanifold edges for:

- left upper head
- right upper head
- left lower face
- right lower face
- rear cassette
- bottom keel

Positive digital results:

- eight fastener records generated
- both body/cassette collision sets clear
- keel/rear-cassette seated collision clear
- protected wire corridor meets the 13 mm by 5 mm provisional bundle envelope
- all eight candidate parts have a real margin-passing ASA slice

Rejected digital results:

- seated keel intersects left lower face in 91 sampled triangle pairs
- seated keel intersects right lower face in 17 sampled triangle pairs
- rear cassette intersects the frozen backplate in 25 triangle pairs
- rear cassette intersects each rail in 4 triangle pairs
- rear cassette intersects each moving shoe envelope in 6 triangle pairs
- the 4 mm nominal drain cuts remove only 3.559 mm³, below the 35 mm³ gate
- the keel service sweep fails at its seated position because of the same
  lower-shell collision

An attempted subtractive post-process was explicitly rejected. It did not
remove the reported seam or metal conflicts, and its edge-scupper Boolean
increased calculated volume instead of removing it. Those outputs were
discarded; the canonical output was regenerated afterward.

## Real slice feasibility

All eight actual STLs were independently orientation-searched and sliced with
the current Prusa ASA review profile. This validates build-envelope feasibility
only.

| Part | Selected XYZ rotation | Margin | Filament | Support | Time |
| --- | --- | ---: | ---: | ---: | ---: |
| Left upper head | 4°, 4°, 10° | 39.718 mm | 133.18 g | 90.527 g | 11:12:55 |
| Right upper head | 126°, 100°, 124° | 37.871 mm | 74.74 g | 35.018 g | 7:13:46 |
| Left lower face | 82°, 166°, 168° | 31.651 mm | 150.77 g | 101.414 g | 13:55:36 |
| Right lower face | 142°, 130°, 138° | 31.910 mm | 131.31 g | 81.306 g | 12:56:36 |
| Left ear | 138°, 110°, 88° | 60.993 mm | 19.03 g | 1.895 g | 1:58:08 |
| Right ear | 138°, 70°, 88° | 58.182 mm | 22.93 g | 5.522 g | 2:28:20 |
| Rear cassette | 62°, 122°, 82° | 13.162 mm | 136.20 g | 26.512 g | 11:38:07 |
| Bottom keel | 50°, 0°, 144° | 41.341 mm | 26.46 g | 4.868 g | 3:08:24 |

Exact eight-part total: 694.62 g filament, including 347.062 g support,
324.348 cm³ support volume, and 64:31:52 estimated print time.

The rear cassette remains the closest part to the bed limit, but its
13.162 mm post-brim margin exceeds the required 10 mm. The earlier concern
about the lower-face piece barely fitting the bed does not require scaling the
head down at this stage.

## Rejected or unsafe variants

- Do not use discrete floating fastener pads or flying connector tabs.
- Do not use the failed multi-Boolean carrier construction; Blender can return
  an empty operand during the second pad union.
- Do not use rectangular coplanar wire rails. They produce nonmanifold Boolean
  edges on the faceted keel.
- Do not use the nominal V4 drain holes as evidence of drainage.
- Do not use the failed subtractive post-process or its edge scuppers.
- Do not treat printer-envelope success as permission for a production print.
- Do not resolve the rear metal conflict by blindly subtracting the complete
  metal envelopes from the legacy cassette. The rear shell must be rebuilt
  from the metal datum as an open bezel.

## Exact regeneration commands

Run from the repository root. The Blender command is expected to exit with
status 2 after saving its review outputs because the digital V4 acceptance gate
is intentionally false.

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/gate9-rear-architecture-comparison-v1.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_service_seams_candidate_v4_review.py -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-service-seams-candidate-v4.json
```

```bash
python3 \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_service_seams_candidate_v4.py \
  --threads 8
```

## Next design and physical-review steps

1. Build V5 directly from complementary interfaces, not by subtracting from the
   V4 legacy solids:
   - derive the keel perimeter from the final left/right service-spine
     envelopes with 0.6 mm positive clearance
   - derive a new open rear bezel from the V0.3 backplate, rail, and moving-shoe
     envelopes
   - generate open edge scuppers as part of the keel boundary mesh rather than
     Boolean cuts
2. Re-run seated collision matrices and ordered removal sweeps before adding
   any further shell details.
3. Integrate the real 20.5 mm aluminum-tube sockets and revise the front/top
   portals to the V0.3 tube angles.
4. Replace the ear pin-against-pin interface with the accepted two-bolt
   interface.
5. Rebuild the connected eye bucket/mount/rear plate and the wrapped glow-panel
   skirts/connectors.
6. Print representative seam, socket, eye, and wrapped-panel coupons.
7. Re-run all eight final slices only after every collision and physical coupon
   gate passes.
