"""One platform help point: retain existing graphics and map collision."""
from pathlib import Path
import sys,json,re,hashlib,collections,shutil,math
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,railhead_map as R,railhead_props as P,railhead_furniture as FU,riverdale_parts as G
OUT=ROOT/'output/railhead/help-point-v1';STAGE=OUT/'stage/Assets';RES='models/props/railhead/help_point_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
F=P.frame_for(-1154.,378.,0.,'+e');m=K.Model();BLUE='rw_train_blue';METAL='rw_stainless';DARK='rw_steel_dark'
def box(c,size,paint,b=.08):G.bevel_box(m,F.p(*c),(F.x,F.y,F.z),size,paint,bevel=b)
def turn(x,y,z,profile,paint=METAL,sides=32,axis=None):G.lathe_axis(m,F.p(x,y,z),F.y if axis is None else axis,profile,paint,sides=sides)
# Formed base and main blue cabinet, with a distinct lower service door.
box((0,0,.3),(14,12,.6),METAL,.15)
box((0,0,24.3),(9.4,7.8,47.4),BLUE,.5)
box((0,3.91,14.3),(8.25,.14,19.6),'rw_black',.12)
box((0,4.02,14.3),(7.9,.16,19.25),BLUE,.14)
for z in (7.7,20.9):box((-3.6,4.17,z),(.38,.32,1.2),METAL,.06)
turn(2.8,4.13,15,[(0,0),(.35,0),(.35,.1),(0,.1)],sides=24)
box((2.8,4.25,15),(.07,.035,.36),DARK,.01)
# Recessed intercom module. The grille slots are actual openings, with a black back and sloped walls.
box((0,3.94,36.4),(8.1,.18,21.2),'rw_black',.16)
holes=[(-2.85,2.85,33.4+i*.82,33.7+i*.82) for i in range(7)]
P._holed(m,F,'rw_kiosk_clad',-3.85,3.85,26.1,46.7,4.17,holes)
for x0,x1,z0,z1 in holes:
 P._bevel(m,F,DARK,x0,x1,z0,z1,4.17,3.98,.07)
P._frect(m,F,'rw_black',-3.1,3.1,3.96,33.1,39.1)
# Existing SOS artwork, not a new safety sign or gameplay function.
P._frect(m,F,'rw_prop_signs',-2.6,2.6,4.19,40.8,46.,uv=FU._sign_uv('sos'))
for x,paint in ((-1.8,BLUE),(1.8,'rw_red_paint')):
 turn(x,4.18,29.1,[(.82,0),(1.13,0),(1.13,.16),(1.02,.26),(.82,.26),(.82,0)],sides=40)
 turn(x,4.25,29.1,[(0,0),(.80,0),(.80,.20),(.72,.27),(0,.27)],paint,sides=40)
# Captive panel screws, with inset cross slots.
for x in (-3.42,3.42):
 for z in (26.7,46.1):
  turn(x,4.18,z,[(0,0),(.18,0),(.18,.06),(.13,.10),(0,.10)],sides=20)
  for w,h in ((.20,.035),(.035,.20)):box((x,4.29,z),(w,.018,h),DARK,.005)
# Opal information head in a chamfered extrusion, original head graphic both sides.
box((0,0,55.0),(10.6,9.,14.),'rw_kiosk_fascia',.55)
for z in (48.,62.05):box((0,0,z),(11.2,9.6,.85),'rw_steel_grey',.18)
for y,face in ((4.52,'front'),(-4.52,'back')):
 box((0,y,55),(8.2,.12,8.2),'rw_black',.10)
 F.quad(m,'rw_prop_signs',0,y+(.08 if y>0 else -.08),55,8,8,face,uv=FU._sign_uv('info_head'))
# Compact lens housing replaces the flat black top disc.
turn(0,0,62.5,[(0,0),(2.2,0),(2.2,.35),(1.8,.45),(0,.45)],DARK,axis=F.z)
turn(0,0,62.95,[(0,0),(1.65,0),(1.53,.5),(1.16,1.0),(.60,1.35),(0,1.45)],'rw_black',axis=F.z)
for x in (-5.6,5.6):
 for y in (-4.4,4.4):
  turn(x,y,.61,[(0,0),(.34,0),(.34,.13),(0,.13)],sides=6,axis=F.z)
R.configure(m);m.tile_overrides[METAL]=12.;K.write_obj(DEST/'help_point.obj',m,'help_point');K.write_vmdl(DEST/'help_point.vmdl',RES,'help_point',m)
# Find the exact original assembly in the current public imports.
old=K.Model();FU.sos_pillar(old,F);R.configure(old);K.write_obj(OUT/'expected.obj',old,'expected')
def records(lines):
 vertices=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':vertices.append(tuple(round(float(v),3) for v in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=collections.Counter(k for i,k in records((OUT/'expected.obj').read_text().splitlines()));docpath=ROOT/'Assets/models/maps/railhead/railhead_dress_west.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc);matches=[]
for rel in imports:
 lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);remaining=wanted.copy();cut=[]
 for i,k in records(lines):
  if remaining[k]:remaining[k]-=1;cut.append(i)
 if len(cut)==sum(wanted.values()) and not +remaining:matches.append((rel,lines,cut))
assert len(matches)==1,'Saved help point differs from generator'
rel,lines,cut=matches[0];cutset=set(cut);(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cutset))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
protected=[docpath,ROOT/'Assets/scenes/maps/Railhead/railhead.scene',*[ROOT/'Assets'/p for p in imports]]
for path in set(m.material_overrides.values()):
 p=ROOT/'Assets'/path;protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,active_base=rel,original_faces=len(cut),triangles=m.triangle_count(),cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('cut','protected','files')}))
