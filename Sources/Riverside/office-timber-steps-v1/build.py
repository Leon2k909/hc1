from pathlib import Path
from collections import Counter
import sys,json,hashlib,re,shutil,math
import numpy as np
ROOT=Path('.').resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as M
OUT=ROOT/'output/riverside/office-timber-steps-v1';RES='models/props/riverside/office_timber_steps_v1';ASSET=ROOT/'Assets'/RES;REVIEW=ASSET/'review'
for p in (OUT,ASSET,REVIEW):p.mkdir(parents=True,exist_ok=True)
X,Y,Z=np.eye(3)
def make(lod):
 m=K.Model();slot=0
 def wood_uv(start,axis,across):
  nonlocal slot
  polys=m.polygons['wood'][start:];allp=np.array([p for pts,n in polys for p in pts]);lo=allp.min(axis=0);span=np.maximum(allp.max(axis=0)-lo,.01)
  u0=8+(slot%2)*1024;v0=8+(3+(slot%6)//2)*168;slot+=1
  for j,(pts,n) in enumerate(polys,start):
   # The end grain uses the remaining axis, preventing zero-area UVs on the cut ends.
   a=axis if np.ptp(np.array(pts)[:,axis])>.01 else next(i for i in range(4) if i!=axis and np.ptp(np.array(pts)[:,i])>.01)
   b=across if across!=a and np.ptp(np.array(pts)[:,across])>.01 else next(i for i in range(4) if i!=a and np.ptp(np.array(pts)[:,i])>.01)
   m.polygon_uvs[('wood',j)]=[((u0+(p[a]-lo[a])/span[a]*1008)/2048,1-(v0+(p[b]-lo[b])/span[b]*152)/2048) for p in pts]
 def timber(c,size,axis=0):
  start=len(m.polygons['wood']);G.bevel_box(m,np.array(c),(X,Y,Z),size,'wood',.14 if lod<2 else 0);wood_uv(start,axis,1 if axis==0 else 2)
 for step in range(4):
  height=7*(step+1)
  for board in range(2):timber((0,step*10+2.45+board*5.1,height-.75),(34,4.9,1.5))
  if lod==0:
   for x in (-14,0,14):
    for y in (step*10+1.5,step*10+8.6):
     p=np.array((x,y,height+.025));G.lathe_axis(m,p,-Z,[(0,0),(.22,0),(.22,.09),(0,.09)],'steel',sides=8 if lod==0 else 6)
     if lod==0:
      for size in ((.27,.04,.015),(.04,.27,.015)):G._box3(m,p+Z*.008,(X,Y,Z),size,'dark')
 for x in (-14,0,14):
  start=len(m.polygons['wood']);profile=[(-y,z) for y,z in [(0,0),(7,0),(40,20),(40,26.5),(30,26.5),(30,19.5),(20,19.5),(20,12.5),(10,12.5),(10,5.5),(0,5.5)]]
  G.extrude(m,(x-.75,0,0),(x+.75,0,0),profile,'wood',up=Z,smooth=0);wood_uv(start,1,2)
  if lod==0:
   for step in range(4):
    y=step*10+6;z=7*(step+1)-1.6
    for s in (-1,1):
     G.bevel_box(m,np.array((x+s*.88,y,z-1)),(X,Y,Z),(.14,4,2),'steel',.025)
     G.bevel_box(m,np.array((x+s*1.45,y,z-.08)),(X,Y,Z),(1.3,4,.14),'steel',.025)
     for dy in (-1.1,1.1):G.lathe_axis(m,np.array((x+s*.97,y+dy,z-1)),X*s,[(0,0),(.2,0),(.2,.09),(0,.09)],'dark',sides=6)
 timber((0,38,18.5),(30,3,3))
 for x in (-12,12):timber((x,38,8.5),(3.5,3.5,17),2)
 m.material_overrides={'wood':'materials/riverside/crate_v2/crate.vmat','steel':'materials/lowtide/lt_steel.vmat','dark':'materials/riverside/rs_dark.vmat'};m.tile_overrides={p:48 for p in m.polygons}
 return m
counts=[K.write_obj(ASSET/f'steps_lod{i}.obj',make(i),'steps') for i in range(3)]
K.write_vmdl(ASSET/'steps.vmdl',RES,'steps_lod0',make(0));t=(ASSET/'steps.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/steps_lod%d.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,RES,i) for i in range(3));groups=','.join('{_class="LODGroup" switch_threshold=%d meshes=["lod%d"]}'%(d,i) for i,d in enumerate((0,18,45)))
(ASSET/'steps.vmdl').write_text(t[:a]+'{_class="RenderMeshList" children=['+files+']},{_class="LODGroupList" children=['+groups+']},'+t[b:])
_,c,yaw,L,W=M.OFFICE;_,info=P.trailer(L,W,'rs_siding_white',seed=51,door_side=1,lit_share=.8,boarded_share=0,door_lit=True,roof_ac_model=True)
foot=np.array((info['door'][0]+80+40,W/2+40,0));old=K.Model();P.steps(old,foot,(-1,0),34,28,'rs_wood','wood');old=P.place(old,(c[0],c[1],M.HIGH),yaw);M.configure(old);K.write_obj(REVIEW/'old_steps.obj',old,'old_steps')
def records(data):
 pts=[];mat=None
 for line in data.decode().splitlines(keepends=True):
  q=line.split();key=None
  if q and q[0]=='v':pts.append(tuple(round(float(v),4) for v in q[1:]))
  if q and q[0]=='usemtl':mat=q[1]
  if q and q[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in q[1:])))
  yield line,key
expected=Counter(k for _,k in records((REVIEW/'old_steps.obj').read_bytes()) if k);source=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';kept=[];cut=[]
for line,key in records(source.read_bytes()):
 if key and expected[key]>0:cut.append(line);expected[key]-=1
 else:kept.append(line)
assert len(cut)==48 and not sum(expected.values()),(len(cut),sum(expected.values()))
(REVIEW/'pad_without_steps.obj').write_bytes(''.join(kept).encode());shutil.copy2(source.with_suffix('.mtl'),REVIEW/'riverside_pad.mtl');(REVIEW/'pad_without_steps.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/riverside/riverside_pad.obj',RES+'/review/pad_without_steps.obj'))
# Canonical steps climb engine+X; original office steps climb plan-E => engine+Y.
position=K.to_world(P.local_to_world(foot,(c[0],c[1],M.HIGH),yaw)).tolist()
protected=[source,source.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']+[ROOT/'Assets'/v for v in make(0).material_overrides.values()]
r=dict(position=position,yaw=90,triangles=counts,old_triangles=48,background=RES+'/review/pad_without_steps.vmdl',width=34,height=28,run=40,risers=4,rise=7,installed=False,new_materials=0,new_textures=0,protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected});(OUT/'review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
