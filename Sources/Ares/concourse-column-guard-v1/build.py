"""One close-route column's replaceable impact jacket; structural column stays unchanged."""
from pathlib import Path
from collections import Counter
import sys,json,re,hashlib,shutil,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,ares_map as A,boxyard_map as B
from belltower_furniture import bevel_box
OUT=ROOT/'output/ares/concourse-column-guard-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/concourse_column_guard_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();origin=np.array((-650.,-1076.,0.));UP=np.array((0.,0.,1.));axes=np.eye(3)
old=K.Model();old.box(origin+(-14.5,-14.5,0),origin+(14.5,14.5,30),'ar_hazard');old.box(origin+(-14.4,-14.4,30),origin+(14.4,14.4,32),'ar_brass');A.configure(old);K.write_obj(OUT/'expected.obj',old,'expected')
def sigs(lines):
 v=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(round(float(x),3) for x in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=Counter(k for i,k in sigs((OUT/'expected.obj').read_text().splitlines()));assert sum(wanted.values())==24
docpath=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for rel in imports:
 lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);remaining=wanted.copy();cut=[]
 for i,k in sigs(lines):
  if remaining[k]:cut.append(i);remaining[k]-=1
 if cut:print('matched',rel,len(cut),'of24')
 if len(cut)==24 and not +remaining:matches.append((rel,lines,cut))
assert len(matches)==1,'Actual column jacket differs from baseline'
rel,lines,cut=matches[0];(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
m=K.Model()
def block(center,size,paint,bevel=.07,local_axes=axes):bevel_box(m,origin+np.array(center),local_axes,np.array(size),paint,bevel)
def lathe(center,axis,profile,paint,sides=12):B.lathe(m,origin+np.array(center),axis,profile,paint,sides=sides,cap=paint)
# Closed base ring: the original column continues through its central opening.
for normal in (np.array((1.,0,0)),np.array((-1.,0,0)),np.array((0,1.,0)),np.array((0,-1.,0))):
 along=np.cross(normal,UP);panel_axes=(along,normal,UP)
 block(normal*14.25+UP*.60,(28.8,.5,1.2),'ar_gunmetal',.08,panel_axes)
 # Separate gasket and removable hazard panel, with clear seams at the corners.
 block(normal*14.08+UP*16.5,(25.7,.07,25.4),'ar_black',.02,panel_axes)
 block(normal*14.20+UP*16.5,(25.4,.18,25.0),'ar_hazard',.065,panel_axes)
 for t in (-10.6,10.6):
  for z in (6.,27.):
   p=normal*14.29+along*t+UP*z
   lathe(p,normal,[(.30,0),(.30,.04),(.21,.055)],'ar_steel',12)
   lathe(p+normal*.055,normal,[(.22,0),(.22,.10),(.19,.13)],'ar_steel',6)
 # A folded upper return replaces the flat brass box; no top face is coplanar.
 block(normal*14.24+UP*31.0,(28.5,.30,1.8),'ar_brass',.10,panel_axes)
 block(normal*14.17+UP*29.75,(25.5,.20,.35),'ar_gunmetal',.04,panel_axes)
# Four L-section corner guards expose the panel joints rather than hiding a solid cube.
for sx in (-1,1):
 for sy in (-1,1):
  block((sx*14.25,sy*13.4,16.0),(.44,2.2,28.6),'ar_gunmetal',.08)
  block((sx*13.4,sy*14.25,16.0),(2.2,.44,28.6),'ar_gunmetal',.08)
  # Small anchors secure the protective guard, not the structural column itself.
  p=(sx*14.23,sy*14.23,1.21)
  lathe(p,UP,[(.24,0),(.24,.07),(.16,.09)],'ar_steel',12)
  lathe(np.array(p)+UP*.09,UP,[(.22,0),(.22,.28),(.19,.33)],'ar_steel',6)
  lathe(np.array(p)+UP*.15,UP,[(.125,0),(.125,.57),(.105,.62)],'ar_steel',12)
A.configure(m);bindings=dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}',doc));m.material_overrides.update({p:bindings.get(p,m.material_overrides[p]) for p in m.polygons});m.material_overrides['ar_gunmetal']='materials/ares/interior-v1/alloy.vmat'
assert not m.boxes and not m.hulls
K.write_obj(DEST/'guard.obj',m,'guard');K.write_vmdl(DEST/'guard.vmdl',RES,'guard',m)
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports]]
for p in set(m.material_overrides.values()):
 path=ROOT/'Assets'/p;protected.append(path)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',path.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,original_faces=24,triangles=m.triangle_count(),column_body_unchanged=True,original_collision_unchanged=True,outer_envelope_inches=[29,29,32],active_base=rel,cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print('CANDIDATE',24,m.triangle_count())
