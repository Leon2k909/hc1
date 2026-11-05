"""Reuse the Belltower shed lock, splicing only changed gate hardware."""
from pathlib import Path
from collections import Counter
import hashlib, importlib.util, json, sys
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/gate-shed-lock-v1'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, riverdale_splice as S
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'Tools/sewage_tunnel_gates.py'
frozen=HERE/'gate-before.py'
assert not (OUT/'plan.json').exists(), 'Revision already staged'
if not frozen.exists():frozen.write_bytes(source.read_bytes())
spec=importlib.util.spec_from_file_location('gate_before',frozen);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
text=frozen.read_text();start=text.index('    # Central slide bolt,');end=text.index('    return m',start)
replacement='''    # Reuse the existing detailed shed hasp and padlock as one correctly seated assembly.
    import belltower_padlock as P
    P.build(m,(-.4,-10.88,62),((0,1.7,0),(-1.7,0,0),(0,0,1.7)))
    m.material_overrides.update({
        'door_brass':'materials/belltower/fountain_bronze.vmat',
        'iron_black':'materials/buildings/iron_black.vmat',
    })
    m.tile_overrides.update({'door_brass':32,'iron_black':32})
'''
source.write_text(text[:start]+replacement+text[end:])
import sewage_tunnel_gates as new
meshes=[]
for mod,label in ((old,'old'),(new,'new')):
    mesh=K.Model()
    for p in mod.PLACEMENTS:mod.emit(mesh,*p)
    K.write_obj(OUT/(label+'.obj'),mesh,'sewage_shell');meshes.append(mesh)
_,before=S.read_obj(OUT/'old.obj');_,after=S.read_obj(OUT/'new.obj')
removed=Counter(before)-Counter(after);added=Counter(after)-Counter(before)
pub=ROOT/'Assets/models/maps/sewage/sewage_shell.obj';header,faces=S.read_obj(pub)
assert not removed-Counter(faces),'Published gate hardware changed'
retained=Counter(faces)-removed;result=list(retained.elements())+list(added.elements())
baseline=OUT/'baseline';install=OUT/'install'
baseline.mkdir();install.mkdir()
for suffix in ('.obj','.mtl','.vmdl'):(baseline/pub.with_suffix(suffix).name).write_bytes(pub.with_suffix(suffix).read_bytes())
S.write_obj(install/pub.name,header,result)
mtl=pub.with_suffix('.mtl').read_text();doc=pub.with_suffix('.vmdl').read_text()
extra={k:v for k,v in meshes[1].material_overrides.items() if k not in old.MATERIALS}
for k,v in extra.items():
    assert f'newmtl {k}\n' not in mtl
    mtl+=f'newmtl {k}\nKd 1 1 1\nd 1\n'
anchor='{ from = "ww_gate_lock.vmat" to = "materials/sewage/crane-blocks-v1/paint.vmat" }'
assert doc.count(anchor)==1
newdoc=doc.replace(anchor,anchor+',\n'+',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in extra.items()))
(install/pub.with_suffix('.mtl').name).write_text(mtl);(install/pub.with_suffix('.vmdl').name).write_text(newdoc)
assert doc[doc.index('_class = "PhysicsShapeList"'):]==newdoc[newdoc.index('_class = "PhysicsShapeList"'):]
assert Counter(S.read_obj(install/pub.name)[1])==retained+added
plan=dict(locks=2,removed_triangles=sum(removed.values()),added_triangles=sum(added.values()),retained_triangles=sum(retained.values()),collision_unchanged=True,
    baseline={p.name:sha(p) for p in baseline.iterdir()},install_files={p.name:sha(p) for p in install.iterdir()},
    hull_hash=sha(ROOT/'Assets/models/maps/sewage/sewage_shell_hulls_default.obj'),reuse='Tools/belltower_padlock.py',materials=extra)
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
# A preserved current model supports matched native before/after closeups.
preview=OUT/'preview';preview.mkdir()
(preview/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_shell.mtl',b'before.mtl'))
(preview/'before.mtl').write_bytes(pub.with_suffix('.mtl').read_bytes())
(preview/'before.vmdl').write_text(doc.replace('models/maps/sewage/sewage_shell.obj','models/maps/sewage/gate-shed-lock-v1/before.obj'))
for name in ('native.py','install.cs.txt'):
    (HERE/name).write_text((HERE.parent/'tunnel-gates-v1'/name).read_text(encoding='utf-8-sig').replace('sewage/tunnel-gates-v1','sewage/gate-shed-lock-v1'))
capture=(HERE.parent/'tunnel-gates-v1/capture-installed.cs.txt').read_text().replace('sewage/tunnel-gates-v1','sewage/gate-shed-lock-v1')
capture=capture.replace('(Name:"green",Eye:W(-1260,-225,84),Target:W(-1486,-230,80),Fov:64f),(Name:"red",Eye:W(1260,85,84),Target:W(1486,80,80),Fov:64f)', '(Name:"lock",Eye:W(-1435,-216,67),Target:W(-1480,-230,61),Fov:40f),(Name:"gate",Eye:W(-1260,-225,84),Target:W(-1486,-230,80),Fov:64f)')
(HERE/'capture.cs.txt').write_text(capture)
print(json.dumps(plan,indent=2))
