from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
HERE=Path(__file__).parent
OUT=HERE.parents[2]/'output/riverside/folded-tarp-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text())
assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
r=json.loads((OUT/'installed-runtime.json').read_text())
assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount']==1 and not r['ErrorModels']
meshes={m['Name']:(m['Triangles'],m['LodMask']) for m in r['PublicModel']['Meshes']}
assert meshes['riverside_levee']==(3590,31)
for i,(count,mask) in enumerate(zip([25152,12016,5008],[1,6,24])):
    assert meshes[f'folded_tarp_lod{i}']==(count,mask)
for i,mask in enumerate([3,12,16]):assert meshes[f'roof_ladder_lod{i}'][1]==mask
public=ROOT/'Assets/models/maps/riverside/riverside_levee.vmdl'
assert public.read_text().split('PhysicsShapeList',1)[1]==(OUT/'install-before.vmdl').read_text().split('PhysicsShapeList',1)[1]
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
assert json.loads((OUT/'installed-scene-unchanged.json').read_text())['unchanged']
sys.path.insert(0,str(ROOT/'Tools'))
import riverside_folded_tarp as T
import map_kit as K
for i in range(3):
    p=OUT/f'generator-check-{i}.obj'
    K.write_obj(p,T.model(i),f'tarp_lod{i}')
    original=ROOT/f'Assets/models/maps/riverside/folded-tarp-v1/tarp_lod{i}.obj'
    assert p.read_text().splitlines()[3:]==original.read_text().splitlines()[3:]
legacy=ROOT/'Assets/models/maps/riverside/folded-tarp-v1/legacy_tarp.vmdl'
assert legacy.exists() and legacy.with_suffix('.obj').exists() and legacy.with_suffix('.mtl').exists()
report=dict(installed=True,actual_play_verified=True,generator_matches=True,physics_preserved=True,roof_ladder_preserved=True,scene_and_state_preserved=True,legacy_resource='models/maps/riverside/folded-tarp-v1/legacy_tarp.vmdl',public_sha256=sha(public))
(OUT/'installed.json').write_text(json.dumps(report,indent=2))
old='Not installed; awaits approval under CLAUDE.md.'
new='Approved and installed on 2026-11-04. The public levee model now uses the folded tarp; the original box is removed from the map and retained as a reusable legacy asset.'
for p in [ROOT/'docs/notes/riverside-folded-tarp-v1-review-20261104.md',ROOT/'Sources/Riverside/folded-tarp-v1/README.md']:
    s=p.read_text().replace(old,new).replace('Original box remains on the map and is preserved separately as legacy_tarp.vmdl.','Original asset: models/maps/riverside/folded-tarp-v1/legacy_tarp.vmdl.')
    s+='\nInstallation verified in actual play with one player and no error models. Original physics, installed roof ladder, saved scene and editor state are preserved. Generator updated without regenerating the map. Material aliases use rf_tarp_. Evidence: installed.json and installed-runtime.json.\n'
    p.write_text(s,encoding='utf-8')
p=ROOT/'CLAUDE.md';s=p.read_text(encoding='utf-8')
rule='- Model upgrade priority: choose props visible at player eye level on main routes or frequently used interaction points. Avoid spending upgrades on hidden rooftop/background details unless requested (user preference, 2026-11-04).'
s=s.replace('\n'+rule,'');at=s.index('- Model upgrades:');s=s[:at]+rule+'\n'+s[at:]
s=s.replace('Riverside folded blue tarp v1 (review candidate, 2026-11-04)','Riverside folded blue tarp v1 (installed; original retained, 2026-11-04)')
p.write_text(s,encoding='utf-8')
for source,dest in [(HERE,ROOT/'Sources/Riverside/folded-tarp-v1'),(OUT,ROOT/'output/riverside/folded-tarp-v1')]:
    for p in source.iterdir():
        if p.is_file() and not p.name.startswith('generator-check-'):shutil.copy2(p,dest/p.name)
print(json.dumps(report,indent=2))
