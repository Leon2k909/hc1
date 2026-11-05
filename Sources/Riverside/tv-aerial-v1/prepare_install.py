"""Recheck the approved aerial and stage only its exact old face removal."""
from pathlib import Path
import collections,json,re,hashlib
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/tv-aerial-v1'
m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['files'].items():
    if not any('/'+n+'.' in p for n in ('legacy_aerial','low_without_aerial')):assert sha(ROOT/p)==h,'Approved asset changed: '+p
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,old=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in old)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_low.vmdl';source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text()):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for _,k in faces):source=p;break
assert source,'Original T2 aerial must still match the active lowland input.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==52 and not +wanted
before=OUT/'install-before';before.mkdir(exist_ok=True)
assert not (before/'source.obj').exists(),'Installation already prepared; inspect before retrying.'
for src,name in ((source,'source.obj'),(vmdl,'low.vmdl'),(ROOT/'Assets/scenes/maps/Riverside/riverside.scene','riverside.scene'),(ROOT/'Tools/riverside_map.py','riverside_map.py'),(ROOT/'Tools/riverside_parts.py','riverside_parts.py')):
    (before/name).write_bytes(src.read_bytes())
stage=OUT/'install-stage/low.obj';stage.parent.mkdir(exist_ok=True);stage.write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
plan=dict(source=source.relative_to(ROOT).as_posix(),source_before=sha(source),source_after=sha(stage),staged=stage.relative_to(ROOT).as_posix(),
          removed_triangles=52,model=m['resource'],position=m['position'],low_vmdl_before=sha(vmdl),triangles=m['triangles'])
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
