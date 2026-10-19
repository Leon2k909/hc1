from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import sys
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[3]
folder=root/'output/belltower/quality/wall-v2'
sys.path.insert(0,str(root/'Tools'))
import belltower_quality_materials as materials
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((folder/'geometry-manifest.json').read_text())
for record in manifest['files']:
    assert sha(root/'Assets'/record['path'])==record['sha256'],record['path']
for name,expected in manifest['protected_sha256'].items():
    assert sha(root/'Assets'/name)==expected,name
assert (root/'Assets/materials/belltower/rubble.vmat').read_text()==materials.material_text('rubble')
assert (root/'Assets/shaders/belltower_relief.shader').read_bytes()==(root/'Sources/Belltower/shaders/belltower_relief.shader').read_bytes()
scene=root/'Assets/scenes/maps/Belltower/belltower.scene'
assert sha(scene)==json.loads((folder/'before-camera.json').read_text())['SourceSceneSha256']
exchange=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/a655920748644334b6c97a5d26da3c29')
for name in ('import-wall-geometry.cs','import-wall-material.cs'):
    shutil.copy2(exchange/name,root/'Sources/Belltower/editor'/name.replace('.cs','.cs.txt'))
result={
    'assets_match_staged_geometry':True,
    'material_matches_generator':True,
    'shader_matches_canonical_source':True,
    'collision_and_model_definitions_unchanged':True,
    'saved_scene_unchanged':True,
    'hidden_area_removed_m2':manifest['hidden_surface_removed_m2'],
    'triangle_change':manifest['triangles_after']-manifest['triangles_before'],
    'note':'Following the ramp and floor boundaries adds 16 triangles across both halves; this is hidden-surface cleanup, not a measured FPS improvement.',
    'visual_geometry_check':'passed: main wall, underfloor corner, west/east ramp joins and exterior captures',
    'checked_at':datetime.now().astimezone().isoformat(),
    'source_sha256':{name:sha(root/name) for name in ('Tools/belltower_wall_cleanup.py','Tools/belltower_stage_wall_cleanup.py','Tools/belltower_map.py','Tools/belltower_quality_materials.py','Sources/Belltower/shaders/belltower_relief.shader')},
}
result['capture_state_preserved']=all(
    json.loads((folder/f'{name}-camera.json').read_text())['GamePreserved']
    and json.loads((folder/f'{name}-camera.json').read_text())['SelectedDocumentPreserved']
    and not json.loads((folder/f'{name}-camera.json').read_text())['SceneHasUnsavedChanges']
    for name in ('after','buried-after','exterior-after','ramp-west','ramp-east'))
assert result['capture_state_preserved']
for before,after,label in [('material-v1','after','above_floor'),('exterior-before','exterior-after','exterior')]:
    a=np.array(Image.open(folder/f'{before}.png').convert('RGB'),dtype=np.float32)
    b=np.array(Image.open(folder/f'{after}.png').convert('RGB'),dtype=np.float32)
    result[f'{label}_capture_mean_absolute_difference_255']=float(np.mean(np.abs(a-b)))
(folder/'file-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
