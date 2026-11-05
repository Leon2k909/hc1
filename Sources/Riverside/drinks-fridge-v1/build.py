"""Replace one flat-picture porch fridge with a stocked glass-door assembly."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_map as R
import riverside_parts as RP
import riverdale_parts as G
import railhead_dress_detail as D
OUT=ROOT/'output/riverside/drinks-fridge-v1';STAGE=OUT/'stage'
RES='models/maps/riverside/drinks-fridge-v1';MAT='materials/riverside/drinks-fridge-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/riverside').rglob('*'))+list((ROOT/'Assets/materials/riverside').rglob('*'))+[ROOT/'Assets/scenes/maps/Riverside/riverside.scene',ROOT/'Tools/riverside_map.py',ROOT/'Tools/riverside_parts.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'drinks-fridge-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
colours=[('enamel',(.63,.62,.54),.54,.05),('liner',(.76,.79,.77),.56,0.),('frame',(.050,.057,.057),.52,.18),('steel',(.47,.51,.52),.31,.85),('red',(.54,.037,.027),.4,.15),('blue',(.035,.13,.37),.4,.15),('green',(.06,.26,.095),.34,.04),('label',(.82,.78,.65),.62,0.)]
for name,colour,rough,metal in colours:
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
(MATERIAL/'glass.vmat').write_text('''"Layer0"
{
 shader "shaders/glass.shader"
 F_GLASS_QUALITY "2"
 g_bFogEnabled "1"
 g_flBlurAmount "0"
 g_flRefractionStrength "1.002"
 AlbedoAbsorption "0.025"
 g_flTintColor "[1 1 1 0]"
 TextureColor "[0.985 0.99 0.985 0]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.065 0.065 0.065 0]"
 TextureMetalness "[0 0 0 0]"
 TextureAmbientOcclusion "[1 1 1 0]"
 TextureBlendMask "materials/default/default_blend.tga"
 TextureTintMask "materials/default/default.tga"
 TextureTranslucency "materials/default/default_trans.tga"
}
''',encoding='utf-8')
m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.));C=np.array((96.,624.,20.))
def P(x,d,z):return C+X*x+Y*d+Z*z
def box(c,size,paint,b=.10,skip=()):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b,skip=skip)
def lathe(c,axis,prof,paint,sides=24):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in prof],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=16):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def bolt(c,axis=Y,r=.12):cylinder(c,axis,.06,r,'steel',12)
FONT={
 'D':[[(0,0),(0,1),(.65,1),(1,.75),(1,.25),(.65,0),(0,0)]],
 'R':[[(0,0),(0,1),(.8,1),(1,.8),(1,.65),(.8,.5),(0,.5)],[(.5,.5),(1,0)]],
 'I':[[(.5,0),(.5,1)],[(.1,0),(.9,0)],[(.1,1),(.9,1)]],
 'N':[[(0,0),(0,1),(1,0),(1,1)]],
 'K':[[(0,0),(0,1)],[(1,1),(0,.5),(1,0)]],
 'S':[[(1,.92),(.8,1),(.2,1),(0,.8),(0,.6),(1,.4),(1,.15),(.8,0),(.2,0),(0,.08)]],
 'C':[[(1,1),(.2,1),(0,.8),(0,.2),(.2,0),(1,0)]],
 'O':[[ (.2,0),(0,.2),(0,.8),(.2,1),(.8,1),(1,.8),(1,.2),(.8,0),(.2,0)]],
 'L':[[(0,1),(0,0),(1,0)]],
 'A':[[(0,0),(0,.75),(.5,1),(1,.75),(1,0)],[(0,.48),(1,.48)]],
 'M':[[(0,0),(0,1),(.5,.45),(1,1),(1,0)]],
 'E':[[(1,1),(0,1),(0,0),(1,0)],[(0,.5),(.85,.5)]]}
def word(text,mapper,height,width,stroke,gap,paint):
 assert all(c in FONT for c in text)
 for index,char in enumerate(text):
  for path in FONT[char]:
   for aa,bb in zip(path,path[1:]):
    a=np.array((index*(width+gap)+aa[0]*width,aa[1]*height));b=np.array((index*(width+gap)+bb[0]*width,bb[1]*height))
    delta=b-a;side=np.array((-delta[1],delta[0]))/np.linalg.norm(delta)*stroke*.5
    D._face(m,paint,[mapper(*q) for q in (a-side,b-side,b+side,a+side)],Y)
# Closed rear and sides; the cabinet front is open, not another picture card.
box((0,0,5.2),(30,28,9.6),'enamel',.45,skip=('+y',))
for s in (-1,1):
 box((s*14.25,0,40.3),(1.5,28,61.8),'enamel',.35)
 box((s*13.44,-.4,38.2),(.10,24.6,53.0),'liner',.025)
box((0,-13.4,40.3),(28.5,1.2,61.8),'enamel',.3)
box((0,-12.72,38.2),(26.7,.12,53.0),'liner',.025)
box((0,0,70.5),(30,28,3.),'enamel',.40)
box((0,-.4,66.1),(26.8,24.6,.18),'liner',.035)
for x in (-11.8,11.8):
 for d in (-10.8,10.8):cylinder((x,d,0),Z,.5,1.1,'frame',20)
# Recessed compressor intake, grille bars and service-panel screws.
box((0,12.8,5.1),(27.2,.18,6.6),'frame',.05)
for z in np.linspace(2.7,7.6,8):box((0,13.95,z),(25.4,.38,.23),'enamel',.055)
for x in (-12.9,12.9):box((x,13.82,5.1),(.45,.50,6.0),'enamel',.12)
box((0,13.8,1.25),(26.6,.45,1.0),'enamel',.15)
box((0,13.8,9.0),(26.6,.45,.85),'enamel',.15)
for x in (-12.,12.):bolt((x,14.04,8.4))
# Four steel-wire shelves with raised retaining lips and label carriers.
for row,z in enumerate((14.5,27.,39.5,52.)):
 for x in np.linspace(-12.3,12.3,12):G.tube(m,[P(x,-10.8,z),P(x,10.8,z)],.055,'steel',sides=8)
 for d in (-10.8,10.8):G.tube(m,[P(-12.3,d,z),P(12.3,d,z)],.10,'steel',sides=10)
 for x in (-12.3,12.3):G.tube(m,[P(x,-10.8,z),P(x,10.8,z)],.10,'steel',sides=10)
 box((0,11.0,z+.35),(25.0,.45,.60),'liner',.06)
 for x in (-8.4,-2.8,2.8,8.4):box((x,11.25,z+.35),(1.8,.025,.32),'label',.006)
 # Rows are stocked with separate cans/bottles, leaving depth between products.
 for depth in (2.5,8.0):
  for col,x in enumerate((-8.4,-2.8,2.8,8.4)):
   paint=('red','blue','green')[(row+col)%3]
   base=z+.14
   if row==0:
    profile=[(0,0),(1.16,0),(1.30,.20),(1.34,.60),(1.34,2.5),(1.34,5.7),(1.34,6.7),(1.25,7.2),(.60,8.4),(.48,8.5),(.48,9.2),(0,9.2)]
    paints=[paint,paint,paint,paint,'label',paint,paint,paint,paint,'frame','frame']
    lathe((x,depth,base),Z,profile,paints,24)
    cylinder((x,depth,base+9.20),Z,.38,.53,paint,20)
   else:
    profile=[(0,0),(1.08,0),(1.23,.14),(1.30,.32),(1.30,1.65),(1.30,2.05),(1.30,4.15),(1.30,4.55),(1.30,5.7),(1.21,6.0),(1.12,6.10),(0,6.10)]
    paints=['steel','steel',paint,paint,paint,'label',paint,paint,paint,'steel','steel']
    lathe((x,depth,base),Z,profile,paints,24)
    G.torus(m,P(x,depth,base+6.12),Z,1.12,.045,'steel',seg=24,sides=6)
    G.torus(m,P(x,depth-.13,base+6.15),Z,.24,.055,'frame',seg=16,sides=6)
   text={'red':'COLA','blue':'SODA','green':'LIME'}[paint]
   radius=1.365 if row==0 else 1.325
   def print_surface(a,b):
    angle=(a-.88)/radius
    return P(x+radius*math.sin(angle),depth+radius*math.cos(angle),base+(3.60 if row==0 else 2.73)+b)
   word(text,print_surface,.60,.35,.047,.12,'frame')
# Framed closed glass door, gasket, hinge barrels and a vertical pull handle.
for s in (-1,1):
 box((s*13.2,12.7,38.0),(1.35,1.6,55.2),'frame',.17)
 box((s*13.15,11.75,38.0),(1.6,.28,56.0),'frame',.08)
for z in (10.7,65.4):box((0,12.7,z),(27.6,1.6,1.35),'frame',.17)
G._box3(m,P(0,13.28,38.0),(X,Y,Z),(25.05,.06,53.3),'glass')
for z in (17,59):
 cylinder((-13.65,12.65,z-1.0),Z,2.0,.34,'steel',20)
 for zz in (z-.75,z+.75):bolt((-13.65,13.05,zz))
for z in (28.,50.):cylinder((11.65,12.9,z),Y,.86,.31,'steel',20)
G.tube(m,[P(11.65,13.78,28),P(11.65,13.78,50)],.31,'steel',sides=20)
# Visible interior diffusers reuse the map's existing cool-lamp material; the
# saved porch-fridge point light remains the only local light for this asset.
for x in (-12.65,12.65):box((x,10.7,38.1),(.30,.35,51.6),'led',.08)
# A simple unlit header avoids another luminous picture across the door.
# The plaque sits proud of the cabinet's d=14 front, including the top slab.
box((0,13.99,68.8),(27.7,.22,4.6),'red',.2)
word('DRINKS',lambda a,b:P(-8.1+a,14.13,67.75+b),2.0,2.05,.14,.78,'label')
for x in (-13.4,13.4):bolt((x,14.11,68.8),r=.10)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p,_,_,_ in colours}
m.material_overrides.update(glass=MAT+'/glass.vmat',led='materials/riverside/rs_lamp_cool.vmat')
m.tile_overrides={p:16 for p in m.polygons}
count=K.write_model(MODEL,RES,'drinks_fridge',m)
legacy=K.Model();RP.fridge(legacy,(96.,560.),(0.,-1.),20.);R.configure(legacy)
K.write_obj(OUT/'legacy-fridge.obj',legacy,'legacy_fridge')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-fridge.obj');wanted=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/riverside/riverside_store.obj';lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved fridge differs from the source helper: inspect before staging'
(MODEL/'store_without_fridge.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib riverside_store.mtl','mtllib store_without_fridge.mtl'))
(MODEL/'store_without_fridge.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_fridge.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/riverside/riverside_store.obj',RES+'/store_without_fridge.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/clock-v1/import.cs.txt').read_text().replace('output/railhead/clock-v1','output/riverside/drinks-fridge-v1').replace('maps/railhead/clock-v1/','maps/riverside/drinks-fridge-v1/').replace('materials/railhead/clock-v1/','materials/riverside/drinks-fridge-v1/')
(HERE/'import.cs.txt').write_text(template,encoding='utf-8')
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files),drinks=32)))
