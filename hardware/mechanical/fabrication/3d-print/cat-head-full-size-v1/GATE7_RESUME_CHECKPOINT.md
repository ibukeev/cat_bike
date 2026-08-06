# Gate 7 Resume Checkpoint

Last updated: 2026-07-19

This is the restart point after adding mechanically retained translucent glow
panels. Gate 7 is a review/test-print candidate and is not cleared for
production printing.

## Current review files

- `output/10-design-gates/gate7-glow-panel-inserts/gate7-glow-panel-inserts-review.blend` -
  primary visual and internal-mount review.
- `output/10-design-gates/gate7-glow-panel-inserts/gate7-glow-panel-inserts-review.stl` -
  combined geometry review, not an individual print part.
- `output/10-design-gates/gate7-glow-panel-inserts/gate7-glow-panel-validation.json` -
  generated validation record.
- `output/10-design-gates/gate7-glow-panel-inserts/glow-inserts/` - seven full-size translucent
  insert STLs.
- `output/10-design-gates/gate7-glow-panel-inserts/shells/` - complete seven-shell Gate 7 set
  with integrated hooks and matching tabs.
- `output/10-design-gates/gate7-glow-panel-inserts/small-model-100mm/` - visual-scale inserts.

Regenerate with:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate7_glow_panel_inserts.py
~~~

## Accepted design state

1. Preserve every accepted Gate 6 shell, gusset, rear-frame, seam-joint, and
   eye-module feature.
2. Preserve the twenty approved Gate 1 glow facets. Combine only panels that
   share a complete source-mesh edge.
3. The twelve connected centerline facets form one printed non-planar insert.
   Four isolated panels remain separate. The right TRI027/bridge/QUAD021 region
   and mirrored left region each form one combined insert, for seven printed
   inserts total.
4. Use nominal 1.5 mm frosted/milky PETG. The deeper fit body uses 0.6 mm
   surface setback and 0.35 mm perimeter clearance, plus a 3 mm hidden overlap
   flange with black gasket.
5. Each insert has an integrated 0.5 mm-thick visible seam cap at 0.15 mm
   surface setback and 0.05 mm perimeter clearance. This makes ordinary
   pane-to-shell seams near-gapless and leaves only a nominal 0.10 mm seam
   between neighboring separately printed caps while preserving deeper fit
   tolerance.
6. Each isolated insert uses one fixed shell hook and one internal M2.5 tab.
   The central insert uses two upper hooks and two lower M2.5 tabs.
7. Hooks and shell tabs are true manifold unions beneath the opaque border.
   Bolt axes are parallel to local panel faces; there are no exterior holes.
8. Install the central insert only after joining the body shells, and remove it
   before separating them. Remove interface-spanning side inserts before ear
   removal.
9. The right ear-root insert has exactly three visible planes: TRI027, the
   bridge, and the outer QUAD021 triangle. The left insert mirrors it. The
   redundant smaller coplanar triangle contained inside each QUAD source panel
   is omitted.
10. Each ear-root skin is edge-connected and solidified once. Its cap, two
    local capture pads, and bolt tab are boolean-unioned, producing exactly one
    connected manifold mesh component with no full perimeter flange lattice.
11. Both retainers for each ear-root insert are on well-separated hidden
    upper-head edges. The ear remains independently removable. Mirrored 25 mm
    top-only reliefs and 10 mm localized top-side setbacks preserve connector
    and tool access while the long front/rear pane edges remain against the
    head. Gate 5 broad ear tabs are recessed at least 8 mm behind both source
    exterior planes and use two narrow embedded roots per tab.
12. LED cassette geometry and light-blocking chamber divisions remain deferred.

## Validation snapshot

- Twenty approved glow facets represented by seven printable inserts.
- One twelve-facet central cluster, four isolated inserts, and two simplified
  three-plane ear-root clusters.
- Eight fixed hooks and eight concealed M2.5 retention paths.
- All seven inserts and all seven revised shells are closed manifold.
- Every full-size insert fits the 240 x 200 x 210 mm printer envelope.
- No exterior fastener holes.
- All seven inserts and both integrated ear-root bridge panes have attached
  near-edge visible caps. The deep body keeps the 0.35 mm fit clearance while
  the cap reduces the normal visible boundary clearance to 0.05 mm.
- Exact recreated Gate 5 ear tabs have zero triangle intersections with either
  combined ear-root insert. Minimum sampled gaps are 2.1675 mm right and
  2.1664 mm left, versus the configured 0.8 mm requirement.
- Both ear-root STLs have exactly one connected component, zero boundary and
  nonmanifold edges, and three visible surface planes.
- A 100 mm-head-scale combined visual insert assembly was exported.
- All automated Gate 7 acceptance checks pass.

## Next review / prototype tasks

1. Review all seven purple inserts and their internal hooks/tabs in the Gate 7
   `.blend` file.
2. Print one isolated full-size insert plus a shell-region coupon; validate
   the tight 0.05 mm cap edge, deeper 0.35 mm fit clearance, gasket compression,
   hook engagement, and M2.5 access.
3. Print the 100 mm visual assembly with the small head. Do not use its scaled
   M2.5 geometry as a hardware test.
4. After mechanical approval, design grouped LED cassettes and opaque light
   partitions without leaking into the independent eye modules.
5. During the first ear-root test fit, verify each combined three-plane insert
   fills the former TRI/QUAD/bridge region, slices as one part, and stays with
   the upper-head shell while the ear is removed. Confirm washer, nut, and tool
   clearance around both M3 ear bolts.
