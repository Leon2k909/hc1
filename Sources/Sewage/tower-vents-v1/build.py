"""Stage louvred pump breather housings; preserve all unrelated tower faces."""
from pathlib import Path
from collections import Counter
import math,sys,json,hashlib
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/tower-vents-v1'
STAGE=OUT/'stage/Assets/models/maps/sewage/tower-vents-v1'
STAGE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_parts as P,riverdale_splice as S
from riverside_parts import place
PLACEMENTS=((-85,500,792),(70,520,792),(210,560,792),(340,510,792))
R.PAINTS.update(steel=96,rust=96)
old=R.model()
for e,n,z in PLACEMENTS:
    old.cylinder((e,n),26,z,z+53,'steel',sides=16)
    old.cylinder((e,n),29,z+50,z+56,'rust',sides=16)
K.write_obj(OUT/'original-housings.obj',old,'sewage_tower')
_,remove=S.read_obj(OUT/'original-housings.obj')
original=ROOT/'Assets/models/maps/sewage/sewage_tower.obj'
header,published=S.read_obj(original)
missing=Counter(remove)-Counter(published)
assert not missing,f'{sum(missing.values())} old vent faces no longer match; do not splice'
remaining=Counter(remove);preserved=[]
for face in published:
    if remaining[face]:remaining[face]-=1
    else:preserved.append(face)
assert not +remaining
S.write_obj(STAGE/'base_tower.obj',header,preserved)
(STAGE/'base_tower.mtl').write_bytes(original.with_suffix('.mtl').read_bytes())
vmdl=original.with_suffix('.vmdl').read_text(encoding='utf-8').replace('filename = "models/maps/sewage/sewage_tower.obj"','filename = "models/maps/sewage/tower-vents-v1/base_tower.obj"')
(STAGE/'base_tower.vmdl').write_text(vmdl,encoding='utf-8')

vent=K.Model()
vent.material_overrides.update(shell='materials/sewage/pipe-texture-v1/pipe.vmat',dark='materials/sewage/crane-blocks-v1/dark.vmat',hardware='materials/sewage/crane-blocks-v1/steel.vmat')
vent.tile_overrides.update(shell=64,dark=64,hardware=32)
Z=P.UP
def lathe(profile,paint='shell',sides=48,cap=None):P.lathe_axis(vent,(0,0,0),Z,profile,paint,sides,cap)
def axle(c,r,length,paint='hardware',sides=24):
    c=np.asarray(c,float);P.rod(vent,c-Z*length/2,c+Z*length/2,r,paint,sides,True)
# Rolled mounting flange, black gasket and a recessed cylindrical filter core.
lathe([(0,0),(29.8,0),(31,1),(31,3.2),(29.8,4.2),(23,4.2),(23,7)],'hardware',cap='hardware')
lathe([(23,4.2),(24,4.6),(24,6.3),(23,6.6)],'dark')
lathe([(22,6.5),(22,45)],'dark',cap='dark')
# Five overlapping rain-shedding louvres with visible gaps to the dark core.
for h in (8,15,22,29,36):
    lathe([(22,h),(27.4,h+.8),(27.8,h+1.5),(27.8,h+2.3),(24.0,h+5.0),(22,h+5.0)])
# Tapered cowl keeps the existing top outlet at the same 848-unit height.
lathe([(22,43),(29.6,44.3),(30.4,45.4),(30.4,47.2),(29.2,48.5),(12.2,54.8),(10.2,54.8),(10.2,56)])
P.torus(vent,(0,0,46.1),Z,30.45,.32,'hardware',48,6)
# Slender tie rods and eight restrained flange fasteners.
for a in np.linspace(0,2*math.pi,3,endpoint=False):
    c=np.array((26.5*math.cos(a),26.5*math.sin(a),0))
    P.rod(vent,c+(0,0,6.7),c+(0,0,42),.65,'hardware',10,True)
for a in np.linspace(0,2*math.pi,8,endpoint=False):
    x,y=27.4*math.cos(a),27.4*math.sin(a)
    axle((x,y,4.5),1.9,.55,'dark',20)
    axle((x,y,5.4),1.35,1.3,'hardware',6)
all_vents=K.Model()
for origin in PLACEMENTS:all_vents.extend(place(vent,origin,0))
triangles=K.write_model(STAGE,'models/maps/sewage/tower-vents-v1','vents',all_vents)
plan=dict(housings=len(PLACEMENTS),removed_faces=len(remove),preserved_faces=len(preserved),new_triangles=triangles,original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
print(plan)
