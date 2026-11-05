"""A plank-built cable reel, staged without rebuilding Railhead."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
OUT=ROOT/'output/railhead/cable-drum-v1';STAGE=OUT/'stage'
RES='models/maps/railhead/cable-drum-v1';MAT='materials/railhead/cable-drum-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_dress_detail.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'cable-drum-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
wood=(ROOT/'Assets/materials/railhead/rw_wood.vmat').read_text()
for name in ('timber_a','timber_b','timber_c'):
 (MATERIAL/f'{name}.vmat').write_text(wood)
for name,colour,rough,metal in [('cable',(.031,.034,.030),.70,0.),('steel',(.36,.38,.36),.49,.80),('recess',(.025,.024,.020),.90,0.)]:
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
''')
m=K.Model();A=np.array((1.,0.,0.));B=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));C=np.array((1878.,-1632.,23.9))
# Recover the installed reel's actual face mapping. The earlier proposal used
# narrower, elongated grain and three tints; retain its shape with the original
# unmodified material and original texture scale. Align the grain to the
# physical boards so the texture's old diagonal seams do not cross them.
def original_timber_mapping():
 source=ROOT/'Assets/models/maps/railhead/road-barrier-v1/east_without_barrier.obj'
 vertices=[];uvs=[];paint='';samples={-1:[],1:[]}
 for line in source.read_text().splitlines():
  fields=line.split()
  if not fields:continue
  if fields[0]=='v':vertices.append(tuple(map(float,fields[1:4])))
  elif fields[0]=='vt':uvs.append(tuple(map(float,fields[1:3])))
  elif fields[0]=='usemtl':paint=fields[1]
  elif fields[0]=='f' and paint=='rw_wood':
   ids=[tuple(map(int,t.split('/')[:2])) for t in fields[1:]]
   pts=[vertices[v-1] for v,_ in ids]
   if not all(-1656<=p[2]<=-1608 and .2<=p[1]<=47.6 for p in pts):continue
   for sign in (-1,1):
    if all(abs(p[0]+1878+sign*15.4)<.002 for p in pts):
     samples[sign].extend(((p[2]+1632,p[1]-23.9,1),uvs[uv-1]) for p,(_,uv) in zip(pts,ids))
 result={}
 for sign,rows in samples.items():
  assert len(rows)>30,'Original flange mapping not found'
  design=np.array([r[0] for r in rows]);uv=np.array([r[1] for r in rows])
  coeff=np.linalg.lstsq(design,uv,rcond=None)[0]
  assert np.max(np.abs(design@coeff-uv))<.0001,'Original face is not affine'
  result[sign]=coeff
 return result
timber_mapping=original_timber_mapping()
def P(t,x,z):return C+A*t+B*x+Z*z
def face(paint,pts,normal,uv=None):D._face(m,paint,pts,normal,uv=uv)
def cyl(at,axis,length,r,paint,sides=20):G.lathe_axis(m,at,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
def clipped(poly,x0,x1):
 for bound,greater in ((x0,True),(x1,False)):
  result=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   va=a[0]-bound;vb=b[0]-bound;ia=va>=-1e-8 if greater else va<=1e-8;ib=vb>=-1e-8 if greater else vb<=1e-8
   if ia:result.append(a)
   if ia!=ib:
    u=va/(va-vb);result.append(tuple(a[q]+u*(b[q]-a[q]) for q in range(2)))
  poly=result
  if len(poly)<3:return []
 return poly
def draw_radial(paint,poly,t,normal):
 sign=1 if float(np.dot(normal,A))>0 else -1
 coeff=timber_mapping[sign]
 u_scale=np.linalg.norm(coeff[:2,0]);v_scale=np.linalg.norm(coeff[:2,1])
 face(paint,[P(t,x,z) for x,z in poly],normal,uv=[(x*u_scale+coeff[2,0],z*v_scale+coeff[2,1]) for x,z in poly])
# Nine individual full-depth planks per flange, separated by narrow daylight
# seams. Their centre opening stays open through both cheeks and the barrel.
for sign in (-1,1):
 front=sign*15.4;back=sign*13.8
 for j in range(9):
  x0=-23.6+j*(47.2/9)+.035;x1=-23.6+(j+1)*(47.2/9)-.035
  paint=('timber_a','timber_c','timber_b','timber_a','timber_b','timber_c','timber_a','timber_c','timber_b')[j]
  for k in range(96):
   a0=math.tau*k/96;a1=math.tau*(k+1)/96
   radial=lambda r,a:(r*math.cos(a),r*math.sin(a))
   poly=clipped([radial(23.44,a0),radial(23.44,a1),radial(2.50,a1),radial(2.50,a0)],x0,x1)
   if poly:
    draw_radial(paint,poly,front,A*sign);draw_radial(paint,poly,back,-A*sign)
   # Chamfered outside rim, with the grain changing on the cut timber edge.
   for t0,r0,t1,r1 in ((front,23.44,front-sign*.16,23.6),(front-sign*.16,23.6,back+sign*.16,23.6),(back+sign*.16,23.6,back,23.44)):
    # Split the rim at each board boundary; no continuous disc bridges seams.
    p0=np.array(radial(r0,a0));p1=np.array(radial(r0,a1));q0=np.array(radial(r1,a0));q1=np.array(radial(r1,a1))
    lo,hi=0.,1.
    for edge0,edge1 in ((p0,p1),(q0,q1)):
     dx=edge1[0]-edge0[0]
     if abs(dx)<1e-8:
      if not x0<=edge0[0]<=x1:hi=-1
     else:
      aa=(x0-edge0[0])/dx;bb=(x1-edge0[0])/dx;lo=max(lo,min(aa,bb));hi=min(hi,max(aa,bb))
    if hi>lo:
     aa=p0+(p1-p0)*lo;bb=p0+(p1-p0)*hi;cc=q0+(q1-q0)*hi;dd=q0+(q1-q0)*lo
     face(paint,[P(t0,*aa),P(t0,*bb),P(t1,*cc),P(t1,*dd)],B*math.cos((a0+a1)/2)+Z*math.sin((a0+a1)/2))
  # The timber's sawn plank edges are visible inside the narrow seams.
  for xx,norm in ((x0,-B),(x1,B)):
   if abs(xx)>=23.44:continue
   zmax=math.sqrt(23.44**2-xx**2)
   intervals=[(-zmax,zmax)] if abs(xx)>=2.5 else [(-zmax,-math.sqrt(2.5**2-xx**2)),(math.sqrt(2.5**2-xx**2),zmax)]
   for z0,z1 in intervals:face(paint,[P(back,xx,z0),P(front,xx,z0),P(front,xx,z1),P(back,xx,z1)],norm)
 # A steel axle sleeve is an annulus, not a painted dot covering the bore.
 G.lathe_axis(m,P(sign*13.65,0,0),A*sign,[(2.50,0),(3.10,0),(3.28,.18),(3.28,1.55),(3.10,1.78),(2.50,1.78),(2.50,0)],'steel',sides=48)
 # Recessed washers, hexagonal nuts and their dark central stud ends.
 for k in range(6):
  a=k*math.tau/6+.20;x=13.0*math.cos(a);z=13.0*math.sin(a)
  cyl(P(front+sign*.025,x,z),A*sign,.065,.88,'recess',32)
  cyl(P(front+sign*.09,x,z),A*sign,.10,.78,'steel',32)
  cyl(P(front+sign*.19,x,z),A*sign,.38,.50,'steel',6)
  cyl(P(front+sign*.58,x,z),A*sign,.025,.21,'recess',16)
 # Small, separate fixing nails along the upper and lower plank edges.
 for j in range(1,8):
  x=-23.6+(j+.5)*47.2/9;zz=math.sqrt(23.44**2-x*x)-1.5
  for z in (-zz,zz):cyl(P(front+sign*.025,x,z),A*sign,.045,.12,'steel',10)
 # Stencilled inventory number on the timber, below the hub.
 D.stroke_text(m,'recess','01',P(front+sign*.025,-3,-19),B,Z,2.8,1.7,.19,gap=.65)
# The barrel's timber core and the wound cable have a true open axle bore.
G.lathe_axis(m,P(-13.8,0,0),A,[(2.50,0),(11.,0),(11.,27.6),(2.50,27.6),(2.50,0)],'timber_b',sides=64)
G.lathe_axis(m,P(-13.50,0,0),A,[(11.,0),(14.80,0),(14.80,27.),(11.,27.)],'cable',sides=64)
# A continuous twelve-turn helix exposes the cable jacket between the cheeks.
turns=12;path=[]
for u in np.linspace(0,1,turns*72+1):
 a=math.tau*turns*u;path.append(P(-12.50+25*u,16.0*math.cos(a),16.0*math.sin(a)))
D.tube(m,path,1.02,'cable',sides=10)
D.disc(m,'cable',path[0],K.normalise(path[0]-path[1]),1.02,10)
D.disc(m,'cable',path[-1],K.normalise(path[-1]-path[-2]),1.02,10)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('timber_a','timber_b','timber_c','cable','steel','recess')}
m.tile_overrides={p:32 for p in m.polygons}
count=K.write_model(MODEL,RES,'cable_drum',m)
legacy=K.Model();D.cable_drum(legacy,1878.,-1632.,.3,'e');R.configure(legacy)
K.write_obj(OUT/'legacy-drum.obj',legacy,'legacy_drum')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-drum.obj');wanted=collections.Counter(key for _,key in old)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl';text=public.read_text()
source=ROOT/'Assets/models/maps/railhead/road-barrier-v1/east_without_barrier.obj'
assert 'models/maps/railhead/road-barrier-v1/east_without_barrier.obj' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved reel differs from legacy helper; inspect before staging'
(MODEL/'east_without_drum.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib east_without_barrier.mtl','mtllib east_without_drum.mtl'))
(MODEL/'east_without_drum.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'east_without_drum.vmdl').write_text(text.replace('models/maps/railhead/road-barrier-v1/east_without_barrier.obj',RES+'/east_without_drum.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/road-barrier-v1/import.cs.txt').read_text().replace('road-barrier-v1','cable-drum-v1')
(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files),planks=18,cable_turns=turns)))
