from pathlib import Path
import json,hashlib,shutil
import numpy as np
from PIL import Image
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=REVIEW/'output/riverside/folded-tarp-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'runtime-review.json').read_text());s=json.loads((OUT/'studio.json').read_text());g=json.loads((OUT/'geometry-verified.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert r['ActualPlayMode'] and r['PlayerCount'] and not r['ErrorModels'] and r['NoExtraLights'] and r['GameplayPostProcessing']
assert s['UserStatePreserved'] and all(not x['IsError'] and x['Emission']==0 for model in s['Models'] for x in model['Materials'])
assert [x['Triangles'] for x in r['Candidate']['Meshes']]==m['triangles']==[x['triangles'] for x in g]
assert json.loads((OUT/'state-restored.json').read_text())['restored'] and json.loads((OUT/'scene-unchanged.json').read_text())['unchanged']
marker='_class = "PhysicsShapeList"';a=(ROOT/m['source_vmdl']).read_text();b=(REVIEW/'Assets/models/maps/riverside/folded-tarp-v1/levee_without_tarp.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
for p in list(OUT.glob('studio-*.png')):
    im=np.asarray(Image.open(p).convert('RGB')).astype(float);pink=(im[:,:,0]>90)&(im[:,:,2]>80)&(im[:,:,1]<np.minimum(im[:,:,0],im[:,:,2])*.5);assert not pink.any(),p
result=dict(preview_only=True,actual_play_verified=True,zero_error_models=True,geometry_valid=True,three_lods=m['triangles'],six_non_emissive_materials=True,original_blue_material_unchanged=sha(ROOT/'Assets/materials/riverside/rs_tarp_blue.vmat'),public_model_unchanged=True,physics_unchanged=True,saved_scene_unchanged=True,editor_state_restored=True)
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
text='''# L1 rooftop folded blue tarp — review candidate

Replaces the original80×80×3-inch plain box with modelled fabric layers, soft stored creases, a turned-up corner with an underside, perimeter hems/stitching, eight metal eyelets and a woven normal map. Parametric geometry, not a cloth simulation. The lower sheet follows the shallow roof pitch. Original blue tint retained; original shared rs_tarp_blue.vmat is unchanged. Existing Orion tarp pile and Spillway generator cover were audited; their draped load shapes do not fit this shallow folded sheet. No other active chat was working on this prop.

Worktree C:/sbox-projects/hc1/folded-tarp-review, branch codex/riverside-folded-tarp-v1. Resource models/maps/riverside/folded-tarp-v1/tarp.vmdl. Position(607,-737,314), yaw90. Three LODs25,152/12,016/5,008 at0/15/35. Six non-emissive materials;1024px weave/normal maps. All mesh indices/UVs/normals and triangle areas checked. Both material sets load without errors.

Matched native studio-whole/detail-before/after.png use inspection lights, reduced equally for both models to avoid washing out the blue. In-game-whole-before/after.png are actual Riverside play captures with copied gameplay post-processing and no added lights: one player, zero error models. Scene/play state restored. Saved scene, public levee ModelDoc/input, all original physics and the newly installed roof ladder remain unchanged. Private levee_without_tarp removes only12 old tarp triangles for preview, retaining all other mesh inputs and physics.

Not installed; awaits approval under CLAUDE.md. Original box remains on the map and is preserved separately as legacy_tarp.vmdl. Do not regenerate Riverside when integrating this. Prefix material aliases to avoid collisions with the installed roof ladder's remaps. Scripts: build.py, check_geometry.py, import.cs.txt/native.py, studio.cs.txt, runtime-review.cs.txt/capture.py and finish.py. Evidence in output/riverside/folded-tarp-v1/verification.json, studio.json, runtime-review.json, geometry-verified.json and scene/state receipts.
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
for folder in ('Sources/Riverside/folded-tarp-v1','output/riverside/folded-tarp-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
(ROOT/'docs/notes/riverside-folded-tarp-v1-review-20261104.md').write_text(text,encoding='utf-8')
p=ROOT/'CLAUDE.md';line='- [Riverside folded blue tarp v1 (review candidate, 2026-11-04)](docs/notes/riverside-folded-tarp-v1-review-20261104.md)'
if line not in p.read_text(encoding='utf-8'):
    with p.open('a',encoding='utf-8') as f:f.write('\n'+line+'\n')
print(json.dumps(result,indent=2))
