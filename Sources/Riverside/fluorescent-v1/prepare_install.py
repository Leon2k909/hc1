"""Stage removal of both exact original fluorescent fixtures from the current store input."""
from pathlib import Path
import collections,json,re,hashlib
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/fluorescent-v1'
m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['files'].items():
    if not any('/'+n+'.' in p for n in ('legacy_fixture','store_without_fixture')):assert sha(ROOT/p)==h,'Approved asset changed: '+p
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,old=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in old)
for _,(mat,pts) in old:
    wanted[(mat,tuple(sorted((round(x-130,3),y,round(z+130,3)) for x,y,z in pts)))]+=1
vmdl=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text()):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for _,k in faces):source=p;break
assert source,'Both original fixtures must still match the active store input.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==28 and not +wanted
before=OUT/'install-before';before.mkdir(exist_ok=True)
assert not (before/'source.obj').exists(),'An installation plan exists; inspect before retrying.'
for src,name in ((source,'source.obj'),(vmdl,'store.vmdl'),(ROOT/'Assets/scenes/maps/Riverside/riverside.scene','riverside.scene'),(ROOT/'Tools/riverside_map.py','riverside_map.py'),(ROOT/'Tools/riverside_parts.py','riverside_parts.py')):
    (before/name).write_bytes(src.read_bytes())
stage=OUT/'install-stage/store.obj';stage.parent.mkdir(exist_ok=True);stage.write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
plan=dict(source=source.relative_to(ROOT).as_posix(),source_before=sha(source),source_after=sha(stage),staged=stage.relative_to(ROOT).as_posix(),
          removed_triangles=28,model=m['resource'],positions=[[760,-150,145.4],[890,-280,145.4]],store_vmdl_before=sha(vmdl))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
