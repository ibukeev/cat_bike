# Design Proposal

## Purpose

Define how the Bio-Luminescent Abyssinian concept should translate into a real, rideable bike build.

The concept images are the visual north star, not literal fabrication drawings. The build should preserve the strongest identity cues while simplifying anything that would make the first version fragile, heavy, hard to mount, or impossible to finish iteratively.

## Design Position

Build toward a polished faceted bio-luminescent cat bike, but do not copy the AI concept exactly.

The concept is strongest when it reads as:

- A gold/yellow utility bike transformed into a cat.
- A faceted copper or rose-gold cat face at the front.
- Bright cyan/aqua eyes.
- Fiber-optic whiskers.
- Cyan, aqua, magenta, and violet glow.
- A curled illuminated tail at the rear.
- Organic body glow that can become more sculptural in later phases.

The concept is weakest where it invents impractical or over-busy details:

- Complex full-body panels before the mount geometry is known.
- Wheel lighting as an early requirement.
- Dense LED fields that would be hard to service.
- Hallucinated structural parts that do not match the actual bike.
- Lighting on controls, handlebars, or flag posts just because they appear in an image.

## Keeper Elements

These should stay consistent from MVP through final build:

| Element | Why It Matters | MVP Interpretation | Final Interpretation |
|---|---|---|---|
| Gold bike frame | Keeps the real bike visible and avoids a full body-shell rebuild | Leave bike frame exposed | Integrate glow around frame without hiding it completely |
| Faceted cat head | Primary visual identity | Cardboard/foamcore faceted head | Plastic, acrylic/PETG, or printed faceted module |
| Copper / rose-gold surface | Gives the build warmth and contrast against cyan LEDs | Mirror film or Mylar on selected facets | Copper/rose-gold mirror vinyl or mirrored plastic facets |
| Cyan/aqua eyes | Strong readable character from front | Frosted eye shapes with small LED clusters | Clean diffused eye modules |
| Fiber-optic whiskers | Signature detail; makes the head feel alive | Temporary fibers or flexible placeholders | Side-glow fiber bundles driven by hidden LEDs |
| Aqua/magenta/violet glow | Bio-luminescent identity | Limited head glow plus basic frame/rack LEDs | Coordinated head, tail, panel, and body glow |
| Tail | Rear cat identity | Deferred until after head MVP | Lightweight illuminated tail on rear rack/basket area |

## MVP Design Strategy

The MVP should prove the cat identity first, not the entire final sculpture.

MVP goals:

- Confirm head size and position on the real bike.
- Confirm steering, brake, cable, headlight, hand, and rider sightline clearance.
- Confirm that a faceted copper/rose-gold head looks good on the gold frame.
- Confirm eye shape and brightness.
- Confirm whisker placement and approximate fiber routing.
- Keep power and wiring temporary but safe.

MVP non-goals:

- Final waterproofing.
- Final body panels.
- Final tail.
- Wheel lighting.
- Full Pixelblaze choreography.
- Final polished fabrication.

## Phase Visual Evolution

| Phase | Visual Result | What Should Be Avoided |
|---|---|---|
| Phase 1: Lighting Foundation | Bike has restrained frame, fork, rack, basket, and underglow lighting in the bio-luminescent palette | Do not make the bike visually crowded before the cat head exists |
| Phase 2A: Cat Head MVP | Bike clearly reads as a cat from the front and side | Do not overbuild the head before scale and steering clearance are proven |
| Phase 2A: Rideable Cat Head | Cat head becomes a removable, lit, rideable module | Do not make it heavy, sharp, cable-hostile, or hard to remove |
| Phase 2B: Tail | Rear silhouette gains cat identity and motion | Do not block basket/cargo function or rider leg clearance |
| Phase 3: Body Panels | Sculptural side glow ties the head and tail together | Do not install panel LEDs until panel geometry exists |
| Phase 4: Showpiece Upgrades | Optional wheels and richer parked/show effects | Do not let show effects compromise ride safety or repairability |

## Cat Head Design Proposal

Current visual reference:

- [cat-head-reference-v1.png](../../assets/references/cat-head/cat-head-reference-v1.png)
- [cat-head-reference-v3.png](../../assets/references/cat-head/cat-head-reference-v3.png) - preferred current visual/style reference.
- [cat-head-reference-v4.png](../../assets/references/cat-head/cat-head-reference-v4.png) - preferred current fabrication/reference-sheet direction.

