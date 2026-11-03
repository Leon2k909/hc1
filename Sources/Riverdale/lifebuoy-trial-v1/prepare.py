"""Extract the actual saved lifebuoy and prepare private review textures."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,shutil,math,re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import sys
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1';TEX=HERE/'textures';OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
TEX.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as P
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
origin=np.array((1000.,300.,64.));out=np.array((-1.,0,0));right=np.cross((0,0,1),out)
m=K.Model();P.life_ring(m,origin,out)
def key(paint,points):return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))
expected=Counter()
for paint,polys in m.polygons.items():
    for points,_ in polys:
        for k in range(1,len(points)-1):expected[key(paint,(points[0],points[k],points[k+1]))]+=1
source=ROOT/'Assets/models/maps/riverdale/riverdale_hall.obj';doc=source.with_suffix('.vmdl')
assert 'filename = "models/maps/riverdale/riverdale_hall.obj"' in doc.read_text()
vertices=[];uv=[];normals=[];paint='';groups=defaultdict(list);matched=Counter()
for line in source.open():
    p=line.split()
    if not p:continue
    if p[0]=='v':a,z,n=map(float,p[1:]);vertices.append(np.array((-a,n,z)))
    elif p[0]=='vt':uv.append(list(map(float,p[1:])))
    elif p[0]=='vn':a,z,n=map(float,p[1:]);normals.append(np.array((-a,n,z)))
    elif p[0]=='usemtl':paint=p[1]
    elif p[0]=='f' and paint in m.polygons:
        ids=[[int(i)-1 for i in s.split('/')] for s in p[1:]];points=[vertices[v] for v,t,n in ids];sig=key(paint,points)
        if expected[sig]>matched[sig]:
            matched[sig]+=1
            def local(p):return [float(p@right),float(-p@out),float(p[2])]
            groups[paint].append({'vertices':[local(v-origin) for v in points],'uv':[uv[t] for v,t,n in ids],'normals':[local(normals[n]) for v,t,n in ids]})
assert matched==expected,(sum(expected.values()),sum(matched.values()),list((expected-matched).items())[:3])
scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene';scene_json=json.loads(scene.read_text())
def walk(go,enabled=True):
    enabled=enabled and go.get('Enabled',True)
    if enabled:
        for c in go.get('Components',[]):
            path=c.get('Model');path=path.get('Path') if isinstance(path,dict) else path
            if c.get('__type')=='Sandbox.ModelRenderer' and c.get('__enabled',True) and path=='models/maps/riverdale/riverdale_hall.vmdl':yield go
    for child in go.get('Children',[]):yield from walk(child,enabled)
renderers=[g for node in scene_json['GameObjects'] for g in walk(node)];assert len(renderers)==1
assert renderers[0]['Position']=='0,0,0' and renderers[0]['Rotation']=='0,0,0,1' and renderers[0]['Scale']=='1,1,1'
(HERE/'before.json').write_text(json.dumps(groups,indent=2))
# Guard this asset's material dependencies. Other map assets and the live scene
# can legitimately change in other work without changing this extracted buoy.
protected=[doc,HERE/'before.json']
for paint in groups:
    material=ROOT/'Assets/materials/riverdale'/f'{paint}.vmat';protected.append(material)
    for path in re.findall(r'"(materials/[^"\r\n]+)"',material.read_text()):
        dependency=ROOT/'Assets'/path
        if dependency.is_file():protected.append(dependency)
(HERE/'source-guard.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in protected},indent=2))
record={'asset':'Riverdale reactor-hall lifebuoy','source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
 'scene':scene.relative_to(ROOT).as_posix(),'sceneSHA256AtExtraction':sha(scene),'enabledSavedRendererVerified':True,'planWallOrigin':origin.tolist(),'out':out.tolist(),
 'localCoordinates':'Inches; +X right, +Z up, front -Y; wall at Y=0','beforeTriangles':sum(matched.values()),
 'exactSavedPositionsUVsNormals':True,'installed':False,'originalGameFilesChanged':False}
(HERE/'provenance.json').write_text(json.dumps(record,indent=2))
shutil.copy2(ROOT/'Sources/Orion/cable-reel-trial-v1/geometry.py',HERE/'geometry.py')
# Restrained fine surface detail. No dark edge mask or baked studio shadows.
N=1024;rng=np.random.default_rng(411);noise=rng.normal(0,1,(N,N)).astype(np.float32)
fine=gaussian_filter(noise,.6);broad=gaussian_filter(noise,17);broad/=broad.std()
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,255))).save(TEX/name)
for prefix,color,rough,metal in [('orange',(190,63,29),143,0),('white',(219,220,207),153,0),('rope',(168,155,115),187,0),('steel',(138,146,148),112,244),('rubber',(30,34,35),182,0),('webbing',(210,208,186),185,0)]:
    save(prefix+'_color.png',np.zeros((N,N,3))+color+fine[:,:,None]*3+broad[:,:,None]*1.7)
    save(prefix+'_roughness.png',rough+fine*9+broad*3)
    save(prefix+'_metallic.png',np.full((N,N),metal))
    yy,xx=np.mgrid[:N,:N];height=fine*.015
    if prefix in ('white','webbing'):height+=.008*np.sin(xx*math.tau/5)*np.sin(yy*math.tau/5)
    if prefix=='rope':height+=.018*np.sin(xx*math.tau/7+np.sin(yy/30))
    dy,dx=np.gradient(height);normal=np.stack((-dx,dy,np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    save(prefix+'_normal.png',(normal*.5+.5)*255)
print(json.dumps({'beforeTriangles':record['beforeTriangles'],'materials':{p:len(f) for p,f in groups.items()},'protectedOriginals':len(protected),'enabledInSavedScene':True}))
