from pathlib import Path
import json,hashlib,shutil
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/shelving-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'installed-runtime.json').read_text());assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoRuntimeModelSubstitution']
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
mesh={m['Name']:m for m in r['PublicStore']['Meshes']};assert r['PublicStore']['LodCount']==7
assert [mesh[f'shelving_lod{i}']['Triangles'] for i in range(3)]==[77200,49200,20720]
assert [mesh[f'shelving_lod{i}']['LodMask'] for i in range(3)]==[1,14,112]
marker='_class = "PhysicsShapeList"';a=(OUT/'install-before/riverside_store.vmdl').read_text();b=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
cleanup=json.loads((OUT/'cleanup-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in cleanup['files'].items()) and not any((ROOT/p).exists() for p in cleanup['delete'])
def facekeys(path):
    lines=path.read_text().splitlines();v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';out=[]
    for line in lines:
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):out.append((paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:]))))
    return set(out)
old=facekeys(OUT/'legacy-absolute.obj');assert all(not old&facekeys(p) for p in (ROOT/'Assets/models/maps/riverside').rglob('*.obj'))
result=dict(installed=True,units=4,actual_play_verified=True,old_shelf_asset_deleted=True,old_boxes_and_panels_removed_from_all_game_sources=True,original_physics_preserved=True,other_upgrades_preserved=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
readme=HERE/'README.md';text=readme.read_text(encoding='utf-8').replace('# Lucky Stop stocked shelving v1 — review candidate','# Lucky Stop stocked shelving v1 — installed 2026-11-04')
text=text.replace("This is a preview; no permanent scene or public store ModelDoc changes have been made for the shelving. Installation awaits approval under CLAUDE.md's graphics-upgrade rule.","User approved replacement and old-model deletion. The public store imports all four shelves; the saved scene and original physics remain unchanged.")
text+='\n## Installation and deletion\n\nThe installed public model was verified in actual play without renderer substitution or extra lights (`installed-runtime.json`, `in-game-installed.png`, `installed-state-restored.json`). Four unit meshes are combined per LOD, sharing eleven material batches; masks are 1/14/112 across the existing seven store LOD groups. Exactly 96 old box/panel faces were removed from each of five store source variants. The standalone old shelving asset, OBJ/MTL and sidecars were deleted through the editor. No old shelf faces remain in Riverside game OBJ sources. Existing shared materials remain for other shop windows. `Tools/riverside_shelving.py` reproduces every approved local mesh and replaces the old authoring calls while preserving all four collisions. Original review scripts/hash guards describe the pre-install baseline and may reference the now-deleted control asset.\n'
readme.write_text(text,encoding='utf-8')
for folder in ('Sources/Riverside/shelving-v1','output/riverside/shelving-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
note=ROOT/'docs/notes/riverside-shelving-v1-20261104.md'
note.write_text('''# Lucky Stop grocery shelving v1 — installed 2026-11-04

Four stocked steel gondolas replace the old wooden shelf boxes and luminous window-atlas product panels. Public `riverside_store.vmdl` imports `shelving-v1/store_without_shelving.obj` plus three absolute shelf meshes with `shv1_` material aliases. All four units are combined per LOD: 77,200/49,200/20,720 triangles (19,300/12,300/5,180 per unit), masks 1/14/112 across the existing seven groups at 0/10/15/20/25/35/45. Eleven non-emissive materials are shared by the four units. No lights changed.

User requested old-model deletion. The standalone legacy shelving asset, OBJ/MTL and sidecars were deleted through the editor. Exactly 96 old box/panel triangles were removed from each of five store source variants; no old shelving faces remain in Riverside game OBJ sources. Shared materials still used by the shop windows were retained. The original ModelDoc physics and saved scene are unchanged. All four old 36×70×56-inch collisions remain.

`Tools/riverside_shelving.py` reproduces the approved local meshes exactly; its hook replaces the old shelf box/panel authoring calls. No full-map regeneration was run. Actual public-model verification: `output/riverside/shelving-v1/in-game-installed.png`, `installed-runtime.json`, `installed-state-restored.json`, `installed.json`. One player, zero error models, no runtime substitution or extra lights. Guarded code, pre-install inputs and cleanup receipts: `Sources/Riverside/shelving-v1`, `output/riverside/shelving-v1`. Historical review controls are outside game Assets and are not installed resources.
''',encoding='utf-8')
index=ROOT/'CLAUDE.md';index.write_text(index.read_text(encoding='utf-8').rstrip()+'\n- [Riverside grocery shelving v1 (installed; old version deleted, 2026-11-04)](docs/notes/riverside-shelving-v1-20261104.md)\n',encoding='utf-8')
print(json.dumps(result,indent=2))
