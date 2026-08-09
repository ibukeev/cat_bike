# FreeCAD Opposite-Side Flange Pilot V1 Checkpoint — 2026-08-07

## Status

The controlled FreeCAD workflow is installed and its first immutable pilot is
ready for face/edge selection. No head, ear, translucent-panel, connector,
reinforcement, eye, rear-cassette, or aluminum geometry was changed.

The frozen Blender source remains:

- `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend`
- SHA-256:
  `cac7c0a1cfadfa0adbd469012b8c94b849b5f1d9a25488098c7e0baa533baa62`

The FreeCAD pilot is:

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_OPPOSITE_SIDE_FLANGE_PILOT_V1.FCStd`
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/reference-manifest.json`
- review images under
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/review/`

## Frozen pilot scope

The document contains exactly three separately selectable reference meshes:

1. `REFERENCE__right_translucent_panel`
   - Blender source: `EAR10_ACCEPTED_V3_BODY__right`
   - role: the only pilot panel
2. `REFERENCE__right_upper_head_owner`
   - Blender source: `right_upper_head`
   - role: receiving structural owner
3. `REFERENCE__right_ear_collision_context`
   - Blender source: `right_ear`
   - role: nearby collision/assembly context only

Explicitly excluded: both sides' V10 orange and green proposed flanges, all
left-side geometry, eyes, lower faces, rear cassette, reinforcement, C006, and
all aluminum plate/rail geometry. The metal workstream remains preserved and
tied to `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

No connector is authorized until the user selects the actual panel and owner
faces/edges in FreeCAD and approves the highlighted selection report. The two
panel attachment regions must be near opposite usable sides of the panel; a
root-volume or center-distance metric cannot substitute for anti-flap leverage.

## Toolchain and safety boundary

- FreeCAD: official `1.1.1` Linux AppImage at
  `/home/bsk/.local/opt/freecad/FreeCAD_1.1.1-Linux-x86_64-py311.AppImage`
- AppImage SHA-256:
  `e2006138400b2fa85fa2e160e872d00767eb32964e85075830f7e198a3a876e1`
- FreeCAD MCP bridge: `/home/bsk/.local/share/freecad-mcp`
- pinned bridge revision:
  `ee2681377af35907c115f19a63de8a09fe158568`
- project MCP allowlist: `.codex/config.toml`
- portable MCP launcher: `software/tools/start_freecad_mcp_cat_head.sh`
- project workflow skill:
  `.agents/skills/cat-head-cad-change-control/SKILL.md`

The bridge is third-party and local-only. Project configuration excludes
arbitrary Python execution, macros, CAM, headless spawning/control, restart,
and reload tools. Geometry-mutating tools remain approval-gated. The custom
skill requires selection evidence, an explicit design contract, separate
`PROPOSED__` solids, one-side review, validation, and user approval before any
mirror, integration, STL, G-code, or print release.

The installed Snap FreeCAD was rejected for this workflow because its bundled
PySide/Qt libraries failed at startup. The Snap was not modified or removed;
only its failed AICopilot addon copy was removed. The official AppImage and its
separate user addon directory are used instead.

## Validation performed

- Frozen-source SHA check: PASS.
- Exact object-name check: PASS; no fallback or substitution was used.
- Export count: PASS; exactly three STL references.
- FreeCAD import count: PASS; exactly three separately selectable objects.
- FreeCAD document save: PASS.
- Alignment/context visual inspection: PASS for pilot setup.
- Connector geometry: NOT CREATED.
- Boolean, repair, remesh, decimation, mirroring, or integration: NOT RUN.

Reference STL hashes:

- panel: `f8e2191fb76167e466b3d96caf1703b9cc433de21232305dcd17e4998e056f39`
- upper-head owner:
  `622b4f9932ed741d028e8e502812cd1bfa5354aa8b489784aa7a290e1840f8de`
- ear collision context:
  `fb5194e7ed7ecc2f989a776c2393e711bc77823a595227609496c82bc59dad39`

Read-only FreeCAD mesh validation exposed pre-existing source conditions:

- right translucent panel: non-manifold, open/not watertight, reported
  self-intersections;
- right upper-head owner: non-manifold, open/not watertight, reported
  self-intersections;
- right ear: manifold and watertight, but reported self-intersections.

No automatic repair was applied because that would silently change the frozen
reference. These conditions are acceptable for a placement-only pilot, but
they are an explicit hold before any final Boolean integration or print
release. A later integration phase must establish a reviewed solid-repair
method or return to the upstream generators.

## Exact reference regeneration

From the repository root:

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/export_freecad_opposite_side_flange_pilot_v1.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/freecad-opposite-side-flange-pilot-v1.json
```

The exporter aborts if the V10 file hash or any of the three exact Blender
object names differs. It does not repair or combine geometry.

The tracked MCP launcher uses `FREECAD_MCP_ROOT` and
`FREECAD_MCP_FREECAD_BIN` when set, with the approved `$HOME/.local` install
locations as defaults. Launch the installed FreeCAD GUI with:

```bash
"${FREECAD_MCP_FREECAD_BIN:-${HOME}/.local/opt/freecad/FreeCAD_1.1.1-Linux-x86_64-py311.AppImage}"
```

Open the pilot `.FCStd` listed above. Start a new Codex session from the
repository root after installation so project MCP configuration and the custom
skill are loaded.

## Next review — no geometry work yet

1. In the FreeCAD tree, confirm the document has only the three `REFERENCE__`
   objects listed above.
2. Select the first intended panel attachment face/edge near one usable side of
   `REFERENCE__right_translucent_panel`.
3. Ctrl-select the second intended panel attachment face/edge near the opposite
   usable side.
4. Select the corresponding receiving regions on
   `REFERENCE__right_upper_head_owner` in a separate selection round.
5. Tell Codex `selected`. Codex must report object labels, subelement IDs,
   centroids, normals, bounding boxes, areas/lengths, owner assignments, and a
   highlighted screenshot.
6. Approve or reject those anchors explicitly. Only approval permits a
   dimensioned, separate `PROPOSED__` flange pair on the right side.

Do not mirror to the left, integrate, export printable parts, or start ASA
printing from this pilot.

## Anchor candidates V1 — awaiting review

The user authorized marker creation after confirming that selecting a large
imported mesh object could not communicate an exact attachment center. The
immutable three-reference pilot was first saved as the separate review file:

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V1.FCStd`

No object in the original pilot file was changed. The review copy contains the
same three `REFERENCE__` objects plus exactly two temporary marker spheres:

- `REVIEW_ONLY__ANCHOR_CANDIDATE_A__FRONT`
- `REVIEW_ONLY__ANCHOR_CANDIDATE_B__REAR`

Each marker has a 5 mm radius. Marker size is only for visibility; the sphere
center is the proposed datum coordinate. Neither marker is connector geometry.

### Numeric marker contract

The centers were derived from the frozen V10 right-panel owner boundary, not
from the screenshot:

- A/front uses reviewed boundary index `2`, mesh edge `[14, 23]`, owner
  `right_upper_head`, and is inset `15.0 mm` from the front boundary extreme.
  Center: `(106.484329, 103.349472, 179.542068) mm`.
- B/rear uses reviewed boundary index `0`, mesh edge `[23, 61]`, owner
  `right_upper_head`, and is inset `15.0 mm` from the rear boundary extreme.
  Center: `(82.255508, 234.494415, 205.475845) mm`.
