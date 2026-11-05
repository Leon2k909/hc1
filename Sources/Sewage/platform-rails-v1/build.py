"""Exact splice of seven central platform rails; preserve installed stair work and collision."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/platform-rails-v1';OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'plan.json').exists(),'Already staged'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S,sewage_platform_rails as T
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
R.PAINTS.update(yellow=64,rust=96)
old,new=R.model(),K.Model()
for a,b in T.PLACEMENTS:R.rail(old,a,b,160);T.emit(new,a,b)
for label,mesh in (('old',old),('new',new)):K.write_obj(OUT/(label+'.obj'),mesh,'sewage_catwalks')
_,removed=S.read_obj(OUT/'old.obj');_,added=S.read_obj(OUT/'new.obj')
pub=ROOT/'Assets/models/maps/sewage/sewage_catwalks.obj';header,faces=S.read_obj(pub)
assert not Counter(removed)-Counter(faces),'Original railing geometry changed; inspect first'
retained=Counter(faces)-Counter(removed);result=list(retained.elements())+added
baseline=OUT/'baseline';install=OUT/'install';preview=OUT/'preview'
for folder in (baseline,install,preview):folder.mkdir()
for suffix in ('.obj','.mtl','.vmdl'):(baseline/pub.with_suffix(suffix).name).write_bytes(pub.with_suffix(suffix).read_bytes())
S.write_obj(install/pub.name,header,result)
mtl=pub.with_suffix('.mtl').read_text();doc=pub.with_suffix('.vmdl').read_text()
mtl+=''.join(f'newmtl {k}\nKd 1 1 1\nd 1\n' for k in T.MATERIALS)
anchor='{ from = "yellow.vmat" to = "materials/sewage/yellow.vmat" }';assert doc.count(anchor)==1
newdoc=doc.replace(anchor,anchor+',\n'+',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in T.MATERIALS.items()))
(install/pub.with_suffix('.mtl').name).write_text(mtl);(install/pub.with_suffix('.vmdl').name).write_text(newdoc)
assert newdoc[newdoc.index('_class = "PhysicsShapeList"'):]==doc[doc.index('_class = "PhysicsShapeList"'):]
assert Counter(S.read_obj(install/pub.name)[1])==retained+Counter(added)
(preview/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_catwalks.mtl',b'before.mtl'))
(preview/'before.mtl').write_bytes(pub.with_suffix('.mtl').read_bytes())
(preview/'before.vmdl').write_text(doc.replace('models/maps/sewage/sewage_catwalks.obj','models/maps/sewage/platform-rails-v1/before.obj'))
plan=dict(segments=len(T.PLACEMENTS),removed_triangles=len(removed),added_triangles=len(added),retained_triangles=sum(retained.values()),collision_unchanged=True,
 baseline={p.name:sha(p) for p in baseline.iterdir()},install_files={p.name:sha(p) for p in install.iterdir()},hull_hash=sha(pub.with_name('sewage_catwalks_hulls_metal.obj')),
 reuse='riverdale_parts.railing, corrected closed rail sockets; unchanged kit source',existing_upgrades_checked=['power_cabinet_v2','salvage-drums-v1','work-lamps-v1','tower-vents-v1','valve-wheels-v1','pipe-flanges-v1','stair-treads-v1'])
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
for name in ('native.py','install.cs.txt','import.cs.txt'):
 text=(HERE.parent/'gate-shed-lock-v1'/name).read_text(encoding='utf-8-sig').replace('sewage/gate-shed-lock-v1','sewage/platform-rails-v1')
 (HERE/name).write_text(text)
capture=(HERE.parent/'gate-lock-v2/capture.cs.txt').read_text().replace('sewage/gate-lock-v2','sewage/platform-rails-v1').replace('Waterworks shell"','Waterworks shell"')
capture=capture.replace('g.Name=="Waterworks shell"','g.Name=="Waterworks catwalks"').replace('models/maps/sewage/sewage_shell.vmdl','models/maps/sewage/sewage_catwalks.vmdl')
capture=capture.replace('"Waterworks bolted flanges"','"Waterworks bolted flanges","Waterworks louvred vent housings"')
start=capture.index(' var views=');end=capture.index('\n foreach(var view',start)
capture=capture[:start]+' var views=new[]{(Name:"platform",Eye:W(-390,-210,228),Target:W(90,95,182),Fov:61f),(Name:"fittings",Eye:W(-95,-2,196),Target:W(10,95,182),Fov:50f)};'+capture[end:]
(HERE/'capture.cs.txt').write_text(capture)
source=ROOT/'Tools/sewage_map.py';text=source.read_text();anchor='def rail(m,a,b,z,height=42,collide=True):\n'
assert text.count(anchor)==1
replacement=anchor+'''    from sewage_platform_rails import matches,emit
    if matches(a,b,z,height):
        emit(m,a,b,z,height)
        if collide:m.beam((*a,z+height*.5),(*b,z+height*.5),(3,height),None,'metal')
        return
'''
(HERE/'sewage_map-before.py').write_bytes(source.read_bytes());source.write_text(text.replace(anchor,replacement))
print(json.dumps(plan,indent=2))
