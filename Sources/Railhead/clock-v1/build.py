"""Private geometric rebuild of the existing 14:03 station clock."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_props as RP
import railhead_map as R
import riverdale_parts as G
OUT=ROOT/'output/railhead/clock-v1';STAGE=OUT/'stage'
RES='models/maps/railhead/clock-v1';MAT='materials/railhead/clock-v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/railhead').rglob('*'))+list((ROOT/'Assets/materials/railhead').rglob('*'))+[ROOT/'Assets/scenes/maps/Railhead/railhead.scene',ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_props.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'clock-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
for name,colour,rough,metal in [('housing',(.075,.085,.09),.5,0.0),('dial',(.84,.83,.77),.62,0.0),('ink',(.012,.014,.015),.45,0.0),('steel',(.43,.46,.47),.32,.8),('seal',(.018,.02,.02),.86,0.0)]:
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
m=K.Model();Z=np.array((0.,0.,1.));C=np.array((0.,1110.,240.))
def lathe(c,axis,profile,paint,sides=64):G.lathe_axis(m,c,axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=20):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def bolt(c,axis,r=.15,h=.09):
    cylinder(c,axis,.035,r*1.25,'steel',12);cylinder(c+axis*.035,axis,h,r,'steel',6)
axis=np.array((0.,1.,0.))
# Rolled housing halves with a real recessed dial seat on both faces.
profile=[(11.08,-2.10),(11.48,-2.33),(11.93,-2.36),(12.28,-2.15),(12.4,-1.88),(12.4,1.88),(12.28,2.15),(11.93,2.36),(11.48,2.33),(11.08,2.10),(11.08,-2.10)]
lathe(C,axis,profile,'housing',96)
G.torus(m,C,axis,12.405,.035,'seal',seg=96,sides=6)
for s in (-1,1):
    out=np.array((0.,float(s),0.));right=np.cross(Z,out)
    def P(u,d,z):return C+right*u+out*d+Z*z
    # Dial and seal are set behind the front retaining lip.
    lathe(C,out,[(0,1.37),(11.1,1.37),(11.1,1.55),(0,1.55)],'dial',96)
    lathe(C,out,[(11.04,1.58),(11.20,1.58),(11.20,2.1),(11.04,2.1),(11.04,1.58)],'seal',96)
    lathe(C,out,[(11.18,2.08),(11.4,2.14),(11.48,2.24),(11.4,2.30),(11.18,2.21),(11.18,2.08)],'steel',96)
    # Physically separate indices and hands retain the saved clock's 14:03 face.
    def bar(angle,r0,r1,width,depth,thickness,paint='ink',bevel=.015):
        rad=right*math.sin(angle)+Z*math.cos(angle);tan=right*math.cos(angle)-Z*math.sin(angle)
        centre=C+rad*((r0+r1)/2)+out*depth
        G.bevel_box(m,centre,(tan,rad,out),(width,r1-r0,thickness),paint,bevel=bevel)
    for minute in range(60):
        major=minute%5==0
        bar(minute*math.pi/30,7.7 if major else 9.5,10.4,.76 if major else .24,1.595,.075,bevel=.012)
    bar(math.radians(61.5),-1.1,6.95,.95,1.73,.14,bevel=.035)
    bar(math.radians(18),-1.55,9.2,.6,1.91,.14,bevel=.025)
    cylinder(P(0,1.91,0),out,.10,.54,'ink',32)
    cylinder(P(0,2.01,0),out,.035,.20,'steel',20)
    for k in range(6):
        a=k*math.pi/3+math.pi/6
        bolt(P(11.83*math.cos(a),2.34,11.83*math.sin(a)),out,.13,.07)
    # A closed, shallow convex cover, without heavy blur or tinted lettering.
    lathe(C,out,[(0,2.05),(11.12,2.05),(11.12,2.14),(8,2.20),(4,2.23),(0,2.24)],'glass',96)
# Mounting clevis, captive pin, hanger ferrules and the ceiling flange.
G.bevel_box(m,C+Z*13.1,(np.array((1.,0.,0.)),axis,Z),(3.2,3.0,2.2),'housing',bevel=.35)
for s in (-1,1):bolt(C+Z*13.2+axis*s*1.52,axis*s,.32,.18)
lathe(C,Z,[(0,13.7),(.82,13.7),(.82,15.0),(.45,15.5),(.45,29.9),(.9,29.9),(.9,30.1),(0,30.1)],'housing',32)
lathe(C,Z,[(0,30.0),(2.2,30.0),(2.4,30.2),(2.4,30.4),(0,30.4)],'housing',48)
for x in (-1.6,1.6):bolt(C+np.array((x,0,29.9)),-Z,.20,.12)
m.material_overrides={name:MAT+'/'+name+'.vmat' for name in ('housing','dial','ink','steel','seal')}
m.material_overrides['glass']='materials/railhead/rw_case_glass.vmat'
m.tile_overrides={paint:16 for paint in m.polygons}
count=K.write_model(MODEL,RES,'station_clock',m)
# Exact legacy face signatures select this clock alone; no bounding-box deletion.
legacy=K.Model();RP.clock(legacy,0.,1110.,240.,'n');R.configure(legacy)
K.write_obj(OUT/'legacy-clock.obj',legacy,'legacy_clock')
def records(path):
    lines=path.read_text().splitlines(keepends=True)
    vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
    paint='';result=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,result
_,old=records(OUT/'legacy-clock.obj');want=collections.Counter(key for _,key in old)
source=ROOT/'Assets/models/maps/railhead/railhead_dress_centre.obj';lines,faces=records(source);removed=set()
for i,key in faces:
    if want[key]:removed.add(i);want[key]-=1
assert not +want,'Saved clock differs from the source helper; inspect before staging'
(MODEL/'dressing_without_clock.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib railhead_dress_centre.mtl','mtllib dressing_without_clock.mtl'))
(MODEL/'dressing_without_clock.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'dressing_without_clock.vmdl').write_text((ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl').read_text().replace('models/maps/railhead/railhead_dress_centre.obj',RES+'/dressing_without_clock.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=count,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/ReefHall/pump-v1/import.cs.txt').read_text().replace('output/reefhall/pump-v1','output/railhead/clock-v1').replace('maps/reefhall/pump-v1/','maps/railhead/clock-v1/').replace('materials/reefhall/pump-v1/','materials/railhead/clock-v1/')
(Path(__file__).parent/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=count,old_triangles=len(removed),files=len(files))))
