"""Preserve the concurrent ceiling-fixture replacement in the sign preview."""
from pathlib import Path
import json,hashlib,collections,shutil
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shop-sign-v1';MODEL=REVIEW/'Assets/models/maps/riverside/shop-sign-v1'
m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=Path('C:/sbox-projects/hc1/shelving-review/Assets/models/maps/riverside/shelving-v1/store_without_shelving.obj');current=ROOT/m['source_model'];assert sha(baseline)==m['source_sha256']
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):faces.append((i,(paint,tuple(sorted(vs[int(p.split('/')[0])-1] for p in l.split()[1:])))))
    return lines,faces
oldlines,old=records(baseline);lines,new=records(current)
oldcount=collections.Counter(k for _,k in old);newcount=collections.Counter(k for _,k in new)
removed=oldcount-newcount;assert not newcount-oldcount
assert sum(removed.values())==28 and collections.Counter({p:sum(n for (paint,_),n in removed.items() if paint==p) for p in {k[0] for k in removed}})=={'rs_dark':24,'rs_lamp_cool':4}
nonfaces=lambda a:[l for l in a if not l.startswith('f ')]
assert nonfaces(oldlines)==nonfaces(lines) and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
_,oldsign=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in oldsign);assert not wanted-newcount
indices=set()
for i,k in new:
    if wanted[k]:indices.add(i);wanted[k]-=1
assert len(indices)==136 and not +wanted
target=MODEL/'store_without_shop_sign.obj';target.write_text(''.join(l for i,l in enumerate(lines) if i not in indices).replace('mtllib '+current.with_suffix('.mtl').name,'mtllib store_without_shop_sign.mtl'),encoding='utf-8')
shutil.copy2(current.with_suffix('.mtl'),MODEL/'store_without_shop_sign.mtl')
m['source_sha256']=sha(current)
for p in (target,MODEL/'store_without_shop_sign.mtl'):m['files'][str(p.relative_to(REVIEW)).replace('\\','/')]=sha(p)
(OUT/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
plan=json.loads((OUT/'lighting-plan.json').read_text());plan['saved_scene_hash']=sha(ROOT/'Assets/scenes/maps/Riverside/riverside.scene');(OUT/'lighting-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(OUT/'lighting-integration-baseline.json').write_text(json.dumps(dict(concurrent_ceiling_fixture_removal_preserved=True,removed_other_faces=28,sign_geometry_unchanged=True,current_source_hash=sha(current)),indent=2),encoding='utf-8')
print('Preserved the ceiling-fixture replacement; changed only the sign preview source and lighting baseline.')
