# Cat Head Gate 9 Rear Architecture Decision — 2026-07-28

## Decision

Proceed with a **full-size rear-loaded cassette**. Keep the accepted 330 mm
head envelope and the frozen
`CAT-HEAD-SHELL-ALUMINUM-V0.3` interface. Do not globally scale the head.

The working cassette ownership boundary is the full-size **-70 mm rear-plane
source-facet threshold** used by
`rear_cassette_full_scale`. This is an architecture selection, not approval of
the current raw facet seam as the final visible seam.

Keep the V0.3 lower rail targets at head X `-40 mm` and `+40 mm` for the first
coordinated rebuild. Do not move the aluminum rails toward the center unless
the final shoe, socket, fastener, tool, wiring, and removal envelopes prove
that a coordinated interface revision is necessary.

## Why this architecture won

All values below are review estimates from clean 1.8 mm low-poly shells, three
perimeters, 15% infill, automatic snug support everywhere, a 5 mm brim, and a
Generic ASA comparison profile on the 250 x 210 x 220 mm MK4/MK4S envelope.
They exclude final flanges, bridges, sockets, seals, drains, wiring features,
and hardware.

| Architecture | Estimated time | Filament | Support mass | Support volume | Minimum post-brim XY margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| Retained full-size partition | 92.32 h | 1022.71 g | 702.03 g | 656.10 cm3 | 12.20 mm |
| Uniform 98% scale | 87.43 h | 969.37 g | 665.14 g | 621.63 cm3 | 14.24 mm |
| Shallow cassette, -35 mm | 115.01 h | 1290.63 g | 975.25 g | 911.44 cm3 | 17.15 mm |
| Shallow cassette, -45 mm | 66.32 h | 768.83 g | 476.23 g | 445.07 cm3 | 26.72 mm |
| **Selected full-size cassette, -70 mm** | **61.84 h** | **713.68 g** | **405.07 g** | **378.56 cm3** | **12.89 mm** |
| Mirrored stepped hybrid | 61.03 h | 730.99 g | 432.88 g | 404.56 cm3 | 12.30 mm |

Relative to the retained full-size partition, the selected cassette reduces:

- estimated clean-shell print time by about 33%;
- total clean-shell filament by about 30%;
- estimated support mass by about 42%.

A 2% global shrink saves only about 5% and retains the same unfavorable
section ownership and metal-envelope conflicts. Scaling is therefore rejected
as the architecture fix.

The mirrored stepped hybrid is about 1.3% faster than the selected cassette,
but it uses about 2.4% more filament, about 6.9% more support, leaves an
additional right-lower topology island, and concentrates 295 g of estimated
support in the cassette. It is rejected.

## Selected review geometry

The current selected comparison geometry has these unrotated envelopes:

| Part | Dimensions |
| --- | --- |
| Left lower face | 158.406 x 200.784 x 126.395 mm |
| Right lower face | 128.291 x 200.784 x 126.395 mm |
| Left upper head | 127.408 x 137.661 x 158.217 mm |
| Right upper head | 127.203 x 137.661 x 158.217 mm |
| Rear cassette | 253.878 x 107.550 x 220.280 mm |

The selected representative cassette slice used rotation X/Y/Z
`62 / 122 / 82 degrees`, produced a toolpath envelope of approximately
`214.143 x 180.930 x 217.4 mm`, and retained at least `12.887 mm` from every
XY bed edge after support and brim.

The coarse collision comparison included:

- the complete V0.3 3 mm aluminum backplate;
- both measured 19 x 19 x 2 mm rails;
- conservative 30 x 30 x 40 mm raw lower-shoe envelopes;
- 24 mm diameter lower-shoe tool envelopes;
- 14 mm diameter by 20 mm adapter-hardware envelopes.

The selected cassette had zero coarse intersections classified as unintended
between those envelopes and the four retained body shells. Cassette contact
and pass-through areas remain deliberate design work, not validated
clearances.

## Topology consequences that must be fixed

The comparison generator closes each disconnected source island independently.
That is useful for measuring print tradeoffs but is not acceptable production
topology.

The selected raw comparison currently produces:

- one connected rear cassette;
- one connected shell for each ear;
- two closed components in each upper shell;
- two closed components in each lower shell.

The production rebuild must make every released STL exactly one connected,
closed, manifold body. Use broad inboard bridges tied into the shell and seam
structure. Do not recreate thin flying tabs, unsupported blades, exposed
reinforcement blocks, or append-only overlapping solids.

Every bridge must stay outside the cassette insertion/removal volume and the
rail, shoe, socket, hardware, tool, wiring, sealing, drainage, and assembly
keep-outs.

## Parser and validation note

The canonical margin result is parser revision V3. V1 incorrectly counted the
MK4 startup purge line at Y `-4 mm`; V2 removed that purge motion and lost its
position state. V3 preserves the Custom XY travel while stripping only startup
purge extrusion. Only V3 pass/fail margins are authoritative.

## Holds before final ASA

This decision does not release STL, G-code, aluminum cuts, holes, or drilling.
Before final ASA:

1. rebuild the selected seven parts as single-body topology;
2. design a hidden cassette mating flange, alignment, sealing, drainage, and
   service-fastener strategy;
3. model real rail pass-throughs, 20.5 mm sockets, lower shoes, anti-crush
   metal load paths, bolts, nuts, washers, and tool access;
4. update front/top portals to the accepted aluminum angles;
5. run exact shell/metal/hardware/tool/wiring collision checks;
6. slice every actual left and right production part with the post-brim 10 mm
   margin rule;
7. print socket, rear-interface, bridge, and cassette-seam coupons before any
   full ASA set.

