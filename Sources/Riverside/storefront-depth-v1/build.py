"""Real shop glazing through the existing wall, revealing the approved stocked interior."""
from pathlib import Path
import sys,json,re,hashlib,collections,ast,math,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_map as R,riverside_parts as P,railhead_dress_detail as D
OUT=ROOT/'output/riverside/storefront-depth-v1';STAGE=OUT/'stage/Assets';RES='models/props/riverside/storefront_depth_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();docpath=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';doc=docpath.read_text();rel='models/maps/riverside/shop-sign-v1/store_without_shop_sign.obj';assert rel in doc;source=ROOT/'Assets'/rel;lines=source.read_text().splitlines(keepends=True)
def records(lines):
 v=[];uv=[];ns=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(map(float,s[1:])))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':ns.append(tuple(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':
   inds=[tuple(int(k)-1 for k in t.split('/')) for t in s[1:]];pts=tuple(v[a] for a,b,c in inds)
   result.append((i,(paint,tuple(sorted(tuple(round(x,3) for x in p) for p in pts))),pts,[uv[b] for a,b,c in inds],[ns[c] for a,b,c in inds]))
 return result
old=K.Model();right=P.right_for((0,-1));UP=np.array((0.,0.,1.));targets=((135.,90.,70.,200.),(320.,70.,270.,370.))
for cx,w,e0,e1 in targets:
 wc=G.v(cx,639.8,82);G.quad(old,'rs_dark',wc,right,UP,w+6,58,off=.2);P.lit(old,'window',wc,right,52,off=.4,w=w)
 if cx>270:
  P.lit(old,'open',wc+G.v(-w*.2,0,14),right,12,off=.7);P.lit(old,'beer',wc+G.v(w*.18,0,-14),right,10,off=.7)
R.configure(old);K.write_obj(OUT/'expected-cards.obj',old,'old_windows');wanted=collections.Counter(row[1] for row in records((OUT/'expected-cards.obj').read_text().splitlines()))
saved=records(lines);cut=[];walls={};neon=[]
for row in saved:
 i,key,pts,uv,ns=row
 if wanted[key]:
  wanted[key]-=1;cut.append(i)
  if key[0]=='rs_lit' and max(p[1] for p in pts)-min(p[1] for p in pts)<13:neon.append(row)
 else:
  for cx,w,e0,e1 in targets:
   for plane in (640.,646.):
    corners={(-e0,20.,plane),(-e1,20.,plane),(-e0,150.,plane),(-e1,150.,plane)}
    if key[0]=='rs_boards_dark' and set(pts).issubset(corners):walls.setdefault((cx,plane),[]).append(row);cut.append(i)
