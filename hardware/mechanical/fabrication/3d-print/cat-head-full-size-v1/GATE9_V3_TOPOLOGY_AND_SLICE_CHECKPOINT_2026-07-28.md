# Gate 9 V3 Topology and Slice Checkpoint — 2026-07-28

## Status

The combined full-scale aperture-frame and bottom-keel V3 candidate passes the
current digital topology, coarse keepout, and real Prusa slicing gates. It is a
review candidate, not authorization for the final ASA print.

The physical-fit review remains the authoritative requirements ledger:

- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- Findings F-01 through F-29
- Acceptance tests A-01 through A-39

The tracked machine-readable result is:

- `review/gate9-aperture-frame-and-keel-v3-summary.json`

Generated review outputs are intentionally ignored by Git and live under:

- `output/gate9-aperture-frame-and-keel-candidate-v3/`
- `output/gate9-aperture-frame-and-keel-candidate-v3/slicer-review/`

## Accepted decisions and dimensions

- Preserve the full 330 mm head width; do not solve printability by scaling the
  head down.
- Use aluminum interface revision `CAT-HEAD-SHELL-ALUMINUM-V0.3`.
- Use the full-size rear cassette at the accepted -70 mm offset.
- Keep the lower aluminum rails at X = -40 mm and +40 mm.
- Remove source faces 109 and 110, plus their synthetic closure triangles, from
  the lower shells and make them one separate bottom-keel part.
- The rear cassette owns the keel/cassette seam.
- Cut 0.6 mm nominal clearance into the keel at the cassette interface.
- Build connected aperture frames with 4.5 mm ribs and 5.5 mm hubs, recessed at
  least 0.3 mm behind the analytic exterior.
- Trim the upper frame endpoints 7 mm at left vertex 47 and right vertex 23 to
  clear the rear cassette.

## Validation performed

The generator reports one closed manifold component, zero boundary edges, and
zero nonmanifold edges for each of:

- left upper head
- right upper head
- left lower face
- right lower face
- bottom keel

The aperture frames satisfy the 0.3 mm exterior recess check. All four shell
frames clear the rear cassette and aluminum keepout envelopes. The relieved
bottom keel clears both the cassette and the aluminum envelopes.

All eight actual candidate STLs were independently orientation-searched and
sliced with the current Prusa V3 project profile. Every part passes the required
10 mm post-brim XY bed margin:

| Part | Selected XYZ rotation | Margin | Filament | Support | Time |
| --- | --- | ---: | ---: | ---: | ---: |
| Left upper head | 4°, 4°, 10° | 39.718 mm | 133.18 g | 90.527 g | 11:12:55 |
| Right upper head | 126°, 100°, 124° | 37.871 mm | 74.74 g | 35.018 g | 7:13:46 |
| Left lower face | 82°, 166°, 168° | 31.651 mm | 137.67 g | 100.277 g | 12:08:35 |
| Right lower face | 10°, 148°, 108° | 32.980 mm | 62.14 g | 29.429 g | 6:29:45 |
| Left ear | 138°, 110°, 88° | 60.993 mm | 19.03 g | 1.895 g | 1:58:08 |
| Right ear | 138°, 70°, 88° | 58.182 mm | 22.93 g | 5.522 g | 2:28:20 |
| Rear cassette | 62°, 122°, 82° | 12.887 mm | 125.18 g | 21.673 g | 10:21:58 |
| Bottom keel | 4°, 126°, 90° | 42.427 mm | 25.40 g | 0.931 g | 2:22:08 |

Exact eight-part total: 600.27 g filament, including 285.272 g support,
266.6 cm³ support volume, and 54:15:35 estimated print time.

## Rejected or unsafe variants

- Do not restore the floating or exterior-protruding reinforcements from the
  printed PLA revision.
- Do not keep the disconnected front aperture frame.
- Do not let both the keel and rear cassette own overlapping seam material.
- Do not use the unrelieved keel that intersects the rear cassette.
- Do not mirror a single slice estimate and call both sides validated; all
  eight V3 parts were sliced independently.
- Do not authorize a full ASA print from this checkpoint. The unresolved
  interfaces below still require implementation and physical coupons.

## Exact regeneration commands

Run from the repository root:

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/gate9-rear-architecture-comparison-v1.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_aperture_frame_and_keel_candidate_v3.py -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-aperture-frame-and-keel-candidate-v3.json
```

```bash
python3 -u \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_aperture_frame_and_keel_candidate_v3.py \
  -- --threads 8
```

## Next design and physical-review steps

1. Design the hidden keel/lower-shell and keel/cassette flanges, alignment
   features, fasteners, sealing, drainage, and wire route.
2. Integrate the actual 20.5 mm aluminum-tube sockets and revise the front/top
   portals to match V0.3 aluminum geometry.
3. Replace the ear pin-against-pin interface with the accepted two-bolt design.
4. Rebuild the eye bucket, mounts, and rear plate around the connected frame.
5. Rebuild the glow-panel skirts/connectors and validate wrapped-panel
   insertion, clearance, retention, and removal.
6. Run complete shell-pair collision, flange-meeting, and assembly-path checks.
7. Print seam/socket/eye/wrapped-panel coupons in representative materials and
   physically validate them.
8. Regenerate and re-slice all eight final parts before authorizing ASA.
