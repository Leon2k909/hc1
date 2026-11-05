"""Improve the old rank sign after checking existing upgraded/reusable assets."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
OUT=ROOT/'output/railhead/taxi-post-v1';STAGE=OUT/'stage';RES='models/maps/railhead/taxi-post-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_dress_detail.py']
if not (OUT/'source-guard.json').exists():
 guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'taxi-post-v1' not in p.parts};(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
audit=dict(target='East taxi-rank head sign at (1488,1180,0)',existing_improvement_found=False,checked=['Assets model filenames for taxi/sign/pole variants','Sources upgrade README/status/installed records','Tools and notes for taxi_post/taxi_rank','Historical output variants named taxi','Riverside speed_sign_v2 reusable model'],findings=['The live rank sign still matches railhead_dress_detail.taxi_post: ten-sided pole, solid rectangular slab and simple collars','rw_taxi_sign and railhead_furniture.taxi_sign belong to car roof lamps, not rank signs','The existing Riverside sign is a single US speed-limit sheet on a perforated U-channel, not this double-sided taxi panel','Newer planter, chair, speaker and inspection-cover assets were excluded from selection'],reuse=['Unchanged existing rw_signs taxi artwork, on both faces','Existing stainless/white/dark finishes','Shared lathe, bevel and face construction helpers'])
(OUT/'existing-upgrade-audit.json').write_text(json.dumps(audit,indent=2))
m=K.Model();frame=D.Frame(1488.,1180.,0.,'+n');X,Y,Z=frame.x,frame.y,frame.z
def P(x,y,z):return frame.p(x,y,z)
def B(c,size,paint='rw_stainless',b=.06,axes=None):G.bevel_box(m,P(*c),axes or (X,Y,Z),size,paint,bevel=b)
def turn(profile,paint='rw_stainless',c=(0,0,0),axis=Z,sides=48):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
# Smooth post and a formed weather cap, retaining the old 102-inch top height.
turn([(0,.35),(1.2,.35),(1.2,101.55),(0,101.55)])
turn([(0,101.5),(1.24,101.5),(1.24,101.7),(1.14,101.9),(.80,102),(0,102)])
# Low anchor flange, seated on the existing pavement rather than a floating pole end.
turn([(0,0),(2.85,0),(3.15,.12),(3.15,.30),(2.95,.46),(1.25,.46),(1.2,.60),(0,.60)])
for k in range(4):
 a=math.pi/4+k*math.pi/2;x,y=2.30*math.cos(a),2.30*math.sin(a)
 turn([(0,0),(.38,0),(.38,.10),(0,.10)],'rw_steel_dark',c=(x,y,.44),sides=24)
 turn([(0,0),(.29,0),(.29,.28),(0,.28)],c=(x,y,.53),sides=6)
# Split saddle collars above and below the panel, with real lugs and through bolts.
for z in (85.6,99.0):
 turn([(1.21,z-.45),(1.47,z-.45),(1.53,z-.32),(1.53,z+.32),(1.47,z+.45),(1.21,z+.45),(1.21,z-.45)],'rw_steel_dark')
 for y in (-.34,.34):B((1.48,y,z),(.52,.22,.85),'rw_stainless',.07)
 G.lathe_axis(m,P(1.48,-.56,z),Y,[(0.,0.),(.17,0.),(.17,.30),(0.,.30)],'rw_stainless',sides=6)
 G.lathe_axis(m,P(1.48,-.26,z),Y,[(0.,0.),(.09,0.),(.09,.82),(0.,.82)],'rw_stainless',sides=16)
# A rounded two-sided cassette encloses the pole; the old thin slab intersected it.
def outline(hx,hz,r):
 points=[]
 for cx,cz,a0 in ((hx-r,hz-r,0.),(-hx+r,hz-r,math.pi/2),(-hx+r,-hz+r,math.pi),(hx-r,-hz+r,3*math.pi/2)):
  for k in range(9):
   a=a0+k*math.pi/16;points.append((cx+r*math.cos(a),92.3+cz+r*math.sin(a)))
 return points
outer=outline(12.2,6.3,.70);inner=outline(12.,6.1,.50)
for k in range(len(outer)):
 j=(k+1)%len(outer);a,b=outer[k],outer[j]
 hint=X*(a[0]+b[0])+Z*(a[1]+b[1]-184.6)
 D._face(m,'rw_stainless',[P(a[0],-1.45,a[1]),P(b[0],-1.45,b[1]),P(b[0],1.45,b[1]),P(a[0],1.45,a[1])],hint)
for side in (-1,1):
 for k in range(len(outer)):
  j=(k+1)%len(outer);a,b=outer[k],outer[j];c,d=inner[j],inner[k]
  D._face(m,'rw_stainless',[P(a[0],side*1.45,a[1]),P(b[0],side*1.45,b[1]),P(c[0],side*1.57,c[1]),P(d[0],side*1.57,d[1])],Y*side)
 D._face(m,'rw_white_paint',[P(x,side*1.57,z) for x,z in inner],Y*side)
 # All artwork is the original atlas entry, including its blue field, icon and text.
 face=D.Frame(1488.,1180.,0.,'+n' if side>0 else '-n')
 face.quad(m,'rw_signs',-11.8,11.8,1.585,86.4,98.2,uv=D._atlas_uv('rw_signs','taxi'))
 for x in (-11.88,11.88):
  for z in (86.35,98.25):
   G.lathe_axis(m,P(x,side*1.58,z),Y*side,[(0.,0.),(.10,0.),(.13,.04),(.08,.08),(0.,.08)],'rw_stainless',sides=20)
# Small underside straps tie the cassette to its lower saddle without crossing the art.
for y in (-1.05,1.05):B((0,y,85.65),(1.45,.35,.7),'rw_steel_dark',.1)
R.configure(m);m.tile_overrides['rw_stainless']=24.;count=K.write_model(MODEL,RES,'taxi_post',m)
if '--candidate-only' in sys.argv:
 manifest=json.loads((OUT/'manifest.json').read_text());assert sha(ROOT/manifest['source'])==manifest['source_sha256'],'Live base changed; rebuild preview splice'
 manifest['files']={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()};manifest['triangles']=count
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(dict(new_triangles=count,candidate_only=True)));sys.exit(0)
legacy=K.Model();D.taxi_post(legacy,1488.,1180.,'+n',0.);R.configure(legacy);K.write_obj(OUT/'legacy-taxi.obj',legacy,'legacy_taxi')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-taxi.obj');wanted=collections.Counter(key for _,key in old)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl';text=public.read_text();source=ROOT/'Assets/models/maps/railhead/cable-drum-v1/east_without_drum.obj'
assert 'models/maps/railhead/cable-drum-v1/east_without_drum.obj' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Installed taxi post differs from helper'
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib east_without_taxi.mtl',content)
(MODEL/'east_without_taxi.obj').write_text(content);(MODEL/'east_without_taxi.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'east_without_taxi.vmdl').write_text(text.replace('models/maps/railhead/cable-drum-v1/east_without_drum.obj',RES+'/east_without_taxi.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),existing_upgrade_checked=True,review_only=True),indent=2))
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Railhead/brick-pallet-v1/import.cs.txt').read_text().replace('brick-pallet-v1','taxi-post-v1'))
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),artwork_preserved=True,existing_upgrades_audited=True)))
