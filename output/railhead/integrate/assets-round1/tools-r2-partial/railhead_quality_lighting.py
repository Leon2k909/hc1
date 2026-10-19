"""Preserve a completed native Railhead lighting bake for map regeneration."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'Sources/Railhead/lighting'
TEXTURES = ('IrradianceTexture', 'DistanceTexture', 'RelocationTexture')


def normalize_volume(volume):
    component = next(c for c in volume['Components'] if c['__type'] == 'Sandbox.IndirectLightVolume')
    if component['BakeVersion'] != 1:
        raise ValueError('The volume does not contain a completed native bake')
    for field in TEXTURES:
        value = component[field]
        path = value['Path'] if isinstance(value, dict) else value
        if not path.startswith('lighting/railhead/') or not path.endswith('.vtex') or '..' in path:
            raise ValueError(f'Unexpected Railhead lighting texture: {path}')
        asset = ROOT / 'Assets' / (path + '_c')
        if not asset.is_file() or not asset.stat().st_size:
            raise FileNotFoundError(asset)
        component[field] = path
    return component


def load_object():
    path = DESTINATION / 'indirect.json'
    if not path.is_file():
        return None
    volume = json.loads(path.read_text(encoding='utf-8'))
    normalize_volume(volume)
    return volume


def preserve(capture):
    directory = (ROOT / 'output/railhead/quality' / capture).resolve()
    if not directory.is_relative_to(ROOT / 'output/railhead/quality'):
        raise ValueError('Capture must remain inside the Railhead quality directory')
    result = json.loads((directory / 'bake-result.json').read_text(encoding='utf-8'))
    status = (directory / 'bake-status.txt').read_text(encoding='utf-8').strip()
    if result.get('Passes') != 2 or result.get('SavedFinalIrradiance') is not True or status != 'Complete ' + result['Grid']:
        raise ValueError('The final native lighting pass has not completed')
    volume = json.loads((directory / 'indirect-light.json').read_text(encoding='utf-8'))
    component = normalize_volume(volume)
    sources = [ROOT / 'Assets' / (component[field] + '_c') for field in TEXTURES]
    sources += sorted((ROOT / 'Assets/models/maps/railhead').glob('*.vmdl'))
    sources += sorted((ROOT / 'Assets/models/maps/railhead').glob('*.obj'))
    sources += sorted((ROOT / 'Assets/materials/railhead').rglob('*.vmat'))
    hashes = {}
    for source in sources:
        with source.open('rb') as stream:
            hashes[source.relative_to(ROOT).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'engine': '26.10.13', 'capture': capture, 'native_bake': result,
                'grid': result['Grid'], 'runtime_intensity': component['RuntimeIntensity'],
                'normal_bias': component['NormalBias'], 'view_bias': component['ViewBias'],
                'source_sha256': hashes,
                'rebake': 'Use the native editor after changing geometry, materials or lighting.'}
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, value in (('indirect.json', volume), ('manifest.json', manifest)):
        pending = DESTINATION / (name + '.pending')
        pending.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        pending.replace(DESTINATION / name)
    print(f'Preserved {capture}: {result["Grid"]}, two completed passes, three checked native textures')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    preserve(parser.parse_args().capture)
