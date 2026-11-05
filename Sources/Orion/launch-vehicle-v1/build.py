"""Stage reproducible inputs for the approved, installed Orion launch vehicle."""
from pathlib import Path
import sys,math,json,hashlib
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import orion_parts as O
import orion_map as R
OUT=ROOT/'output/orion/launch-vehicle-v1';STAGE=OUT/'stage/Assets';RES='models/props/orion/launch_vehicle_v1';MODEL=STAGE/RES
MODEL.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
H=float(R.ROCKET_H);r=float(R.ROCKET_R)
from orion_launch_vehicle import model

def write(path,m,name):
    K.write_obj(path,m,name);lines=path.read_text().splitlines(keepends=True);v=np.array([l.split()[1:] for l in lines if l.startswith('v ')],float);out=[];count=0
    for l in lines:
        if l.startswith('f '):
            ids=[int(t.split('/')[0])-1 for t in l.split()[1:]];q=v[ids]
            if np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))<1e-8:continue
            count+=1
        out.append(l)
    path.write_text(''.join(out));return count
models=[];counts=[]
for lod in range(3):
    m=model(lod);models.append(m);counts.append(write(MODEL/f'vehicle_lod{lod}.obj',m,f'vehicle_lod{lod}'))
K.write_vmdl(MODEL/'vehicle.vmdl',RES,'vehicle_lod0',models[0]);doc=(MODEL/'vehicle.vmdl').read_text()
a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/vehicle_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,90,200)))
(MODEL/'vehicle.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
manifest=dict(installed=True,triangles=counts,height=H,radius=r,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'build-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'installed':True}))
