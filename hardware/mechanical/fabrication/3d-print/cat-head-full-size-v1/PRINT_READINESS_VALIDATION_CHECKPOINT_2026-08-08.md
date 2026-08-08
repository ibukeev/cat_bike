# Cat-Head Print-Readiness Validation Checkpoint — 2026-08-08

## Status

Validation-only iteration complete. No geometry or aluminum changed. No STL,
G-code, or print release was generated.

Gate 3 through Gate 8 now require every production part to contain exactly one
connected, closed, manifold body. Gate 8 also requires a nominal 10 mm XY edge
reserve per side before brim and support generation.

## Current review and output files

- Closure ledger: `FEEDBACK_CLOSURE_MATRIX_2026-08-08.md`
- Dashboard: `PRINT_READINESS_DASHBOARD_2026-08-08.md`
- Coupon audit: `PRINTABLE_COUPON_AUDIT_2026-08-08.md`
- Shared policy: `source/print_topology_policy.py`
- Regression: `tests/automated/test_cat_head_print_topology_policy.py`
- Active A hardware review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`
- Pending B shape review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-panel-tab-clearance-review-v1/CAT_HEAD_RIGHT_B_PANEL_TAB_CLEARANCE_REVIEW_V1.FCStd`

## Accepted decisions and dimensions

- Printable-body component count: exactly `1`.
- Boundary edges: `0`; non-manifold edges: `0`.
- Nominal plate-edge reserve: `10 mm` per XY side (`20 mm` per axis).
- This reserve is necessary but does not replace the final brim/support slice.

## Validation performed and results

- Focused policy tests: `9/9 PASS`.
- Full automated suite: `22/23 PASS`; the sole failure is the pre-existing,
  unrelated lighting-map test because `glow_pairs` is absent from the current
  Gate 1 panel-role data.
- Gate 3 and Gate 5 were explicitly audited and now raise a nonzero validation
  error after writing their report when any acceptance item is false.
- Python syntax compilation for policy and Gate 3–8 generators: `PASS`.
- Git whitespace/error check: `PASS`.
- PrusaSlicer current-artifact audit:
  - lower faces: `61` parts each — fail;
  - upper heads: `41` left / `42` right — fail;
  - eye buckets: `6` parts each — fail.
- Current lower-face pre-brim/support total margins:
  - right: `7.798/6.216 mm`;
  - left: `7.798/6.471 mm`;
  - required: `20 mm` on both axes — fail.
- The sole generated portal-fit coupon is one part and manifold, but it is
  obsolete for V0.5-M2: its cavity is `20.50 mm` and has no removable cap,
  while the frozen current interface uses a `21.00 mm` serviceable U-cradle.


## Rejected or unsafe variants

- Reject “manifold = yes” as proof of one printable body.
- Reject one STL filename as proof of one unioned part.
- Reject binary bounding-box containment as production bed fit.
- Do not silently union review geometry without selected owners, a numeric
  contract, evidence, and approval.
- Do not weaken the 10 mm reserve to pass legacy lower faces.
- Do not use the old Gate 8 fixed-socket coupon to approve V0.5-M2 rail fit.

## Exact validation commands

```bash
python3 -m unittest tests.automated.test_cat_head_print_topology_policy
python3 -m unittest discover -s tests/automated -p 'test_*.py'
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/print_topology_policy.py hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate{3,5,6,7,8}_*.py
prusa-slicer --info hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/shells/{left,right}_{lower_face,upper_head}.stl
```

## Next physical review

1. Review existing right-B relief.
2. Review existing right-A short M3 insert contract.
3. After approval, integrate only right A/B.
4. Print small ASA fit/tool/pull-out coupons before mirroring.
5. Review complete head and slicer previews before ASA release.
6. Measure the actual purchased rail and approve a current V0.5-M2 socket/cap
   coupon contract before exporting a replacement coupon STL.
