"""Rounded camping lantern proposal at the existing dog-run placement."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_map as R
import riverdale_parts as G
OUT=ROOT/'output/riverside/lantern-v1';STAGE=OUT/'stage'
RES='models/maps/riverside/lantern-v1';MAT='materials/riverside/lantern-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/riverside').rglob('*'))+list((ROOT/'Assets/materials/riverside').rglob('*'))+[ROOT/'Assets/scenes/maps/Riverside/riverside.scene',ROOT/'Tools/riverside_map.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'lantern-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('enamel',(.16,.24,.18),.43,.15),('metal',(.42,.45,.43),.3,.8),('rubber',(.035,.042,.037),.78,0.)]:
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
m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));C=np.array((-50.,-205.,96.))
def P(x=0,y=0,z=0):return C+np.array((x,y,z),float)
def lathe(c,axis,profile,paint,sides=64):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=20):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def torus(c,axis,r,t,paint,seg=64):G.torus(m,P(*c),axis,r,t,paint,seg=seg,sides=8)
def box(c,size,paint,bevel=.04):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=bevel)
# Rubber foot, softly rolled battery housing and its screw-off lower seam.
lathe((0,0,0),Z,[(0,.02),(2.85,.02),(3.08,.10),(3.15,.3),(3.15,.48),(2.95,.57),(0,.57)],'rubber')
lathe((0,0,0),Z,[(0,.42),(2.94,.42),(3.12,.54),(3.2,.8),(3.2,1.55),(3.12,1.9),(2.82,2.25),(2.72,2.45),(0,2.45)],'enamel')
torus((0,0,.60),Z,3.07,.055,'metal')
torus((0,0,2.35),Z,2.72,.09,'rubber')
for k in range(16):
 a=2*math.pi*k/16
 # Shallow grip ribs remain below the broad face of the housing.
 G.tube(m,[P(3.17*math.cos(a),3.17*math.sin(a),.91),P(3.17*math.cos(a),3.17*math.sin(a),1.48)],.028,'rubber',sides=6)
# Smooth, closed frosted diffuser. It uses the installed glow material unchanged.
lathe((0,0,0),Z,[(0,2.38),(2.34,2.38),(2.51,2.58),(2.6,2.9),(2.6,7.9),(2.54,8.24),(2.35,8.5),(0,8.5)],'globe',96)
for z in (2.6,8.25):torus((0,0,z),Z,2.56,.09,'metal')
# Six stays protect the globe, with rounded sockets at both ends.
for k in range(6):
 a=math.pi/6+k*math.pi/3;x,y=2.7*math.cos(a),2.7*math.sin(a)
 G.tube(m,[P(x,y,2.25),P(x,y,8.65)],.10,'enamel',sides=10)
 for z in (2.3,8.45):cylinder((x,y,z),Z,.23,.17,'metal',12)
# Cast top, rolled lip, concentric vent seam and handle bosses.
lathe((0,0,0),Z,[(0,8.42),(2.7,8.42),(2.98,8.54),(3.04,8.76),(3.04,9.0),(2.89,9.22),(2.4,9.66),(1.45,9.92),(0,10.0)],'enamel')
torus((0,0,8.64),Z,2.96,.065,'metal')
torus((0,0,9.82),Z,1.75,.065,'rubber')
for s in (-1,1):
 cylinder((s*2.66,0,9.35),X*s,.38,.37,'enamel',24)
 cylinder((s*3.04,0,9.35),X*s,.06,.20,'metal',20)
# A continuous wire carry handle with a round shoulder and short soft grip.
handle=[P(-2.72,0,9.35),P(-2.8,0,11.0)]
handle += [P(2.8*math.cos(a),0,11+2.8*math.sin(a)) for a in np.linspace(math.pi,0,33)]
handle += [P(2.72,0,9.35)]
G.tube(m,handle,.115,'metal',sides=12,bend_radius=.12)
grip=[P(2.8*math.cos(a),0,11+2.8*math.sin(a)) for a in np.linspace(math.pi*.64,math.pi*.36,13)]
G.tube(m,grip,.21,'rubber',sides=12,bend_radius=.15)
# A recessed knurled dimmer; small marker on its face, no invented text.
lathe((0,-3.08,1.35),-Y,[(0,0),(.62,0),(.65,.05),(.65,.12),(.55,.17),(.49,.17),(.49,.31),(0,.31)],'rubber',40)
for k in range(24):
 a=k*math.pi/12
 cylinder((.49*math.cos(a),-3.26,1.35+.49*math.sin(a)),-Y,.11,.035,'rubber',6)
G.tube(m,[P(0,-3.40,1.55),P(0,-3.40,1.75)],.035,'metal',sides=6)
m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('enamel','metal','rubber')}
m.material_overrides['globe']='materials/riverside/rs_lantern.vmat'
m.tile_overrides={p:16 for p in m.polygons}
count=K.write_model(MODEL,RES,'camping_lantern',m)
legacy=K.Model();R.lantern(legacy,(-50,-205,96));R.configure(legacy)
K.write_obj(OUT/'legacy-lantern.obj',legacy,'legacy_lantern')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
_,old=records(OUT/'legacy-lantern.obj');wanted=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/riverside/riverside_pad.obj';lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Saved lantern differs from generator: inspect before staging'
(MODEL/'pad_without_lantern.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib riverside_pad.mtl','mtllib pad_without_lantern.mtl'))
(MODEL/'pad_without_lantern.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'pad_without_lantern.vmdl').write_text(source.with_suffix('.vmdl').read_text().replace('models/maps/riverside/riverside_pad.obj',RES+'/pad_without_lantern.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Railhead/clock-v1/import.cs.txt').read_text().replace('output/railhead/clock-v1','output/riverside/lantern-v1').replace('maps/railhead/clock-v1/','maps/riverside/lantern-v1/').replace('materials/railhead/clock-v1/','materials/riverside/lantern-v1/')
(HERE/'import.cs.txt').write_text(template,encoding='utf-8')
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files))))
