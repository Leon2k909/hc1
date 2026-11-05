"""Stack individual facing bricks on a serviceable timber pallet."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
import belltower_furniture as F
OUT=ROOT/'output/railhead/brick-pallet-v1';STAGE=OUT/'stage';RES='models/maps/railhead/brick-pallet-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_dress_detail.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'brick-pallet-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
m=K.Model();frame=D.Frame(1884.,-1580.,.3,'+n');X,Y,Z=frame.x,frame.y,frame.z
def P(x,y,z):return frame.p(x,y,z)
def wood(c,size,seed):F.bevel_box(m,P(*c),(X,Y,Z),size,F.WOOD,bevel=.10,seed=seed)
def box(c,size,paint,b=.04):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
# Three bottom runners, nine bearing blocks, cross bearers and seven deck boards.
for i,x in enumerate((-15.4,0.,15.4)):
 wood((x,0,.425),(4.8,47.2,.85),i+1)
 for j,y in enumerate((-18.3,0.,18.3)):wood((x,y,2.15),(4.8,6.,2.60),i*3+j+6)
for j,y in enumerate((-18.3,0.,18.3)):wood((0,y,3.625),(39.4,5.,.35),j+20)
for k,x in enumerate(np.linspace(-17.3,17.3,7)):
 wood((x,0,4.25),(4.8,47.2,.9),k+30)
 for y in (-18.3,0.,18.3):
  for dx in (-1.25,1.25):D.disc(m,'steel',P(x+dx,y,4.71),Z,.075,10)
# UV patches lie inside the existing dressed-red image's individual blocks,
# excluding its photographed mortar lines. The material/textures are unchanged.
patches=((.03,.03,.20,.18),(.27,.03,.56,.18),(.62,.04,.82,.18),(.03,.24,.36,.38),(.42,.24,.66,.38),(.73,.25,.94,.38),(.05,.44,.21,.56),(.27,.44,.55,.56),(.62,.44,.94,.56))
def brick(x,y,z,turn,seed,top=False):
 axes=(X,Y,Z) if not turn else (Y,-X,Z);size=np.array((9.4,4.6,2.64));centre=P(x,y,z)
 u0,v0,u1,v1=patches[seed%len(patches)]
 def uv(points,normal):
  nn=np.array([np.dot(normal,a) for a in axes]);dominant=int(np.argmax(np.abs(nn)));a,b=[i for i in range(3) if i!=dominant]
  return [(u0+(np.dot(q-centre,axes[a])/size[a]+.5)*(u1-u0),v0+(np.dot(q-centre,axes[b])/size[b]+.5)*(v1-v0)) for q in points]
 start=len(m.polygons['brick'])
 G.bevel_box(m,centre,axes,size,'brick',bevel=.075,skip=('+z',) if top else ())
 for index in range(start,len(m.polygons['brick'])):
  points,normal=m.polygons['brick'][index];m.polygon_uvs[('brick',index)]=uv(points,normal)
 if top:
  # A true recessed frog in each top brick, with sloping walls and a floor.
  def at(a,b,h):return centre+axes[0]*a+axes[1]*b+Z*h
  outer=[(-4.625,-2.225),(4.625,-2.225),(4.625,2.225),(-4.625,2.225)]
  opening=[(-3.30,-1.15),(3.30,-1.15),(3.30,1.15),(-3.30,1.15)]
  bottom=[(-3.05,-.90),(3.05,-.90),(3.05,.90),(-3.05,.90)]
  def face(points,normal):D._face(m,'brick',points,normal,uv=uv(points,normal))
  for k in range(4):
   j=(k+1)%4
   face([at(*outer[k],1.32),at(*outer[j],1.32),at(*opening[j],1.32),at(*opening[k],1.32)],Z)
   points=[at(*opening[k],1.32),at(*opening[j],1.32),at(*bottom[j],.82),at(*bottom[k],.82)]
   middle=(np.array(opening[k])+np.array(opening[j]))/2;hint=-axes[0]*middle[0]-axes[1]*middle[1]+Z*.5
   face(points,hint)
  face([at(a,b,.82) for a,b in bottom],Z)
count_bricks=0
for row in range(13):
 turn=row%2;nx,ny=(4,10) if not turn else (8,5);stepx,stepy=(9.54,4.68) if not turn else (4.72,9.44)
 for ix in range(nx):
  for iy in range(ny):
   x=(ix-(nx-1)/2)*stepx;y=(iy-(ny-1)/2)*stepy
   brick(x,y,4.7+row*2.72+1.32,turn,row*47+ix*13+iy*7,top=row==12);count_bricks+=1
# Thin strapping wraps the brick stack and passes below the timber deck.
def band(fixed,along_y=True,layer=0.):
 span=23.60 if along_y else 19.25;top=40.06+layer
 path=[(-span,4.3),(-span,top-.45),(-span+.45,top),(span-.45,top),(span,top-.45),(span,4.3),(span-.45,3.92),(-span+.45,3.92)]
 def at(w,a,z):return P(fixed+w,a,z) if along_y else P(a,fixed+w,z)
 axis=Y if along_y else X
 for (a,z),(b,zz) in zip(path,path[1:]+path[:1]):
  hint=axis*(-(zz-z))+Z*(b-a)
  D._face(m,'strap',[at(-.38,a,z),at(.38,a,z),at(.38,b,zz),at(-.38,b,zz)],hint)
for x in (-9.6,9.6):
 band(x)
 box((x,0,40.13),(1.05,2.1,.12),'steel',.025)
 for y in (-.78,.78):box((x,y,40.205),(.75,.08,.035),'strap',.008)
for y in (-11.5,11.5):band(y,False,.035)
m.material_overrides={F.WOOD:'materials/railhead/rw_wood.vmat','brick':'materials/railhead/rw_dressed_red.vmat','strap':'materials/railhead/rw_black.vmat','steel':'materials/railhead/rw_steel_dark.vmat'}
m.tile_overrides={paint:32 for paint in m.polygons};count=K.write_model(MODEL,RES,'brick_pallet',m)
legacy=K.Model();D.brick_pallet(legacy,1884.,-1580.,.3,'n');R.configure(legacy);K.write_obj(OUT/'legacy-pallet.obj',legacy,'legacy_pallet')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-pallet.obj');wanted=collections.Counter(key for _,key in old)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl';text=public.read_text();source=ROOT/'Assets/models/maps/railhead/cable-drum-v1/east_without_drum.obj'
assert 'models/maps/railhead/cable-drum-v1/east_without_drum.obj' in text
lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Installed pallet differs from its helper'
content=''.join(l for i,l in enumerate(lines) if i not in removed);content=re.sub(r'(?m)^mtllib .+$','mtllib east_without_pallet.mtl',content)
(MODEL/'east_without_pallet.obj').write_text(content);(MODEL/'east_without_pallet.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'east_without_pallet.vmdl').write_text(text.replace('models/maps/railhead/cable-drum-v1/east_without_drum.obj',RES+'/east_without_pallet.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),bricks=count_bricks,review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/road-barrier-v1/import.cs.txt').read_text().replace('road-barrier-v1','brick-pallet-v1');(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),bricks=count_bricks,files=len(files),existing_materials_reused=True)))
