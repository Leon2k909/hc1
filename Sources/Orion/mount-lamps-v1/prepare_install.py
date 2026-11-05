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
header,_=S.read_obj(ROOT/base);_,faces=S.read_obj(ROOT/'Assets/models/maps/orion/mount-lamps-v1/pad_preview.obj')
p=STAGE/base;p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,faces)
text=(ROOT/'Tools/orion_parts.py').read_text();needle='    box( m, c[0] - 3.5, c[0] + 3.5, c[1] - 3.5, c[1] + 3.5, c[2] - 3.5, c[2] + 3.5, "oa_lamp_warm" )'
assert text.count(needle)==1
text=text.replace(needle,'''    from orion_mount_lamps import CENTRES, build as draw_mount_lamp
    if any(np.allclose(c, position) for position in CENTRES):
        draw_mount_lamp(m,c)
    else:
    '''+needle,1);compile(text,'orion_parts.py','exec')
put('Tools/orion_parts.py',text);put('Tools/orion_mount_lamps.py',(HERE/'lamp.py').read_text())
plan=dict(guards=preview['guards'],files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
s=(ROOT/'Sources/ReefHall/office-desk-v1/install.cs.txt').read_text().replace('Sources/ReefHall/office-desk-v1/review','Sources/Orion/mount-lamps-v1/review').replace('Tools/reefhall_office_desk.py','Tools/orion_mount_lamps.py').replace('Workstations=1','MountLamps=4')
a=s.index('var allowed=');b=s.index('\nforeach',a);s=s[:a]+'var allowed=new[]{'+','.join(json.dumps(k) for k in plan['files'])+'};'+s[b:]
(HERE/'install.cs.txt').write_text(s)
