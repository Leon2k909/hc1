"""Stage four detailed valve wheels; remove only the exact original wheel faces."""
from pathlib import Path
from collections import Counter
import math, sys, json, hashlib
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/valve-wheels-v1'
STAGE=OUT/'stage/Assets/models/maps/sewage/valve-wheels-v1'
STAGE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, sewage_map as R, riverdale_parts as P, riverdale_splice as S
from riverside_parts import place
PLACEMENTS=((-958,-650,195),(872,-320,80),(-940,420,220),(930,620,310))
R.PAINTS.update(steel=96,rust=96)
old=R.model()
for e,n,z in PLACEMENTS:
    R.torus(old,(e,n,z),(0,1,0),22,2.8,'rust',24)
    for t in np.linspace(0,2*math.pi,5,endpoint=False):
        R.tube(old,(e,n,z),(e+20*math.cos(t),n,z+20*math.sin(t)),1.7,'steel',8)
    R.tube(old,(e,n-14,z),(e,n+14,z),4,'steel',12)
K.write_obj(OUT/'original-wheels.obj',old,'sewage_pipework')
_,remove=S.read_obj(OUT/'original-wheels.obj')
original=ROOT/'Assets/models/maps/sewage/sewage_pipework.obj'
header,published=S.read_obj(original)
missing=Counter(remove)-Counter(published)
assert not missing,f'{sum(missing.values())} original wheel faces no longer match; do not splice'
remaining=Counter(remove)
preserved=[]
for face in published:
    if remaining[face]: remaining[face]-=1
    else: preserved.append(face)
assert not +remaining
S.write_obj(STAGE/'base_pipework.obj',header,preserved)
(STAGE/'base_pipework.mtl').write_bytes(original.with_suffix('.mtl').read_bytes())
vmdl=original.with_suffix('.vmdl').read_text(encoding='utf-8')
vmdl=vmdl.replace('filename = "models/maps/sewage/sewage_pipework.obj"','filename = "models/maps/sewage/valve-wheels-v1/base_pipework.obj"')
(STAGE/'base_pipework.vmdl').write_text(vmdl,encoding='utf-8')

wheel=K.Model()
wheel.material_overrides.update(enamel='materials/riverdale/rv_valve_red.vmat',steel='materials/sewage/crane-blocks-v1/steel.vmat',dark='materials/sewage/crane-blocks-v1/dark.vmat')
wheel.tile_overrides.update(enamel=48,steel=32,dark=32)
Y=P.v(0,1,0)
def axle(c,r,length,paint='steel',sides=32):
    c=np.array(c,float)
    P.rod(wheel,c-Y*length/2,c+Y*length/2,r,paint,sides,caps=True)
# Stem, packed gland, cast hub and retaining hardware.
axle((0,-9,0),3.3,20,'steel')
P.lathe_axis(wheel,(0,-12,0),Y,[(5.5,0),(6.2,1),(6.2,3),(4.7,4),(4.7,9),(6.4,10),(6.4,12),(5.6,13),(5.6,16),(4.8,17)],'dark',32,cap='dark')
axle((0,-5,0),5.1,3,'steel',6)
P.lathe_axis(wheel,(0,-2,0),Y,[(6.5,0),(7.2,.7),(7.2,4),(6.3,5),(5.2,5.6)],'enamel',40,cap='enamel')
# Smooth rounded rim and five dished, swept cast spokes.
P.torus(wheel,(0,0,0),Y,22,2.85,'enamel',64,12)
for angle in np.linspace(0,2*math.pi,5,endpoint=False):
    points=[]
    for t in np.linspace(0,1,7):
        r=6+15.8*t
        a=angle+.14*t
        points.append((r*math.cos(a),3.2*(1-t),r*math.sin(a)))
    P.pipe(wheel,points,1.9,'enamel',sides=10,bend=.5,caps=True)
    tip=np.array(points[-1]);axle(tip,2.3,2.6,'enamel',16)
axle((0,4.15,0),4.6,1.1,'steel',40)
P.torus(wheel,(0,4.8,0),Y,3.9,.25,'dark',32,6)
axle((0,5.9,0),3.3,2.1,'steel',6)
axle((0,7.1,0),1.15,.6,'dark',6)
# A small spindle key projects through the cap instead of a featureless central cylinder.
P.bevel_box(wheel,(0,7.45,0),(P.v(1,0,0),Y,P.UP),(1.5,.3,.45),'steel',.12)
all_wheels=K.Model()
for e,n,z in PLACEMENTS:
    # The original wheel is buried in its vertical pipe. Extend the spindle
    # towards the aisle and give the first wheel clearance from the wall.
    all_wheels.extend(place(wheel,(e+(5 if e==-958 else 0),n+26,z),0))
triangles=K.write_model(STAGE,'models/maps/sewage/valve-wheels-v1','wheels',all_wheels)
plan=dict(removed_faces=len(remove),preserved_faces=len(preserved),new_triangles=triangles,placements=PLACEMENTS,original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
print(plan)
