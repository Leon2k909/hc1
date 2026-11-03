"""A guarded, renderer-only circulation pump proposal for Reef Hall."""
from pathlib import Path
import hashlib,json,sys,math,collections
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
OUT=ROOT/'output/reefhall/pump-v1';STAGE=OUT/'stage'
RES='models/maps/reefhall/pump-v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
MAT='materials/reefhall/pump-v1';MATERIAL=STAGE/'Assets'/MAT;MATERIAL.mkdir(parents=True,exist_ok=True)
for name,colour,rough in [('blue',(52,108,139),.52),('graphite',(45,53,56),.58),('pipe',(94,106,111),.54)]:
    rng=np.random.default_rng(731+len(name));noise=rng.normal(0,1,(512,512))
    albedo=np.clip(np.asarray(colour)[None,None,:]+noise[:,:,None]*.7,0,255).astype('uint8')
    Image.fromarray(albedo).save(MATERIAL/f'{name}_color.png')
    Image.fromarray(np.clip(rough*255+noise*2,0,255).astype('uint8')).save(MATERIAL/f'{name}_rough.png')
    normal=np.zeros((512,512,3),dtype='uint8');normal[:]=[128,128,255]
    normal[:,:,:2]=np.clip(128+np.stack(np.gradient(noise),axis=-1)*.6,0,255).astype('uint8')
    Image.fromarray(normal).save(MATERIAL/f'{name}_normal.png')
    (MATERIAL/f'{name}.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0.0"
 g_flRoughnessScaleFactor "1"
 TextureColor "'''+MAT+'/'+name+'''_color.png"
 TextureNormal "'''+MAT+'/'+name+'''_normal.png"
 TextureRoughness "'''+MAT+'/'+name+'''_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
}
''')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=list((ROOT/'Assets/models/maps/reefhall').rglob('*'))+list((ROOT/'Assets/materials/reefhall').rglob('*'))+[ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene',ROOT/'Tools/reefhall_map.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'pump-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
m=K.Model();X=np.array((1,0,0));Y=np.array((0,1,0));Z=np.array((0,0,1))
def P(x,y,z):return np.array((-380+x,1610+y,z),float)
def box(c,size,paint,bevel=.25,axes=(X,Y,Z)):G.bevel_box(m,P(*c),axes,size,paint,bevel=bevel)
def lathe(c,axis,profile,paint,sides=32):G.lathe_axis(m,P(*c),axis,[(float(r),float(z)) for r,z in profile],paint,sides=sides)
def cylinder(c,axis,length,r,paint,sides=20):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
def bolt(c,axis=Z,r=.65,h=.55):
    cylinder(c,axis,.16,r*1.3,'steel',16);cylinder(tuple(np.array(c)+axis*.16),axis,h,r,'steel',6)
box((0,0,4),(68,36,8),'base',.9)
box((0,0,7.8),(62,30,.7),'metal',.25)
for x in (-28,28):
    for y in (-13,13):bolt((x,y,8.2))
for x in (-23,-8):
    for y in (-8.5,8.5):
        box((x,y,11),(7,7,6),'blue',.5)
        bolt((x,y,14),Z,.55,.5)
# Closed motor shell with formed end bells, axial cooling fins and fan cover.
lathe((0,0,26),X,[(0,-31),(10.5,-31),(12.3,-29.5),(12.7,-26),(11.5,-24),(11.5,-3),(10.3,-1),(5.5,0),(0,0)],'blue',40)
for k in range(24):
    a=2*math.pi*k/24;rad=np.array((0,math.cos(a),math.sin(a)));tan=np.cross(X,rad)
    centre=np.array((-14,0,26))+rad*12.6
    box(tuple(centre),(20,2.2,.48),'blue',.13,axes=(X,rad,tan))
lathe((0,0,26),X,[(10.5,-31.3),(12.7,-30.5),(13.3,-28.8),(13.3,-25.8),(12.7,-25.2),(11.5,-25.2),(11.5,-28.5),(10.5,-29.2),(10.5,-31.3)],'metal',40)
cylinder((-31.2,0,26),X,.35,10.5,'dark',32)
for k in range(14):
    a=2*math.pi*k/14;rad=np.array((0,math.cos(a),math.sin(a)));tan=np.cross(X,rad)
    c=np.array((-31.5,0,26))+rad*6
    box(tuple(c),(.45,8.5,.4),'blue',.12,axes=(X,rad,tan))
for y,z in ((0,38.5),(12.5,26),(0,13.5),(-12.5,26)):bolt((-30.8,y,z),-X,.45,.4)
box((-13,-12,35),(13,9,8),'blue',.7)
box((-13,-12,39.3),(13.6,9.6,1.0),'metal',.3)
for x in (-18,-8):
    for y in (-15.4,-8.6):bolt((x,y,39.8),Z,.38,.3)
cylinder((-19.5,-12,35),-X,2,1.4,'dark',12)
cylinder((-21.5,-12,35),-X,1.3,1.05,'steel',12)
# Coupling, guarded by a ventilated cage with real spaces between the ribs.
cylinder((-1,0,26),X,10,3.3,'steel',24)
for x in (0,6):cylinder((x,0,26),X,1.5,5,'metal',24)
for x in np.linspace(.4,7.6,7):
    G.torus(m,P(float(x),0,26),X,7.6,.35,'metal',seg=32,sides=6,a0=0,a1=math.pi)
for angle in (.2,math.pi/2,math.pi-.2):
    r=np.array((0,math.cos(angle),math.sin(angle)))
    G.tube(m,[P(0,*(r[1:]*7.6+np.array((0,26)))),P(8,*(r[1:]*7.6+np.array((0,26))))],.4,'metal',sides=8)
# Asymmetric cast volute, with chamfered shoulders, a gasket and bolted cover.
def shape(x,shrink=0):
    return [P(x,(17+2.2*a/(2*math.pi)-shrink)*math.cos(a),26+(17+2.2*a/(2*math.pi)-shrink)*math.sin(a)) for a in np.linspace(0,2*math.pi,49)[:-1]]
rings=[shape(8,1),shape(10),shape(23),shape(25,1)]
for a,b in zip(rings,rings[1:]):
    ns=[K.normalise(np.cross(a[(i+1)%48]-a[i],b[(i+1)%48]-a[i])) for i in range(48)]
    smooth=[K.normalise(ns[i-1]+ns[i]) for i in range(48)]
    for i in range(48):m.polygon('blue',[a[i],a[(i+1)%48],b[(i+1)%48],b[i]],normals=[smooth[i],smooth[(i+1)%48],smooth[(i+1)%48],smooth[i]])
for x,outer,inner,paint,reverse in [(8,rings[0],3.4,'blue',True),(25,rings[-1],6.1,'blue',False)]:
    hole=[P(x,inner*math.cos(a),26+inner*math.sin(a)) for a in np.linspace(0,2*math.pi,49)[:-1]]
    for i in range(48):
        pts=[hole[i],outer[i],outer[(i+1)%48],hole[(i+1)%48]]
        if reverse:pts=pts[::-1]
        m.polygon(paint,pts)
G.torus(m,P(23.3,0,26),X,16.9,.22,'dark',seg=48,sides=6)
for a in np.linspace(0,2*math.pi,12,endpoint=False):bolt((25.25,15.2*math.cos(a),26+15.2*math.sin(a)),X,.65,.6)
# The inlet/outlet keep the original centres and terminate at x=40 / z=70.
lathe((0,0,26),X,[(6.1,25),(7,25),(7,36),(10,36.8),(10,39.7),(9.5,40),(6.1,40),(6.1,25)],'pipe',32)
cylinder((28,0,26),X,.2,6.1,'dark',24)
for a in np.linspace(0,2*math.pi,8,endpoint=False):bolt((39.65,8.3*math.cos(a),26+8.3*math.sin(a)),-X,.42,.4)
lathe((18,0,0),Z,[(0,40),(7.3,40),(7.3,65.5),(10,66.2),(10,69.6),(9.5,70),(6.0,70),(6.0,46),(0,46)],'pipe',32)
for a in np.linspace(0,2*math.pi,8,endpoint=False):bolt((18+8.3*math.cos(a),8.3*math.sin(a),69.65),-Z,.42,.4)
for y in (-11,11):box((17,y,11),(16,7,6),'blue',.6)
# Lifting eye, drain plug and a small unlit service plate.
G.torus(m,P(-13,0,41),Y,2.0,.55,'steel',seg=24,sides=8)
cylinder((16,-17.5,16),-Y,1.5,.7,'steel',6)
box((-13,-16.6,35),(8,.25,3.8),'steel',.15)
for x in (-16.2,-9.8):bolt((x,-16.82,35),-Y,.22,.15)
m.material_overrides={'blue':MAT+'/blue.vmat','pipe':MAT+'/pipe.vmat','metal':MAT+'/graphite.vmat','base':MAT+'/graphite.vmat','dark':'materials/reefhall/rh_black.vmat','steel':'materials/reefhall/rh_stainless.vmat'}
m.tile_overrides={p:32 for p in m.polygons}
tris=K.write_model(MODEL,RES,'circulation_pump',m)
# Match the saved source by exact material/triangle positions, rather than a
# bounding box that could accidentally include a nearby pipe or floor.
legacy=K.Model();R.pump(legacy,(-380,1610),0.);R.configure(legacy)
K.write_obj(OUT/'legacy-pump.obj',legacy,'legacy_pump')
def records(path):
    lines=path.read_text().splitlines(keepends=True)
    verts=[tuple(round(float(s),3) for s in l.split()[1:4]) for l in lines if l.startswith('v ')]
    paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):faces.append((i,(paint,tuple(sorted(verts[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,expected=records(OUT/'legacy-pump.obj');wanted=collections.Counter(key for _,key in expected)
source=ROOT/'Assets/models/maps/reefhall/reefhall_filter.obj';lines,faces=records(source)
removed=set()
for i,key in faces:
    if wanted[key]>0:wanted[key]-=1;removed.add(i)
assert not +wanted,'Original pump does not match published geometry'
assert len(removed)==len(expected)
(MODEL/'filter_without_pump.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib reefhall_filter.mtl','mtllib filter_without_pump.mtl'))
(MODEL/'filter_without_pump.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'filter_without_pump.vmdl').write_text((ROOT/'Assets/models/maps/reefhall/reefhall_filter.vmdl').read_text().replace('models/maps/reefhall/reefhall_filter.obj',RES+'/filter_without_pump.obj'))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=tris,original_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Lowtide/quay-ladder-v1/import.cs.txt').read_text().replace('output/lowtide/quay-ladder-v1','output/reefhall/pump-v1').replace('maps/lowtide/quay-ladder-v1/','maps/reefhall/pump-v1/').replace('materials/lowtide/quay-ladder-v1/','materials/reefhall/pump-v1/')
(Path(__file__).parent/'import.cs.txt').write_text(template)
print(json.dumps(dict(new_triangles=tris,old_triangles=len(removed),stage_files=len(files))))
