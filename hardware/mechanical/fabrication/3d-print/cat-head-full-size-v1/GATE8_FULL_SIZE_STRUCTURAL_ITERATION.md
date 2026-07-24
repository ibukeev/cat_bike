# Gate 8 Full-Size Structural Iteration

Status: generated and automatically validated. This is the first 330 mm
full-size review candidate based on feedback from the 100 mm print. It is not
cleared for final ASA production until the tube coupon, one structural shell,
and the assembled aluminum load path are physically tested.

## What changed

### Opaque muzzle structure

The failed small print showed that the center nose area had too little opaque
structure. Gate 8 reclassifies six source facets from translucent to opaque:

- right: `QUAD001`, `TRI001`, and `TRI003`;
- left: `QUAD022`, `TRI041`, and `TRI042`.

They are integrated into the adjacent upper- and lower-head shells. Six
internal root ribs, totaling about 245 mm of reinforced edge, tie the new
panels to those shells. The central light window is now the single printable
`glow_insert_central_6_panel_cluster.stl`, made from `MANQ001`, `TRI002`,
`TRI004`, `TRI017`, `TRI031`, and `TRI032`. It uses two hooks and two M2.5
retainers spaced across its two upper-head edges.

This panel-boundary split replaces the rejected Boolean-cut experiment. No
destructive perimeter cut is used in the final model.

### Stronger shell connections

- Normal shell flange modules are up to 42 mm long, 4.5 mm thick, and 12 mm
  deep, with two M3 through-bolts per module.
- Each tapered ear root uses one broad matching saddle with four M3
  through-bolts. The realized saddle length is about 24 mm because the source
  ear-root seam is only 26.6 mm long.
- Every matching flange plate now has a continuous convex solid base spanning
  its two proven shell anchors. The former open space between the narrow root
  legs is filled, while the body plates remain at least 3 mm behind the local
  exterior planes and the ear plates remain at least 8 mm behind them.
- Glow-panel hooks and shell tabs are recessed 2 mm behind their exterior
  source planes so their rectangular bodies cannot print through the skin.
- Main triangular internal ribs are 4 x 5 mm. Compact opposite-side ribs are
  2 x 3 mm. Junction hubs overlap rib endpoints by 5 mm.
- Six opaque structural sections also receive continuous 6 x 7 mm internal
  seam rails.
- All M3 hardware remains internal; Gate 8 adds no exterior fastener holes.

### Glow-insert clearance

Panel ribs and continuous seam rails are now clipped against every removable
translucent insert. The fit envelope is 0.8 mm beyond each insert, and the
Boolean cutter continues another 1.5 mm into the discarded side so angled rib
ends do not remain tangent to the pane.

The generator treats each closed reinforcement solid and each closed insert
body independently, then rejects any non-manifold result. In the current
model it detected 616 pre-trim triangle intersections and reports zero against
both the finished inserts and their 0.8 mm envelopes. About 8.64 cm3 of
interfering reinforcement is removed. One 449 mm3 right ear-root member (about
0.34 percent of all targeted reinforcement) could not be clipped watertight,
so that individual member is conservatively omitted; neighboring ribs and the
ear saddle remain. The report enforces that this fallback stays below one
percent of targeted reinforcement volume.

### Aluminum load-path sockets

Two blind square sockets are printed integrally with `left_upper_head.stl` and
`right_upper_head.stl`. There are no separate clamp caps. They are sized for
the locally available Everbilt 6605 nominal 3/4-inch square aluminum tube:

- nominal tube outside width: 19.05 mm;
- printed design opening: 20.50 mm, giving 1.45 mm total design clearance;
- blind socket length: 30 mm;
- socket wall and end stop: 6 mm;
- retention: one transverse 4.5 mm M4 clearance path, 10 mm inside the socket
  mouth, through both printed side walls and the drilled aluminum tube;
- modeled tube route from the lower rear area to each upper portal: about
  160.32 mm.

Each socket is shifted about 18.17 mm farther inward than the earlier review
geometry. Its nearest generated vertex is 8.499 mm behind the local exterior
plane, and validation reports zero socket vertices outside either shell. Its
mounting pad is a 68-percent inset copy of the actual triangular shell face,
not an exterior rectangular pad, so it stays inside that face boundary as well
as behind its plane. The tube stops inside the head. The sockets do not create
exterior openings.
Final tube cut lengths, lower backplate brackets, and load testing remain for
the next physical-fit iteration.

The lower M3 holes on the two sloped rear-base rails also move from 65 percent
to 48 percent down each rail. Their distance from the lower inside corners is
now about 44.27 mm instead of 29.79 mm, adding 14.47 mm for bolt, washer, and
tool access.

## Review and printable files

Primary review:

- `output/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend`
- `output/gate8-full-size-structural-iteration/review-renders/`
- `output/gate8-full-size-structural-iteration/gate8-full-size-structural-validation.json`

Print individual parts from:

- `shells/` — seven structural shell parts;
- `eye-modules/` — six eye-module parts;
- `glow-inserts/` — seven translucent insert parts;
- `portal-clamps/` — intentionally empty; the sockets are part of the two
  upper-head shell STLs;
- `test-coupons/` — one integrated 20.50 mm socket-fit coupon.

The combined review STL is not an individual printable part.

## First physical checks

1. Print `gate8_portal_fit_coupon_integrated_socket.stl` in PLA before cutting
   aluminum.
2. Place one outer socket wall on the bed. The upper wall bridges across the
   opening; there are no projecting clamp ears.
3. Test the actual Everbilt tube. The target is easy hand insertion with no
   serious rattle before drilling. Tune `tube_design_clearance_mm` if the local
   stock or printer differs.
4. Mark the transverse M4 center through the printed coupon, drill the
   aluminum, and verify an M4 bolt passes through both socket walls and tube.
5. Print one ear plus the mating upper-head corner and verify access to all
   four M3 positions.
6. Print one lower-face shell and the central six-panel diffuser to verify the
   new opaque/translucent boundary and the upper-only diffuser retention.
7. Dry-fit the four large side inserts and both ear-root inserts from inside.
   Confirm that no red rib or seam rail enters a pane's seating path, including
   the right ear-root corner where one conflicting member was omitted.
8. Assemble both aluminum uprights and the final lower brackets before
   committing to ASA shells.

## Automated validation

The Gate 8 report currently passes all configured checks:

- all shells, inserts, and the one-piece socket coupon are closed manifold
  meshes;
- all shell parts fit the configured Prusa orientation search;
- four opaque muzzle groups contain all six reclassified panels and each has
  at least one structural shell root;
- the six-panel central diffuser remains intact;
- reinforcement has zero measured triangle intersections with every finished
  glow insert and every 0.8 mm insertion envelope;
- conservative omission is limited to one 449 mm3 member, below one percent of
  the targeted reinforcement volume;
- both aluminum portal pads intersect their upper shells;
- both 20.50 mm sockets are integral with their upper shells, have blind end
  stops, and contain one transverse M4 path;
- the tube-fit opening is larger than the nominal 19.05 mm tube;
- no exterior fastener holes were introduced.

PrusaSlicer `--info` also reports both upper socket shells, the rear base, and
the one-piece socket coupon as manifold. A tiny inherited malformed hidden
bridge in `left_upper_head.stl` is rebuilt as a clean convex solid during Gate
8 export. Shell and diffuser STLs contain
multiple closed overlapping reinforcement bodies by design; the slicer unions
them into one print.

## Regenerate

From the repository root:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate8_full_size_iteration.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate8_review.py
~~~
