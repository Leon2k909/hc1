"""One detailed storage locker, preserving Ares' original finishes and physics."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import ares_map as R
import riverdale_parts as G
import railhead_dress_detail as D
OUT=ROOT/'output/ares/locker-v1';STAGE=OUT/'stage';RES='models/maps/ares/locker-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
public=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';text=public.read_text()
paths=list((ROOT/'Assets/models/maps/ares').rglob('*'))+list((ROOT/'Assets/materials/ares').rglob('*'))+[ROOT/'Assets/scenes/maps/Ares/ares.scene',ROOT/'Tools/ares_map.py',ROOT/'Tools/ares_interior.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'locker-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));C=np.array((1278.,-709.,0.))
def P(x,d,z):return C+X*x+Y*d+Z*z
def box(c,size,paint='ar_steel',b=.10):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
def cyl(c,axis,length,r,paint='ar_steel',sides=20):G.lathe_axis(m,P(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
def screw(x,d,z):
 cyl((x,d,z),Y,.035,.16,'ar_steel',16)
 box((x,d+.039,z),(.17,.008,.035),'ar_dark',.003)
# Folded sheet enclosure with a recessed toe plinth and separate top cap.
box((0,-.4,1.8),(25.,21.2,3.6),'ar_gunmetal',.22)
box((0,0,83.15),(25.,22.,1.7),'ar_steel',.32)
box((0,-10.6,43.0),(24.1,.8,79.0),'ar_steel',.20)
for s in (-1,1):
 box((s*12.05,0,43.0),(.9,22.,79.0),'ar_steel',.21)
 box((s*11.82,10.53,43.0),(1.18,.94,78.8),'ar_steel',.13)
 for d in (-8.6,8.6):cyl((s*9.8,d,0),Z,1.15,.75,'ar_dark',20)
box((0,0,4.05),(23.3,20.9,.9),'ar_steel',.16)
# The gasket sits behind a formed door: recessed centre and raised folded edges.
box((0,10.54,43.0),(23.35,.32,78.2),'ar_dark',.16)
box((0,10.54,43.0),(22.65,.36,77.0),'ar_white',.20)
for s in (-1,1):box((s*10.90,10.95,43.0),(.85,.46,76.5),'ar_white',.14)
for z in (5.05,80.95):box((0,10.95,z),(22.3,.46,.85),'ar_white',.14)
box((0,10.77,7.2),(20.0,.09,.055),'ar_dark',.012)
# Pressed ventilation slots with dark recesses and real angled metal blades.
angle=math.radians(18);out=Y*math.cos(angle)+Z*math.sin(angle);up=-Y*math.sin(angle)+Z*math.cos(angle)
for centre in (16.,71.0):
 box((0,10.76,centre),(15.0,.08,8.1),'ar_dark',.06)
 for j in range(6):
  G.bevel_box(m,P(0,10.98,centre-3.1+j*1.24),(X,out,up),(14.6,.65,.40),'ar_gunmetal',bevel=.065)
 for x in (-7.57,7.57):box((x,10.82,centre),(.18,.18,8.3),'ar_gunmetal',.035)
# Three serviceable hinge barrels and their mounting leaves.
for z in (16.,43.,70.):
 for x in (-11.55,-10.48):
  box((x,10.93,z),(.68,.36,2.8),'ar_steel',.10)
  for zz in (z-.9,z+.9):screw(x,11.13,zz)
 cyl((-11.0,11.10,z-1.7),Z,3.4,.31,'ar_steel',24)
 for zz in (z-1.73,z+1.65):cyl((-11.,11.1,zz),Z,.13,.37,'ar_brass',20)
# Recessed pull pocket, rounded brass handle and a keyed cylinder.
box((6.1,10.78,48.2),(3.3,.09,7.2),'ar_dark',.18)
G.tube(m,[P(6.1,10.90,45.5),P(6.1,11.64,46.0),P(6.1,11.64,50.4),P(6.1,10.90,50.9)],.23,'ar_brass',sides=16,bend_radius=.4)
for z in (45.5,50.9):cyl((6.1,10.86,z),Y,.20,.39,'ar_brass',24)
cyl((6.1,10.78,53.1),Y,.40,.47,'ar_brass',32)
box((6.1,11.19,53.1),(.095,.018,.58),'ar_dark',.012)
# Small inset identifier: geometry lettering stays sharp without a glowing card.
box((-1.0,10.83,58.4),(7.1,.21,4.2),'ar_steel',.17)
box((-1.0,10.95,58.4),(6.6,.05,3.7),'ar_dark',.08)
segments={'0':'abcedf','4':'bcfg'}
lines={'a':((0,1),(1,1)),'b':((1,1),(1,.5)),'c':((1,.5),(1,0)),'d':((0,0),(1,0)),'e':((0,0),(0,.5)),'f':((0,.5),(0,1)),'g':((0,.5),(1,.5))}
for i,char in enumerate('04'):
 for seg in segments[char]:
  a,b=lines[seg];a=np.array((-2.75+i*2.0+a[0]*1.15,57.20+a[1]*2.4));b=np.array((-2.75+i*2.0+b[0]*1.15,57.20+b[1]*2.4))
  dv=b-a;side=np.array((-dv[1],dv[0]))/np.linalg.norm(dv)*.065
  D._face(m,'ar_white',[P(-q[0]-2.0,10.99,q[1]) for q in (a-side,b-side,b+side,a+side)],Y)
for x in (-11.7,11.7):
 for z in (4.7,81.2):screw(x,11.03,z)
R.configure(m);count=K.write_model(MODEL,RES,'locker',m)
legacy=K.Model();legacy.box((1265.5,-720,0),(1290.5,-698,84),{'default':'ar_steel','+n':'ar_gunmetal'});legacy.box((1276,-698,50),(1280,-697,56),'ar_brass');R.configure(legacy)
K.write_obj(OUT/'legacy-locker.obj',legacy,'legacy_locker')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-locker.obj');wanted=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj';assert 'models/maps/ares/pressure-doors-v2/hall_base.obj' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved locker differs from legacy boxes; inspect before staging'
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib hall_without_locker.mtl',content)
(MODEL/'hall_without_locker.obj').write_text(content)
mtllib=re.search(r'(?m)^mtllib (.+)$',source.read_text()).group(1).strip()
(MODEL/'hall_without_locker.mtl').write_bytes((source.parent/mtllib).read_bytes())
(MODEL/'hall_without_locker.vmdl').write_text(text.replace('models/maps/ares/pressure-doors-v2/hall_base.obj',RES+'/hall_without_locker.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/ReefHall/office-chair-v1/import.cs.txt').read_text().replace('reefhall/office-chair-v1','ares/locker-v1')
(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files),existing_materials_reused=True)))
