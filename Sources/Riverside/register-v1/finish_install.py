from pathlib import Path
import ast,json,hashlib,sys,shutil
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/register-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'installed-runtime.json').read_text());assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoRuntimeModelSubstitution']
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
meshes={m['Name']:m for m in r['PublicStore']['Meshes']}
assert r['PublicStore']['LodCount']==5 and r['PublicStore']['LodSwitchDistances']==[0,10,20,25,45]
assert [meshes[f'register_lod{i}']['Triangles'] for i in range(3)]==[2720,2328,1716]
assert [meshes[f'register_lod{i}']['LodMask'] for i in range(3)]==[1,6,24]
assert [meshes[f'ice_lod{i}']['LodMask'] for i in range(3)]==[3,12,16]
old=(OUT/'install-before/riverside_store.vmdl').read_text();new=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):]
source=(HERE/'build.py').read_text();keys=next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='keys' for t in n.targets))
body=source[source.index('X=np.array'):source.index('\ncounts=[]')]
head='''"""Approved Lucky Stop register. No collision, matching the original decoration."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/register-v1"
keys='''+repr(keys)+'\n'
suffix='''
def append_to(target,position):
    m=model(0)
    offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="regv1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/riverside_register.py').write_text(head+body+suffix)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import riverside_register as G
for lod in range(3):
    proof=OUT/f'generator-proof-{lod}.obj';K.write_obj(proof,G.model(lod),f'register_lod{lod}')
    assert proof.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/register-v1/register_lod{lod}.obj').read_text().splitlines()[3:]
generator=ROOT/'Tools/riverside_map.py';text=generator.read_text();oldline='    obox( m, v( e0 + 50, n1 - 65, F + 46 ), ( 1, 0, 0 ), ( 16, 12, 12 ), "rs_dark" )';assert text.count(oldline)==1
(OUT/'install-before/riverside_map.py').write_bytes(generator.read_bytes())
generator.write_text(text.replace(oldline,'''    from riverside_register import append_to as append_approved_register
    append_approved_register( m, v( e0 + 50, n1 - 65, F + 40 ) )'''))
result=dict(installed=True,actual_play_verified=True,physics_unchanged=True,other_store_upgrades_preserved=True,approved_geometry_reproduced=True,editor_state_restored=True,no_extra_lights=True,no_runtime_substitution=True)
(OUT/'installed.json').write_text(json.dumps(result,indent=2))
readme=HERE/'README.md';text=readme.read_text().replace('# Lucky Stop cash register v1 — review candidate','# Lucky Stop cash register v1 — installed 2026-11-04').replace('The original saved scene and public store ModelDoc remain unchanged by this candidate. Installation awaits approval under CLAUDE.md\'s graphics-upgrade rule.','User approved installation. The public store ModelDoc now imports the register, preserving the ice cabinet and drinks fridge. The saved scene and complete physics section remain unchanged.')
text+='\n## Installed verification\n\n`installed-runtime.json` and `in-game-installed.png` verify the public model in offline Riverside play, without runtime substitution or added lights. `installed-state-restored.json` records editor restoration. All three approved local OBJ meshes match `Tools/riverside_register.py` exactly. The authoring hook replaces only the original register box; no full-map regeneration was run. The public store uses the union of existing ice and register switch distances (0/10/20/25/45); its shared meshes remain visible in every group. Original review/build scripts target the pre-install baseline and intentionally guard against applying the replacement twice.\n'
readme.write_text(text)
for folder in ('Sources/Riverside/register-v1','output/riverside/register-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
note=ROOT/'docs/notes/riverside-register-v1-20261104.md'
note.write_text('''# Lucky Stop cash register v1 — installed 2026-11-04

Approved register installed in `riverside_store.vmdl`. Its private store input removes exactly 12 old register triangles and preserves every other mesh. Three translated register meshes have 2,720/2,328/1,716 triangles and private `regv1_` material aliases. The combined ModelDoc has five LOD groups at 0/10/20/25/45 to preserve both the register and ice cabinet thresholds. Shared store/drinks meshes use mask 31, ice meshes 3/12/16, register meshes 1/6/24. The original physics section and saved scene are unchanged.

Actual offline gameplay verification: `output/riverside/register-v1/in-game-installed.png`, `installed-runtime.json`, `installed-state-restored.json`, `installed.json`. One player, no error models, no runtime substitutions, no extra lights, existing gameplay camera effects. All three approved local meshes are reproduced exactly by `Tools/riverside_register.py`; only the register authoring hook in `Tools/riverside_map.py` changed. No full-map regeneration was run. Native guarded scripts and pre-install inputs: `Sources/Riverside/register-v1` and `output/riverside/register-v1/install-before`.
''')
index=ROOT/'CLAUDE.md';line='- [Riverside cash register v1 (installed, 2026-11-04)](docs/notes/riverside-register-v1-20261104.md)';index.write_text(index.read_text().rstrip()+'\n'+line+'\n')
print(json.dumps(result,indent=2))
