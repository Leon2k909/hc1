from pathlib import Path
import json,hashlib,collections,shutil,re
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/counter-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'installed-runtime.json').read_text());assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoRuntimeModelSubstitution']
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
plan=json.loads((OUT/'install-plan.json').read_text())
for path,digest in plan['files'].items():
    if sha(ROOT/path)==digest:continue
    assert path=='Assets/models/maps/riverside/riverside_store.vmdl','An installed source changed'
    expected=(OUT/'install-stage'/path).read_text();current=(ROOT/path).read_text()
    expected,n=re.subn(r'\{\s*from = "rs_porch_light.vmat" to = "materials/riverside/rs_porch_light.vmat"\s*\},?','',expected)
    assert n==1 and re.sub(r'\s+','',expected)==re.sub(r'\s+','',current),'Unexpected ModelDoc change'
    (OUT/'post-install-concurrent.json').write_text(json.dumps(dict(preserved='unused rs_porch_light material remap removed',geometry_unchanged=True,current_public_hash=sha(ROOT/path)),indent=2),encoding='utf-8')
mesh={m['Name']:m for m in r['PublicStore']['Meshes']};assert r['PublicStore']['LodCount']==7
assert r['PublicStore']['LodSwitchDistances']==[0,10,15,20,25,35,45]
assert [mesh[f'counter_lod{i}']['Triangles'] for i in range(3)]==[5296,3436,1628]
assert [mesh[f'counter_lod{i}']['LodMask'] for i in range(3)]==[3,28,96]
assert [mesh[f'ice_lod{i}']['LodMask'] for i in range(3)]==[7,56,64]
assert [mesh[f'register_lod{i}']['LodMask'] for i in range(3)]==[1,14,112]
marker='_class = "PhysicsShapeList"';a=(OUT/'install-before/riverside_store.vmdl').read_text();b=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
cleanup=json.loads((OUT/'cleanup-plan.json').read_text())
for path,digest in cleanup['files'].items():
    if sha(ROOT/path)==digest:continue
    assert path in ('Assets/models/maps/riverside/drinks-fridge-v1/store_without_fridge.obj','Assets/models/maps/riverside/ice-cabinet-v1/store_without_ice.obj')
    staged=(OUT/'cleanup-stage'/path).read_text();current=(ROOT/path).read_text()
    expected,n=re.subn(r'(?m)^usemtl rs_porch_light\n(?:f[^\n]*\n){12}','',staged)
    assert n==1 and expected==current,'Unrelated store mesh changed during cleanup'
assert not any((ROOT/p).exists() for p in cleanup['delete'])
def facekeys(path):
    lines=path.read_text().splitlines();v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';out=[]
    for line in lines:
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):out.append((paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:]))))
    return set(out)
old=facekeys(OUT/'legacy-absolute.obj')
assert all(not old&facekeys(p) for p in (ROOT/'Assets/models/maps/riverside').rglob('*.obj'))
result=dict(installed=True,actual_play_verified=True,old_counter_asset_deleted=True,old_counter_faces_removed_from_all_game_sources=True,original_physics_preserved=True,other_upgrades_preserved=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
readme=HERE/'README.md';text=readme.read_text(encoding='utf-8').replace('# Lucky Stop checkout counter v1 — review candidate','# Lucky Stop checkout counter v1 — installed 2026-11-04')
text=text.replace("The public store ModelDoc and saved scene are unchanged by this preview. Permanent installation awaits the user's review under CLAUDE.md's graphics-upgrade rule.","User approved replacement and deletion of the old counter. The public store imports the new counter; the saved scene and physics section are unchanged.")
text+='\n## Installed and old version deleted\n\nActual public-model play verification: `in-game-front-installed.png`, `installed-runtime.json`, `installed-state-restored.json`, `installed.json`. No runtime substitution or added lights. The old standalone counter asset, OBJ/MTL and sidecars were deleted from game Assets through the editor; its 12 old faces were removed from four remaining store source variants. `cleanup-plan.json`/`cleanup.json` record exact targets. Shared store materials remain. The approved geometry is reproduced by `Tools/riverside_counter.py`; the old authoring box was replaced without regenerating the map. An intervening 12-triangle porch-light removal was preserved (`integration-baseline.json`). Historical review/build scripts target the pre-install baseline and may reference the deleted comparison asset; retain them as evidence rather than re-importing the old asset.\n'
readme.write_text(text,encoding='utf-8')
for folder in ('Sources/Riverside/counter-v1','output/riverside/counter-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
note=ROOT/'docs/notes/riverside-counter-v1-20261104.md'
note.write_text('''# Lucky Stop checkout counter v1 — installed 2026-11-04

User approved replacement and deletion of the old counter. `riverside_store.vmdl` imports `counter-v1/store_without_counter.obj` and three translated `ctrv1_` counter meshes. Three approved LODs: 5,296/3,436/1,628 triangles; counter masks 3/28/96 across combined distances 0/10/15/20/25/35/45. Store/drinks masks 127, ice 7/56/64, register 1/14/112. The original ModelDoc physics section and saved scene are unchanged. A concurrent porch-light removal was preserved during integration.

The old standalone `counter-v1/legacy_counter` asset, OBJ/MTL and sidecars were deleted through the editor. Exactly 12 old counter triangles were also removed from each of four old store source variants, preserving all unrelated records. No old counter faces remain in Riverside game OBJ sources. Shared materials were retained. `Tools/riverside_counter.py` reproduces all approved LODs and replaces the old counter authoring box in `Tools/riverside_map.py`; no full-map regeneration was run.

Actual public-model play verification: `output/riverside/counter-v1/in-game-front-installed.png`, `installed-runtime.json`, `installed-state-restored.json`, `installed.json`. One player, zero error models, original camera effects, no added lights or runtime model substitution. Guarded sources, cleanup plans and receipts: `Sources/Riverside/counter-v1` and `output/riverside/counter-v1`. Earlier review assets/hash guards describe pre-install baselines and must not be reapplied blindly.
''',encoding='utf-8')
index=ROOT/'CLAUDE.md';line='- [Riverside checkout counter v1 (installed; old version deleted, 2026-11-04)](docs/notes/riverside-counter-v1-20261104.md)';index.write_text(index.read_text(encoding='utf-8').rstrip()+'\n'+line+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
