# Universal Pixelblaze Controller Box V1

## Decision

Use the in-hand Pixelblaze V3 Pico for Phase 1. Keep enough free tray space for
a Pixelblaze V3 Standard so either controller can be installed without changing
the enclosure, external connectors, converter, or bike harness.

The existing Controller Box V0 shell already satisfies this requirement:

- Enclosure body: 132 x 92 x 42 mm, excluding mounting ears.
- Electronics tray: 118 x 78 mm.
- Standard controller envelope: 39.5 x 34.2 mm, including antenna.
- Pico envelope: 33.3 x 11 mm.

Do not enlarge the outer box for the Pico. The switch, wire bend radius, converter,
connector panel, and service access dominate the enclosure size.

## Simple Controller Installation

The controller location reserves the larger Standard board envelope. For the MVP,
the Pico may lie loose inside the closed enclosure. No printed adapter, carrier,
or clip is required.

Put the Pico in a nonconductive sleeve or loose heat-shrink wrap so its pads cannot
touch the converter, fasteners, or other conductors. Anchor the incoming and
outgoing harness to the tray or enclosure so the Pico does not hang by its solder
pads. Keep the antenna end uncovered and away from metal and bundled power wire.

When using the Standard later, install it in the same reserved tray area with a
simple removable mounting method appropriate to the physical board.

## Power Architecture

Use one existing Magnolora 12 V to 5 V, 3 A converter as a dedicated controller
supply:

```text
protected switched 12 V
  -> dedicated Magnolora 12 V to 5 V converter
  -> keyed low-current controller plug
  -> selected Pixelblaze
       -> data + common ground to LED harness
```

Reserve at least 200 mA at 5 V for the Pixelblaze. A 3 A converter has ample
capacity for the controller but is not the body-LED supply.

- Never connect 12 V to the Pico.
- Do not pass 12 V body-strip current through either Pixelblaze.
- Do not parallel the outputs of multiple 5 V converters.
- Use a separate 5 V branch/converter for the 5 V cat head.
- Join controller ground, 12 V LED ground, and 5 V head ground at the protected
  distribution ground.

## Plug-and-Play Controller Interface

Use the same internal low-current harness for either controller:

| Pin | Signal | Requirement |
|---|---|---|
| 1 | +5 V controller power | Keyed; verify polarity before insertion |
| 2 | Ground | Common with all LED power supplies |
| 3 | Data out | Routes to the first whole-bike LED input |
| 4 | Reserved/button | Optional; cap if unused |

The external LED and battery connectors remain on the replaceable connector
panel and do not move when the controller changes.

## Internal Layout Zones

- Power-entry zone: protected switched 12 V input and strain relief.
- Conversion zone: the Magnolora module, retained by adjustable ties with airflow.
- Logic/RF zone: reserved Standard-sized tray area next to a plastic wall.
- Connector zone: replaceable connector panel with labeled, keyed connections.

Keep the controller antenna end away from metal fasteners, the converter, bundled
power wire, and metallic coatings. Preserve a 10 mm minimum no-metal service
region around the antenna as a provisional build rule, then verify Wi-Fi with the
lid closed.

## What Is Still Provisional

- Physical Pico antenna end and safe insulation boundary.
- Standard board mounting-hole locations and tallest component.
- Actual Magnolora body and rigid wire-exit dimensions.
- Final internal controller connector family.
- Final connector-panel cutouts.

The configured PCB envelopes prove that both controllers fit the enclosure.

## Bench Acceptance Tests

1. Confirm 5.0 V at the unplugged controller connector and verify polarity.
2. Insulate the Pico, strain-relieve its harness, and confirm cable loads do not
   reach its solder pads.
3. Confirm the antenna end has no metal or power bundle in its keepout region.
4. Power the Pico with LEDs disconnected, then with the data harness connected.
5. Run the 12 V body strip from its separate fused power branch.
6. Verify a common ground and stable data with riding and show brightness caps.
7. Close the lid and run a 30-minute thermal and Wi-Fi test.
8. Repeat controller-power, fit, and Wi-Fi checks after swapping to the Standard.
