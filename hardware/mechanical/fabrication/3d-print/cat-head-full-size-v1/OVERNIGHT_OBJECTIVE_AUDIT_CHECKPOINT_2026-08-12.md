# Cat-Head Overnight Objective Audit Checkpoint — 2026-08-12

## Scope

This checkpoint records objective work that does not require subjective user
placement approval. It does not release printing or aluminum fabrication.

## Preserved approved baselines

- `CAT_HEAD_PRIMARY_EAR_BILATERAL_EXACT_MIRROR_REVIEW_V2.FCStd` validates as an
  intact FCStd archive (`1,107,640` bytes).
- `CAT_HEAD_BILATERAL_AB_MIRROR_REVIEW_V1.FCStd` validates as an intact FCStd
  archive (`1,645,257` bytes).
- Rear-cassette V5, requested reinforcement additions V1, and the shared
  `CAT-HEAD-SHELL-ALUMINUM-V0.5` contract remain the controlled sources.

## Deterministic regeneration results

### Rear cassette V5

Regenerated from the Gate 8 baseline. Results:

- source exterior ledger: `51` faces;
- candidate exterior ledger: `51` faces;
- deleted: `0`; added: `0`; duplicated: `0`;
- fingerprint match:
  `4787ed3e5bf7d8ae2540aa90894bcb9fcc97dd0c0aa54883b12db9127eb25b55`;
- all four review shells closed and valid;
- protected Gate 8 geometry unchanged.

Command:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_rear_cassette_lossless_repartition_review_v5.py
```

### Lower reinforcement ownership

Regenerated from the refreshed V5 file. Results:

- `109` components total;
- `26` cassette, `71` retained, `8` seam-crossing, `4` unclassified;
- source/review geometry fingerprints match;
- every inventoried component is closed and manifold;
- protected source geometry unchanged.

The four unclassified components are the rejected left/right C002 eye mounts
and two tiny detached rib residues (`0.02356 mm3` left, `0.08049 mm3` right).
They must not enter a production owner. The eight seam-crossing components
must be redesigned or assigned explicitly; they must not be chopped or silently
attached to one side.

Command:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_lower_reinforcement_ownership_review_v1.py
```

### Requested reinforcement additions

Regenerated from the approved horizontal-seam review. Results:

- six tie rails plus one mirrored C056 rib;
- all seven new objects closed and manifold;
- all left ties overlap both named source ribs;
- all right ties attach to their named targets;
- two right ties are exact mirrors and one is independently surface-fitted as
  previously approved;
- protected preexisting geometry and approved V5 boundary unchanged;
- shared aluminum revision remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

Command:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/horizontal-seam-interface-review-v1/horizontal-seam-interface-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_requested_reinforcement_additions_review_v1.py
```

## Current production STL audit

The current Gate 8 outputs remain unsuitable for structural printing:

| Part | Slicer parts | Result |
|---|---:|---|
| left lower face | 61 | fail connected-body gate |
| right lower face | 61 | fail connected-body gate; 28 reversed facets reported |
| left upper head | 41 | fail connected-body gate |
| right upper head | 42 | fail connected-body gate |
| left eye bucket | 6 | fail connected-body gate |
| right eye bucket | 6 | fail connected-body gate |
| left eye rear cap | 7 | fail intended-one-cap gate |
| right eye rear cap | 7 | fail intended-one-cap gate |

No ASA shell print should start from these STLs.

## Next objective work

1. Deterministically rebuild the right eye from its clean six sources with
   per-source retained-volume checks; keep the cap independently removable.
2. Remove rejected C002 mounts and the two tiny loose rib residues from the
   future production source ledger.
3. Enumerate the eight seam-crossing reinforcement owners and prepare explicit
   retained/cassette redesign contracts around V0.5 aluminum.
4. Create connected production owner unions only after the one-sided geometry
   reviews are accepted; then rerun slicer part counts and orientation margins.

## Holds

- No mirroring of unapproved eye repair.
- No final shell union that guesses seam-crossing ownership.
- No STL, G-code, ASA print, aluminum cutting, or drilling release.
