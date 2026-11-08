"""Replace Orion's four flush cards with an actually recessed service facade."""
from pathlib import Path
import sys,json,re,hashlib,collections,shutil,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,orion_map as O,riverdale_parts as G,railhead_dress_detail as D
OUT=ROOT/'output/orion/undercroft-facade-v1';STAGE=OUT/'stage/Assets';RES='models/props/orion/undercroft_facade_v1';MAT='materials/orion/undercroft_facade_v1';DEST=STAGE/RES;MD=STAGE/MAT
DEST.mkdir(parents=True,exist_ok=True);MD.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'Assets/models/maps/orion/orion_launch_deck.obj';docpath=source.with_suffix('.vmdl');doc=docpath.read_text();assert 'filename = "models/maps/orion/orion_launch_deck.obj"' in doc
lines=source.read_text().splitlines(keepends=True)
def records(lines):
 v=[];uv=[];ns=[];paint='';rows=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(map(float,s[1:])))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':ns.append(tuple(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':
   indices=[tuple(int(k)-1 for k in t.split('/')) for t in s[1:]];points=tuple(v[a] for a,b,c in indices)
   key=(paint,tuple(sorted(tuple(round(x,3) for x in p) for p in points)))
   rows.append((i,key,points,[uv[b] for a,b,c in indices],[ns[c] for a,b,c in indices]))
 return rows
# Exact current-baseline signatures: four 0.1-inch boxes, and only the front
# two triangles of the concrete mass. All other mass surfaces remain intact.
expected=K.Model()
for k,e in enumerate((-500.,-380.,-250.,-130.)):O.box(expected,e-30,e+30,899.9,900,10,96,'oa_window_lit' if k%2 else 'oa_door')
O.configure(expected);K.write_obj(OUT/'expected-cards.obj',expected,'cards')
wanted=collections.Counter(r[1] for r in records((OUT/'expected-cards.obj').read_text().splitlines()))
saved=records(lines);cut=[];wall=[]
for row in saved:
 i,key,points,uv,ns=row
 if wanted[key]:wanted[key]-=1;cut.append(i)
 elif key[0] in ('oa_wall','oa_wall_dark') and all(abs(p[2]-900)<.001 for p in points) and set(points).issubset({(560.,0.,900.),(-180.,0.,900.),(-180.,240.,900.),(560.,240.,900.)}):wall.append(row);cut.append(i)
assert not +wanted and len(wall)==2 and len(cut)==50,dict(unmatched=sum((+wanted).values()),wall=len(wall),cut=len(cut))
cutset=set(cut);(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cutset))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile(source.parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace('models/maps/orion/orion_launch_deck.obj',RES+'/preview.obj'))
# Fit the original front wall's actual UVs so its texture remains fixed outside holes.
fitp=[];fituv=[]
for i,key,pts,uv,ns in wall:
 for p,t in zip(pts,uv):fitp.append((-p[0],p[1],1));fituv.append(t)
uvfit=np.linalg.lstsq(np.array(fitp),np.array(fituv),rcond=None)[0];m=K.Model();X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1))
def q(x,d,z):return np.array((x,900-d,z),float)
def face(paint,pts,hint,uv=None):D._face(m,paint,pts,hint,uv=uv)
def rect(paint,x0,x1,d,z0,z1):face(paint,[q(x0,d,z0),q(x1,d,z0),q(x1,d,z1),q(x0,d,z1)],Y)
def box(c,size,paint='door',b=.15):G.bevel_box(m,q(*c),(X,Y,Z),size,paint,bevel=b)
def turn(c,axis,profile,paint='alloy',sides=24):G.lathe_axis(m,q(*c),axis,profile,paint,sides=sides)
holes=[(e-32,e+32,0.,98.) if j%2==0 else (e-32,e+32,28.,96.) for j,e in enumerate((-500.,-380.,-250.,-130.))]
zcuts=sorted({0.,240.,*[z for a,b,c,d in holes for z in (c,d)]})
for z0,z1 in zip(zcuts,zcuts[1:]):
 spans=sorted((a,b) for a,b,c,d in holes if c<=(z0+z1)/2<=d);cursor=-560.
 for a,b in spans+[(180.,180.)]:
  if a>cursor:
   pts=[q(cursor,0,z0),q(a,0,z0),q(a,0,z1),q(cursor,0,z1)]
   face(wall[0][1][0],pts,Y,uv=[np.array((p[0],p[2],1))@uvfit for p in pts])
  cursor=max(cursor,b)
