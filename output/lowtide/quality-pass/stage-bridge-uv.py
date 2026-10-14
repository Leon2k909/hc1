"""Repair only the footbridge's existing UVs; retain every other OBJ byte."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

folder=Path(__file__).resolve().parent
root=folder.parents[2]
sys.path.insert(0,str(root/'Tools'))
import map_kit as K
import lowtide_map as L
import lowtide_bridge as B

path=root/'Assets/models/maps/lowtide/lowtide_fleet.obj'
original=path.read_bytes()
lines=original.decode().splitlines(keepends=True)
positions=[]
uv_lines=[]
deck_refs=set()
other_refs=set()
active=False
faces=0
for index,line in enumerate(lines):
    if line.startswith('v '):positions.append(tuple(map(float,line.split()[1:])))
    elif line.startswith('vt '):uv_lines.append(index)
    elif line.startswith('usemtl '):active=line.split()[1]==B.PAINT
    elif line.startswith('f '):
        refs=[tuple(map(int,p.split('/'))) for p in line.split()[1:]]
        if active:
            faces+=1
            deck_refs.update((v,t) for v,t,_ in refs)
        else:other_refs.update(t for _,t,_ in refs)
assert deck_refs and not {t for _,t in deck_refs}&other_refs
deck=K.Model()
B.deck_surface(deck,-L.FLEET,L.FLEET,L.FOOTBRIDGE[0]+6,L.FOOTBRIDGE[1]-6)
expected={}
for i,(points,normal) in enumerate(deck.polygons[B.PAINT]):
    for point,uv in zip(points,deck.polygon_uvs[(B.PAINT,i)]):
        # Adjacent boards share positions but have independent atlas rows.
        key=tuple(map(float,K.obj_vector(K.to_world(point)).split()))
        expected.setdefault(key,[]).append(uv)
changed=[]
old_padding=0
source,rows,atlas=B.atlas_layout()
for vertex,uv_id in sorted(deck_refs):
    index=uv_lines[uv_id-1]
    line=lines[index]
    u,v=map(float,line.split()[1:3])
    target=(u,1-v)
    assert any(abs(a-u)<1.1e-5 and abs(b-target[1])<1.1e-5 for a,b in expected[positions[vertex-1]]),(vertex,uv_id)
    old_padding+=int((1-v)*atlas>=source.shape[0])
    assert 0<target[1]<1 and 0<(1-target[1])*atlas<source.shape[0]
    newline='\r\n' if line.endswith('\r\n') else '\n'
    lines[index]=f'vt {u:.5f} {target[1]:.5f}'+newline
    changed.append(index)
assert faces==2*len(deck.polygons[B.PAINT])
assert len(changed)==4*len(deck.polygons[B.PAINT])
updated=''.join(lines).encode()
old_lines=original.decode().splitlines(keepends=True)
assert [i for i,(a,b) in enumerate(zip(old_lines,lines)) if a!=b]==sorted(changed)
before=folder/'bridge-uv-before/lowtide_fleet.obj'
before.parent.mkdir(exist_ok=True)
if before.exists():assert before.read_bytes()==original
else:before.write_bytes(original)
stage=folder/'bridge-uv-stage/lowtide_fleet.obj'
stage.parent.mkdir(exist_ok=True)
stage.write_bytes(updated)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={}
for p in (root/'Assets/models/maps/lowtide').iterdir():
    if p.suffix in ('.obj','.mtl','.vmdl') and p!=path:protected[str(p.relative_to(root))]=digest(p)
for name in ('Assets/scenes/maps/Lowtide/lowtide.scene','Tools/lowtide_bridge_source.png',
             'Assets/materials/lowtide/lt_bridge_deck.vmat'):
    p=root/name;protected[name]=digest(p)
for p in (root/'Assets/materials/lowtide').glob('lt_bridge_deck_*.png'):protected[str(p.relative_to(root))]=digest(p)
report={'before':digest(before),'after':digest(stage),'changedUvLines':changed,'boards':faces//2,
        'triangles':faces,'uvsChanged':len(changed),'previouslySamplingPadding':old_padding,
        'geometryUnchanged':True,'protected':protected}
(folder/'bridge-uv-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('changedUvLines','protected')}))
