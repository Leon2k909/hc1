from pathlib import Path
import hashlib,json,collections,re
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/cerroblanco/courtyard-bench-native-review'
source=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'
plan=json.loads((ROOT/'output/cerroblanco/courtyard-bench-v1/geometry-checks.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['source_sha256'],'Dressing changed since candidate built'
old=(source.with_suffix('.vmdl')).read_text();new=(ROOT/'Assets/models/maps/cerroblanco/courtyard-bench-v1/courtyard_dressing.vmdl').read_text()
if 'PhysicsShapeList' in old:assert old.split('PhysicsShapeList',1)[1]==new.split('PhysicsShapeList',1)[1]
def keys(path):
    vs=[];m='';out=[]
    for l in path.read_text().splitlines():
        if l.startswith('v '):vs.append(tuple(float(x) for x in l.split()[1:]))
        elif l.startswith('usemtl '):m=l.split()[1]
        elif l.startswith('f '):out.append((m,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return collections.Counter(out)
a=keys(source);b=keys(ROOT/'Assets/models/maps/cerroblanco/courtyard-bench-v1/courtyard_dressing.obj')
assert sum((a-b).values())==70
assert sum((b-a).values())==plan['added_triangles']
result={'source_still_matches_candidate':True,'removed_triangles':sum((a-b).values()),'added_triangles':sum((b-a).values()),'unrelated_faces_preserved':sum((a&b).values()),'physics_preserved':True}
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(result)
