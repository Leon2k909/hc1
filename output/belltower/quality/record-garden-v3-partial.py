"""Record the verified partial import without touching live editor resources."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUALITY = ROOT/'output/belltower/quality'
manifest = json.loads((QUALITY/'models/garden-v3/native-import.json').read_text())
states = json.loads((QUALITY/'garden-v3-native/partial-import-state.json').read_text())
assert len(states) == 2
for state in states:
    assert state['current'] in (state['expected'], state['staged'])
    assert state['backup'] == state['expected']
    path = ROOT/'Assets'/state['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == state['current']
published = [s['path'] for s in states if s['current'] == s['staged']]
pending = [s['path'] for s in states if s['current'] == s['expected']]
assert published == ['models/maps/belltower/belltower_east.obj']
assert pending == ['models/maps/belltower/belltower_west.obj']
assert states[1]['incoming'] == states[1]['staged']
path = QUALITY/'garden-v3-checkpoint.json'
checkpoint = json.loads(path.read_text())
checkpoint.update({
    'state': 'partial native import; west publication and native review pending',
    'native_assets_replaced': True,
    'native_import_complete': False,
    'published_assets': published,
    'pending_assets': pending,
    'partial_import_record': 'output/belltower/quality/garden-v3-native/partial-import-state.json',
    'editor_window': 'Released at the human request to wait. Saved Cerro Blanco remained selected, play stopped. No compile or capture followed the west OBJ replacement failure. Resume the checked import in a later coordinated window.',
})
path.write_text(json.dumps(checkpoint, indent=2)+'\n')

path = ROOT/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
old = '''    Garden v3 is staged only: its wheelbarrow chassis stays below the basin, with four mounts and lowered braces.'''
new = '''    Garden v3 is partly imported: its wheelbarrow chassis stays below the basin, with four mounts and lowered braces.'''
assert text.count(old) == 1
text = text.replace(old, new)
old = '''    to installed v2. The import request selects v3; the accepted manifest still records installed v2. Wait for the
    next coordinated window, then compile and capture the wheelbarrow and terrace before recording acceptance.'''
new = '''    to the accepted v2 predecessor. East is now the checked v3 OBJ; west remains v2 after Windows denied atomic
    replacement. Both v2 backups and the staged incoming west file match their expected hashes, recorded in
    `garden-v3-native/partial-import-state.json`. The accepted manifest still records v2; do not treat this partial
    import as accepted. The editor was released on saved Cerro Blanco, play stopped, at the human request to wait.
    Resume the checked native import in a later coordinated window, then compile both models and capture the
    wheelbarrow and terrace before recording acceptance.'''
assert text.count(old) == 1
text = text.replace(old, new)
incoming = path.with_name('CLAUDE.belltower-partial.tmp')
assert not incoming.exists()
incoming.write_text(text, encoding='utf-8', newline='')
assert path.read_bytes() == before, 'CLAUDE changed concurrently; inspect before replacing.'
incoming.replace(path)
print(json.dumps({'published': published, 'pending': pending, 'backups_checked': 2}))
