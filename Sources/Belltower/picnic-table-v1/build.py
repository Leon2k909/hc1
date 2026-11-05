"""One beer-garden picnic table, preserving the live town's bounded imports."""
from pathlib import Path
import sys,math,json,hashlib,collections,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as R
import belltower_furniture as F
import railhead_dress_detail as D
OUT=ROOT/'output/belltower/picnic-table-v1';STAGE=OUT/'stage'
RES='models/maps/belltower/picnic-table-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
public=ROOT/'Assets/models/maps/belltower/belltower_west.vmdl';original=public.read_text()
imports=re.findall(r'filename = "([^"]+\.obj)"',original)
guard_paths=[public,ROOT/'Assets/models/maps/belltower/belltower_west.obj',ROOT/'Assets/scenes/maps/Belltower/belltower.scene',ROOT/'Tools/belltower_map.py',ROOT/'Tools/belltower_furniture.py']+[ROOT/'Assets'/p for p in imports]
shared_mtl=ROOT/'Assets/models/maps/belltower/compiler-safe/west/materials.mtl';guard_paths.append(shared_mtl)
for name in ('wood_planks','wood_planks_dark'):
 mat=ROOT/f'Assets/materials/belltower/{name}.vmat';guard_paths.append(mat)
 guard_paths.extend(ROOT/'Assets'/p for p in re.findall(r'Texture\w+ "([^\"]+\.png)"',mat.read_text()))
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in dict.fromkeys(guard_paths)}
guard_file=OUT/'source-guard.json'
if guard_file.exists():
 pinned=json.loads(guard_file.read_text());assert all(sha(ROOT/p)==h for p,h in pinned.items()),'Original guarded source changed'
 guard={**guard,**pinned}
guard_file.write_text(json.dumps(guard,indent=2))
m=K.Model();p=R.Place((-800.,-600.,0.),90.);X,Y,Z=p.x,p.y,p.z
def P(x,y,z):return p.at((x,y,z))
def board(c,size,paint=F.WOOD,seed=0,b=.16):F.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b,seed=seed)
def endgrain(x,y,z,w,h):
 for s in (-1,1):
  pts=[P(s*x,y-w/2,z-h/2),P(s*x,y+w/2,z-h/2),P(s*x,y+w/2,z+h/2),P(s*x,y-w/2,z+h/2)]
  D._face(m,'cut',pts,X*s,uv=[(0,0),(w/12,0),(w/12,h/12),(0,h/12)])
# Individual eased boards with real gaps and exposed end grain.
gap=.25;w=(32.-5*gap)/6
for k in range(6):
 y=-16+w/2+k*(w+gap)
 board((0,y,28.7),(84,w,2.6),seed=k+2,b=.17)
 endgrain(42.012,y,28.7,w-.34,2.25)
 for x in (-29.5,29.5):F.bolt(m,P(x,y,30.015),Z,.19)
for s in (-1,1):
 for k in range(2):
  y=s*30+(k-.5)*6.2
  board((0,y,16.75),(84,5.8,2.5),seed=k+12+(s+1)*3,b=.18)
  endgrain(42.012,y,16.75,5.45,2.14)
  for x in (-29.5,29.5):F.bolt(m,P(x,y,18.015),Z,.21)
# Flat-cut, chamfered legs: open A frames rather than solid timber walls.
def inset(poly,amount):
 result=[]
 for a,b,c in zip(poly[-1:]+poly[:-1],poly,poly[1:]+poly[:1]):
  e0=b-a;e1=c-b;n0=np.array((-e0[1],e0[0]))/np.linalg.norm(e0);n1=np.array((-e1[1],e1[0]))/np.linalg.norm(e1)
  result.append(np.linalg.solve(np.array((n0,n1)),np.array((np.dot(n0,b)+amount,np.dot(n1,b)+amount))))
 return result
