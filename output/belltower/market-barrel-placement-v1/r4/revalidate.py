"""Accept unrelated generator and model-description changes without replacing them."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[4]
folder = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    assert re.fullmatch('r[0-9]+', sys.argv[1])
    folder = folder.parent / sys.argv[1]
manifest_path = folder / 'manifest.json'
manifest = json.loads(manifest_path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert all(sha(root / p) == row['before'] for p, row in manifest['files'].items())
changed = {g: [p for p, h in manifest[g].items() if sha(root / p) != h]
           for g in ('source_sha256', 'protected_sha256')}
assert set(changed['source_sha256']) <= {'Tools/belltower_map.py'}
assert set(changed['protected_sha256']) <= {
    'Assets/models/maps/belltower/belltower_west.vmdl',
    'Assets/models/maps/belltower/belltower_east.vmdl'}
source = root / 'Tools/belltower_map.py'
source_hash = sha(source)
tree = ast.parse(source.read_text())
placement = next(n for n in tree.body if isinstance(n, ast.Assign) and any(
    isinstance(t, ast.Name) and t.id == 'MARKET_STORAGE_BARRELS' for t in n.targets))
assert ast.literal_eval(placement.value) == ((-1873., 1475.), (-1873., 1506.), (-1906., 1487.))
barrels = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'barrels')
expected = ast.parse('''
def barrels(model, centre, count, rng, z=0.0, placements=None):
    if placements is not None:
        assert len(placements) == count
    for k in range(count):
        a = rng.uniform(0, 2 * math.pi)
        d = 0 if k == 0 else 27.0
        at = (centre[0] + d * math.cos(a + k * 2.1), centre[1] + d * math.sin(a + k * 2.1))
        barrel(model, placements[k] if placements is not None else at, z)
''').body[0]
assert ast.dump(barrels) == ast.dump(expected)
street = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'street_props')
calls = [n for n in ast.walk(street) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id == 'barrels' and any(k.arg == 'placements' for k in n.keywords)]
expected_call = ast.parse('barrels(model, (-1840 + 30, 1300), 3, rng, placements=MARKET_STORAGE_BARRELS)').body[0].value
assert len(calls) == 1 and ast.dump(calls[0]) == ast.dump(expected_call)
assert sha(source) == source_hash
updates = {}
for group, paths in changed.items():
    for path in paths:
        if path.endswith('.vmdl'):
            side = 'west' if path.endswith('_west.vmdl') else 'east'
            text = (root / path).read_text()
            refs = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text)
            wanted = manifest['models'][side]['bounded_imports']
            wanted = wanted + [f'models/maps/belltower/belltower_{side}_hulls_wood.obj']
            assert all(refs.count(p) == 1 for p in wanted)
            assert {p for p in refs if any(p.endswith('_'+paint+'.obj') for paint in
                    ('iron_black', 'planks', 'planks_dark'))} == set(wanted[:-1])
        new_hash = sha(root / path)
        updates[path] = {'before': manifest[group][path], 'after': new_hash}
        manifest[group][path] = new_hash
assert manifest['source_sha256']['Tools/belltower_map.py'] == source_hash
assert all(sha(root / p) == h for g in ('source_sha256', 'protected_sha256') for p, h in manifest[g].items())
assert all(sha(root / p) == row['before'] for p, row in manifest['files'].items())
(folder / 'revalidation.json').write_text(json.dumps({
    'shared_changes_preserved': updates, 'barrel_generator_semantics_exact': True,
    'targeted_geometry_unchanged_since_staging': True,
    'all_referenced_barrel_imports_and_collision_still_active': True}, indent=2)+'\n')
manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'revalidated_unrelated_changes': list(updates), 'target_files_unchanged': True}))
