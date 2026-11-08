"""One player-height landing railing, preserving all current map geometry outside it."""
from pathlib import Path
from collections import Counter
import sys,json,re,hashlib,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,ares_map as A,boxyard_map as B,riverdale_parts as R
from belltower_furniture import bevel_box
OUT=ROOT/'output/ares/stair-landing-rail-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/stair_landing_rail_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=K.Model();A.railing(base,(-760,-158),(-760,-80),208);A.configure(base)
K.write_obj(OUT/'expected.obj',base,'expected')
def signatures(lines):
 v=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(round(float(x),3) for x in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=Counter(k for i,k in signatures((OUT/'expected.obj').read_text().splitlines()));assert sum(wanted.values())==base.triangle_count()
docpath=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for rel in imports:
 raw=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);remaining=wanted.copy();cut=[]
 for i,key in signatures(raw):
  if remaining[key]:remaining[key]-=1;cut.append(i)
 if cut:print('matched',rel,len(cut),'of',sum(wanted.values()))
 if len(cut)==sum(wanted.values()) and not +remaining:matches.append((rel,raw,cut))
assert len(matches)==1,'Current railing differs from generated baseline'
rel,raw,cut=matches[0];(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(raw) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(raw),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
m=K.Model();A.configure(m);up=np.array((0.,0.,1.));along=np.array((0.,1.,0.));side=np.array((-1.,0.,0.));axis=np.eye(3)
def tube(a,b,r,paint,sides=20):
 a=np.array(a,float);b=np.array(b,float);B.lathe(m,a,b-a,[(r,0),(r,float(np.linalg.norm(b-a)))],paint,sides=sides,cap=paint)
def bolt(p,d,r=.28):
 d=np.array(d,float);B.lathe(m,p,d,[(r*1.35,0),(r*1.35,.10),(r,.11),(r,.40)],'ar_steel',sides=6,cap='ar_steel')
# Rounded, closed tubes retain the exact original rail centrelines and heights.
tube((-760,-158,249),(-760,-80,249),1.2,'ar_gunmetal',24)
tube((-760,-158,230),(-760,-80,230),.7,'ar_brass',20)
for n in (-158.,-80.):
 foot=np.array((-760.,n,208.))
 tube(foot+up*(-13),foot+up*40.6,.95,'ar_gunmetal',20)
 # Reuse the approved closed cast tee design, avoiding the old open sleeve issue.
 R._rail_fitting(m,foot,41.,'ar_gunmetal',along)
 # Side mounting reaches the existing landing's vertical stringer face.
 bevel_box(m,(-759.6,n,201.5),axis,(.55,6.,12.),'ar_steel',.10)
 for dn in (-1.9,1.9):
  for z in (197.,206.):bolt((-759.28,n+dn,z),(1,0,0),.30)
 # Welded post saddle and a small triangular knee beneath the handrail.
 B.lathe(m,foot+up*(-11),up,[(1.04,0),(1.04,9.4)],'ar_steel',sides=20,cap='ar_steel')
 B.lathe(m,foot+up*22-along*1.15,along,[(.88,0),(.88,2.3)],'ar_gunmetal',sides=16,cap='ar_gunmetal')
 bolt(foot+np.array((1.10,0,22)),(1,0,0),.22)
 # Physical end plugs and closed connection collars at adjoining rails.
 for h,r in ((41,1.2),(22,.7)):
  outward=-along if n==-158 else along
  B.lathe(m,foot+up*h+outward*.03,outward,[(r*.94,0),(r*.94,.18),(r*.78,.30)],'ar_black',sides=20,cap='ar_black')
# A folded toe board with a returned upper lip, mounted to the post feet.
bevel_box(m,(-760,-119,211),axis,(.6,78,6),'ar_in_frame',.12)
m.box((-760.3,-158,213.7),(-758.8,-80,214.1),'ar_gunmetal')
for n in (-154.,-84.):bolt((-759.65,n,210.7),(1,0,0),.22)
# Preserve the two original marker blocks and surround them with small metal bezels.
p=np.array((-760.,-80.,208.))
for sgn in (-1,1):
 center=p+side*sgn*1.4+up*34
 m.oriented_box(center,(along,side,up),(1.2,.8,2.4),'ar_led_warm')
 for dn in (-.82,.82):m.oriented_box(center+along*dn,(along,side,up),(.25,1.0,3.0),'ar_gunmetal')
 for dz in (-1.43,1.43):m.oriented_box(center+up*dz,(along,side,up),(1.9,1.0,.25),'ar_gunmetal')
A.configure(m)
bindings=dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}',doc));m.material_overrides.update({p:bindings.get(p,m.material_overrides[p]) for p in m.polygons})
m.material_overrides['ar_gunmetal']='materials/ares/interior-v1/alloy.vmat'
assert not m.boxes and not m.hulls
K.write_obj(DEST/'rail.obj',m,'rail');K.write_vmdl(DEST/'rail.vmdl',RES,'rail',m)
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports],ROOT/'Tools/riverdale_parts.py']
manifest=dict(preview_only=True,reused_approved_closed_tee_fittings=True,original_faces=len(cut),triangles=m.triangle_count(),active_base=rel,cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print('CANDIDATE',len(cut),m.triangle_count())
