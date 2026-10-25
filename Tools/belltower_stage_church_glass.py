"""Stage only the church facade's three private glazing materials."""
import hashlib
import json
from pathlib import Path
import shutil
import belltower_church_windows as W

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/church-windows-v1'
STAGE = OUT/'revision4/stage'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (STAGE/'manifest.json').exists()
    previous = json.loads((OUT/'revision3/stage/manifest.json').read_text())
    manifest = {**previous, 'stage_revision': 'revision4', 'repair': 'Private glazing readability adjustment', 'files': {},
        'source_sha256': {p: sha(ROOT/p) for p in previous['source_sha256']}}
    manifest['protected_sha256']['Assets/shaders/cerroblanco_glass.shader'] = sha(ROOT/'Assets/shaders/cerroblanco_glass.shader')
    for name, text in W.glass_materials().items():
        relative = 'Assets/materials/belltower/church-windows-v1/'+name+'.vmat'
        installed = ROOT/relative; target = STAGE/relative; backup = STAGE/'before'/relative
        target.parent.mkdir(parents=True, exist_ok=True); target.write_text(text)
        backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(installed, backup)
        manifest['files'][relative] = {'before': sha(installed), 'after': sha(target),
            'source': target.relative_to(ROOT).as_posix(), 'backup': backup.relative_to(ROOT).as_posix()}
    (STAGE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'revision': 'revision4'}))
    print('Staged three private glazing materials; shared shaders unchanged.')


if __name__ == '__main__': main()
