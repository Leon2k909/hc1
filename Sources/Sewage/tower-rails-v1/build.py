from pathlib import Path
from collections import Counter
import sys,math,json,hashlib
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/tower-rails-v1';STAGE=OUT/'stage/Assets/models/maps/sewage/tower-rails-v1'
STAGE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_parts as P,riverdale_splice as S
R.PAINTS.update(yellow=64,steel=96,rust=96)
old=R.model();c=np.array((180,510))
for i in range(64):
    a=2*math.pi*i/64;b=2*math.pi*(i+1)/64
    R.rail(old,c+293*np.array([math.cos(a),math.sin(a)]),c+293*np.array([math.cos(b),math.sin(b)]),792,collide=False)
K.write_obj(OUT/'original-rails.obj',old,'sewage_tower')
_,remove=S.read_obj(OUT/'original-rails.obj')
original=ROOT/'Assets/models/maps/sewage/tower-vents-v1/base_tower.obj'
header,published=S.read_obj(original)
assert not Counter(remove)-Counter(published),'Old railing geometry does not match'
remaining=Counter(remove);preserved=[]
for face in published:
    if remaining[face]:remaining[face]-=1
    else:preserved.append(face)
assert not +remaining
S.write_obj(STAGE/'base_tower.obj',header,preserved)
(STAGE/'base_tower.mtl').write_bytes(original.with_suffix('.mtl').read_bytes())
vmdl=original.with_suffix('.vmdl').read_text().replace('filename = "models/maps/sewage/tower-vents-v1/base_tower.obj"','filename = "models/maps/sewage/tower-rails-v1/base_tower.obj"')
(STAGE/'base_tower.vmdl').write_text(vmdl)
m=K.Model();m.material_overrides.update(paint='materials/riverdale/rv_hall_paint_yellow.vmat',metal='materials/sewage/crane-blocks-v1/steel.vmat',dark='materials/sewage/crane-blocks-v1/dark.vmat')
m.tile_overrides.update(paint=64,metal=32,dark=32)
Z=P.UP
for z in (812,834):P.torus(m,(180,510,z),Z,293,1.8,'paint',256,10)
for i in range(32):
    a=2*math.pi*i/32
    radial=np.array((math.cos(a),math.sin(a),0));tangent=np.array((-math.sin(a),math.cos(a),0))
    foot=np.array((180,510,792))+293*radial
    P.bevel_box(m,foot+(0,0,1.2),(radial,tangent,Z),(9.5,9.5,2.4),'metal',.45)
    P.rod(m,foot+(0,0,2.4),foot+(0,0,42),2.25,'paint',20,True)
    P.torus(m,foot+(0,0,2.8),Z,2.35,.25,'dark',24,6)
    for z in (20,42):
        P.torus(m,foot+(0,0,z),Z,2.3,.22,'metal',24,6)
    for r in (-3.4,3.4):
        for t in (-3.4,3.4):
            q=foot+radial*r+tangent*t
            P.rod(m,q+(0,0,2.4),q+(0,0,2.8),1,'dark',16,True)
            P.rod(m,q+(0,0,2.8),q+(0,0,4),.7,'metal',6,True)
# A low rolled toe board closes the gap at the deck edge without changing collision.
P.lathe_axis(m,(180,510,792),Z,[(291.2,.2),(292.5,.2),(292.5,5.2),(291.2,5.2),(291.2,.2)],'paint',256)
triangles=K.write_model(STAGE,'models/maps/sewage/tower-rails-v1','rails',m)
plan=dict(removed_faces=len(remove),preserved_faces=len(preserved),new_triangles=triangles,posts=32,original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(plan)
