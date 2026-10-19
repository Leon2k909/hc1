"""Read-only candidate or saved-forest checks; no native assets or scene edits."""
import argparse
import hashlib
import json
import math
from pathlib import Path

root=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--saved',action='store_true')
args=parser.parse_args()
stage=root/'output/belltower/quality/forest-v1-staging'
manifest=json.loads((stage/'manifest.json').read_text())
records=json.loads((stage/'import.json').read_text())
group=json.loads((stage/'forest.json').read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha(root/manifest['generator'])==manifest['generator_sha256']
assert sha(stage/'forest.json')==manifest['source_group_sha256']
assert sha(root/'Sources/Belltower/generated/forest-trees-v1.png')==manifest['atlas_sha256']
assert len({r['path'] for r in records})==len(records)
for record in records:
    assert sha(root/record['source'])==record['sha256'], record['source']
    assert sha(root/'Assets'/record['path'])==record['sha256'], record['path']

models={r['path'] for r in records if r['path'].endswith('.vmdl')}
renderers=[child['Components'][0] for child in group['Children']]
assert all(len(child['Components'])==1 for child in group['Children'])
assert all(r['__type']=='Sandbox.ModelRenderer' and r['RenderType']=='Off' for r in renderers)
assert {r['Model'] for r in renderers}==models
assert len(models)==manifest['sectors']
vertices=triangles=0
stale=[]
for relative in sorted(models):
    asset=root/'Assets'/relative
    assert 'PhysicsShape' not in asset.read_text()
    mesh=asset.with_suffix('.obj')
    v=uv=n=f=0
    with mesh.open() as stream:
        for line in stream:
            bits=line.split()
            if not bits:
                continue
            if bits[0] in ('v','vt','vn'):
                values=[float(x) for x in bits[1:]]
                assert all(math.isfinite(x) for x in values), relative
                if bits[0]=='v':
                    v+=1
                elif bits[0]=='vt':
                    uv+=1
                    assert all(0<=x<=1 for x in values), relative
                else:
                    n+=1
            elif bits[0]=='f':
                assert len(bits)==4, relative
                for token in bits[1:]:
                    vi,ti,ni=map(int,token.split('/'))
                    assert 1<=vi<=v and 1<=ti<=uv and 1<=ni<=n, relative
                f+=1
    assert v%4==0 and f==v//2 and uv==32 and n==1, relative
    vertices+=v
    triangles+=f
    compiled=Path(str(asset)+'_c')
    if not compiled.exists() or compiled.stat().st_mtime<max(asset.stat().st_mtime,mesh.stat().st_mtime):
        stale.append(relative)

assert triangles==manifest['triangles'] and vertices//4==manifest['trees']
scene=root/'Assets/scenes/maps/Belltower/belltower.scene'
saved=json.loads(scene.read_text())
woodland=[o for o in saved['GameObjects'] if o.get('Name')=='Distant woodland']
if args.saved:
    assert len(woodland)==1 and woodland[0]['__guid']==group['__guid']
    cache=root/'Sources/Belltower/landscape/forest.json'
    assert json.loads(cache.read_text())==woodland[0], 'Generator cache differs from the saved group'
    children=woodland[0]['Children']
    assert len(children)==manifest['sectors']
    assert {c['__guid'] for c in children}=={c['__guid'] for c in group['Children']}
    assert all(len(c['Components'])==1 for c in children)
    components=[c['Components'][0] for c in children]
    assert all(c['__type']=='Sandbox.ModelRenderer' and c['RenderType']=='Off' for c in components)
    paths={c['Model']['Path'] if isinstance(c['Model'],dict) else c['Model'] for c in components}
    assert paths==models
    native=json.loads((stage/'native-resources.json').read_text())
    assert native['ManifestSha256']==sha(stage/'manifest.json')
    assert native['Models']==len(models) and native['Triangles']==triangles
    assert not stale, 'Saved woodland has stale models'
else:
    assert not woodland, 'Candidate has already been saved; use --saved.'
result=dict(manifest_sha256=sha(stage/'manifest.json'),files=len(records),models=len(models),
    vertices=vertices,triangles=triangles,trees=vertices//4,colliders=0,shadow_casting=False,
    asset_inputs_match_candidate=True,original_atlas_preserved=True,
    scene_sha256=sha(scene),forest_saved_in_scene=args.saved,
    native_models_requiring_compile=stale,
    status=('Saved group, generator cache, native resources and source checks passed. Gameplay performance remains unverified.'
            if args.saved else 'Source checks passed. Native compilation, visual review and performance validation remain required.'))
(stage/('source-audit-saved.json' if args.saved else 'source-audit.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='native_models_requiring_compile'},indent=2))
print('Native models requiring compile:',len(stale))
