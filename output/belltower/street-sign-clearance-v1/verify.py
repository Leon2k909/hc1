import ast
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[3]
base=root/'output/belltower/street-sign-clearance-v1'
manifest=json.loads((base/'stage/manifest.json').read_text())
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

# Other chats are editing this shared generator. Verify our exact two function
# bodies against the saved pre-edit source instead of overwriting their work.
expected=(base/'before-source/Tools/belltower_map.py').read_text()
expected=expected.replace('    wall.fixtures. Drawn only. """',
                         '    wall.fixtures. Projecting stone mouldings must also clear its whole slab.\n    Drawn only. """')
expected=expected.replace('        for z0 in ( 110.0, 134.0, 148.0 ):\n',
    '        for z0 in ( 110.0, 134.0, 148.0 ):\n'
    '            if any( a < r0+w+2 and b > r0-2 and c < z0+h+2 and d > z0-2\n'
    '                    for a,b,c,d in getattr( wall, "plaque_obstacles", () ) ):\n'
    '                continue\n')
needle='                slab_at( model, wall, r, c0, 0.0, 2.0, z, z + 6, paint )\n'
expected=expected.replace(needle,needle+
    '                wall.plaque_obstacles = list( getattr( wall, "plaque_obstacles", () ) ) + [ ( r, c0, z, z+6 ) ]\n')
def functions(text):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body
            if isinstance(n,ast.FunctionDef) and n.name in ('street_plaque','bands')}
assert functions(expected)==functions((root/'Tools/belltower_map.py').read_text())
sys.path.insert(0,str(root/'Tools'))
import belltower_stage_street_sign as stage
assert stage.placement_check()==manifest['placement']
current={p:sha(root/p)==r['after'] for p,r in manifest['files'].items()}
protected={p:sha(root/p)==h for p,h in manifest['protected_sha256'].items()}
sources={p:sha(root/p)==h for p,h in manifest['source_sha256'].items() if p!='Tools/belltower_map.py'}
def slab_faces(path,side):
    vertices={}
    index=0
    for line in path.open('rb'):
        if line.startswith(b'v '):
            index+=1
            point=tuple(map(float,line.split()[1:]))
            if stage.in_slab((point[0],point[1]-stage.RISE,point[2]),side):
                vertices[index]=point
    material=None
    faces=Counter()
    for line in path.open('rb'):
        if line.startswith(b'usemtl '):
            material=line.split()[1]
        elif line.startswith(b'f '):
            ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            touched=set(ids)&vertices.keys()
            if touched:
                assert touched==set(ids)
                faces[(material,tuple(sorted(vertices[i] for i in ids)))]+=1
    return faces
slabs={}
for p,row in manifest['files'].items():
    side='west' if 'west' in p else 'east'
    intended=slab_faces(root/row['source'],side)
    actual=slab_faces(root/p,side)
    assert intended and actual==intended,(p,'The actual raised slab no longer matches the publication')
    slabs[p]={'triangles':sum(actual.values()),'matches_published_slab':True}
q=root/'output/belltower/quality/street-sign-clearance-v1-after'
captures={v:{'image':(q/(v+'.png')).relative_to(root).as_posix(),
             'sha256':sha(q/(v+'.png')),
             'all_state_restored':all(json.loads((q/(v+'-restore.json')).read_text()).values())}
          for v in ('west','west-oblique','east')}
compiled={}
for side in ('west','east'):
    path=root/f'Assets/models/maps/belltower/belltower_{side}.vmdl_c'
    # The render imports are the actual VMDL inputs. Canonical authoring OBJs
    # may receive unrelated, preserved crate edits from the main chat afterward.
    inputs=[root/p for p in manifest['files'] if f'/{side}/' in p]
    compiled[side]={'exists':path.exists(),
        'modified_utc':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),
        'newer_than_changed_inputs':path.stat().st_mtime>=max(p.stat().st_mtime for p in inputs)}
assert all(ok for p,ok in current.items() if '/compiler-safe/' in p) and all(sources.values())
assert all(v['all_state_restored'] for v in captures.values())
assert all(v['exists'] and v['newer_than_changed_inputs'] for v in compiled.values())
report={'revision':manifest['revision'],'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'placement':manifest['placement'],'runtime_files_match':current,'actual_slabs':slabs,
    'protected_file_count':len(protected),'protected_mismatches':[p for p,ok in protected.items() if not ok],
    'other_authoring_sources_match':sources,'plaque_and_band_function_bodies_match':True,
    'current_map_generator_sha256':sha(root/'Tools/belltower_map.py'),
    'concurrent_change_scope':'Subsequent crate work changed canonical OBJs, separate wood hulls, and iron/plank imports. The raised slabs still match the publication in both canonical OBJs; all four referenced plaque imports remain byte-identical. No shared work was reverted.',
    'shared_map_generator_received_unrelated_changes_since_import':sha(root/'Tools/belltower_map.py')!=manifest['source_sha256']['Tools/belltower_map.py'],
    'native_import':json.loads((base/'native-import.json').read_text()),'compiled_models':compiled,
    'explicit_compile_call':'West asset_compile timed out; no blind retry. Both watcher-built resources are newer than imported inputs; both loaded models were visually reviewed in the saved scene.',
    'native_views':captures,'all_non_plaque_bytes_exact':all(r['all_unrelated_source_bytes_preserved'] for r in manifest['files'].values()),
    'triangle_count_unchanged':all(r['triangles_before']==r['triangles_after'] for r in manifest['files'].values()),
    'effective_gpu_exposure_verified':False}
(base/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'verified':True,'runtime_files':len(current),'protected_files':len(protected),
                  'views_reviewed':list(captures),'compiled_resources_current':True}))
