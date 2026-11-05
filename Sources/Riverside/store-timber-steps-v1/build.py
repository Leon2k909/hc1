"""Review-only player-route timber entrance steps; existing approved wood atlas reused."""
from pathlib import Path
import sys,json,hashlib,re,collections,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as R
OUT=ROOT/'output/riverside/store-timber-steps-v1';STAGE=OUT/'stage';RES='models/props/riverside/store_timber_steps_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1));origin=np.array(((R.STORE_DOOR[0]+R.STORE_DOOR[1])/2,R.PORCH_N0-30,0.))
def make(lod):
 m=K.Model();slot=0
 def wood_uv(start,axis,across):
  nonlocal slot
  polys=m.polygons['wood'][start:];allp=np.array([p for pts,n in polys for p in pts]);lo=allp.min(axis=0);span=np.maximum(allp.max(axis=0)-lo,.01)
  u0=8+(slot%2)*1024;v0=8+(3+(slot%6)//2)*168;slot+=1
  for j,(pts,n) in enumerate(polys,start):
   # The end grain uses the remaining axis, preventing zero-area UVs on the cut ends.
   a=axis if np.ptp(np.array(pts)[:,axis])>.01 else next(i for i in range(3) if i!=axis and np.ptp(np.array(pts)[:,i])>.01)
   b=across if across!=a and np.ptp(np.array(pts)[:,across])>.01 else next(i for i in range(3) if i!=a and np.ptp(np.array(pts)[:,i])>.01)
   m.polygon_uvs[('wood',j)]=[((u0+(p[a]-lo[a])/span[a]*1008)/2048,1-(v0+(p[b]-lo[b])/span[b]*152)/2048) for p in pts]
 def timber(c,size,axis=0):
  start=len(m.polygons['wood']);G.bevel_box(m,np.array(c),(X,Y,Z),size,'wood',.14 if lod<2 else 0);wood_uv(start,axis,1 if axis==0 else 2)
 for step in range(3):
  height=6.5*(step+1)
  for board in range(2):timber((0,step*10+2.45+board*5.1,height-.75),(90,4.9,1.5))
  if lod<2:
   for x in (-42,-14,14,42):
    for y in (step*10+1.5,step*10+8.6):
     p=np.array((x,y,height+.025));G.lathe_axis(m,p,-Z,[(0,0),(.22,0),(.22,.09),(0,.09)],'steel',sides=8 if lod==0 else 6)
     if lod==0:
      for size in ((.27,.04,.015),(.04,.27,.015)):G._box3(m,p+Z*.008,(X,Y,Z),size,'dark')
 for x in (-42,-14,14,42):
  start=len(m.polygons['wood']);profile=[(-y,z) for y,z in [(0,0),(7,0),(30,13),(30,18),(20,18),(20,11.5),(10,11.5),(10,5),(0,5)]]
  G.extrude(m,(x-.75,0,0),(x+.75,0,0),profile,'wood',up=Z,smooth=0);wood_uv(start,1,2)
  if lod<2:
   for step in range(3):
    y=step*10+6;z=6.5*(step+1)-1.6
    for s in (-1,1):
     G.bevel_box(m,np.array((x+s*.88,y,z-1)),(X,Y,Z),(.14,4,2),'steel',.025)
     G.bevel_box(m,np.array((x+s*1.45,y,z-.08)),(X,Y,Z),(1.3,4,.14),'steel',.025)
     for dy in (-1.1,1.1):G.lathe_axis(m,np.array((x+s*.97,y+dy,z-1)),X*s,[(0,0),(.2,0),(.2,.09),(0,.09)],'dark',sides=6)
 timber((0,28,11.5),(86,3,3))
 for x in (-40,40):timber((x,28,5),(3.5,3.5,10),2)
 m.material_overrides={'wood':'materials/riverside/crate_v2/crate.vmat','steel':'materials/lowtide/lt_steel.vmat','dark':'materials/riverside/rs_dark.vmat'};m.tile_overrides={p:48 for p in m.polygons}
 return m
counts=[K.write_obj(MODEL/f'steps_lod{i}.obj',make(i),f'steps_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'steps.vmdl',RES,'steps_lod0',make(0));t=(MODEL/'steps.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/steps_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'steps.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{files}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
old=K.Model();P.steps(old,origin[:2],(0,1),90,19.5,'rs_wood','wood',rise=7);R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_steps')
local=K.Model();P.steps(local,(0,0),(0,1),90,19.5,'rs_wood','wood',rise=7);local.boxes.clear();local.hulls.clear();R.configure(local);K.write_model(MODEL,RES,'legacy_steps',local)
tree=ast.parse((ROOT/'Sources/Riverside/still-here-board-v1/prepare_install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='records');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'records','exec'),env);records=env['records']
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for _,k in fs);vmdl=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for _,k in fs):source=p;break
assert source,'Original entrance steps do not match saved store input'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)==36 and not +want
(MODEL/'store_without_steps.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_steps.mtl'));(MODEL/'store_without_steps.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'store_without_steps.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/store_without_steps.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene'];external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in make(0).material_overrides.values()}
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),yaw=0,removed_old_triangles=36,resource=RES+'/steps.vmdl',background=RES+'/store_without_steps.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
