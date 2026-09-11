# Phase 1 body LED placement — resumable checkpoint

## Current review output

- `assets/photos/Concepts/Selected/Bio-Luminescent Abyssinian/Phase_1_LED_References/phase1-body-strip-placement-proposal-v1.png`
- Base geometry reference: `assets/photos/Original_bike/front_back/02-bike-side-profile-wide.jpg`
- Aesthetic reference: `assets/photos/Concepts/Selected/Bio-Luminescent Abyssinian/Gemini_Generated_Image_5en5a65en5a65en5.png`

## Proposed decisions shown

- Phase 1 uses exposed/removable 12 V addressable strips rather than illuminated body panels.
- The strongest visual line follows the fixed lower frame and step-through/belly curve.
- Secondary strips describe the upper rear haunch/rack, one rear support, the forward edge of the battery/torso area, and the underside of the basket.
- Cyan/teal is illustrative; Pixelblaze color and animation remain programmable.
- The proposal is a visual-placement study, not yet a cut-length or pixel-index drawing.

## Validation performed

- Compared the concept, the existing Phase 1 reference, and the real side-profile photograph.
- Corrected the first generated variant after it incorrectly placed LEDs on the front fork.
- Confirmed the retained routes visually sit on fixed frame/rack members and avoid wheels and spokes in this side view.

## Rejected or unsafe variants

- No LED strips on front fork legs, wheels, spokes, tires, or brake rotors.
- No fabricated glowing side panels in Phase 1.
- Do not treat the generated glow as proof of clearance; chain, crank, battery-removal, cable, and tire clearances require physical measurement before cutting.

## Exact regeneration recipe

Built-in `image_gen` edit flow:

1. Load the real side-profile photograph, the current Phase 1 LED reference, and the selected bioluminescent concept.
2. Generate a dusk placement mockup with narrow cyan/teal LED-node strips on the fixed lower belly/frame, upper rear haunch/rack, rear support, forward torso/battery edge, and basket underside.
3. Run a correction edit with the latest generated image as the only input and this instruction:

   `Remove the entire cyan LED strip from the front fork leg. There must be no LEDs on either fork leg, wheel, spokes, tire, brake rotor, or steering/moving component. Preserve the strips on the fixed lower frame and step-through belly curve, lower horizontal frame tube, rear upper haunch/rack tube, rear support strut, forward torso/battery edge, and basket underside. Preserve everything else unchanged.`

## Next physical-review steps

1. User reviews the silhouette and chooses which proposed lines to keep or remove.
2. Measure retained paths directly on the bike with a flexible tape.
3. Record segment lengths, LED counts, data directions, connectors, power injection, and zip-tie locations.
4. Produce left/right/front/rear fabrication overlays before cutting the waterproof strip.
