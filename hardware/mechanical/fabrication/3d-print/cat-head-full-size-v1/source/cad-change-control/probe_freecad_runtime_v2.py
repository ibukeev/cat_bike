#!/usr/bin/env python3
"""Print the exact FreeCAD/OCCT runtime identity used by V2 tooling."""

from __future__ import annotations

import json
import platform

import FreeCAD as App
import Part


def runtime_record() -> dict[str, object]:
    version = list(App.Version())
    return {
        "freecad_version": version,
        "freecad_program_version": f"{version[0]}.{version[1]}R{version[3]}",
        "occt_version": str(Part.OCC_VERSION),
        "python_version": platform.python_version(),
        "platform_machine": platform.machine(),
    }


def main() -> int:
    print(json.dumps(runtime_record(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
