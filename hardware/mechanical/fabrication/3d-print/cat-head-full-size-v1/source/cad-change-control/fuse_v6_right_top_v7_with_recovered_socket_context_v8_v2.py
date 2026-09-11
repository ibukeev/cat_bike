"""Backfill and fuse the exact V5 V34 socket context into a V8 right-top review.

Unlike the first attempt, this script does not depend on the transient GUI
selection.  It reads the approved component list directly from preserved V5,
verifies every copied solid in V6, then creates the V8 review-only fusion.
"""

import FreeCAD as App
import FreeCADGui as Gui


V5_PATH = (
    "/home/bsk/Projects/BM_personal_LED-projects /cat_bike/"
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/"
    "70-freecad-pilots/opposite-side-flange-pilot-v1/"
    "right-upper-as-printed-working-assembly-v1/"
    "RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V5.FCStd"
)
V6_SUFFIX = "RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V6.FCStd"
SOURCE_NAME = "PROPOSED_TOP_RIGHT_PRINT_PACKAGE_V7_M3_NUT_POCKET_CLEARANCE"
RECOVERY_GROUP = "RECOVERED_RIGHT_UPPER_V34_SOCKET_CONNECTION_CONTEXT"
OUTPUT_NAME = "PROPOSED_TOP_RIGHT_PRINT_PACKAGE_V8_SOCKET_CONTEXT_FUSED"
EXPECTED = (
    "WORKING_RIGHT_UPPER_C002_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C020_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C022_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C023_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C033_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C034_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C037_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C038_V34_BASELINE",
    "WORKING_RIGHT_UPPER_C042_V34_BASELINE",
)
EPSILON = 1e-7


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def valid(shape, message):
    require(shape is not None and not shape.isNull() and shape.isValid(), message)


def bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)


v6 = App.ActiveDocument
require(v6 is not None and v6.FileName.endswith(V6_SUFFIX), "Activate V6 before running.")
v5 = next((doc for doc in App.listDocuments().values() if doc.FileName == V5_PATH), None)
if v5 is None:
    v5 = App.openDocument(V5_PATH)
require(v5 is not None, "Could not open preserved V5.")

source = v6.getObject(SOURCE_NAME)
require(source is not None, "V7 trial package not found.")
valid(source.Shape, "V7 package has no valid shape.")

group = v6.getObject(RECOVERY_GROUP)
if group is None:
    group = v6.addObject("App::DocumentObjectGroup", RECOVERY_GROUP)
    group.Label = "RECOVERED V34 RIGHT SOCKET CONNECTION CONTEXT — FROZEN REFERENCES"

recovered = []
for source_name in EXPECTED:
    source_obj = v5.getObject(source_name)
    require(source_obj is not None, "V5 source not found: %s" % source_name)
    valid(source_obj.Shape, "Invalid V5 source: %s" % source_name)
    require(len(source_obj.Shape.Solids) == 1, "V5 source is not one solid: %s" % source_name)

    output_name = "RECOVERED_%s_REFERENCE" % source_name.replace("_V34_BASELINE", "")
    output = v6.getObject(output_name)
    if output is None:
        output = v6.addObject("Part::Feature", output_name)
        output.addProperty("App::PropertyString", "RecoverySourceDocument", "Recovery")
        output.addProperty("App::PropertyString", "RecoverySourceObject", "Recovery")
        output.addProperty("App::PropertyString", "Status", "Recovery")
        output.addProperty("App::PropertyBool", "FrozenRailContext", "Recovery")
        output.RecoverySourceDocument = V5_PATH
        output.RecoverySourceObject = source_name
        output.Status = "FROZEN_EXACT_V5_REFERENCE_ONLY__NOT_PACKAGED__NOT_PRINT_RELEASED"
        output.FrozenRailContext = True
        group.addObject(output)
    output.Shape = source_obj.Shape.copy()
    v6.recompute()
    valid(output.Shape, "Invalid recovered V6 shape: %s" % source_name)
    require(len(output.Shape.Solids) == 1, "Recovered V6 source is not one solid: %s" % source_name)
    require(abs(output.Shape.Volume - source_obj.Shape.Volume) <= EPSILON, "Volume mismatch: %s" % source_name)
    require(all(abs(a - b) <= EPSILON for a, b in zip(bounds(output.Shape), bounds(source_obj.Shape))), "Bounds mismatch: %s" % source_name)
    output.ViewObject.ShapeColor = (0.35, 0.85, 0.35)
    output.ViewObject.Transparency = 25
    recovered.append(output)

c002 = next(obj for obj in recovered if obj.RecoverySourceObject.endswith("C002_V34_BASELINE"))
c042 = next(obj for obj in recovered if obj.RecoverySourceObject.endswith("C042_V34_BASELINE"))
c002_c042 = c002.Shape.common(c042.Shape).Volume
require(c002_c042 > 600.0, "C002/C042 engagement missing: %.6f mm3" % c002_c042)

fused = source.Shape.fuse([obj.Shape for obj in recovered])
valid(fused, "V8 fusion produced an invalid shape.")
require(len(fused.Solids) >= 1, "V8 fusion produced no solids.")
source_retained = fused.common(source.Shape).Volume
require(abs(source_retained - source.Shape.Volume) <= EPSILON, "V8 did not retain all V7 geometry.")

output = v6.getObject(OUTPUT_NAME)
if output is None:
    output = v6.addObject("Part::Feature", OUTPUT_NAME)
    output.addProperty("App::PropertyLink", "SourcePackage", "Provenance")
    output.addProperty("App::PropertyLinkList", "RecoveredSocketContext", "Provenance")
    output.addProperty("App::PropertyString", "Status", "Review")
    output.addProperty("App::PropertyString", "Contract", "Review")
output.Shape = fused
output.Label = "PROPOSED TOP-RIGHT — V8 SOCKET CONTEXT FUSED — REVIEW ONLY"
output.SourcePackage = source
output.RecoveredSocketContext = recovered
output.Status = "REVIEW_ONLY__FROZEN_RAIL_CONTEXT_RESTORED__NOT_PRINT_RELEASED"
output.Contract = "V7 + exact V5 C002/C020/C022/C023/C033/C034/C037/C038/C042; C032 excluded"
output.ViewObject.ShapeColor = (0.20, 0.75, 0.95)
output.ViewObject.LineColor = (0.10, 0.10, 0.10)
output.ViewObject.Transparency = 0
v6.recompute()
valid(output.Shape, "Stored V8 candidate invalid after recompute.")

print("Created %s" % OUTPUT_NAME)
print("Backfilled/restored: %s" % ", ".join(EXPECTED))
print("V7 solids: %d | V8 solids: %d" % (len(source.Shape.Solids), len(output.Shape.Solids)))
print("C002/C042 common volume: %.6f mm3" % c002_c042)
print("V7 retained: %.6f mm3" % source_retained)
print("V7 and frozen sources unchanged; V6 not saved or print-released.")

source.ViewObject.Visibility = False
for obj in recovered:
    obj.ViewObject.Visibility = False
output.ViewObject.Visibility = True
App.setActiveDocument(v6.Name)
Gui.Selection.clearSelection()
Gui.Selection.addSelection(output)
Gui.activeDocument().activeView().fitAll()
