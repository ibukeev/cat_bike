# V0.5-M2 coordinated bottom M5 checkpoint — 2026-07-29

## Status

`CAT-HEAD-SHELL-ALUMINUM-V0.5` and metal handoff `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` are the active coordinated review interfaces. The two-hole change is accepted and the aluminum generation passes. This is not a metal-fabrication, final-ASA-print, or riding release.

Source shell coordination commit: `0077da2330c0eeae403ab8698c6c1db58bd1b22f`. Previous aluminum baseline commit: `3924f770a393f6a8d97dba29e540002a583540c7`.

## Current review and source files

- Shared interface: `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json`
- Metal config/coordinator: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/config/frame-fixed-mount-v05-final.json` and `frame-fixed-mount-v05-interface.json`
- Metal preflight/generator: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v05_interface.py` and `generate_frame_fixed_mount_v05.py`
- Tracked metal summary: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/review/frame-fixed-mount-v05-final-summary.json`
- Generated metal review model: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/v05-m2-coordinated-centers/review-model/frame-fixed-mount-v05-m2-angle-stock-review.blend`
- Generated drawings, renders, and validation: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/v05-m2-coordinated-centers/`
- Coordinated V7 config/generator: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json` and `source/generate_gate9_m2_rear_interface_candidate_v7.py`
- Tracked shell result: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review/gate9-v7-v05-coordinated-interface-validation.json`
- Generated V7 review model/report/renders: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/`

Generated output directories are ignored build artifacts. Regenerate them before physical review if source, interface, or Blender version changes.

## Accepted coordinated change

Only the bottom shell-attachment M5 centers changed:

- left: `(-10,-30)` to `(-7.4,-30)` mm;
- right: `(10,-30)` to `(7.4,-30)` mm.

The shell consumer uses `14 x 36 x 12 mm` bottom ASA pads. These provide 2 mm of ASA beyond the 10 mm washer on each narrow side and contain the full 14 mm tool envelope.

Unchanged: top pair X `+/-10`, V `30`; middle pair X `+/-20`, V `0`; all six angle-base holes; plate outline; four adapter holes; rail axes; X `+/-40` lower targets; 21 mm sockets; upper M4 retention; rail cut lengths; and compound rail datums.

Rails remain 152.476123 mm centerline finished length, 152.5 mm drawing length, 160 mm rough cut, and 133.776123 mm from lower bearing datum to upper M4 station. Ordered angle remains Randall 6063-T6 nominal `38.1 x 38.1 x 3.175 mm` and is not receipt-verified.

## Validation performed

Metal V0.5 preflight and Blender generation pass all checks. Key margins:

- bottom M5 hole to plate edge: 7.0819 mm;
- 10 mm washer to plate edge: 4.8319 mm;
- 14 mm tool to plate edge: 2.8319 mm;
- opposing 14 mm tool gap: 0.8 mm;
- bottom tool to nearest adapter-hole edge: 7.3963 mm;
- minimum all-hole pair ligament: 5.9 mm;
- minimum sequential hardware/tool gap: 0.4 mm.

The coordinated V7 shell rerun confirms the bottom pads have the required washer bearing and tool containment, opposing bottom pads are disjoint, the complete seated M2 assembly clears fixed shells, the proposal-specific bottom pads clear all recorded withdrawal samples, and all six shell parts plus both caps remain closed one-component manifolds.

The full V7 digital candidate remains FAIL and held for reasons outside the bottom-center delta:

1. middle M5 nut-tool envelopes at X `+/-20`, V `0` intersect lower crossbolt/head envelopes;
2. preassembled lower crossbolts intersect upper shells during sampled withdrawal at 5, 10, 20, and 31 mm;
3. installed socket caps overlap their receiver upper shells; and
4. the root-recess check reports the intended 8 mm root/1 mm shell overlap as 7 mm cavity-plane protrusion, indicating a validator sign/definition defect.

No failed full-V7 check was waived or changed to pass.

## Rejected or unsafe variants

- Keep X `+/-10`, V `-30` with 19 x 36 mm pads: lower-crossbolt sweep collision.
- Keep those old centers with an 11 mm round boss: only 0.5 mm outside the 10 mm washer.
- Move any other plate, angle, rail, or socket datum in this revision: unnecessary and outside scope.
- Treat the passing aluminum audit as a final shell, fabrication, or ride release: prohibited.
- Start the final ASA shell print before the four V7 issues pass: prohibited.

## Exact regeneration commands

```bash
python3 hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v05_interface.py

blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/generate_frame_fixed_mount_v05.py

blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python-expr "import sys; sys.path.insert(0, hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source); import generate_gate9_m2_rear_interface_candidate_v7 as candidate; candidate.v6.main=lambda: None; candidate.main()" \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json

python3 -m unittest tests.automated.test_cat_head_shared_interface
```

The V7 monkeypatch intentionally loads the locked V6.1 BLEND without rerunning the known-rejected V6 blind-socket gate; V7 owns the removable-cap correction.

## Next physical and shell review

1. Resolve the four V7 blockers without moving any V0.5 plate center or preserved rail/socket datum, then rerun complete A-39 insertion, seated, fastened, tool-access, and removal validation.
2. Review the V0.5 plate drawing and V7 rear/hardware renders.
3. On angle receipt, measure both legs, thickness, inside radius, straightness, and alloy/temper marking before cutting.
4. Measure actual rail inside dimensions and corner radii before fitting plugs.
5. Fabricate only an approved rear-interface/angle coupon; do not cut final plate or rails yet.
6. Preserve tether, headlight/steering, proof-load, vibration, and progressive ride gates.
