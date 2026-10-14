"""Retain native editor checks and the exact source/capture fingerprints."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).resolve().parent
exchange = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/b85c6516c54b41ca8eb4fb9aaecf25af')
for name in ('check-water-editor-lifecycle.cs', 'capture-water-fallback.cs',
             'capture-water-command.cs', 'inspect-camera-capture.cs',
             'capture-water-editor-route.cs', 'capture-water-diagnostic.cs'):
    shutil.copy2(exchange / name, folder / name)
files = [
    root / 'Code/Map/LowtideWaterReflections.cs',
    root / 'Assets/scenes/maps/lowtide/lowtide.scene',
    root / 'Assets/shaders/hc1_lowtide_water.shader',
    root / 'Assets/materials/lowtide/lt_water.vmat',
    *(folder / (name + '.png') for name in
      ('water-editor-fixed', 'water-bank-fixed', 'water-quay-fixed')),
]
result = {
    'scope': 'Editor rendering route; no shader, material, geometry or scene edit',
    'engine': '26.10.13',
    'lifecycle': json.loads((folder / 'water-editor-lifecycle.json').read_text()),
    'compile': {'success': True, 'errors': 0, 'water_diagnostics': []},
    'global_errors_since_cursor_667': [],
    'final_console_cursor': 681,
    'gameplay_tested_this_pass': False,
    'performance_claim': None,
    'sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
}
(folder / 'water-editor-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'checks': len(result['lifecycle']['checks']), 'files': len(files),
                  'scene_clean': not result['lifecycle']['HasUnsavedChanges']}))
