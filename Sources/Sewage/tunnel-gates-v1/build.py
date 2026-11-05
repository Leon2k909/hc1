"""Stage two genuinely new tunnel-end gates after auditing existing gate models."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/tunnel-gates-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S,sewage_tunnel_gates as T
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OUT.mkdir(parents=True,exist_ok=True)
baseline=OUT/'baseline';baseline.mkdir(exist_ok=True)
pub=ROOT/'Assets/models/maps/sewage/sewage_shell.obj'
for suffix in ('.obj','.mtl','.vmdl'):
    source=pub.with_suffix(suffix);target=baseline/source.name
    if target.exists():assert target.read_bytes()==source.read_bytes(),'Published shell changed'
    else:target.write_bytes(source.read_bytes())
R.PAINTS.update(steel=96,concrete=256)
old_mesh=R.model();new_mesh=K.Model()
for placement in T.PLACEMENTS:
    T.original_end(old_mesh,*placement);T.emit(new_mesh,*placement)
K.write_obj(OUT/'old-ends.obj',old_mesh,'sewage_shell')
K.write_obj(OUT/'new-gates.obj',new_mesh,'sewage_shell')
_,removed=S.read_obj(OUT/'old-ends.obj');_,added=S.read_obj(OUT/'new-gates.obj')
header,published=S.read_obj(pub)
assert not Counter(removed)-Counter(published),'Original tunnel ends no longer match published geometry'
retained=Counter(published)-Counter(removed);result=list(retained.elements())+added
for _,corners in added:
    points=[np.array([float(x) for x in c[0].split()]) for c in corners]
    assert all(np.isfinite(p).all() for p in points)
    cross=np.cross(points[1]-points[0],points[2]-points[0])
    assert np.linalg.norm(cross)>1e-5,'Degenerate gate triangle'
    if corners[0][2]:
        normal=np.array([float(x) for x in corners[0][2].split()])
        assert np.dot(cross,normal)>0,'Gate winding opposes shading normals'
modeldir=STAGE/'Assets/models/maps/sewage/tunnel-gates-v1';modeldir.mkdir(parents=True,exist_ok=True)
S.write_obj(modeldir/'after.obj',['mtllib after.mtl\n','o after\n'],result)
(modeldir/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_shell.mtl',b'before.mtl'))
old_mtl=pub.with_suffix('.mtl').read_text()
new_mtl=old_mtl+''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in sorted(T.MATERIALS))
doc=pub.with_suffix('.vmdl').read_text()
marker='{ from = "steel.vmat" to = "materials/sewage/steel.vmat" }'
assert doc.count(marker)==1
remaps=',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in T.MATERIALS.items())
new_doc=doc.replace(marker,marker+',\n'+remaps)
for name,material,source_doc in (('before',old_mtl,doc),('after',new_mtl,new_doc)):
    (modeldir/f'{name}.mtl').write_text(material)
    (modeldir/f'{name}.vmdl').write_text(source_doc.replace('models/maps/sewage/sewage_shell.obj',f'models/maps/sewage/tunnel-gates-v1/{name}.obj'))
install=OUT/'install';install.mkdir(exist_ok=True)
S.write_obj(install/'sewage_shell.obj',header,result)
(install/'sewage_shell.mtl').write_text(new_mtl)
(install/'sewage_shell.vmdl').write_text(new_doc)
_,installed=S.read_obj(install/'sewage_shell.obj')
assert Counter(installed)==retained+Counter(added)
assert new_doc[new_doc.index('_class = "PhysicsShapeList"'):]==doc[doc.index('_class = "PhysicsShapeList"'):]
plan=dict(gates=2,removed_triangles=len(removed),added_triangles=len(added),retained_triangles=sum(retained.values()),total_triangles=len(result),collision_unchanged=True,
 baseline={p.name:sha(p) for p in baseline.iterdir() if p.is_file()},
 hull_hash=sha(ROOT/'Assets/models/maps/sewage/sewage_shell_hulls_default.obj'),
 preview_files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 install_files={p.name:sha(p) for p in install.iterdir() if p.is_file()},
 existing_models_checked=['Belltower town gate v2: timber/wrought-iron town doors','Veridant gates v1: solid outdoor forecourt leaves','Ares pressure doors v3: rectangular sliding doors','Riverside entrance gate v1: rejected chain-link proposal'],
 selection='No matching arched sewer grille replacement found; new tunnel-specific model')
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
for source in ('import.cs.txt','install.cs.txt','native.py'):
    text=(ROOT/'Sources/sewage/warning-sign-v1'/source).read_text().replace('sewage/warning-sign-v1','sewage/tunnel-gates-v1')
    (HERE/source).write_text(text)
capture=(ROOT/'Sources/sewage/stair-treads-v1/capture.cs.txt').read_text().replace('sewage/stair-treads-v1','sewage/tunnel-gates-v1')
capture=capture.replace('g.Name=="Waterworks catwalks"','g.Name=="Waterworks shell"').replace('Warning sign review camera','Tunnel gate review camera')
capture=capture.replace('"Chamber suspended moisture"','"Chamber suspended moisture","Waterworks caged work lamps","Waterworks valve wheels","Waterworks bolted flanges"')
start=capture.index(' var views=');end=capture.index('\n foreach(var view',start)
capture=capture[:start]+' var views=new[]{(Name:"green",Eye:W(-1260,-225,84),Target:W(-1486,-230,80),Fov:64f),(Name:"red",Eye:W(1260,85,84),Target:W(1486,80,80),Fov:64f)};'+capture[end:]
(HERE/'capture.cs.txt').write_text(capture)
