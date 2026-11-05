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
    elif sys.argv[1] in ('capture', 'lod2'):
        template = (ROOT / 'Sources/Spillway/canvas-cover-v2/compare.cs.txt').read_text()
        template = template.replace('spillway_east.vmdl', 'spillway_west.vmdl').replace('models/maps/spillway/pallet_v2/pallet.vmdl', MODEL)
        cameras = {
            'standing': ((-1170, 300, 70), (-1320, 220, 70), 60),
            'front': ((-1120, 220, 78), (-1320, 220, 71), 46),
            'low': ((-1218, 285, 42), (-1315, 220, 67), 58),
            'detail': ((-1243, 252, 78), (-1308, 220, 75), 55),
            'far': ((-930, 370, 72), (-1320, 220, 72), 50),
        }
        if sys.argv[1] == 'lod2':
            cameras = {name: value for name, value in cameras.items() if name in ('standing', 'far')}
            template = template.replace('go.Components.Create<ModelRenderer>().Model = model;',
                'var added = go.Components.Create<ModelRenderer>(); added.Model = model; if (path == "' + MODEL + '") added.LodOverride = 2;')
        results = {}
        for setup in (('before', 'after') if sys.argv[1] == 'capture' else ('lod2',)):
            shots = ', '.join(f'("{setup}_{name}", {pos(*eye)}, {pos(*target)}, {fov}f)' for name, (eye, target, fov) in cameras.items())
            placed = '' if setup == 'before' else f'("{MODEL}", {pos(-1328,220,25)},0f), ("{TEMP}west_rest.vmdl",Vector3.Zero,0f)'
            code = template.replace('%OUT%', 'output/asset-improvement-20261030/spillway-vent/matched').replace('%SHOTS%', shots)
            code = code.replace('%PLACE%', placed).replace('%HIDE%', str(setup != 'before').lower())
            code = code.replace('%HIDE_MATS%', ', '.join('"' + m + '"' for m in manifest['hidden_materials']))
            result = editor.script(code, setup + '.cs')
            print(setup, json.dumps(result), flush=True)
            results[setup] = result
        (WORK / ('native-captures.json' if sys.argv[1] == 'capture' else 'native-lod2.json')).write_text(json.dumps(results, indent=2))
    elif sys.argv[1] == 'check':
        generator_changed = False
        for path, expected in manifest['unchanged'].items():
            matches = hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
            if path == 'Tools/spillway_map.py':
                generator_changed = not matches
            else:
                assert matches, 'Saved render input changed during review: ' + path
        status = editor.call('editor_status')
        print(json.dumps(status, indent=2))
        model = editor.script('''var model = Model.Load("models/maps/spillway/wall_vent_v2/wall_vent.vmdl");
if (model is null || model.IsError) throw new InvalidOperationException("Wall vent model is invalid.");
return new { Model = model.ResourcePath, model.Bounds, Materials = model.Materials.Select(m => m?.ResourcePath).ToArray() };''', 'check-model.cs')
        print(json.dumps(model, indent=2))
        console = editor.call('read_console', dict(minimumLevel='Error', filter='wall_vent', limit=10))
        print(console)
        (WORK / 'native-validation.json').write_text(json.dumps(dict(Editor=status, Model=model, Console=console,
            SavedMapUnchanged=True, SavedSceneUnchanged=True, GeneratorChangedSincePreparation=generator_changed), indent=2))
        print('Saved west model and scene match their review hashes.')
        if generator_changed:
            print('The generator changed separately after preparation; review tools do not write it. Current hose placement is retained.')