def leg(x,s,seed):
 foot=s*26.;top=s*10.;profile=[np.array(q,float) for q in ((foot-2.7,0),(foot+2.7,0),(top+2.7,27.35),(top-2.7,27.35))]
 inner=inset(profile,.14)
 rings=[[P(xx,*q) for q in shape] for xx,shape in ((x-1.9,inner),(x-1.75,profile),(x+1.75,profile),(x+1.9,inner))]
 centre=P(x,(foot+top)/2,13.675);axis=K.normalise(Y*(top-foot)+Z*27.35);cross=K.normalise(np.cross(X,axis))
 u0,u1=F.STRIPS[seed%9]
 def face(points,normal):
  uv=[(u0+(np.dot(q-centre,cross)/4.7+.5)*(u1-u0),np.dot(q-centre,axis)/F.TILE+.31*seed) for q in points]
  D._face(m,F.DARK,points,normal,uv=uv)
 for j in range(3):
  for k in range(4):
   kk=(k+1)%4;pts=[rings[j][k],rings[j][kk],rings[j+1][kk],rings[j+1][k]]
   face(pts,np.mean(pts,axis=0)-centre-X*np.dot(np.mean(pts,axis=0)-centre,X))
 face(rings[0],-X);face(rings[-1],X)
for x in (-29.5,29.5):
 for s in (-1,1):leg(x,s,int(x+40)+(s+1)*3)
 board((x,0,26.25),(3.8,33.,2.3),F.DARK,seed=int(x+42),b=.15)
 board((x,0,13.85),(3.8,71.4,3.3),F.DARK,seed=int(x+44),b=.18)
 for side in (-1,1):
  for s in (-1,1):
   y=s*(26.-16.*13.85/27.35)
   F.bolt(m,P(x+side*1.93,y,13.85),X*side,.34)
  for y in (-12.8,12.8):F.bolt(m,P(x+side*1.93,y,26.2),X*side,.28)
# Long stretcher and knee braces connect the two end frames.
board((0,0,9.4),(62.8,3.3,3.5),F.DARK,seed=51,b=.17)
for s in (-1,1):
 F.beam(m,P(s*28.0,0,25.0),P(s*4.0,0,11.2),(2.6,2.6),F.DARK,.15,seed=55+(s+1))
 for x,z in ((s*27.,24.3),(s*5.,11.8)):
  for side in (-1,1):F.bolt(m,P(x,side*1.33,z),Y*side,.25)
# Existing scanned wood finish. Undo its legacy shader UV multiplier so the
# furniture helper's seam-free photographed strips remain seam-free.
m.material_overrides={F.WOOD:'materials/belltower/wood_planks.vmat',F.DARK:'materials/belltower/wood_planks_dark.vmat',F.IRON:'materials/buildings/iron_black.vmat','cut':'materials/gunsmith_range/bench_oak_endgrain.vmat'}
for key,uv in list(m.polygon_uvs.items()):
 if key[0] in (F.WOOD,F.DARK):m.polygon_uvs[key]=[(u/1.2192,v/1.2192) for u,v in uv]
m.tile_overrides={paint:32 for paint in m.polygons}
count=K.write_model(MODEL,RES,'picnic_table',m)
legacy=K.Model();R.picnic_table(legacy,(-800.,-600.),90.);R.Detail.configure(legacy,render=True)
K.write_obj(OUT/'legacy-table.obj',legacy,'legacy_table')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-table.obj');wanted=collections.Counter(key for _,key in old)
sources={};text=original;total=0
for source_path in imports:
 if not re.search(r'west_\d+_planks(?:_dark)?\.obj$',source_path):continue
 source=ROOT/'Assets'/source_path;lines,faces=records(source);removed=set()
 for i,key in faces:
  if wanted[key]:removed.add(i);wanted[key]-=1
 if not removed:continue
 name='base_dark' if '_dark.' in source.name else 'base_wood'
 # Preserve all records except the precisely matched legacy faces.
 content=''.join(l for i,l in enumerate(lines) if i not in removed)
 content=re.sub(r'(?m)^mtllib .+$',f'mtllib {name}.mtl',content)
 (MODEL/f'{name}.obj').write_text(content);(MODEL/f'{name}.mtl').write_bytes(shared_mtl.read_bytes())
 text=text.replace(source_path,RES+'/'+name+'.obj');sources[name]=dict(path=str(source.relative_to(ROOT)),removed=len(removed));total+=len(removed)
assert not +wanted,'Installed table differs from its source helper; inspect before staging'
assert total==60,total
(MODEL/'west_without_table.vmdl').write_text(text)
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=total,sources=sources,review_only=True),indent=2))
template=(ROOT/'Sources/ReefHall/office-chair-v1/import.cs.txt').read_text().replace('reefhall/office-chair-v1','belltower/picnic-table-v1')
(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=total,files=len(files),sources=sources)))