# Actual reveal surfaces run eight inches back from the new openings.
for x0,x1,z0,z1 in holes:
 face('oa_wall_dark',[q(x0,0,z0),q(x0,-8,z0),q(x0,-8,z1),q(x0,0,z1)],X)
 face('oa_wall_dark',[q(x1,-8,z0),q(x1,0,z0),q(x1,0,z1),q(x1,-8,z1)],-X)
 face('oa_wall_dark',[q(x0,0,z1),q(x0,-8,z1),q(x1,-8,z1),q(x1,0,z1)],-Z)
 if z0:face('oa_wall_dark',[q(x0,-8,z0),q(x0,0,z0),q(x1,0,z0),q(x1,-8,z0)],Z)
# Reuse accepted powder-coat, rubber and metal finishes from the service cabinet.
for cx in (-500.,-250.):
 # Continuous dark stop behind the leaves seals head, meeting stile and threshold gaps.
 box((cx,-9.15,49),(61.,.22,96.),'rubber',.10)
 # Projecting folded steel architrave, deep jamb returns, weather seals and threshold.
 for x in (cx-31,cx+31):box((x,-3.5,49),(2.,10.,98.),'frame',.18)
 box((cx,-3.5,97),(64.,10.,2.),'frame',.18);box((cx,-3.5,.65),(64.,10.,1.3),'alloy',.12)
 for x in (cx-29.9,cx+29.9):box((x,-7.5,48),(1.,.4,94.),'rubber',.10)
 for s in (-1,1):
  mid=cx+s*14.8
  box((mid,-8.,48.3),(29.3,1.8,93.6),'door',.2)
  # Folded edges, a narrow centre seam, and a fixed lower kick plate.
  box((mid,-7.04,12),(27.,.12,18.),'frame',.12)
  for z in (4.5,19.5):
   for dx in (-11.,11.):turn((mid+dx,-6.95,z),Y,[(0,0),(.14,0),(.14,.07),(0,.07)],sides=16)
  for z in (17.,48.,80.):
   hx=cx+s*29.3
   box((hx,-6.65,z),(1.8,.28,4.4),'alloy',.10)
   for dz in (-1.5,0,1.5):turn((hx,-6.35,z+dz-.60),Z,[(0,0),(.38,0),(.38,1.2),(0,1.2)],'alloy',24)
  # Lever with a return toward the leaf, key barrel and escutcheon.
  hx=cx+s*3.8;box((hx,-6.95,43),(2.5,.20,8.),'alloy',.22)
  turn((hx,-6.7,45),Y,[(0,0),(.58,0),(.58,.70),(0,.70)],'alloy',24)
  G.tube(m,[q(hx,-6.,45),q(hx+s*4.0,-6.,45),q(hx+s*4.6,-6.45,45)],.32,'alloy',sides=16,bend_radius=.3)
  turn((hx,-6.78,41),Y,[(0,0),(.35,0),(.35,.14),(0,.14)],'alloy',24)
  box((hx,-6.61,41),(.07,.025,.32),'rubber',.01)
 # Small, restrained identification plate above the leaf's working area.
 box((cx+14.8,-6.96,70),(17.,.12,4.7),'frame',.1)
 face('label',[q(cx+7.,-6.86,68),q(cx+22.6,-6.86,68),q(cx+22.6,-6.86,72),q(cx+7.,-6.86,72)],Y,uv=[(0,0),(1,0),(1,1),(0,1)])