Reference interpretation:

| Reference | Role | Keep | Modify for MVP |
|---|---|---|---|
| `cat-head-reference-v1.png` | Early visual direction | Elegant face, copper facets, cyan eyes | Simplify neck/base and reduce whisker density |
| `cat-head-reference-v2.png` | Access/mount thinking | Rear access plate, wire exit, practical module logic | Avoid the large visible rectangular base |
| `cat-head-reference-v3.png` | Best beauty/style reference | Face silhouette, diffused glow, polished copper faceting | Simplify lower neck/base and reduce whiskers |
| `cat-head-reference-v4.png` | Best fabrication reference | Front/side/rear views, rear access panel, hidden mount points, wire exit | Treat labels and dimensions as design intent, not exact CAD |

### Overall Direction

The cat head should be a removable front module that rotates with the handlebars. It should feel like a faceted copper/rose-gold mask with controlled internal glow, not a soft costume head and not a heavy metal sculpture.

Recommended visual hierarchy:

1. Eye glow.
2. Face silhouette and ears.
3. Whiskers.
4. Selected glowing facets.
5. Mirror/copper reflections.

The head should still look intentional in daylight with LEDs off.

### Shape

The head should be angular and low-poly, with clear ears, eyes, muzzle, nose, and cheek planes. The face should be readable from both front and three-quarter side views.

Initial target envelope:

| Dimension | Target | Reason |
|---|---:|---|
| Width | 14 in | Large enough to read as a sculpture, still inside handlebar width |
| Height | 12 in | Allows ears and face without blocking rider view |
| Depth | 8 in | Gives room for LEDs/fibers while limiting steering mass |
| Whiskers | 8-12 in per side | Expressive but flexible and safer than rigid rods |
| Weight | Under 2 lb, ideally near 1 lb | Keeps steering and mount loads reasonable |

If the first mockup feels oversized, reduce width before reducing height. A cat head that is too wide may interfere with hands and controls; a head that is too short may lose the cat silhouette.

### Facet Language

Use facets deliberately. The head should not become a random triangle mosaic.

Recommended facet roles:

- Large mirrored facets for ears, forehead sides, cheeks, and outer muzzle.
- Translucent glowing facets around forehead center, cheek glow, and lower muzzle.
- Strong dark seams or shadow gaps between facets to define the face.
- Eyes as the brightest and cleanest shapes.

Do not light every facet. Too many lit facets will flatten the face and make the eyes less important.

### Eyes

The eyes should be the strongest lighting feature.

Recommended MVP:

- Slanted cyan/aqua eye shapes.
- Frosted diffuser material or translucent plastic.
- Small LED clusters or short strip pieces behind each eye.
- Bright enough to read outdoors at night, but not aimed directly at the rider.

Avoid round LED rings unless the rest of the head design changes toward a more mechanical style. The current direction wants angular feline eyes.

### Whiskers

Whiskers should use side-glow fiber optics or a close temporary substitute.

Recommended look:

- 5-9 strands per side for MVP review.
- Exit from cheek/muzzle area, not randomly from the side of the head.
- Slight fan shape: some forward, some sideward, some slightly downward.
- Mostly cyan/aqua with occasional magenta/violet shimmer.

Whiskers should be flexible, rounded, and non-pokey. They must not contact hands, brake levers, cables, tire, or pedestrians during normal riding.

### Finish

The preferred final finish is flat faceted geometry plus copper/rose-gold mirror vinyl or mirrored plastic. Paint alone is acceptable for internal structure and edges, but it is unlikely to achieve the reflective look from the concept images.

MVP finish:

- Use Mylar, mirror craft film, copper tape, or temporary mirror vinyl on selected facets.
- Test only enough finish to judge the look.
- Do not spend time making the first shell perfect before size and clearance are proven.

Final finish:

- Copper/rose-gold mirror vinyl on flat opaque facets, or laser-cut mirrored acrylic/PETG facets.
- Frosted translucent plastic for lit facets and eyes.
- Dark seam lines or trim to preserve low-poly definition.

### Lighting

Head lighting should be internally mounted and diffused.

Recommended MVP lighting zones:

