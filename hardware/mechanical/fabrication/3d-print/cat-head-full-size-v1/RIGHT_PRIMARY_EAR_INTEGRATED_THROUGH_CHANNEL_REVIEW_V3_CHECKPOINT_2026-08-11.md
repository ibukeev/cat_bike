# Right primary-ear integrated through-channel V3 — 2026-08-11

## Status

Digital pass and user visual approval on 2026-08-11 ("OK good enough"). This
is the approved right-side integration source for left mirroring and bilateral
validation, not a print release.

## Review file

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-integrated-through-channel-review-v3/CAT_HEAD_RIGHT_PRIMARY_EAR_INTEGRATED_THROUGH_CHANNEL_REVIEW_V3.FCStd`

The default view shows the two integrated owner solids and highlights two
full-length 3.0 mm shaft proofs. To inspect the interface without the large
owners, hide the two `...INTEGRATED_V3` objects and show the two copied
`...FACE2_COMPACT_V3...` flange objects.

## Accepted sources and anchors

- untouched repaired right upper-head owner from clean-owner V4;
- flush-clean right ear owner from clean-owner V4;
- unchanged compact head flange with round channels `Face6` and `Face7`;
- unchanged compact ear flange with round `Face6` and slot bounded by
  `Face7`/`Face10`;
- common bolt direction
  `(0.940522, 0.141403, 0.308907)`;
- measured bolt spacing `9.4977 mm`, matching the `9.5 mm` contract.

## Construction correction

Cutting the already-fused owner/flange compound with a cutter exactly tangent
to the existing 3.4 mm flange bore produced a misleading coincident-surface
Boolean. That unsaved trial is rejected.

The accepted operation order is:

1. cut two 3.4 mm channels into copied clean owners;
2. preserve the ear-side `3.4 x 5.0 mm` capsule slot;
3. union the already-holed compact flanges to those cut owners;
4. insert two full-length 3.0 mm shaft proofs.

This keeps the approved flange shapes, hole locations, edge material, and
`0.3500 mm` pair gap unchanged.

## Validation

- head result: valid closed one-solid, `76127.47 mm3`, `1680` faces;
- ear result: valid closed one-solid, `17567.11 mm3`, `57` faces;
- no self-intersections in either integrated result;
- shaft A clears both owners by at least `0.1955 mm` radially;
- shaft B clears both owners by at least `0.1946 mm` radially;
- zero M3 shaft/owner intersections;
- the pre-existing remote `51.7854 mm3` owner-owner overlap is unchanged
  from the clean V4 sources and was not introduced by this interface.

## Rejected or absent

- the wrong-axis unsaved trial is rejected;
- the fuse-first coincident-cylinder Boolean is rejected;
- no left mirror;
- no STL, slicer project, G-code, or ASA print release;
- no change to aluminum, eyes, reinforcement, rear cassette, or lower faces.

## Exact resume command

`FreeCAD hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-integrated-through-channel-review-v3/CAT_HEAD_RIGHT_PRIMARY_EAR_INTEGRATED_THROUGH_CHANNEL_REVIEW_V3.FCStd`

## Visual review

1. Confirm both highlighted shaft proofs visibly pass through the paired
   flanges.
2. Hide each shaft proof in turn and confirm the opening remains visible.
3. Confirm the head has two round paths and the ear keeps one round plus one
   slot.
4. Confirm neither flange has moved or grown.
5. Confirm no four-hole residue returned.

The user approved this review on 2026-08-11. The next controlled change is an
exact left-side mirror and bilateral validation. Printing remains blocked by
the other open shell gates.
