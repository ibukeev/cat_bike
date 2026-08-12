# Central, Front, and Side Glow-Panel Review Contracts — 2026-08-12

These contracts translate F-15 through F-18 into non-guessing CAD gates. No
geometry is changed here because the exact physical front/side STL identities
and owner faces are not yet confirmed.

## Shared contract

- Skirts are non-structural light-control features only.
- Connector loads enter through the main glow-panel body through broad,
  continuous roots.
- Validate the complete insertion sweep and final seated position against the
  final shell, reinforcement, flange, fastener, washer/nut, tool, and wiring
  envelopes.
- Installation must require no cutting, scraping, bending, force-fitting, or
  connector tension to pull the panel into position.
- Work one side/one panel at a time; preserve all other owners and aluminum.

## F-15 central continuous back-skirt

Preserve the useful continuous skirt, but locally relieve only measured
collision regions. Required anchors before CAD:

1. central glow-panel main-body face;
2. complete skirt perimeter edge loop;
3. every contacted shell/reinforcement/flange face through the insertion path;
4. seated datum and insertion direction.

Exit checks: continuous light closure remains; minimum sweep/seated clearance
is positive at every sample; no relief enters the main structural panel body.

## F-16 central lower anti-flap point

Add one lower retention point on the lower vertical nose owner, not the small
adjacent horizontal piece. Required anchors:

1. lower vertical central-panel face;
2. matching lower vertical nose-owner face;
3. approved upper two-point connector references;
4. nut/washer and straight-tool escape direction.

The lower point must be spatially separated from the upper pair and use a broad
continuous root. It seats an already aligned panel; it must not pull the panel
into shape. Numeric root, overlap, fastener, gap, and tool contracts must be
frozen after the two faces are selected.

## F-17 front nose-side panel

First identify the exact physical STL/side. Then select two widely separated
main-body owner regions and matching shell faces. Do not attach through the
skirt. The skirt receives only local collision relief after the full insertion
sweep identifies the occupied regions.

Exit checks: two broad rooted connectors; no skirt loading; no collisions or
forced insertion; both connectors accessible after seating.

## F-18 side panel

First identify the exact physical STL/side. Select two owner regions near
opposite practical ends of the panel and matching shell faces. The current
single connector is not reused as the sole retention. Audit every skirt corner
against complete reinforcement/flange geometry throughout insertion.

Exit checks: two broad separated connectors; no perimeter corner collision;
no bending or tensioned alignment; positive tool and hardware clearance.

## Review evidence package

For each panel, the next proposal must include:

- source-only and proposed-only objects;
- selected anchor face/edge IDs;
- a numeric design-contract table;
- front, back, side, section, and insertion-sweep evidence;
- interference and minimum-clearance report;
- one connected-body and required-source-retention validation;
- explicit list of unchanged owners/workstreams;
- no mirror/integration/export until the one-side proposal is approved.
