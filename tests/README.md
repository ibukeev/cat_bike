# Tests

Use this area for verification.

- `manual/` - checklists for bench tests, bike installation checks, night tests, and playa readiness.
- `automated/` - tests for any scripts, pattern transforms, generated files, or configuration validators.

Use `manual/cat-head-lighting-gates.md` for physical coupon and integration gates.

Document the exact hardware setup used for manual tests.

## Retained-build checks

From the repository root, with the retained Git LFS files downloaded:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.automated.test_bilateral_eye_carrier_corner_clearance_v3_print_release_v1 \
  tests.automated.test_right_eye_front_rear_print_packaging_v1 \
  tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract \
  tests.automated.test_small_v1_merged_mouth_pane_rev113_contract \
  tests.automated.test_cat_head_visible_freecad_review_copy
node tests/automated/validate_mvp_bike_patterns.js
```

On 2026-09-10 these ran 35 passing Python tests and passed the mapper and all
10 lighting patterns. They check retained contracts/tooling, not physical fit,
structural strength, new geometry, or a new print release.

## Historical CAD checks and known limits

The user authorized deleting or committing the 29 previously untracked test
files on 2026-09-10. Twenty-four were retained unchanged because their matching
source/contracts are already tracked and they retain release, numeric-regression,
or safety-check coverage. Being retained does not make an old design approved.

Removed from that untracked set:

- `test_lower_front_bilateral_feedback_cleanup_review_v3.py`: byte-for-byte
  duplicate of the retained V2 test, including its V2 paths and assertions.
- `test_right_eye_serviceable_fit_tooling_v4.py`, `..._v5.py`, `..._v6.py`, and
  `..._v6_attempt_002.py`: stale version-specific acceptance snapshots that still
  assert those designs are not rejected. The rejection registry now rejects them.
- The root `tmp_eye_audit_probe_marker.txt`, containing only `temporary`.

The CAD source, rejection registry, numeric gates, approval fields, hash pins and
all retained test bytes were left unchanged. No CAD runtime or generator ran.
The obsolete untracked tests were deleted, not committed as another archive;
the duplicate content remains in the retained V2 test.

The complete historical suite is still not all green:

```bash
env -u CAT_HEAD_FREECAD_APPDIR PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests/automated -p 'test_*.py'
```

Fresh-process result after this triage: 280 tests, 1 failure, 4 errors and 36
skip events. Remaining problems are two lower-C001 modules importing unavailable
FreeCAD, the retired eye-validator candidate fixture, an eye-validator iteration-ID
mismatch during combined discovery, and the old cat-head lighting test expecting
the absent `glow_pairs` field. CAD-only tests skip without their runtime; some also
require retired fixtures even when FreeCAD is available. Do not infer a runtime
pass from a skip, recreate rejected candidates, repin evidence, or relax guards
to make these tests green. Their supported future scope is a separate review.
