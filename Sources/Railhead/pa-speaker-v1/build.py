"""One platform PA speaker, rebuilt without changing its saved scene or physics."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
OUT=ROOT/'output/railhead/pa-speaker-v1';STAGE=OUT/'stage'
RES='models/maps/railhead/pa-speaker-v1';MAT='materials/railhead/pa-speaker-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_dress_detail.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'pa-speaker-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('housing',(.58,.60,.57),.48,0.),('grille',(.105,.12,.125),.45,.35),('rubber',(.022,.027,.030),.8,0.),('bracket',(.14,.16,.17),.43,.5),('steel',(.45,.48,.48),.30,.85)]:
 (MATERIAL/f'{name}.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flRoughnessScaleFactor "1"
 g_flMetalness "'''+str(metal)+'''"
 TextureColor "materials/default/default_color.tga"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "['''+f'{rough} {rough} {rough} 0'+''']"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "['''+' '.join(map(str,colour))+''' 1]"
}
''',encoding='utf-8')
m=K.Model();F=D.Frame(7.7,820.,214.,'+e');X=F.x;Z=np.array((0.,0.,1.))
N=F.y*math.cos(.35)-Z*math.sin(.35);U=np.cross(N,X);C=F.p(0,6.4,-.6)
def P(x,d,u):return C+X*x+N*d+U*u
def box(c,size,paint='housing',b=.1,skip=()):G.bevel_box(m,P(*c),(X,N,U),size,paint,bevel=b,skip=skip)
def lathe(c,axis,profile,paint,sides=40):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=16):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def face(paint,points,towards):D._face(m,paint,points,towards)
# Rounded weather-resistant shell, front open so the grille is a real aperture.
box((0,0,0),(11.8,6.3,7.8),'housing',.45,skip=('+y',))
# Recessed baffle, rubber perimeter seal and a narrow rolled bezel.
box((0,2.27,0),(10.9,.25,6.9),'rubber',.12)
for s in (-1,1):
 box((s*5.48,2.91,0),(.20,.30,6.7),'rubber',.045)
 box((s*5.59,3.06,0),(.16,.18,6.8),'housing',.04)
 box((0,2.91,s*3.39),(10.8,.3,.20),'rubber',.045)
 box((0,3.06,s*3.50),(11.,.18,.16),'housing',.04)
# Two recessed drivers, with a curved surround and dust cap behind the mesh.
for x in (-2.65,2.65):
 lathe((x,0,0),N,[(0,2.37),(1.0,2.37),(2.05,2.57),(2.38,2.70),(2.45,2.80),(2.45,2.86),(2.25,2.86),(1.85,2.68),(.9,2.47),(0,2.57)],'rubber',48)
 G.torus(m,P(x,2.81,0),N,2.32,.09,'grille',seg=48,sides=8)
# A near-grille acoustic baffle closes the cavity right up to the edges, even
# from a steep side angle. Its two circular apertures expose only the drivers.
for x in (-2.70,2.70):
 outer=[];inner=[]
 for a in np.linspace(0,2*math.pi,65)[:-1]:
  ca,sa=math.cos(a),math.sin(a)
  t=min(2.70/max(abs(ca),1e-9),3.45/max(abs(sa),1e-9))
  outer.append(P(x+ca*t,2.985,sa*t))
  inner.append(P(x+ca*2.40,2.985,sa*2.40))
 for k in range(64):
  j=(k+1)%64
  face('rubber',[outer[k],outer[j],inner[j],inner[k]],N)
# Perforated steel sheet: each hole is open and has an inner wall, rather than
# being a painted dot. The rim and baffle hide the unneeded rear of the sheet.
nx,ny=24,16;w,h=10.5,6.4;dx,dy=w/nx,h/ny;r=.128;depth=3.04;thick=.045
for i in range(nx):
 for j in range(ny):
  cx=-w/2+(i+.5)*dx;cy=-h/2+(j+.5)*dy
  outer=[(dx/2,0),(dx/2,dy/2),(0,dy/2),(-dx/2,dy/2),(-dx/2,0),(-dx/2,-dy/2),(0,-dy/2),(dx/2,-dy/2)]
  inner=[(r*math.cos(k*math.pi/4),r*math.sin(k*math.pi/4)) for k in range(8)]
  for k in range(8):
   kk=(k+1)%8
   front=lambda p:P(cx+p[0],depth,cy+p[1])
   back=lambda p:P(cx+p[0],depth-thick,cy+p[1])
   face('grille',[front(outer[k]),front(outer[kk]),front(inner[kk]),front(inner[k])],N)
   toward=-X*(inner[k][0]+inner[kk][0])-U*(inner[k][1]+inner[kk][1])
   face('grille',[front(inner[k]),front(inner[kk]),back(inner[kk]),back(inner[k])],toward)
# Captive grille screws sit in the solid border, with a narrow visible slot.
for x in (-5.55,5.55):
 for u in (-2.8,2.8):
  cylinder((x,3.12,u),N,.07,.12,'steel',16)
  box((x,3.198,u),(.14,.012,.018),'rubber',.003)
# Mounting plate, continuous arm, toothed tilt pivot and its end bolts.
G.bevel_box(m,F.p(0,.18,0),(F.x,F.y,Z),(2.8,.36,3.4),'bracket',bevel=.14)
for x in (-.85,.85):
 for z in (-1.,1.):G.lathe_axis(m,F.p(x,.38,z),F.y,[(0.,0.),(.13,0.),(.13,.08),(0.,.08)],'steel',sides=12)
G.tube(m,[F.p(0,.4,0),F.p(0,2.2,0),P(0,-3.27,0)],.31,'bracket',sides=16,bend_radius=.4)
cylinder((-.9,-3.25,0),X,1.8,.62,'bracket',32)
for s in (-1,1):cylinder((s*.91,-3.25,0),X*s,.12,.27,'steel',6)
box((0,-3.17,0),(2.0,.25,2.0),'housing',.14)
# A weather boot and a short cable loop into the column.
cylinder((-2.7,-3.16,-1.1),-N,.28,.22,'rubber',16)
G.tube(m,[P(-2.7,-3.42,-1.1),F.p(-2.5,1.7,-2.2),F.p(-1.7,.5,-3.4)],.09,'rubber',sides=10,bend_radius=.35)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('housing','grille','rubber','bracket','steel')};m.tile_overrides={p:16 for p in m.polygons}
count=K.write_model(MODEL,RES,'pa_speaker',m)
# The installed clock already changed the public model's base import. Trim the
# actual current base, preserving the approved clock's separate render import.
public=ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl'
source=ROOT/'Assets/models/maps/railhead/clock-v1/dressing_without_clock.obj'
assert 'models/maps/railhead/clock-v1/dressing_without_clock.obj' in public.read_text()
legacy=K.Model();D.loudspeaker(legacy,7.7,820.,214.,'+e');R.configure(legacy)
K.write_obj(OUT/'legacy-speaker.obj',legacy,'legacy_speaker')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-speaker.obj');wanted=collections.Counter(key for _,key in old)
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved speaker differs from helper: inspect before staging'
(MODEL/'centre_without_speaker.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib dressing_without_clock.mtl','mtllib centre_without_speaker.mtl'))
(MODEL/'centre_without_speaker.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'centre_without_speaker.vmdl').write_text(public.read_text().replace('models/maps/railhead/clock-v1/dressing_without_clock.obj',RES+'/centre_without_speaker.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/clock-v1/import.cs.txt').read_text().replace('output/railhead/clock-v1','output/railhead/pa-speaker-v1').replace('maps/railhead/clock-v1/','maps/railhead/pa-speaker-v1/').replace('materials/railhead/clock-v1/','materials/railhead/pa-speaker-v1/')
(HERE/'import.cs.txt').write_text(template,encoding='utf-8')
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files))))
