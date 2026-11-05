from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/discharge-elbows-v1';OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'plan.json').exists()
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S,sewage_discharge_elbows as T
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
R.PAINTS.update(steel=96,rust=96)
old,new=R.model(),K.Model()
for e in T.PLACEMENTS:T.original(old,e);T.emit(new,e)
for label,mesh in (('old',old),('new',new)):K.write_obj(OUT/(label+'.obj'),mesh,'base_pipework')
_,removed=S.read_obj(OUT/'old.obj');_,added=S.read_obj(OUT/'new.obj')
pub=ROOT/'Assets/models/maps/sewage/valve-wheels-v1/base_pipework.obj';header,faces=S.read_obj(pub)
assert not Counter(removed)-Counter(faces),'Installed outlet geometry no longer matches'
retained=Counter(faces)-Counter(removed);result=list(retained.elements())+added
baseline=OUT/'baseline';install=OUT/'install';preview=OUT/'preview'
for folder in (baseline,install,preview):folder.mkdir()
for suffix in ('.obj','.mtl','.vmdl'):(baseline/pub.with_suffix(suffix).name).write_bytes(pub.with_suffix(suffix).read_bytes())
S.write_obj(install/pub.name,header,result)
mtl=pub.with_suffix('.mtl').read_text();doc=pub.with_suffix('.vmdl').read_text()
mtl+=''.join(f'newmtl {k}\nKd 1 1 1\nd 1\n' for k in T.MATERIALS)
anchor='{ from = "steel.vmat" to = "materials/sewage/steel.vmat" }';assert doc.count(anchor)==1
newdoc=doc.replace(anchor,anchor+',\n'+',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in T.MATERIALS.items()))
(install/pub.with_suffix('.mtl').name).write_text(mtl);(install/pub.with_suffix('.vmdl').name).write_text(newdoc)
assert newdoc[newdoc.index('_class = "PhysicsShapeList"'):]==doc[doc.index('_class = "PhysicsShapeList"'):]
assert Counter(S.read_obj(install/pub.name)[1])==retained+Counter(added)
(preview/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_pipework.mtl',b'before.mtl').replace(b'base_pipework.mtl',b'before.mtl'))
(preview/'before.mtl').write_bytes(pub.with_suffix('.mtl').read_bytes())
(preview/'before.vmdl').write_text(doc.replace('models/maps/sewage/valve-wheels-v1/base_pipework.obj','models/maps/sewage/discharge-elbows-v1/before.obj'))
plan=dict(elbows=2,removed_triangles=len(removed),added_triangles=len(added),retained_triangles=sum(retained.values()),collision_unchanged=True,
 baseline={p.name:sha(p) for p in baseline.iterdir()},install_files={p.name:sha(p) for p in install.iterdir()},
 reused='riverdale_parts smooth sweep, turned rings and fasteners; existing approved pipe finish',original_public_untouched='models/maps/sewage/sewage_pipework.vmdl')
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
for name in ('native.py','install.cs.txt','import.cs.txt'):
 text=(HERE.parent/'gate-shed-lock-v1'/name).read_text(encoding='utf-8-sig').replace('sewage/gate-shed-lock-v1','sewage/discharge-elbows-v1')
 if name=='install.cs.txt':text=text.replace('"Assets/models/maps/sewage",p.Key','"Assets/models/maps/sewage/valve-wheels-v1",p.Key')
 (HERE/name).write_text(text)
capture=(HERE.parent/'platform-rails-v1/capture.cs.txt').read_text().replace('sewage/platform-rails-v1','sewage/discharge-elbows-v1')
capture=capture.replace('g.Name=="Waterworks catwalks"','g.Name=="Waterworks pipework"').replace('models/maps/sewage/sewage_catwalks.vmdl','models/maps/sewage/valve-wheels-v1/base_pipework.vmdl')
start=capture.index(' var views=');end=capture.index('\n foreach(var view',start)
capture=capture[:start]+' var views=new[]{(Name:"outlet",Eye:W(-215,50,590),Target:W(-48,320,645),Fov:53f),(Name:"pair",Eye:W(180,-150,630),Target:W(180,325,645),Fov:76f)};'+capture[end:]
(HERE/'capture.cs.txt').write_text(capture)
source=ROOT/'Tools/sewage_map.py';text=source.read_text();anchor='        pipe(pipes,points,34,open_end=True)';assert text.count(anchor)==1
(HERE/'sewage-map-before.py').write_bytes(source.read_bytes())
source.write_text(text.replace(anchor,"        from sewage_discharge_elbows import emit as draw_discharge_elbow\n        draw_discharge_elbow(pipes,e)\n        pipes.beam(points[0],points[1],(56.1,56.1),None,'metal',up=(0,0,1))"))
print(json.dumps(plan,indent=2))