- Direct center-to-center span: `135.862403 mm`.
- Owner-boundary path span between marker centers: `146.805684 mm`.
- FreeCAD measured sphere-to-sphere surface clearance: `125.862 mm`, consistent
  with the direct center span minus two 5 mm marker radii.

Both points are on owner-supported boundary segments at opposite usable panel
regions. This is an anchor-placement proposal only. Root engagement, fastener
axis, tab orientation, collision, motion, hardware access, and exterior-mask
checks have not begun.

### Validation and rejected marker method

- Reference-object count before marker work: exactly `3`.
- Review-object count after marker work: exactly `5`.
- Both marker centers match the numeric contract to displayed FreeCAD
  precision.
- Both markers are closed, valid solids with no reported self-intersection.
- Original pilot and V10 reference geometry remain unchanged.

The first attempt used two `PartDesign::Point` datum objects. The installed
handler stored the requested attachment offsets but rendered the points at the
document origin. That failed visual-position validation. The document was
rolled back to checkpoint `before_anchor_candidates_v1`, removing the body,
origin features, and both failed points before the marker spheres were made.
No failed datum objects remain.

### Exact marker recreation operations

Starting from the immutable pilot copy, use only the allowed FreeCAD
`part_operations` tool:

```text
{"operation":"sphere","name":"REVIEW_ONLY__ANCHOR_CANDIDATE_A__FRONT","radius":5.0,"x":106.484329,"y":103.349472,"z":179.542068}
{"operation":"sphere","name":"REVIEW_ONLY__ANCHOR_CANDIDATE_B__REAR","radius":5.0,"x":82.255508,"y":234.494415,"z":205.475845}
```

### Next physical review

1. Rotate the current FreeCAD view with both white/blue marker spheres visible.
2. Confirm that A is acceptably near the front usable extreme and B near the
   rear usable extreme of the translucent panel.
3. Approve both centers or describe which marker must move and in which
   direction.
4. Do not infer flange approval from marker approval. After anchor approval,
   write and review the numeric flange design contract before modeling any
   connector.

## Anchor candidates V2 — awaiting review

The user requested that A/front move “towards the back a bit” and B/rear move
“to the front a bit.” Because no distance was specified, this review uses a
reversible `10.0 mm` step for each marker along its existing reviewed boundary.
No cross-boundary or screen-space movement was used.

- Current review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V2.FCStd`
- V1 remains preserved and unchanged for comparison.
- Checkpoint before movement: `before_anchor_adjustment_v2`.

### V2 coordinates

- A/front moved rearward by
  `(+2.704559, +9.546654, +1.243729) mm` to
  `(109.188889, 112.896126, 180.785797) mm`.
- B/rear moved forward by
  `(+4.837013, -8.484375, -2.149094) mm` to
  `(87.092522, 226.010040, 203.326752) mm`.
- Each marker is now `25.0 mm` inward from its corresponding boundary extreme.
- Direct center-to-center span: `117.435522 mm`.
- Owner-boundary path span: `126.805684 mm`.
- FreeCAD sphere-to-sphere surface clearance: `107.436 mm`, consistent with
  the center span minus two 5 mm marker radii.

### V2 validation

- Exactly the same three frozen `REFERENCE__` objects remain present.
- Exactly two `REVIEW_ONLY__` marker spheres remain present.
- FreeCAD center-of-mass measurements match the target coordinates to displayed
  precision.
- Both markers remain closed, valid solids.
- V2 `.FCStd` ZIP validation: PASS, size `69921` bytes.
- No flange, hole, cut, union, mirror, STL, G-code, or print release exists.

Exact relative move operations from V1:

```text
{"operation":"move","object_name":"REVIEW_ONLY__ANCHOR_CANDIDATE_A__FRONT","x":2.704559,"y":9.546654,"z":1.243729}
{"operation":"move","object_name":"REVIEW_ONLY__ANCHOR_CANDIDATE_B__REAR","x":4.837013,"y":-8.484375,"z":-2.149094}
```

Next review: rotate the V2 document with both selected marker spheres visible.
Approve both positions or request another marker-only movement. Anchor approval
still does not authorize flange geometry.

## Anchor candidates V3 — awaiting review

The user requested the same movement amount in the same direction once more.
V3 therefore applies another exact `10.0 mm` boundary-following step to each
V2 marker. No screen-space movement, flange geometry, or reference-object
change was made.

- Current review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V3.FCStd`
- V1 and V2 remain preserved and unchanged for comparison.
- Checkpoint before movement: `before_anchor_adjustment_v3`.

### V3 coordinates

- A/front moved rearward again by
  `(+2.704559, +9.546654, +1.243729) mm` to
  `(111.893448, 122.442780, 182.029526) mm`.
- B/rear moved forward again by
  `(+4.837013, -8.484375, -2.149094) mm` to
  `(91.929535, 217.525665, 201.177658) mm`.
- Each marker is now `35.0 mm` inward from its corresponding original boundary
  extreme.
- Direct center-to-center span: `99.025067 mm`.
- Owner-boundary path span: `106.805684 mm`.
- FreeCAD sphere-to-sphere surface clearance: `89.025 mm`, consistent with the
  center span minus two 5 mm marker radii.

### V3 validation

- Exactly the same three frozen `REFERENCE__` objects remain present.
- Exactly two `REVIEW_ONLY__` marker spheres remain present.
- FreeCAD center-of-mass measurements match the target coordinates to displayed
  precision.
- Both markers remain closed, valid solids with no reported self-intersection.
- V3 `.FCStd` ZIP validation: PASS, size `69881` bytes.
- No flange, hole, cut, union, mirror, STL, G-code, or print release exists.

Exact relative move operations from V2:

```text
{"operation":"move","object_name":"REVIEW_ONLY__ANCHOR_CANDIDATE_A__FRONT","x":2.704559,"y":9.546654,"z":1.243729}
{"operation":"move","object_name":"REVIEW_ONLY__ANCHOR_CANDIDATE_B__REAR","x":4.837013,"y":-8.484375,"z":-2.149094}
```

Next review: rotate the V3 document with both selected marker spheres visible.
Approve both positions or request another marker-only movement. Anchor approval
still does not authorize flange geometry.

## Right flange shape V1 — rejected by root gate

The user explicitly approved the V3 anchor positions with “Awesome LGTM” and
authorized the next step. One right-side, shape-only proposal was then built
around those exact anchors. No source reference, left-side geometry, hole,
cut, union, mirror, STL, G-code, or print-release state was changed.

