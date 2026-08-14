#!/usr/bin/env python3
"""Build a Prusa-compatible 3MF with separate movable A/B coupon objects."""
import argparse,json,struct,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[6]
NS="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
SNS="http://schemas.slic3r.org/3mf/2017/06"

def mesh(path):
    data=path.read_bytes()
    count=struct.unpack_from("<I",data,80)[0]
    if len(data)!=84+50*count: raise RuntimeError(f"Invalid binary STL: {path}")
    verts=[]; faces=[]; ids={}
    for off in range(84,len(data),50):
        row=struct.unpack_from("<12fH",data,off); face=[]
        for raw in (row[3:6],row[6:9],row[9:12]):
            v=tuple(float(x) for x in raw)
            if v not in ids: ids[v]=len(verts); verts.append(v)
            face.append(ids[v])
        faces.append(tuple(face))
    lo=[min(v[i] for v in verts) for i in range(3)]
    hi=[max(v[i] for v in verts) for i in range(3)]
    cx=(lo[0]+hi[0])/2; cy=(lo[1]+hi[1])/2
    verts=[(x-cx,y-cy,z-lo[2]) for x,y,z in verts]
    return verts,faces,tuple(hi[i]-lo[i] for i in range(3))

def object_xml(resources,oid,name,verts,faces):
    obj=ET.SubElement(resources,f"{{{NS}}}object",{"id":str(oid),"type":"model","name":name})
    m=ET.SubElement(obj,f"{{{NS}}}mesh")
    vs=ET.SubElement(m,f"{{{NS}}}vertices")
    for x,y,z in verts:
        ET.SubElement(vs,f"{{{NS}}}vertex",{"x":f"{x:.9g}","y":f"{y:.9g}","z":f"{z:.9g}"})
    ts=ET.SubElement(m,f"{{{NS}}}triangles")
    for a,b,c in faces:
        ET.SubElement(ts,f"{{{NS}}}triangle",{"v1":str(a),"v2":str(b),"v3":str(c)})

def prusa_xml(config,oid,name,count):
    obj=ET.SubElement(config,"object",{"id":str(oid),"instances_count":"1"})
    ET.SubElement(obj,"metadata",{"type":"object","key":"name","value":name})
    vol=ET.SubElement(obj,"volume",{"firstid":"0","lastid":str(count-1)})
    for k,v in (("name",name),("volume_type","ModelPart"),("source_file",name),("source_object_id","0"),("source_volume_id","0")):
        ET.SubElement(vol,"metadata",{"type":"volume","key":k,"value":v})
    ET.SubElement(vol,"mesh",{"edges_fixed":"0","degenerate_facets":"0","facets_removed":"0","facets_reversed":"0","backwards_edges":"0"})

def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,required=True); a=p.parse_args()
    cfg=json.loads(a.config.resolve().read_text()); out=cfg["outputs"]
    directory=(ROOT/out["output_dir"]).resolve()
    entries=[(1,"RIGHT_A_V4_SHORT_INSERT_COUPON",directory/out["a_stl"]),(2,"RIGHT_B_V2_SHORT_INSERT_COUPON",directory/out["b_stl"])]
    meshes=[(oid,name,*mesh(path)) for oid,name,path in entries]
    ET.register_namespace("",NS); ET.register_namespace("slic3rpe",SNS)
    model=ET.Element(f"{{{NS}}}model",{"unit":"millimeter","{http://www.w3.org/XML/1998/namespace}lang":"en-US"})
    ET.SubElement(model,f"{{{NS}}}metadata",{"name":"slic3rpe:Version3mf"}).text="1"
    ET.SubElement(model,f"{{{NS}}}metadata",{"name":"Title"}).text=cfg["review_id"]
    ET.SubElement(model,f"{{{NS}}}metadata",{"name":"Description"}).text="Separate movable A/B exact coupon objects; user controls print orientation"
    resources=ET.SubElement(model,f"{{{NS}}}resources"); build=ET.SubElement(model,f"{{{NS}}}build"); pcfg=ET.Element("config")
    gap=12.0; txs=(-gap/2-meshes[0][4][0]/2,gap/2+meshes[1][4][0]/2)
    for (oid,name,verts,faces,size),tx in zip(meshes,txs):
        object_xml(resources,oid,name,verts,faces)
        ET.SubElement(build,f"{{{NS}}}item",{"objectid":str(oid),"transform":f"1 0 0 0 1 0 0 0 1 {tx:.9g} 0 0","printable":"1"})
        prusa_xml(pcfg,oid,name,len(faces))
    types=b"""<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>"""
    rels=b"""<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>"""
    dest=directory/out["slicer_project"]
    with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",types); z.writestr("_rels/.rels",rels)
        z.writestr("3D/3dmodel.model",ET.tostring(model,encoding="utf-8",xml_declaration=True))
        z.writestr("Metadata/Slic3r_PE_model.config",ET.tostring(pcfg,encoding="utf-8",xml_declaration=True))
    print(dest)

if __name__=="__main__": main()
