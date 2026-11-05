"""Locate the complete NO PLACE BETTER cabinet, keeping the pole/physics/lights."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys,math
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/neon-sign-v1';ASSET=ROOT/'Assets/models/props/riverside/neon_sign_v1/review'
for p in (OUT,ASSET):p.mkdir(parents=True,exist_ok=True)
base,facing=M.NO_PLACE;old=K.Model();P.neon_sign(old,base,facing)
for mat in list(old.polygons):
    if mat not in ('rs_dark','rs_lit'):del old.polygons[mat]
M.configure(old);K.write_obj(ASSET/'old_cabinet.obj',old,'neon_cabinet')
def faces(data):
    pts=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':pts.append(tuple(round(float(q),4) for q in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ASSET/'old_cabinet.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_dressing.obj';data=path.read_bytes();kept=[];cut=[]
for line,key in faces(data):
    if key and expected[key]>0:cut.append(line);expected[key]-=1
    else:kept.append(line)
assert not sum(expected.values()) and len(cut)==16,(sum(expected.values()),len(cut))
(ASSET/'dressing_without_cabinet.obj').write_bytes(''.join(kept).encode());shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_dressing.mtl')
remaps=re.findall(r'\{\s*from\s*=\s*"[^\"]+"\s+to\s*=\s*"[^\"]+"\s*\}',path.with_suffix('.vmdl').read_text())
background='models/props/riverside/neon_sign_v1/review/dressing_without_cabinet.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="background" filename="models/props/riverside/neon_sign_v1/review/dressing_without_cabinet.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}]}]}}
'''.replace('%R%',','.join(remaps)))
pos=K.to_world(np.array(base)+P.UP*410);f=K.to_world(P.unit((*facing,0)));yaw=math.degrees(math.atan2(f[1],f[0]))
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
shared=ROOT/'Assets/materials/riverside/shop-sign-v1'
protected+=list(shared.glob('*.vmat'))+[shared/f'paint_{name}.png' for name in ('color','normal','rough')]
plan=dict(position=pos.tolist(),yaw=yaw,old_triangles=16,background=background,lettering='NO / PLACE / BETTER',shared_materials='shop-sign-v1',protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(position=pos.tolist(),yaw=yaw,old_triangles=16),indent=2))