- Proposal file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V1.FCStd`
- Preserved pre-proposal checkpoint:
  `before_proposed_right_flange_shape_v1`.
- Frozen V10 SHA-256 remains
  `cac7c0a1cfadfa0adbd469012b8c94b849b5f1d9a25488098c7e0baa533baa62`.
- Approved anchors remain A/front
  `(111.893448, 122.442780, 182.029526) mm` and B/rear
  `(91.929535, 217.525665, 201.177658) mm`.

### Shape contract and objects

- Four parametric `Part::Box` source solids: panel/head tabs at A and B.
- Each tab is `22 x 12 x 4 mm` and undrilled in this review bucket.
- Each pair retains the frozen `0.3 mm` mating gap.
- The objects are linked under
  `PROPOSED__RIGHT_FLANGE_SHAPE_V1`; source boxes are hidden to avoid duplicate
  display geometry.
- Named values are stored in
  `PROPOSED__RIGHT_FLANGE_PARAMETERS_V1`, including the deferred `3.4 mm` M3
  bore and the frozen root/edge gates.

Tab centers:

- A panel: `(104.543248, 124.697973, 180.702438) mm`.
- A head: `(106.904844, 124.500895, 177.079729) mm`.
- B panel: `(85.132711, 214.069102, 199.526038) mm`.
- B head: `(86.920905, 215.964224, 196.069035) mm`.

The A local axes are tangent
`(0.27045545, 0.95466518, 0.12437177)`, interior
`(-0.85095203, 0.29746947, -0.43288863)`, and across
`(-0.45026046, 0.01124268, 0.89282644)`. The B axes are tangent
`(-0.48370078, 0.84843820, 0.21490952)`, interior
`(-0.81416923, -0.34606928, -0.46622366)`, and across
`(-0.32118839, -0.40048546, 0.85816628)`. Both matrices pass the right-handed
determinant gate.

### Validation and failed gate

- Four proposed tabs are closed, valid solids: PASS.
- Reported tab centers match the target coordinates: PASS.
- A and B pair gaps are exactly `0.3000 mm`: PASS.
- Approved anchor span remains `99.025067 mm`, with each anchor `35.0 mm`
  inward from its original boundary extreme: PASS.
- Diagnostic root intersections were A/panel `73.5218 mm3`, A/head
  `144.5924 mm3`, B/panel `85.2299 mm3`, and B/head `105.7136 mm3`.
- A/panel versus the `80 mm3` minimum: **FAIL**.

The three frozen reference meshes were temporarily converted to separate
`VALIDATION_ONLY__` Part objects to obtain those diagnostic intersections.
FreeCAD reported the panel and upper-head conversions as invalid geometry, so
their volumes cannot clear a production gate. All three temporary conversion
objects were deleted after the check. The below-threshold A/panel result is
therefore treated conservatively as a hard hold, not rounded up or ignored.

### Exact shape recreation operations

Create each `22 x 12 x 4 mm` box at the origin listed below, then apply the
listed local X/Y/Z rotations in order:

```text
A panel origin = (107.574470939, 112.389353578, 180.146027588)
A head origin  = (109.936066933, 112.192275324, 176.523318218)
A rotations    = (-0.721443726, -26.760396045, 72.368343247) deg
B panel origin = (95.980811502, 207.613668030, 198.243042695)
B head origin  = (97.769006194, 209.508790129, 194.786039531)
B rotations    = (25.017324398, -18.734808918, 120.714694760) deg
```

Next action: obtain explicit approval for a tab-length change before replacing
V1. The recommended controlled V2 trial is `26 x 12 x 4 mm` for all four tabs,
with the approved anchors, depth, thickness, gap, offsets, and all frozen
workstreams unchanged. Re-run every root, collision, access, and shape gate
before presenting V2. Do not cut M3 holes until the shape bucket passes.

## Right flange shape V2 — 26 mm root pass, interference proof held

The user approved the recommended length change with “go.” V1 remains preserved
on disk and at FreeCAD checkpoint `completed_failed_flange_shape_v1`. The
active document was rolled back to the five-object checkpoint
`before_proposed_right_flange_shape_v1`, then saved as a separate V2 before
new objects were created.

- V2 proposal file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V2_26MM.FCStd`
- V1 preserved SHA-256:
  `5f513edb7a0078f40c0213c15a63a64c9765181132e9eb102c37806d7a3575f2`.
- V2 pre-proposal checkpoint:
  `before_proposed_right_flange_shape_v2`.
- V2 contains the same three frozen references and two approved V3 marker
  spheres, plus one parameter spreadsheet and one isolated four-component
  `PROPOSED__RIGHT_FLANGE_SHAPE_V2_26MM` assembly.

### Approved V2 contract

- Change only tab length from `22.0 mm` to `26.0 mm`.
- Retain `12.0 mm` depth, `4.0 mm` thickness, `0.3 mm` pair gap,
  `1.0 mm` shared interior offset, and `0.5 mm` moving-tab relief.
- Retain approved A/B anchors, tab centers, local frames, `99.025067 mm`
  anchor span, and `35.0 mm` inset from each original boundary extreme.
- Keep the `3.4 mm` M3 bore in the parameter sheet only; V2 remains undrilled.
- Preserve V10, both upper owners, exact ear, lower/rear ownership,
  reinforcement, C006, and aluminum V0.5.

Named values were verified in
`PROPOSED__RIGHT_FLANGE_PARAMETERS_V2_26MM!A1:C12`.

### Exact V2 creation operations

Create each `26 x 12 x 4 mm` Part box at the listed origin and apply local
X/Y/Z rotations in order:

```text
A panel origin = (107.033560039, 110.480023210, 179.897284054)
A head origin  = (109.395156034, 110.282944955, 176.274574684)
A rotations    = (-0.721443726, -26.760396045, 72.368343247) deg
B panel origin = (96.948213066, 205.916791624, 197.813223647)
B head origin  = (98.736407758, 207.811913723, 194.356220483)
B rotations    = (25.017324398, -18.734808918, 120.714694760) deg
```

Recalculated origins keep all four tab centers identical to V1:

- A panel: `(104.543248, 124.697973, 180.702438) mm`.
- A head: `(106.904844, 124.500895, 177.079729) mm`.
- B panel: `(85.132711, 214.069102, 199.526038) mm`.
- B head: `(86.920905, 215.964224, 196.069035) mm`.

### V2 validation

- Four proposed tabs are closed, valid solids with no self-intersections: PASS.
- Reported centers match the unchanged target coordinates: PASS.
- A and B pair gaps are exactly `0.3000 mm`: PASS.
- V2 FCStd ZIP validation: PASS, size `76449` bytes.
- Diagnostic root intersections: A/panel `86.8860 mm3`, A/head
  `164.5685 mm3`, B/panel `100.7237 mm3`, B/head `124.9342 mm3`;
  all exceed `80 mm3`.
- Ear diagnostic clearances: A/panel `27.4952 mm`, A/head `27.4965 mm`,
  B/panel `9.1285 mm`, B/head `13.2877 mm`.
- A/head to panel diagnostic clearance: `0.7071 mm`.
- B/panel to head diagnostic clearance: `0.0647 mm`.
- B/head to panel diagnostic clearance: `0.5994 mm`.
- A/panel tab versus head owner: **FAIL**, reported intersection
  `1.3988 mm3`.

The root and interference numbers use temporary `VALIDATION_ONLY__`
mesh-to-Part conversions. As in V1, FreeCAD reports the panel and upper-head
conversions as invalid geometry, so those numbers are diagnostic rather than
production proof. All temporary conversions were deleted after measurement.
The A/panel overlap is treated as a conservative hard hold; the tiny B/panel
clearance is also inadequate evidence for physical tolerance.

### Current hold and next action

The approved `26 mm` length fixes the V1 root-volume problem, but V2 cannot
pass the zero-unintended-interference, motion, or physical-clearance gates
against invalid reference solids. Do not move anchors, trim tabs, drill holes,
mirror, integrate, or print from V2.

The next independent work bucket is to create shape-preserving, valid Part
reference solids for the three pilot references from the frozen upstream
geometry, then rerun the V2 root and interference checks without changing the
proposal. That validation-baseline work requires explicit user authorization.

## Right flange shape V3 — review-display correction only

The user correctly reported that the visible flange in V2 appeared far from
the translucent-panel boundary. Numeric inspection found a review-display
defect: each visible `App::Link` component in the V2 assembly had lost the
placement of its source box and was stacked at center of mass
`(13.00, 6.00, 2.00) mm`. That floating geometry was not at an approved anchor
and must not be used for spatial review.

