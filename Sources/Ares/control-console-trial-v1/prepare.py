"""Extract the actual installed Ares console and prepare private PBR resources."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,re,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/ares-control-console'
OUT.mkdir(parents=True,exist_ok=True);TEX=HERE/'textures';TEX.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
doc=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl'
imports=re.findall(r'filename = "([^"]+\.obj)"',doc.read_text())
assert imports==['models/maps/ares/crate-v2/dressing-base.obj'],imports
source=ROOT/'Assets'/imports[0];origin=np.array((230.,-440.,0.))
vertices=[];uv=[];normals=[];paint='';groups=defaultdict(list)
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
        ids=[[int(i)-1 for i in t.split('/')] for t in p[1:]]
        pts=np.array([vertices[v]-origin for v,t,n in ids])
        if np.all(pts.min(0)>=(-30.001,-16.001,-.001)) and np.all(pts.max(0)<=(30.001,18.001,64.001)):
            groups[paint].append({'vertices':pts.tolist(),'uv':[uv[t] for v,t,n in ids],'normals':[normals[n] for v,t,n in ids]})
count=sum(map(len,groups.values()));assert count==40,(count,{k:len(v) for k,v in groups.items()})
assert set(groups)=={'ar_steel','ar_gunmetal','ar_led_cyan','ar_screens','ar_bezel'},set(groups)
(HERE/'before.json').write_text(json.dumps(groups,indent=2))
scene=ROOT/'Assets/scenes/maps/Ares/ares.scene';assert 'models/maps/ares/ares_dressing.vmdl' in scene.read_text()
protected=[scene,doc,source,source.with_suffix('.mtl')]+sorted((ROOT/'Assets/materials/ares').glob('*'))
protected += sorted((ROOT/'Sources/Ares/bulkhead-lamp-trial-v1').rglob('*'))
protected=[p for p in protected if p.is_file() and '__pycache__' not in p.parts]
guard={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
(HERE/'source-guard.json').write_text(json.dumps(guard,indent=2))
record={'asset':'Ares central-hall floor-standing control console','source':source.relative_to(ROOT).as_posix(),
    'sourceSHA256':sha(source),'modelDoc':doc.relative_to(ROOT).as_posix(),'planOrigin':origin.tolist(),
    'worldOrigin':[-440,-230,0],'beforeTriangles':count,'exactSavedGeometryUVsNormals':True,
    'widthDepthHeightInches':[60,34,64],'frontDirectionLocal':'-Y','installed':False,'gameFilesWritten':False}
(HERE/'provenance.json').write_text(json.dumps(record,indent=2))

# Clone the existing approved screen atlas unchanged; retain its original UV tile.
for name in ('ar_screens_color.png','ar_screens_illum.png'):
    shutil.copy2(ROOT/'Assets/materials/ares'/name,TEX/name)

N=1024;rng=np.random.default_rng(135)
noise=rng.normal(0,1,(N,N)).astype(np.float32)
fine=gaussian_filter(noise,.7);broad=gaussian_filter(noise,16);broad/=broad.std()
dy,dx=np.gradient(fine*.22)
normal=np.stack((-dx*.35,dy*.35,np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,255))).save(TEX/name)
for prefix,color,rough,metal in [('paint',(150,155,151),164,0),('dark',(43,48,49),148,0),('steel',(145,150,153),112,245)]:
    base=np.zeros((N,N,3),np.float32)+color;base+=fine[:,:,None]*3+broad[:,:,None]*.6
    if prefix=='steel':base+=np.mean(noise,axis=1)[:,None,None]*80
    save(prefix+'_color.png',base);save(prefix+'_roughness.png',rough+fine*13+broad*2)
    save(prefix+'_metallic.png',np.zeros((N,N))+metal);save(prefix+'_normal.png',(normal*.5+.5)*255)

# An atlas for real engraved controls, panel identification and key legends.
atlas=Image.new('RGB',(2048,1024),(35,40,40));d=ImageDraw.Draw(atlas)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',58)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',35)
labels=['ARES / PROCESS CONTROL','LOCAL STATION 02','POWER   |   STATUS   |   ALARM',
        'ISOLATE SUPPLY BEFORE SERVICE','CONTROL ENABLE','ACKNOWLEDGE','SYSTEM RESET','EMERGENCY STOP']
for i,label in enumerate(labels):
    y=(i//2)*256;x=(i%2)*1024
    d.rectangle((x+5,y+5,x+1018,y+249),outline=(102,114,109),width=3)
    d.text((x+26,y+80),label,font=small if len(label)>24 else font,fill=(203,214,204))
atlas.save(TEX/'panel_labels.png')
keys=Image.new('RGB',(1024,1024),(37,42,43));d=ImageDraw.Draw(keys)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',66)
letters=['1','2','3','4','5','6','7','8','9','0','-','+','Q','W','E','R','T','Y','U','I','O','P','[',']','A','S','D','F','G','H','J','K','L',';','Z','X','C','V','B','N','M',',','.','/','ESC','DEL','ENT','CTL','ALT','UP','DN','OK','F1','F2','F3','F4','F5','F6','F7','F8']
for i,label in enumerate(letters):
    x=(i%8)*128;y=(i//8)*128
    box=d.textbbox((0,0),label,font=font);d.text((x+(128-box[2])/2,y+28),label,font=font,fill=(199,211,202))
keys.save(TEX/'key_legends.png')
print(json.dumps({'asset':record['asset'],'beforeTriangles':count,'protectedFiles':len(guard),'screenAtlasCopiedUnchanged':True}))
