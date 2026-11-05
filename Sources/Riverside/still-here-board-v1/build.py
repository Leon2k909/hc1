"""Review-only reclaimed plank board, using the approved crate wood and original graffiti."""
from pathlib import Path
import sys,json,hashlib,collections,re,math
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as R,riverside_materials as RM
OUT=ROOT/'output/riverside/still-here-board-v1';STAGE=OUT/'stage';RES='models/props/riverside/still_here_board_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.));w=270*.7*.62;h=49.
text=K.Model();P.paint(text,'still_here',np.array((0.,-.8,0)),X,h*.86,tone='red',off=0)
def make(lod):
 m=K.Model()
 for k in range(6):
  z=-h/2+(k+.5)*h/6;bh=h/6-.20;front=-.82+(.03 if k%2 else -.03)
  G.bevel_box(m,np.array((0,front+.75,z)),(X,Y,Z),(w,1.5,bh),'wood',.12 if lod<2 else 0)
  # Reuse unlettered plank crops from the approved crate atlas.
  for i,(pts,n) in enumerate(m.polygons['wood']):
   if ('wood',i) in m.polygon_uvs:continue
   slot=k+6;u0=8+(slot%2)*1024;v0=8+(slot//2)*168
   m.polygon_uvs[('wood',i)]=[((u0+(p[0]/w+.5)*1008)/2048,1-(v0+(1-(p[2]-(z-bh/2))/bh)*152)/2048) for p in pts]
  for paint,polys in text.polygons.items():
   for j,(pts,n) in enumerate(polys):
    uv=text.polygon_uvs[(paint,j)];corners={(round(p[0],5),round(p[2],5)):np.array(t) for p,t in zip(pts,uv)}
    xmin=min(p[0] for p in pts);xmax=max(p[0] for p in pts);zmin=min(p[2] for p in pts);zmax=max(p[2] for p in pts)
    a=max(z-bh/2,zmin);b=min(z+bh/2,zmax)
    if b<=a:continue
    def tuv(x,zz):
     s=(x-xmin)/(xmax-xmin);t=(zz-zmin)/(zmax-zmin)
     return ((1-s)*(1-t)*corners[(round(xmin,5),round(zmin,5))]+s*(1-t)*corners[(round(xmax,5),round(zmin,5))]+s*t*corners[(round(xmax,5),round(zmax,5))]+(1-s)*t*corners[(round(xmin,5),round(zmax,5))]).tolist()
    pp=[np.array((xx,front-.025,zz)) for xx,zz in [(xmin,a),(xmax,a),(xmax,b),(xmin,b)]]
    G.card(m,paint,pp,-Y,uv=[tuv(xmin,a),tuv(xmax,a),tuv(xmax,b),tuv(xmin,b)])
  if lod<2:
   for x in (-w*.4,w*.4):
    G.lathe_axis(m,np.array((x,front-.04,z)),-Y,[(0,0),(.28,0),(.28,.13),(0,.13)],'steel',sides=6)
    if lod==0:m.oriented_box(np.array((x,front-.18,z)),(X,Y,Z),(.3,.025,.05),'dark')
 for x in (-w*.4,w*.4):G.bevel_box(m,np.array((x,1.55,0)),(X,Y,Z),(3.2,1.6,h-3),'wood',.1 if lod<2 else 0)
 m.beam(np.array((-w*.38,2.0,-h*.4)),np.array((w*.38,2.0,h*.4)),(2.5,1.3),'wood')
 for side in (-1,1):
  G.bevel_box(m,np.array((side*(w/2-1),2.9,0)),(X,Y,Z),(10,.25,h-6),'steel',.08 if lod<2 else 0)
 for i,(pts,n) in enumerate(m.polygons['wood']):
  if ('wood',i) in m.polygon_uvs:continue
  points=np.array(pts);axis=2 if np.ptp(points[:,2])>np.ptp(points[:,0]) else 0;cross=0 if axis==2 else 2
  lo=points.min(axis=0);span=np.maximum(points.max(axis=0)-lo,.01)
  m.polygon_uvs[('wood',i)]=[((8+(p[axis]-lo[axis])/span[axis]*1008)/2048,1-(8+10*168+(p[cross]-lo[cross])/span[cross]*152)/2048) for p in pts]
 m.material_overrides={'wood':'materials/riverside/crate_v2/crate.vmat','steel':'materials/lowtide/lt_steel.vmat','dark':'materials/riverside/rs_dark.vmat','rs_paint_red':'materials/riverside/rs_paint_red.vmat'};m.tile_overrides={p:48 for p in m.polygons}
 return m
counts=[K.write_obj(MODEL/f'board_lod{i}.obj',make(i),f'board_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'board.vmdl',RES,'board_lod0',make(0));t=(MODEL/'board.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/board_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,20,50)))
(MODEL/'board.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{files}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
f=G.unit((*R.SIGN[1],0));right=P.right_for(f);yaw=math.degrees(math.atan2(right[1],right[0]));th=270*.7/RM.aspect(RM.LIT,'park_sign');mh=210*.7/RM.aspect(RM.LIT,'marquee');zmq=370-th-14*.7-mh
origin=np.array(R.SIGN[0],float)+Z*(zmq-26*.7-h/2)+f*4
old=K.Model();P.obox(old,origin,right,(w,1.5,h),'rs_plywood');P.paint(old,'still_here',origin+f*.8,right,h*.86,tone='red',off=0);R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_board')
local=K.Model();P.obox(local,np.zeros(3),(1,0),(w,1.5,h),'rs_plywood');P.paint(local,'still_here',np.array((0.,-.8,0)),X,h*.86,tone='red',off=0);R.configure(local);K.write_model(MODEL,RES,'legacy_board',local)
def records(p):
 ls=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in ls if l.startswith('v ')];mat='';fs=[]
 for i,l in enumerate(ls):
  if l.startswith('usemtl '):mat=l.split()[1]
  if l.startswith('f '):fs.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return ls,fs
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for i,k in fs);vmdl=ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for i,k in fs):source=p;break
assert source,'Original board does not match saved dressing'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)==14 and not +want
(MODEL/'dressing_without_board.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib dressing_without_board.mtl'));(MODEL/'dressing_without_board.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'dressing_without_board.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/dressing_without_board.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene'];external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in make(2).material_overrides.values()}
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),yaw=yaw,removed_old_triangles=14,resource=RES+'/board.vmdl',background=RES+'/dressing_without_board.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()});(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
