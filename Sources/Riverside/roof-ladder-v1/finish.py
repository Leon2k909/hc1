from pathlib import Path
import json,hashlib,shutil
import numpy as np
from PIL import Image
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=REVIEW/'output/riverside/roof-ladder-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'runtime-review.json').read_text());studio=json.loads((OUT/'studio.json').read_text());g=json.loads((OUT/'geometry-verified.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['files'].items()) and all(sha(ROOT/'Assets'/p)==h for p,h in m['external_files'].items())
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoExtraLights'] and r['GameplayPostProcessing']
assert studio['UserStatePreserved'] and all(not mat['IsError'] and mat['Emission']==0 for model in studio['Models'] for mat in model['Materials'])
assert [x['Triangles'] for x in r['Candidate']['Meshes']]==m['triangles']==[x['triangles'] for x in g]
assert json.loads((OUT/'state-restored.json').read_text())['restored'] and json.loads((OUT/'scene-unchanged.json').read_text())['unchanged']
marker='_class = "PhysicsShapeList"';a=(ROOT/m['source_vmdl']).read_text();b=(REVIEW/'Assets/models/maps/riverside/roof-ladder-v1/levee_without_ladder.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
for p in list(OUT.glob('in-game-*.png'))+list(OUT.glob('studio-*.png')):
    im=np.asarray(Image.open(p).convert('RGB')).astype(float)
    # Night captures contain unrelated coloured effects at the image borders; inspect the ladder region.
    if p.name.startswith('in-game-'):im=im[:,200:-200]
    pink=(im[:,:,0]>90)&(im[:,:,2]>80)&(im[:,:,1]<np.minimum(im[:,:,0],im[:,:,2])*.5);assert not pink.any(),p
v=dict(preview_only=True,actual_play_verified=True,zero_error_models=True,geometry_valid=True,three_lods=m['triangles'],approved_recipe_reused='Tools/lowtide_quay_ladders.py',approved_recipe_sha256=sha(ROOT/'Tools/lowtide_quay_ladders.py'),approved_materials_unchanged=True,public_model_unchanged=True,physics_unchanged=True,saved_scene_unchanged=True,editor_state_restored=True,matching_studio_lighting=True,no_magenta_error_patterns=True)
(OUT/'verification.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
text='''# Raised trailer L1 roof ladder — review candidate

Adapts the approved Lowtide quay ladder recipe to L1's220-inch rise and38-inch lean, reusing the retained galvanized steel finish and existing hardware/grip materials. No new textures. Continuous rails, returned roof handholds, anti-slip treads, grip studs, sealed lower ends, wall brackets and bolted roof feet replace the original204-triangle rods. Top feet are individually fitted to the trailer's pitched roof at their actual lateral positions. Original trailer, roof, graffiti, physics, lighting and climbing behavior are unchanged.

Worktree C:/sbox-projects/hc1/roof-ladder-review, branch codex/riverside-roof-ladder-v1. Private resource models/maps/riverside/roof-ladder-v1/ladder.vmdl; placement(407,-697,96), yaw90. LODs6,904/4,252/2,060 at0/20/45. Four reused non-emissive finishes. Original approved recipe/material files are unchanged. This is separate from the installed guard-tower ladder and T2 steps.

Actual Riverside play verified one player, zero error models and copied gameplay post-processing. in-game-whole/detail-before/after.png are matching night captures with no added lights. studio-whole/detail-before/after.png use matched inspection lights in an isolated native SceneWorld, clearly supplementary to the night map. Source scene/play state restored. Geometry, materials, source hashes, original public physics and saved scene validated; verification.json records results.

No public replacement or authoring hook yet; original ladder remains installed. Private levee_without_ladder removes only204 old ladder triangles for preview and retains the entire original PhysicsShapeList. Await approval under CLAUDE.md. Do not regenerate the map on installation; integrate the approved ladder narrowly and retain all existing upgrades. Scripts: build.py, check_geometry.py, native.py/import.cs.txt, studio.cs.txt, runtime-review.cs.txt/capture.py and finish.py. setup.py/refine_fit.py are one-time preparation history.
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
for folder in ('Sources/Riverside/roof-ladder-v1','output/riverside/roof-ladder-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
(ROOT/'docs/notes/riverside-roof-ladder-v1-review-20261104.md').write_text(text,encoding='utf-8')
p=ROOT/'CLAUDE.md';line='- [Riverside L1 roof ladder v1 (review candidate; approved design reused, 2026-11-04)](docs/notes/riverside-roof-ladder-v1-review-20261104.md)'
if line not in p.read_text(encoding='utf-8'):
    with p.open('a',encoding='utf-8') as f:f.write('\n'+line+'\n')
print(json.dumps(v,indent=2))
