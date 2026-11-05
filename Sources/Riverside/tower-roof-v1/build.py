"""Guard tower's corrugated canopy, review only; existing images reused."""
from pathlib import Path
import sys,json,hashlib,collections,re,math,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as R
OUT=ROOT/'output/riverside/tower-roof-v1';STAGE=OUT/'stage';RES='models/props/riverside/tower_roof_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
MAT='materials/riverside/tower_roof_v1';MATERIAL=STAGE/'Assets'/MAT;MATERIAL.mkdir(parents=True,exist_ok=True)
t=(ROOT/'Assets/materials/riverside/rs_roof.vmat').read_text().replace('materials/riverside/rs_roof_normal.jpg','materials/default/default_normal.tga').replace('g_flRoughnessScaleFactor "1"','g_flRoughnessScaleFactor "1.2"')
(MATERIAL/'sheet.vmat').write_text(t)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.));slope=8/136
def make(lod):
 m=K.Model();normal=G.unit((0,slope,1));along=G.unit((0,1,-slope))
 for panel in range(4):
  left=-68+panel*34;right=min(68,left+34.7);steps=(80,40,10)[lod]
  xs=np.linspace(left,right,steps+1)
  def point(x,y):return np.array((x,y,-slope*y+(.35*math.cos(2*math.pi*x/3.5) if lod<2 else 0)+panel*.035))
  for a,b in zip(xs,xs[1:]):
   pts=[point(a,-68),point(b,-68),point(b,68),point(a,68)]
   G.card(m,'roof',pts,normal)
   low=[p-Z*.065 for p in pts];G.card(m,'roof',low,-normal)
   for k,n in ((0,-Y),(2,Y)):G.card(m,'roof',[pts[k],pts[k+1],low[k+1],low[k]],n)
  for x,n in ((left,-X),(right,X)):
   a,b=point(x,-68),point(x,68);G.card(m,'roof',[a,b,b-Z*.065,a-Z*.065],n)
 # Folded perimeter caps cover the exposed cut edges and let water drip clear of the wood.
 for side in (-1,1):
  x=side*68
  G.bevel_box(m,np.array((x,0,-.9)),(X,along,normal),(.12,137,2.5),'steel',.03 if lod<2 else 0)
  G.bevel_box(m,np.array((side*67.1,0,.55)),(X,along,normal),(2.0,137,.12),'steel',.03 if lod<2 else 0)
  y=side*68;z=-slope*y
  G.bevel_box(m,np.array((0,y,z-.8)),(X,Y,Z),(137,.14,2.3),'steel',.03 if lod<2 else 0)
 # Two tapered timber bearers land exactly on the existing post tops (world Z620).
 for side in (-1,1):
  x=side*58
  for n,pts in [(Z,[(x-1.75,-68,3.5),(x+1.75,-68,3.5),(x+1.75,68,-4.5),(x-1.75,68,-4.5)]),(-Z,[(x-1.75,-68,-8),(x+1.75,-68,-8),(x+1.75,68,-8),(x-1.75,68,-8)])]:G.card(m,'wood',[np.array(p) for p in pts],n)
  for xx,n in ((x-1.75,-X),(x+1.75,X)):G.card(m,'wood',[np.array(p) for p in [(xx,-68,-8),(xx,68,-8),(xx,68,-4.5),(xx,-68,3.5)]],n)
  for y,n in ((-68,-Y),(68,Y)):
   top=-slope*y-.5;G.card(m,'wood',[np.array(p) for p in [(x-1.75,y,-8),(x+1.75,y,-8),(x+1.75,y,top),(x-1.75,y,top)]],n)
 for y in (-58,0,58):G.bevel_box(m,np.array((0,y,-slope*y))-normal*2.12,(X,along,normal),(136,3.5,3.2),'wood',.12 if lod<2 else 0)
 if lod<2:
  for y in (-58,0,58):
   for x in np.arange(-63,64,14):
    p=np.array((x,y,-slope*y+.365+.035*min(3,int((x+68)/34))))
    G.lathe_axis(m,p,normal,[(0,0),(.34,0),(.34,.1),(0,.1)],'dark',sides=8 if lod==0 else 6)
    G.lathe_axis(m,p+normal*.1,normal,[(0,0),(.23,0),(.23,.18),(0,.18)],'steel',sides=6)
 m.material_overrides={'roof':MAT+'/sheet.vmat','wood':'materials/riverside/rs_wood.vmat','steel':'materials/lowtide/lt_steel.vmat','dark':'materials/riverside/rs_dark.vmat'};m.tile_overrides={p:96 for p in m.polygons}
 return m
counts=[K.write_obj(MODEL/f'roof_lod{i}.obj',make(i),f'roof_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'roof.vmdl',RES,'roof_lod0',make(0));t=(MODEL/'roof.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/roof_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,25,60)))
(MODEL/'roof.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{files}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
f=G.unit((*R.TOWER[1],0));side=np.cross(Z,f);origin=np.array(R.TOWER[0],float)+Z*628;yaw=math.degrees(math.atan2(-side[1],-side[0]))
pts=[origin+side*sx+f*sy+Z*(-slope*sy) for sx,sy in [(-68,-68),(68,-68),(68,68),(-68,68)]]
old=K.Model();G.card(old,'rs_roof',pts,Z+f*.1);G.card(old,'rs_roof',pts,-Z);R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_roof')
local=K.Model();pts=[np.array((x,y,-slope*y)) for x,y in [(-68,-68),(68,-68),(68,68),(-68,68)]];G.card(local,'rs_roof',pts,Z);G.card(local,'rs_roof',pts,-Z);R.configure(local);K.write_model(MODEL,RES,'legacy_roof',local)
tree=ast.parse((ROOT/'Sources/Riverside/still-here-board-v1/build.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='records');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'records','exec'),env);records=env['records']
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for i,k in fs);vmdl=ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for i,k in fs):source=p;break
assert source,'Old roof no longer matches saved mesh'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)==4 and not +want
(MODEL/'dressing_without_roof.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib dressing_without_roof.mtl'));(MODEL/'dressing_without_roof.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'dressing_without_roof.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/dressing_without_roof.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene'];external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in make(0).material_overrides.values() if not v.startswith(MAT+'/')}
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),yaw=yaw,removed_old_triangles=4,resource=RES+'/roof.vmdl',background=RES+'/dressing_without_roof.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()});(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
