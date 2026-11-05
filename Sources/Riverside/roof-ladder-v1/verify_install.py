from pathlib import Path
import json,hashlib,sys,shutil
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/roof-ladder-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'installed-runtime.json').read_text());assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount'] and not r['ErrorModels']
meshes={x['Name']:x for x in r['PublicModel']['Meshes']};assert r['PublicModel']['LodCount']==3
assert [meshes[f'roof_ladder_lod{i}']['Triangles'] for i in range(3)]==[6904,4252,2060]
assert [meshes[f'roof_ladder_lod{i}']['LodMask'] for i in range(3)]==[1,2,4] and meshes['riverside_levee']['LodMask']==7
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
marker='_class = "PhysicsShapeList"';a=(OUT/'install-before.vmdl').read_text();b=(ROOT/'Assets/models/maps/riverside/riverside_levee.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored'] and json.loads((OUT/'installed-scene-unchanged.json').read_text())['unchanged']
sys.path.insert(0,str(ROOT/'Tools'));import riverside_roof_ladder as L;import map_kit as K
for i in range(3):
    p=OUT/f'authoring-check{i}.obj';K.write_obj(p,L.model(i),f'ladder_lod{i}');assert p.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/roof-ladder-v1/ladder_lod{i}.obj').read_text().splitlines()[3:]
old=ROOT/'Assets/models/maps/riverside/roof-ladder-v1/legacy_ladder.vmdl';assert old.exists() and old.with_suffix('.obj').exists() and old.with_suffix('.mtl').exists()
result=dict(installed=True,actual_public_model_verified=True,no_runtime_substitution=True,original_asset_preserved=old.relative_to(ROOT/'Assets').as_posix(),original_asset_sha256=sha(old),old_ladder_removed_from_map=True,physics_unchanged=True,scene_unchanged=True,authoring_geometry_exact=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for folder in ('Sources/Riverside/roof-ladder-v1','output/riverside/roof-ladder-v1'):
    dst=ROOT/folder;dst.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dst/p.name)
addition='''
## Installed; original retained

User approved the new roof ladder and requested that the original remain a reusable game asset. The public riverside_levee.vmdl now imports levee_without_ladder.obj plus installed_lod0/1/2.obj, baked to the approved world placement. Original shared geometry remains in all three LODs; the full original PhysicsShapeList and saved scene are unchanged. Actual public model checked in play without temporary model replacement: one player, zero error models. Tools/riverside_roof_ladder.py and the narrow riverside_map.py hook reproduce the approved geometry without a full-map regeneration.

The original 204-triangle model remains at models/maps/riverside/roof-ladder-v1/legacy_ladder.vmdl, with its OBJ/MTL and original aluminum material. It is not placed on Riverside. Local foot is origin, native lean toward negative Y, rise220 inches, width18 inches between rails. It can be placed on other maps through the Asset Browser. No original asset was deleted. Receipts: installed.json, installed-runtime.json and installed-state-restored.json. Final photos: in-game-whole-installed.png and in-game-detail-installed.png.
'''
for p in (ROOT/'Sources/Riverside/roof-ladder-v1/README.md',ROOT/'docs/notes/riverside-roof-ladder-v1-review-20261104.md',HERE/'README.md'):
    p.write_text(p.read_text(encoding='utf-8').replace('— review candidate','— installed; original retained')+addition,encoding='utf-8')
p=ROOT/'CLAUDE.md';s=p.read_text(encoding='utf-8').replace('Riverside L1 roof ladder v1 (review candidate; approved design reused, 2026-11-04)','Riverside L1 roof ladder v1 (installed; original retained for reuse, 2026-11-04)');p.write_text(s,encoding='utf-8')
print(json.dumps(result,indent=2))
