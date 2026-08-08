# Cat Head Full-Size V1

This package turns the shape-approved cat-head panel surface into the 330 mm
fabrication master described in [FABRICATION_PLAN.md](FABRICATION_PLAN.md).

## Current release status — 2026-08-08

**HOLD: do not start the structural ASA head or use historical Gate 8 print
recommendations.** The current shell exports are disconnected multi-part
meshes, and the old 20.50 mm fixed-socket coupon does not represent the frozen
V0.5-M2 21.00 mm serviceable socket/cap interface.

- Start at `PRINT_READINESS_DASHBOARD_2026-08-08.md`.
- Track feedback in `FEEDBACK_CLOSURE_MATRIX_2026-08-08.md`.
- Read `PRINTABLE_COUPON_AUDIT_2026-08-08.md` before printing any coupon.
- Review the proposed replacement contract in
  `V05_M2_SOCKET_CAP_COUPON_CONTRACT_PROPOSAL_2026-08-08.md`.


## Current Gate

Gate 1 was visually approved on 2026-07-15. It freezes:

- the uniformly scaled 330 mm exterior;
- the rear service cut plane;
- source facet identity;
- two corrected eye-material silhouettes traced from the annotated review;
- twenty removable glow/light-transmitting panels selected in purple, including both completed mirrored side pairs.

The seven-piece printer-sized section layout was approved on 2026-07-15. Gate 5
adds compact internal flange tabs, hidden section joints, lightweight
triangular gussets on both panel sides at every eligible internal source-panel
connection in the four body shells, and triangulated hubs at every shared main
gusset endpoint. Gate 6 adds two isolated, removable eye lightboxes with
frosted diffusers, opaque LED chambers, and two recessed internal head-mount
flanges per eye.
Gate 7 represents the twenty approved glow facets with nine removable
translucent inserts: one combined twelve-facet centerline diffuser and eight
isolated inserts. Concealed fixed hooks and internal M2.5 tabs retain them.
Gate 8 is the current full-size feedback iteration. It reclassifies six
eye-adjacent center facets as opaque structure, replaces the center diffuser
with one six-panel insert, enlarges the hidden M3 flange system and ribs, and
gives every matching flange a continuous solid shell-root base. Glow mounts
are recessed 2 mm, and it adds two blind 20.50 mm aluminum-tube sockets
directly to the upper-head shell STLs. Each socket stays at least 8 mm behind
its local exterior plane, uses an inset triangular backing footprint, and has
one transverse M4 retention path for nominal 19.05 mm Everbilt 6605 square
aluminum tube. Final backplate brackets and full-load validation remain
deferred.

## Generate Gate 2 Section Review

From the repository root:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate2_section_layout.py
~~~

The tracked layout is `config/gate2-section-layout.json`. Generated review
assets are written under `output/10-design-gates/gate2-section-layout/`:

- `gate2-section-review.svg` — section ownership in four views;
- `gate2-section-layout.obj` and `.mtl` — colored face-level topology;
- `gate2-face-section-map.csv` — traceable face-to-section assignments;
- `gate2-fit-report.json` — connectivity, orientation, and printer-envelope checks.

The candidate uses four body shells, two removable ears, and a compact rear-base
surround. The large center-bottom facet and the rear-facing `MANQ006` / `MANQ007`
facets are divided on the centerline and belong to the two lower shells; they are
not part of the rear-base section. The compact rear base frames the upper rear
opening on the upper-head rear plane; the lower rear panels remain continuous.
It reserves the future backplate/service-cover interface.

## Generate Gate 3 Structural Shell Baseline

Gate 3 requires Blender and produces inward 1.8 mm walls without changing the
approved exterior:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate3_structural_shells.py
~~~

Tracked parameters are in `config/gate3-structural-shells.json`. Generated
assets under `output/10-design-gates/gate3-structural-shells/` include:

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
eyes, then cuts the legacy planned 100 × 80 mm rear service opening. This Gate 4
review is superseded for fabrication by the compact Gate 5 rear frame:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate4_assembly_review.py
~~~

Review `output/10-design-gates/gate4-assembly-review/gate4-complete-review-assembly.stl` in the
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

The command writes these ignored review assets under `output/10-design-gates/gate1-review/`:

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

Gate 5 adds 16 pairs of matching, plain rectangular internal flange tabs at
source-section seams. The rear base uses four continuous shell-integrated
connector rails instead of isolated tab pairs; six M3 paths through those rails
connect it to all four adjacent head shells. It also adds 110 integral
low-profile triangular gussets
on both sides of every source-panel connection internal to the four body shells
and 38 triangulated hubs at every shared main-gusset endpoint. The tabs,
gussets, and hubs are printed as part of the seven shell parts; use normal M3 through-bolts,
washers, and loose nyloc nuts. On
angled source-panel seams, the M3 axis follows the shared inner bisector so both
tabs remain hidden behind the exterior skin. Rear-base rails follow the sloped
rear-frame plane. There are no receiver-only parts,
captive-nut pockets, separate printed joiners, dowels, or exterior fastener
holes:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate5_ribs_and_joints.py
~~~

Tracked dimensions and clearances are in
config/gate5-ribs-and-joints.json. Generated review assets are under
output/10-design-gates/gate5-ribs-and-joints/:

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

