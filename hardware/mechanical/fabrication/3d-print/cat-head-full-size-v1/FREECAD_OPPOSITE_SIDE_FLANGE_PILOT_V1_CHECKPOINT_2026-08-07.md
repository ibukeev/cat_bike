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
