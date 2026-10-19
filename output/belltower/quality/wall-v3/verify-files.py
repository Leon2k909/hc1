from pathlib import Path
import hashlib
import json
import shutil
import sys
root=Path(__file__).resolve().parents[4]
folder=root/'output/belltower/quality/wall-v3'
sys.path.insert(0,str(root/'Tools'))
import belltower_quality_materials as M
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for name in ('wall-limestone-v3-color.png','wall-limestone-v3-height.png','wall-limestone-v3-quilt.png','ivy-climb-v3.png'):
    assert sha(root/'Sources/Belltower/generated'/name)==sha(root/'Assets/materials/belltower/generated'/name),name
for name in ('rubble','ivy_climb'):
    assert (root/f'Assets/materials/belltower/{name}.vmat').read_text()==M.material_text(name)
assert sha(root/'Sources/Belltower/shaders/belltower_masonry_v3.shader')==sha(root/'Assets/shaders/belltower_masonry_v3.shader')
geometry=json.loads((root/'output/belltower/quality/wall-v2/geometry-manifest.json').read_text())
for file in geometry['files']:
    assert sha(root/'Assets'/file['path'])==file['sha256']
for name,digest in geometry['protected_sha256'].items():
    assert sha(root/'Assets'/name)==digest
scene_hash=json.loads((root/'output/belltower/quality/wall-v2/before-camera.json').read_text())['SourceSceneSha256']
assert sha(root/'Assets/scenes/maps/Belltower/belltower.scene')==scene_hash
for name in ('wall-front','wall-ivy-close','grazing','east-wall'):
    camera=json.loads((folder/f'{name}-camera.json').read_text())
    assert camera['GamePreserved'] and camera['SelectedDocumentPreserved'] and not camera['SceneHasUnsavedChanges']
native=json.loads((folder/'native-verification.json').read_text())
assert native['BelltowerSaved'] and len(native['Materials'])==2
exchange=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/a655920748644334b6c97a5d26da3c29')
for name in ('import-wall-v3','verify-wall-v3'):
    shutil.copy2(exchange/f'{name}.cs',root/f'Sources/Belltower/editor/{name}.cs.txt')
generation_path=root/'Sources/Belltower/wall-v3/generation.json'
generation=json.loads(generation_path.read_text())
generation['outputs']['uv_data']='Sources/Belltower/generated/wall-limestone-v3-quilt.png'
generation['uv_data_method']='Tools/belltower_wall_quilt.py: numerical UV selectors and per-stone luminance; original ImageGen color/height pixels retained'
generation['sha256']={name:sha(root/name) for name in generation['outputs'].values()}
generation_path.write_text(json.dumps(generation,indent=2)+'\n')
result={'source_and_live_assets_match':True,'scene_and_collision_unchanged':True,
        'previous_wall_geometry_cleanup_retained':True,'four_native_capture_states_preserved':True,
        'materials_loaded_with_expected_textures':True,
        'source_sha256':{name:sha(root/name) for name in ('Tools/belltower_wall_quilt.py','Tools/belltower_quality_materials.py','Sources/Belltower/shaders/belltower_masonry_v3.shader')},
        'captures':['wall-front.png','wall-ivy-close.png','grazing.png','east-wall.png']}
(folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
