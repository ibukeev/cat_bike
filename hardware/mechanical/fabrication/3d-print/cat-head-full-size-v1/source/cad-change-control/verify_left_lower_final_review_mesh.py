"""Write manifold/connectivity health for the left-lower review STL."""

import json
import os

import bmesh
import bpy


ROOT = "/home/bsk/Projects/BM_personal_LED-projects /cat_bike"
OUTPUT_DIR = os.path.join(
    ROOT,
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower",
)
INPUT_STL = os.path.join(OUTPUT_DIR, "left-lower-final-review-voxel-union-025mm.stl")
REPORT = os.path.join(OUTPUT_DIR, "mesh-health.json")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=INPUT_STL)
items = [item for item in bpy.context.scene.objects if item.type == "MESH"]
if len(items) != 1:
    raise RuntimeError("Expected one mesh object, got %d" % len(items))

bm = bmesh.new()
bm.from_mesh(items[0].data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

parent = list(range(len(bm.verts)))
def find(index):
    while parent[index] != index:
        parent[index] = parent[parent[index]]
        index = parent[index]
    return index
def join(left, right):
    left, right = find(left), find(right)
    if left != right:
        parent[right] = left

for edge in bm.edges:
    join(edge.verts[0].index, edge.verts[1].index)

nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
boundary = sum(len(edge.link_faces) == 1 for edge in bm.edges)
wire = sum(len(edge.link_faces) == 0 for edge in bm.edges)
components = len({find(vertex.index) for vertex in bm.verts})
report = {
    "input_stl": INPUT_STL,
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "nonmanifold_edges": nonmanifold,
    "boundary_edges": boundary,
    "wire_edges": wire,
    "connected_components": components,
    "watertight_single_component": nonmanifold == 0 and components == 1,
}
with open(REPORT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps(report, sort_keys=True))
bm.free()
