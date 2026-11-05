"""Stage caged bulkhead work lamps and a details mesh with only old lamps removed."""
from pathlib import Path
from collections import Counter
import math, sys, json, hashlib
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/work-lamps-v1'
STAGE=OUT/'stage/Assets/models/maps/sewage/work-lamps-v1'
STAGE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, sewage_map as R, riverdale_parts as P, riverdale_splice as S
from riverside_parts import place
AMBER=[(-960,-560,310),(-720,-600,52),(-680,-110,205),(-850,260,226),(-900,670,414),(-380,920,424),(460,920,424),(900,620,414),(880,-300,220),(-850,-380,610),(850,-350,610),(-360,180,610),(470,180,610),(-100,240,815),(410,320,815),(250,780,815)]
PLACEMENTS=[(p,'amber') for p in AMBER]+[((-940,-230,220),'green')]+[(p,'red') for p in [(935,80,228),(-900,270,175),(835,280,175)]]+[(p,'white') for p in [(-820,510,120),(820,520,130),(145,215,55),(-200,-800,240)]]
R.PAINTS.update(steel=96,**{f'lamp_{c}':64 for c in ('amber','white','green','red')})
old=R.model()
for p,kind in PLACEMENTS: R.lamp(old,p,kind)
K.write_obj(OUT/'original-lamps.obj',old,'sewage_details')
_,remove=S.read_obj(OUT/'original-lamps.obj')
original=ROOT/'Assets/models/maps/sewage/sewage_details.obj'
header,published=S.read_obj(original)
missing=Counter(remove)-Counter(published)
assert not missing,f'{sum(missing.values())} original lamp faces do not match; do not splice'
remaining=Counter(remove);preserved=[]
for face in published:
    if remaining[face]: remaining[face]-=1
    else: preserved.append(face)
assert not +remaining
S.write_obj(STAGE/'base_details.obj',header,preserved)
(STAGE/'base_details.mtl').write_bytes(original.with_suffix('.mtl').read_bytes())
vmdl=original.with_suffix('.vmdl').read_text(encoding='utf-8').replace('filename = "models/maps/sewage/sewage_details.obj"','filename = "models/maps/sewage/work-lamps-v1/base_details.obj"')
(STAGE/'base_details.vmdl').write_text(vmdl,encoding='utf-8')
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.UP
def fixture(kind):
    m=K.Model()
    lens='glass_'+kind
    m.material_overrides.update(body='materials/sewage/crane-blocks-v1/steel.vmat',dark='materials/sewage/crane-blocks-v1/dark.vmat')
    m.material_overrides[lens]=f'materials/sewage/lamp_{kind}.vmat'
    m.tile_overrides.update(body=32,dark=32)
    m.tile_overrides[lens]=64
    def box(c,size,paint='body',bevel=.4):P.bevel_box(m,c,(X,Y,Z),size,paint,bevel)
    def axle(c,axis,r,length,paint='body',sides=16):
        c=np.asarray(c,float);axis=np.asarray(axis,float)
        P.rod(m,c-axis*length/2,c+axis*length/2,r,paint,sides,caps=True)
    # Back casting, black gasket and inset chamfered lens.
    box((0,1,0),(22,8,12),'body',1.5)
    box((0,-3.4,0),(20.2,1.0,10.2),'dark',1.0)
    box((0,-5.7,0),(18.4,4.0,9.0),lens,1.5)
    # Lower diffuser preserves the original fixture's downward glow.
    box((0,-1,-5.9),(16,5,.45),lens,.18)
    # Lens flutes: shallow ribs remain visible around the edges of the diffuser.
    for x in np.linspace(-7.6,7.6,13):
        P.rod(m,(x,-7.78,-3.1),(x,-7.78,3.1),.12,lens,6,True)
    # Cast frame and domed protective cage, clear of the glowing glass.
    for z in (-5.2,5.2):P.rod(m,(-9.8,-7.5,z),(9.8,-7.5,z),.46,'dark',8,True)
    for x in (-9.8,9.8):P.rod(m,(x,-7.5,-5.2),(x,-7.5,5.2),.46,'dark',8,True)
    for x in (-7,-3.5,0,3.5,7):
        points=[(x,-7.4,-5.3),(x,-9.4,-3.4),(x,-10.1,0),(x,-9.4,3.4),(x,-7.4,5.3)]
        P.pipe(m,points,.34,'body',sides=8,bend=.7)
    P.rod(m,(-9.8,-10.15,0),(9.8,-10.15,0),.3,'dark',8,True)
    # Mounting ears, fasteners and a sealed side cable gland.
    for sign in (-1,1):
        box((sign*12.5,3,0),(4,2,6),'body',.65)
        axle((sign*12.5,1.7,0),Y,1.35,1.0,'dark',20)
        axle((sign*12.5,.9,0),Y,.85,1.0,'body',6)
        for z in (-4.3,4.3):axle((sign*9,-4.0,z),Y,.5,.6,'body',6)
    axle((-12,1,-1),X,2.1,4,'dark',12)
    axle((-14,1,-1),X,2.5,1.4,'body',6)
    P.pipe(m,[(-14.8,1,-1),(-17.5,1,-1),(-19,2,-2.5),(-19.5,3,-6)],.65,'dark',sides=8,bend=1.4)
    return m
models={kind:fixture(kind) for kind in ('amber','white','green','red')}
lamps=K.Model()
for origin,kind in PLACEMENTS: lamps.extend(place(models[kind],origin,0))
triangles=K.write_model(STAGE,'models/maps/sewage/work-lamps-v1','lamps',lamps)
plan=dict(fixtures=len(PLACEMENTS),removed_faces=len(remove),preserved_faces=len(preserved),new_triangles=triangles,original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
print(plan)
