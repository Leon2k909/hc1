"""Apply only the reviewed transform strings, and only with s&box closed."""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SCENE = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_closed():
    result = subprocess.run(['rtk', 'proxy', 'tasklist', '/FI', 'IMAGENAME eq sbox-dev.exe', '/FO', 'CSV', '/NH'],
                            capture_output=True, text=True, check=True)
    if 'sbox-dev.exe' in result.stdout.lower():
        raise RuntimeError('An editor is running; use native scene tools instead.')


require_closed()
plan = json.loads((OUT / 'plan.json').read_text())
assert sha(SCENE) == plan['before_scene_sha256']
for path, expected in (plan['model_guards'] | plan['source_after']).items():
    assert sha(ROOT / path) == expected, path
raw = SCENE.read_bytes()
text = raw.decode('utf8')
expected_scene = copy.deepcopy(json.loads(text))
replacements = []
for row in plan['objects']:
    obj = expected_scene
    for part in row['path'].strip('/').split('/'):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    assert obj['__guid'] == row['id'] and obj['Name'] == 'Beech shrub'
    assert obj['Position'] == row['old_position'] and obj['Scale'] == row['old_scale']
    marker = '"__guid": "' + row['id'] + '"'
    assert text.count(marker) == 1
    start = text.index(marker)
    end = text.index('"Components"', start)
    header = text[start:end]
    for field, key, old_key in [('Position', 'position', 'old_position'), ('Scale', 'scale', 'old_scale')]:
        matches = list(re.finditer(r'"' + field + r'"\s*:\s*("[^"\\]*")', header))
        assert len(matches) == 1
        match = matches[0]
        assert json.loads(match.group(1)) == row[old_key]
        replacements.append((start + match.start(1), start + match.end(1), json.dumps(row[key])))
        obj[field] = row[key]
assert len(replacements) == 488
for start, end, value in sorted(replacements, reverse=True):
    text = text[:start] + value + text[end:]
assert json.loads(text) == expected_scene
incoming = SCENE.with_name(SCENE.name + '.grounding-incoming')
assert not incoming.exists()
try:
    incoming.write_bytes(text.encode('utf8'))
    assert json.loads(incoming.read_bytes()) == expected_scene
    require_closed()
    assert sha(SCENE) == plan['before_scene_sha256']
    os.replace(incoming, SCENE)
finally:
    incoming.unlink(missing_ok=True)
result = {'before_scene_sha256': plan['before_scene_sha256'], 'after_scene_sha256': sha(SCENE),
          'garden_plants_changed': 244, 'transform_string_values_changed': 488,
          'all_other_scene_bytes_preserved': True, 'editor_closed_during_save': True,
          'native_visual_validation_pending': True,
          'reason': 'Editor repeatedly exited during startup before any native connection became available.'}
(OUT / 'closed-editor-publication.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
