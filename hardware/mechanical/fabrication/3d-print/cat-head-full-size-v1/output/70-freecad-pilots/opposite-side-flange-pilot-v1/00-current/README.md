# Current working set

## Authoritative collision result

V35 is the current full right-eye-versus-right-shell result. It is a read-only
JSON audit, not CAD geometry, and it fails the print gate. Four real
intersections remain: upper C001, lower C001, lower C012, and lower C013.

Read:
`../right-eye-all-shell-components-conflict-audit-v35/validation-v35.json`

Checkpoint:
`../../../../RIGHT_EYE_ALL_SHELL_COMPONENTS_CONFLICT_AUDIT_V35_CHECKPOINT_2026-08-16.md`

## Open this review

`../right-upper-c009-deletion-review-v34/CAT_HEAD_RIGHT_UPPER_C009_DELETION_REVIEW_V34.FCStd`

V34 starts from the accepted pre-V33 right-upper baseline and omits only C009.
It adds no replacement geometry and does not mirror or production-integrate.
Its C009-deletion-only automated validation passes, but V35 proves the full
eye/shell assembly is not collision-free.

Check that C009 is absent with no hole, residue, or disconnected fragment, and
that the repaired eye, right primary ear, lower face, and translucent under-ear
A/B panel remain unobstructed. Do not use V34 for print approval.

Validation:
`../right-upper-c009-deletion-review-v34/validation-v34.json`

The V33 reposition preview is rejected because it floats in the translucent
under-ear panel region.

Accepted source directories remain at this pilot root. Superseded and rejected iterations are under `../90-archive/2026-08-16/`.
