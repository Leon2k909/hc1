"""Cut the approved office AC's exact faces from the current input; stage only that OBJ change."""
from pathlib import Path
import json,hashlib,collections,re
ROOT=Path(__file__).absolute().parents[3]
OUT=ROOT/'output/riverside/roof-ac-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in manifest['files'].items():
    if '/legacy_ac.' not in p and '/pad_without_ac.' not in p:assert sha(ROOT/p)==h,'Approved asset changed: '+p
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';result=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,result
_,old=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in old)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_pad.vmdl';source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text()):
    path=ROOT/'Assets'/resource
    if not path.exists():continue
    lines,faces=records(path)
    if not wanted-collections.Counter(k for _,k in faces):source=path;break
assert source,'Old office AC absent or changed; inspect installation before retrying.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==24 and not +wanted
backup=OUT/'install-before';backup.mkdir(exist_ok=True)
assert not (backup/'source.obj').exists(),'Install preparation already exists; inspect the existing plan.'
(backup/'source.obj').write_bytes(source.read_bytes());(backup/'pad.vmdl').write_bytes(vmdl.read_bytes())
(backup/'riverside.scene').write_bytes((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_bytes())
target=OUT/'install-stage/pad.obj';target.parent.mkdir(exist_ok=True)
target.write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
plan=dict(source=source.relative_to(ROOT).as_posix(),source_before=sha(source),source_after=sha(target),staged=target.relative_to(ROOT).as_posix(),
          removed_triangles=24,model=manifest['resource'],position=manifest['position'],pad_vmdl_before=sha(vmdl))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
