# Cat Head Full-Size V1

This package turns the shape-approved cat-head panel surface into the 330 mm
fabrication master described in [FABRICATION_PLAN.md](FABRICATION_PLAN.md).

## Current Gate

Gate 1 was visually approved on 2026-07-15. It freezes:

- the uniformly scaled 330 mm exterior;
- the rear service cut plane;
- source facet identity;
- two corrected eye-material silhouettes traced from the annotated review;
- twenty removable glow/light-transmitting panels selected in purple, including both completed mirrored side pairs.

The seven-piece printer-sized section layout was approved on 2026-07-15. Gate 5
now adds compact internal flange tabs, hidden section joints, and lightweight
triangular gussets at every eligible internal source-panel connection in the
four body shells. Lighting carriers and the bike-mount load path remain
deferred.

## Generate Gate 2 Section Review

From the repository root:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate2_section_layout.py
~~~

The tracked layout is `config/gate2-section-layout.json`. Generated review
assets are written under `output/gate2-section-layout/`:

- `gate2-section-review.svg` — section ownership in four views;
- `gate2-section-layout.obj` and `.mtl` — colored face-level topology;
- `gate2-face-section-map.csv` — traceable face-to-section assignments;
- `gate2-fit-report.json` — connectivity, orientation, and printer-envelope checks.

The candidate uses four body shells, two removable ears, and a rear-base section.
The large center-bottom facet is divided on the centerline and belongs to the
two lower shells; it is not part of the rear-base section.
The rear base creates printer margin and a clean future backplate/service-cover
interface. `QUAD002` and `QUAD004`, the opaque eye-adjacent panels, will attach
to their lower shells through internal rear frame ribs.

## Generate Gate 3 Structural Shell Baseline

Gate 3 requires Blender and produces inward 1.8 mm walls without changing the
approved exterior:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate3_structural_shells.py
~~~

Tracked parameters are in `config/gate3-structural-shells.json`. Generated
assets under `output/gate3-structural-shells/` include:

- seven closed-manifold STL shell baselines;
- `gate3-structural-shells.blend` and `.glb` assembled models;
- front and rear PNG previews;
- `gate3-shell-validation.json` with manifold and printer-envelope checks.

The shell baseline is not yet fabrication-ready: the two opaque eye-adjacent
islands still need internal rear ribs, and all major seams still need flanges,
alignment keys, and fastener features.

Both large bottom/throat openings inherited from the accepted surface are now
closed integrally in the lower-shell STLs. Ventilation is reserved for protected
rear-facing features; only small deliberate drain holes will be added at the
lowest points later.

## Generate Gate 4 Complete Coverage Review

This review adds temporary solids for all twenty glow panels and both corrected
eyes, then cuts the planned 100 × 80 mm rear service opening:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate4_assembly_review.py
~~~

Review `output/gate4-assembly-review/gate4-complete-review-assembly.stl` in the
slicer rather than judging an isolated structural section. The combined STL is
review-only; individual temporary panel STLs are also exported for inspection.

## Generate Gate 1 Assets

From the repository root:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate1_master.py
~~~

The tracked candidate role selection is
[`config/gate1-panel-roles.json`](config/gate1-panel-roles.json). Adjust that
file, not generated output, when reviewing alternate lighting compositions.

The command writes these ignored review assets under `output/gate1-review/`:

- `gate1-master-330mm.obj` — exterior-only, uniformly scaled master.
- `gate1-role-review.obj` and `.mtl` — master with opaque, purple glow, and
  mouth-opening roles. Corrected eye material is currently a front-view review
  silhouette pending 3D projection onto the shell.
- `gate1-review.svg` — front, right-side, top, and isometric role review.
- `gate1-panel-role-map.csv` and `gate1-glow-units.csv` — fabrication-unit
  identities, areas, and centers.
- `gate1-validation-report.json` — source hashes, transformed dimensions, and
  Gate 1 acceptance checks.

The generator verifies that all accepted source facets have one role, exactly
the twenty purple selections are assigned as glow/light-transmitting panels,
no ear facets glow, two corrected eye-material shapes remain separate, and the
330 mm exterior is an exact
uniform transform of the accepted source. The rear-service plane is shown for
planning only; it does not cut the Gate 1 exterior.

Generated output is intentionally ignored by Git. The generator, approved
configuration, validation expectations, and fabrication documentation are the
source of truth.

## Generate Gate 5 Internal Flange Tabs

Gate 5 adds 18 pairs of matching, plain rectangular internal flange tabs across
the eight structural interfaces, plus 51 integral low-profile triangular
gussets at every source-panel connection internal to the four body shells. The
tabs and gussets are printed as part of the seven shell parts; use normal M3
through-bolts, washers, and loose nyloc nuts. On
angled seams, the M3 axis follows the shared inner bisector so both tabs remain
hidden behind the exterior skin. There are no receiver-only parts,
captive-nut pockets, separate printed joiners, dowels, or exterior fastener
holes:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate5_ribs_and_joints.py
~~~

Tracked dimensions and clearances are in
config/gate5-ribs-and-joints.json. Generated review assets are under
output/gate5-ribs-and-joints/:

- shells/ — seven flange-tab structural shell STLs;
- joiners/ — intentionally empty compatibility directory; do not print parts
  from it;
- gate5-internal-flange-tabs-review.blend and .glb — colored assembly review;
- gate5-internal-flange-tabs-review.stl — combined geometry review;
- gate5-validation-report.json — topology, printer fit, structural mass,
  hidden hardware, tab/gusset exterior clearance, internal-panel connection
  coverage, and
  Gate 3 baseline-volume protection;
- gate5-seam-audit.json — traceable source-facet seam map.

The rear base includes a 100 x 80 mm service opening, 10 x 10 mm internal rim,
and lower tie rails. The connector flange, rear cover/gasket, backplate, rails,
lighting cassette points, ventilation/drain features, and user-directed final
reinforcement remain later operations. See
[GATE5_RIBS_AND_JOINTS.md](GATE5_RIBS_AND_JOINTS.md) for hardware and assembly
constraints and [GATE5_RESUME_CHECKPOINT.md](GATE5_RESUME_CHECKPOINT.md) for
the current resumable state.

## Coordinate System

- `X`: left/right, centered on the face.
- `Y`: front to rear, with the nose-side minimum normalized to `0`.
- `Z`: chin to ear tips, normalized to `0..330 mm`.
