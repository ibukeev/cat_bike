# Gate 1 Approval

Approved: 2026-07-15

The approved fabrication-role baseline is:

- 330 mm chin-to-ear-tip exterior, uniformly scaled from the accepted panel mesh;
- twenty removable purple glow/light-transmitting panels after completing both mirrored side pairs;
- all previously proposed cyan glow panels returned to opaque structure;
- two corrected separate eye-material silhouettes traced from the annotated SVG;
- two red lower-front facets reserved as the mouth opening;
- no illuminated ear panels;
- rear-service plane retained as a planning reference only.

The annotated review source is `output/gate1-review/gate1-review (Copy).svg`.
The tracked role source of truth is `config/gate1-panel-roles.json`.

Post-review correction: `QUAD031` mirrors `QUAD017`, and `QUAD021` mirrors
`QUAD035`. Both counterparts are glow panels so the side treatment is bilateral.

## Constraint Passed to Section Layout

Approved glow panels occupy the facial centerline. Do not use a straight
top-to-bottom center seam through the face. The printable-section layout must
either jog along existing facet edges around these panels or use a separate
center-front structural module. The choice must be resolved in multiview review
before shell thickness, flanges, or fasteners are modeled.
