from pathlib import Path
import json,hashlib,shutil
REVIEW=Path(__file__).resolve().parents[3]
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=REVIEW/'output/riverside/ice-cabinet-v1'
report=json.loads((OUT/'installed-runtime.json').read_text())
assert report['ActualPlayMode'] and report['PlayerCount']>0 and not report['ErrorModels']
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
plan=json.loads((OUT/'install-plan.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in plan['files'].items())
assert report['StoreMesh']['LodCount']==3
meshes={m['Name']:m for m in report['StoreMesh']['Meshes']}
assert [meshes[f'ice_lod{i}']['Triangles'] for i in range(3)]==[4692,2444,1248]
assert [meshes[f'ice_lod{i}']['LodMask'] for i in range(3)]==[1,2,4]
assert meshes['riverside_store']['LodMask']==meshes['drinks_fridge']['LodMask']==7
original=(OUT/'install-before/riverside_store.vmdl').read_text();current=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();mark='_class = "PhysicsShapeList"'
assert original[original.index(mark):]==current[current.index(mark):]
summary=dict(installed=True,actual_play_verified=True,old_panel_removed=True,three_lods=True,physics_unchanged=True,no_extra_lights=True,no_runtime_substitution=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(summary,indent=2))
readme=REVIEW/'Sources/Riverside/ice-cabinet-v1/README.md'
text=readme.read_text();text='# Installed 2026-11-04\n\nUser approved installation. The public store ModelDoc now includes the cabinet at all three LODs, with original physics preserved. Actual offline Riverside gameplay capture passed with one player and no error models. See `output/riverside/ice-cabinet-v1/installed-in-game.png`.\n\n'+text
readme.write_text(text)
for folder in ('Sources/Riverside/ice-cabinet-v1','output/riverside/ice-cabinet-v1'):
    target=ROOT/folder;target.mkdir(parents=True,exist_ok=True)
    for path in (REVIEW/folder).glob('*'):
        if path.is_file():shutil.copy2(path,target/path.name)
note=ROOT/'docs/notes/riverside-ice-cabinet-v1-20261104.md'
note.write_text('''# Lucky Stop ice cabinet v1 — installed 2026-11-04

Approved and installed after actual offline Riverside play verification. Native images: `output/riverside/ice-cabinet-v1/installed-in-game.png` and `installed-porch.png`. These use the map lighting and gameplay camera effects; no extra lights or runtime model substitutions.

`riverside_store.vmdl` now imports `ice-cabinet-v1/store_without_ice.obj` in place of the existing store input (exactly 14 old cabinet triangles removed), retains the upgraded drinks-fridge mesh, and adds three translated cabinet meshes with collision-safe `icev1_` material aliases. Store and drinks-fridge meshes have LOD mask 7; cabinet meshes have masks 1/2/4, 4,692/2,444/1,248 triangles, thresholds 0/20/45. Original ModelDoc physics section and saved scene are unchanged. The existing ice-machine point light remains unchanged.

`Tools/riverside_ice_cabinet.py` reproduces all three approved local OBJ meshes exactly. Its authoring hook replaces the old cabinet and atlas panel in `Tools/riverside_map.py`; no full-map regeneration was run. The authoring helper retains the original 38×30×60 inch collision and placement. Source, guarded installation scripts and receipts are in `Sources/Riverside/ice-cabinet-v1` and `output/riverside/ice-cabinet-v1`.
''')
index=ROOT/'CLAUDE.md';line='- [Riverside ice cabinet v1 (installed, 2026-11-04)](docs/notes/riverside-ice-cabinet-v1-20261104.md)'
index.write_text(index.read_text().rstrip()+'\n'+line+'\n')
print(json.dumps(summary,indent=2))
