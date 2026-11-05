"""Private review of the T2 concrete entry unit, with current door/roof/hitch upgrades retained."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys,math
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/t2-precast-entry-v1';ASSET=ROOT/'Assets/models/props/riverside/t2_precast_entry_v1/review'
for p in (OUT,ASSET):p.mkdir(parents=True,exist_ok=True)
captured=[];original=P.steps
def record(m,foot,along,width,z_top,*args,**kw):
    old=K.Model();original(old,foot,along,width,z_top,*args,**kw);captured.append((old,np.array(foot),np.array(along),width,z_top))
    return original(m,foot,along,width,z_top,*args,**kw)
P.steps=record
name,origin,yaw,L,W,tint,side,seed,extra=M.LOW_TRAILERS[0];M.build_trailer(name,L,W,tint,side,seed,extra);P.steps=original
assert len(captured)==1
old,foot,along,width,height=captured[0];assert width==36 and height==29
old=P.place(old,(*origin,0),yaw);M.configure(old);K.write_obj(ASSET/'old_steps.obj',old,'steps')
def faces(data):
    pts=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':pts.append(tuple(round(float(q),4) for q in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ASSET/'old_steps.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_low.obj';data=path.read_bytes();kept=[];cut=[]
for line,key in faces(data):
    if key and expected[key]>0:cut.append(line);expected[key]-=1
    else:kept.append(line)
assert not sum(expected.values()) and len(cut)==48,(sum(expected.values()),len(cut))
(ASSET/'low_without_steps.obj').write_bytes(''.join(kept).encode());shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_low.mtl')
remaps=re.findall(r'\{\s*from\s*=\s*"[^\"]+"\s+to\s*=\s*"[^\"]+"\s*\}',path.with_suffix('.vmdl').read_text())
background='models/props/riverside/t2_precast_entry_v1/review/low_without_steps.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="background" filename="models/props/riverside/t2_precast_entry_v1/review/low_without_steps.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}]}]}}
'''.replace('%R%',','.join(remaps)))
pos=K.to_world(P.local_to_world(foot,(*origin,0),yaw));a=K.to_world(along);heading=math.degrees(math.atan2(a[1],a[0]))+yaw
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene',ROOT/'Assets/materials/riverdale/rv_precast.vmat']+[ROOT/f'Assets/materials/riverdale/rv_precast_{x}' for x in ('color.jpg','normal.png','rough.png')]
plan=dict(position=pos.tolist(),yaw=heading,width=36,depth=40,height=29,risers=4,old_triangles=48,background=background,protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(position=pos.tolist(),yaw=heading,old_triangles=48),indent=2))
