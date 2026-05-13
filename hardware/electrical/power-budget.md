# Power Budget

## Purpose

Estimate LED current, battery needs, fuse sizing, and runtime for the Cat Bike LED installation.

## Current Assumptions

- Controller: Pixelblaze or Pixelblaze-compatible setup.
- Main visual palette: cyan/aqua/magenta/violet with brightness limits.
- Bike use case: Burning Man night riding with a lower-power riding mode and brighter parked/show mode.
- Tentative electrical decision: use 5 V addressable LEDs as the primary LED system.
- Electrical decision: use a dedicated LED battery only. Do not tap or modify the bike traction battery.
- Phase 1 should include independent LED zones and reserved interfaces for later head, tail, panel, and wheel zones.
- Battery and power distribution should be sized for the likely whole-bike build, not just the first installed Phase 1 zones.
- Phase 1 should reserve fused branch capacity and connectors for later cat head, tail, and body panel loads.
- Whiskers are planned as side-glow fiber optics lit by hidden LEDs inside the cat head, not LEDs installed along each whisker.

## Phase 1 LED Count Estimate

| Zone | Estimated Pixels | Notes |
|---|---:|---|
| Lower frame segmented spine | 60-120 | Main Phase 1 visual zone. |
| Fork gill accents | 24-60 | Short segments on both fork legs. |
| Rear rack rib accents | 40-100 | Repeated short segments on rack supports. |
| Basket underside glow | 30-80 | Hidden glow under basket bottom edge. |
| Ground underglow | 30-80 | Downward-facing visibility/glow; may share physical LEDs with lower frame/rack zones. |

Initial Phase 1 installed planning range: 184-440 pixels before cat head, tail, body panels, or wheels. This is intentionally broad until actual LED density and measured path lengths are selected.

## Future Whole-Bike LED Count Estimate

The power system should support later expansion without rebuilding the main battery, fuse, switch, and distribution architecture.

| Phase | Zone | Low Pixels | Nominal Pixels | High Pixels | Notes |
|---|---|---:|---:|---:|---|
| Phase 1 | Lower frame segmented spine | 60 | 90 | 120 | Active first build. |
| Phase 1 | Fork gill accents | 24 | 40 | 60 | Active first build. |
| Phase 1 | Rear rack rib accents | 40 | 70 | 100 | Active first build. |
| Phase 1 | Basket underside glow | 30 | 50 | 80 | Active first build. |
| Phase 1 | Ground underglow | 30 | 50 | 80 | Active first build; may overlap with frame/rack LEDs. |
| Phase 2A | Cat head facets | 40 | 80 | 140 | Depends on mask/head size and diffuser method. |
| Phase 2A | Eyes | 8 | 16 | 32 | Small but visually important. |
| Phase 2A | Fiber-optic whisker light engines | 4 | 8 | 16 | Hidden LEDs drive side-glow fiber bundles; lower load than LED whiskers. |
| Phase 2B | Tail | 30 | 80 | 160 | Depends on length and density. |
| Phase 3 | Body panels | 80 | 180 | 360 | Depends heavily on panel geometry and diffuser strategy. |
| Phase 4 | Optional wheels | 0 | 0 | 240 | Deferred; do not size baseline requirement around this unless explicitly included. |

| Scenario | Included Scope | Total Pixels |
|---|---|---:|
| Phase 1 low | Installed starter zones only | 184 |
| Phase 1 nominal | Installed starter zones only | 300 |
| Phase 1 high | Installed starter zones only | 440 |
| Whole bike low, no wheels | Phase 1 + head + eyes + fiber whiskers + tail + modest panels | 346 |
| Whole bike nominal, no wheels | Phase 1 + head + eyes + fiber whiskers + tail + panels | 664 |
| Whole bike high, no wheels | Phase 1 + head + eyes + fiber whiskers + tail + dense panels | 1,108 |
| Whole bike high, with wheels | High whole-bike build plus optional wheels | 1,348 |

## Current Estimate Formula

For WS2812-style 5 V pixels, worst-case current is commonly estimated as:

```text
max_current_amps = pixel_count * 0.06
```

For practical animation use, plan a brightness-limited estimate:

```text
typical_current_amps = max_current_amps * brightness_limit * pattern_factor
```

Initial planning values:

- `brightness_limit`: 0.25 to 0.50
- `pattern_factor`: 0.35 to 0.70

## Current Draw Scenarios

These estimates assume 5 V addressable RGB pixels at 60 mA maximum per pixel. Real patterns should be brightness-limited well below full-white maximum.

