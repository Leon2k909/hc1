"""Locate the exact published gate triangles for a disposable before/after comparison."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/entrance-gate-v1';ASSET=ROOT/'Assets/models/props/riverside/entrance_gate_v1/review'
ASSET.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
old=K.Model();P.chainlink(old,[(-220,M.PAD[2]+10),(220,M.PAD[2]+10)],80,220,z=M.HIGH,barbed=True,name='gate')
M.configure(old);K.write_obj(ASSET/'old_gate.obj',old,'gate')
def faces(data):
    points=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':points.append(tuple(round(float(v),4) for v in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(points[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ASSET/'old_gate.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';original=path.read_bytes();kept=[];removed=[]
for line,key in faces(original):
    if key and expected[key]>0:removed.append(line);expected[key]-=1
    else:kept.append(line)
assert sum(expected.values())==0,('Missing exact gate faces',sum(expected.values()))
assert len(removed)==82,len(removed)
(ASSET/'pad_without_gate.obj').write_bytes(''.join(kept).encode());shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_pad.mtl')
remaps=re.findall(r'\{\s*from\s*=\s*"[^\"]+"\s+to\s*=\s*"[^\"]+"\s*\}',path.with_suffix('.vmdl').read_text())
background='models/props/riverside/entrance_gate_v1/review/pad_without_gate.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[
{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},
{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="background" filename="models/props/riverside/entrance_gate_v1/review/pad_without_gate.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}]}
]}}
'''.replace('%R%',','.join(remaps)))
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
plan=dict(position=[M.PAD[2]+10,0,M.HIGH],old_triangles=len(removed),background=background,
    protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
