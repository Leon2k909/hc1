"""Native editor import and matched before/after captures. python review.py discover|compile|capture|check"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from native import Editor

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/asset-improvement-20261030/spillway-hose'
MODEL = 'models/maps/spillway/hose_coil_v2/hose_coil.vmdl'
TEMP = 'models/compare_old/spillway_hose_v2/'


def position(e, n, z):
    return f'new Vector3({n}f, {-e}f, {z}f)'


with Editor() as editor:
    mode = sys.argv[1]
    if mode == 'discover':
        tools = editor.call('search_tools', dict(query='asset_compile'))['tools']
        print(json.dumps([t for t in tools if t['name'] == 'asset_compile'], indent=2))
    elif mode == 'compile':
        for path in [MODEL, TEMP + 'old_hose.vmdl', TEMP + 'cargo_dark_rest.vmdl']:
            print(json.dumps(editor.call('asset_compile', dict(path=path)), indent=2), flush=True)
    elif mode == 'capture':
        template = (ROOT / 'Sources/Spillway/canvas-cover-v2/compare.cs.txt').read_text()
        template = template.replace('spillway_east.vmdl', 'spillway_cargo.vmdl').replace('models/maps/spillway/pallet_v2/pallet.vmdl', MODEL)
        # Match original bounds first, then show construction up close and its readability from a standing player.
        cameras = {
            'standing': ((130, -950, 70), (90, -1080, 3), 55),
            'low': ((114, -1014, 19), (90, -1080, 2.5), 58),
            'above': ((90, -1078, 160), (90, -1080, 0), 52),
            'fittings': ((150, -1085, 29), (120, -1090, 2), 55),
            'far': ((150, -750, 70), (90, -1080, 3), 50),
        }
        results = {}
        for setup in ('before', 'after'):
            shots = ', '.join(f'("{setup}_{name}", {position(*eye)}, {position(*target)}, {fov}f)'
                              for name, (eye, target, fov) in cameras.items())
            placed = '' if setup == 'before' else f'("{MODEL}", {position(90, -1080, 0)}, 0f), ("{TEMP}cargo_dark_rest.vmdl", Vector3.Zero, 0f)'
            code = template.replace('%OUT%', 'output/asset-improvement-20261030/spillway-hose/matched').replace('%SHOTS%', shots)
            code = code.replace('%PLACE%', placed).replace('%HIDE%', str(setup == 'after').lower()).replace('%HIDE_MATS%', '"rv_dark"')
            result = editor.script(code, setup + '.cs')
            print(setup, json.dumps(result), flush=True)
            results[setup] = result
        (WORK / 'native-captures.json').write_text(json.dumps(results, indent=2))
    elif mode == 'check':
        manifest = json.loads((WORK / 'review_manifest.json').read_text())
        for path, expected in manifest['unchanged'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Changed during review: ' + path
        status = editor.call('editor_status')
        print(json.dumps(status, indent=2))
        print(editor.call('read_console', dict(minimumLevel='Error', filter='hose', limit=10)))
        print('Saved scene, map mesh and generator match the pre-review hashes.')
