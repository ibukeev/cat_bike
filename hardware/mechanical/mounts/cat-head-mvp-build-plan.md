# Cat Head MVP Build Plan

## Purpose

Build the minimum cat head prototype and support system needed to prove the Phase 2A concept on the bike.

This MVP is intentionally not the final playa-ready head. It should answer the important unknowns quickly:

- Does the head size feel right?
- Does it rotate safely with the handlebars?
- Does it preserve steering, braking, sightline, and headlight clearance?
- Does the faceted copper/rose-gold visual language work in real life?
- Do whiskers and simple internal lighting fit inside the head?

## MVP Scope

Current visual reference:

- [cat-head-reference-v1.png](../../../assets/references/cat-head/cat-head-reference-v1.png)
- [cat-head-reference-v3.png](../../../assets/references/cat-head/cat-head-reference-v3.png) - preferred current visual/style reference.
- [cat-head-reference-v4.png](../../../assets/references/cat-head/cat-head-reference-v4.png) - preferred current fabrication/reference-sheet direction.

### Build

- Cardboard, paper, or foamcore faceted cat head shell.
- Starting envelope near 14 in wide, 12 in high, 8 in deep.
- Temporary copper/rose-gold mirror film, Mylar, or metallic finish test on selected facets.
- Temporary translucent eye placeholders.
- Temporary whisker placeholders.
- Temporary handlebar/stem-area mount.
- Safety tether.
- Optional simple eye/facet/whisker lighting test.

### Do Not Build Yet

- Final acrylic/PETG shell.
- Final waterproofing.
- Final metal/plastic mounting bracket.
- Final quick-disconnect connector.
- Final Pixelblaze pattern.
- Final full-bike wiring harness.

## Track 1: Mechanical / Visual MVP

| Step | Task | Done When |
|---|---|---|
| 1 | Choose origami/faceted cat PDF or pattern | Pattern file/link is saved or referenced. |
| 2 | Build paper prototype | Full-size paper head exists at rough target scale. |
| 3 | Review paper prototype on bike | Front/side/rider-view photos confirm whether scale and silhouette are worth rebuilding. |
| 4 | Build cardboard/foamcore shell | Head exists at rough target scale with stronger material. |
| 5 | Add temporary finish | A few facets have mirror/copper/rose-gold treatment. |
| 6 | Add temporary eyes | Eye openings/diffusers are visible. |
| 7 | Add temporary whiskers | Whisker size and placement can be judged. |
| 8 | Temporary mount to bike | Head can be held near handlebar/stem area. |
| 9 | Clearance test | Full steering, brakes, headlight, cables, and rider sightline are checked. |
| 10 | Photo review | Front and side photos are captured for iteration. |

## Cardboard / Papercraft Approach

The MVP should be treated as low-poly papercraft or tabbed cardboard construction, not pure origami.

The accepted panel surface and reproducible workflow are tracked in [Cat Head Cardboard Fabrication V1](../fabrication/templates/cat-head-cardboard-fabrication-v1/README.md). Earlier paper-template experiments are local archive material rather than active design sources.

Pure origami is not the right constraint for this head because the design needs:

- A hollow internal volume for LEDs, wiring, and fiber-optic light engines.
- A rear access panel.
- A wire exit.
- Hidden mount points or a backplate.
- Different materials for mirrored opaque facets and translucent glowing facets.

Recommended construction approach:

1. Use the V4 fabrication reference as the shape guide.
2. Start with a simplified low-poly cat mask pattern or existing papercraft cat template.
3. Scale to the 14 in wide x 12 in tall x 8 in deep starting envelope.
4. Build from cardstock first if the pattern is unknown.
5. Rebuild in foamcore/cardboard after the shape feels right.
6. Add tabs, tape, hot glue, or small internal strips as needed; the folds do not need to be mathematically pure.
7. Leave the rear open or removable until LEDs, whisker routing, and the mount are understood.

MVP simplification rules:

- Use fewer, larger facets than the image shows.
- Keep the eyes, ears, muzzle, and cheeks readable.
- Do not model every small triangle from the AI reference.
- Use temporary marked translucent facets before cutting final diffuser openings.
- Keep the back practical even if the front is decorative.

Done when:

- A full-size cardboard/foamcore shell can be held at the bike handlebar/stem area.
- The shell reads as the V3/V4 cat head from front and side.
- Rear access, wire exit, and a possible mount area are physically visible.
- Scale and clearance can be judged before adding real LEDs.

## Track 2: Temporary Electrical Support MVP

Use the simplest safe electrical setup needed to light the head on the bench or in a driveway test.

Acceptable temporary power sources:

- Existing USB power bank for small 5 V LED tests.
- Existing 12 V battery with a 12 V to 5 V buck converter.
- Temporary bench supply if available.

Minimum temporary stack:

```text
temporary battery / bench supply
  -> fuse if using higher-current battery
  -> 5 V supply or buck converter
  -> Pixelblaze
  -> short LED harness
  -> cat head test LEDs
```

Temporary LED targets:

- Eyes: small 5 V pixel cluster or short strip.
- Facets: a few internal test pixels behind translucent material.
- Whiskers: hidden LED cluster lighting a small bundle of side-glow fiber or temporary substitute.

Safety rules:

- Keep brightness low during tests.
- Fuse temporary 12 V battery setups.
- Do not put loose wires near wheels, brakes, chain, pedals, or steering.
- Do not ride with the MVP head until the mount is secure.
- Use strain relief even on temporary head wiring.

## Initial Cat Head Lighting MVP

| Zone | MVP Implementation | Notes |
|---|---|---|
| Eyes | 2 small clusters or short LED strip pieces behind frosted placeholders | Proves eye shape and brightness. |
| Facet glow | 1-3 lit translucent facets | Proves internal glow concept without wiring the whole head. |
| Whiskers | 1 hidden LED cluster per side lighting fiber samples | Proves fiber whisker concept. |

## MVP Review Criteria

The MVP is successful if:

- The head reads as a cat from front and side.
- Scale feels close enough to refine.
- Head does not interfere with steering, brakes, rider sightline, headlight, or hands.
- Mirror/copper faceted finish looks promising.
- Whisker placement looks plausible.
- Lighting can fit inside without obvious glare or heat issues.
- The module can be removed from the bike without disturbing the normal bike setup.

## Next Decisions After MVP

- Keep or change head scale.
- Final mount type.
- Final shell material.
- Final facet finish: mirror vinyl vs mirrored plastic vs paint.
- Eye diffuser shape/material.
- Fiber whisker count and routing.
- Final connector type for the removable head.
