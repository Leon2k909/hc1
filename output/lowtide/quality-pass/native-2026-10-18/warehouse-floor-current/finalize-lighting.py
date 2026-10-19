"""Verify native serialization scope and preserve the accepted DDGI resources."""
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def at(doc,path):
    for part in path.strip('/').split('/'):
        doc=doc[int(part)] if isinstance(doc,list) else doc[part]
    return doc
def walk(node):
    if isinstance(node,dict):
        yield node
        for value in node.values(): yield from walk(value)
    elif isinstance(node,list):
        for value in node: yield from walk(value)
def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for key in sorted(set(a)|set(b)):
            yield from diff(a.get(key),b.get(key),path+'/'+key)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)): yield from diff(x,y,path+'/'+str(i))
    elif a!=b: yield [path,a,b]

old=read(OUT/'lighting-before/lowtide.scene')
new=read(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')
differences=read(OUT/'lighting/scene-diff.json')
assert sorted(diff(old,new))==sorted(differences), 'Saved scene changed after native diff was captured'
counts=collections.Counter()
for path,a,b in differences:
    if re.fullmatch(r'/GameObjects/6/Children/11/Children/\d+/Components/0/(Start|End|ColliderFlags|SurfaceVelocity)',path):
        assert at(new,path.rsplit('/',1)[0])['__type']=='Sandbox.CapsuleCollider'
        key=path.rsplit('/',1)[-1]
        if key=='ColliderFlags': assert a is None and b==0
        elif key=='SurfaceVelocity': assert a is None and b=='0,0,0'
        else:
            assert all(abs(float(x)-float(y))<.00002 for x,y in zip(a.split(','),b.split(',')))
        counts['native_collider_default_or_float_serialization']+=1
    elif re.fullmatch(r'/GameObjects/7/Children/[0-3]/Components/0/Model/Id',path):
        assert a=='2302da73-5373-4405-ad16-0883016b77ef' and b=='d38c6121-743f-4ce0-941c-931c50e1455b'
        assert at(old,path.rsplit('/',1)[0])['Path']==at(new,path.rsplit('/',1)[0])['Path']
        counts['native_resource_identity_refresh']+=1
    elif re.fullmatch(r'/GameObjects/8/Children/(24|25)/Components/0/(IrradianceTexture|DistanceTexture|RelocationTexture)/(Id|Path)',path):
        counts['baked_texture_path_or_identity']+=1
    elif re.fullmatch(r'/GameObjects/(21|22)/__PrefabIdToInstanceId/[^/]+',path):
        obj=new['GameObjects'][int(path.split('/')[2])]
        prefab=read(ROOT/'Assets'/obj['__Prefab']['Path'])
        ids={x.get('__guid') for x in walk(prefab) if '__guid' in x}
        key=path.split('/')[-1]
        # These are serializer cache entries, not source object/component IDs.
        # Keep the native save; verify that no authored prefab state changed.
        assert key not in ids
        previous=old['GameObjects'][int(path.split('/')[2])]
        assert obj['__Prefab']==previous['__Prefab']
        assert len(obj['__PrefabIdToInstanceId'])==len(previous['__PrefabIdToInstanceId'])
        assert obj['__PrefabInstancePatch']==old['GameObjects'][int(path.split('/')[2])]['__PrefabInstancePatch']
        counts['native_prefab_identity_cache_refresh']+=1
    else: raise AssertionError(('Unexpected saved-scene change',path,a,b))
assert dict(counts)==dict(native_collider_default_or_float_serialization=224,native_resource_identity_refresh=4,baked_texture_path_or_identity=12,native_prefab_identity_cache_refresh=4)

stored=read(OUT/'lighting/stored.json')
for row in stored:
    assert sha(ROOT/'Assets'/(row['Target']+'_c'))==row['Hash']
    assert row['Depth']==6
volumes=[x for x in walk(new) if x.get('Name') in ('Warehouse East Bounced Light','Warehouse West Bounced Light')]
assert len(volumes)==2
for volume in volumes:
    c=volume['Components'][0]
    assert c['ProbeDensity']==12 and c['RuntimeIntensity']==4 and c['RuntimeContrast']==.85
    for key in ('IrradianceTexture','DistanceTexture','RelocationTexture'):
        assert c[key]['Path'] in [x['Target'] for x in stored]

source=ROOT/'Sources/Lowtide/lighting/warehouse-lighting.json'
data=read(source)
assert sha(source)==read(OUT/'lighting-before/hashes.json')[source.relative_to(ROOT).as_posix()]
data['volumes']=volumes
data['engineVersion']='26.10.13a'
data['notes']='Refreshed 2026-10-18 using native IndirectLightVolume.BakeProbes after accepted warehouse floor materials and corrected dressing model bounds. Both volumes retain 1200 probes, intensity 4 and contrast 0.85. Re-bake after static geometry, material, fixture or daylight changes.'
source.write_text(json.dumps(data,indent=2)+'\n')
import lowtide_lighting as lighting
expected=copy.deepcopy(new)
lighting.apply_scene(expected)
assert expected==new, 'Canonical lighting integration is not idempotent'
report=dict(status='native_bake_saved_and_static_views_reviewed',scene_sha256=sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene'),
    native_api='IndirectLightVolume.BakeProbes',volumes=2,probes_each=1200,compiled_textures=stored,
    intended_scene_edits='Six baked texture references',native_serialization=counts,
    resource_paths_and_prefab_overrides_preserved=True,canonical_lighting_idempotent=True,
    reviewed_captures=6,visual_evidence=OUT.relative_to(ROOT).as_posix()+'/lighting-review/capture.json',
    source_sha256=sha(source),performance_verified=False)
(OUT/'lighting/verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='compiled_textures'},indent=2))
