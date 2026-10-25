"""Revalidate a fully staged patch after an unrelated source guard changed."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).resolve().parent
previous = json.loads((folder/'r4/manifest.json').read_text())
manifest = json.loads(json.dumps(previous))
for name, row in manifest['files'].items():
    for key in ('source', 'backup'):
        row[key] = row[key].replace('/r4/', '/r6/')
    target, backup, staged = root/name, root/row['backup'], root/row['source']
    def sha(p):
        with p.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    before = sha(backup)
    assert sha(target) == before, ('Concurrent geometry edit', name)
    unchanged = hashlib.sha256()
    moved = 0
    side = 'west' if '/west/' in name or 'belltower_west' in name else 'east'
    offsets = [[-p['new'][0]+p['old'][0], 0., p['new'][1]-p['old'][1]]
               for p in manifest['models'][side]['translations']]
    with backup.open('rb') as a, staged.open('rb') as b:
        for old, new in itertools.zip_longest(a, b):
            assert old is not None and new is not None
            if old == new:
                unchanged.update(old)
                continue
            assert old.startswith(b'v ') and new.startswith(b'v ')
            delta = [y-x for x,y in zip(map(float,old.split()[1:]),map(float,new.split()[1:]))]
            assert len(delta) == 3 and any(max(abs(x-y) for x,y in zip(delta,v)) < .0021 for v in offsets)
            moved += 1
    assert moved == row['moved_position_rows'], (name, moved)
    row.update(before=before, after=sha(staged), unchanged_rows_sha256=unchanged.hexdigest())
    assert sha(target) == before
for path, expected in manifest['source_sha256'].items():
    if path != 'Tools/belltower_map.py':
        assert sha(root/path) == expected
assert sha(root/'Assets/scenes/maps/Belltower/belltower.scene') == manifest['protected_sha256']['Assets/scenes/maps/Belltower/belltower.scene']
manifest_path = folder/'r6/manifest.json'
assert not manifest_path.exists()
manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
subprocess.run(['rtk','proxy','python','-X','utf8',str(folder/'r4/revalidate.py'),'r6'],cwd=root,check=True)
(folder/'revision.txt').write_text('r6')
subprocess.run(['rtk','proxy','python','-X','utf8','output/knife-throw/editor_check.py',
    '--script',str(folder/'import.cs.txt'),'--output-dir',str(folder/'native-import-final-r6'),
    '--direct-call','--cleanup-exchange','--timeout','60'],cwd=root,check=True)
