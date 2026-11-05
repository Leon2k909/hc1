"""Refine the east yard roadworks barrier without rebuilding the shared map."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
OUT=ROOT/'output/railhead/road-barrier-v1';STAGE=OUT/'stage'
RES='models/maps/railhead/road-barrier-v1';MAT='materials/railhead/road-barrier-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_dress_detail.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'road-barrier-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('white',(.74,.75,.71),.46,0.),('red',(.65,.035,.024),.38,.05),('yellow',(.65,.46,.075),.76,0.),('rubber',(.035,.040,.035),.87,0.),('steel',(.48,.51,.50),.43,.85)]:
 (MATERIAL/f'{name}.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flRoughnessScaleFactor "1"
 g_flMetalness "'''+str(metal)+'''"
 TextureColor "['''+' '.join(map(str,colour))+''' 0]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "['''+f'{rough} {rough} {rough} 0'+''']"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
}
''',encoding='utf-8')
m=K.Model();F=D.Frame(1905.,-1556.,0.,'+n');X=F.x;Y=F.y;Z=np.array((0.,0.,1.))
def P(x,y,z):return F.p(x,y,z)
def box(c,size,paint,b=.08):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
def face(paint,pts,n):D._face(m,paint,pts,n)
def lathe(c,axis,prof,paint,sides=20):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in prof],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=16):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def screw(c,axis,r=.17):
 cylinder(c,axis,.055,r*1.25,'steel',20)
 q=np.array(c,float);q+=np.array((0,0,.055)) if np.dot(axis,Z)>.9 else np.array((0,.055 if np.dot(axis,Y)>0 else -.055,0))
 cylinder(tuple(q),axis,.12,r,'steel',6)
def outline(w,h,r):
 pts=[]
 for cx,cy,a0 in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,math.pi/2),(-w/2+r,-h/2+r,math.pi),(w/2-r,-h/2+r,3*math.pi/2)):
  for a in np.linspace(a0,a0+math.pi/2,9):pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
 return pts
def loft(rings,paint,normal_hint,caps=()):
 n=len(rings[0]);norms=[[np.zeros(3) for _ in ring] for ring in rings];faces=[]
 for j in range(len(rings)-1):
  for k in range(n):
   kk=(k+1)%n;pts=[rings[j][k],rings[j][kk],rings[j+1][kk],rings[j+1][k]]
   normal=K.normalise(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
   if np.dot(normal,normal_hint(j,k,pts))<0:normal=-normal
   for jj,ii in ((j,k),(j,kk),(j+1,k),(j+1,kk)):norms[jj][ii]+=normal
   faces.append((j,k,kk,pts,normal))
 for j,k,kk,pts,normal in faces:
  ns=[K.normalise(norms[j][k]),K.normalise(norms[j][kk]),K.normalise(norms[j+1][kk]),K.normalise(norms[j+1][k])]
  D._face(m,paint,pts,normal,normals=ns)
 for index,normal in caps:face(paint,rings[index],normal)
# Weighted moulded feet: rubber ground pads, rounded shoulders and recessed grip
# pockets on both sides, with the steel posts seated in a raised socket.
for x in (-16.7,16.7):
 box((x,0,.16),(13.2,7.2,.28),'rubber',.10)
 profiles=[(.22,13.5,7.5,.85),(.48,14.,8.,1.0),(1.92,14.,8.,1.0),(2.4,13.2,7.2,.95)]
 rings=[[P(x+a,b,z) for a,b in outline(w,h,r)] for z,w,h,r in profiles]
 loft(rings,'yellow',lambda j,k,pts:np.mean(pts,axis=0)-P(x,0,profiles[j][0]),caps=((0,-Z),(-1,Z)))
 for sy in (-1,1):
  box((x,sy*4.015,1.25),(6.8,.035,.73),'rubber',.012)
  box((x,sy*3.99,1.70),(7.2,.22,.23),'yellow',.09)
  for dx in (-2.8,2.8):box((x+dx,sy*3.995,1.23),(.20,.22,.74),'yellow',.07)
 box((x,0,2.56),(2.6,2.6,.70),'rubber',.2)
 box((x,0,20.7),(1.4,1.4,36.6),'steel',.09)
 box((x,0,39.05),(1.50,1.50,.32),'rubber',.09)
 for z in (12,16,20,24):
  cylinder((x,.711,z),Y,.015,.13,'rubber',12)
 # A thumb screw retains each post in its weighted socket.
 cylinder((x,1.30,2.6),Y,.65,.19,'steel',16)
 cylinder((x,1.94,2.6),Y,.30,.42,'rubber',24)
 for dx in (-.28,.28):box((x+dx,2.12,2.6),(.18,.26,.44),'rubber',.07)
# Rounded hollow-board exterior and its inset laminated faces.
board_profiles=[(-.55,39.0,9.5,.55),(-.37,39.4,9.9,.75),(.37,39.4,9.9,.75),(.55,39.0,9.5,.55)]
board_offset=1.4
board_rings=[[P(x,d+board_offset,34.45+u) for x,u in outline(w,h,r)] for d,w,h,r in board_profiles]
loft(board_rings,'white',lambda j,k,pts:np.mean(pts,axis=0)-P(0,board_profiles[j][0]+board_offset,34.45),caps=((0,-Y),(-1,Y)))
def clip(poly,axis,bound,greater):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  va=axis(a)-bound;vb=axis(b)-bound;ia=va>=-1e-9 if greater else va<=1e-9;ib=vb>=-1e-9 if greater else vb<=1e-9
  if ia:result.append(a)
  if ia!=ib:
   t=va/(va-vb);result.append(tuple(a[q]+t*(b[q]-a[q]) for q in range(2)))
 return result
for s in (-1,1):
 # The red diagonal panels are geometry on both faces. The original blocked
 # colour board is replaced, without adding a light or emissive material.
 for k in range(-4,5):
  poly=[(-18.7,-4.),(18.7,-4.),(18.7,4.),(-18.7,4.)]
  poly=clip(poly,lambda p:p[0]+p[1],k*9.5,True)
  if poly:poly=clip(poly,lambda p:p[0]+p[1],k*9.5+4.6,False)
  if len(poly)>=3:face('red',[P(x,board_offset+s*.565,34.45+u) for x,u in poly],Y*s)
 for x in (-18.3,18.3):
  for z in (30.8,38.1):
   cylinder((x,board_offset+s*.57,z),Y*s,.045,.13,'rubber',16)
   cylinder((x,board_offset+s*.617,z),Y*s,.035,.085,'steel',12)
 # A shallow seam at the foot of each board face catches light at close range.
 box((0,board_offset+s*.57,29.95),(36.6,.025,.055),'rubber',.008)
# Formed saddle clamps on the back of the board and two short folded stays.
for x in (-16.7,16.7):
 for z in (31.0,37.8):
  box((x,-.875,z),(3.5,.25,1.2),'steel',.08)
  box((x,.82,z),(3.5,.16,1.2),'steel',.05)
  for dx in (-1.55,1.55):box((x+dx,-.015,z),(.32,1.7,1.2),'steel',.07)
  for dx in (-1.35,1.35):screw((x+dx,-1.025,z),-Y,.14)
 G.tube(m,[P(x,-.9,30.3),P(x,-1.8,27.8),P(x,-.70,26.2)],.18,'steel',sides=12,bend_radius=.3)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('white','red','yellow','rubber','steel')};m.tile_overrides={p:16 for p in m.polygons}
count=K.write_model(MODEL,RES,'road_barrier',m)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl'
source=ROOT/'Assets/models/maps/railhead/extinguisher-v2/east-base.obj'
assert 'models/maps/railhead/extinguisher-v2/east-base.obj' in public.read_text()
legacy=K.Model();D.road_barrier(legacy,1905.,-1556.,'e');R.configure(legacy)
K.write_obj(OUT/'legacy-barrier.obj',legacy,'legacy_barrier')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-barrier.obj');wanted=collections.Counter(key for _,key in old)
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved barrier differs from helper: inspect before staging'
(MODEL/'east_without_barrier.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib railhead_dress_east.mtl','mtllib east_without_barrier.mtl'))
(MODEL/'east_without_barrier.mtl').write_bytes((source.parent/'railhead_dress_east.mtl').read_bytes())
(MODEL/'east_without_barrier.vmdl').write_text(public.read_text().replace('models/maps/railhead/extinguisher-v2/east-base.obj',RES+'/east_without_barrier.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/clock-v1/import.cs.txt').read_text().replace('output/railhead/clock-v1','output/railhead/road-barrier-v1').replace('maps/railhead/clock-v1/','maps/railhead/road-barrier-v1/').replace('materials/railhead/clock-v1/','materials/railhead/road-barrier-v1/')
(HERE/'import.cs.txt').write_text(template,encoding='utf-8')
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files))))
