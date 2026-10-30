"""Archive only the rejected, unplaced fixture files owned by this task."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
from veridant_install_lamp_placement import no_editor
from veridant_stage_lamp_placement import sha

no_editor()
manifest = json.loads((ROOT / 'output/veridant/modern-lamp-v1/asset-stage-v1/manifest.json').read_text())
for relative, item in manifest['files'].items():
    assert sha(ROOT / relative) == item['sha256'], ('Prototype file changed', relative)

archive = (ROOT / 'output/veridant/modern-lamp-v1/rejected-prototype').resolve()
assert archive.is_relative_to(ROOT.resolve())
targets = ('Assets/materials/veridant/modern-lamp-v1',
           'Assets/models/props/veridant/modern-lamp-v1',
           'Sources/Veridant/modern-lamp-v1',
           'Tools/veridant_modern_lamp.py',
           'Tools/veridant_stage_modern_lamp.py')
receipt = []
for relative in targets:
    source = (ROOT / relative).resolve()
    destination = (archive / relative).resolve()
    assert source.is_relative_to(ROOT.resolve()) and destination.is_relative_to(archive)
    assert source.exists() and not destination.exists()
    files = [source] if source.is_file() else [p for p in source.rglob('*') if p.is_file()]
    digests = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    no_editor()
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    for original, digest in digests.items():
        assert sha(archive / original) == digest
    receipt.append({'source': str(source), 'archive': str(destination), 'files': len(files)})
(ROOT / 'output/veridant/lamp-placement-v1/rejected-prototype-archive.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'archived_task_owned_paths': len(receipt), 'original_lanterns_retained': True}))
