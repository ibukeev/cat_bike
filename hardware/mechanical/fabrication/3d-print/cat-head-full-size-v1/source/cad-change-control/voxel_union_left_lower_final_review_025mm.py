"""Voxel-union the left-lower review compound into one STL review artifact."""

import os

import bpy


ROOT = "/home/bsk/Projects/BM_personal_LED-projects /cat_bike"
OUTPUT_DIR = os.path.join(
    ROOT,
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower",
)
INPUT_STL = os.path.join(OUTPUT_DIR, "input-overlap-compound.stl")
OUTPUT_STL = os.path.join(OUTPUT_DIR, "left-lower-final-review-voxel-union-025mm.stl")
VOXEL_SIZE_MM = 0.25

if not os.path.isfile(INPUT_STL):
    raise RuntimeError("Missing FreeCAD input: " + INPUT_STL)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=INPUT_STL)
items = [item for item in bpy.context.scene.objects if item.type == "MESH"]
if not items:
    raise RuntimeError("No mesh objects were imported")

bpy.ops.object.select_all(action="DESELECT")
for item in items:
    item.select_set(True)
bpy.context.view_layer.objects.active = items[0]
if len(items) > 1:
    bpy.ops.object.join()

candidate = bpy.context.view_layer.objects.active
remesh = candidate.modifiers.new(name="Voxel union 0.25 mm", type="REMESH")
remesh.mode = "VOXEL"
remesh.voxel_size = VOXEL_SIZE_MM
remesh.use_smooth_shade = False
bpy.ops.object.modifier_apply(modifier=remesh.name)

bpy.ops.object.select_all(action="DESELECT")
candidate.select_set(True)
bpy.context.view_layer.objects.active = candidate
bpy.ops.wm.stl_export(filepath=OUTPUT_STL, export_selected_objects=True)

print("EXPORTED LEFT-LOWER REVIEW STL:", OUTPUT_STL)
print("Voxel size:", VOXEL_SIZE_MM, "mm")
print("Vertices:", len(candidate.data.vertices))
print("Faces:", len(candidate.data.polygons))
