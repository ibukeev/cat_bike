# Cat Head Full-Size V1

This package turns the shape-approved cat-head panel surface into the 330 mm
fabrication master described in [FABRICATION_PLAN.md](FABRICATION_PLAN.md).

## Current Gate

Gate 1 is planned to freeze:

- the uniformly scaled 330 mm exterior;
- the rear service cut plane;
- source facet identity;
- two eye inserts;
- an initial symmetric set of fourteen removable glow facets.

It does **not** yet create printable shell thickness, joints, section splits,
lighting carriers, reinforcement, or mounting geometry.

## Planned Gate 1 Commands

The source generators referenced below are the next implementation step and
are not part of this planning checkpoint yet.

From the repository root:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate1_master.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate1_review.py
```

The first command writes the candidate role map to `config/` and review data
to `output/gate1-review/`. The second command adds rendered orthographic and
three-quarter views.

Generated output is intentionally ignored by Git. The generator, approved
configuration, validation expectations, and fabrication documentation are the
source of truth.

## Coordinate System

- `X`: left/right, centered on the face.
- `Y`: front to rear, with the nose-side minimum normalized to `0`.
- `Z`: chin to ear tips, normalized to `0..330 mm`.
