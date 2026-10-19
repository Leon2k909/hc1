"""Validate the published parcel-v4 files and refresh regeneration metadata."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/quality/parcel-v4-production'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    published=json.loads((STAGE/'native-publish-result.json').read_text())
    assert published['Updated']==18 and published['GamePreserved'] and published['SelectedDocumentPreserved']
    manifest=json.loads((STAGE/'publish-manifest.json').read_text())
    assert len(manifest['assets'])==18
    for rec in manifest['assets']:
        assert sha(ROOT/rec['source'])==rec['source_sha256']
        assert sha(ROOT/rec['target'])==rec['source_sha256']
        assert sha(STAGE/'before-publication'/rec['target'])==rec['expected_sha256']
    scene=json.loads((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_text())
    roots={obj.get('Name'):obj for obj in scene['GameObjects'] if obj.get('Name') in ('Distant woodland','Landscape trees')}
    assert len(roots['Distant woodland']['Children'])==88
    assert len(roots['Landscape trees']['Children'])==1600
    model_refs=[child['Components'][0]['Model'] for child in roots['Distant woodland']['Children']]
    assert all(x.startswith('models/maps/belltower/forest/parcel-v4/') for x in model_refs)
    assert all((ROOT/'Assets'/(x+'_c')).is_file() for x in model_refs)
    accepted=ROOT/'Sources/Belltower/landscape/textures.json'
    textures=json.loads(accepted.read_text())
    textures['generator_sha256']=sha(ROOT/'Tools/belltower_vista_paint.py')
    for path in textures['source_sha256']:
        textures['source_sha256'][path]=sha(ROOT/path)
    textures['accepted_at_utc']=datetime.now(timezone.utc).isoformat()
    textures['revision']='parcel-v4'
    textures['parcel_scale']=.9
    textures['native_review']='output/belltower/quality/parcel-v4-production/native-publish-result.json'
    accepted.write_text(json.dumps(textures,indent=2)+'\n',encoding='utf-8')
    forest_path=ROOT/'Sources/Belltower/landscape/forest-manifest.json'
    forest=json.loads(forest_path.read_text())
    trial=json.loads((ROOT/'output/belltower/quality/parcel-v4-forest/manifest.json').read_text())
    forest.update({key:trial[key] for key in ('generator_sha256','trees','triangles','sectors','colliders','shadow_casting','minimum_distance','maximum_distance')})
    forest['revision']='parcel-v4'
    forest['source_group_sha256']=sha(ROOT/'Sources/Belltower/landscape/forest.json')
    forest['assets']={p.relative_to(ROOT/'Assets').as_posix():sha(p) for p in (ROOT/'Assets/models/maps/belltower/forest/parcel-v4').glob('*') if p.suffix in ('.vmdl','.obj','.mtl')}
    forest['runtime_performance_verified']=False
    forest['native_resource_report']='output/belltower/quality/parcel-v4-model-compile.json'
    forest_path.write_text(json.dumps(forest,indent=2)+'\n',encoding='utf-8')
    (STAGE/'verification.json').write_text(json.dumps({'revision':'parcel-v4','terrain_files':15,'near_trees':1600,'forest_sectors':88,'source_hashes_match':True,'backups_match':True,'compiled_sector_models':88,'gameplay_scene_roots_preserved':True},indent=2)+'\n')
    print('Validated 18 installed files, 18 backups, 88 compiled sectors, 1600 trees; refreshed terrain/forest cache manifests.')

if __name__=='__main__':main()