| Scenario | Pixels | Theoretical Max Current @ 5 V | Practical Current @ 25% brightness, 50% pattern | Practical Current @ 40% brightness, 60% pattern |
|---|---:|---:|---:|---:|
| Phase 1 low | 184 | 11.0 A | 1.4 A | 2.6 A |
| Phase 1 nominal | 300 | 18.0 A | 2.3 A | 4.3 A |
| Phase 1 high | 440 | 26.4 A | 3.3 A | 6.3 A |
| Whole bike low, no wheels | 346 | 20.8 A | 2.6 A | 5.0 A |
| Whole bike nominal, no wheels | 664 | 39.8 A | 5.0 A | 9.6 A |
| Whole bike high, no wheels | 1,108 | 66.5 A | 8.3 A | 16.0 A |
| Whole bike high, with wheels | 1,348 | 80.9 A | 10.1 A | 19.4 A |

Planning implication: design the main distribution so it can eventually handle roughly 10-17 A practical whole-bike current without wheel effects, while fusing branches so Phase 1 can run safely at a smaller installed load.

## Battery Energy Scenarios

At 5 V, approximate LED energy draw is:

```text
watts = volts * amps
runtime_hours = battery_usable_watt_hours / watts
```

Rough usable energy examples:

| Battery Pack | Nominal Energy | Usable Planning Energy | Notes |
|---|---:|---:|---|
| Small USB-C/power bank style pack | 74 Wh | 55-65 Wh | Good for testing or short Phase 1 use only. |
| Medium dedicated LED pack | 150 Wh | 115-130 Wh | Better Phase 1 riding target. |
| Large dedicated LED pack | 250 Wh | 190-220 Wh | Better for whole-bike expansion. |
| Very large dedicated LED pack | 400 Wh | 300-350 Wh | Heavy, but supports longer show modes. |

Approximate runtime at practical current:

| Scenario | Practical Current | LED Watts @ 5 V | 150 Wh Pack Usable 120 Wh | 250 Wh Pack Usable 200 Wh | 400 Wh Pack Usable 320 Wh |
|---|---:|---:|---:|---:|---:|
| Phase 1 nominal, conservative | 2.3 A | 11.5 W | 10.4 hr | 17.4 hr | 27.8 hr |
| Phase 1 nominal, brighter | 4.3 A | 21.5 W | 5.6 hr | 9.3 hr | 14.9 hr |
| Whole bike nominal, conservative | 5.0 A | 25.0 W | 4.8 hr | 8.0 hr | 12.8 hr |
| Whole bike nominal, brighter | 9.6 A | 48.0 W | 2.5 hr | 4.2 hr | 6.7 hr |
| Whole bike high, brighter | 16.0 A | 80.0 W | 1.5 hr | 2.5 hr | 4.0 hr |

## Battery Type Options

| Option | Fit | Pros | Cons | Recommendation |
|---|---|---|---|---|
| USB-C phone-style power bank | Bench testing or tiny demo only | Cheap, easy to charge, removable | Output current too low for whole-bike 5 V loads; may auto-shutoff; poor weather/dust fit | Do not use as final battery |
| Small portable power station, 80-125 Wh | Testing or short Phase 1 use | Integrated charger and enclosure | Too little energy for 6-8 hr target as build expands; bulky for capacity | Not recommended for final build |
| Portable power station, 220-300 Wh | Possible Phase 1 or moderate build | Integrated charger, multiple outputs, easy to use | Inefficient if using AC outlet; may be bulky; 12 V DC output current must be verified | Possible if already owned, but not preferred |
| 12 V LiFePO4 standalone battery, 15-16 Ah | Phase 1 with limited expansion | Light, cheap, safer chemistry | Marginal for whole-bike 6-8 hr riding target | Acceptable only if minimizing size/cost |
| 12 V LiFePO4 standalone battery, 20 Ah | Baseline recommendation | Around 256 Wh, good weight/runtime balance, common chargers | Whole-bike brighter runtime still requires brightness discipline | Recommended starter battery |
| 12 V LiFePO4 standalone battery, 30 Ah | More runtime margin | Around 384 Wh, better whole-bike target | Larger/heavier; harder to mount | Recommended if physical mounting works |
| 12 V LiFePO4 standalone battery, 50 Ah | Very long runtime | Huge energy margin | Likely too large/heavy for this bike; mounting and crash load become serious | Avoid unless there is a strong reason |
| Lead-acid motorcycle/car battery | Poor fit | Cheap and available | Heavy, low usable capacity per pound, awkward charging and mounting | Avoid |

## Battery Decision

- Use a dedicated standalone battery for the LED system.
- Do not touch the bike traction battery.
- Preferred chemistry: LiFePO4.
- Preferred architecture: 12 V LiFePO4 battery feeding a fused 5 V buck converter and 5 V branch distribution.
- Baseline size: 12 V 20 Ah LiFePO4, about 256 Wh.
- Higher-margin size: 12 V 30 Ah LiFePO4, about 384 Wh, if it fits cleanly.
- Avoid two smaller batteries in parallel.
- If carrying two batteries, use one installed battery plus one charged spare, swapped manually.

