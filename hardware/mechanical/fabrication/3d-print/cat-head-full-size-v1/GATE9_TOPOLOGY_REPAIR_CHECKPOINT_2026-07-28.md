# Gate 9 Body-Shell Topology Repair Checkpoint — 2026-07-28

## Current state

The selected Gate 9 full-size `-70 mm` rear-cassette architecture remains the
working baseline. No production STL or G-code is released.

The original pre-export source topology has now been audited separately from
STL import. This matters because STL import can weld coincident coordinates and
make point- or edge-only contact appear connected even though the printed joint
has essentially no structural root.

## Current review and output files

Tracked diagnostics:

- `source/analyze_gate9_selected_bridge_sites.py`
- `source/analyze_gate9_selected_bridge_sites_v2.py`
- `source/analyze_gate9_selected_face_adjacency.py`

Local generated review outputs:

- `output/gate9-selected-bridge-site-audit-v2/`
- `output/gate9-selected-face-adjacency/`

The authoritative architecture and interface inputs remain:

- `GATE9_REAR_ARCHITECTURE_CHECKPOINT_2026-07-28.md`
- `../../../../CAT_HEAD_GATE9_REAR_ARCHITECTURE_DECISION_2026-07-28.md`
- `../../../../interfaces/cat-head-shell-aluminum-interface-v03.json`
- `../../../../CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`

## Accepted decisions and dimensions

- Preserve the full 330 mm exterior scale.
- Retain the full-size `-70 mm` rear cassette.
- Retain shared interface revision `CAT-HEAD-SHELL-ALUMINUM-V0.3`.
- Retain lower rail targets at head X `+/-40 mm` for the first coordinated
  rebuild.
- Measured rail stock is 19 x 19 x 2 mm square aluminum tube.
- Do not repair disconnected shells with thin flying tabs, point-contact
  appendages, or STL-coordinate welding.

## Validation performed and results

### Pre-export solid topology

The four selected body parts were duplicated directly from the Gate 9
comparison BLEND before STL export and separated by loose topology:

| Body part | Closed solid components |
| --- | ---: |
| Left upper head | 2 |
| Right upper head | 2 |
| Left lower face | 2 |
| Right lower face | 2 |

Every component is individually closed and manifold. The problem is not an
open mesh; it is multiple closed solids with inadequate contact.

The closest apparent contacts are all zero-distance coincident point or edge
contacts. A provisional 14 mm bridge envelope at each contact produced zero
coarse collisions with the selected cassette, V0.3 backplate, both rails,
lower-shoe envelopes, tool envelopes, and adapter-hardware envelopes.

That collision result only establishes available volume. It does not approve
the provisional cylindrical bridge shape or placement.

### Pre-solidify source-face topology

The source facets were then evaluated before shell solidification:

| Body part | Source edge-components | Face counts by component |
| --- | ---: | --- |
| Left upper head | 2 | 6, 3 |
| Right upper head | 2 | 6, 3 |
| Left lower face | 3 | 14, 2, 1 |
| Right lower face | 3 | 13, 2, 1 |

The minimum upper-shell face paths cross exactly one removed glow facet:

- right: opaque face `63` -> removable-glow face `72` -> opaque face `71`;
- left: opaque face `92` -> removable-glow face `98` -> opaque face `97`.

The minimum lower-shell nose paths also cross exactly one removed glow facet:

- right: opaque face `67` -> removable-glow face `10` -> opaque face `8`;
- left: opaque face `93` -> removable-glow face `14` -> opaque face `12`.

The third lower component is the manually split bottom-center
`MANQ008_RIGHT` / `MANQ008_LEFT` facet. It has no edge-connected path to the
main lower component and only meets the surrounding source at vertices. The
configured bottom-closure triangles do not create a dependable pre-export
single-body connection and appear as the second isolated closed solid after
solidification.

## Rejected or unsafe variants

- Treating imported-STL connectedness as proof of structural continuity.
- Keeping the isolated lower bottom-closure plate unchanged.
- Using the provisional 14 mm cylinders as production bridges.
- Restoring the Gate 5 nearest-vertex eye ribs or any similar arbitrary
  center-directed cylinder.
- Filling an entire glow facet with opaque structure merely to make topology
  pass.

The provisional cylinders are useful keep-out probes, but their visible and
insert-adjacent placement does not provide a controlled glow-panel landing
surface, assembly clearance, or exterior-preservation proof.

## Required production direction

1. Build a recessed internal perimeter frame at each affected glow opening.
   The frame must overlap substantial areas of both opaque source components,
   leave a deliberate illuminated aperture, and provide controlled panel
   seating/retention space.
2. Give each frame and seam feature one explicit shell owner so opposing shell
   reinforcement cannot occupy the same assembly volume.
3. Repartition or deliberately frame the two bottom-center `MANQ008` facets
   and closure areas. Vertex-only contact is forbidden.
4. Boolean-union every retained frame into its parent shell and require exactly
   one closed manifold connected component before export.
5. Compare the result against the clean faceted exterior and reject every
   outward deviation on visible or mirror-panel landing faces.
6. Validate glow-panel and eye insertion against the complete final internal
   frame, not against the clean shell alone.

## Exact regeneration commands

From the repository root:

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/gate9-rear-architecture-comparison-v1.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/analyze_gate9_selected_bridge_sites_v2.py \
  -- \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-selected-bridge-site-audit-v2

blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/analyze_gate9_selected_face_adjacency.py \
  -- \
  --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-selected-face-adjacency/gate9-selected-face-adjacency.json
```

## Next physical-review steps

Do not print a complete body shell yet. After the aperture-frame ownership and
geometry pass digital review:

1. print one upper-shell aperture-frame/bridge coupon;
2. print one lower nose/underside connection coupon;
3. test both against the matching glow-panel edge or a clearance dummy;
4. reject any coupon that telegraphs through the exterior, blocks the insert
   path, flexes at the root, or separates under firm hand loading.
