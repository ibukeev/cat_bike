#!/usr/bin/env python3
"""Headless runner for the V22 exact-face review generator.

FreeCAD command mode has no ViewObject.  The primary generator intentionally
contains GUI styling for normal review use, so this runner omits only those
styling assignments and redirects the result to a distinct exact-face package.
Geometry, face identities, traceability, and the change-control contract are
unchanged.
"""

from __future__ import annotations

from pathlib import Path


GENERATOR = Path(__file__).with_name(
    "generate_right_upper_eye_c001_anchor_localization_review_v22.py"
)
source = GENERATOR.read_text()
source = "\n".join(line for line in source.splitlines() if ".ViewObject." not in line)
namespace = {"__file__": str(GENERATOR), "__name__": "v22_generator"}
exec(compile(source, str(GENERATOR), "exec"), namespace)

output_dir = namespace["PILOT_ROOT"] / "right-upper-eye-c001-exact-anchor-review-v22"
namespace["OUTPUT_DIR"] = output_dir
namespace["OUTPUT_FCSTD"] = (
    output_dir / "CAT_HEAD_RIGHT_UPPER_EYE_C001_EXACT_ANCHOR_REVIEW_V22.FCStd"
)
namespace["OUTPUT_JSON"] = output_dir / "validation-v22.json"
namespace["main"]()
