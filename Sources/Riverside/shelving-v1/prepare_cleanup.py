"""Stage deletion of the superseded counter only, retaining all shared store data."""
from pathlib import Path
import collections,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shelving-v1';stage=OUT/'cleanup-stage';stage.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def records(path):
    lines=path.read_text().splitlines(keepends=True);vertices=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):faces.append((i,(paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,old=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(key for _,key in old);assert sum(wanted.values())==96
files={};before={}
for source in (ROOT/'Assets/models/maps/riverside').rglob('*.obj'):
    lines,faces=records(source);available=collections.Counter(key for _,key in faces)
    if wanted-available:continue
    removed=[i for i,key in faces if key in wanted];assert len(removed)==96
    relative=str(source.relative_to(ROOT)).replace('\\','/');target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(line for i,line in enumerate(lines) if i not in set(removed)),encoding='utf-8')
    files[relative]=sha(target);before[relative]=sha(source)
assert files,'No remaining legacy counter geometry found; inspect before retrying'
legacy=ROOT/'Assets/models/maps/riverside/shelving-v1'
delete=[str(p.relative_to(ROOT)).replace('\\','/') for p in legacy.glob('legacy_shelving*') if p.is_file()]
assert all(Path(p).name in ('legacy_shelving.obj','legacy_shelving.mtl','legacy_shelving.vmdl','legacy_shelving.obj.meta','legacy_shelving.vmdl.meta','legacy_shelving.vmdl_c') for p in delete)
plan=dict(before=before,files=files,delete={p:sha(ROOT/p) for p in delete},removed_triangles_per_source=96)
(OUT/'cleanup-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps(dict(patched_sources=list(files),delete=delete),indent=2))
