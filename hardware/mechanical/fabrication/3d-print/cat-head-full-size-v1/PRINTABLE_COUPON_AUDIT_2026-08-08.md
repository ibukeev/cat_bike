# Cat-Head Printable Coupon Audit — 2026-08-08

## Release result

**No current cat-head coupon is released for printing.** The only generated
coupon found in the repository is a valid one-body manifold mesh, but it tests
the obsolete Gate 8 fixed-socket geometry rather than the frozen V0.5-M2
serviceable socket.

## Audited artifact

`output/10-design-gates/gate8-full-size-structural-iteration/test-coupons/gate8_portal_fit_coupon_integrated_socket.stl`

PrusaSlicer reports:

- `number_of_parts = 1`;
- `manifold = yes`;
- size `32.5 x 29.2 x 32.5 mm`;
- volume `20906.709 mm3`.

The mesh is printable as geometry, but it is not a valid current-interface
test:

| Contract item | Old Gate 8 coupon | Frozen V0.5-M2 interface |
|---|---:|---:|
| Square cavity | `20.50 mm` | `21.00 mm` |
| Socket construction | Closed fixed socket | Serviceable U-cradle plus keyed removable cap |
| Cap fasteners | None | Four M3 per cap |
| Intended rail | Nominal `19.05 mm` square | Actual purchased `19 x 19 x 2 mm` stock, measurement still required |

A fit result from the old coupon would therefore not close F-02 or A-38 and
could cause the current socket to be tuned from misleading evidence.

## Rejected or unsafe action

- Do not print or use the Gate 8 coupon to approve V0.5-M2 fit.
- Do not regenerate the old Gate 8 coupon and relabel it as current.
- Do not cut or drill aluminum from this coupon.

## Required replacement coupon

After the actual rail stock is measured, create a V0.5-M2-specific coupon that
contains the frozen `21.00 mm` cavity, `23 mm` lead-in, `30 mm` depth,
current M4 station, removable outer cap, cap receivers, and representative M3
insert features. It must be one connected closed manifold body per printed
piece and must pass a real slicer review before release.

The user must approve the isolated coupon contract and evidence before STL

The replacement numeric contract is staged for review in
`V05_M2_SOCKET_CAP_COUPON_CONTRACT_PROPOSAL_2026-08-08.md`. It creates no
geometry and does not bypass the required approval gate.
export under the cat-head CAD change-control gate.

## Validation command

```bash
prusa-slicer --info hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/test-coupons/gate8_portal_fit_coupon_integrated_socket.stl
```
