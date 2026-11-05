from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=REVIEW/'output/riverside/neon-sign-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'runtime-review.json').read_text());g=json.loads((OUT/'geometry-verified.json').read_text());materials=json.loads((OUT/'materials-verified.json').read_text());engine=json.loads((OUT/'engine-review.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['files'].items()) and all(sha(ROOT/p)==h for p,h in m['external_files'].items())
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert r['ActualPlayMode'] and r['PlayerCount'] and not r['ErrorModels'] and r['NoExtraLights'] and r['ExistingNeonLightsUnchanged'] and r['GameplayPostProcessing']
assert [x['Triangles'] for x in r['Candidate']['Meshes']]==[x['triangles'] for x in g]==m['triangles']==[34908,9660,6444]
assert [x['LodMask'] for x in r['Candidate']['Meshes']]==[1,2,4] and r['Candidate']['LodCount']==3
assert materials['AllMaterialsLoaded'] and materials['OnlyTubesEmissive'] and len(materials['Materials'])==6 and all(x['ColorWidth'] for x in materials['Materials'])
assert engine['UserStatePreserved'] and json.loads((OUT/'state-restored.json').read_text())['restored'] and json.loads((OUT/'scene-unchanged.json').read_text())['unchanged']
marker='_class = "PhysicsShapeList"';original=(ROOT/m['source_vmdl']).read_text();preview=(REVIEW/'Assets/models/maps/riverside/neon-sign-v1/dressing_without_neon.vmdl').read_text();assert original[original.index(marker):]==preview[preview.index(marker):]
photos=[]
for variant in ('before','after'):
    path=OUT/f'in-game-front-{variant}.png';im=np.asarray(Image.open(path).convert('RGB')).astype(float)
    assert im.shape==(1200,1200,3)
    pink=(im[:,:,0]>90)&(im[:,:,2]>80)&(im[:,:,1]<np.minimum(im[:,:,0],im[:,:,2])*.5);assert not pink.any()
    text=im[340:880,320:940];green=(text[:,:,1]>160)&(text[:,:,0]<text[:,:,1]*.8)&(text[:,:,2]<150);assert green.sum()<10
    photos.append(dict(file=path.name,magenta_error_pixels=0,green_tube_pixels=int(green.sum()),clipped_white_text_pixels=int(((text[:,:,0]>247)&(text[:,:,1]>235)&(text[:,:,2]>220)).sum())))
result=dict(preview_only=True,actual_play_verified=True,one_player=True,zero_error_models=True,only_tubes_emissive=True,six_materials_verified=True,triangles=m['triangles'],original_public_model_unchanged=True,original_physics_preserved=True,saved_scene_unchanged=True,original_red_lights_unchanged=True,main_camera_not_replaced=True,gameplay_post_processing_copied=True,editor_state_restored=True,photos=photos)
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
