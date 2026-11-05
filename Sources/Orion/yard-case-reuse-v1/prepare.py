"""Review an already approved equipment case at a close-range Orion yard placement."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,re
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import orion_map as R
import orion_parts as O
import riverdale_parts as G
OUT=ROOT/'output/orion/yard-case-reuse-v1';STAGE=OUT/'stage/Assets';RES='models/props/orion/yard_case_reuse_v1';MODEL=STAGE/RES;MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
center=np.array((18.,601.))+np.random.default_rng(10).normal(0,.6,2)
m=K.Model();G.case(m,center,(70,40,46),(1,0),'rv_olive',O.PALLET_H,None);R.configure(m)
K.write_obj(OUT/'generated.obj',m,'generated')
def records(path):
    lines=path.read_text().splitlines(keepends=True);vertices=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):faces.append((i,(paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,wantedfaces=records(OUT/'generated.obj');wanted=Counter(k for _,k in wantedfaces)
source=ROOT/'Assets/models/maps/orion/orion_props.obj';lines,actual=records(source);remaining=wanted.copy();cut=set()
for i,key in actual:
    if remaining[key]:remaining[key]-=1;cut.add(i)
assert cut and not +remaining,'Original case does not match the current packed map'
(MODEL/'preview.obj').write_text(''.join(line for i,line in enumerate(lines) if i not in cut))
attributes=[[line for line in lines if line.startswith(prefix)] for prefix in ('v ','vt ','vn ')]
selected=[];paint=''
for i,line in enumerate(lines):
    if line.startswith('usemtl '):paint=line.split()[1]
    elif i in cut:selected.append((paint,[[int(x)-1 for x in t.split('/')] for t in line.split()[1:]]))
used=[sorted({token[k] for _,face in selected for token in face}) for k in range(3)]
mapping=[{old:new+1 for new,old in enumerate(group)} for group in used]
compact=['# Exact current case; original attributes retained, unused records omitted\n','mtllib before.mtl\n','o before\n']
for k,group in enumerate(used):compact.extend(attributes[k][index] for index in group)
paint=None
for material,face in selected:
    if paint!=material:compact.append(f'usemtl {material}\n');paint=material
    compact.append('f '+' '.join('/'.join(str(mapping[k][token[k]]) for k in range(3)) for token in face)+'\n')
(MODEL/'before.obj').write_text(''.join(compact))
for name in ('preview','before'):
    path=MODEL/f'{name}.obj';s=path.read_text();s=re.sub(r'^mtllib .+$',f'mtllib {name}.mtl',s,flags=re.M);path.write_text(s)
    (MODEL/f'{name}.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
doc=source.with_suffix('.vmdl').read_text()
(MODEL/'preview.vmdl').write_text(doc.replace('filename = "models/maps/orion/orion_props.obj"',f'filename = "{RES}/preview.obj"'))
K.write_vmdl(MODEL/'before.vmdl',RES,'before',m)
for name in ('generated.obj','generated.mtl'):(OUT/name).unlink()
shared=[p for d in ('Assets/models/props/collider/equipment-case-trial-v1','Assets/materials/collider/equipment-case-trial-v1') for p in (ROOT/d).rglob('*') if p.is_file() and not p.name.endswith(('.meta','_c'))]
public=[ROOT/'Assets/scenes/maps/Orion/orion.scene',source,source.with_suffix('.mtl'),source.with_suffix('.vmdl')]
manifest=dict(preview_only=True,existing_model_reused='models/props/collider/equipment-case-trial-v1/after.vmdl',
    audit=dict(checked=['Orion and Collider source/readme/acceptance records','Spillway control desk','project equipment-case/hardcase model and source filenames'],
               decision='Reuse the already approved Collider case; no duplicate upgraded mesh or materials',
               target='Single 70x40x46 case on a pallet beside the central playable yard route, original case_block seed 10'),
    original_triangles=len(cut),replacement_triangles=15568,position_plan=[*map(float,center),O.PALLET_H],
    original_face_lines=sorted(cut),
    position_world=[float(center[1]),float(-center[0]),O.PALLET_H],scale_world=[40/56,70/100,46/65],
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in public+shared},
    files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','protected','original_face_lines')},indent=2))
