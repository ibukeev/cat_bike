# Power Enclosure Plan

## Purpose

Plan the physical mounting and enclosure strategy for the LED battery, fuse, switch, 12 V to 5 V converter, Pixelblaze controller, and branch distribution.

## Current Direction

Use a rear-area mounting strategy:

- Battery under the rear rack if clearance and bracket strength are verified.
- Electronics/distribution box behind the seat or at the front edge of the basket/rack area.
- MVP fallback: secured removable box inside the basket.

Do not touch or modify the bike traction battery.

## Preferred Architecture

### Two-Box Layout

| Box | Contents | Preferred Location | Notes |
|---|---|---|---|
| Battery mount / battery enclosure | 12 V LiFePO4 battery, XT60 battery lead, main fuse close to battery | Under rear rack if clearance works | Must be rigid, waterproof/dust resistant, removable, and mechanically retained. |
| Electronics / distribution enclosure | Master switch, 12 V to 5 V buck converter, Pixelblaze, fused 5 V branch distribution, service connectors | Behind seat / front basket-rack area | Easier fuse/switch/controller access than under-rack mounting. |

This keeps the battery mass low/hidden while keeping service electronics more accessible.

### MVP Fallback

Use one secured removable box inside the basket containing:

- Battery.
- Main fuse.
- Master switch.
- 12 V to 5 V converter.
- Pixelblaze.
- Fused branch distribution.

This sacrifices cargo space but is easiest to build, inspect, charge, and remove after Burning Man.

## Location Options

| Location | Best For | Pros | Risks / Requirements |
|---|---|---|---|
| Under rear rack | Battery | Hidden, preserves basket cargo space, close to rear wiring | Must verify tire clearance, bracket strength, waterproofing, and removal access. |
| Behind seat / between seat post and basket | Electronics distribution, maybe battery if small enough | Accessible, protected from tire spray, close to rear wiring | Must avoid rider, seat adjustment, basket, future tail, and body-panel work. |
| Inside basket | MVP combined box or removable spare battery | Easiest access and removal | Uses cargo space, visible, needs cargo-impact protection and anti-theft awareness. |
| Frame/step-through | Avoid | Lower center of gravity | Likely conflicts with rider, pedals, battery access, and year-round removability. |

## Mechanical Requirements

- No permanent glue directly on the painted bike frame.
- No zip-tie-only battery mount.
- Use bolted brackets, metal straps, clamp plates, or a rigid cradle for the battery.
- Add rubber isolation where clamps contact frame/rack tubes.
- Add a secondary safety strap or tether for the battery enclosure.
- Enclosure must not be the lowest point under the rack.
- Enclosure must not interfere with tire, wheel removal, brake hardware, chain, pedals, kickstand, or rider movement.
- Battery and electronics must be removable after Burning Man.
- All cable exits need strain relief.

## Environmental Requirements

- Dust-resistant and splash-resistant enclosure.
- Cable glands, sealed bulkhead connectors, or downward-facing protected cable exits.
- Avoid openings that face upward into dust/water.
- Converter heat must have a path out; do not fully bury a hot buck converter in foam.
- Avoid placing connectors where dust/water can pool.

## Service Requirements

- Master switch must be reachable.
- Main fuse should be close to the battery and inspectable.
- Branch fuses should be accessible without disassembling sculpture.
- Battery should be removable for charging when practical.
- Branch connectors should be labeled.
- Reserved head, tail, and panel connectors should be capped when unused.

## Measurement Checklist

Measure before buying or fabricating the final enclosure:

- Under-rack clearance from rack underside to highest tire point.
- Available under-rack length and width.
- Behind-seat space between seat post and basket.
- Basket internal footprint if using MVP fallback box.
- Candidate 20 Ah and 30 Ah battery dimensions.
- Wheel/tire clearance with rider weight and vibration margin.
- Cable route from rear power area to lower frame and fork.

## Current Recommendation

Start with the two-box architecture as the target:

- Battery under rear rack if the physical measurements are favorable.
- Electronics/distribution behind seat or front basket-rack area.

Keep the inside-basket removable box as the MVP fallback if under-rack mounting becomes too slow or risky.
