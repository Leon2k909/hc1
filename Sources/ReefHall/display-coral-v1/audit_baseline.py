from pathlib import Path
import json,math,hashlib
root=Path(__file__).absolute().parents[3];out=root/'output/reefhall/display-coral-v1';out.mkdir(parents=True,exist_ok=True);src=root/'Assets/models/maps/reefhall/reefhall_rotunda_tanks.obj'
e,n=430*math.cos(math.radians(200)),430*math.sin(math.radians(200));vertices=[];paint='';chosen=[];coords=[]
lines=src.read_text().splitlines(keepends=True)
for i,line in enumerate(lines):
    if line.startswith('v '):
        a,z,b=map(float,line.split()[1:]);vertices.append((-a,b,z))
    elif line.startswith('usemtl '):paint=line.split()[1]
    elif line.startswith('f ') and paint=='rh_coral_purple':
        points=[vertices[int(token.split('/')[0])-1] for token in line.split()[1:]]
        if all(abs(p[0]-e)<20 and abs(p[1]-n)<20 and 32<p[2]<64 for p in points):chosen.append(i);coords.extend(points)
assert len(chosen)==288,'Current colony changed; inspect before using this baseline'
lo=[min(p[k] for p in coords) for k in range(3)];hi=[max(p[k] for p in coords) for k in range(3)]
data=dict(faces=len(chosen),bounds=[lo,hi],face_lines=chosen,source=src.relative_to(root).as_posix(),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),paint='rh_coral_purple')
(out/'baseline.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='face_lines'},indent=2))