V2 is preserved unchanged with SHA-256
`f605ef90d425868fec685137295cd79c0767b5a90d088c00e9688b55b2b7a359`.
The corrected display-only review copy is:

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V3_DISPLAY_FIXED.FCStd`
- V3 SHA-256:
  `9df75d1a0a39d8bb1262ed9e63713025529813ca9d8065252281e689ec30967b`
- FreeCAD ZIP validation: PASS, current size `74414` bytes.

V3 does not move, resize, cut, drill, union, mirror, or integrate any flange.
It hides the four broken assembly links and displays the four correctly placed
source solids directly. Their measured centers remain:

- A panel: `(104.54, 124.70, 180.70) mm`.
- A head: `(106.90, 124.50, 177.08) mm`.
- B panel: `(85.13, 214.07, 199.53) mm`.
- B head: `(86.92, 215.96, 196.07) mm`.

The numeric contract is unchanged: four undrilled `26 x 12 x 4 mm` tabs,
`0.3 mm` pair gap, approved A/B anchors, and `99.025067 mm` anchor span. The
file opens in a panel-owner-only evidence view so both opposite-side locations
can be related to the translucent panel. To inspect the other owner, hide
`REFERENCE__right_translucent_panel` and show
`REFERENCE__right_upper_head_owner`; the same four source solids remain
visible. Owner-only panel and head renders were captured in the review session.

Rejected review method: do not use the four `...001` assembly-link components
for placement evidence. Their link placements are invalid even though their
source geometry remains correct.

Next physical review: open V3, confirm that the two paired locations are near
opposite panel boundaries in the panel-owner view, then toggle to the
head-owner view and confirm both head-side roots. Do not infer hole,
integration, mirror, or print approval from this display correction.

## Right flange shape V4 — rejected invalid-reference conversion

After the user approved the V3 display correction and authorized the next
bucket, validation began without changing the four approved tabs. The contract
for this bucket was zero movement or resizing of the tabs and anchors, frozen
`REFERENCE__` objects untouched, and acceptance only if separately named
validation copies became closed valid Part solids without changing the frozen
reference envelope.

Preserved files:

- Pre-validation checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V4_PRE_VALIDATION_CHECKPOINT.FCStd`
  SHA-256 `7e993040153bba3785b5be66108c1c07a6e7f729b0372ab7fbbfd2d777bef5a6`,
  ZIP validation PASS, size `74781` bytes.
- Rejected diagnostic:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V4_REJECTED_INVALID_REFERENCE_CONVERSION.FCStd`
  SHA-256 `846d336770b1fa1e9594fc0bfac43d88419a25e39d473e220d27660ef1462e57`,
  ZIP validation PASS, size `677435` bytes.

### Validation results

Each original STL was imported under a `VALIDATION_ONLY__` name. Read-only
validation reproduced the frozen source defects. Automatic repair was applied
only to those copies. In all three cases FreeCAD reported that hole filling
failed (`fillupHoles: function takes at least 1 argument`) and the converted
Part remained open and invalid:

- Translucent panel: imported `71` points / `142` facets; repaired copy
  `71` points / `139` facets; converted Part `139` faces, `1` shell, volume
  `14179.89 mm3`; closed FAIL, valid FAIL.
- Upper-head owner: imported `1583` points / `3102` facets; repaired copy
  `1391` points / `2282` facets; converted Part `2010` faces, `46` shells,
  volume `700971.45 mm3`; closed FAIL, valid FAIL.
- Ear collision context: imported `177` points / `362` facets; repaired copy
  `171` points / `337` facets; converted Part `322` faces, `3` shells, volume
  `24640.53 mm3`; closed FAIL, valid FAIL.

The reported bounding boxes remained aligned with the frozen manifest at the
tool's displayed precision, but bounding-box agreement cannot override invalid
topology. The automatic-repair result is rejected and must not be substituted
for the frozen references or used to clear Boolean root/interference gates.

Exact FreeCAD operation sequence for each copy:

```text
mesh_operations import_mesh from the frozen reference STL as VALIDATION_ONLY__*
mesh_operations validate_mesh auto_repair=false
mesh_operations validate_mesh auto_repair=true
mesh_operations mesh_to_solid tolerance=0.01
measurement_operations check_solid
part_operations check_geometry
measurement_operations get_bounding_box
geometric_verification verify_no_self_intersection
```

V3 was reopened as the active review after preserving the rejected diagnostic.
No tab, anchor, hole, owner, mirror, union, STL, G-code, or aluminum geometry
changed. M3 holes remain blocked.

Next action requires a new explicit bucket: repair the panel and upper-head
topology at their upstream source, one owner at a time, while proving the
accepted exterior and aluminum workstream remain unchanged. Then regenerate
valid pilot references and rerun root, interference, motion, and hardware
access checks before drilling.

## Right-panel topology repair V1 — user-approved topology reference

The user explicitly authorized an isolated right translucent-panel upstream
topology repair. The frozen V10 blend was not edited. A separate generator
duplicates only `EAR10_ACCEPTED_V3_BODY__right`, preserves every existing
world-space vertex coordinate, and replaces its 35 polygon faces with 142
explicit triangles.

### Numeric contract

- Existing vertex displacement: exactly `0.0 mm`.
- Bounding-box change: exactly `0.0 mm`.
- Required connected components: `1`.
- Required boundary edges: `0`.
- Required non-manifold edges: `0`.
- No change to flanges, anchors, head, ear, left side, lower/rear ownership,
  reinforcement, C006, eyes, or aluminum V0.5.
- Acceptance requires a valid closed FreeCAD Part and a clean mesh re-export.

Tracked regeneration inputs:

- `config/right-panel-topology-repair-review-v1.json`
- `source/generate_right_panel_topology_repair_review_v1.py`

Review outputs:

- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/CAT_HEAD_RIGHT_PANEL_TOPOLOGY_REPAIR_REVIEW_V1.blend`
  SHA-256 `c6db282dbab74997b5bf1334e88c6e06cd655883c2b3f42c45512112fed0478c`.
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/CAT_HEAD_RIGHT_PANEL_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`
  SHA-256 `9b53d39d5e6ac472213c0270230bc0705be84f14cbef0efc3abb9f9b5ff490d5`,
  ZIP validation PASS, size `116797` bytes.
- `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/PROPOSED__RIGHT_TRANSLUCENT_PANEL__VALID_PART_REEXPORT_V1.stl`
  SHA-256 `ccb5542810558028383c3a858c92806ec701088217f2249a65451c03e4c571c8`.
- Blender validation: `right-panel-topology-repair-v1/validation.json`.
- FreeCAD validation: `right-panel-topology-repair-v1/freecad-validation.json`.

### Validation results

- Frozen V10 SHA-256 remains
  `cac7c0a1cfadfa0adbd469012b8c94b849b5f1d9a25488098c7e0baa533baa62`.
- V3 flange-review SHA-256 remains
  `9df75d1a0a39d8bb1262ed9e63713025529813ca9d8065252281e689ec30967b`.
- Aluminum V0.5 SHA-256 remains
  `6326b211e4eef8c87a2b17687e2d68406682d21a6fa7c81ad52c8a1b9e713c79`.
- Source object fingerprint before/after: identical.
- Existing vertex coordinates and exact bounds: identical.
- Blender topology: `71` vertices, `213` edges, `142` triangles, one
  component, zero boundary and non-manifold edges: PASS.
- The direct Blender STL triggered FreeCAD's mesh-level self-intersection
  heuristic, so it is not the clean handoff artifact.
- Converted FreeCAD Part: valid, closed, one solid/one shell, `142` faces,
  `213` edges, `71` vertices, volume `14122.19 mm3`: PASS.
- Dedicated Part no-self-intersection verification: PASS.
- FreeCAD Part re-export: `71` points, `142` facets, manifold, watertight,
  zero self-intersections: PASS.
- A panel-tab root: `86.8860 mm3` versus `80 mm3`: PASS.
- B panel-tab root: `99.8054 mm3` versus `80 mm3`: PASS.
- A head-tab to panel clearance: `0.7071 mm`.
- B head-tab to panel clearance: `0.5994 mm`.

Exact regeneration command:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_panel_topology_repair_review_v1.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-panel-topology-repair-review-v1.json
```

