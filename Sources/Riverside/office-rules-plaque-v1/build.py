from pathlib import Path
from collections import Counter
import sys,json,hashlib,shutil,re,math
import numpy as np
ROOT=Path('.').resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as M,riverside_materials as RM
OUT=ROOT/'output/riverside/office-rules-plaque-v1';RES='models/props/riverside/office_rules_plaque_v1';ASSET=ROOT/'Assets'/RES;REVIEW=ASSET/'review'
for p in (OUT,ASSET,REVIEW):p.mkdir(parents=True,exist_ok=True)
_,c,yaw,L,W=M.OFFICE;part,info=P.trailer(L,W,'rs_siding_white',seed=51,door_side=1,lit_share=.8,boarded_share=0,door_lit=True,roof_ac_model=True)
centre=P.v(info['door'][0]+70,W/2,P.FLOOR+50);right=P.right_for((0,1));old=K.Model();width=P.sign(old,'office_rules',centre,right,30,off=.6);old=P.place(old,(c[0],c[1],M.HIGH),yaw);M.configure(old);K.write_obj(REVIEW/'old_sign.obj',old,'old_sign')
def records(data):
 pts=[];mat=None
 for line in data.decode().splitlines(keepends=True):
  q=line.split();key=None
  if q and q[0]=='v':pts.append(tuple(round(float(v),4) for v in q[1:]))
  if q and q[0]=='usemtl':mat=q[1]
  if q and q[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in q[1:])))
  yield line,key
expected=Counter(k for _,k in records((REVIEW/'old_sign.obj').read_bytes()) if k);source=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';kept=[];cut=[]
for line,key in records(source.read_bytes()):
 if key and expected[key]>0:cut.append(line);expected[key]-=1
 else:kept.append(line)
assert len(cut)==2 and not sum(expected.values())
(REVIEW/'pad_without_rules.obj').write_bytes(''.join(kept).encode());shutil.copy2(source.with_suffix('.mtl'),REVIEW/'riverside_pad.mtl');(REVIEW/'pad_without_rules.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/riverside/riverside_pad.obj',RES+'/review/pad_without_rules.obj'))
def p(x,y,z):return np.array((-y,x,z),float)
X,Y,Z=[p(*v) for v in [(1,0,0),(0,1,0),(0,0,1)]]
def make(lod):
 m=K.Model();radius=.65;half=width/2
 # Rounded corners and actual folded sheet edges instead of a decorative rim.
 zs=np.unique(np.r_[np.linspace(-15+radius,15-radius,(19,11,7)[lod]),[-15,-14.9,-14.65,14.65,14.9,15]])
 us=np.linspace(-1,1,(17,9,5)[lod])
 def extent(z):return half-radius+math.sqrt(max(0,radius**2-max(0,abs(z)-(15-radius))**2))
 def depth(y,z):
  curl=1.35*max(0,(y-(half-3.4))/3.4)**2*max(0,(z-10.8)/4.2)**2
  bent=.48*max(0,(-y-(half-2.5))/2.5)**2*max(0,(-z-11.5)/3.5)**2
  inset=min(half-abs(y),15-abs(z))
  pressed=-.045*math.exp(-((inset-.45)/.16)**2)
  return .36+curl+bent+pressed
 def point(y,z):return p(depth(y,z),y,z)
 def normal(y,z):
  e=.001;dy=(depth(y+e,z)-depth(y-e,z))/(2*e);dz=(depth(y,z+e)-depth(y,z-e))/(2*e);return G.unit(p(1,-dy,-dz))
 def uv(y,z):return RM.atlas_uv(RM.SIGNS,RM.SIGN_ATLAS,'office_rules',(y+half)/width,(z+15)/30)
 rows=[[(u*extent(z),z) for u in us] for z in zs]
 for r0,r1 in zip(rows,rows[1:]):
  for j in range(len(us)-1):
   yz=[r0[j],r0[j+1],r1[j+1],r1[j]]
   G.card(m,'face',[point(y,z) for y,z in yz],X,uv=[uv(y,z) for y,z in yz],normals=[normal(y,z) for y,z in yz])
   G.card(m,'back',[point(y,z)-X*.055 for y,z in yz],-X,normals=[-normal(y,z) for y,z in yz])
 boundary=rows[0]+[r[-1] for r in rows[1:]]+rows[-1][-2::-1]+[r[0] for r in rows[-2:0:-1]]
 for aa,bb in zip(boundary,boundary[1:]+boundary[:1]):
  pa,pb=point(*aa),point(*bb);toward=p(0,(aa[0]+bb[0])/2,(aa[1]+bb[1])/2)
  G.card(m,'back',[pa,pb,pb-X*.055,pa-X*.055],toward)
  # A short return fold on the back, not a coloured tube on the front.
  ca=np.array(aa)*.986;cb=np.array(bb)*.986
  G.card(m,'back',[pa-X*.055,pb-X*.055,point(*cb)-X*.16,point(*ca)-X*.16],-X)
 if lod<2:
  # Two centreline screws hold the sheet; the curled outside corners are free.
  for z in (-13.4,13.4):
   q=point(0,z)+X*.025
   G.lathe_axis(m,q,X,[(0,0),(.24,0),(.24,.035),(0,.035)],'grime',sides=12 if lod==0 else 8)
   G.lathe_axis(m,q+X*.035,X,[(0,0),(.17,0),(.17,.065),(.10,.12),(0,.12)],'steel',sides=12 if lod==0 else 8)
   if lod==0:G.rod(m,q+X*.151-Y*.11,q+X*.151+Y*.11,.018,'grime',sides=4)
 if lod==0:
  # Sparse irregular paint losses expose neutral grey metal at cut edges.
  for side,z,length in [(-1,-10,1.1),(-1,8,.7),(1,-6,1.4),(1,10,.8)]:
   y=side*(half-.04);yz=[(y,z),(y-side*.12,z+.2),(y-side*.045,z+length),(y,z+length+.1)]
   G.card(m,'back',[point(a,b)+X*.009 for a,b in yz],X)
 m.material_overrides={'face':'materials/riverside/rs_signs.vmat','back':'materials/riverside/rs_steel.vmat','steel':'materials/riverside/rs_alu.vmat','grime':'materials/riverside/rs_dark.vmat'};m.tile_overrides={k:64 for k in m.material_overrides}
 return m
counts=[K.write_obj(ASSET/f'plaque_lod{i}.obj',make(i),'plaque') for i in range(3)]
K.write_vmdl(ASSET/'plaque.vmdl',RES,'plaque_lod0',make(0));t=(ASSET/'plaque.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/plaque_lod%d.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,RES,i) for i in range(3));groups=','.join('{_class="LODGroup" switch_threshold=%d meshes=["lod%d"]}'%(d,i) for i,d in enumerate((0,15,40)))
(ASSET/'plaque.vmdl').write_text(t[:a]+'{_class="RenderMeshList" children=['+files+']},{_class="LODGroupList" children=['+groups+']},'+t[b:])
origin=K.to_world(P.local_to_world(centre+P.v(0,.6,0),(c[0],c[1],M.HIGH),yaw)).tolist();protected=[source,source.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']+[ROOT/'Assets'/v for v in make(0).material_overrides.values()]
r=dict(position=origin,yaw=0,triangles=counts,width=width,height=30,background=RES+'/review/pad_without_rules.vmdl',old_triangles=2,installed=False,new_materials=0,new_textures=0,protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected});(OUT/'review.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
