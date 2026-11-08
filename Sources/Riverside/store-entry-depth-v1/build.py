"""Finish the shop entrance with fixed-open reused glazed leaves and a physical frame."""
from pathlib import Path
import sys,json,re,hashlib,collections,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverside_map as R,riverside_parts as P,riverdale_parts as G
OUT=ROOT/'output/riverside/store-entry-depth-v1';STAGE=OUT/'stage/Assets';RES='models/props/riverside/store_entry_depth_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
docpath=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';doc=docpath.read_text();rel='models/maps/riverside/shop-sign-v1/store_without_shop_sign.obj';assert rel in doc;source=ROOT/'Assets'/rel;lines=source.read_text().splitlines(keepends=True)
old=K.Model();G.quad(old,'rs_dark',G.v(235,639.8,58),P.right_for((0,-1)),G.UP,76,79,off=.1);R.configure(old);K.write_obj(OUT/'expected.obj',old,'entry')
def records(lines):
 v=[];paint='';rows=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(round(float(x),3) for x in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':rows.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in s[1:])))))
 return rows
wanted=collections.Counter(k for i,k in records((OUT/'expected.obj').read_text().splitlines()));cut=[]
for i,k in records(lines):
 if wanted[k]:wanted[k]-=1;cut.append(i)
assert len(cut)==2 and not +wanted,'Actual saved entrance differs from baseline'
(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in set(cut)))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile(source.parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
m=K.Model()
def box(c,size,paint='rs_alu',b=.10):G.bevel_box(m,c,np.eye(3),size,paint,bevel=b)
for x in (200.,270.):box((x,640.,58.),(2.4,6.,76.),b=.14)
box((235,640.,94.8),(70.,6.,2.4),b=.14)
box((235,640.,20.25),(70.,8.,.5),b=.12)
for x in (201.2,268.8):
 for z in (27.4,57.,86.6):
  box((x,638.4,z),(1.4,1.,3.2),b=.12)
# Floor stops meet the inner face of each leaf at its fully open position.
for x in (203.,267.):
 G.lathe_axis(m,(x,607.,20.),G.UP,[(0,0),(.80,0),(.80,.35),(.60,.55),(.60,1.2),(0,1.2)],'rs_rubber',sides=24)
 G.lathe_axis(m,(x,607.,20.),G.UP,[(0,0),(.45,0),(.45,.14),(0,.14)],'rs_alu',sides=16)
R.configure(m);K.write_obj(DEST/'frame.obj',m,'frame');K.write_vmdl(DEST/'frame.vmdl',RES,'frame',m)
ids=K.SceneIds('863cc5f2-31bf-4923-a429-e738e4a51288');leaf='models/props/veridant/reception_doors_v1/leaf.vmdl';key='store/open-glazed-entry'
children=[K.game_object(ids,'Open Glazed Shop Door',f'{key}/{i}',(640,-e,20),rotation=K.yaw_rotation(-90),scale=K.vec((1,33.7/29.15,.74)),components=[K.component(ids,'Sandbox.ModelRenderer',f'{key}/{i}/renderer',Model=leaf,RenderType='On',Tint='1,1,1,1')]) for i,e in enumerate((201.2,268.8))]
node=K.game_object(ids,'Lucky Stop Open Glazed Entry',key,components=[K.component(ids,'Sandbox.ModelRenderer',key+'/frame',Model=RES+'/frame.vmdl',RenderType='On',Tint='1,1,1,1')],children=children);(OUT/'node.json').write_text(json.dumps(node,indent=2))
leafdoc=ROOT/'Assets'/leaf;protected=[docpath,ROOT/'Assets/scenes/maps/Riverside/riverside.scene',leafdoc,*[ROOT/'Assets'/p for p in re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc+'\n'+leafdoc.read_text())]]
materials=set(m.material_overrides.values())|set(re.findall(r'to\s*=\s*"([^\"]+\.vmat)"',leafdoc.read_text()))
for path in materials:
 p=ROOT/'Assets'/path;protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,active_base=rel,original_faces_removed=2,frame_triangles=m.triangle_count(),reused_leaf_model=leaf,reused_leaves=2,leaf_scale=[1,33.7/29.15,.74],leaf_yaw=-90,opening_width=70,clear_aisle_width=65.6,cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('cut','protected','files')}))
