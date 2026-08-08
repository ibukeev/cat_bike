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
