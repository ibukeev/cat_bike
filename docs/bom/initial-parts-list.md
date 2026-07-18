# Initial Parts List

## Purpose

Track candidate parts for the Bio-Luminescent Abyssinian Cat Bike. This is a planning list, not a final purchase list.

## Electronics

| Item | Qty | Status | Notes |
|---|---:|---|---|
| Pixelblaze V3 Standard-compatible controller | 1 | Selected / needed | One central controller and one initial data output. |
| Cat-head addressable LEDs | 52 | Inventory check | 5 V RGB WS2812/SK6812-compatible: 16 whisker, 8 eye, and 28 facet pixels. Existing parts may be used when protocol and voltage match. |
| 12 V LiFePO4 battery | 1 | Recommended | Baseline: 20 Ah / about 256 Wh. Consider 30 Ah / about 384 Wh if mounting works. |
| 12 V LiFePO4 charger | 1 | Recommended | Use charger intended for 12 V / 4S LiFePO4 batteries, typically 14.4-14.6 V output. 5 A is a practical default for 20 Ah. |
| 12 V to 5 V buck converter | 1 | Needed | Size for Phase 1 plus future expansion; likely 5 V 20-30 A class depending on final branch plan. |
| Fuse holder and fuses | TBD | Needed | Size after power estimate. |
| Master switch or emergency disconnect | 1 | Needed | Must be reachable. |
| XT60 connector pair | TBD | Needed | Battery/main 12 V connector decision. |
| Cat-head M12 A-coded 4-pin connector pair and cap | 1 set | Selected / buy after coupons | IP67 and at least 4 A/contact; temporary connectors are acceptable for bench work. |
| Wire | TBD | Needed | Gauge depends on current and run length. |
| Heat shrink and sleeving | TBD | Needed | Dust and strain relief. |

## Sculpture and Lighting Materials

| Item | Qty | Status | Notes |
|---|---:|---|---|
| Cat mask/head base | 1 | Needed | Ready-made or fabricated. |
| Copper/rose-gold finish material | TBD | Needed | Paint, film, or metallic panels. |
| Frosted PETG diffuser samples | 1.0 and 1.5 mm | Needed for Gate L1 | Compare sheet and printed samples at 20, 25, and 30 mm setback. |
| Bare 2.0 mm side-emitting PMMA fiber | 9 m | Ordered; due 2026-07-16 | User-confirmed order. Reserve one sacrificial coupon length before cutting fourteen 320 mm development strands. |
| Eight-pixel RGB whisker light engines | 2 | Inventory check | One 5 V WS2812/SK6812-compatible stick per cheek; seven direct-coupled fibers and one masked pixel. |
| Tail structure material | 1 | Needed | Flexible or rigid TBD. |
| Mounting brackets | TBD | Needed | For cat head, tail, controller, battery, LEDs. |


## Cat Head Lighting Prototype

Use existing parts when they meet the listed interface. Record manufacturer,
part number, measured dimensions, and quantity before Gate L1 approval.

| Prototype Item | Qty | Timing | Notes |
|---|---:|---|---|
| Bare 2.0 mm side-glow PMMA fiber | 9 m | Ordered; due 2026-07-16 | Critical-path material secured for the first one-pixel/one-fiber coupon, cheek coupon, final strands, and repair stock. |
| Optional 1.5 mm and 3.0 mm side-glow samples | 1 m each | Optional now | Compare flexibility and brightness without delaying the 2.0 mm baseline. |
| 5 V addressable RGB pixel modules or strip | At least 16 pixels | Verify now | Existing WS2812/SK6812/NeoPixel parts are acceptable for whisker coupons. |
| Dense 5 V RGB eye pixels | 8 pixels | Verify before eye coupon | Four pixels per eye. |
| 5 V RGB facet pixels | 28 pixels | Verify before facet cassettes | Two pixels per approved glow panel. |
| Current-limited 5 V bench supply | 2 A coupon / 5 A full head | Verify now | Temporary USB or bench power is acceptable for the first optical coupon. |
| 1,000 uF capacitor, at least 10 V | 1 plus spare | Before full-head wiring | Install across 5 V and ground at the head entrance. |
| Temporary 3-wire connectors | As needed | Use existing | Bench-only 5 V, ground, and data connections; M12 is not required for Gate L1. |
| Black heat-shrink or opaque coupling tube | Assorted | Before fiber arrives | Blocks light leakage around temporary LED-to-fiber couplers. |
| Fresh razor or POF cutter and fine abrasive | 1 set | Before fiber arrives | Produce square input faces and safely rounded external tips. |
| TPU/silicone grommet and clear tip-cap samples | Assorted | During Gate L1 | Validate port abrasion protection and non-pokey external tips. |
| IP67 M12 A-coded 4-pin connector and cap | 1 set | After optical coupons | Purchase only after confirming cable gauge, routing, and panel-mount geometry. |
## Mechanical and Safety

| Item | Qty | Status | Notes |
|---|---:|---|---|
| Rubber-lined clamps | TBD | Needed | Protect frame paint and reduce vibration. |
| Zip ties or reusable cable ties | TBD | Needed | Use with strain relief. |
| Fasteners | TBD | Needed | Stainless preferred. |
| Safety tether material | TBD | Needed | For cat head and other removable sculpture. |
| Weather/dust enclosure | TBD | Needed | Controller and power distribution. |

## Spares and Repair Kit

| Item | Qty | Status | Notes |
|---|---:|---|---|
| Spare LEDs | TBD | Later | Match final LED type. |
| Spare connectors | TBD | Later | Match final harness. |
| Spare fuses | TBD | Later | Match final fuse rating. |
| Tape and heat shrink | TBD | Later | Field repairs. |
| Small tools | TBD | Later | Bike and electrical repair basics. |

## Decisions Needed Before Purchase

- Final LED type and voltage.
- Dedicated LED battery vs bike battery tap. Decision: dedicated LED battery only; do not touch bike battery.
- Battery type. Recommendation: standalone 12 V LiFePO4, one main battery, 20 Ah baseline or 30 Ah if mounting works.
- Battery/main connector. Decision: XT60.
- Cat-head connector. Decision: IP67 M12 A-coded four-pin, at least 4 A/contact; purchase after optical coupons and routing confirmation.
- Cat head construction method.
- Whisker lighting method. Decision: fourteen individually addressable 2.0 mm side-glow fibers, one pixel per fiber.
- Whether wheel lighting is first phase or deferred.
