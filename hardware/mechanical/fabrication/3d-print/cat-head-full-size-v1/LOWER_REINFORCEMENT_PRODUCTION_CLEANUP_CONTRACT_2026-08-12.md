# Lower Reinforcement Production-Cleanup Contract — 2026-08-12

This is a deterministic cleanup contract derived from the refreshed V5
ownership audit. It is not new CAD geometry and does not release printing.

## Remove from future production owners

These four complete source components are not valid production reinforcement:

| Object | Reason |
|---|---|
| `R1_UNCL__L__C002__eye_mount` | Rejected C002 eye mount; `6.6075 mm` from retained shell and not integrated. |
| `R1_UNCL__R__C002__eye_mount` | Rejected C002 eye mount; `7.5116 mm` from retained shell and not integrated. |
| `R1_UNCL__L__C060__rib` | Detached `0.02356 mm3` residue; at least `4.753 mm` from an owner surface. |
| `R1_UNCL__R__C062__rib` | Detached `0.08049 mm3` residue; at least `4.753 mm` from an owner surface. |

Removal means exclude the complete component from the new production owner
ledger. Do not Boolean-cut nearby accepted geometry and do not edit the frozen
review baselines.

## Hold for explicit seam redesign

These eight components contact both retained and cassette facets and therefore
cannot be assigned wholesale without changing service ownership:

- `R1_CROSS__L__C000__flange`
- `R1_CROSS__L__C024__rib`
- `R1_CROSS__L__C026__rib`
- `R1_CROSS__L__C049__rib`
- `R1_CROSS__R__C000__flange`
- `R1_CROSS__R__C015__rib`
- `R1_CROSS__R__C025__rib`
- `R1_CROSS__R__C049__rib`

The two `C000` objects are shell-integrated mixed components and require an
owner rebuild, not a loose-part move. The six ribs require complementary seam
terminations or replacement ties. Nothing may be truncated at the V5 seam
without a numeric root/overlap contract and one-side review.

## Preserve

- All `71` retained and `26` cassette-classified components remain unchanged.
- The approved MANQ007 horizontal rail pair remains unchanged.
- The six requested tie rails and mirrored right C056 rib remain review-only
  until collision-clipped and unioned to explicit owners.
- Aluminum interface revision stays `CAT-HEAD-SHELL-ALUMINUM-V0.5`, including
  the `21 x 21 mm` rail sockets, six M5 shell centers, and rear service path.

## Production acceptance gate

The next lower/cassette production build must report:

1. zero `R1_UNCL` components;
2. zero accidental loose solids or residues;
3. zero components silently spanning retained/cassette ownership;
4. all retained/cassette reinforcement positively unioned to its named owner;
5. unchanged V5 exterior fingerprint and protected aluminum interface;
6. one intended connected body per exported part in PrusaSlicer.

## Source and regeneration

Source validation:

`output/30-reinforcement-baselines/lower-reinforcement-ownership-review-v1/lower-reinforcement-ownership-review-v1-validation.json`

Regenerate with:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_lower_reinforcement_ownership_review_v1.py
```
