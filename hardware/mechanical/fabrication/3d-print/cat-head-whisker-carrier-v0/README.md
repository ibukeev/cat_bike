# Cat Head Whisker Carrier V0

## Status

- Simplified two-part bench prototype; not released for the complete head.
- Eight independently driven 2 mm PMMA fibers per cheek.
- Two uncoated four-pixel WS2812B strip sections.
- Measured LED grid: 16.5 mm pitch, 66 mm cut length, and 10 mm strip width.
- The final curved head-side mounting bosses and cheek ports remain deferred.

## Design

The carrier has exactly two printable parts:

1. **Base** — two shallow strip channels, four captive M2.5 nut traps, and two
   integrated M3 mounting ears.
2. **Top** — eight isolated underside light cavities, eight 2.15 mm fiber holes
   extended by 5 x 6 mm exterior guide collars, four M2.5 assembly holes, and
   wiring reliefs at both ends.

The LED strips form a compact serpentine chain:

```text
DIN -> W1 -> W2 -> W3 -> W4
                            |
DOUT <- W8 <- W7 <- W6 <- W5
```

Rotate the second four-pixel strip 180 degrees. Join row-one `DOUT` to
row-two `DIN` at one end. Bring `+5V`, `GND`, `DIN`, and `DOUT`
out through the opposite top relief.

The top is the only fiber-specific part. Each exterior collar adds 6 mm of
straight gluing and support length without thickening the complete panel. The
fiber is guided for about 9.6 mm total between the collar and the roof above
the LED cavity. If the actual cable or printed-hole fit requires a different
diameter, change `top_hole_diameter_mm` and reprint only the top.

## Generated Files

- `output/whisker-carrier-base.stl`
- `output/whisker-carrier-top-2p15.stl`
- `output/whisker-carrier-v0-review.png`
- `output/whisker-carrier-v0-review.glb`
- `output/whisker-carrier-v0-validation.json`

## Generate

From the repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-whisker-carrier-v0/source/generate_whisker_carrier_v0.py
```

## Hardware

Prototype assumptions:

- Four M2.5 screws for the top.
- Four M2.5 nuts loaded into the underside traps before mounting the base.
- Two M3 screws through the integrated end ears into the future head-side
  structural bosses.
- Black printed material for the top to isolate the eight optical cells.
- A four-conductor service pigtail with strain relief away from the 2 mm pads.

The base is 86 x 36 x 3 mm including its mounting ears. The top plate is
74 x 36 x 6 mm, with collars extending its overall height to 12 mm. The
assembled plate stack is 9 mm, plus the 6 mm collars, before wiring and fiber
bend clearance.

## Assembly

1. Print the base with its strip channels facing up. Print the top with its
   LED-cavity side on the bed and the eight guide collars pointing up. Use no
   supports; the 10.5 mm cavity ceilings are short bridges. Inspect the center
   of each bridge and clear the 2.15 mm bore before inserting a fiber.
2. Confirm both 66 x 10 mm strip sections sit flat in the channels.
3. Insert four M2.5 nuts from the underside of the base.
4. Cut and place the two four-pixel strip sections with the second row reversed.
5. Solder the serpentine jumper, shared 5 V/ground, and service pigtail.
6. Add strain relief that does not load the short strip pads.
7. Place the top over the unpowered strips and confirm every cavity clears its
   LED and nearby passive components.
8. Secure the top with four M2.5 screws.
9. Insert polished fibers through the guide collars until their faces are
   approximately 0-0.5 mm above the LED lenses, then mark their insertion
   depth externally.
10. After the optical test passes, secure each fiber in its collar with a small
    amount of PMMA-compatible flexible adhesive. Keep adhesive out of the bore
    below the collar and off the polished end face.
11. Test one pixel at a time before running the complete eight-fiber pattern.

## V0 Acceptance Criteria

- Both strip sections lie flat without crushing LEDs or passive components.
- Every fiber hole centers over its LED.
- Each fiber can be inserted and removed without shaving, binding, or stress
  whitening.
- No visible light crosses into an adjacent optical cavity at 60% brightness.
- Wiring exits without pinching and cannot pull directly on the solder pads.
- Four top screws can be removed without disturbing the head mounting ears.
- The assembled carrier survives three open/close cycles without stripped
  plastic, loose nuts, or damaged fibers.
- Full-white current remains at or below 0.48 A for the eight-pixel carrier.

## Head Integration After the Coupon

The final head receives two reinforced M3 bosses matching the base ears. Those
bosses must bridge into opaque cheek ribs or dedicated internal structure, not
only the 1.8 mm exterior skin and never a removable glow panel.

The base remains mounted inside the cheek while the top is removed for fiber or
LED service. The cheek ports and soft grommets establish the visible whisker
directions and carry external flex loads. Preserve at least a 20 mm fiber bend
radius between the top and cheek ports.

## Remaining Measurements

- Exact fiber diameter at three points.
- Exact LED-strip total thickness.
- Printed 2.15 mm top-hole fit.
- M2.5 nut-trap fit.
- Wiring-relief clearance after soldering.
- Final M3 boss locations in the left and right lower-face shells.

## Resume Checkpoint

The accepted V0 direction is a two-part carrier: one common base and one
fiber-specific top. Do not restore the discarded slide dock, keeper, or separate
fiber-insert plates unless a physical test demonstrates a need. After the flat
coupon passes, add mirrored M3 mounting bosses to the head interior and validate
rear access and 20 mm fiber routing before changing the production shell.
