# Gate 8 Resume Checkpoint

Updated: 2026-07-22

Gate 8 is the current 330 mm full-size structural review candidate. Generation
and automatic validation pass. Do not restart from Gate 5 after a crash unless
one of the Gate 5-7 source dependencies or structural settings changed.

## Resume here

Open:

`output/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend`

Read:

- `GATE8_FULL_SIZE_STRUCTURAL_ITERATION.md`
- `output/gate8-full-size-structural-iteration/gate8-full-size-structural-validation.json`
- `config/gate8-full-size-structural-iteration.json`

The generator reuses the staged Gate 7 scene only when it is newer than the
Gate 8 config and Gate 5-7 generator sources. If those inputs change, it
rebuilds the structural, eye, and glow stages automatically. Blender can
occasionally exit while repeatedly reopening staged scenes; rerunning the same
command is safe because generated stages are deterministic and individually
validated.

## Accepted design state

- Head envelope remains 330 mm tall.
- Six eye-adjacent center facets are now opaque structural shell panels.
- The center diffuser is one six-panel translucent part, not the old
  twelve-panel part and not a Boolean-trimmed part.
- Normal body flanges use two M3 bolts; each ear uses one four-M3 saddle.
- Main internal ribs and their junction hubs are enlarged.
- Continuous internal seam rails cover both ears and all four main head shells.
- Ribs and seam rails are clipped to a 0.8 mm envelope around all seven glow
  inserts. Validation records 616 intersections before trimming and zero
  afterward.
- All matching M3 flange tabs now use continuous convex solid bases spanning
  their two shell anchors. Body plates remain at least 3 mm behind their local
  exterior planes; ear plates remain at least 8 mm behind them.
- Glow-panel shell mounts are recessed 2 mm behind their exterior source planes.
- One 449 mm3 right upper-head/ear-root reinforcement member is intentionally
  omitted because its Boolean trim was not watertight. This is 0.34 percent of
  targeted reinforcement; the surrounding rails and four-M3 ear saddle remain.
- Two blind 20.50 mm square sockets are integral with the upper-head shell
  STLs. Each accepts nominal 19.05 mm Everbilt 6605 square aluminum tube and
  has one transverse M4 path 10 mm inside its mouth. Both sockets were moved
  about 18.17 mm inward; their closest vertices remain 8.499 mm behind the
  exterior source planes, with zero outside vertices. Each backing pad follows
  a 68-percent inset of its triangular source face rather than using a
  rectangular exterior footprint.
- The lower holes on both sloped rear-base rails are 14.47 mm farther from the
  lower inside corners, leaving about 44.27 mm of corner distance.
- Gate 8 export merges three inherited overlapping hidden left-upper bridge
  solids at the known bridge location into one clean convex solid.
  PrusaSlicer reports the resulting shell as manifold.
- All fasteners and tube stops remain hidden from the exterior.

## Generated part count

- 7 structural shell STLs
- 6 eye-module STLs
- 7 glow-insert STLs
- 0 separate portal-cap STLs; sockets are included in the upper-head shells
- 1 integrated socket-fit coupon STL

## Known physical-validation items

- Print the socket coupon with one outer wall on the bed and assess the bridge
  across its upper wall.
- Measure the actual aluminum tube before final ASA printing; nominal stock can
  vary and printed holes shrink.
- The two approximately 175 mm modeled tube routes are reference geometry.
  Determine final cut lengths only after the backplate and lower brackets are
  fixed on the bike.
- Validate access to the four ear bolts at full size.
- Validate the six-panel center diffuser's upper-only hook/screw retention
  under vibration.
- Dry-fit every glow insert and check the full insertion path, especially the
  right ear-root corner with the conservatively omitted local member.
- Final backplate brackets, drainage, ventilation, wiring strain relief, and
  external LED cassette mounts remain deferred.

## Next recommended print

Print the one-piece integrated socket coupon first. Then print one ear and its mating
upper-head corner, followed by one lower-face shell plus the central diffuser.
Do not begin the complete ASA set until those three checks pass.
