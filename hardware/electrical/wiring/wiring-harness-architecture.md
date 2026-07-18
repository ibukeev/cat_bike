# Wiring Harness Architecture

## Purpose

Define the draft power and data wiring architecture for the Cat Bike LED installation. This is a planning document; final wire gauges and fuse ratings must be verified against actual parts, measured current, and physical routing.

## Current Electrical Decisions

- LED system uses a dedicated battery only; do not tap the bike battery.
- Primary LED system is 5 V addressable RGB LEDs.
- Battery chemistry target is standalone 12 V LiFePO4.
- Battery/main 12 V connector is XT60.
- Preferred converter is a 12 V to 5 V buck converter, 5 V 30 A class if quality and mounting are acceptable.
- Use fused 5 V branch distribution.
- Use removable connectors for serviceable LED zones.

## System Flow

```text
12 V LiFePO4 battery
  -> XT60 connector
  -> main fuse near battery
  -> master switch / emergency disconnect
  -> 12 V to 5 V buck converter
  -> fused 5 V distribution
  -> removable LED branch connectors
  -> LED zones
```

Keep the 12 V section short where practical. Put the buck converter near the distribution enclosure, not at a random LED zone.

## Draft Wire Gauges

| Run | Tentative Wire Gauge | Notes |
|---|---:|---|
| Battery to main fuse / switch / converter input | 12-14 AWG | Size for converter input current and main fuse. |
| Converter 5 V output to distribution block | 12-14 AWG | Higher current than 12 V side; keep short. |
| Lower frame branch | 16-18 AWG | Final choice depends on measured length/current. |
| Fork/front branch | 18 AWG | Modest current; keep protected around steering/fork movement. |
| Rear rack/basket branch | 16-18 AWG | May carry multiple rack/basket zones. |
| Cat head branch | 18 AWG | Locked 52-pixel, 3.12 A maximum load on a 4 A fused branch. |
| Tail reserved branch | 18 AWG | Future removable tail. |
| Body panel reserved branch | 16-18 AWG | Final choice depends on panel pixel count. |
| Data lines | 22-26 AWG typical | Route with ground; avoid long noisy runs without planning. |

Fuses protect wires. Final fuse values must match actual wire gauge and branch load.

## Branch Layout

| Branch ID | Branch | Phase | Power | Data | Notes |
|---|---|---|---|---|---|
| B1 | Lower frame spine | Phase 1 | Active | Active | Main visual Phase 1 branch. |
| B2 | Fork/front | Phase 1 + Phase 2A reserve | Active / reserved | Active / reserved | Fork accents now; cat head interface later. |
| B3 | Rear rack/basket | Phase 1 | Active | Active | Rack rib accents and basket underside glow. |
| B4 | Cat head | Phase 2A | 5 V / 4 A fused | S5 terminating range | M12 four-pin removable interface; head-local indices 0-51. |
| B5 | Tail reserved | Phase 2B | Reserved | Reserved | Removable tail connector near rear rack/basket. |
| B6 | Body panels reserved | Phase 3 | Reserved | Reserved | Capped branch connector near future panel zones. |

## Power Injection Policy

- Inject power at the start of each active branch.
- Inject at both ends for longer or higher-current LED runs.
- Do not rely on LED strip copper as the only long power path.
- Keep power and ground paired physically where practical.
- Share a solid ground reference between Pixelblaze/data and LED power.
- Use brightness limits in Pixelblaze so normal current remains below fuse and converter limits.

## Connector Policy

- XT60 for battery/main 12 V connection.
- Candidate removable LED branch connectors:
  - 3-pin 18 AWG waterproof LED pigtails for normal modest-current branches.
  - IP67 M12 A-coded four-pin connector, at least 4 A/contact, for the cat head.
- Avoid exposed JST-SM connectors on the final bike.
- Use capped connectors for reserved future branches.
- Add strain relief at every removable connector.

## Open Checks

- Measure actual under-rack and behind-seat mounting space.
- Choose exact battery size and physical battery dimensions.
- Choose exact converter model and enclosure.
- Record the purchased cat-head M12 part number and choose connector families for remaining removable zones.
- Confirm wire routing paths on the physical bike.
- Measure actual current draw during bench testing.
