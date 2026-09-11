"""Export the approved working-lower print-candidate inputs for voxel union.

Scope is deliberately limited to the mutable right-lower working source, every
3 mm thickness preview, Cut001, and the selected 2 mm outboard thickening.
Frozen context and upper-owner objects are never read or modified.
"""

import json
import os

import FreeCAD as App
import MeshPart
import Part


TARGET = "WORKING_RIGHT_LOWER_STRUCTURAL_V1"
PREVIEW_PREFIX = "RIGHT_LOWER_3MM_INWARD_PREVIEW"
LOCAL_REPAIR = "Cut001"
OUTBOARD_REPAIR = "PROPOSED_RIGHT_LOWER_OUTBOARD_FACE_THICKEN_2MM"
OUTPUT_DIR = (
    "/home/bsk/Projects/BM_personal_LED-projects /cat_bike/"
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower"
)
OUTPUT_STL = os.path.join(OUTPUT_DIR, "input-overlap-compound.stl")
MANIFEST = os.path.join(OUTPUT_DIR, "input-manifest.json")
LINEAR_DEFLECTION_MM = 0.08
ANGULAR_DEFLECTION_RAD = 0.175

doc = App.ActiveDocument
base = doc.getObject(TARGET)
if base is None or base.Shape.isNull() or not base.Shape.isValid():
    raise RuntimeError("Working lower source is missing or invalid")

previews = [
    item for item in doc.Objects
    if item.Name == PREVIEW_PREFIX
    or (
        item.Name.startswith(PREVIEW_PREFIX + "_")
        and item.Name[len(PREVIEW_PREFIX) + 1:].isdigit()
    )
]
previews.sort(key=lambda item: item.Name)
if not previews:
    raise RuntimeError("No 3 mm thickness previews found")

required_repairs = [LOCAL_REPAIR, OUTBOARD_REPAIR]
repairs = []
for name in required_repairs:
    item = doc.getObject(name)
    if item is None:
        raise RuntimeError("Required approved working repair is missing: " + name)
    if item.Shape.isNull() or not item.Shape.isValid():
        raise RuntimeError("Required approved working repair is invalid: " + name)
    repairs.append(item)

inputs = [base] + previews + repairs
for item in inputs:
    if item.Shape.isNull() or not item.Shape.isValid():
        raise RuntimeError("Invalid candidate input: " + item.Name)

compound = Part.makeCompound([item.Shape for item in inputs])
mesh = MeshPart.meshFromShape(
    Shape=compound,
    LinearDeflection=LINEAR_DEFLECTION_MM,
    AngularDeflection=ANGULAR_DEFLECTION_RAD,
    Relative=False,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)
mesh.write(OUTPUT_STL)
with open(MANIFEST, "w", encoding="utf-8") as handle:
    json.dump({
        "purpose": "review-only voxel-union input; not a print release",
        "inputs": [item.Name for item in inputs],
        "mesh_facets": mesh.CountFacets,
        "linear_deflection_mm": LINEAR_DEFLECTION_MM,
        "angular_deflection_rad": ANGULAR_DEFLECTION_RAD,
    }, handle, indent=2, sort_keys=True)
    handle.write("\n")

print("EXPORTED FINAL-REVIEW VOXEL-UNION INPUT:", OUTPUT_STL)
print("Input components:", len(inputs))
print("3 mm previews:", len(previews))
print("Mesh facets:", mesh.CountFacets)
print("Frozen context excluded. Document geometry unchanged.")