The rear base is a compact 60 mm-top / 120 mm-bottom trapezoidal closed frame
with a 20 mm structural surround and 18 mm of depth extending inward from the
upper-head rear plane. Its remaining tapered access opening is approximately
20 mm wide at the top, 80 mm wide at the bottom, and 39 mm high. It is intended
for wiring, inspection, and nut access; full hand service remains available by
removing a head section until a dedicated rear cover is designed. Four
continuous concealed rails follow the adjacent shell interfaces and carry six
M3 through-bolt paths: two per upper shell and one per lower shell. The deep
rear-frame surround is the continuous mating member, so no isolated planks or
tabs project into the opening. The lower rear panels remain continuous and
their center seams receive hidden flange modules. The old lower service cut,
rectangular rim, and tie rails are gone.
The connector flange, rear cover/gasket, backplate, rails,
lighting cassette points, ventilation/drain features, and user-directed final
reinforcement remain later operations. See
[GATE5_RIBS_AND_JOINTS.md](GATE5_RIBS_AND_JOINTS.md) for hardware and assembly
constraints and [GATE5_RESUME_CHECKPOINT.md](GATE5_RESUME_CHECKPOINT.md) for
the current resumable state.

## Generate Gate 6 Eye Lightboxes

Gate 6 preserves Gate 5 and adds three full-size parts per eye: an opaque
bucket/bezel, a 1.5 mm frosted diffuser, and an opaque removable LED rear cap.
Each chamber reserves four independently addressable pixels and 11 mm of
diffusion distance. Two recessed internal M2.5 flange bolts, centered on the
outer-side and lower eye edges, retain each module without exterior holes:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
~~~

Review `output/10-design-gates/gate6-eye-modules/gate6-eye-modules-review.blend`. Print the
eye parts from `eyes/` and use the revised seven-shell set from `shells/`,
because both lower-face shells now contain matching paired eye-mount tabs. The
`small-model-100mm/` exports are visual-fit parts only; use a full-size eye to
validate LEDs, hardware, diffuser fit, heat, and light leakage. See
[GATE6_EYE_MODULES.md](GATE6_EYE_MODULES.md) and
[GATE6_RESUME_CHECKPOINT.md](GATE6_RESUME_CHECKPOINT.md).

## Generate Gate 7 Glow-Panel Inserts

Gate 7 preserves Gate 6 and adds nine printable 1.5 mm translucent PETG
inserts. Each uses a hidden 3 mm overlap flange and black gasket seat. Eight
single inserts use one fixed hook and one internal M2.5 retainer; the combined
twelve-facet center insert uses two hooks and two retainers:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate7_glow_panel_inserts.py
~~~

Review `output/10-design-gates/gate7-glow-panel-inserts/gate7-glow-panel-inserts-review.blend`.
Print translucent parts from `glow-inserts/` and use the revised structural
parts from `shells/`. See [GATE7_GLOW_PANEL_INSERTS.md](GATE7_GLOW_PANEL_INSERTS.md)
and [GATE7_RESUME_CHECKPOINT.md](GATE7_RESUME_CHECKPOINT.md).

## Generate Gate 8 Full-Size Structural Iteration

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate8_full_size_iteration.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate8_review.py
~~~

Review `output/10-design-gates/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend`.
Print only the individual files in its part subdirectories. Start with the
one-piece integrated socket file in `test-coupons/`; `portal-clamps/` is empty
because both sockets are included in the upper-head STLs. Gate 8 also
clips internal ribs and seam rails to a validated 0.8 mm clearance envelope
around every removable glow insert. See
[GATE8_FULL_SIZE_STRUCTURAL_ITERATION.md](GATE8_FULL_SIZE_STRUCTURAL_ITERATION.md)
and [GATE8_RESUME_CHECKPOINT.md](GATE8_RESUME_CHECKPOINT.md).

## Generate Mirror-Facet Cap Prototypes

The mirror-finish experiment uses four representative Gate 8 source facets.
Two non-planar source quads split along their existing diagonals, producing six
truly planar caps at both 0.6 mm and 0.8 mm thickness:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_mirror_facet_cap_prototypes.py
~~~

Start with `mirror-facet-cap-left-starter-plate-0p8mm.stl`, a three-part
black-PETG trial derived from the actual left muzzle, forehead, and ear facets
for the currently printed left shell. Review the two complete thickness plates
and 1:1 SVG under `output/40-prototypes/mirror-facet-cap-prototypes/`. A textured starter
print is valid for handling and bonding tests; repeat the chosen cap on a
protected smooth sheet before final optical approval. Apply adhesive mirror
film while each cap is fully supported on a flat table. See
[MIRROR_FACET_CAP_PROTOTYPES.md](MIRROR_FACET_CAP_PROTOTYPES.md) for the
Amazon film shortlist, application procedure, and acceptance checks, and
[MIRROR_FACET_CAP_PROTOTYPES_RESUME_CHECKPOINT.md](MIRROR_FACET_CAP_PROTOTYPES_RESUME_CHECKPOINT.md)
for the resumable state.

## Coordinate System

- `X`: left/right, centered on the face.
- `Y`: front to rear, with the nose-side minimum normalized to `0`.
- `Z`: chin to ear tips, normalized to `0..330 mm`.
