from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/stair-treads-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S,sewage_stair_treads as T
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OUT.mkdir(parents=True,exist_ok=True)
baseline=OUT/'baseline';baseline.mkdir(exist_ok=True)
pub=ROOT/'Assets/models/maps/sewage/sewage_catwalks.obj'
for suffix in ('.obj','.mtl','.vmdl'):
    source=pub.with_suffix(suffix);target=baseline/source.name
    if target.exists():assert target.read_bytes()==source.read_bytes(),'Published catwalks changed'
    else:target.write_bytes(source.read_bytes())
R.PAINTS.update(steel=96,grate=96,yellow=64)
old_mesh=T.original_treads(R.model(),*T.MAIN_FLIGHT)
K.write_obj(OUT/'old-treads.obj',old_mesh,'sewage_catwalks')
new_mesh=T.emit(K.Model(),*T.MAIN_FLIGHT)
K.write_obj(OUT/'new-treads.obj',new_mesh,'sewage_catwalks')
_,removed=S.read_obj(OUT/'old-treads.obj');_,added=S.read_obj(OUT/'new-treads.obj')
header,published=S.read_obj(pub)
assert not Counter(removed)-Counter(published),'Original flight no longer matches published geometry'
assert len(removed)==480
retained=Counter(published)-Counter(removed);result=list(retained.elements())+added
for _,corners in added:
    pts=[np.array([float(x) for x in c[0].split()]) for c in corners]
    assert all(np.isfinite(p).all() for p in pts)
    assert np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))>1e-5
modeldir=STAGE/'Assets/models/maps/sewage/stair-treads-v1';modeldir.mkdir(parents=True,exist_ok=True)
S.write_obj(modeldir/'after.obj',['mtllib after.mtl\n','o after\n'],result)
(modeldir/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_catwalks.mtl',b'before.mtl'))
old_mtl=pub.with_suffix('.mtl').read_text()
new_mtl=old_mtl+''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in sorted(T.MATERIALS))
doc=pub.with_suffix('.vmdl').read_text()
marker='{ from = "yellow.vmat" to = "materials/sewage/yellow.vmat" }'
assert doc.count(marker)==1
remaps=',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in T.MATERIALS.items())
new_doc=doc.replace(marker,marker+',\n'+remaps)
for name,material,source_doc in (('before',old_mtl,doc),('after',new_mtl,new_doc)):
    (modeldir/f'{name}.mtl').write_text(material)
    (modeldir/f'{name}.vmdl').write_text(source_doc.replace('models/maps/sewage/sewage_catwalks.obj',f'models/maps/sewage/stair-treads-v1/{name}.obj'))
install=OUT/'install';install.mkdir(exist_ok=True)
S.write_obj(install/'sewage_catwalks.obj',header,result)
(install/'sewage_catwalks.mtl').write_text(new_mtl)
(install/'sewage_catwalks.vmdl').write_text(new_doc)
_,installed=S.read_obj(install/'sewage_catwalks.obj')
assert Counter(installed)==retained+Counter(added)
assert new_doc[new_doc.index('_class = "PhysicsShapeList"'):]==doc[doc.index('_class = "PhysicsShapeList"'):]
plan=dict(removed_triangles=len(removed),added_triangles=len(added),retained_triangles=sum(retained.values()),total_triangles=len(result),collision_unchanged=True,
 baseline={p.name:sha(p) for p in baseline.iterdir() if p.is_file()},
 hull_hash=sha(ROOT/'Assets/models/maps/sewage/sewage_catwalks_hulls_metal.obj'),
 preview_files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 install_files={p.name:sha(p) for p in install.iterdir() if p.is_file()})
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
# Native import/install wrappers use the same hash-guarded asset workflow as the accepted sign.
for source,target in (('import.cs.txt','import.cs.txt'),('install.cs.txt','install.cs.txt'),('native.py','native.py')):
    text=(ROOT/'Sources/sewage/warning-sign-v1'/source).read_text().replace('sewage/warning-sign-v1','sewage/stair-treads-v1')
    (HERE/target).write_text(text)
capture=(ROOT/'Sources/sewage/warning-sign-v1/capture.cs.txt').read_text().replace('sewage/warning-sign-v1','sewage/stair-treads-v1')
capture=capture.replace('g.Name=="Waterworks signage"','g.Name=="Waterworks catwalks"')
capture=capture.replace('var views=new[]{(Name:"close",Eye:W(-790,-510,95),Target:W(-615,-400,35),Fov:43f),(Name:"rear",Eye:W(-510,-310,80),Target:W(-611,-400,35),Fov:51f)};',
    'var views=new[]{(Name:"flight",Eye:W(-690,-310,170),Target:W(-845,80,80),Fov:54f),(Name:"close",Eye:W(-775,-130,68),Target:W(-845,45,50),Fov:65f)};')
(HERE/'capture.cs.txt').write_text(capture)
