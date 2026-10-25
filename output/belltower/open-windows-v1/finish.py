import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Tools'))
from belltower_safe_imports import span

OUT = ROOT/'output/belltower/open-windows-v1'
manifest = json.loads((OUT/'covered-a/stage/manifest.json').read_text())
original = json.loads((OUT/'review-d/stage/manifest.json').read_text())
hashes = {}
for relative, entry in manifest['files'].items():
    if '/open-windows-v1/' in relative:
        digest = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
        assert digest == entry['after'], relative
        hashes[relative] = digest
physics = {}
concurrent_physics = {}
for part in ['centre', 'west', 'east']:
    relative = f'Assets/models/maps/belltower/belltower_{part}.vmdl'
    current = (ROOT/relative).read_text()
    before = (ROOT/original['files'][relative]['backup']).read_text()
    a, b = span(current, '_class = "PhysicsShapeList"')
    c, d = span(before, '_class = "PhysicsShapeList"')
    staged = (ROOT/original['files'][relative]['source']).read_text()
    e, f = span(staged, '_class = "PhysicsShapeList"')
    assert staged[e:f] == before[c:d], part
    concurrent_physics[part] = current[a:b] != staged[e:f]
    physics[part] = True
    assert current.count(f'models/maps/belltower/open-windows-v1/{part}/windows.obj') == 1
    old = re.findall(r'filename\s*=\s*"([^"]+)"', before)
    now = re.findall(r'filename\s*=\s*"([^"]+)"', current)
    assert all(p in now for p in old), part
for revision in ['review-d', 'covered-a']:
    receipt = json.loads((OUT/revision/'native-import.json').read_text())
    assert receipt['EditorStatePreserved'] and not receipt['SceneChanged'] and not receipt['PhysicsChanged']
loaded = json.loads((OUT/'native-verify.json').read_text())
assert len(loaded['Models']) == 3 and all(not m['IsError'] for m in loaded['Models'])
captures = {}
for view in ['hall', 'bakery-covered', 'bakery-inside', 'tavern']:
    path = ROOT/f'output/belltower/quality/open-windows-v1-final/{view}-camera.json'
    data = json.loads(path.read_text())
    assert all(data['Restoration'].values()), view
    captures[view] = path.with_name(view+'.png').relative_to(ROOT).as_posix()
result = {
    'revision': 'open-windows-v1', 'date': '2026-10-21',
    'windows': 42, 'leaves': 84,
    'buildings': {'Town Hall': 14, 'Bakery': 4, 'Dairy': 4, 'Inn': 10, 'Tavern': 10},
    'outward_windows': 38, 'covered_windows_folded_inside': 4,
    'description': 'Bevelled timber casements, separate wavy glass panes, glazing beads and iron hinges/latches. Openings remain clear.',
    'generator': 'Tools/belltower_open_windows.py',
    'hook': 'Tools/belltower_map.py: dress window branch; bakery covered_windows style',
    'stage_manifest': 'output/belltower/open-windows-v1/covered-a/stage/manifest.json',
    'geometry': manifest['geometry'],
    'all_existing_imports_preserved': True, 'physics_exact': physics,
    'all_three_models_compiled': True, 'all_window_materials_loaded_without_errors': True,
    'geometry_checks': 'Finite vertices, outward triangle winding, no zero-area triangles after OBJ rounding, mirrored east geometry, no added collision.',
    'concurrent_physics_changes_after_initial_publication': concurrent_physics,
    'editor_state_restored_after_each_capture': True,
    'captures': captures, 'private_asset_sha256': hashes,
    'current_scene_sha256_for_reference': hashlib.sha256((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest(),
    'notes': ['Only window work belongs to this side conversation. Concurrent map/scene work is preserved.',
              'No scene save, scene reload, or play-session stop was issued for this change.']
}
target = ROOT/'Sources/Belltower/windows/open-windows-v1.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2)+'\n')
(OUT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: result[k] for k in ['windows', 'leaves', 'physics_exact', 'all_three_models_compiled', 'all_window_materials_loaded_without_errors']}))
