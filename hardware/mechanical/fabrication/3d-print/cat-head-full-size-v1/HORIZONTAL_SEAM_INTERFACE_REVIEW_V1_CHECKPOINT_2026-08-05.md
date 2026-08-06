# Horizontal Seam Interface Review V1 Checkpoint — 2026-08-05

## Status

V1 is ready for visual review only. It adds one mirrored reinforcement rail
pair along the longest horizontal exposed edge of the V5 cassette-owned
`MANQ007_LEFT` and `MANQ007_RIGHT` panels. No other reinforcement gap, eye
mount, connector, exterior facet, or aluminum geometry is changed.

## Primary review files

- Blender: `output/horizontal-seam-interface-review-v1/horizontal-seam-interface-review-v1.blend`
- Validation: `output/horizontal-seam-interface-review-v1/horizontal-seam-interface-review-v1-validation.json`
- Renders: `output/horizontal-seam-interface-review-v1/renders/`

## Blender review structure

- `H1_PROPOSED_HORIZONTAL_MANQ007_RAILS`: two bright-green proposed rails.
- `H1_UNCHANGED_REINFORCEMENT_REFERENCE`: unchanged R1 standalone
  reinforcement, shown gray.
- `H1_APPROVED_V5_BOUNDARY_REFERENCE`: unchanged yellow V5 boundary curves.
- `H1_REJECTED_SOURCE_REFERENCE`: the rejected C006 rails and C002 eye mounts;
  preserved for traceability but hidden by default.
- V5 retained/cassette review shells remain available as wireframe viewport
  context and are not included in the normal renders.

## Exact target selected

The yellow `V5_BOUNDARY` curves contain several kinds of edges. This review
selects only the unique long horizontal exposed edge on each cassette-owned
`MANQ007` panel:

- Left endpoints: `[-88.9455, 188.3385, 47.8725]` to
  `[0, 188.3385, 47.8725]` mm.
- Right endpoints: `[88.9455, 188.3385, 47.8725]` to
  `[0, 188.3385, 47.8725]` mm.
- Boundary length per side: `88.9455 mm`.

This is not the `73.848 mm` diagonal retained/cassette ownership cut. The
approved V5 ownership cut is unchanged.

## Proposed dimensions and placement

- Rail count: 2, exact X mirrors.
- Rail dimensions per side: `83.9455 x 6 x 7 mm`.
- End setback: `2.5 mm` at both ends.
- Boundary coverage per side: `94.3786%`.
- Panel-edge inset: `0.8 mm`.
- Shell overlap: `0.8 mm`.
- Source shell wall convention: `1.8 mm` inward.
- Fastener holes, bosses, and connector geometry: none in this review.
- The two center setbacks intentionally leave `5 mm` total for the later
  connector-interface decision; no center connector is guessed here.

## Rejected source components

The following source review objects remain preserved but are hidden and are not
used by the proposed rail geometry:

- `R1_RET__L__C006__seam_rail`
- `R1_RET__R__C006__seam_rail`
- `R1_UNCL__L__C002__eye_mount`
- `R1_UNCL__R__C002__eye_mount`

The C002 eye-mount design remains rejected. Its replacement is a later separate
feedback item.

## Validation performed

- Both configured MANQ007 target endpoints match within `0.01 mm`.
- Both proposed rails are closed and manifold.
- Left/right proposed rail vertices match exactly after X reflection.
- Both rail volumes match: `3525.7104 mm3` per side.
- Approved V5 boundary-curve fingerprints are unchanged.
- Every pre-existing mesh fingerprint is unchanged.
- Rejected C006/C002 source objects are preserved but hidden.
- Proposed rails remain more than `115 mm` from every rejected C002 eye-mount
  piece and more than `178 mm` from the rejected C006 rails, proving none of
  their geometry was reused.
- Rear, rear-left, rear-right, and front renders were generated for both the
  existing-frame context and isolated proposed rails.
- No STL or G-code was generated.

## Explicitly deferred feedback

- Redesign both rejected C002 eye-mount pieces.
- Add the missing `L__C036` to `L__C038` tie.
- Restore the missing mirror of `L__C056`.
- Add the missing `L__C026` to `L__C039` tie.
- Add the missing `L__C036` to `L__C003` tie.
- Design the connector interface that replaces the old C006 rails.

None of these are silently included in V1.

## Rejected or unsafe approaches

- Do not reinforce every horizontal spline in `V5_BOUNDARY`; several are
  different exposed interfaces or coincident source edges.
- Do not move the V5 ownership seam to fit a reinforcement member.
- Do not reuse, trim, or cosmetically hide the rejected C006 or C002 geometry.
- Do not add connector holes before the connector architecture is reviewed.
- Do not union review geometry into production shells before visual approval.

## Exact regeneration command

From repository root:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/lower-reinforcement-ownership-review-v1/lower-reinforcement-ownership-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_horizontal_seam_interface_review_v1.py
```

## Next physical review

1. Open the Blender file in the default rear/interior view.
2. Confirm the bright-green pair is on the horizontal edge you intended.
3. Isolate `H1_PROPOSED_HORIZONTAL_MANQ007_RAILS` with
   `H1_APPROVED_V5_BOUNDARY_REFERENCE`; confirm the 2.5 mm setbacks and mirrored
   placement.
4. Confirm C006 and C002 are absent from the visible candidate.
5. Review only this rail path and its dimensions. Do not approve connectors,
   other missing ties, eye mounts, printing, or aluminum from this file.