The FreeCAD review opens with the valid proposed panel solid highlighted in
head/ear context. Toggle the proposed solid off and
`REFERENCE__right_translucent_panel` on to compare the frozen display; their
accepted exterior vertices and bounds are identical.

The user visually approved this isolated panel topology reference on
2026-08-08. This is not integration or print approval. Full interference,
motion, driver/washer/nut access, holes, mirroring, integration, and printing
remain held.

## Right upper-head topology repair — V1/V2 rejected, V3 user-approved

The next isolated bucket repairs only the frozen V10 `right_upper_head`
topology so FreeCAD can use it as a reliable collision and root reference.
No accepted exterior, panel, flange, ear, left-side, lower/rear,
reinforcement, C006, eye, or aluminum geometry was modified.

### Rejected variants

- V1 triangulated the complete source with Blender BEAUTY/BEAUTY while
  preserving all `1587` vertex coordinates and bounds. The result retained
  `2` non-manifold edges and was rejected before FreeCAD integration. An
  in-memory EAR_CLIP comparison was worse at `7` non-manifold edges.
- V2 preserved all `42` existing connected components separately without
  changing vertices or faces. Blender source-topology checks passed, but
  FreeCAD rejected components `C001`, `C002`, `C003`, `C009`, `C013`, and
  `C024`. Their converted Parts were closed but invalid; C001 was explicitly
  unorientable. No automatic repair, compound approval, or integration was
  performed.

### V3 numeric contract

- Source: frozen V10 `right_upper_head`, SHA-256
  `cac7c0a1cfadfa0adbd469012b8c94b849b5f1d9a25488098c7e0baa533baa62`.
- Source object fingerprint before/after:
  `8647f88d822573db2ce3bdb7124fac4fa144bf5445f482f791b255306c025c4e`.
- Preserve all `42` existing connected components; do not union them.
- Weld tolerance: at most `0.00001 mm`.
- Remove exactly four redundant vertices: two exact-coordinate duplicates in
  C001 and two C002 pairs separated by `0.000003814697265625 mm`.
- Maximum retained-vertex displacement: exactly `0.0 mm`.
- Bounding-box change: exactly `0.0 mm`.
- Deterministic triangulation: Blender `BEAUTY/BEAUTY`.
- Every repaired component must have zero boundary and non-manifold edges and
  become a closed valid FreeCAD Part with no self-intersection.
- No production union, mirror, holes, fabrication export, slicing, or print
  release.

Tracked regeneration inputs:

- `config/right-upper-head-deterministic-topology-repair-review-v3.json`
- `source/generate_right_upper_head_deterministic_topology_repair_review_v3.py`

Current review outputs:

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/CAT_HEAD_RIGHT_UPPER_HEAD_TOPOLOGY_REPAIR_REVIEW_V3.FCStd`,
  SHA-256 `070d9e33420d4e0a8d0a5732e94f8446821ace7d03766d9dabea45b204242e15`,
  ZIP validation PASS.
- Blender:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/CAT_HEAD_RIGHT_UPPER_HEAD_TOPOLOGY_REPAIR_REVIEW_V3.blend`,
  SHA-256 `12b95f6a501e7da9f13ba8589410e04b86aa536b351a825f9ec515182da79723`.
- Blender validation:
  `right-upper-head-deterministic-topology-repair-v3/validation.json`.
- FreeCAD validation:
  `right-upper-head-deterministic-topology-repair-v3/freecad-validation.json`.
- Context evidence:
  `right-upper-head-deterministic-topology-repair-v3/review/01-right-upper-head-context-isometric.png`,
  SHA-256 `ab1bbbb8c8d4f475a047c5a728d41f4522a0c9b69759e8cc1b383facf3fe95c4`.
- Isolated evidence:
  `right-upper-head-deterministic-topology-repair-v3/review/02-right-upper-head-isolated-isometric.png`,
  SHA-256 `510009aebb9c834d240a24b738a41f367d9638757b4ebdb093527f4b10e482f6`.

### V3 validation results

- Blender repair gates: PASS. Four redundant vertices removed, all retained
  coordinates unchanged, exact bounds preserved, `42` components preserved,
  and every component has zero boundary/non-manifold edges.
- FreeCAD component gates: all `42/42` converted Parts are closed, valid, and
  pass the dedicated no-self-intersection check. C001 retains a mesh-level
  heuristic warning but its decisive Part checks pass: one valid closed solid,
  `1859` faces, `2910` edges, `1011` vertices, volume `75969.39 mm3`.
- Non-unioned validation compound: valid and closed; `42` solids, `42` shells,
  `2757` faces, `4304` edges, `1583` vertices, volume `150643.54 mm3`.
- Exact compound bounds: X `[-30.0, 126.93900299072266]`, Y
  `[42.84299850463867, 269.3445129394531]`, Z
  `[109.75635528564453, 268.1520080566406]` mm: unchanged from source.
- A head-tab root: `164.5685 mm3` versus `80 mm3`: PASS.
- B head-tab root: `124.9343 mm3` versus `80 mm3`: PASS.
- Existing A panel-side tab to repaired head: `1.3988 mm3` interference:
  HOLD for a later connector-adjustment bucket; V3 does not alter it.
- B panel-side tab to repaired head: `0.0647 mm` clearance.
- Repaired panel to repaired head: `0.0353 mm` clearance.

