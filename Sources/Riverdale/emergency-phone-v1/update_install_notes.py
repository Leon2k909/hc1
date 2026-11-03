from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
def update(path,new):
    old=path.read_bytes();incoming=path.with_name(path.name+'.phone-incoming');incoming.write_text(new,encoding='utf-8')
    assert path.read_bytes()==old,'Documentation changed concurrently'
    incoming.replace(path);assert path.read_text()==new
p=HERE/'README.md';old=p.read_text()
intro='''# Approved Riverdale emergency phones

Installed on 2026-10-31 after the user approved the right-hand native preview. All eight wall phones
are shared instances of the exact approved model, with a matching static ModelCollider on each.
Exactly 80 body triangles and 928 fine-detail triangles were removed from the two packed hall OBJs.
Every unrelated OBJ line is byte identical; the only scene change is the Emergency Phones group.
Original mounting positions and facing are preserved, and desk phones are unchanged.

The editor closed before installation, so the saved-file installation did not reopen it. The shared
phone asset had already compiled and passed all seven native collision tests. Fresh native validation
of the placed scene remains pending. The two packed hall models need compilation after the removed
faces; their unchanged ModelDocs were timestamped newer than their compiled caches to trigger a stale
check. Use native asset_compile (or compile-stale.cs.txt) on the next editor session before validating.

Current receipt: installed.json. Verification: verify_install.py checks all transforms, model/collider
bindings, UUID uniqueness, exact face removal, preserved scene content and matching regeneration.
Tools/riverdale_emergency_phones.py records the original hall placements and emits shared scene objects;
riverdale_hall.wall_phone records each placement, and riverdale_map.write_scene authors the group.
Rollback and stage: output/riverdale-emergency-phone-installed-20261031/.

The following describes the historical preview.

'''
if not old.startswith('# Approved Riverdale emergency phones'):update(p,intro+old)
p=ROOT/'docs/notes/093-riverdale-multiplayer-map-tools-riverdale-map-py.md';old=p.read_text();header=old.splitlines()[0]+'\n'
entry='''- Emergency phones approved and installed (2026-10-31): all eight old wall phones are replaced by
  shared instances of models/props/riverdale/emergency-phone-v1/after.vmdl with static model collision.
  Exactly 80 detail and 928 fine triangles are removed; unrelated OBJ lines and the rest of the saved
  scene are preserved. Original wall positions/facing and desk phones are unchanged. The approved model
  and materials are byte unchanged, with seven native asset-level collision tests already passed.
  The editor was closed during installation; fresh placed-scene validation and compilation of the two
  packed hall meshes are pending the next editor session. Their ModelDoc source timestamps are refreshed.
  Tools/riverdale_emergency_phones.py, riverdale_hall.wall_phone and riverdale_map.write_scene preserve
  regeneration. Sources/Riverdale/emergency-phone-v1/installed.json and verify_install.py record exact
  source/scene/transform checks; output/riverdale-emergency-phone-installed-20261031/ retains rollback.
'''
if 'Emergency phones approved and installed (2026-10-31)' not in old:update(p,old.replace(header,header+entry,1))
print('Installation documentation updated')
