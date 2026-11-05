"""A detailed swivel chair in the upper office, staged independently of the map."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
OUT=ROOT/'output/reefhall/office-chair-v1';STAGE=OUT/'stage'
RES='models/maps/reefhall/office-chair-v1';MAT='materials/reefhall/office-chair-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/reefhall').rglob('*'))+list((ROOT/'Assets/materials/reefhall').rglob('*'))+[ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene',ROOT/'Tools/reefhall_map.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'office-chair-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('polymer',(.052,.062,.068),.57,0.),('steel',(.39,.42,.44),.32,.85),('rubber',(.024,.027,.027),.85,0.)]:
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
m=K.Model();X=np.array((-1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.));C=np.array((1960.,806.,208.))
def P(x,y,z):return C+X*x+Y*y+Z*z
def box(c,size,paint='polymer',bevel=.12):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=bevel)
def cyl(c,axis,prof,paint='steel',sides=24):G.lathe_axis(m,P(*c),axis,prof,paint,sides=sides)
def rod(c,axis,length,r,paint='steel',sides=20):cyl(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def outline(w,d,r,steps=8):
 pts=[]
 for cx,cy,a0 in ((w/2-r,d/2-r,0),(-w/2+r,d/2-r,math.pi/2),(-w/2+r,-d/2+r,math.pi),(w/2-r,-d/2+r,3*math.pi/2)):
  for a in np.linspace(a0,a0+math.pi/2,steps+1):pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
 return pts
def loft(rings,paint):
 n=len(rings[0]);vertices=[p for ring in rings for p in ring];centres=[np.mean(ring,axis=0) for ring in rings];tri=[]
 for j in range(len(rings)-1):
  for k in range(n):
   a=j*n+k;b=j*n+(k+1)%n;c=(j+1)*n+(k+1)%n;d=(j+1)*n+k
   hint=(vertices[a]+vertices[b]+vertices[c]+vertices[d])/4-(centres[j]+centres[j+1])/2
   tri.extend(((a,b,c,hint),(a,c,d,hint)))
 for j,normal in ((0,centres[0]-centres[1]),(len(rings)-1,centres[-1]-centres[-2])):
  idx=len(vertices);vertices.append(centres[j])
  for k in range(n):tri.append((idx,j*n+k,j*n+(k+1)%n,normal))
 accum=[np.zeros(3) for _ in vertices];faces=[]
 for a,b,c,hint in tri:
  normal=K.normalise(np.cross(vertices[b]-vertices[a],vertices[c]-vertices[a]))
  if np.dot(normal,hint)<0:normal=-normal
  for i in (a,b,c):accum[i]+=normal
  faces.append((a,b,c,normal))
 for a,b,c,normal in faces:D._face(m,paint,[vertices[i] for i in (a,b,c)],normal,normals=[K.normalise(accum[i]) for i in (a,b,c)])
# Rounded, subtly crowned upholstery keeps the existing map's finish.
seat=[(15.8,16.6,14.8,2.0),(16.3,17.7,16.1,2.4),(17.5,18.,16.5,2.6),(18.8,17.6,16.0,2.5),(19.15,16.5,14.8,2.2)]
loft([[P(x,y,z) for x,y in outline(w,d,r)] for z,w,d,r in seat],'upholstery')
box((0,-.2,15.4),(15.5,13.0,1.2),'polymer',.35)
seam=[P(x,y,17.7) for x,y in outline(18.05,16.55,2.6)];D.tube(m,seam+[seam[0]],.035,'rubber',sides=6)
def back_surface(x,z):return -8.25+1.00*(x/8.8)**2+.65*math.exp(-((z-24.)/3.5)**2)
# Curved rear shell and padded front, with a wrapped lumbar contour.
shell=[]
for depth,w,h,r in ((-1.85,16.7,15.4,2.2),(-1.65,18.0,17.0,2.6),(-1.15,18.0,17.0,2.6),(-1.0,17.6,16.6,2.5)):
 shell.append([P(x,back_surface(x,27.4+z)+depth,27.4+z) for x,z in outline(w,h,r)])
loft(shell,'polymer')
back=[]
for depth,w,h,r in ((-.98,16.9,16.0,2.3),(-.45,17.7,16.4,2.5),(.40,17.6,16.2,2.5),(.62,16.4,15.1,2.2)):
 back.append([P(x,back_surface(x,27.4+z)+depth,27.4+z) for x,z in outline(w,h,r)])
loft(back,'upholstery')
for s in (-1,1):
 G.tube(m,[P(s*4.7,-5.7,15.15),P(s*4.7,-10.0,17.1),P(s*4.7,-10.0,31.0)],.43,'polymer',sides=12,bend_radius=.8)
 for z in (22.5,29.2):
  yy=back_surface(s*4.7,z)-1.90
  rod((s*4.7,-10.,z),Y,yy+10.05,.30,'polymer',16)
  rod((s*4.7,yy,z),-Y,.06,.26,'steel',16)
  box((s*4.7,yy-.067,z),(.24,.018,.045),'rubber',.006)
 # Adjustable arm supports and contoured polymer pads.
 box((s*8.3,-.4,15.1),(3.3,3.0,.8),'polymer',.20)
 box((s*9.55,-.4,20.2),(1.25,1.6,9.4),'polymer',.25)
 loft([[P(s*10.0+x,y-.2,z) for x,y in outline(w,d,r,6)] for z,w,d,r in ((24.6,2.1,9.7,.85),(24.95,2.6,10.1,1.0),(25.7,2.5,9.7,1.0),(25.9,1.9,8.8,.8))],'polymer')
 # The telescoping arm's release button is a separate inset.
 box((s*10.20,-.4,22.1),(.06,.65,1.2),'rubber',.02)
# Tilt mechanism, adjustment lever and gas lift below the cushion.
box((0,.2,13.9),(5.4,7.8,2.0),'polymer',.35)
G.tube(m,[P(-2.3,1.2,14.),P(-7.0,1.2,13.2),P(-9.,1.2,13.2)],.13,'steel',sides=10,bend_radius=.35)
box((-9.2,1.2,13.3),(2.9,.9,.72),'polymer',.25)
rod((0,0,6.5),Z,6.5,.67,'steel',32)
cyl((0,0,3.8),Z,[(0,0),(1.35,0),(1.5,.35),(1.20,.70),(1.20,4.5),(1.07,4.8),(0,4.8)],'polymer',32)
for z in (6.5,7.2,7.9):G.torus(m,P(0,0,z),Z,1.19,.065,'rubber',seg=32,sides=6)
cyl((0,0,2.9),Z,[(0,0),(2.20,0),(2.35,.45),(2.20,1.7),(1.4,2.1),(0,2.1)],'polymer',40)
# Five swept feet terminate in swivel forks and twin rolling casters.
for k in range(5):
 angle=math.tau*k/5+.20;dx,dy=math.cos(angle),math.sin(angle)
 a=P(dx*1.8,dy*1.8,4.5);b=P(dx*9.0,dy*9.0,3.0)
 direction=K.normalise(b-a);side=K.normalise(np.cross(Z,direction));up=np.cross(direction,side)
 G.bevel_box(m,(a+b)/2,(direction,side,up),(np.linalg.norm(b-a)+.3,1.65,1.1),'polymer',bevel=.32)
 xx,yy=dx*9.0,dy*9.0
 rod((xx,yy,2.2),Z,1.4,.28,'steel',16)
 yaw=angle+.43+.18*math.sin(k*3.);ax=X*math.cos(yaw)+Y*math.sin(yaw);out=np.cross(Z,ax)
 centre=P(xx,yy,1.35)
 G.bevel_box(m,centre+Z*1.18,(ax,out,Z),(1.7,1.35,.60),'polymer',bevel=.18)
 for s in (-1,1):
  q=centre+ax*s*.58
  G.lathe_axis(m,q,ax*s,[(0,0),(1.10,0),(1.34,.12),(1.35,.48),(1.20,.62),(0,.62)],'rubber',sides=28)
  G.lathe_axis(m,q+ax*s*.63,ax*s,[(0,0),(.53,0),(.53,.06),(0,.06)],'polymer',sides=24)
  G.lathe_axis(m,q+ax*s*.70,ax*s,[(0,0),(.17,0),(.17,.035),(0,.035)],'steel',sides=16)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('polymer','steel','rubber')}
m.material_overrides['upholstery']='materials/reefhall/rh_pad_dark.vmat'
m.tile_overrides={p:32 for p in m.polygons};m.tile_overrides['upholstery']=R.RM.paints()['rh_pad_dark'][1]
count=K.write_model(MODEL,RES,'office_chair',m)
# Match just the three legacy chair boxes, leaving the desk and its screens intact.
legacy=K.Model();fr=R.Frame((1960.,780.),(-1.,0.));z=R.L1
R.fbox(legacy,fr,-9,9,-34,-18,z+16,z+19,'rh_pad_dark')
R.fbox(legacy,fr,-9,9,-36,-33,z+19,z+36,'rh_pad_dark')
R.fbox(legacy,fr,-1.5,1.5,-27.5,-24.5,z,z+16,'rh_gunmetal');R.configure(legacy)
K.write_obj(OUT/'legacy-chair.obj',legacy,'legacy_chair')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-chair.obj');wanted=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/reefhall/reefhall_control.obj';lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved office chair differs from helper; inspect before staging'
(MODEL/'control_without_chair.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib reefhall_control.mtl','mtllib control_without_chair.mtl'))
(MODEL/'control_without_chair.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'control_without_chair.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/reefhall/reefhall_control.obj',RES+'/control_without_chair.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/ReefHall/server-rack-v1/import.cs.txt').read_text().replace('server-rack-v1','office-chair-v1')
(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files),casters=5)))
