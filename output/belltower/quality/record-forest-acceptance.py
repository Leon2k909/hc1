"""Record the reviewed native forest save without modifying scene or asset files."""
import ast
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
STAGE=ROOT/'output/belltower/quality/forest-v1-staging'
OUT=ROOT/'output/belltower/quality/forest-v8-saved'
SOURCE=ROOT/'Sources/Belltower/landscape'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

before_path=ROOT/'output/belltower/quality/before-forest-v1/belltower.scene'
scene_path=ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
before=read(before_path)
after=read(scene_path)
old={o['__guid']:o for o in before['GameObjects']}
new={o['__guid']:o for o in after['GameObjects']}
cache=read(SOURCE/'forest.json')
assert set(new)-set(old)=={cache['__guid']}
assert not set(old)-set(new)
assert new[cache['__guid']]==cache
normalizations=collections.Counter()
prefab_remaps=[]

def compare(a,b,path):
    if isinstance(a,dict) and isinstance(b,dict):
        # Native resource IDs are per editor process; the asset paths must agree.
        if 'Id' in a and 'Id' in b and 'Path' in a and a.get('Path')==b.get('Path'):
            if a['Id']!=b['Id']:
                normalizations['resource_ids']+=1
            a={k:v for k,v in a.items() if k!='Id'}
            b={k:v for k,v in b.items() if k!='Id'}
        for key in a.keys()|b.keys():
            p=path+'/'+key
            if key=='__PrefabIdToInstanceId':
                # Preserve every existing mapping; only the engine's two
                # regenerated child IDs changed during this native save.
                x,y=a[key],b[key]
                assert all(x[k]==y[k] for k in x.keys()&y.keys()),p
                removed,added=set(x)-set(y),set(y)-set(x)
                assert len(removed)==len(added) and len(added)<=1,p
                if added:
                    prefab_remaps.append(dict(path=p,removed=sorted(removed),added=sorted(added)))
                continue
            if key=='ZombiesOnly' and key not in a and b[key] in (False,'False'):
                assert path.endswith('/Metadata') or a.get('__type')=='Facepunch.MapInformation',p
                normalizations['explicit_false_zombies_default']+=1
                continue
            assert key in a and key in b,p
            compare(a[key],b[key],p)
    elif isinstance(a,list) and isinstance(b,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):
            compare(x,y,path+'/'+str(i))
    else:
        assert a==b,(path,a,b)

for identity in old:
    compare(old[identity],new[identity],old[identity].get('Name',identity))
compare({k:v for k,v in before.items() if k!='GameObjects'},
        {k:v for k,v in after.items() if k!='GameObjects'},'Scene')
assert len(prefab_remaps)==2
town=next(o for o in old.values() if o.get('Name')=='Town')
assert town==new[town['__guid']], 'Town rendering and collision configuration changed'

# Exercise the actual generator cache reader without running the model build.
generator=ROOT/'Tools/belltower_map.py'
tree=ast.parse(generator.read_text(encoding='utf-8'))
reader=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='landscape_forest_object')
namespace={'Path':Path,'json':json,'__file__':str(generator)}
exec(compile(ast.Module(body=[reader],type_ignores=[]),str(generator),'exec'),namespace)
assert namespace['landscape_forest_object']()==cache

manifest=read(STAGE/'manifest.json')
native=read(STAGE/'native-resources.json')
audit=read(STAGE/'source-audit-saved.json')
assert native['ManifestSha256']==audit['manifest_sha256']==sha(STAGE/'manifest.json')
assert audit['scene_sha256']==sha(scene_path)
assert audit['forest_saved_in_scene'] and not audit['native_models_requiring_compile']
captures={}
for name in ('valley','west-ridge','terrace'):
    image=OUT/(name+'.png')
    assert image.is_file()
    captures[name]=dict(path=image.relative_to(ROOT).as_posix(),sha256=sha(image))

report=dict(scene_sha256=sha(scene_path),before_scene_sha256=sha(before_path),
    added_root=cache['__guid'],added_sectors=len(cache['Children']),removed_roots=0,
    existing_scene_values_preserved_except_native_serialization=True,
    native_serialization=dict(normalizations),prefab_child_remaps=prefab_remaps,
    town_rendering_and_collision_configuration_unchanged=True,
    generator_cache_matches_saved_group=True,captures=captures,
    runtime_performance='Not measured; editor performance sample is not a gameplay benchmark.')
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
accepted={**manifest,'revision':'forest-v8','accepted_date':'2026-10-15',
    'source_group_sha256':sha(SOURCE/'forest.json'),
    'staged_group_sha256':manifest['source_group_sha256'],
    'source_group':'Sources/Belltower/landscape/forest.json',
    'native_resource_report':'output/belltower/quality/forest-v1-staging/native-resources.json',
    'saved_verification':'output/belltower/quality/forest-v8-saved/verification.json',
    'visual_scope':'Nearby wooded hills have reviewed canopy silhouettes. Distant valley and overall AAA quality remain unfinished.',
    'runtime_performance_verified':False,
    'assets':{r['path']:r['sha256'] for r in read(STAGE/'import.json')},
    'landscape_inputs':{f'materials/belltower/vista/vista_{z}_{kind}.jpg':
        sha(ROOT/f'Assets/materials/belltower/vista/vista_{z}_{kind}.jpg')
        for z in 'bcd' for kind in ('color','normal')}}
(SOURCE/'forest-manifest.json').write_text(json.dumps(accepted,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('captures','prefab_child_remaps')},indent=2))