Exact regeneration command:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_upper_head_deterministic_topology_repair_review_v3.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-upper-head-deterministic-topology-repair-review-v3.json
```

### Approval recorded and next controlled bucket

On 2026-08-08 the user visually reviewed V3 and approved it: “LGTM - don't
visually see anything off.” This approves only the isolated right upper-head
topology reference and its validated non-unioned compound. It does not approve
the known A panel-side tab overlap or authorize a production union, left-side
mirror, integration, holes, fabrication export, slicing, or printing.

The next independent prerequisite is an isolated right-ear topology repair so
the unchanged ear can become a valid collision and motion reference. That must
be a new one-side proposal with its own numeric contract and review evidence.
The A panel-tab adjustment remains a later connector bucket after all receiving
owners are valid.

The ear source remains invalid and cannot yet clear motion/interference gates.
Left-side mirroring, integration, hardware access, holes, aluminum changes,
fabrication export, slicing, and printing remain held.

## Right-ear topology repair V1 — user-approved topology reference

This isolated bucket changes only the tessellation representation of frozen
V10 object `right_ear`. It preserves the two existing connected source
components, every one of their `177` world-space vertex coordinates, and the
exact source bounds. The frozen V10 blend, approved panel, approved upper-head
V3 compound, connector tabs, eye work, lower/rear work, reinforcements, C006,
and aluminum V0.5 were not changed.

On 2026-08-08 the user visually reviewed this isolated right-ear reference and
approved it with “LGTM.” This approval accepts only the unchanged right-ear
topology reference and its validated non-unioned compound. It does not resolve
the inherited two-component overlap or authorize mirroring, integration,
connector adjustment, holes, aluminum changes, fabrication export, slicing, or
printing.

### Numeric contract

- Source and proposal vertices: `177`; no vertices added or removed.
- Existing vertex displacement and weld tolerance: exactly `0.0 mm`.
- Source and proposal connected components: exactly `2`; no production union.
- Deterministic triangulation: Blender `BEAUTY/BEAUTY`, `362` total triangles.
- Bounding-box change: exactly `0.0 mm`.
- Exact bounds: X `[55.797000885009766, 151.91549682617188]`, Y
  `[124.44599914550781, 210.15899658203125]`, Z
  `[187.2570037841797, 330.0]` mm.
- Acceptance requires both component meshes and Parts plus their non-unioned
  validation compound to be closed, valid, and self-intersection-free.
- No automatic mesh repair, mirror, integration, connector adjustment, holes,
  aluminum change, fabrication export, slicing, or print release.

Tracked regeneration inputs:

- `config/right-ear-deterministic-topology-repair-review-v1.json`
- `source/generate_right_ear_deterministic_topology_repair_review_v1.py`

Current review outputs:

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/CAT_HEAD_RIGHT_EAR_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`,
  SHA-256 `132c4906e69a356b4e834b196d001763bcd9b83ea6820f59df61968368b87d3e`,
  ZIP validation PASS, size `1600837` bytes.
- Blender:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/CAT_HEAD_RIGHT_EAR_TOPOLOGY_REPAIR_REVIEW_V1.blend`,
  SHA-256 `3da526146174aa537dc887098e300f2fce8922503b8973df7d97253fcb87dbb6`.
- Blender validation:
  `right-ear-deterministic-topology-repair-v1/validation.json`.
- FreeCAD validation:
  `right-ear-deterministic-topology-repair-v1/freecad-validation.json`.
- Context evidence:
  `right-ear-deterministic-topology-repair-v1/review/01-right-ear-context-isometric.png`,
  SHA-256 `960ce768a21e7c31dfd17119a28e77835d4e8b583170297a6691f69e63bb6a97`.
- Isolated evidence:
  `right-ear-deterministic-topology-repair-v1/review/02-right-ear-isolated-front.png`,
  SHA-256 `c82dd35a5d8fd4fa42a17f09d920f310df7ed4f84ea350eadbc7fdde7df085e5`.

### Validation results

- Blender gates: PASS. Source fingerprint before/after remains
  `884fabfca43dfa27dad15304bde2b5411b77df770c241ef6017eef98fc9c0de5`;
  all coordinates and exact bounds are unchanged.
- C001 mesh: `169` points, `350` facets; validation PASS without auto-repair.
  FreeCAD Part: one closed valid solid, no self-intersection, `334` faces,
  `509` edges, `169` vertices, volume `17512.81 mm3`.
- C002 mesh: `8` points, `12` facets; validation PASS without auto-repair.
  FreeCAD Part: one closed valid solid, no self-intersection, `11` faces,
  `17` edges, `8` vertices, volume `908.74 mm3`.
- Non-unioned compound `PROPOSED__RIGHT_EAR__VALIDATION_COMPOUND_V1`:
  closed and valid with no self-intersection; `2` solids, `2` shells, `345`
  faces, `526` edges, `177` vertices, volume `18421.55 mm3`.
- The two original source components overlap by `185.0521 mm3`. This inherited
  relationship is preserved explicitly; the topology pass did not move,
  reshape, or union them.
- Ear to approved panel: no interference; `0.0761 mm` clearance.
- Ear to approved upper head: no volumetric interference; exactly touching at
  the inherited source seams.
- Ear to the four approved A/B panel/head tabs: no interference; minimum gaps
  are `27.4952`, `27.4965`, `9.1285`, and `13.2877 mm` respectively.

Exact regeneration command:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_ear_deterministic_topology_repair_review_v1.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-ear-deterministic-topology-repair-review-v1.json
```

### Approval recorded and next controlled bucket

The approved review object is
`PROPOSED__RIGHT_EAR__VALIDATION_COMPOUND_V1`. The accepted evidence covers its
saved right panel/head context, unchanged placement and bounds, inherited root
seam contact, and isolated surface appearance.

The next independent bucket is the isolated right-side A panel-tab adjustment:
remove the measured `1.3988 mm3` overlap with the now-valid right upper-head
reference while preserving the approved panel, upper-head, and ear owners.
That change requires a new numeric contract and review evidence before any
integration. The inherited `185.0521 mm3` overlap between the two ear source
components also remains explicit and unresolved. Left mirroring, hardware
access, holes, aluminum changes, fabrication export, slicing, and printing
remain held.

## Right A panel-tab local clearance review V1 — awaiting user approval

This bucket changes only the isolated right A panel-side tab. The approved A
anchor, A head tab, both B tabs, valid panel, valid upper-head V3 compound,
valid ear V1 compound, frozen V10, left side, lower/rear ownership,
reinforcements, eyes, C006, and aluminum V0.5/M2 remain unchanged.

### Numeric contract and approved datums

- Approved A anchor:
  `REVIEW_ONLY__ANCHOR_CANDIDATE_A__FRONT` at
  `(111.893448, 122.442780, 182.029526) mm`.
- A remains `35.0 mm` inward from its original boundary extreme; unchanged A/B
  anchor span is `99.025067 mm`.
- Accepted tab envelope remains `26 x 12 x 4 mm`; A head tab and its mating
  face are fixed.
- Required A pair gap: `0.300 mm`.
- Required actual upper-head clearance: at least `0.400 mm`.
- Required panel-root overlap: at least `80 mm3`.
- Future `3.4 mm` M3 bore requires at least `3.5 mm` modeled edge material,
  but no hole is created or approved in this shape bucket.
- Approved local across axis:
  `(-0.45026046, 0.01124268, 0.89282644)`.

Tracked contract:

- `config/right-a-panel-tab-local-clearance-review-v1.json`

