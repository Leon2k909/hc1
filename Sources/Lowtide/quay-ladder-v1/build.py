"""Review-only replacement of one original Lowtide quay ladder."""
from pathlib import Path
import sys,math,json,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
OUT=ROOT/'output/lowtide/quay-ladder-v1';STAGE=OUT/'stage'
RES='models/maps/lowtide/quay-ladder-v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guardpaths=list((ROOT/'Assets/models/maps/lowtide').rglob('*'))+list((ROOT/'Assets/materials/lowtide').rglob('*'))+[ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene',ROOT/'Tools/lowtide_map.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in guardpaths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c') and 'quay-ladder-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))
m=K.Model();N=-1450.
def P(e,n,z):return np.array((e,N+n,z),float)
def tube(points,r,paint,sides=12):
    points=[np.asarray(p,float) for p in points];rings=[];norms=[]
    for i,p in enumerate(points):
        tangent=K.normalise(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
        u=np.array((0,1,0),float) if abs(tangent[1])<.9 else np.array((0,0,1),float)
        u=K.normalise(u-tangent*np.dot(tangent,u));v=K.normalise(np.cross(tangent,u))
        ns=[u*math.cos(2*math.pi*k/sides)+v*math.sin(2*math.pi*k/sides) for k in range(sides)]
        rings.append([p+r*n for n in ns]);norms.append(ns)
    distance=0.
    for i in range(len(points)-1):
        length=np.linalg.norm(points[i+1]-points[i])
        for j in range(sides):
            j1=(j+1)%sides
            pts=[rings[i][j],rings[i][j1],rings[i+1][j1],rings[i+1][j]]
            normals=[norms[i][j],norms[i][j1],norms[i+1][j1],norms[i+1][j]]
            m.polygon(paint,pts,normals=normals,uv=[(j/sides,distance/12),((j+1)/sides,distance/12),((j+1)/sides,(distance+length)/12),(j/sides,(distance+length)/12)])
        distance+=length
    m.polygon(paint,rings[0][::-1]);m.polygon(paint,rings[-1])
def box(e,n,z,de,dn,dz,paint):m.box(P(e-de/2,n-dn/2,z-dz/2),P(e+de/2,n+dn/2,z+dz/2),paint)
def bolt(e,n,z):
    tube([P(e,n,z),P(e-.3,n,z)],.42,'hardware',6)
    box(e-.32,n,z,.05,.37,.10,'dark')
# Smooth continuous rails turn over the coping, ending in small foot plates.
for n in (-8,8):
    path=[P(234,n,-132),P(234,n,15)]
    for angle in np.linspace(math.pi,0,17)[1:]:path.append(P(237+3*math.cos(angle),n,15+3*math.sin(angle)))
    path.append(P(240,n,1.0));tube(path,1.0,'paint',16)
    # Fix to the narrow front lip of the coping, clear of the railing at e=243.
    box(240,n,.6,3.0,5.5,1.2,'paint')
    for offset in (-1.7,1.7):tube([P(240,n+offset,1.21),P(240,n+offset,1.5)],.36,'hardware',6)
    # Wall standoffs transfer the rail to bolted plates, with no floating joins.
    for z in (-15,-66,-116):
        box(239.65,n,z,.7,4.2,6.0,'paint')
        tube([P(234,n,z),P(239.3,n,z)],.65,'paint',12)
        for dz in (-1.8,1.8):bolt(239.2,n,z+dz)
        tube([P(234,n,z-1.2),P(234,n,z+1.2)],1.2,'paint',16)
    tube([P(234,n,-132),P(234,n,-130.7)],1.12,'dark',16)
# Round-ended anti-slip tread sections; subtle worn edge strips and grip studs.
for z in range(-120,0,12):
    tube([P(234,-8,z),P(234,8,z)],.62,'paint',12)
    box(233.9,0,z+.57,2.9,14.1,.32,'paint')
    box(232.5,0,z+.60,.17,13.9,.22,'worn')
    for n in np.linspace(-6,6,9):
        box(233.9,float(n),z+.78,1.65,.17,.13,'grip')
    for n in (-7.4,7.4):tube([P(234,n-.24,z),P(234,n+.24,z)],.85,'paint',12)
m.material_overrides={'paint':'materials/lowtide/structure/lt_cast_iron_v2.vmat','hardware':'materials/lowtide/lt_steel.vmat','dark':'materials/lowtide/structure/lt_cast_iron_v2.vmat','worn':'materials/lowtide/lt_steel.vmat','grip':'materials/lowtide/drainage/lt_grate_cast_iron.vmat'}
m.tile_overrides={p:12 for p in m.polygons}
tris=K.write_model(MODEL,RES,'quay_ladder',m)
# Preserve the installed architecture's exact indices and all unrelated faces.
source=ROOT/'Assets/models/maps/lowtide/lowtide_east.obj';lines=source.read_text().splitlines(keepends=True)
ov=[tuple(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')];verts=[(c,a,b) for a,b,c in ov]
kept=[];removed=[];paint=''
for line in lines:
    if line.startswith('usemtl '):paint=line.split()[1]
    if line.startswith('f ') and paint=='iron_black':
        pts=[verts[int(t.split('/')[0])-1] for t in line.split()[1:]]
        # native world X=n, Y=-e
        if all(-1459.01<=x<=-1440.99 and -244.01<=y<=-233.99 and -132.01<=z<=18.01 for x,y,z in pts):
            removed.append(line);continue
    kept.append(line)
assert len(removed)==168,len(removed)
(MODEL/'east_without_ladder.obj').write_text(''.join(kept).replace('mtllib lowtide_east.mtl','mtllib east_without_ladder.mtl'))
(MODEL/'east_without_ladder.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
vmdl=(ROOT/'Assets/models/maps/lowtide/lowtide_east.vmdl').read_text().replace('models/maps/lowtide/lowtide_east.obj',RES+'/east_without_ladder.obj')
(MODEL/'east_without_ladder.vmdl').write_text(vmdl)
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=tris,removed_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
template=(ROOT/'Sources/Ares/observation-sign-v1/import.cs.txt').read_text().replace('output/ares/observation-sign-v1','output/lowtide/quay-ladder-v1').replace('maps/ares/observation-sign-v1/','maps/lowtide/quay-ladder-v1/').replace('materials/ares/observation-sign-v1/','materials/lowtide/quay-ladder-v1/')
(Path(__file__).parent/'import.cs.txt').write_text(template)
print(json.dumps(dict(triangles=tris,removed_triangles=len(removed),staged_files=len(files))))
