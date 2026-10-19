"""Bind the completed garden build to exact source, destination and collision inputs."""
from collections import Counter
import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import sys

platform._wmi=None
root=Path.cwd()
sys.path.insert(0,str(root/'Tools'))
from belltower_quality_models import collision_signature
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
options=parser.parse_args()
quality=root/'output/belltower/quality'
stage=quality/'models'/options.revision
manifest=json.loads((stage/'model-import.json').read_text())
checks=json.loads((quality/f'{options.revision}-geometry-checks.json').read_text())
assert manifest['spots']==94 and manifest['invalid_spots']==manifest['unreachable_spots']==0
assert checks['checks']==11 and checks['garden_collision_preserved'] and checks['shared_random_sequence_preserved']
hash_file=lambda p:sha256(p.read_bytes()).hexdigest()
assert all(hash_file(root/path)==fingerprint for path,fingerprint in checks['sources'].items())
extensions=['obj','mtl','vmdl'] if options.revision=='garden-v1' else ['obj']
allowed={f'models/maps/belltower/belltower_{side}.{ext}' for side in ['west','east'] for ext in extensions}
assert {f['path'] for f in manifest['files']}==allowed
if options.revision in ('garden-v2','garden-v3'):
    assert len(checks['cladding_trim_separation'])==3
    predecessor=quality/'models'/('garden-v1' if options.revision=='garden-v2' else 'garden-v2')/'native-import.json'
    previous=json.loads(predecessor.read_text())
    assert all(hash_file(root/'Assets'/f['path'])==f['sha256'] for f in previous['files'])
    manifest['predecessor_manifest']={'path':predecessor.relative_to(root).as_posix(),'sha256':hash_file(predecessor)}
    manifest['unchanged_model_inputs']=previous.get('unchanged_model_inputs',[])+[{'path':'Assets/'+f['path'],'sha256':f['sha256']} for f in previous['files'] if not f['path'].endswith('.obj')]
    assert all(hash_file(root/item['path'])==item['sha256'] for item in manifest['unchanged_model_inputs'])
    if options.revision=='garden-v3':
        assert checks['wheelbarrow_basin_clearance']['v2_intruding_samples']>0
        assert checks['wheelbarrow_basin_clearance']['v3_intruding_samples']==0
else:
    manifest['unchanged_model_inputs']=[]
manifest['revision']=options.revision
for file in manifest['files']:
    file['sha256']=hash_file(root/file['source'])
    file['expected_sha256']=hash_file(root/'Assets'/file['path'])
# Publish remaps before the new visual mesh so a watcher never sees an unknown material.
manifest['files'].sort(key=lambda f:(Path(f['path']).stem,{'mtl':0,'vmdl':1,'obj':2}[Path(f['path']).suffix[1:]]))
manifest['geometry_checks']=checks
manifest['source_hashes']={p:hash_file(root/p) for p in (
    'Tools/belltower_map.py','Tools/belltower_gardens.py','Tools/belltower_furniture.py',
    'Tools/belltower_architecture.py','Tools/belltower_detail.py','Tools/belltower_quality_models.py','Tools/map_kit.py')}
manifest['collision_inputs']=[]
for record in manifest['models']:
    name=record['name']
    a,b=stage/(name+'.vmdl'),root/'Assets/models/maps/belltower'/(name+'.vmdl')
    physics=lambda p:p.read_text().partition('_class = "PhysicsShapeList"')[2].partition('\n\t\t]\n')[0]
    assert physics(a)==physics(b)
    record['physics_sha256']=sha256(physics(b).encode()).hexdigest()
    for path in stage.glob(name+'_hulls_*.obj'):
        current=root/'Assets/models/maps/belltower'/path.name
        assert collision_signature(path)==collision_signature(current)
        manifest['collision_inputs'].append({'path':current.relative_to(root).as_posix(),'sha256':hash_file(current)})
    counts=Counter()
    paint=None
    for line in (stage/(name+'.obj')).open():
        if line.startswith('usemtl '): paint=line.strip().split()[1]
        elif line.startswith('f '): counts[paint]+=len(line.split())-3
    assert sum(counts.values())==record['triangles']
    record['first_material']='materials/belltower/ashlar.vmat'
    record['first_material_triangles']=counts['ashlar']
    record['new_material']='materials/gunsmith_range/bench_oak_endgrain.vmat'
material=root/'Assets/materials/gunsmith_range/bench_oak_endgrain.vmat'
dependencies=[material]+[root/'Assets'/p for p in re.findall(r'Texture\w+ "([^"]+)"',material.read_text()) if p.startswith('materials/gunsmith_range/')]
assert len(dependencies)==4 and all(p.is_file() for p in dependencies)
manifest['existing_material_dependencies']=[{'path':p.relative_to(root).as_posix(),'sha256':hash_file(p)} for p in dependencies]
(stage/'native-import.json').write_text(json.dumps(manifest,indent=2)+'\n')
checkpoint={'state':'staged; native review pending','models':manifest['models'],'files':len(manifest['files']),
            'gameplay_spots':94,'geometry_checks':11,'shared_random_sequence_preserved':True,'native_assets_replaced':False,
            'capture_views':['wheelbarrow','terrace'] if options.revision=='garden-v3' else ['terrace','coping','garden-shed','small-shed','garden-store','firewood','wheelbarrow'],
            'native_import':'Sources/Belltower/editor/import-gardens.cs.txt','native_verify':'Sources/Belltower/editor/verify-gardens.cs.txt',
            'manifest_sha256':hash_file(stage/'native-import.json'),
            'editor_window':'Offline correction prepared; wait for the next editor handoff before native changes.'}
(quality/f'{options.revision}-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
(quality/'garden-import-request.json').write_text(json.dumps({'revision':options.revision})+'\n')
print(json.dumps({'files':len(manifest['files']),'models':manifest['models'],'collision_inputs':len(manifest['collision_inputs']),
                  'existing_material_dependencies':len(dependencies),'native_assets_replaced':False},indent=2))
