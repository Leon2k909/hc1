"""Stage the missing array separator in the facade's added render import."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/church-windows-v1'
STAGE = OUT/'revision3/stage'
RELATIVE = 'Assets/models/maps/belltower/belltower_centre.vmdl'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT/RELATIVE
    raw = source.read_bytes()
    pattern = rb'(\}\s*)(\{\s*_class\s*=\s*"RenderMeshFile"\s*name\s*=\s*"church_front_windows_v1")'
    matches = list(re.finditer(pattern, raw))
    assert len(matches) == 1, 'Inspect the import definition before changing it.'
    match = matches[0]
    at = match.start()+1
    updated = raw[:at]+b','+raw[at:]
    assert updated[:at]+updated[at+1:] == raw
    assert not (STAGE/'manifest.json').exists()
    target = STAGE/RELATIVE; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(updated)
    backup = STAGE/'before'/RELATIVE; backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, backup)
    previous = json.loads((OUT/'revision2/stage/manifest.json').read_text())
    manifest = {**previous, 'stage_revision': 'revision3', 'repair': 'One separator before church_front_windows_v1',
        'source_sha256': {p: sha(ROOT/p) for p in previous['source_sha256']},
        'files': {RELATIVE: {'source': target.relative_to(ROOT).as_posix(), 'before': sha(source), 'after': sha(target),
                            'backup': backup.relative_to(ROOT).as_posix()}}}
    (STAGE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'revision': 'revision3'}))
    print('Staged a one-byte render-import separator correction.')


if __name__ == '__main__': main()
