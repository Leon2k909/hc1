"""Run the photographic-look review scripts through the installed native editor CLI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import copy
import uuid
import hashlib
import tempfile


def protocol_call(name=None, arguments=None):
    """Use MCP stdin for documents larger than Windows's command-line limit."""
    with tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as errors:
        process = subprocess.Popen(['rtk', 'proxy', str(engine_path() / 'bin/managed/sbox-cli.exe'), '--connect'],
                                   cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
                                   text=True, encoding='utf-8')

        def send(message):
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()

        def receive(ident):
            while True:
                line = process.stdout.readline()
                if not line:
                    errors.seek(0)
                    raise RuntimeError('Native MCP disconnected: ' + errors.read())
                if line.startswith('[rtk]'):
                    continue
                message = json.loads(line)
                if message.get('id') is None and 'error' in message:
                    raise RuntimeError(str(message['error']))
                if message.get('id') != ident:
                    continue
                if 'error' in message:
                    raise RuntimeError(str(message['error']))
                return message['result']
        try:
            send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-11-25', 'capabilities': {},
                'clientInfo': {'name': 'hc1-photographic-review', 'version': '1'}}})
            initialized = receive(1)
            if name is None:
                return initialized
            if Path(initialized['_meta']['project']).resolve() != (ROOT / 'hc1.sbproj').resolve():
                raise RuntimeError('Native MCP project changed.')
            send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments or {}}})
            response = receive(2)
            if response.get('isError'):
                raise RuntimeError(str(response.get('content')))
            if 'structuredContent' in response:
                return response['structuredContent']
            text = '\n'.join(c['text'] for c in response.get('content', []) if c['type'] == 'text')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            process.stdout.close()

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Sources/Rendering/photographic-look-v1'
OUTPUT = ROOT / 'output/photographic-look-20261027'


def engine_path():
    value = os.environ.get('FACEPUNCH_ENGINE')
    if not value:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            value = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
    return Path(value)


def call(name, arguments=None):
    if arguments is not None and len(json.dumps(arguments)) > 16000:
        return protocol_call(name, arguments)
    command = ['rtk', 'proxy', str(engine_path() / 'bin/managed/sbox-cli.exe'), '--call', name]
    if arguments is not None:
        command.append(json.dumps(arguments))
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=360)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    text = result.stdout.strip()
    # RTK may print its first-run hint before the native output.
    text = '\n'.join(line for line in text.splitlines() if not line.startswith('[rtk]'))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def install_cameras():
    """Use the editor's resource tools, preserving every existing camera property and identity."""
    result = []
    for path in ['prefabs/player/cameras/default_player_camera.prefab', 'scenes/theater_playback.scene']:
        document = call('asset_read', {'path': path})
        original = copy.deepcopy(document)
        native_path = ROOT / 'Assets' / path
        backup = OUTPUT / 'before' / path
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(native_path.read_bytes())

        def walk(obj):
            yield obj
            for child in obj.get('Children', []):
                yield from walk(child)

        roots = [document['RootObject']] if 'RootObject' in document else document['GameObjects']
        cameras = [o for top in roots for o in walk(top)
                   if any(c['__type'] == 'Sandbox.CameraComponent' and not c.get('Orthographic', False)
                          for c in o.get('Components', []))]
        if len(cameras) != 1:
            raise RuntimeError(f'Expected one perspective camera in {path}, got {len(cameras)}.')
        camera = cameras[0]
        effects = [c for c in camera['Components'] if c['__type'] == 'Facepunch.PhotographicResponse']
        if not effects:
            camera['Components'].append({
                '__type': 'Facepunch.PhotographicResponse',
                '__guid': str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/' + path + '/photographic-response')),
                '__enabled': True, 'Strength': 0.65, 'LocalContrast': 0.15, 'HighlightDesaturation': 0.12,
                'EdgeSoftness': 0.18, 'Aberration': 0.3, 'Grain': 0.012,
            })
            written = call('asset_write', {'path': path, 'json': json.dumps(document, indent=2)})
            if not written.get('Success'):
                raise RuntimeError(f'Editor did not save {path}: {written}')
        current = call('asset_read', {'path': path})
        if current != document:
            raise RuntimeError(f'Editor resource readback differs for {path}.')
        stripped = copy.deepcopy(current)
        stripped_roots = [stripped['RootObject']] if 'RootObject' in stripped else stripped['GameObjects']
        for top in stripped_roots:
            for obj in walk(top):
                obj['Components'] = [c for c in obj.get('Components', []) if c['__type'] != 'Facepunch.PhotographicResponse']
        if not effects and stripped != original:
            raise RuntimeError(f'Unrelated data changed in {path}.')
        result.append({'path': path, 'camera': camera['Name'], 'saved': True, 'existing_data_preserved': True})
    return {'cameras': result}


