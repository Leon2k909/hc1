"""Extract the saved Orion generator; stage private textures without editing Assets."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,re,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter
ROOT=Path.cwd();assert (ROOT/'hc1.sbproj').exists()
HERE=ROOT/'Sources/Orion/generator-trial-v1';OUT=ROOT/'output/asset-improvement-20261030/orion-generator'
TEX=HERE/'textures';TEX.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'Assets/models/maps/orion/orion_launch_deck.obj';doc=source.with_suffix('.vmdl')
assert re.findall(r'filename = "([^"]+\.obj)"',doc.read_text())[0]=='models/maps/orion/orion_launch_deck.obj'
origin=np.array((265.,1335.,240.));vs=[];uv=[];ns=[];paint='';groups=defaultdict(list)
for line in source.open():
    p=line.split()
    if not p:continue
    if p[0]=='v':a,z,n=map(float,p[1:]);vs.append(np.array((-a,n,z)))
    elif p[0]=='vt':uv.append(list(map(float,p[1:])))
    elif p[0]=='vn':a,z,n=map(float,p[1:]);ns.append([-a,n,z])
    elif p[0]=='usemtl':paint=p[1]
    elif p[0]=='f':
        ids=[[int(i)-1 for i in t.split('/')] for t in p[1:]];pts=np.array([vs[v]-origin for v,t,n in ids])
        # Match only the generator's eight exact box corners, excluding nearby pipes.
        corner=np.all(np.minimum(abs(pts-np.array((-65,-35,0))),abs(pts-np.array((65,35,70))))<.001)
        if corner:
            groups[paint].append({'vertices':pts.tolist(),'uv':[uv[t] for v,t,n in ids],'normals':[ns[n] for v,t,n in ids]})
assert sum(map(len,groups.values()))==12 and set(groups)=={'oa_dark','oa_steel'}, {k:len(v) for k,v in groups.items()}
(HERE/'before.json').write_text(json.dumps(groups,indent=2))
scene=ROOT/'Assets/scenes/maps/Orion/orion.scene';data=json.loads(scene.read_text())
def walk(go,enabled=True):
    enabled=enabled and go.get('Enabled',True)
    if enabled:
        for c in go.get('Components',[]):
            path=c.get('Model');path=path.get('Path') if isinstance(path,dict) else path
            if c.get('__enabled',True) and c.get('__type')=='Sandbox.ModelRenderer' and path=='models/maps/orion/orion_launch_deck.vmdl':yield go
    for child in go.get('Children',[]):yield from walk(child,enabled)
found=[go for go in data['GameObjects'] for go in walk(go)];assert len(found)==1
assert found[0]['Position']=='0,0,0' and found[0]['Rotation']=='0,0,0,1' and found[0]['Scale']=='1,1,1'
protected=[scene,source,doc,source.with_suffix('.mtl'),ROOT/'Tools/orion_map.py',ROOT/'Tools/orion_cable_reel.py']
protected+=list((ROOT/'Assets/materials/orion').rglob('*'))+list((ROOT/'Assets/models/props/orion').rglob('*'))
for folder in ('Sources/Ares/bulkhead-lamp-trial-v1','Sources/Ares/control-console-trial-v1','Sources/Orion/cable-reel-trial-v1'):
    protected+=list((ROOT/folder).rglob('*'))
protected=[p for p in protected if p.is_file() and '__pycache__' not in p.parts]
(HERE/'source-guard.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in protected},indent=2))
record={'asset':'Orion launch-deck enclosed generator','source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
 'modelDoc':doc.relative_to(ROOT).as_posix(),'scene':scene.relative_to(ROOT).as_posix(),'enabledRendererVerified':True,
 'planOrigin':origin.tolist(),'worldOrigin':[1335,-265,240],'beforeTriangles':12,'exactSavedGeometryUVsNormals':True,
 'outerEnvelopeInches':[130,70,70],'installed':False,'gameFilesWritten':False,'editorStatus':'No running project editor',
 'locationEvidence':'output/orion-cable-reel-installed-20261030/installed-reel-and-clear-stairs.png'}
(HERE/'provenance.json').write_text(json.dumps(record,indent=2))
shutil.copy2(ROOT/'Sources/Orion/cable-reel-trial-v1/geometry.py',HERE/'geometry.py')
N=1024;rng=np.random.default_rng(338);noise=rng.normal(0,1,(N,N)).astype(np.float32)
fine=gaussian_filter(noise,.65);broad=gaussian_filter(noise,19);broad/=broad.std()
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,255))).save(TEX/name)
for prefix,color,rough,metal in [('paint',(69,86,84),160,0),('skid',(37,43,45),172,0),('rubber',(24,27,29),185,0),
 ('zinc',(151,156,154),117,241),('steel',(107,111,113),126,245),('heat',(80,68,56),163,170)]:
    save(prefix+'_color.png',np.zeros((N,N,3))+color+fine[:,:,None]*4+broad[:,:,None]*2.4)
    save(prefix+'_roughness.png',rough+fine*10+broad*4);save(prefix+'_metallic.png',np.zeros((N,N))+metal)
    dy,dx=np.gradient(fine*.12);normal=np.stack((-dx*.45,dy*.45,np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    save(prefix+'_normal.png',(normal*.5+.5)*255)
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',size)
im=Image.new('RGB',(1536,384),(38,46,47));d=ImageDraw.Draw(im)
d.line((38,42,1498,42),fill=(185,164,82),width=9);d.text((42,68),'ORION  /  AUXILIARY POWER',font=font(78),fill=(212,219,210))
d.text((46,185),'GS-45    |    STANDBY GENERATING SET',font=font(46),fill=(166,179,174));d.text((46,272),'45 kVA   /   400 V   /   50 Hz',font=font(43),fill=(166,179,174));im.save(TEX/'brand.png')
im=Image.new('RGB',(1024,768),(13,26,30));d=ImageDraw.Draw(im)
d.rectangle((16,16,1007,115),fill=(35,65,65));d.text((38,34),'GS-45 / LOCAL',font=font(54),fill=(179,222,198))
for y,label,value in [(164,'FREQUENCY','50.0 Hz'),(290,'OIL PRESSURE','4.2 bar'),(416,'COOLANT','84 C')]:
    d.text((40,y),label,font=font(31),fill=(100,155,148));d.text((40,y+38),value,font=font(58),fill=(174,220,196))
d.rectangle((38,616,984,710),outline=(70,116,106),width=3);d.text((67,636),'AUTO READY / 01482 h',font=font(40),fill=(160,201,170));im.save(TEX/'display.png')
im=Image.new('RGB',(768,512),(194,170,66));d=ImageDraw.Draw(im)
d.polygon([(62,221),(172,38),(282,221)],fill=(31,34,30));d.text((150,88),'!',font=font(106),fill=(205,181,72))
d.text((315,55),'CAUTION',font=font(54),fill=(28,33,29));d.text((315,130),'HOT SURFACE',font=font(34),fill=(28,33,29))
d.line((37,257,730,257),fill=(30,33,29),width=4);d.text((40,286),'ISOLATE BEFORE SERVICE',font=font(43),fill=(28,33,29));d.text((40,365),'READ OPERATING INSTRUCTIONS',font=font(34),fill=(28,33,29));im.save(TEX/'warning.png')
print(json.dumps({'asset':record['asset'],'beforeTriangles':12,'protectedOriginals':len(protected),'enabledInSavedScene':True,'assetsWritten':False}))
