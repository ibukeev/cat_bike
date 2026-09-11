# Left-lower manual master V1

Status: **USER-DESIGNATED AUTHORITATIVE LEFT-LOWER MASTER**.

The user manually edited this left-lower opaque assembly and designated it as
the sole starting point for later left-lower CAD sessions. The promotion copied
the two source files byte-for-byte; it did not open FreeCAD, change geometry,
re-export a mesh, or slice a print.

## Master files

- `LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1.FCStd` — authoritative
  CAD master for all future left-lower work.
- `LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1-Compound.3mf` — the
  user's corresponding 3MF companion, retained unchanged.

## Future-session rule

Start from the exact hash-matched FCStd in this directory. Open it read-only
and save any later work to a fresh review/output name. Do not overwrite this
master, reconstruct it from earlier review files, or substitute a mirrored or
automatically generated left-lower assembly. Preserve every manual cut and
connector already present unless the user explicitly authorizes a later
change.

This package is a lineage/master designation. No new geometric, topology,
clearance, slicer, or physical-fit validation was performed during promotion,
and no G-code was generated.