Current review outputs:

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-panel-tab-clearance-review-v1/CAT_HEAD_RIGHT_A_PANEL_TAB_CLEARANCE_REVIEW_V1.FCStd`,
  SHA-256 `da583a49deac7cf7cd322e29081ed727b922b5b1104efb9e92138c9412789236`,
  ZIP validation PASS, size `3579369` bytes.
- Validation:
  `right-a-panel-tab-clearance-review-v1/freecad-validation.json`.
- Evidence images:
  `review/01-right-side-owner-context-isometric.png`,
  `review/02-a-panel-tab-and-anchor-isolated.png`,
  `review/03-a-tab-pair-close-up.png`,
  `review/04-a-tab-pair-unobstructed-close-up.png`, and
  `review/05-c001-interior-section-context.png`.

### Rejected trials

- V1 used a `0.4 mm` C001 sweep along the approved across axis. It removed the
  original `1.3988 mm3` collision but produced only `0.0850 mm` actual head
  clearance, so it failed the `0.400 mm` gate.
- V2 used a `2.0 mm` sweep. It produced `0.4251 mm` head clearance and retained
  `80.4737 mm3` root overlap, but the required future M3 edge envelope
  intersected the relief by `0.0511 mm3`. It was rejected rather than rounding
  away the failure.

### V3 proposal and validation

`PROPOSED__RIGHT_A__PANEL_TAB__LOCAL_RELIEF_1P9_SWEEP_V3` is a separate copy of
the accepted A panel tab cut only by a copy of actual valid upper-head C001
translated `1.9 mm` along the approved across axis, or
`(-0.855494874, 0.021361092, 1.696370236) mm`.

- Closed valid solid with no self-intersection: PASS.
- One solid, one shell, `8` faces, `18` edges, `12` vertices: PASS.
- Final volume `1224.13 mm3`; local material removed `23.87 mm3`.
- Upper-head interference: none; clearance `0.4039 mm`: PASS.
- Panel-root overlap `81.4577 mm3`: PASS.
- A head-tab mating gap unchanged at `0.3000 mm`: PASS.
- Ear interference: none; clearance `27.5188 mm`: PASS.
- New A tab to B panel/head tabs: no interference; `64.9019` and
  `65.6319 mm` clearances.
- A head tab to panel remains `0.7071 mm`; B head tab to panel remains
  `0.5994 mm`.
- The unchanged B panel tab remains only `0.0647 mm` from the valid upper head;
  it is explicitly outside this A-only bucket.
- The V3 tab is a strict material-removal result from the prior 26 mm V2 tab,
  so it cannot worsen that tab's envelope. However, V2 never passed a full
  valid-owner insertion/removal motion gate. No 41-sample motion pass is
  claimed here; full motion and access approval remain held.

The existing future A M3 axis misses the `3.5 mm` edge-material gate: its
required radius-`5.2 mm` envelope overlaps the V3 relief by `0.0327 mm3`. A
validation-only axis candidate shifted `0.12 mm` farther along the approved
interior direction clears the relief by `0.0085 mm`. That is feasibility
evidence only. No hole or hardware change is included; the datum requires a
separate user-approved hole bucket.

### Exact controlled recreation

No arbitrary Python, macro, or headless FreeCAD command is authorized. In a
clean copy of the approved right-ear V1 review, use the allowlisted FreeCAD GUI
operations to:

1. insert a separate shape copy of
   `PROPOSED__RIGHT_A__PANEL_TAB__V2_26MM_SHAPE_ONLY`;
2. insert a separate shape copy of
   `PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C001_SOLID_V3` translated
   `(-0.855494874, 0.021361092, 1.696370236) mm`;
3. cut the tab copy by that translated C001 copy and name the result
   `PROPOSED__RIGHT_A__PANEL_TAB__LOCAL_RELIEF_1P9_SWEEP_V3`; and
4. rerun the solid, self-intersection, root, gap, head, ear, sibling-tab, and
   future-hole-envelope checks in `freecad-validation.json`.

### Next physical review

Open the FreeCAD file in the current output above. Review the saved opaque
right panel/head/ear context first. Then hide the context owners and inspect
`PROPOSED__RIGHT_A__PANEL_TAB__LOCAL_RELIEF_1P9_SWEEP_V3` with the unchanged A
head tab from both ends and from the interior. Approval applies only to the
local V3 shape. The `0.12 mm` future hole-datum candidate, B-tab clearance,
integration, mirror, aluminum, fabrication export, slicing, and printing all
remain held.

## Right A M3 hole-axis review V1 — user-approved drilled pair

The user visually approved the V3 right-A panel-tab relief and later approved
the drilled pair with “Holes are OK.” The accepted owners and tab shapes remain
unchanged. Only proposal copies receive the common M3 bore.

- Review file:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-m3-hole-axis-review-v1/CAT_HEAD_RIGHT_A_M3_HOLE_AXIS_REVIEW_V1.FCStd`
- SHA-256:
  `ea76555c39aa34429e2bbcc38bbc0b8f2d9f14a27b43899df754da2a11ab13d4`
- FreeCAD ZIP validation: PASS.
- Contract:
  `config/right-a-m3-hole-axis-review-v1.json`.
- Approved proposal objects:
  `PROPOSED__RIGHT_A__PANEL_TAB__M3_BORE_MINUS_4P5_V2` and
  `PROPOSED__RIGHT_A__HEAD_TAB__M3_BORE_MINUS_4P5_V2`.

The bore center is `(104.4048820139, 120.3391366839, 178.2794638319) mm`.
It retains the validated `0.12 mm` inward correction and moves `-4.5 mm`
along the approved tab tangent. Both drilled tabs are closed valid solids with
no self-intersection, retain the `0.3000 mm` mating gap, and retain owner-root
overlaps of `81.46 mm3` and `164.57 mm3`. Both radius-`5.2 mm` edge
envelopes are contained in the accepted tab shapes.

Rejected trials are preserved as review evidence. The original shifted axis
collided with the head-side washer. Tangent trials at `-3.0`, `-4.0`, and
`-4.25 mm` retained measurable washer collisions. The `-4.5 mm` position is
the first zero-collision washer position. A user-authorized `-4.5` through
`-7.5 mm` sweep showed that no position provides a straight 10 mm-diameter,
15 mm-long axial tool path on either side. Exact separated hardware envelopes
at `-4.5 mm` clear: the low-profile panel-side M3 head by `0.9931 mm` and
the head-side M3 nyloc by `0.5137 mm`.

Tool access remains a release hold. Approval covers the drilled-pair placement
and bore shape, not a ball-end hex-key or thin-open-wrench approach. Right B,
mirror, integration, full-head validation, fabrication export, slicing, and
ASA printing remain held.

Exact recreation uses only allowlisted FreeCAD GUI operations: insert separate
copies of the approved V3 panel tab and V2 head tab, insert two copies of the
prior 3.4 mm bore cutter, move both cutters by
`(-1.217049525, -4.29599331, -0.559672965) mm`, and cut only the proposal
copies. No source owner is cut or modified.

## Right B panel-tab local-clearance review V1 — user visually approved

The right-B shape-only bucket preserves the approved B anchor, unchanged B
head tab, `26 x 12 x 4 mm` tab envelope, `0.3000 mm` pair gap, approved
right-A drilled pair, all owners, the left side, and aluminum V0.5-M2. Only a
separate proposal copy of the B panel tab was relieved against the actual
valid right upper-head C001 component.

