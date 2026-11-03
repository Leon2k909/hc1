"""Native import and isolated matched renders for the wall vent. python review.py compile|capture|check"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor

WORK = ROOT / 'output/asset-improvement-20261030/spillway-vent'
MODEL = 'models/maps/spillway/wall_vent_v2/wall_vent.vmdl'
TEMP = 'models/compare_old/spillway_vent_v2/'
manifest = json.loads((WORK / 'review_manifest.json').read_text())


def pos(e, n, z):
    return f'new Vector3({n}f, {-e}f, {z}f)'


with Editor() as editor:
    if sys.argv[1] == 'compile':
        for path in [MODEL, TEMP + 'old_vent.vmdl', TEMP + 'west_rest.vmdl']:
            result = editor.call('asset_compile', dict(path=path))
            assert result.get('Success'), result
            print(json.dumps(result), flush=True)
    elif sys.argv[1] == 'capture':
        template = (ROOT / 'Sources/Spillway/canvas-cover-v2/compare.cs.txt').read_text()
        template = template.replace('spillway_east.vmdl', 'spillway_west.vmdl').replace('models/maps/spillway/pallet_v2/pallet.vmdl', MODEL)
        cameras = {
            'standing': ((-1170, 300, 70), (-1320, 220, 70), 60),
            'front': ((-1120, 220, 78), (-1320, 220, 71), 46),
            'low': ((-1218, 285, 42), (-1315, 220, 67), 58),
            'detail': ((-1243, 252, 78), (-1308, 220, 75), 55),
            'far': ((-930, 370, 72), (-1320, 220, 72), 50),
        }
        results = {}
        for setup in ('before', 'after'):
            shots = ', '.join(f'("{setup}_{name}", {pos(*eye)}, {pos(*target)}, {fov}f)' for name, (eye, target, fov) in cameras.items())
            placed = '' if setup == 'before' else f'("{MODEL}", {pos(-1328,220,25)},0f), ("{TEMP}west_rest.vmdl",Vector3.Zero,0f)'
            code = template.replace('%OUT%', 'output/asset-improvement-20261030/spillway-vent/matched').replace('%SHOTS%', shots)
            code = code.replace('%PLACE%', placed).replace('%HIDE%', str(setup == 'after').lower())
            code = code.replace('%HIDE_MATS%', ', '.join('"' + m + '"' for m in manifest['hidden_materials']))
            result = editor.script(code, setup + '.cs')
            print(setup, json.dumps(result), flush=True)
            results[setup] = result
        (WORK / 'native-captures.json').write_text(json.dumps(results, indent=2))
    elif sys.argv[1] == 'check':
        for path, expected in manifest['unchanged'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Changed during review: ' + path
        print(json.dumps(editor.call('editor_status'), indent=2))
        print(editor.call('read_console', dict(minimumLevel='Error', filter='wall_vent', limit=10)))
        print('Saved map, scene and generator unchanged by vent review.')
