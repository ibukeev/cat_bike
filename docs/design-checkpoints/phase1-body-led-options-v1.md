# Phase 1 body LED option set — resumable checkpoint

## Current review files

- Comparison: `assets/photos/Concepts/Selected/Bio-Luminescent Abyssinian/Phase_1_LED_References/body-strip-design-options-v1/00-comparison-sheet.jpg`
- Individual options: `01-minimal-feline-silhouette.png`, `02-bioluminescent-dashes.png`, `03-feline-ribcage.png`, and `04-geometric-facet-echo.png` in the same folder.
- Option descriptions and fabrication implications: `body-strip-design-options-v1/README.md`.
- Exact built-in image-generation sequence: `body-strip-design-options-v1/generation-prompts.md`.

## Status and accepted constraints

- No visual direction is selected yet.
- Options use removable 12 V LED strips rather than permanent illuminated panels.
- Fork, wheel, tire, spoke, brake rotor, chain, crank, steering, cable, and moving-component lighting is excluded.
- The cat head should remain the main focal point; body lighting should support rather than overpower it.

## Validation

- Four distinct directions were generated from the real side-profile bike geometry.
- The labeled comparison sheet was visually checked after correcting its original label order.
- Options 1 and 2 mostly use existing tubes; options 3 and 4 require removable backing bars and more fabrication.

## Rejected/unsafe variants

- The earlier fork-mounted strip was rejected.
- Generated strip placement is not clearance proof and must not be used as a cutting template.

## Regeneration

Use the built-in `image_gen` edit flow and follow `body-strip-design-options-v1/generation-prompts.md` in order. The sequence uses the latest image as the sole edit input (`num_last_images_to_include: 1`).

## Next physical review

1. User selects option 1–4 or names elements for a hybrid.
2. Produce a refined selected-side visual, then a mirrored opposite-side visual.
3. Measure only the selected paths and create the cut-length, connector, data-direction, power-injection, and zip-tie map.
