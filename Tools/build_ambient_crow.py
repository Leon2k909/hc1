"""Build the runtime crow mesh and the identical offline preview geometry. No editor needed."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parts = {}

def add(a, b): return tuple(x+y for x,y in zip(a,b))
def sub(a, b): return tuple(x-y for x,y in zip(a,b))
def mul(a, s): return tuple(x*s for x in a)
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return mul(a, 1/max(1e-8,math.sqrt(sum(x*x for x in a))))

def surface(part, material, rings, sides=12):
    key = part, material
    mesh = parts.setdefault(key, {'points': [], 'normals': [], 'faces': []})
    offset = len(mesh['points'])
    # Each ring supplies center, two perpendicular radius vectors, and normal directions.
    for center, axis_a, axis_b in rings:
        for j in range(sides):
            theta = j*math.tau/sides
            radial = add(mul(axis_a,math.cos(theta)),mul(axis_b,math.sin(theta)))
            mesh['points'].append(add(center,radial))
            # An elliptical cross section's outward normal.
            normal = add(mul(norm(axis_a), math.cos(theta)/max(.001, math.sqrt(sum(x*x for x in axis_a)))),
                         mul(norm(axis_b), math.sin(theta)/max(.001, math.sqrt(sum(x*x for x in axis_b)))))
            mesh['normals'].append(norm(normal))
    for i in range(len(rings)-1):
        for j in range(sides):
            a = offset+i*sides+j
            b = offset+i*sides+(j+1)%sides
            c,d = a+sides,b+sides
            mesh['faces'].extend(((a,c,b),(b,c,d)))

def ellipsoid(part, material, center, size, segments=20, rows=12):
    mesh = parts.setdefault((part,material), {'points': [], 'normals': [], 'faces': []})
    start=len(mesh['points'])
    for i in range(rows+1):
        phi=math.pi*(.001+.998*i/rows)
        for j in range(segments):
            t=j*math.tau/segments
            direction=(math.cos(phi),math.sin(phi)*math.cos(t),math.sin(phi)*math.sin(t))
            mesh['points'].append(add(center,tuple(x*s for x,s in zip(direction,size))))
            mesh['normals'].append(norm(tuple(x/s for x,s in zip(direction,size))))
    for i in range(rows):
        for j in range(segments):
            a=start+i*segments+j;b=start+i*segments+(j+1)%segments
            mesh['faces'].extend(((a,a+segments,b),(b,a+segments,b+segments)))

def feather(part, material, root, tip, width, curve=.25, thickness=.12):
    along=norm(sub(tip,root))
    across=norm(cross((0,0,1),along))
    rings=[]
    for u in (.001, .06, .16, .40, .7, .90, .96, .99, .999):
        # Full rounded vane tapering to an individual feather tip, gently curved down.
        cap = math.sqrt(max(.0001, 1-((u-.90)/.10)**2)) if u>.90 else 1
        w=width*min(1,math.sqrt(u/.16))*cap
        center=add(add(root,mul(sub(tip,root),u)),(0,0,-curve*u*u))
        rings.append((center,mul(across,w),(0,0,max(.012,w*thickness))))
    surface(part,material,rings,6)

# Rounded chest, tapered rump, raised neck and a separate head with a crow-like forehead.
surface('body','plumage', [((x,0,z),(0,w,0),(0,0,h)) for x,z,w,h in
    [(-9.2,-.4,.05,.05),(-8,-.3,1.5,1.5),(-6,-.15,2.5,2.8),(-3,0,3.25,3.6),
     (0,0,3.35,3.75),(3,.5,3,3.3),(5,1.2,2.5,2.8),(6.5,2,2.15,2.5),
     (8,2.8,2.2,2.4),(9.5,3.1,2.25,2.5),(11,3.0,1.9,2.15),(12,2.8,1.35,1.5),
     (12.7,2.6,.3,.35)]],24)
ellipsoid('body','beak',(12.8,0,2.45),(2.9,.92,.9),16,8)
# Sharply tapered beak, curved dorsal ridge and narrower lower mandible.
surface('body','beak', [((12.0,0,2.65),(0,.9,0),(0,0,.8)),
    ((14.5,0,2.55),(0,.72,0),(0,0,.53)), ((16.1,0,2.25),(0,.34,0),(0,0,.28)),
    ((17.0,0,1.95),(0,.015,0),(0,0,.02))],12)
for side in (-1,1):
    ellipsoid('body','eye',(10.35,side*2.10,3.65),(.37,.23,.36),12,8)
    # Small folded feet tuck into the belly instead of hanging down in flight.
    ellipsoid('body','beak',(-4.6,side*1.15,-2.6),(2.0,.35,.36),12,6)

# A rounded fan of twelve overlapping tail feathers rather than a triangular fork.
for i in range(12):
    y=(i-5.5)*.63
    feather('body','flight',(-5.7,y*.5,-.25),(-18.1+abs(i-5.5)*.32,y,-1.05),.62,.25)

# Broad, cambered upper wing. The leading edge bends naturally at elbow and wrist.
stations=[(1,2.0,4.4,-4.5,.65),(5,2.1,5.9,-5.3,.95),(10,2.0,5.2,-7.4,.8),
          (15,1.65,2.8,-9.0,.55),(19,1.2,.1,-9.8,.3),(22,.8,-2.6,-9,.12)]
rings=[]
for y,z,front,back,height in stations:
    rings.append((((front+back)/2,y,z),((front-back)/2,0,0),(0,0,height)))
surface('left','plumage',rings,16)
# Distinct outer primary fingers: rounded ends and small gaps in the extended hand.
for i in range(8):
    root=(2.5-i*1.15,14.5+i*.50,1.4-i*.10)
    tip=(3.1-i*2.25,26.8+math.sin(i/7*math.pi)*4.4-i*.15,.2-i*.14)
    feather('left','flight',root,tip,1.0 if i<5 else 1.1,.35)
# Overlapping secondaries fill the trailing edge all the way back to the body.
for i in range(12):
    y=3+i*1.35
    feather('left','flight',(.9,y,1.55),(-9.6-i*.19,y+1.2,.7),.91,.30)
# Smaller coverts create feather layering on both sides of the wing, with shallow relief.
for below in (False,True):
    for row in range(2):
        for i in range(12):
            y=3+i*1.48
            x=2.8-row*2.8-max(0,y-10)*.30
            z=(.3 if below else 3.05)-max(0,y-7)*.10-row*.04
            feather('left','plumage',(x,y,z),(x-4.0,y+.65,z-.10),.75,.10,.08)

for mesh in parts.values():
    for i,(a,b,c) in enumerate(mesh['faces']):
        face_normal=cross(sub(mesh['points'][b],mesh['points'][a]),sub(mesh['points'][c],mesh['points'][a]))
        if sum(x*y for x,y in zip(face_normal,mesh['normals'][a]))<0:
            mesh['faces'][i]=(a,c,b)
    accumulated=[(0,0,0)]*len(mesh['points'])
    for a,b,c in mesh['faces']:
        n=cross(sub(mesh['points'][b],mesh['points'][a]),sub(mesh['points'][c],mesh['points'][a]))
        for vertex in (a,b,c):accumulated[vertex]=add(accumulated[vertex],n)
    mesh['normals']=[norm(n) for n in accumulated]

for (part,material),mesh in list(parts.items()):
    if part!='left': continue
    parts[('right',material)] = {
        'points': [(x,-y,z) for x,y,z in mesh['points']],
        'normals': [(x,-y,z) for x,y,z in mesh['normals']],
        'faces': [(a,c,b) for a,b,c in mesh['faces']]}

dest=ROOT/'Sources/AmbientBirds'
dest.mkdir(parents=True,exist_ok=True)
payload=[dict(part=k[0],material=k[1],**v) for k,v in parts.items()]
(dest/'crow-mesh.json').write_text(json.dumps(payload,separators=(',',':')))

def number(x):
    if abs(x)<.00005:x=0
    return f'{x:.4f}f'

lines=['// Generated by Tools/build_ambient_crow.py. Geometry also exported for offline renders.',
       'namespace Facepunch;', 'internal static class AmbientCrowMesh','{']
for part in ('body','left','right'):
    lines += [f'\tpublic static Model {part.title()}( Material plumage, Material flight, Material beak, Material eye )',
              '\t{','\t\tvar builder = Model.Builder;']
    for (p,mat),mesh in parts.items():
        if p!=part:continue
        lines += [f'\t\tAdd( builder, {mat}, [']
        for point,normal in zip(mesh['points'],mesh['normals']):
            lines += ['\t\t\t'+','.join(number(x) for x in (*point,*normal))+',']
        lines += ['\t\t], [']
        indices=[x for f in mesh['faces'] for x in f]
        for i in range(0,len(indices),48):lines += ['\t\t\t'+','.join(map(str,indices[i:i+48]))+',']
        lines += ['\t\t] );']
    lines += ['\t\treturn builder.Create();','\t}']
# Avoid depending on the engine builder's concrete type: build meshes in a list instead.
lines=[line.replace('var builder = Model.Builder;', 'var meshes = new List<Mesh>();')
       .replace('Add( builder,','Add( meshes,').replace('return builder.Create();','return Model.Builder.AddMeshes( meshes.ToArray() ).Create();') for line in lines]
lines += ['\tprivate static void Add( List<Mesh> meshes, Material material, float[] data, int[] indices )',
          '\t{','\t\tvar vertices = new Vertex[data.Length / 6];',
          '\t\tfor ( var i = 0; i < vertices.Length; i++ )', '\t\t{','\t\t\tvar k = i * 6;',
          '\t\t\tvertices[i] = new Vertex( new Vector3( data[k], data[k+1], data[k+2] ), new Vector3( data[k+3], data[k+4], data[k+5] ), Vector3.Forward, new Vector4() );',
          '\t\t}', '\t\tvar mesh = new Mesh( material );','\t\tmesh.CreateVertexBuffer( vertices.Length, vertices );',
          '\t\tmesh.CreateIndexBuffer( indices.Length, indices );',
          '\t\tmesh.Bounds = new BBox( new Vector3( -20, -33, -5 ), new Vector3( 18, 33, 7 ) );',
          '\t\tmeshes.Add( mesh );','\t}','}']
(ROOT/'Code/World/AmbientCrowMesh.cs').write_text('\n'.join(lines)+'\n')
print('Crow:',sum(len(x['points']) for x in payload),'vertices;',sum(len(x['faces']) for x in payload),'triangles across all three parts')
