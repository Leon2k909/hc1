from pathlib import Path
from collections import Counter
import sys,math,json,hashlib
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/tower-deck-v1';STAGE=OUT/'stage/Assets/models/maps/sewage/tower-deck-v1'
STAGE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_parts as P,riverdale_splice as S
R.PAINTS['grate']=96
old=R.model();old.cylinder((180,510),293,782,792,'grate',sides=64,surface='metal')
K.write_obj(OUT/'old-deck.obj',old,'sewage_tower')
_,remove=S.read_obj(OUT/'old-deck.obj')
original=ROOT/'Assets/models/maps/sewage/tower-rails-v1/base_tower.obj'
header,published=S.read_obj(original)
assert not Counter(remove)-Counter(published),'Old deck no longer matches'
remaining=Counter(remove);preserved=[]
for face in published:
    if remaining[face]:remaining[face]-=1
    else:preserved.append(face)
assert not +remaining
S.write_obj(STAGE/'base_tower.obj',header,preserved)
(STAGE/'base_tower.mtl').write_bytes(original.with_suffix('.mtl').read_bytes())
vmdl=original.with_suffix('.vmdl').read_text().replace('filename = "models/maps/sewage/tower-rails-v1/base_tower.obj"','filename = "models/maps/sewage/tower-deck-v1/base_tower.obj"')
(STAGE/'base_tower.vmdl').write_text(vmdl)
m=K.Model();m.material_overrides.update(steel='materials/sewage/tower-deck-v1/coated_steel.vmat',frame='materials/sewage/pipe-texture-v1/pipe.vmat',dark='materials/sewage/crane-blocks-v1/dark.vmat')
m.tile_overrides.update(steel=32,frame=64,dark=32)
c=np.array((180,510,0));Z=P.UP
# Solid inner/outer edge bands; all upper bearing surfaces remain at z=792.
for r0,r1,low in ((242,246,788),(291,293,782)):
    profile=[tuple(map(float,p)) for p in [(r0,low),(r1,low),(r1,792),(r0,792),(r0,low)]]
    P.lathe_axis(m,(180,510,0),Z,profile,'frame',512)
# Thin radial bearing bars with eight wider panel-divider ribs.
for i in range(1024):
    a=2*math.pi*i/1024;radial=np.array((math.cos(a),math.sin(a),0));tangent=np.array((-math.sin(a),math.cos(a),0))
    divider=i%128==0
    width,depth=(1.4,5.5) if divider else (.45,2.8)
    center=c+radial*268.5+np.array((0,0,792-depth/2))
    m.oriented_box(center,(radial,tangent,Z),(45,width,depth),'frame' if divider else 'steel')
# Recessed cross rods form true openings between the bearing bars.
for r in (249,257,265,273,281,289):P.torus(m,(180,510,791.5),Z,r,.28,'steel',512,6)
for i in range(8):
    a=2*math.pi*i/8;radial=np.array((math.cos(a),math.sin(a),0))
    for r in (244,292):
        p=c+radial*r
        P.rod(m,p+(0,0,792),p+(0,0,792.35),1,'dark',16,True)
        P.rod(m,p+(0,0,792.35),p+(0,0,793.25),.7,'steel',6,True)
triangles=K.write_model(STAGE,'models/maps/sewage/tower-deck-v1','deck',m)
plan=dict(removed_faces=len(remove),preserved_faces=len(preserved),new_triangles=triangles,original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(plan)
