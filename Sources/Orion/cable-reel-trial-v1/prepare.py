"""Extract Orion's actual placeholder reel; prepare isolated review resources."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,re,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/orion-cable-reel';OUT.mkdir(parents=True,exist_ok=True)
TEX=HERE/'textures';TEX.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
doc=ROOT/'Assets/models/maps/orion/orion_launch_deck.vmdl'
source=ROOT/'Assets/models/maps/orion/orion_launch_deck.obj'
assert re.findall(r'filename = "([^"]+\.obj)"',doc.read_text())[0]=='models/maps/orion/orion_launch_deck.obj'
origin=np.array((380.,1320.,240.));vertices=[];uv=[];normals=[];paint='';groups=defaultdict(list)
for line in source.open():
    p=line.split()
    if not p:continue
    if p[0]=='v':
        a,z,n=map(float,p[1:]);vertices.append(np.array((-a,n,z)))
    elif p[0]=='vt':uv.append(list(map(float,p[1:])))
    elif p[0]=='vn':
        a,z,n=map(float,p[1:]);normals.append([-a,n,z])
    elif p[0]=='usemtl':paint=p[1]
    elif p[0]=='f':
        ids=[[int(i)-1 for i in t.split('/')] for t in p[1:]];pts=np.array([vertices[v]-origin for v,t,n in ids])
        if np.all(pts.min(0)>=(-26.001,-26.001,-.001)) and np.all(pts.max(0)<=(26.001,26.001,46.001)):
            groups[paint].append({'vertices':pts.tolist(),'uv':[uv[t] for v,t,n in ids],'normals':[normals[n] for v,t,n in ids]})
count=sum(map(len,groups.values()));assert count==28,(count,{k:len(v) for k,v in groups.items()})
assert set(groups)=={'oa_wall_dark'}
(HERE/'before.json').write_text(json.dumps(groups,indent=2))
scene=ROOT/'Assets/scenes/maps/Orion/orion.scene';data=json.loads(scene.read_text())
def walk(go,enabled=True):
    enabled=enabled and go.get('Enabled',True)
    if enabled:
        for c in go.get('Components',[]):
            if c.get('__enabled',True) and c.get('__type')=='Sandbox.ModelRenderer' and c.get('Model')=='models/maps/orion/orion_launch_deck.vmdl':yield go
    for child in go.get('Children',[]):yield from walk(child,enabled)
found=[go for go in data['GameObjects'] for go in walk(go)];assert len(found)==1
assert found[0]['Position']=='0,0,0' and found[0]['Rotation']=='0,0,0,1' and found[0]['Scale']=='1,1,1'
protected=[scene,doc,source,source.with_suffix('.mtl'),ROOT/'Tools/orion_map.py']
protected+=sorted((ROOT/'Assets/materials/orion').glob('*'))
for previous in ('bulkhead-lamp-trial-v1','control-console-trial-v1'):
    protected+=sorted((ROOT/'Sources/Ares'/previous).rglob('*'))
protected=[p for p in protected if p.is_file() and '__pycache__' not in p.parts]
scans=ROOT/'Assets/materials/belltower/scans'
for source_name,dest_name in [('brown_planks_03_diffuse_4k.png','wood_color.png'),('brown_planks_03_rough_4k.png','wood_roughness.png'),('brown_planks_03_nor_gl_4k.png','wood_normal.png')]:
    shutil.copy2(scans/source_name,TEX/dest_name);protected.append(scans/source_name)
(HERE/'source-guard.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in protected},indent=2))
record={'asset':'Orion launch-deck cable reel','source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
    'modelDoc':doc.relative_to(ROOT).as_posix(),'scene':scene.relative_to(ROOT).as_posix(),'enabledRendererVerified':True,
    'planOrigin':origin.tolist(),'worldOrigin':[1320,-380,240],'beforeTriangles':count,
    'beforeGeometry':'Open 14-sided cylinder; no top or bottom faces','exactSavedGeometryUVsNormals':True,
    'outerEnvelopeInches':{'diameter':52,'height':46},'installed':False,'gameFilesWritten':False}
(HERE/'provenance.json').write_text(json.dumps(record,indent=2))

# The private helper module is bundled with this proposal; earlier sources stay untouched.
assert (HERE/'geometry.py').exists()
N=1024;rng=np.random.default_rng(205);noise=rng.normal(0,1,(N,N)).astype(np.float32)
fine=gaussian_filter(noise,.6);broad=gaussian_filter(noise,12);broad/=broad.std()
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,255))).save(TEX/name)
dy,dx=np.gradient(fine*.13);normal=np.stack((-dx*.28,dy*.28,np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
for prefix,color,rough,metal in [('cable',(27,30,31),153,0),('zinc',(130,136,137),133,235),('oxide',(86,70,52),179,105)]:
    a=np.zeros((N,N,3),np.float32)+color;a+=fine[:,:,None]*4+broad[:,:,None]*(1.8 if prefix=='cable' else 5.0)
    save(prefix+'_color.png',a);save(prefix+'_roughness.png',rough+fine*12+broad*3)
    save(prefix+'_normal.png',(normal*.5+.5)*255);save(prefix+'_metallic.png',np.zeros((N,N))+metal)

# A separate cut-grain material for the exposed ends of the sawn boards.
yy,xx=np.mgrid[0:N,0:N].astype(np.float32)/N
radius=np.sqrt(((xx-.23)*1.2)**2+((yy+1.5)*.28)**2)
rings=np.sin(radius*185+gaussian_filter(noise,7)*4)
grain=np.maximum(0,rings)**9
end=np.zeros((N,N,3),np.float32)+np.array((113,108,96))
end-=grain[:,:,None]*11;end+=fine[:,:,None]*4+broad[:,:,None]*1.1
height=grain*.04+fine*.02;dy,dx=np.gradient(height)
normal=np.stack((-dx*2,dy*2,np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
save('endgrain_color.png',end);save('endgrain_roughness.png',183+grain*7+fine*9)
save('endgrain_normal.png',(normal*.5+.5)*255)

label=Image.new('RGB',(1024,512),(200,192,158));d=ImageDraw.Draw(label)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',69);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',37)
d.rectangle((10,10,1013,501),outline=(54,58,51),width=8)
d.text((40,35),'ORION / CABLE',font=font,fill=(46,52,44));d.text((40,140),'DRUM 0148   |   0.6 / 1kV',font=small,fill=(46,52,44))
d.text((40,208),'LENGTH  240 m   /   4 x 70',font=small,fill=(46,52,44));d.text((40,280),'KEEP DRY  /  LIFT AT BORE',font=small,fill=(46,52,44))
for x in range(46,975,8):
    if rng.random()>.35:d.rectangle((x,362,x+int(rng.integers(2,6)),454),fill=(45,50,44))
label.save(TEX/'inventory_label.png')
print(json.dumps({'asset':record['asset'],'beforeTriangles':count,'protectedOriginals':len(protected),'enabledInSavedScene':True}))