| Zone | MVP | Final |
|---|---|---|
| Eyes | 2 small LED clusters or strip pieces | Dedicated diffused eye modules |
| Face facets | 1-3 glowing translucent facets | 40-80 pixels behind selected facets |
| Whiskers | 1 hidden light engine per side | 2-4 pixels per side, or richer clusters if useful |
| Nose/muzzle | Optional single glow point | Optional accent tied to whisker/face behavior |

The face should avoid harsh raw LED glare unless a visible pixel texture is chosen intentionally.

### Mechanical Design

The first mount should be temporary, but the design should already respect final constraints.

Direction:

- Head rotates with handlebars.
- Preferred mount point is handlebar center/stem area.
- Add a safety tether even for mockups.
- Keep a removable back/access panel in the design if possible.
- Keep wiring exit near the handlebar/stem area.
- Use a quick-disconnect later so the bike can be returned to normal use.

The mount should never rely on the head shell alone. The shell is visual; the bracket carries the load.

### MVP Build Interpretation

The first build should be intentionally rough:

1. Choose the origami/faceted cat pattern.
2. Scale it near the 14 x 12 x 8 in target envelope.
3. Build the paper/cardboard/foamcore shell.
4. Add temporary mirror/copper finish to representative facets.
5. Add temporary eye diffusers.
6. Add temporary whiskers.
7. Hold or temporarily mount it near the handlebar/stem area.
8. Photograph front, side, and three-quarter views.
9. Decide whether to scale up/down before adding real lighting.

Use `cat-head-reference-v1.png` as the current visual target, with these MVP modifications:

- Simplify the neck/base into a compact hidden mount interface.
- Reduce whiskers to roughly 6-9 flexible strands per side.
- Use larger facets where possible so the shell can be cut from foamcore, cardboard, acrylic, or PETG.
- Prefer diffused cheek/muzzle glow over visible LED matrix panels.
- Add a rear access/wire-exit plan that is not visible from the front.

Use `cat-head-reference-v3.png` and `cat-head-reference-v4.png` as the active pair:

- `cat-head-reference-v3.png` defines the desired style and emotional read.
- `cat-head-reference-v4.png` defines the practical module direction: front/side/rear references, rear access panel, wire exit, and hidden mount points.

MVP build spec translated from V4:

| Feature | MVP Target |
|---|---|
| Starting envelope | 14 in wide x 12 in tall x 8 in deep |
| Structure | Cardboard, foamcore, or heavy cardstock low-poly shell |
| Face finish | Copper/rose-gold mirror film or metallic test finish on selected facets |
| Seam treatment | Dark seam lines, tape, paint, or shadow gaps to preserve facet definition |
| Eyes | Two cyan/aqua diffused slanted eye shapes |
| Face glow | 1-3 frosted translucent glowing facets, likely forehead/cheek/muzzle |
| Whiskers | 6-9 flexible strands per side, exiting from cheek/muzzle area |
| Rear service | Simple rear access panel or removable back area |
| Wire exit | Lower rear grommet or protected cable exit |
| Mount interface | Hidden rear/backplate points for temporary bracket and later final bracket |
| Safety | Lightweight shell, no sharp whisker tips, safety tether for bike tests |

Good MVP result:

- It clearly reads as a cat.
- The proportions feel intentional on the actual bike.
- It does not threaten steering, braking, rider sightline, or headlight use.
- The copper/faceted direction looks promising even before final materials.

Bad MVP result:

- It looks like a costume mask taped to the bike.
- The ears or whiskers interfere with controls.
- The face is visually busy but not readable.
- The eyes are weak compared with the rest of the lighting.
- The head is too heavy or too far forward.

## Current Recommendation

Proceed with the cat head MVP as the next design/build focus.

Do not start body panels or final tail fabrication until the head scale is validated. Body panels should visually support the head, not compete with it. The tail can be designed in parallel after the head envelope is known, because the head will set the level of polish and the final visual language.

## Open Decisions

- Which origami/faceted cat PDF will be the starting geometry?
- Exact scale after the first cardboard/foamcore test.
- Which facets are mirrored, translucent, or dark seam/trim.
- Eye diffuser material and exact eye shape.
- Fiber strand count and whisker fan geometry.
- Whether the first rideable shell is reinforced cardboard/foamcore, plastic, acrylic/PETG, or 3D printed.
- Final removable bracket design.
