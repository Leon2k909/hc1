"""Locate one original T2 door, preserving its existing lit/dark window exactly."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys,math
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/office-door-reuse-v1';ASSET=ROOT/'Assets/models/props/riverside/office_door_reuse_v1/review'
for p in (OUT,ASSET):p.mkdir(parents=True,exist_ok=True)
captured=[];original_door=P.door
def record(m,foot,right,**kwargs):
    old=K.Model();original_door(old,foot,right,**kwargs);captured.append((old,np.array(foot),np.array(right),kwargs))
    return original_door(m,foot,right,**kwargs)
P.door=record
name,origin,yaw,L,W=M.OFFICE
P.trailer(L,W,'rs_siding_white',seed=51,door_side=1,lit_share=.8,boarded_share=0,door_lit=True,roof_ac_model=True)
origin=(*origin,M.HIGH)
assert len(captured)==1
old,foot,right,args=captured[0];old=P.place(old,origin,yaw);M.configure(old)
# The original window remains in the background, including its original UVs/emission.
for mat in list(old.polygons):
    if mat in ('rs_lit','rs_window_dark'):del old.polygons[mat]
K.write_obj(ASSET/'old_door.obj',old,'door')
def faces(data):
    points=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':points.append(tuple(round(float(v),4) for v in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(points[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ASSET/'old_door.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';data=path.read_bytes();kept=[];cut=[]
for line,key in faces(data):
    if key and expected[key]>0:cut.append(line);expected[key]-=1
    else:kept.append(line)
assert not sum(expected.values()),('Missing original faces',sum(expected.values()))
assert len(cut)==16,len(cut)
(ASSET/'pad_without_door.obj').write_bytes(''.join(kept).encode());shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_pad.mtl')
remaps=re.findall(r'\{\s*from\s*=\s*"[^\"]+"\s+to\s*=\s*"[^\"]+"\s*\}',path.with_suffix('.vmdl').read_text())
background='models/props/riverside/office_door_reuse_v1/review/pad_without_door.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[
{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},
{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="background" filename="models/props/riverside/office_door_reuse_v1/review/pad_without_door.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}]}
]}}
'''.replace('%R%',','.join(remaps)))
base=K.to_world(P.local_to_world(foot,origin,yaw));out=K.to_world(np.cross(right,P.UP));heading=math.degrees(math.atan2(out[1],out[0]))+yaw
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene',ROOT/'Assets/models/maps/riverside/riverside_pad.obj']
plan=dict(position=base.tolist(),yaw=heading,old_triangles=len(cut),background=background,original_door_parameters={k:v for k,v in args.items()},
    protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