assert not +wanted and len(cut)==20 and len(neon)==4 and all(len(v)==2 for v in walls.values()) and len(walls)==4,dict(unmatched=sum((+wanted).values()),cut=len(cut),walls={str(k):len(v) for k,v in walls.items()},neon=len(neon))
cutset=set(cut);(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cutset))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile(source.parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
# Reuse the accepted slider's construction at physical shop-window dimensions.
# Extract its pure model function, without executing its historical export script.
frame_source=ROOT/'Sources/Riverside/sliding-window-v1/build.py';tree=ast.parse(frame_source.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='model');module=ast.Module(body=[fn],type_ignores=[])
def frame(w,h,lod):
 scope=dict(K=K,G=G,P=P,R=R,np=np,math=math,W=w,H=h,X=np.eye(3)[0],Y=np.eye(3)[1],Z=np.eye(3)[2]);exec(compile(module,str(frame_source),'exec'),scope);return scope['model'](lod)
def build(lod):
 m=K.Model()
 for cx,w,e0,e1 in targets:
  x0,x1=cx-w/2-1,cx+w/2+1;z0,z1=55.,109.
  # Both sides of the six-inch wall are cut, with actual jamb/head/sill returns.
  for plane in (640.,646.):
   fp=[];ft=[]
   for i,key,pts,uv,ns in walls[cx,plane]:
    for p,t in zip(pts,uv):fp.append((-p[0],p[1],1));ft.append(t)
   fit=np.linalg.lstsq(np.array(fp),np.array(ft),rcond=None)[0]
   rects=((e0,x0,20.,150.),(x1,e1,20.,150.),(x0,x1,20.,z0),(x0,x1,z1,150.))
   for a,b,c,d in rects:
    pts=[G.v(a,plane,c),G.v(b,plane,c),G.v(b,plane,d),G.v(a,plane,d)]
    D._face(m,'rs_boards_dark',pts,(0,-1 if plane==640 else 1,0),uv=[np.array((p[0],p[2],1))@fit for p in pts])
  D._face(m,'rs_wood',[G.v(x0,640,z0),G.v(x0,646,z0),G.v(x0,646,z1),G.v(x0,640,z1)],(1,0,0))
  D._face(m,'rs_wood',[G.v(x1,646,z0),G.v(x1,640,z0),G.v(x1,640,z1),G.v(x1,646,z1)],(-1,0,0))
  for z,hint in ((z0,UP),(z1,-UP)):D._face(m,'rs_wood',[G.v(x0,640,z),G.v(x1,640,z),G.v(x1,646,z),G.v(x0,646,z)],hint)
  m.extend(P.place(frame(w,52.,lod),(cx,642.,82.),0.))
  # Glazing sits behind each offset sash, so actual stocked shelves are visible.
  for side,plane in ((-1,642.05),(1,642.46)):
   a,b=(cx-w/2+.8,cx-.2) if side<0 else (cx+.2,cx+w/2-.8)
   for offset,hint in ((0.,(0,-1,0)),(.025,(0,1,0))):D._face(m,'glass',[G.v(a,plane+offset,56.8),G.v(b,plane+offset,56.8),G.v(b,plane+offset,107.2),G.v(a,plane+offset,107.2)],hint)
 # Retain the exact neon artwork behind the new glazing, with actual backing and hangers.
 signs={}
 beer_points=np.array([G.v(-a,c+7.2,b) for i,key,pts,uv,ns in neon if np.mean([p[1] for p in pts])<85 for a,b,c in pts]);beer_c=(beer_points.min(0)+beer_points.max(0))/2;beer_scale=min(1.,31.5/np.ptp(beer_points[:,0]))
 for i,key,pts,uv,ns in neon:
  p=[G.v(-a,c+7.2,b) for a,b,c in pts];normals=[G.v(-a,c,b) for a,b,c in ns]
  if np.mean([q[2] for q in p])<85:
   for q in p:q[0]=337.5+(q[0]-beer_c[0])*beer_scale;q[2]=beer_c[2]+(q[2]-beer_c[2])*beer_scale
  m.polygon('rs_lit',p,np.mean(normals,axis=0),uv=uv,normals=normals)
  label='open' if np.mean([q[2] for q in p])>85 else 'beer';signs.setdefault(label,[]).extend(p)
 for pts in signs.values():
  p=np.array(pts);lo=p.min(0);hi=p.max(0);c=(lo+hi)/2;c[1]=646.65
  G.bevel_box(m,c,np.eye(3),(hi[0]-lo[0]+.5,.5,hi[2]-lo[2]+.5),'rs_dark',bevel=.15)
  for x in (lo[0]+1.,hi[0]-1.):G.tube(m,[G.v(x,646.65,hi[2]+.2),G.v(x,646.65,108.5)],.055,'rs_rubber',sides=8)
 m.material_overrides['glass']='materials/railhead/rw_glass.vmat';R.configure(m);return m
models=[build(lod) for lod in range(3)];counts=[]
for lod,model in enumerate(models):counts.append(K.write_obj(DEST/f'windows_lod{lod}.obj',model,f'windows_lod{lod}'))
K.write_vmdl(DEST/'windows.vmdl',RES,'windows_lod0',models[0]);vdoc=(DEST/'windows.vmdl').read_text();a=vdoc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=vdoc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/windows_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3));groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,25,70)))
(DEST/'windows.vmdl').write_text(vdoc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+vdoc[b:])
protected=[docpath,ROOT/'Assets/scenes/maps/Riverside/riverside.scene',frame_source,*[ROOT/'Assets'/p for p in re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc)]]
for path in set(models[0].material_overrides.values()):
 p=ROOT/'Assets'/path;protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
m=dict(review_only=True,active_base=rel,cut=cut,original_faces_removed=20,wall_faces_removed=8,flat_window_neon_faces_removed=12,triangles=counts,reused_approved_slider_construction=True,actual_stocked_interior_preserved=True,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k not in ('cut','protected','files')}))
