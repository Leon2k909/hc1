"""Rebase the approved counter over the concurrent porch-light removal only."""
from pathlib import Path
import json,hashlib,collections,subprocess,sys
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/counter-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
def records(path):
    lines=path.read_text().splitlines();vertices=[tuple(round(float(v),3) for v in line.split()[1:4]) for line in lines if line.startswith('v ')];paint='';faces=[]
    for line in lines:
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):faces.append((paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in line.split()[1:]))))
    return lines,collections.Counter(faces)
preview=REVIEW/'Assets/models/maps/riverside/counter-v1/store_without_counter.obj'
before_lines,before=records(preview);after_lines,after=records(ROOT/manifest['source_model'])
_,counter=records(OUT/'legacy-absolute.obj')
added=after-before;removed=before-after
assert added==counter,'Unexpected new geometry in active store input'
assert sum(removed.values())==12 and {key[0] for key in removed}=={'rs_porch_light'},'Unreviewed change in active store geometry'
nonfaces=lambda lines:[l for l in lines if not l.startswith(('f ','mtllib ','usemtl '))]
assert nonfaces(before_lines)==nonfaces(after_lines),'Vertex/UV/normal data changed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
approved={p:h for p,h in manifest['files'].items() if 'store_without_counter' not in p}
(OUT/'review-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
subprocess.run(['rtk','proxy',sys.executable,str(HERE/'build.py')],cwd=REVIEW,check=True)
assert all(sha(REVIEW/p)==h for p,h in approved.items()),'Approved model or texture changed'
(OUT/'integration-baseline.json').write_text(json.dumps(dict(approved_counter_unchanged=True,concurrent_change='12 old rs_porch_light triangles removed; retained',old_counter_triangles=12,new_source_hash=sha(ROOT/manifest['source_model'])),indent=2),encoding='utf-8')
print('Preserved the porch-light removal; approved counter meshes/materials are byte-identical.')
