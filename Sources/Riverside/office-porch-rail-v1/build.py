from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,re,math
import numpy as np
ROOT=Path('.').resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as M
SRC=ROOT/'Sources/Riverside/office-porch-rail-v1';OUT=ROOT/'output/riverside/office-porch-rail-v1';RES='models/props/riverside/office_porch_rail_v1';ASSET=ROOT/'Assets'/RES;REVIEW=ASSET/'review'
for p in (OUT,ASSET,REVIEW):p.mkdir(parents=True,exist_ok=True)
name,c,yaw,L,W=M.OFFICE
part,info=P.trailer(L,W,'rs_siding_white',seed=51,door_side=1,lit_share=.8,boarded_share=0,door_lit=True,roof_ac_model=True)
x0,x1=info['door'][0]-80,info['door'][0]+80;y=140;z=P.FLOOR-2
old=K.Model();posts=list(np.linspace(x0+3,x1-3,max(2,int((x1-x0)/96)+1)))
for x in posts:M.box(old,x-1.5,x+1.5,y-1.5,y+1.5,z,z+36,'rs_wood')
M.box(old,x0,x1,y-1.5,y+1.5,z+33,z+36,'rs_wood')
for x in np.arange(x0+6,x1-3,7):M.box(old,x-.8,x+.8,y-.6,y+.6,z,z+33,'rs_wood')
old=P.place(old,(c[0],c[1],M.HIGH),yaw);M.configure(old);K.write_obj(REVIEW/'old_rail.obj',old,'old_rail')
def faces(data):
 pts=[];mat=None
 for line in data.decode().splitlines(keepends=True):
  q=line.split();key=None
  if q and q[0]=='v':pts.append(tuple(round(float(x),4) for x in q[1:]))
  if q and q[0]=='usemtl':mat=q[1]
  if q and q[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in q[1:])))
  yield line,key
source=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';expected=Counter(k for _,k in faces((REVIEW/'old_rail.obj').read_bytes()) if k);total=sum(expected.values());kept=[];cut=[]
for line,key in faces(source.read_bytes()):
 if key and expected[key]>0:cut.append(line);expected[key]-=1
 else:kept.append(line)
assert not sum(expected.values()) and len(cut)==total,(sum(expected.values()),len(cut),total)
(REVIEW/'pad_without_rail.obj').write_bytes(''.join(kept).encode());shutil.copy2(source.with_suffix('.mtl'),REVIEW/'riverside_pad.mtl')
modeltext=source.with_suffix('.vmdl').read_text();(REVIEW/'pad_without_rail.vmdl').write_text(modeltext.replace('models/maps/riverside/riverside_pad.obj',RES+'/review/pad_without_rail.obj'))
X,Y,Z=np.eye(3)
def make(lod):
 m=K.Model();b=.12 if lod<2 else 0
 def beam(c,size,paint='wood',bevel=b):G.bevel_box(m,np.array(c,float),(X,Y,Z),size,paint,bevel)
 # Chamfered posts with sloping caps and visible structural joints.
 for x in (-77,77):
  beam((x,0,17.2),(3.2,3.2,34.4));beam((x,0,35.2),(3.8,3.8,1.6),bevel=.35 if lod<2 else 0)
 # Shaped cap and bottom stretcher. Smooth eased corners, not a square plank.
 beam((0,0,34.5),(160,3.5,3),'wood',.55 if lod<2 else 0)
 beam((0,-.10,4),(154,1.8,3),'wood',.18 if lod<2 else 0)
 for k,x in enumerate(np.arange(-74,77,7)):
  lean=(.32*math.sin(k*2.6) if lod<2 else 0)
  # Balusters retain the barrier; slight imperfect lean and split ends suit an abandoned porch.
  if k in (7,13):
   # Broken balusters remain in the same barrier envelope; two jagged timber stubs.
   profiles=[[(x-.8,4),(x+.8,4),(x+.8,13.8),(x+.32,12.0),(x+.05,15.0),(x-.3,12.8),(x-.8,14.4)],[(x-.8,28),(x-.28,29.6),(x+.08,27.1),(x+.45,29),(x+.8,28.4),(x+.8,33),(x-.8,33)]]
   for profile in profiles:
    near=[np.array((xx,-.6,zz)) for xx,zz in profile];far=[np.array((xx,.6,zz)) for xx,zz in profile]
    G._cap(m,'wood',near,profile,-Y);G._cap(m,'wood',far,profile,Y)
    for j in range(len(profile)):
     j2=(j+1)%len(profile);d=near[j2]-near[j];G.card(m,'wood',[near[j],near[j2],far[j2],far[j]],np.cross(d,Y))
  else:
   centre=np.array((x+lean/2,0,18.5));axis=G.unit((lean,0,29));side=G.unit(np.cross(Y,axis));G.bevel_box(m,centre,(side,Y,axis),(1.6,1.2,29),'wood',.12 if lod<2 else 0)
  if lod==0:
   for zz in (5,31):
    G.lathe_axis(m,np.array((x,.64,zz)),Y,[(0,0),(.12,0),(.12,.055),(0,.055)],'steel',sides=6)
 # Bolt washers at the two post joints.
 if lod<2:
  for x in (-77,77):
   for zz in (5,31):
    G.lathe_axis(m,np.array((x,1.62,zz)),Y,[(0,0),(.30,0),(.30,.07),(0,.07)],'dark',sides=10)
    G.lathe_axis(m,np.array((x,1.70,zz)),Y,[(0,0),(.19,0),(.19,.12),(0,.12)],'steel',sides=6)
 m.material_overrides={'wood':'materials/riverdale/rv_pallet_wood.vmat','steel':'materials/riverside/rs_rust.vmat','dark':'materials/riverside/rs_dark.vmat'};m.tile_overrides={'wood':48,'steel':24,'dark':24}
 for i,(pts,n) in enumerate(m.polygons['wood']):
  a=np.array(pts);n=np.array(n)
  horizontal=np.ptp(a[:,0])>10
  if horizontal:
   coords=[((v[1] if abs(n[2])>abs(n[1]) else v[2])/12+.27,v[0]/64+.13) for v in a]
  else:
   dominant=int(np.argmax(abs(n)))
   coords=[(v[0]/12+.27,v[2]/48+.13) for v in a] if dominant==1 else [(v[1]/12+.27,v[2]/48+.13) for v in a] if dominant==0 else [(v[0]/12+.27,v[1]/12+.13) for v in a]
  m.polygon_uvs[('wood',i)]=coords
 return m
counts=[K.write_obj(ASSET/f'rail_lod{i}.obj',make(i),'rail') for i in range(3)]
K.write_vmdl(ASSET/'rail.vmdl',RES,'rail_lod0',make(0));t=(ASSET/'rail.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/rail_lod%d.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,RES,i) for i in range(3))
groups=','.join('{_class="LODGroup" switch_threshold=%d meshes=["lod%d"]}'%(d,i) for i,d in enumerate((0,18,45)))
(ASSET/'rail.vmdl').write_text(t[:a]+'{_class="RenderMeshList" children=['+files+']},{_class="LODGroupList" children=['+groups+']},'+t[b:])
position=K.to_world((c[0]+info['door'][0],c[1]+140,M.HIGH+z)).tolist();protected=[source,source.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']+[ROOT/'Assets'/v for v in make(0).material_overrides.values()]
report=dict(position=position,yaw=0,triangles=counts,old_triangles=total,background=RES+'/review/pad_without_rail.vmdl',protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},installed=False,new_materials=0,new_textures=0)
(OUT/'review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
