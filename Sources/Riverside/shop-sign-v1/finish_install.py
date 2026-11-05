from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/shop-sign-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'installed-runtime.json').read_text());assert r['Installed'] and r['ActualPlayMode'] and r['PlayerCount'] and not r['ErrorModels'] and r['NoRuntimeModelSubstitution']
assert json.loads((OUT/'installed-state-restored.json').read_text())['restored']
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
meshes={x['Name']:x for x in r['PublicStore']['Meshes']}
assert [meshes[f'shop_sign_lod{i}']['Triangles'] for i in range(3)]==[9016,5548,2248]
assert [meshes[f'shop_sign_lod{i}']['LodMask'] for i in range(3)]==[7,56,64]
marker='_class = "PhysicsShapeList"';a=(OUT/'install-before/riverside_store.vmdl').read_text();b=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
cleanup=json.loads((OUT/'cleanup-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in cleanup['files'].items()) and not any((ROOT/p).exists() for p in cleanup['delete'])
scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());queue=[scene];light=[]
while queue:
    obj=queue.pop()
    if isinstance(obj,dict):
        if obj.get('__guid')=='ad251c23-5036-51ff-9ecb-932578dc96f1':light.append(obj)
        queue.extend(obj.values())
    elif isinstance(obj,list):queue.extend(obj)
assert len(light)==1 and abs(light[0]['Intensity']-.2)<1e-6
sys.path.insert(0,str(ROOT/'Tools'));import riverside_shop_sign as S;import map_kit as K
for lod in range(3):
    target=OUT/f'authoring-check-lod{lod}.obj';K.write_obj(target,S.model(lod),target.stem)
    assert target.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/shop-sign-v1/shop_sign_lod{lod}.obj').read_text().splitlines()[3:]
result=dict(installed=True,actual_play_verified=True,old_sign_deleted=True,legacy_faces_removed_from_six_sources=True,original_physics_preserved=True,other_upgrades_preserved=True,light_intensity=.2,face_emission=0,bulb_emission=1,authoring_geometry_exact=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
readme=HERE/'README.md';readme.write_text(readme.read_text(encoding='utf-8')+'\n## Installed 2026-11-04\n\nUser approved the toned sign. Public store now uses three new meshes with face_toned.vmat; the existing saved sign PointLight has Intensity 0.20. Old sign assets and bright reference controls were deleted; 136 old triangles removed from six source variants. Existing physics retained byte-for-byte. Tools/riverside_shop_sign.py reproduces all three approved meshes. Actual play verified one player, zero error models, no runtime substitution, no extra lights. See installed.json and in-game-installed.png. Historical preview scripts refer to deleted controls and are archival.\n',encoding='utf-8')
for folder in ('Sources/Riverside/shop-sign-v1','output/riverside/shop-sign-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
note=ROOT/'docs/notes/riverside-shop-sign-v1-20261104.md';note.write_text('''# Lucky Stop roof sign v1 — installed 2026-11-04

Approved formed steel lightbox and gooseneck lamps replace the old sign. 9,016/5,548/2,248 triangles, masks 7/56/64 across the existing seven store LOD groups. Placement (514,-220,150), original 168×8×48-inch cabinet volume and all public ModelDoc physics retained. Public store imports shop-sign-v1/store_without_shop_sign.obj and installed_lod0/1/2.obj, with shopsignv1_ aliases. Face uses verified face_toned.vmat (non-emissive, roughness 0.72); private bulb brightness 1.0. Global materials and camera look unchanged.

The existing store sign PointLight (7867677a-76dd-57bc-9e53-006ab54770cb, component ad251c23-5036-51ff-9ecb-932578dc96f1) was saved through native set_component with Intensity 0.20. LightColor 2.2,1.584,0.924,1, radius420 and animation remain unchanged. Bridge set_property did not mark the scene dirty, so native set_component was used and the saved JSON/runtime were checked. Authoring equivalent scale0.44.

Old standalone sign and bright lighting control resources deleted via native Asset.Delete; exactly136 old faces removed from six source variants. Other upgrades preserved, no full-map regeneration. Tools/riverside_shop_sign.py reproduces all three approved meshes; riverside_map hook uses it and preserves the cabinet collider. Actual public model checked in offline play: one player, zero error models, no renderer substitution or extra lights. Editor returned to Sewage, clean and stopped.

Evidence: output/riverside/shop-sign-v1/installed.json, installed-runtime.json, in-game-installed.png; scripts in Sources/Riverside/shop-sign-v1. Pre-install review sources are archival and may reference deleted control assets.
''',encoding='utf-8')
index=ROOT/'CLAUDE.md';line='- [Lucky Stop roof sign v1 (installed; lighting toned down; old sign deleted, 2026-11-04)](docs/notes/riverside-shop-sign-v1-20261104.md)'
text=index.read_text(encoding='utf-8');assert line not in text;index.write_text(text.rstrip()+'\n'+line+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
