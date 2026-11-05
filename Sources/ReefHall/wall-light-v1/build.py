"""A sealed curved-diffuser wall luminaire; existing point light remains unchanged."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
OUT=ROOT/'output/reefhall/wall-light-v1';STAGE=OUT/'stage';RES='models/maps/reefhall/wall-light-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/reefhall').rglob('*'))+list((ROOT/'Assets/materials/reefhall').rglob('*'))+[ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene',ROOT/'Tools/reefhall_map.py',ROOT/'Tools/reefhall_materials.py']
if not (OUT/'source-guard.json').exists():
 guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'wall-light-v1' not in p.parts};(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
m=K.Model();X,Y,Z=np.eye(3);O=np.array((760.,1100.,110.))
def P(x,y,z):return O+np.array((x,y,z))
def B(c,size,paint='rh_gunmetal',b=.12):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
# Cast backplate, rear gasket and recessed sealed body, within the old enclosure.
B((0,.18,8),(7,.36,16),b=.32)
B((0,.43,8),(6.55,.18,15.55),'rh_rubber',.22)
B((0,1.32,8),(6.65,1.62,15.35),b=.42)
# Two recessed side channels and longitudinal trim strips.
for side in (-1,1):
 B((side*2.95,2.13,8),(.40,.25,13.65),'rh_rubber',.10)
 B((side*3.10,2.33,8),(.22,.28,13.55),'rh_stainless',.09)
 for z in (3.,5.,7.,9.,11.,13.):B((side*3.31,1.15,z),(.10,.74,.15),'rh_steel',.04)
# The lens is an actual convex elliptical extrusion, rather than a glowing box face.
for k in range(40):
 a=-math.pi/2+math.pi*k/40;b=-math.pi/2+math.pi*(k+1)/40
 def q(t,z):return P(2.68*math.sin(t),1.9+1.1*math.cos(t),z)
 def normal(t):return K.normalise(np.array((math.sin(t)/2.68,math.cos(t)/1.1,0.)))
 na,nb=normal(a),normal(b)
 D._face(m,'rh_frosted_lit',[q(a,1.6),q(b,1.6),q(b,14.4),q(a,14.4)],na+nb,normals=[na,nb,nb,na],uv=[(k/40,0),((k+1)/40,0),((k+1)/40,1),(k/40,1)])
# Rounded end shoes, gasket seams, front fasteners and restrained diffuser guards.
for z in (.8,15.2):
 B((0,1.62,z),(6.9,2.76,1.6),b=.35)
 B((0,2.75,z+(.80 if z<8 else -.80)),(5.9,.16,.10),'rh_rubber',.035)
 for x in (-2.35,2.35):
  G.lathe_axis(m,P(x,2.995,z),Y,[(0.,0.),(.19,0.),(.23,.06),(.23,.13),(.17,.18),(0.,.18)],'rh_stainless',sides=24)
  B((x,3.184,z),(.22,.022,.045),'rh_black',.009)
for z in (4.,12.):
 # A shallow guard follows the convex lens, leaving the opal visible between it.
 pts=[P(2.70*math.sin(t),1.9+1.1*math.cos(t)+.055,z) for t in np.linspace(-math.pi/2,math.pi/2,25)]
 G.tube(m,pts,.075,'rh_gunmetal',sides=8,caps=True)
R.configure(m);count=K.write_model(MODEL,RES,'wall_light',m)
legacy=K.Model();frame,base,_=R.side_frame(R.FILTER,'s');R.sconce(legacy,frame,760-base,110.);R.configure(legacy);K.write_obj(OUT/'legacy-light.obj',legacy,'legacy_light')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-light.obj');wanted=collections.Counter(key for _,key in old)
public=ROOT/'Assets/models/maps/reefhall/reefhall_filter.vmdl';text=public.read_text();source=ROOT/'Assets/models/maps/reefhall/reefhall_filter.obj'
assert 'models/maps/reefhall/reefhall_filter.obj' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Installed wall light differs from helper'
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib filter_without_light.mtl',content)
(MODEL/'filter_without_light.obj').write_text(content);(MODEL/'filter_without_light.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'filter_without_light.vmdl').write_text(text.replace('models/maps/reefhall/reefhall_filter.obj',RES+'/filter_without_light.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/ReefHall/circulation-pump-v1/import.cs.txt').read_text().replace('circulation-pump-v1','wall-light-v1');(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),existing_materials_reused=True,point_lights_unchanged=True)))
