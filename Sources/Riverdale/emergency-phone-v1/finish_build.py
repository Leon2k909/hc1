"""Finish a private preview and verify its baseline against current saved phone triangles."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).parent;sys.path.insert(0,str(HERE))
import build as B
ROOT=B.ROOT;OUT=B.OUT;STAGE=B.STAGE;DEST=B.DEST;MD=B.MD
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Render printed labels at their physical aspect before packing them into square atlas cells.
path=MD/'ep_print_color.png';labels=Image.open(path).convert('RGB');draw=ImageDraw.Draw(labels)
for i,w,h,bg,fg,title,sub in [(12,6.6,1.12,(34,39,37),(218,211,172),'EMERGENCY','PLANT TELEPHONE'),
 (13,4.25,1.10,(190,178,130),(30,36,31),'LIFT HANDSET','DIAL 222 - CONTROL'),
 (14,2.70,.93,(26,40,32),(123,157,119),'LINE READY','SECURE PLANT NETWORK'),
 (15,3.25,.60,(184,169,119),(39,43,36),'RIVERDALE','COMMUNICATIONS / U1-07')]:
    width=1536;height=round(width*h/w);tile=Image.new('RGB',(width,height),bg);d=ImageDraw.Draw(tile)
    for text,y,size,fontname in [(title,.33,.38,'arialbd.ttf'),(sub,.78,.21,'arial.ttf')]:
        font=ImageFont.truetype('C:/Windows/Fonts/'+fontname,round(height*size))
        while d.textbbox((0,0),text,font=font)[2]>width*.92:
            font=ImageFont.truetype('C:/Windows/Fonts/'+fontname,font.size-1)
        d.text((width/2,height*y),text,anchor='mm',font=font,fill=fg)
    row,col=divmod(i,4);labels.paste(tile.resize((512,512),Image.Resampling.LANCZOS),(col*512,row*512))
labels.save(path)
def triangles(path,transform=False):
    vs=[];uv=[];ns=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            x,z,n=map(float,line.split()[1:]);p=np.array((-x,n,z));vs.append(B.ORIGIN+p@B.BASIS if transform else p)
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            x,z,n=map(float,line.split()[1:]);normal=np.array((-x,n,z));ns.append(normal@B.BASIS if transform else normal)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            if path.name.startswith('riverdale_hall'):
                if paint not in ('rv_door_yellow','rv_hall_plastic','rv_hall_signs','rv_hall_led_red'):continue
                if any(not (993<=vs[v][0]<=1000.1 and 335<=vs[v][1]<=345 and 41<=vs[v][2]<=62) for v,t,n in ids):continue
            yield paint,tuple(sorted(tuple(np.round(vs[v],3))+tuple(np.round(uv[t],5))+tuple(np.round(ns[n],4)) for v,t,n in ids))
original_full=list(triangles(DEST/'before.obj',True))
key=lambda item:(item[0],tuple(tuple(v[:5]) for v in item[1]))
original=Counter(key(i) for i in original_full);assert sum(original.values())==126
current=Counter()
normal_error=0.;original_by_key={key(i):i for i in original_full}
for name in ('riverdale_hall_detail','riverdale_hall_fine'):
    for item in triangles(ROOT/f'Assets/models/maps/riverdale/{name}.obj'):
        k=key(item)
        if k in original:
            current[k]+=1
            normal_error=max(normal_error,max(abs(a-b) for v,w in zip(item[1],original_by_key[k][1]) for a,b in zip(v[5:],w[5:])))
assert not original-current,'Original phone changed; re-extract the actual baseline'
assert normal_error<.0015,normal_error
guards={p.relative_to(ROOT).as_posix():sha(p) for folder in ('Assets/models/maps/riverdale','Assets/materials/riverdale') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.png','.vmat')}
scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene';guards[scene.relative_to(ROOT).as_posix()]=sha(scene)
for paint in ('ep_yellow','ep_black','ep_metal','ep_dark','ep_red'):
    for channel in ('color','normal','rough','metal'):
        with Image.open(MD/f'{paint}_{channel}.png') as im:assert im.size==(2048,2048)
after=list(triangles(DEST/'after.obj'));doc=(DEST/'after.vmdl').read_text()
report=dict(status='proposal-not-installed',userApproved=False,installedInMap=False,originalRetained=True,
 resource=B.RESOURCE,materials=B.MAT,originalTriangles=126,proposedTriangles=len(after),originalMatchesCurrentSavedMeshAndUV=True,maximumReexportNormalQuantizationError=normal_error,
 selectedOriginalPlan=B.ORIGIN.tolist(),protectedSourceSHA256=guards,models={name:dict(sha256=sha(DEST/f'{name}.obj')) for name in ('before','after')},
 collisionBoxes=doc.count('_class = "PhysicsShapeBox"'),collisionHullFiles=doc.count('_class = "PhysicsHullFile"'),
 externalHallEditDetectedDuringBuild=True,nativeChecks='pending',allTexturesPowerOfTwo=True)
for p in (HERE/'candidate.json',OUT/'candidate.json'):p.write_text(json.dumps(report,indent=2)+'\n')
priorities={'.png':0,'.obj':1,'.mtl':2,'.vmat':3,'.vmdl':4}
files=[dict(path=p.relative_to(STAGE).as_posix(),sha256=sha(p)) for p in sorted(STAGE.rglob('*'),key=lambda p:(priorities.get(p.suffix,9),str(p))) if p.is_file()]
(OUT/'publish.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
print(json.dumps(dict(originalVerified=True,proposedTriangles=len(after),filesToPublish=len(files),mapEdited=False)))
