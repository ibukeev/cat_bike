# Lower Reinforcement Ownership Review V1 Checkpoint — 2026-08-04

## Status

V1 is ready for visual ownership review only. It inventories existing Gate 8
reinforcement from both lower-face source objects against the approved V5
exterior repartition. It does not cut, redesign, delete, union, or transfer any
reinforcement and does not change the approved exterior seam.

## Primary review files

- Blender: `output/30-reinforcement-baselines/lower-reinforcement-ownership-review-v1/lower-reinforcement-ownership-review-v1.blend`
- Validation: `output/30-reinforcement-baselines/lower-reinforcement-ownership-review-v1/lower-reinforcement-ownership-review-v1-validation.json`
- Renders: `output/30-reinforcement-baselines/lower-reinforcement-ownership-review-v1/renders/`

## Blender review structure

- `R1_REINFORCEMENT__RETAINED_LOWER`: cyan standalone components contacting
  only retained lower-face source facets.
- `R1_REINFORCEMENT__REAR_CASSETTE`: orange standalone components contacting
  only cassette-owned source facets.
- `R1_REINFORCEMENT__CROSSES_APPROVED_SEAM`: red standalone components with
  verified contact on both sides of the approved seam.
- `R1_REINFORCEMENT__UNCLASSIFIED`: magenta standalone components with no
  verified source-facet contact inside the configured envelope.
- `R1_INTEGRATED_SHELL_PLUS_REINFORCEMENT`: six complete source components
  containing substantial shell geometry as well as tagged reinforcement. They
  remain preserved but are hidden by default so the shell does not obscure the
  standalone internal frame.
- The V5 retained/cassette shells are visible as wireframe context in the
  default Blender viewport. The yellow V5 boundary remains unchanged.

## Review rule and dimensions

- Whole connected components are classified from their actual mesh vertices.
- Maximum verified source-facet contact distance: `2.25 mm`.
- Retained/cassette distance tie tolerance: `0.25 mm`.
- A component contacting both ownership regions remains whole and is red.
- A component with no verified contact remains magenta; no nearest-side guess
  is accepted.
- Components with less than `50%` reinforcement-tagged surface area are placed
  in the integrated-shell collection instead of being shown as standalone
  reinforcement.
- The approved V5 exterior facet ownership, V0.5 aluminum interface, upper
  head, ears, eyes, connectors, glow inserts, and `rear_base` remain unchanged.

## Inventory results

- Complete tagged component inventory: 109 whole connected components.
- Standalone internal components shown by default: 103.
  - 67 cyan retained-lower candidates.
  - 26 orange rear-cassette candidates.
  - 6 red components crossing the approved seam.
  - 4 magenta unclassified components.
- Integrated shell-plus-reinforcement components hidden by default: 6.
  - 4 contact only retained facets.
  - 2 contact both retained and cassette facets.
- Dominant source reinforcement tags:
  - 85 internal panel ribs.
  - 16 continuous inter-shell rails.
  - 4 internal flange-tab components.
  - 4 eye/head mount flange components.

The four magenta components are:

- `R1_UNCL__L__C002__eye_mount`: minimum retained-facet distance `6.6075 mm`.
- `R1_UNCL__R__C002__eye_mount`: minimum retained-facet distance `7.5116 mm`.
- `R1_UNCL__L__C060__rib`: `0.0236 mm3` Boolean sliver.
- `R1_UNCL__R__C062__rib`: `0.0805 mm3` Boolean sliver.

The two large integrated source components
`R1_CROSS__L__C000__flange` and `R1_CROSS__R__C000__flange` contain the old
lower shells as well as flange-tagged geometry. They cross the approved V5
ownership seam and cannot be transferred whole. They are an explicit later
redesign item, not a standalone reinforcement assignment.

## Validation performed

- Left source reinforcement-tagged polygons: 826; inventoried: 826; missing: 0;
  duplicated: 0.
- Right source reinforcement-tagged polygons: 808; inventoried: 808; missing:
  0; duplicated: 0.
- Every review component geometry fingerprint matches its complete source
  component.
- All 109 review components are closed and manifold.
- All pre-existing V5/Gate 8 mesh fingerprints are unchanged.
- The isolated rear and oblique renders were visually checked for visible
  internal-frame continuity and color separation.
- No STL or G-code was generated.

## Rejected or unsafe approaches

- Do not assign a component from its centroid or general left/right location.
- Do not cut a crossing component merely to make it fit the ownership groups.
- Do not hide unclassified pieces by forcing them to their nearest shell.
- Do not treat the two old shell-plus-flange source components as standalone
  planks; doing so obscures the review and misstates their physical scope.
- Do not alter the approved V5 exterior seam during reinforcement review.

## Exact regeneration command

From repository root:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_lower_reinforcement_ownership_review_v1.py
```

## Next physical review

1. Open the Blender review and inspect the default rear/interior view.
2. Isolate the cyan retained and orange cassette collections separately; check
   whether the ownership looks physically sensible.
3. Isolate the red crossing collection; confirm these are the members that
   visibly bridge the approved seam.
4. Isolate the magenta collection and review the two eye-mount pieces. Do not
   decide their ownership from the two negligible Boolean slivers.
5. Leave `R1_INTEGRATED_SHELL_PLUS_REINFORCEMENT` hidden during the normal
   internal-frame review; inspect it separately only to confirm why those six
   complete components cannot be treated as standalone planks.
6. Do not print from this file. After explicit ownership approval, redesign the
   red crossing members as the next separate change without moving the exterior
   seam or changing aluminum.
