"""Prepare a guarded, coordinated parcel-v4 production publication.

Generates an exact scene-source replacement containing only new near/far
vegetation groups, with unchanged gameplay/collision and other scene roots.
The native editor script owns publishing; Python never writes accepted assets.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/quality/parcel-v4-production'
SCENE=ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
TREES=ROOT/'Sources/Belltower/landscape/trees.json'
FOREST=ROOT/'Sources/Belltower/landscape/forest.json'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    root=json.loads(SCENE.read_text())
    new_trees=json.loads((ROOT/'output/belltower/quality/parcel-v4-foliage/trees.json').read_text())
    new_forest=json.loads((ROOT/'output/belltower/quality/parcel-v4-forest/forest.json').read_text())
    replacements={'Landscape trees':new_trees,'Distant woodland':new_forest}
    original={o['Name']:o for o in root['GameObjects'] if o.get('Name') in replacements}
    assert set(original)==set(replacements)
    assert len(new_trees['Children'])==1600 and len(new_forest['Children'])==88
    assert all(c['Components'][0]['RenderType']=='Off' for c in new_forest['Children'])
    assert all(len(c['Components'])==1 and c['Components'][0]['__type']=='Sandbox.ModelRenderer' for c in new_forest['Children'])
    for child in new_forest['Children']:
        assert child['Components'][0]['Model'].startswith('models/maps/belltower/forest/parcel-v4/')
    for i,object_ in enumerate(root['GameObjects']):
        if object_.get('Name') in replacements:
            root['GameObjects'][i]=replacements[object_['Name']]
    (STAGE/'belltower.scene').write_text(json.dumps(root,indent=2)+'\n',encoding='utf-8')
    other=lambda g:[(o.get('Name'),o) for o in g['GameObjects'] if o.get('Name') not in replacements]
    assert other(root)==other(json.loads(SCENE.read_text()))
    inputs=[]
    outputs=[]
    files=[(STAGE/name,ROOT/'Assets/materials/belltower/vista'/name) for z in 'abcd' for name in [f'vista_{z}_{suffix}' for suffix in ('color.jpg','kind.png','normal.jpg')]]
    files += [(STAGE/name,ROOT/'Assets/materials/belltower/vista'/name) for name in ('detail_grass.png','detail_soil.png','detail_stone.png')]
    files += [(STAGE/'belltower.scene',SCENE),(ROOT/'output/belltower/quality/parcel-v4-foliage/trees.json',TREES),(ROOT/'output/belltower/quality/parcel-v4-forest/forest.json',FOREST)]
    for source,target in files:
        assert source.is_file() and target.is_file()
        outputs.append({'source':source.relative_to(ROOT).as_posix(),'target':target.relative_to(ROOT).as_posix(),
                        'source_sha256':sha(source),'expected_sha256':sha(target)})
    report={'revision':'parcel-v4','scene_roots_untouched':len(root['GameObjects'])-2,
            'near_trees':1600,'forest_sectors':88,'forest_cards':320000,'colliders_added':0,
            'forest_model_prefix':'models/maps/belltower/forest/parcel-v4/',
            'assets':outputs,
            'model_manifest_sha256':sha(ROOT/'output/belltower/quality/parcel-v4-forest/manifest.json'),
            'model_compile_log_sha256':sha(ROOT/'output/belltower/quality/parcel-v4-model-compile.json'),
            'material_manifest_sha256':sha(STAGE/'native-trial-manifest.json')}
    (STAGE/'publish-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'prepared':len(files),'terrain_files':15,'scene_and_groups':3,'near_trees':1600,'forest_sectors':88}))

if __name__=='__main__':main()
