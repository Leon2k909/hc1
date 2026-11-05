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
base='Assets/models/maps/reefhall/reefhall_control.obj'
header,_=S.read_obj(ROOT/base);_,faces=S.read_obj(ROOT/'Assets/models/maps/reefhall/office-desk-v1/control_preview.obj')
p=STAGE/base;p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,faces)
text=(ROOT/'Tools/reefhall_map.py').read_text();a=text.index('    fbox( model, fr, -36, 36',text.index('def desk('));b=text.index('    fbox( model, fr, -9, 9, -34',a)
old=text[a:b]
replacement='''    if np.allclose(centre[:2], (1960,780)) and abs(yaw-180.0)<.001 and abs(z-208.0)<.001:
        from reefhall_office_desk import build as draw_office_workstation
        draw_office_workstation(model,centre,yaw,z)
        # Retain the original desktop collision; chairs below stay untouched.
        fbox(model,fr,-36,36,-16,16,z+28,z+30,{"default":None},WOOD)
    else:
'''+''.join('    '+line+'\n' for line in old.splitlines())
text=text[:a]+replacement+text[b:];compile(text,'reefhall_map.py','exec')
put('Tools/reefhall_map.py',text);put('Tools/reefhall_office_desk.py',(HERE/'desk.py').read_text())
plan=dict(guards=preview['guards'],files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/install.cs.txt').read_text().replace('bronze-planter-v1','office-desk-v1').replace('Tools/reefhall_bronze_planter.py','Tools/reefhall_office_desk.py').replace('Planters=2','Workstations=1')
a=s.index('var allowed=');b=s.index('\nforeach',a);s=s[:a]+'var allowed=new[]{'+','.join(json.dumps(k) for k in plan['files'])+'};'+s[b:]
(HERE/'install.cs.txt').write_text(s)
s=(ROOT/'Sources/Spillway/roof-fans-v1/retain_old.cs.txt').read_text().replace('Spillway/roof-fans-v1','ReefHall/office-desk-v1').replace('spillway/roof-fans-v1','reefhall/office-desk-v1').replace('legacy_fan','legacy_workstation').replace('/fan.vmdl','/desk.vmdl')
(HERE/'retain_old.cs.txt').write_text(s)
