# Mirror Landing Objective Audit — 2026-08-12

## Scope

Read-only dry-run of the existing mirror-facet prototype generator against the
frozen accepted surface. This does not change shell geometry and is not the
final HS-19 minimal-count mirror set.

## Result

The existing per-plane prototype calculations pass their `0.05 mm` planarity
contract. The audit also confirms that two source quads contain real diagonal
bends and cannot accept one rigid flat mirror across the full quad:

| Source region | Full-region residual | Required handling |
|---|---:|---|
| `QUAD014` right cheek | `1.996 mm` | split at the real diagonal bend |
| `QUAD008` right ear outer plane | `0.870 mm` | split at the real diagonal bend |

Each separated triangle/subplane has numerical planarity residual below
`2.4e-14 mm`, well inside tolerance. The largest current prototype subplane is
approximately `140.17 x 61.68 mm`; all six current right-side samples fit one
`240 x 200 mm` plate with margins.

## Interpretation

- Do not subdivide a maximal connected coplanar landing region merely because
  the mesh is triangulated.
- Do split where the measured source surface has a real bend above `0.05 mm`,
  at a required service seam/opening, or where the backing/bed limit requires.
- The current prototype selection samples only four source facets and is not a
  complete whole-head mirror inventory.
- Final mirror outlines must be regenerated after structural owner unions,
  exterior-deviation cleanup, eye/ear integration, and cassette seams are
  frozen; otherwise connector bumps or later cuts can invalidate them.

## Command and result

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_mirror_facet_cap_prototypes.py --dry-run
```

Dry-run acceptance passed: all selected facets planar, all insets retain
positive area, generated topology is closed/manifold, and plate layouts fit.

## Next HS-16/HS-19 gate

After the final exterior owners exist, compute connected coplanar regions over
the complete opaque exterior, merge triangulated faces within `0.05 mm`, then
subtract openings/service seams and apply the `0.9 mm` perimeter reveal. The
result should use one largest practical mirror per maximal landing region.