Current review output:

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-panel-tab-clearance-review-v1/CAT_HEAD_RIGHT_B_PANEL_TAB_CLEARANCE_REVIEW_V1.FCStd`
- SHA-256:
  `e27b49f52cf7f399bc5b3cb495e039809353abdd0724407588544cba7e0ea5cd`
- FreeCAD ZIP validation: PASS, size `4985227` bytes.
- Contract and validation:
  `config/right-b-panel-tab-local-clearance-review-v1.json`.
- Preserved pre-change checkpoint:
  `before_right_b_panel_tab_clearance_v1`.

The accepted source B panel tab initially had only `0.0647 mm` clearance to
`PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C001_SOLID_V3`. A `0.5 mm`
across-axis cutter sweep was rejected because the actual oblique-edge gap was
only `0.1232 mm`, below the `0.4000 mm` gate. The current proposal
`PROPOSED__RIGHT_B__PANEL_TAB__LOCAL_RELIEF_1P9_SWEEP_V1` uses a `1.9 mm`
sweep with translation `(-0.610257941, -0.760922374, 1.630515932) mm`.

Validation results:

- Actual clearance to the valid upper-head compound and C001: `0.4450 mm`:
  PASS.
- Panel-root overlap: `94.72 mm3` versus `80.00 mm3`: PASS.
- B pair gap: `0.3000 mm`, unchanged: PASS.
- Ear clearance: `9.1285 mm`: PASS.
- Clearance to the approved A panel tab: `64.9019 mm`: PASS.
- Result volume: `1229.92 mm3`; removed volume: `18.08 mm3`.
- One closed valid solid and no self-intersection: PASS.

Exact recreation uses the official FreeCAD GUI and allowlisted operations:
open the approved A M3 source file; insert copies of the accepted B panel tab
and valid C001; move the C001 copy by
`(-0.610257941, -0.760922374, 1.630515932) mm`; cut that moved copy from the
B panel-tab copy; then rerun the clearance, root-common, solid, and
self-intersection checks recorded above. No arbitrary macro or headless
FreeCAD command is used.

The saved default view isolates the relieved panel tab (selected) and the
unchanged B head tab. For owner context, show
`PROPOSED__RIGHT_TRANSLUCENT_PANEL__TRIANGULATED_V1_SOLID`,
`PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__C001_SOLID_V3`, and
`PROPOSED__RIGHT_EAR__VALIDATION_COMPOUND_V1`; hide them again for the clean
pair close-up.

The user visually approved this relieved B shape on 2026-08-08. The selected
legacy small upper-head projection removal was then visually approved on
2026-08-09, so the B hole/fastener/access bucket is now unblocked. No B hole,
production union, mirror, aluminum change, fabrication export, slicing, or ASA
print release is authorized yet.

## Right upper-head selected legacy small-flange removal review V1 — user visually approved

The user selected
`PROPOSED__RIGHT_UPPER_HEAD__VALIDATION_COMPOUND_V3.Face1668` and authorized an
isolated proposal to remove that old small internal projection. The accepted
V3 upper-head source remains unchanged. A separate C001 copy was cut using the
numeric `12.4 x 2.4 x 5.3 mm` contract while retaining a `1.8 mm` exterior
wall; only that modified C001 copy was substituted into a separate 42-part
validation compound.

- Review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/CAT_HEAD_RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1.FCStd`
- Contract:
  `config/right-upper-head-legacy-small-flange-removal-review-v1.json`
- Dedicated checkpoint:
  `RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1_CHECKPOINT_2026-08-08.md`
- FCStd SHA-256:
  `9d18d60dc7db24c97fd7931fdda24c87bea546309d68eef325f62bae9ad4731e`.
- FCStd ZIP validation: PASS, `7999704` bytes.

The complete proposal is valid, closed, and self-intersection-free with 42
solids. Its bounding box is unchanged. The approved B head root remains
`124.93 mm3`; the relieved B panel tab remains clear by `0.445 mm`; the
translucent panel remains non-interfering at `0.0353 mm`. Aluminum V0.5-M2 and
every other workstream are frozen.

On 2026-08-09 the user visually approved this isolated removal with
“lgtm go next.” Approval applies only to the selected Face1668 projection
removal. The next review is the existing right-A short heat-set-insert and
25-degree tool-access contract. No integration, mirror, aluminum edit,
fabrication export, slicing, or ASA print release is authorized.

## Right A tool-access audit V1 — user-approved hardware contract

This independent bucket preserves the user-approved A panel-tab relief, common
M3 hole axis, and panel tab. It audits access on the actual approved axis and
proposes replacing only the head-side nyloc contract with a short heat-set
insert. No owner shell, B proposal, left-side geometry, aluminum, lower/rear,
reinforcement, eye, or C006 workstream changed.

Current review output:

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`
- SHA-256:
  `31b304cc9bf7de9dba330c5b1d70f3c30d969b72c12e836b3af6a2f0bbd511a3`
- FreeCAD ZIP validation: PASS, size `5050047` bytes.
- Contract and validation:
  `config/right-a-tool-access-audit-v1.json`.
- Preserved pre-change checkpoint:
  `before_right_a_tool_access_axis_audit_v1`.

The previously saved 10 mm panel-side tool cylinder is displaced `3.0 mm`
along negative tangent from the final approved hole axis. A rebuilt 10 mm
straight path on the correct axis still fails, intersecting the translucent
panel by `204.5764 mm3`. A conservative 3.4 mm-diameter straight shaft also
fails by `5.0725 mm3`.

The passing panel-side path is a 3.4 mm-diameter, 15 mm-long shaft envelope at
`25 degrees` along the positive approved interior direction. Object
`VALIDATION_ONLY__RIGHT_A__PANEL_BALL_HEX_25DEG_INWARD_V1` clears the
translucent panel by `2.1211 mm`, upper head by `7.7887 mm`, ear by
`40.2087 mm`, and approved panel tab by `1.4404 mm`. The ball tip contacts
the low-profile screw socket intentionally. Bondhus states that its standard
long-arm ball end operates at a 25-degree angle.

A correctly centered 8 mm-diameter thin socket still intersects the upper head
by `121.2826 mm3`, so the head-side nyloc remains impractical. The proposed
replacement is an M3 x 3 mm short heat-set insert installed from the mating
side before assembly, driven by an M3 x 8 low-profile socket screw and the
existing 7 mm OD x 0.8 mm washer from the panel side.

The final V3 insert cavity is `4.25 mm` diameter x `3.0 mm` deep and starts
`0.2 mm` behind the mating face. It leaves a closed `0.8 mm` exterior wall
and provides calculated `2.7 mm` thread engagement with M3 x 8. The complete
radius-`5.625 mm` cavity envelope is contained, proving `3.5 mm` radial
edge material. The cavity remains `1.3536 mm` from the valid upper head.

Validation of
`PROPOSED__RIGHT_A__HEAD_TAB__M3X3_SHORT_INSERT_RECESSED_V3`:

- closed valid solid and no self-intersection: PASS;
- head-root overlap `164.57 mm3` versus `80.00 mm3`: PASS;
- pair gap `0.3000 mm`, unchanged: PASS;
- result volume `1196.36 mm3`.

Rejected evidence is preserved: the straight 10 mm and 3.4 mm paths, the
25-degree negative-interior path, the 8 mm thin socket, the outer-face insert
with only 1.9 mm M3 x 8 engagement, and the flush mating-face cavity with a
`1.4972 mm3` geometric protrusion.

Exact recreation uses only official FreeCAD GUI allowlisted operations.
Construct the tool cylinders on the approved axis and the 25-degree interior
direction recorded in the JSON contract. Insert a copy of the approved drilled
head tab, subtract the V3 4.25 mm x 3 mm cavity at
`(105.9132545549, 120.3014737059, 175.2884952579) mm`, then rerun the
containment, owner-clearance, edge-envelope, root, pair-gap, solid, and
self-intersection checks.

On 2026-08-09 the user visually approved the complete isolated right-A
hardware contract with “OK, LGTM - move next.” This covers the M3 x 3 short
insert, recessed 4.25 mm x 3 mm cavity, M3 x 8 low-profile screw and washer,
and the 25-degree panel-side ball-end access path. The validation-only tool
shaft remains non-printing evidence.

Next physical work: print an ASA coupon in the final tab orientation with the
same cavity, install the exact insert, and perform pull-out/torque testing.
The next isolated CAD bucket is right-B hole, fastener, and tool access. No
mirror, production union, fabrication export, slicing, or ASA head print
release is authorized yet.