## Charging Plan

- Use a charger made for 12 V LiFePO4 / 4S LiFePO4 batteries.
- Typical full-charge voltage: 14.4-14.6 V.
- For a 20 Ah battery, a 2 A charger is slow but gentle; a 5 A charger is a practical default.
- Charge the battery off-bike or in a removable enclosure when practical.
- Do not use a random lead-acid car charger unless it explicitly supports LiFePO4 mode.
- Do not charge from the bike battery.

## Mounting Direction

Candidate locations:

| Location | Pros | Cons | Current Read |
|---|---|---|---|
| Under rear rack | Hidden, close to rear wiring, preserves basket cargo space | Needs very secure bracket, waterproofing, tire clearance, and service clearance | Preferred battery location if clearance and bracket work |
| Behind seat / between seat post and basket | Accessible, protected from tire debris, close to rear wiring | Limited space; must avoid rider, seat adjustment, and future tail/body work | Preferred distribution enclosure location; possible battery location if dimensions work |
| Inside basket in removable box | Easiest MVP access and removal | Uses cargo space; visible; theft/weather exposure | MVP fallback for battery and/or electronics |
| Frame/step-through area | Lower center of gravity | Likely conflicts with rider, pedals, battery access, removability | Avoid unless measurements prove it works |

Mounting requirements:

- Battery must be removable after Burning Man.
- Battery must be mechanically retained against vibration and bumps.
- Battery mount must not block cargo use more than intended.
- Battery must not interfere with rider legs, pedals, chain, wheels, brakes, or bike battery access.
- Use a fused output close to the battery.
- Do not mount the battery under the rack unless tire clearance and bracket strength are verified.
- MVP fallback: store the battery in a secured removable box inside the basket.

Current mounting decision:

- Use some combination of under-rack and behind-seat/basket-area mounting.
- Prefer battery under the rear rack if a safe bracket and tire clearance are confirmed.
- Prefer power distribution behind the seat or at the front edge of the basket/rack area for service access.
- If custom mounting is not ready for MVP, use a secured removable battery/electronics box inside the basket.

## Fuse Strategy

Fuses are required because the LED battery can deliver high current into a short. Fuses are primarily there to protect wiring, connectors, the battery, and the bike. They are not mainly there to protect LEDs or the Pixelblaze.

Likely fault cases:

- LED strip wire rubs through on the frame.
- Connector gets dusty, wet, damaged, or plugged incorrectly.
- Cable gets pinched under the basket, rack, panel, head, or tail mount.
- Removable sculpture wiring is damaged during transport or installation.
- A converter or branch module fails internally.

Minimum acceptable protection:

- Main fuse close to the LED battery positive terminal.

Preferred protection:

- Main fuse close to the LED battery.
- Master switch after the main fuse.
- 12 V to 5 V buck converter.
- Fused 5 V branch distribution so one failed zone does not take down or overheat the whole harness.

Tentative branch strategy:

| Branch | Purpose | Tentative Fuse | Notes |
|---|---|---:|---|
| Lower frame spine | Main Phase 1 frame lighting | 5 A | Size final fuse to actual wire and measured load. |
| Fork/front | Fork gill accents and future front interface | 2-3 A | Keep front wiring light and protected. |
| Rear rack/basket | Rear rack ribs and basket underside glow | 5 A | May be split later if basket and rack are removable separately. |
| Cat head reserved | Future head facets, eyes, whisker light engines | 3-5 A | Use quick disconnect and strain relief. |
| Tail reserved | Future illuminated tail | 3-5 A | Use quick disconnect and safety tether. |
| Body panels reserved | Future panel-integrated LEDs | 5-10 A | Final value depends on panel LED count. |

Tentative main fuse and converter pairing:

| Converter | 5 V Output Power | Approx. 12 V Input Current | Suggested 12 V Main Fuse | Notes |
|---|---:|---:|---:|---|
| 5 V 20 A | 100 W | 9-11 A | 10 A | Good for Phase 1 and modest expansion. |
| 5 V 30 A | 150 W | 14-16 A | 15 A | Preferred for future head, tail, and panels. |

Current recommendation:

- Use a 5 V 30 A buck converter if size and quality are acceptable.
- Use a 15 A main fuse on the 12 V battery side.
- Use fused 5 V branch distribution.
- Keep normal operation below fuse limits using Pixelblaze brightness limits.
- Final fuse ratings must match actual wire gauge, converter, and measured current.

## Connector Strategy

Connector requirements:

- Polarized or keyed where possible.
- Resistant to dust, moisture, and vibration.
- Easy to disconnect for transport, repair, and post-Burning-Man removal.
- Rated for the branch current.
- Strain relieved so cable movement does not stress solder joints or terminals.

Current connector decisions:

