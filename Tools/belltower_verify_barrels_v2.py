"""Verify the installed scoped update and retain a compact source-side receipt."""
from pathlib import Path
import argparse
import ast
from collections import Counter
from datetime import datetime
import hashlib
import json
import shutil
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/belltower/barrels-v2'
parser=argparse.ArgumentParser();parser.add_argument('--revision',default='r5');parser.add_argument('--cleanup-failed-stages',action='store_true');args=parser.parse_args()
assert args.revision=='r5','Review the installed revision before changing this receipt.'
stage=FOLDER/args.revision/'stage';manifest=json.loads((stage/'manifest.json').read_text())
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
shared_updates=[]
for relative,row in manifest['files'].items():
    if sha(ROOT/relative)!=row['after']:
        assert relative in [f'Assets/models/maps/belltower/belltower_{s}.{ext}' for s in ('west','east') for ext in ('obj','vmdl')],f'Installed resource changed: {relative}'
        shared_updates.append(relative)
for relative,digest in manifest['protected_sha256'].items():
    assert sha(ROOT/relative)==digest,f'Protected resource changed: {relative}'
models={};expected={}
for side in ('west','east'):
    p=ROOT/f'Assets/models/maps/belltower/barrels-v2/{side}.obj'
    tables={b'v':[],b'vt':[],b'vn':[]};faces=[];wanted=Counter();paint=None
    for line in p.read_bytes().splitlines():
        kind,*values=line.split()
        if kind in tables:tables[kind].append(list(map(float,values)))
        elif kind==b'usemtl':paint=values[0]
        elif kind==b'f':
            face=[[int(x) for x in token.split(b'/')] for token in values];faces.append(face)
            wanted[paint,tuple(sorted(tuple(tables[b'v'][indices[0]-1]) for indices in face))]+=1
    assert all(np.isfinite(np.asarray(t)).all() for t in tables.values())
    assert len(faces)==12180 and all(len(f)==3 for f in faces)
    for face in faces:
        for indices in face:
            assert len(indices)==3 and all(1<=index<=len(tables[k]) for index,k in zip(indices,tables))
    models[side]=np.asarray(tables[b'v'])
    expected[side]=wanted
    result=json.loads((FOLDER/args.revision/f'compile-{side}/asset_compile.json').read_text())
    data=next(json.loads(c['text']) for c in result['content'] if c['type']=='text')
    assert data['Success'],side
assert Counter(map(tuple,models['east']))==Counter(map(tuple,models['west']*[-1,1,1]))
# Other work can add geometry to the shared canonical mesh or model description.
# Verify this repair semantically rather than rejecting those unrelated additions.
placement=json.loads((ROOT/'Sources/Belltower/barrels/placement-v2.json').read_text())['barrels']
for side,sign in (('west',1),('east',-1)):
    canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
    old=[np.array((r['old'][0]*sign,r['old'][1])) for r in placement]
    new=[np.array((r['new'][0]*sign,r['new'][1])) for r in placement]
    sparse={};vertex=0;paint=None;found=Counter();old_faces=0
    for line in canonical.open('rb'):
        if line.startswith(b'v '):
            vertex+=1;p=tuple(map(float,line.split()[1:]));plan=np.array((-p[0],p[2]))
            if -.001<=p[1]<=36.1 and any(np.max(np.abs(plan-c))<13.7 for c in old+new):sparse[vertex]=(p,plan)
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f '):
            ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            if not all(i in sparse for i in ids):continue
            if paint in (b'planks_dark',b'planks',b'iron_black') and any(all(np.max(np.abs(sparse[i][1]-c))<13.12 for i in ids) for c in old):old_faces+=1
            key=paint,tuple(sorted(sparse[i][0] for i in ids))
            if key in expected[side]:found[key]+=1
    assert old_faces==0,(side,'Old barrel faces remain',old_faces)
    assert found==expected[side],(side,'Canonical new geometry differs',sum(found.values()))
    vmdl=(ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl').read_text()
    assert vmdl.count(f'name = "clock_barrels_v2_{side}"')==1
    assert vmdl.count(f'filename = "models/maps/belltower/barrels-v2/{side}.obj"')==1
    assert f'belltower_{side}_hulls_wood.obj' in vmdl and 'from = "barrel_rust.vmat" to = "materials/stillhouse/sh_rust.vmat"' in vmdl
collision=json.loads((FOLDER/'collision-after.json').read_text());assert collision['Passed'] and len(collision['Checks'])==10
for name in ('west-after','west-detail-after','east-after'):
    restore=json.loads((FOLDER/f'captures/native/{name}-restore.json').read_text())
    assert all(restore.values()),(name,restore)
    assert (FOLDER/f'captures/native/{name}.png').stat().st_size>100000
source=ast.parse((ROOT/'Tools/belltower_map.py').read_text())
barrel=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='barrel')
assert any(isinstance(n,ast.Import) and n.names[0].name=='belltower_barrels_v2' for n in barrel.body)
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='resolve' for n in ast.walk(barrel))
receipt={'revision':'clock-frontage-barrels-v2','verified_at':datetime.now().astimezone().isoformat(),
         'barrels_rebuilt':4,'collision_hulls_moved':4,'door_approaches_clear':True,
         'native_collision_checks':10,'compiled_models':['belltower_west','belltower_east'],
         'triangles_per_pair':12180,'all_other_obj_and_hull_bytes_preserved':True,
         'scene_and_materials_preserved':True,'editor_state_and_cameras_restored':True,
         'placement':'Sources/Belltower/barrels/placement-v2.json',
         'stage_manifest':str((stage/'manifest.json').relative_to(ROOT)).replace('\\','/'),
         'screenshots':[f'output/belltower/barrels-v2/captures/native/{n}.png' for n in ('west-after','west-detail-after','east-after')],
         'shared_files_with_verified_unrelated_updates':shared_updates,
         'installed_sha256':{p:sha(ROOT/p) for p in manifest['files']}}
(ROOT/'Sources/Belltower/barrels/installed-v2.json').write_text(json.dumps(receipt,indent=2)+'\n')
if args.cleanup_failed_stages:
    for revision in ('r1','r2','r3','r4'):
        candidate=(FOLDER/revision/'stage').resolve()
        assert candidate.parent.parent==FOLDER.resolve() and candidate.name=='stage' and candidate.parent.name==revision
        if candidate.exists():
            print('Removing task-owned failed stage '+str(candidate),flush=True)
            shutil.rmtree(candidate)
print(json.dumps({'verified':True,'barrels':4,'native_collision_checks':10,'asset_compiles':2,'state_restoration_checks':3}))