# Recessed industrial glazing with real mullions and a shallow enclosed utility room.
for cx in (-380.,-130.):
 box((cx,-3.5,26),(70.,15.,4.),'oa_wall_dark',.4)
 for x in (cx-30,cx+30):box((x,-7.,62),(2.,2.2,66.),'frame',.12)
 for z in (30.,94.):box((cx,-7.,z),(62.,2.2,2.),'frame',.12)
 box((cx,-6.7,62),(1.5,2.5,62.),'frame',.1);box((cx,-6.7,62),(58.,2.5,1.5),'frame',.1)
 for x0,x1 in ((cx-29,cx-.8),(cx+.8,cx+29)):
  for z0,z1 in ((31,61.2),(62.8,93)):
   rect('glass',x0,x1,-8.25,z0,z1)
   face('glass',[q(x0,-8.28,z0),q(x0,-8.28,z1),q(x1,-8.28,z1),q(x1,-8.28,z0)],-Y)
 # A real back, side walls, floor and ceiling occupy the depth visible through the window.
 rect('oa_wall_dark',cx-32,cx+32,-48,28,100)
 face('oa_wall_dark',[q(cx-32,-8,28),q(cx-32,-48,28),q(cx-32,-48,100),q(cx-32,-8,100)],X)
 face('oa_wall_dark',[q(cx+32,-48,28),q(cx+32,-8,28),q(cx+32,-8,100),q(cx+32,-48,100)],-X)
 for z,hint in ((28,Z),(100,-Z)):face('oa_wall_dark',[q(cx-32,-8,z),q(cx+32,-8,z),q(cx+32,-48,z),q(cx-32,-48,z)],hint)
 box((cx-16,-42,58),(22.,10.,56.),'door',.2)
 for x in (cx-27,cx-5):box((x,-36.8,58),(.4,.3,52.),'frame',.05)
 box((cx-7,-36.6,57),(.5,.8,6.),'alloy',.1)
 for z in (45,64,82):box((cx+17,-38,z),(23.,14.,1.),'frame',.1)
 for j in range(3):box((cx+10+j*7,-38,52+j*4),(5.,7.,10.+j*3),'door',.1)
 box((cx,-25,97),(26.,8.,2.),'frame',.15)
 box((cx,-25,95.8),(23.,5.,.4),'oa_lamp_warm',.1)
O.configure(m)
shared='materials/spillway/service-cabinet-v1/'
m.material_overrides.update(door=shared+'door.vmat',frame=shared+'body.vmat',rubber=shared+'rubber.vmat',alloy=shared+'alloy.vmat',glass='materials/railhead/rw_glass.vmat',label=MAT+'/label.vmat')
for p in ('door','frame','rubber','alloy'):m.tile_overrides[p]=36.
image=Image.new('RGB',(1024,256),(35,43,45));d=ImageDraw.Draw(image);font=ROOT/'Assets/fonts/Dinish-Bold.ttf';d.text((512,128),'PLANT / SERVICE',font=ImageFont.truetype(str(font),95),fill=(202,208,200),anchor='mm');image.save(MD/'label.png')
(MD/'label.vmat').write_text('Layer0\n{\n shader "shaders/complex.shader"\n TextureColor "'+MAT+'/label.png"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[0.65 0.65 0.65 0]"\n g_flMetalness "0"\n}\n')
K.write_obj(DEST/'facade.obj',m,'facade');K.write_vmdl(DEST/'facade.vmdl',RES,'facade',m)
protected=[source,docpath,ROOT/'Assets/scenes/maps/Orion/orion.scene',font]
protected.extend(ROOT/'Assets'/p for p in re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc))
for path in set(m.material_overrides.values()):
 p=ROOT/'Assets'/path
 if not p.is_file():continue
 protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  t=ROOT/'Assets'/texture
  if t.is_file():protected.append(t)
manifest=dict(review_only=True,original_faces_removed=50,old_flat_cards_removed=48,old_wall_faces_removed=2,triangles=m.triangle_count(),cut=cut,holes=holes,interior_lights=[dict(position=[926.,380.,90.],color=[.9,.82,.65],radius=90),dict(position=[926.,130.,90.],color=[.9,.82,.65],radius=90)],protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('cut','protected','files')}))
