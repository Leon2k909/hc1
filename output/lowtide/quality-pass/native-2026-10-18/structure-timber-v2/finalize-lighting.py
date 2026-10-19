"""Validate the native save and preserve the warehouse v5 lighting provenance."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'Sources/Lowtide/lighting'
sys.path.insert(0,str(ROOT/'Tools'))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)
def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):yield from diff(a.get(k),b.get(k),path+'/'+k)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)):yield from diff(x,y,path+'/'+str(i))
    elif a!=b:yield [path,a,b]

old=read(HERE/'lighting-before/lowtide.scene')
new=read(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')
changes=list(diff(old,new))
(HERE/'lighting/scene-diff.json').write_text(json.dumps(changes,indent=2)+'\n')
assert len(changes)==12, f'Expected six texture path/identity changes, found {len(changes)}: {changes}'
assert all(re.fullmatch(r'/GameObjects/8/Children/(24|25)/Components/0/(IrradianceTexture|DistanceTexture|RelocationTexture)/(Id|Path)',p) for p,a,b in changes)
stored=read(HERE/'lighting/stored.json')
for row in stored: assert sha(ROOT/'Assets'/(row['Target']+'_c'))==row['Hash']
volumes=[x for x in walk(new) if x.get('Name') in ('Warehouse East Bounced Light','Warehouse West Bounced Light')]
assert len(volumes)==2
for v in volumes:
    c=v['Components'][0]
    assert c['ProbeDensity']==12 and c['RuntimeIntensity']==4 and c['RuntimeContrast']==.85
    for k in ('IrradianceTexture','DistanceTexture','RelocationTexture'):
        assert c[k]['Path'] in [x['Target'] for x in stored]
before=read(HERE/'lighting-before/hashes.json')
source=SOURCE/'warehouse-lighting.json'
assert sha(source)==before[source.relative_to(ROOT).as_posix()]
data=read(source);data['volumes']=volumes
data['notes']='Refreshed 2026-10-18 through native IndirectLightVolume.BakeProbes after the accepted continuous structural timber and painted cast-iron materials. Warehouse floor/dressing fixes remain included. Both volumes retain 1200 probes, intensity 4 and contrast 0.85. Re-bake after static geometry, material, fixture or daylight changes.'
source.write_text(json.dumps(data,indent=2)+'\n')
import lowtide_lighting as lighting
expected=copy.deepcopy(new);lighting.apply_scene(expected)
assert expected==new, 'Canonical lighting integration changed the saved scene'
provenance=SOURCE/'bake-provenance.json';history=SOURCE/'bake-provenance-v4.json'
assert sha(provenance)==before[provenance.relative_to(ROOT).as_posix()]
if history.exists():assert history.read_bytes()==provenance.read_bytes()
else:shutil.copyfile(provenance,history)
previous=read(provenance)
plan=read(HERE/'promotion-plan.json')
for p,h in plan['resources'].items(): assert sha(ROOT/'Assets'/p)==h
record=dict(engineVersion='26.10.13a',observedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    nativeApi='IndirectLightVolume.BakeProbes',status='native_v5_bake_saved_pending_reload_review',
    geometrySha256={p:sha(ROOT/p) for p in previous['geometrySha256']},
    floorMaterialSha256=previous['floorMaterialSha256'],structureMaterialSha256=plan['resources'],
    sceneBeforeLightingSha256=before['Assets/scenes/maps/Lowtide/lowtide.scene'],
    savedSceneSha256=sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene'),lightingDataSha256=sha(source),
    textures=[dict(path='Assets/'+r['Target']+'_c',bytes=(ROOT/'Assets'/(r['Target']+'_c')).stat().st_size,sha256=r['Hash'],width=r['Width'],height=r['Height'],depth=r['Depth']) for r in stored],
    volumes=2,probesPerVolume=1200,runtimeIntensity=4,runtimeContrast=.85,
    evidence=HERE.relative_to(ROOT).as_posix()+'/lighting/verification.json',previousProvenance=history.relative_to(ROOT).as_posix(),
    rebakeWhen='Static warehouse geometry, materials, fixtures or daylight changes',performanceVerified=False)
provenance.write_text(json.dumps(record,indent=2)+'\n')
verification=dict(status=record['status'],scene_sha256=record['savedSceneSha256'],source_sha256=record['lightingDataSha256'],
    native_api=record['nativeApi'],compiled_textures=stored,intended_scene_edits=12,unrelated_scene_changes=0,
    canonical_lighting_idempotent=True,fresh_load_verified=False,performance_verified=False)
(HERE/'lighting/verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps({k:v for k,v in verification.items() if k!='compiled_textures'},indent=2))
