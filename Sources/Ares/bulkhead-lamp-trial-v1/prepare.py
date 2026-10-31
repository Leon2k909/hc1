"""Extract the installed lamp verbatim and prepare private review resources.

Writes only Sources/Ares/bulkhead-lamp-trial-v1 and output/.../bulkhead-lamp.
Never writes Assets, scenes, materials or runtime references.
"""
from pathlib import Path
from collections import defaultdict
import hashlib, json, math, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/bulkhead-lamp'
OUT.mkdir(parents=True,exist_ok=True)
TEX=HERE/'textures';TEX.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
scene=ROOT/'Assets/scenes/maps/Ares/ares.scene'
doc=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl'
imports=re.findall(r'filename = "([^"]+\.obj)"',doc.read_text())
assert 'models/maps/ares/crate-v2/dressing-base.obj' in imports, imports
source=ROOT/'Assets'/imports[0]
origin=np.array((-1100.,-300.,120.))
vertices=[];uv=[];normals=[];paint='';groups=defaultdict(list)
def local(p):
    # Installed OBJ a,z,n -> Ares plan e,n,z -> lamp x,y,z (front = -Y).
    return [float(p[1]),-float(p[0]),float(p[2])]
for line in source.open():
    parts=line.split()
    if not parts:continue
    if parts[0]=='v':
        a,z,n=map(float,parts[1:]);vertices.append(np.array((-a,n,z)))
    elif parts[0]=='vt':uv.append(list(map(float,parts[1:])))
    elif parts[0]=='vn':
        a,z,n=map(float,parts[1:]);normals.append(np.array((-a,n,z)))
    elif parts[0]=='usemtl':paint=parts[1]
    elif parts[0]=='f':
        ids=[[int(i)-1 for i in token.split('/')] for token in parts[1:]]
        points=np.array([vertices[v]-origin for v,t,n in ids])
        if np.all(points.min(0)>=(-.0001,-5.0001,-3.0001)) and np.all(points.max(0)<=(4.2001,5.0001,3.0001)):
            groups[paint].append({'vertices':[local(p) for p in points],
                'uv':[uv[t] for v,t,n in ids], 'normals':[local(normals[n]) for v,t,n in ids]})
count=sum(map(len,groups.values()))
assert count==24,(count,{k:len(v) for k,v in groups.items()})
assert set(groups)=={'ar_gunmetal','ar_led_warm'}
(HERE/'before.json').write_text(json.dumps(groups,indent=2))
refs=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.read_text()))
assert 'models/maps/ares/ares_dressing.vmdl' in scene.read_text()
protected=[scene,doc,source,source.with_suffix('.mtl')]
protected+=sorted((ROOT/'Assets/materials/ares').glob('*'))
protected=[p for p in protected if p.is_file()]
guard={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
(HERE/'source-guard.json').write_text(json.dumps(guard,indent=2))
record={'asset':'Ares lower-hall wall bulkhead lamp','nativeScene':'scenes/maps/Ares/ares.scene',
    'modelDoc':doc.relative_to(ROOT).as_posix(),'actualImportedMesh':source.relative_to(ROOT).as_posix(),
    'sourceSHA256':sha(source),'planOrigin':origin.tolist(),'worldOrigin':[-300,1100,120],
    'beforeTriangles':count,'beforeMaterials':refs,'copiedSavedGeometryUVsNormals':True,
    'outerEnvelopeInches':{'width':10,'height':6,'depth':4.2},
    'reviewOnly':True,'installed':False,'gameFilesWritten':False,
    'output':OUT.relative_to(ROOT).as_posix()}
(HERE/'provenance.json').write_text(json.dumps(record,indent=2))

# Scale-controlled reusable PBR maps: casting grain, handling marks, subtle dust.
rng=np.random.default_rng(813)
N=1024
noise=rng.normal(0,1,(N,N)).astype(np.float32)
from scipy.ndimage import gaussian_filter
fine=gaussian_filter(noise,.65)
coarse=gaussian_filter(noise,9);coarse/=max(coarse.std(),1e-6)
base=np.zeros((N,N,3),np.float32)+np.array([54,61,65])
base+=fine[:,:,None]*4+coarse[:,:,None]*.9
rough=np.clip(160+fine*11+coarse*2,0,255)
height=gaussian_filter(noise,.7)*.35
dy,dx=np.gradient(height)
normal=np.stack((-dx*.44,dy*.44,np.ones_like(dx)),2)
normal/=np.linalg.norm(normal,axis=2)[:,:,None]
def save(name,arr):Image.fromarray(np.uint8(np.clip(arr,0,255))).save(TEX/name)
save('housing_color.png',base);save('housing_roughness.png',rough)
save('housing_normal.png',(normal*.5+.5)*255)
save('housing_metallic.png',np.zeros((N,N))+2)
steel=Image.new('RGB',(N,N),(142,149,153));draw=ImageDraw.Draw(steel)
for i in range(2800):
    x=int(rng.integers(0,N));y=int(rng.integers(0,N));length=int(rng.integers(3,80))
    v=int(rng.integers(133,160));draw.line((x,y,x+length,y),fill=(v,v+3,v+5),width=1)
steel.save(TEX/'steel_color.png')
save('steel_roughness.png',np.clip(100+fine*13+coarse*4,0,255))
save('steel_metallic.png',np.zeros((N,N))+245)
save('steel_normal.png',(normal*.5+.5)*255)

# A small legible manufacturer/service plate, entirely fictional HC1 markings.
plate=Image.new('RGB',(1024,256),(39,44,46));d=ImageDraw.Draw(plate)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',42)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',24)
d.rectangle((6,6,1017,249),outline=(125,135,135),width=3)
d.text((28,22),'ARES / BULKHEAD 06',font=font,fill=(210,215,204))
d.text((28,98),'24V DC   |   IP67   |   3000K',font=small,fill=(167,180,171))
d.text((28,143),'S/N A3-0428    INSPECT  /  06',font=small,fill=(167,180,171))
d.text((28,186),'ISOLATE SUPPLY BEFORE SERVICE',font=small,fill=(180,163,113))
plate.save(TEX/'identification_color.png')
print(json.dumps({'selected':record['asset'],'beforeTriangles':count,'guardedFiles':len(guard),'source':record['actualImportedMesh']}))
