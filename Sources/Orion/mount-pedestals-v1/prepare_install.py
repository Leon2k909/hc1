from pathlib import Path
import json,hashlib,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
preview=json.loads((OUT/'preview-plan.json').read_text())
for k,v in preview['guards'].items():assert sha(ROOT/k)==v,k
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/orion/orion_pad.obj'
header,_=S.read_obj(ROOT/base);_,faces=S.read_obj(ROOT/'Assets/models/maps/orion/mount-pedestals-v1/pad_preview.obj')
p=STAGE/base;p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,faces)
text=(ROOT/'Tools/orion_parts.py').read_text();needle='        box( m, q[0] - 14, q[0] + 14, q[1] - 10, q[1] + 10, zt, zt + 40, "oa_dark" )'
assert text.count(needle)==1
text=text.replace(needle,'        from orion_mount_pedestals import build as draw_service_pedestal\n        draw_service_pedestal(m,q)',1)
compile(text,'orion_parts.py','exec');put('Tools/orion_parts.py',text);put('Tools/orion_mount_pedestals.py',(HERE/'pedestal.py').read_text())
plan=dict(guards=preview['guards'],files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
s=(ROOT/'Sources/Orion/mount-lamps-v1/install.cs.txt').read_text().replace('Sources/Orion/mount-lamps-v1/review','Sources/Orion/mount-pedestals-v1/review').replace('Tools/orion_mount_lamps.py','Tools/orion_mount_pedestals.py').replace('MountLamps=4','ServicePedestals=4')
a=s.index('var allowed=');b=s.index('\nforeach',a);s=s[:a]+'var allowed=new[]{'+','.join(json.dumps(k) for k in plan['files'])+'};'+s[b:]
(HERE/'install.cs.txt').write_text(s)
s=(ROOT/'Sources/Orion/mount-lamps-v1/retire_old.cs.txt').read_text().replace('mount-lamps-v1','mount-pedestals-v1').replace('NewLightsKept','NewPedestalsKept');(HERE/'retire_old.cs.txt').write_text(s)