def install_indirect_light():
    path = 'scenes/maps/Ares/ares.scene'
    if any(s['ResourcePath'].lower() == path.lower() for s in call('list_scenes')['Scenes']):
        raise RuntimeError('Ares is open; use scene tools to integrate its reviewed volume.')
    document = call('asset_read', {'path': path})
    original = copy.deepcopy(document)
    expected = json.loads((OUTPUT / 'ares-gi-v1/scene-before.json').read_text(encoding='utf-8'))
    if document != expected:
        raise RuntimeError('Ares changed since the bake; inspect the changes before adoption.')
    volume = json.loads((SOURCE / 'ares-indirect-light.json').read_text(encoding='utf-8'))
    for prop in ['IrradianceTexture', 'DistanceTexture', 'RelocationTexture']:
        if not (ROOT / 'Assets' / (volume['Components'][0][prop] + '_c')).is_file():
            raise RuntimeError('Missing native lighting texture: ' + prop)
    document['GameObjects'].append(volume)
    result = call('asset_write', {'path': path, 'json': json.dumps(document, indent=2)})
    current = call('asset_read', {'path': path})
    if not result.get('Success') or current != document:
        raise RuntimeError('Native Ares readback differs; inspect before retrying.')
    stripped = copy.deepcopy(current)
    stripped['GameObjects'] = [o for o in stripped['GameObjects'] if o.get('__guid') != volume['__guid']]
    if stripped != original:
        raise RuntimeError('An unrelated Ares property changed.')
    textures = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in (ROOT / 'Assets/lighting/ares/photographic-v1').glob('*.vtex_c')}
    return {'scene': path, 'volume': volume['__guid'], 'intensity': 0.65, 'saved': True,
            'existing_scene_data_preserved': True, 'textures': textures}