- Battery/main 12 V connector: XT60.
- Do not use JST-SM as exposed final bike connectors; use them only for bench testing or inside sealed enclosures if unavoidable.

Removable LED zone connector options:

| Connector Type | Pros | Cons | Best Use | Status |
|---|---|---|---|---|
| 3-pin 18 AWG waterproof LED pigtails | Cheap, simple, compact, already matches `+5V/GND/DATA`, easy to buy in packs | Amp rating may be unclear; quality varies; limited to one data line; compatibility varies between sellers | Normal modest-current LED branches such as fork, rack/basket, tail, simple panel sections | Candidate |
| M8/M12 waterproof circular connectors | More robust, threaded/locking, available in 3/4/5 pin, cleaner for serviceable modules | Bulkier, more expensive, soldering/crimping can be fiddly | Cat head, future panels, higher-confidence removable modules | Candidate |
| XT30 | Good compact power connector | Power only, not waterproof by itself | Optional small power-only branch connector inside enclosure or protected area | Optional |
| XT60 | High-current, common, polarized | Power only, not waterproof by itself | Battery/main 12 V connection | Decision |

Suggested 3-pin LED branch pinout:

- `+5V`
- `GND`
- `DATA`

For cat head and future panels, consider 4-pin or 5-pin connectors if we want a spare data line, second ground, separate power grouping, or future expansion.

## Design Targets

- Fuse the LED supply close to the battery.
- Include a reachable master switch or emergency disconnect.
- Keep controller power separate from high-current LED injection paths where practical.
- Use power injection for long LED runs.
- Document voltage drop assumptions before final wiring.
- Prefer a main power architecture that can support later whole-bike expansion without rewiring the battery, master fuse, switch, and distribution enclosure.
- Use separately fused branch circuits for front/head, lower frame, rear rack/basket, tail, and future panels.
- Use capped weather-resistant connectors for reserved future branches.
- Use parallel 5 V branches rather than one long LED power path.
- Inject power at zone starts and at both ends where needed.
- Keep the LED system electrically independent from the bike traction battery.
- Do not tap, splice, or modify the bike battery or bike electrical system.
- Use one main LED battery by default. Do not parallel smaller batteries unless the system is intentionally designed for that.
- Use branch fuses to isolate removable zones and make field repair safer.
- Use XT60 for the battery/main 12 V connector.
- Keep M8/M12 waterproof circular connectors and 3-pin 18 AWG waterproof LED pigtails as candidate connector families for removable LED zones.

Detailed draft wiring architecture is tracked in [Wiring Harness Architecture](wiring/wiring-harness-architecture.md).

## Runtime Planning

| Mode | Brightness | Runtime Target | Notes |
|---|---:|---:|---|
| Riding | 25-35% tentative cap | 6-8 hr | Primary runtime target for normal night riding. |
| Parked/show | 50-60% tentative cap | 2-4 hr | Planning target for brighter effects; not additive with riding target. |
| Low power | 10-15% tentative cap | 1 hr minimum reserve | Backup mode for end-of-night riding. |

Runtime targets are mode-specific. The system does not need to run 6-8 hours of riding plus 2-4 hours of show mode at full brightness in the same night, but battery sizing should preserve a low-power reserve after normal use.

Tentative brightness policy:

- Use 25-35% max brightness for riding mode.
- Use 50-60% max brightness for parked/show mode.
- Use 10-15% max brightness for low-power reserve mode.
- Keep an initial absolute system brightness cap around 60%.
- Fine tune after bench current measurements and outdoor night visibility tests.

## Decisions Needed

- LED voltage: 5 V vs 12 V addressable LEDs. Tentative decision: 5 V primary system.
- Battery source: dedicated LED battery vs bike battery tap. Decision: dedicated LED battery only; do not touch bike battery.
- Target runtime. Decision: 6-8 hours riding mode, 2-4 hours show/parked planning target, 1 hour low-power reserve.
- Maximum acceptable LED brightness. Tentative decision: 25-35% riding, 50-60% show, 10-15% reserve, 60% initial absolute cap.
- Whether wheel lighting is in the first electrical design.
- Dedicated LED battery size and mounting location.
- Battery type. Decision: standalone 12 V LiFePO4 preferred; 20 Ah baseline, 30 Ah if mounting works.
- Main fuse rating and branch fuse strategy. Tentative recommendation: 5 V 30 A buck converter, 15 A main fuse on 12 V side, fused 5 V branch distribution.
- Power distribution enclosure location. Tentative decision: behind seat / front basket-rack area if space works; MVP fallback is inside-basket removable box.
- Connector family for removable head, tail, panel, and basket/rack zones. Decision: XT60 for battery/main 12 V; removable LED zone connectors still choosing between M8/M12 waterproof circular connectors and 3-pin 18 AWG waterproof LED pigtails.
