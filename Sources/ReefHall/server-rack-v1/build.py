"""Isolated equipment-rack proposal; exact legacy-face removal, unchanged physics."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
OUT=ROOT/'output/reefhall/server-rack-v1';STAGE=OUT/'stage'
RES='models/maps/reefhall/server-rack-v1';MAT='materials/reefhall/server-rack-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/reefhall').rglob('*'))+list((ROOT/'Assets/materials/reefhall').rglob('*'))+[ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene',ROOT/'Tools/reefhall_map.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'server-rack-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('frame',(.105,.125,.14),.5,.25),('panel',(.18,.20,.22),.46,.35),('rail',(.39,.43,.45),.34,.8),('black',(.025,.031,.036),.73,0.),('port',(.28,.31,.33),.42,.6)]:
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
''')
m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.));AXES=(X,Y,Z)
width=340/13;W=width-1.2
for k in range(13):
 C=np.array((1960+(k+.5)*width,900.,0.))
 def P(x,d,z):return C+X*x+Y*d+Z*z
 def box(x,d,z,sx,sd,sz,paint='frame',bevel=.08):
  if min(sx,sd,sz)<.30 or bevel<=.05:
   G._box3(m,P(x,d,z),AXES,(sx,sd,sz),paint)
  else:G.bevel_box(m,P(x,d,z),AXES,(sx,sd,sz),paint,bevel=min(bevel,min(sx,sd,sz)*.24))
 def lathe(x,d,z,profile,paint='rail',sides=12):
  G.lathe_axis(m,P(x,d,z),Y,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
 def screw(x,d,z):lathe(x,d,z,[(0,0),(.15,0),(.15,.065),(0,.065)],sides=8)
 # Rolled cabinet edges, closed side panels and a shadowed equipment bay.
 box(0,14.5,1.6,W,29,3.2,'black',.2)
 box(0,14.5,82.8,W,29,2.4,'frame',.23)
 box(0,1.0,42,W,2,80,'black',.15)
 for s in (-1,1):
  box(s*(W/2-.5),14.5,42,1.,29,80,'frame',.17)
  box(s*(W/2-.65),28.7,42,1.3,2.6,78,'frame',.23)
  box(s*10.75,27.6,42,.60,.55,76,'rail',.05)
  # Actual rack fixing holes as dark insets, with alternating exposed screws.
  for z in range(5,80,3):
   box(s*10.75,27.91,z,.28,.035,.55,'black',.01)
 for z in (3.5,80.5):box(0,28.5,z,W-1.2,2.6,1.2,'frame',.16)
 # Six removable 5U-style equipment chassis: recessed face, ventilated intake,
 # drive caddies, status lamps, pull handles and captive mounting screws.
 for row in range(6):
  z=10+row*12
  box(0,14.5,z+.6,20.65,25.8,10.8,'black',.18)
  box(0,28.0,z+.6,20.55,.7,10.4,'panel',.12)
  # Recessed open vent slots. Black backing sits behind the physical grille bars.
  box(-3.25,28.40,z+1.2,11.7,.10,4.9,'black',.015)
  for j in range(5):box(-3.25,28.58,z-1.2+j*1.2,11.7,.25,.22,'panel',.025)
  for x in (-9.1,-3.25,2.6):box(x,28.58,z+1.2,.20,.25,4.9,'panel',.025)
  # Serviceable drive/patch modules, with latch and a tiny activity indicator.
  for q in range(3):
   xx=4.1+q*1.75
   box(xx,28.6,z+.9,1.45,.55,5.3,'frame',.09)
   box(xx,28.93,z+.8,.65,.10,3.1,'black',.02)
   box(xx,29.0,z+2.8,.7,.08,.22,'rail',.015)
  for s in (-1,1):
   for zz in (z-3.5,z+4.6):
    box(s*9.4,28.85,zz,.48,.80,.48,'rail',.08)
   box(s*9.4,29.35,z+.55,.42,.42,8.1,'frame',.15)
   for zz in (z-3.7,z+4.8):screw(s*10.05,28.44,zz)
 # Keep the six indicator levels and alternating cool/warm saved colour pattern.
  paint='cool' if (k+row)%3 else 'warm'
  box(-6.8,28.79,z,1.1,.10,.32,paint,.018)
  box(-8.2,28.74,z,.5,.14,.5,'black',.05)
  screw(-8.2,28.83,z)
  # Short horizontal service-label carrier, deliberately unlit.
  box(-3.25,28.47,z-3.6,6.0,.08,.50,'rail',.015)
 # Top access vent and discreet end-panel fasteners.
 for x in (-7,-3.5,0,3.5,7):box(x,16,84-.08,.8,15,.12,'black',.015)
# Four cantilever service lamps are part of the proposal. Their actual runtime
# lights are enabled with the candidate, not used as capture-only fill lights.
for e in (2000.,2085.,2170.,2255.):
 C=np.array((e,900.,0.))
 box(0,15,83.5,6,6,1,'rail',.15)
 box(0,15,96,2.0,2.0,24,'frame',.17)
 box(0,35.5,108,2.,43.,2.,'frame',.17)
 box(0,56,107.5,24,6,4,'frame',.35)
 box(0,56,105.42,21,4,.35,'diffuser',.05)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('frame','panel','rail','black','port')}
m.material_overrides.update(cool='materials/reefhall/rh_led_cool.vmat',warm='materials/reefhall/rh_led_warm.vmat',diffuser='materials/reefhall/rh_frosted_lit.vmat')
m.tile_overrides={p:32 for p in m.polygons}
count=K.write_model(MODEL,RES,'server_racks',m)
fr,base,_=R.side_frame(R.CONTROL,'n');legacy=K.Model();R.server_rack(legacy,fr,1960-base,2300-base);R.configure(legacy)
K.write_obj(OUT/'legacy-racks.obj',legacy,'legacy_racks')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-racks.obj');wanted=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/reefhall/reefhall_control.obj';lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved racks differ from generator: inspect before staging'
(MODEL/'control_without_racks.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib reefhall_control.mtl','mtllib control_without_racks.mtl'))
(MODEL/'control_without_racks.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'control_without_racks.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/reefhall/reefhall_control.obj',RES+'/control_without_racks.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True,racks=13),indent=2))
template=(ROOT/'Sources/Railhead/clock-v1/import.cs.txt').read_text().replace('output/railhead/clock-v1','output/reefhall/server-rack-v1').replace('maps/railhead/clock-v1/','maps/reefhall/server-rack-v1/').replace('materials/railhead/clock-v1/','materials/reefhall/server-rack-v1/')
(HERE/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files),racks=13)))