def build_report():
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    load = lambda name: json.loads((OUTPUT / name).read_text(encoding='utf-8'))
    checks = load('source-validation.json')
    assert all(checks.values())
    native = load('integration-verification-native.json')
    assert native['EditorStatePreserved'] and native['ShaderMaterialValid']
    assert all(t['Valid'] for t in native['BakedTextures'])
    compilers = [c for c in load('final-compile-status.json')['Compilers'] if 'razedtest' in c['Name']]
    assert all(c['Success'] and not c['IsBuilding'] and c['Errors'] == 0 for c in compilers)
    evidence = {name: load(name + '-native.json')
                for name in ['daylight-review', 'ares-gi-reduced', 'identity-control']}
    assert all(e['EditorStatePreserved'] and e['TemporaryScenesDestroyed'] for e in evidence.values())
    folder = OUTPUT / 'identity-control'
    base = np.asarray(Image.open(folder / 'boxyard-control-before.png').convert('RGB')).astype(float)
    controls = {}
    for variant in ['after', 'repeat', 'zero']:
        current = np.asarray(Image.open(folder / ('boxyard-control-' + variant + '.png')).convert('RGB')).astype(float)
        difference = np.abs(current - base)
        controls[variant] = {'mean_absolute_rgb_8bit': float(difference.mean()),
                             'percentile_99_rgb_8bit': float(np.percentile(difference, 99))}
    assert controls['repeat']['mean_absolute_rgb_8bit'] < .005
    assert controls['zero']['mean_absolute_rgb_8bit'] < .005
    assert controls['after']['mean_absolute_rgb_8bit'] > .02
    assert (ROOT / 'Assets/shaders/hc1_photographic_response.shader').read_bytes() == (SOURCE / 'hc1_photographic_response.shader').read_bytes()
    assert (ROOT / 'Assets/shaders/hc1_photographic_response.shader_c').is_file()
    report = {'installed': True, 'native_compile_errors': 0, 'native_profile_checks': native,
              'source_checks': checks, 'identity_controls': controls,
              'reviewed_maps': ['Ares', 'Belltower', 'Lowtide', 'Veridant', 'Boxyard'],
              'camera_finish_shared_across_maps': True, 'new_baked_light_maps': ['Ares'],
              'full_match_and_controlled_gpu_benchmark_run': False,
              'superseded_evidence': ['first-trial: exposure had not settled'],
              'timing_scope': 'Offscreen rendering with readback only; no gameplay FPS claim.'}
    (OUTPUT / 'review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    canvas = Image.new('RGB', (1800, 1184), '#171b20')
    draw = ImageDraw.Draw(canvas)
    font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/segoeui.ttf'
    font = ImageFont.truetype(str(font_path), 24)
    title_font = ImageFont.truetype(str(font_path), 30)
    draw.text((22, 12), 'ARES — matched exposure and camera position', fill='#f5f5f5', font=title_font)
    for row, (name, title) in enumerate([('ares-hall', 'Atmos Hall'), ('ares-concourse', 'Cargo corridor')]):
        y = 68 + row * 550
        for col, (variant, label) in enumerate([('before', 'Before'), ('after', 'Bounced lighting + camera finish')]):
            x = col * 900
            draw.text((x + 18, y), title + ' · ' + label, fill='#dce1e6', font=font)
            with Image.open(OUTPUT / 'ares-gi-reduced' / (name + '-' + variant + '.png')) as shot:
                canvas.paste(shot.resize((900, 506), Image.Resampling.LANCZOS), (x, y + 34))
    canvas.save(OUTPUT / 'before-after.png')
    return {'review': str(OUTPUT / 'review.json'), 'comparison': str(OUTPUT / 'before-after.png'),
            'checks_passed': True, 'maps_reviewed': 5}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', choices=['audit', 'bake', 'cameras', 'capture', 'gi', 'install', 'report', 'verify'])
    parser.add_argument('--request', type=Path)
    parser.add_argument('--label', default='review')
    args = parser.parse_args()
    if args.script == 'report':
        print(json.dumps(build_report(), indent=2))
        return
    status = call('editor_status')
    if Path(status['Paths']['ProjectRoot']).resolve() != ROOT.resolve():
        raise RuntimeError('Native editor is attached to a different checkout.')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.script in ['cameras', 'gi']:
        result = install_cameras() if args.script == 'cameras' else install_indirect_light()
        (OUTPUT / (args.script + '-install.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
        return
    opened_ares = False
    if args.script == 'bake':
        if status['IsPlaying']:
            raise RuntimeError('Stop the active play test before baking.')
        scenes = call('list_scenes')['Scenes']
        if not any(s['ResourcePath'].lower() == 'scenes/maps/ares/ares.scene' for s in scenes):
            call('open_scene', {'path': 'scenes/maps/Ares/ares.scene'})
            opened_ares = True
            call('switch_scene', {'scene': status['ActiveScenePath']})
    session = call('instance_status')
    exchange = Path(session['ExchangeDirectory'])
    exchange.mkdir(parents=True, exist_ok=True)
    source = SOURCE / (args.script + '.cs.txt')
    target = exchange / (args.script + '.cs')
    target.write_text(source.read_text(encoding='utf-8').replace('SCRIPT_PATH', target.as_posix()), encoding='utf-8')
    if args.request:
        shutil.copyfile(args.request, exchange / 'request.json')
    try:
        result = call('run_csharp', {'path': str(target)})
    finally:
        if opened_ares:
            call('close_scene', {'scene': 'scenes/maps/ares/ares.scene'})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / (args.label + '-native.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if isinstance(result, dict) and 'Captures' in result:
        print(json.dumps({'report': str(OUTPUT / (args.label + '-native.json')),
                          'captures': len(result['Captures']), 'editor_preserved': result['EditorStatePreserved']}, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
