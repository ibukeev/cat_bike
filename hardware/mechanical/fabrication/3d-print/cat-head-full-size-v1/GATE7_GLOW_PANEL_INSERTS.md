# Gate 7 Grouped Translucent Glow-Panel Inserts

Status: generated and automatically validated. This is a visual-review and
test-print candidate, not a production release. Print at least one isolated
insert and its shell interface before printing the central diffuser.

## Grouping

The twenty approved purple source facets become seven printable translucent
parts:

- one non-planar centerline insert combining the twelve facets that share full
  source-mesh edges;
- four individual inserts for isolated approved panels;
- one simplified right ear-root insert combining `TRI027`, its bridge, and
  `QUAD021`;
- one mirrored left ear-root insert combining `TRI055`, its bridge, and
  `QUAD035`.

Panels that only touch at a vertex are normally not combined. Each ear-root
cluster is an explicit exception because its synthetic bridge supplies the two
complete shared edges needed to make a connected surface.

## Ear-root revision

The formerly separate right `TRI027` and `QUAD021` parts are replaced by
`glow_insert_right_ear_root_cluster.stl`. Its visible skin is exactly three
planes: the TRI plane, the missing bridge triangle, and the outer QUAD plane.
The smaller coplanar QUAD source triangle was entirely contained inside the
outer triangle and is deliberately omitted. Keeping it was the source of the
overlapping, nonmanifold-looking geometry. The left cluster is an exact mirror.

Each cluster skin is edge-connected before being solidified. Its shallow cap,
two local capture pads, and bolt tab are boolean-unioned into that body. The
result is one connected STL component rather than a collection of overlapping
closed shells. There is no full perimeter flange lattice on these two parts.

Gate 7 does not modify the structural Gate 5 ear joint. Its broad matching tabs
now sit at least 8 mm behind both adjacent exterior planes and connect through
two narrow embedded roots per tab. Both cluster retainers sit on well-separated
hidden upper-head edges, so each ear remains independently removable. A
mirrored 25 mm top-only relief and 10 mm localized top-side setbacks preserve
access to the two-bolt M3 ear flange while retaining the long front and rear
pane boundaries against the head.

The generator recreates the exact Gate 5 ear tabs and performs a BVH collision
check before accepting Gate 7. The current generated result has zero triangle
intersections on both sides. Minimum sampled gaps are 2.1675 mm for the right
cluster and 2.1664 mm for the left cluster, both above the configured 0.8 mm
minimum.

## Insert construction

Each insert uses nominal 1.5 mm frosted or milky translucent PETG. The deeper
fit body remains recessed 0.6 mm behind the shell with 0.35 mm perimeter
clearance, so shrink and minor dimensional error do not jam the insert during
assembly.

A shallow integrated translucent face cap closes the visible seams without
removing that deeper fit tolerance. The cap is 0.5 mm thick, recessed only
0.15 mm from the exterior shell surface, and stops 0.05 mm from each aperture
edge. Two neighboring separately printed caps therefore have a nominal 0.10
mm pane-to-pane seam. This is intentionally near-gapless rather than a literal
zero-clearance fit. Every normal opaque-panel boundary and both synthetic
ear-root bridge panes receive the same cap treatment.

A 3 mm-wide translucent flange overlaps the shell from inside and seats
against a thin black gasket on the central and four isolated inserts. Each
three-plane ear-root cluster instead uses only two local hidden capture pads,
one at its hook and one at its bolt. The 25 mm top-only ear-connector relief
and 10 mm top-side tip setbacks are deliberate and preserve M3 flange, washer,
nut, and tool access without shortening the main front/rear contact edges.

## Attachment

Every noncentral insert, including each combined ear-root cluster, uses one
integrated fixed hook and one concealed M2.5 through-bolt. The central
twelve-panel insert uses two upper hooks and two lower M2.5 bolts. Hooks and
shell-side bolt tabs are manifold-unioned into the owning shell. All hook lips
and bolt tabs sit under the opaque shell border; there are no exterior
fastener holes.

Gate 7 panel-retention hardware total:

- eight M2.5 through-bolts;
- sixteen M2.5 washers;
- eight loose M2.5 nyloc nuts;
- eight fixed hooks printed as part of the structural shells.

Choose bolt length from a physical coupon. Start with M2.5 x 8-10 mm and
confirm full nyloc engagement without crushing the PETG tab.

## Assembly order

1. Apply thin black gasket tape to the opaque shell seat without narrowing the
   visible aperture.
2. From inside the head, slide the insert overlap flange under its fixed hook
   or hooks.
3. Rotate the remaining edge forward until the diffuser seats evenly against
   the gasket.
4. Install the internal M2.5 bolt, two washers, and loose nyloc nut at each
   screw tab. Tighten only enough to stop movement and compress the gasket.
5. Install the central insert after joining the four body shells. Remove the
   central insert before separating those shells.
6. Each combined ear-root insert stays with its upper-head shell; the ear is
   not a retention point and can be removed independently.
7. At each ear root, confirm that the relieved insert corner does not enter the
   M3 washer, nut, or tool-access envelope before final tightening.

## Generated files

Run:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate7_glow_panel_inserts.py
~~~

Review `output/10-design-gates/gate7-glow-panel-inserts/gate7-glow-panel-inserts-review.blend`
first.

- `glow-inserts/` contains the seven full-size translucent insert STLs.
- `shells/` contains the complete seven-piece shell set with integrated hooks
  and matching internal bolt tabs.
- `small-model-100mm/` contains scaled visual parts and a combined insert
  assembly STL. Scaled M2.5 holes are not hardware coupons.
- `gate7-glow-panel-validation.json` records grouping, mount ownership,
  topology, printer fit, and exports.

## Required physical checks

- Print one isolated insert and a matching shell-region coupon first.
- Confirm the 0.05 mm visible cap edge clearance does not bind after real PETG
  and ASA shrink; lightly dress an edge if necessary. The deeper insert body
  retains 0.35 mm assembly clearance.
- Confirm ordinary pane-to-shell seams appear closed and adjacent separately
  printed pane caps leave only the nominal 0.10 mm visual seam.
- Confirm the 3 mm overlap stays captured under the hook during vibration.
- Confirm each combined ear-root STL slices as one connected part with three
  visible planes and no internal duplicate QUAD triangle.
- Confirm its two local capture pads engage the upper-head hook and bolt tab.
- Confirm the 25 mm top relief preserves access to both M3 ear bolts and that
  the ear can be removed without releasing the translucent cluster.
- Verify bolt and nyloc access from the rear service opening.
- Inspect the outside for hook/tab visibility from front, side, above, and
  below. Faint coplanar topology edges in Blender are not exterior holes.
- Test 1.0 and 1.5 mm diffuser samples before locking optical material.
- LED setback, light chambers, cassette grouping, heat, and hotspots remain a
  later lighting gate.
