# V0.5-M2 Socket/Cap Coupon Contract Proposal — 2026-08-08

**State:** review-only numeric contract. No CAD, STL, G-code, aluminum cut, or
print release is authorized by this document.

## Narrow purpose

This isolated coupon would close only the physical rail-fit, cap assembly, M4
alignment, and M3 insert-access questions in F-02/A-38. It does not validate
the shell root, complete-head insertion, vibration strength, or metal
fabrication.

## Physical input required before CAD

Measure the purchased rail with calipers at both ends and the midpoint:

| Measurement | Record |
|---|---|
| Width at three stations | TBD mm |
| Height at three stations | TBD mm |
| Wall thickness at both ends | TBD mm |
| Maximum corner radius | TBD mm |
| Straightness over the coupon insertion length | TBD mm |

The V0.5 file records a nominal measured section of `19 x 19 mm`; the current
control checkpoint still requires physical verification. A material deviation
is a shared-interface review item, not permission to silently alter the socket.

## Frozen geometry copied from V0.5-M2

| Feature | Contract |
|---|---:|
| Straight cavity | `21.00 x 21.00 mm` |
| Lead-in mouth | `23.00 x 23.00 mm` |
| Lead-in depth | `1.00 mm` |
| Insertion depth | `30.00 mm` |
| M4 clearance path | `4.50 mm` |
| M4 center from open end | `10.00 mm` |
| Removed outboard-wall clearance | `0.25 mm` |
| Cap tongue clearance | `0.30 mm` |
| Cap receiver clearance | `0.30 mm` |
| Cap cover thickness | `3.00 mm` |
| Cap axis-end clearance | `0.30 mm` |
| Cap fasteners | four M3 |
| M3 clearance diameter | `3.40 mm` |
| Insert pocket | `4.60 mm diameter x 4.20 mm deep` |
| M3 axial stations from mouth | `5.50 mm`, `24.50 mm` |
| M3 cross-section stations | `-13.35 mm`, `+13.35 mm` |
| M3 head envelope | `6.00 mm diameter x 2.50 mm` |
| M3 tool envelope | `8.00 mm diameter x 20.00 mm` |

The coupon consists of one representative U-cradle and one keyed removable
cap. Each exported printed piece must be exactly one connected, closed,
manifold body.

## Proposed acceptance checks

1. PrusaSlicer reports one part and manifold for each STL.
2. The saved slice has at least `10 mm` XY reserve per side before brim and
   support.
3. The measured rail enters the full `30 mm` by hand without cutting,
   sanding, hammering, or permanent spreading.
4. The rail can be removed by hand after ten insertion/removal cycles.
5. With the rail seated, a `4.0 mm` test pin passes through both coupon walls
   and the drilled rail at the frozen M4 station.
6. The cap seats without forcing; its exterior is no more than `0.30 mm`
   proud of the coupon datum.
7. All four M3 screws can be installed and removed with the specified
   `8 x 20 mm` tool envelope.
8. Heat-set pockets do not crack or visibly delaminate after three
   install/remove cycles.
9. Any binding, crack, stripped insert, cap lift, or obvious rail rattle is a
   failed coupon; do not tune production geometry without shared approval.

## Proposed print sequence

1. PLA geometry-only coupon for fit, cap motion, drilling alignment, and tool
   access.
2. ASA repeat using the intended production profile for heat-set behavior and
   repeatability.

Both slicer previews and results must be recorded before this interface can
advance. The first user decision is approval or correction of this contract;
CAD generation comes afterward.

## Frozen source references

- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json`
- `config/gate9-m2-rear-interface-candidate-v7.json`
- `hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`
