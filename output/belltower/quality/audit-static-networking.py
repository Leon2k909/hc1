"""Inspect saved static visuals without loading or changing the shared editor scene."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/belltower/quality/network-static-audit'
scene_path = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'
source = scene_path.read_bytes()
scene = json.loads(source)
native = json.loads((OUT / 'run_csharp.json').read_text(encoding='utf-8'))
assert not native.get('isError')
enums = json.loads(next(c['text'] for c in native['content'] if c['type'] == 'text'))
snapshot = enums['NetworkModes']['Snapshot']
never = enums['NetworkModes']['Never']
excluded_flags = enums['GameObjectFlags']['EditorOnly'] | enums['GameObjectFlags']['NotNetworked']
types = {'Sandbox.ModelRenderer', 'Sandbox.SkinnedModelRenderer', 'Sandbox.EnvmapProbe',
         'Sandbox.IndirectLightVolume', 'Sandbox.DirectionalLight', 'Sandbox.PointLight',
         'Sandbox.SpotLight', 'Sandbox.SkyBox2D', 'Sandbox.Tonemapping', 'Sandbox.Bloom',
         'Sandbox.AmbientOcclusion', 'Sandbox.Fog', 'Sandbox.VolumetricFogVolume'}
objects, issues, lighting = {}, [], []
counts = Counter()
mode_counts = Counter()


def visit(obj, ancestors):
    objects[obj['__guid']] = obj
    chain = ancestors + [obj]
    labels = [item.get('Name', '<unnamed>') for item in chain]
    mode = obj.get('NetworkMode')
    mode_counts[str(mode)] += 1
    component_types = [item.get('__type') for item in obj.get('Components', [])]
    visual_types = [name for name in component_types if name in types]
    for name in visual_types:
        counts[name] += 1
    if visual_types:
        rejected = [item.get('Name', '<unnamed>') for item in chain
                    if item.get('NetworkMode') == never or item.get('Flags', 0) & excluded_flags
                    or item.get('NetworkTransmit') is False]
        missing = [item.get('Name', '<unnamed>') for item in chain if item.get('NetworkMode') is None]
        if rejected or missing:
            issues.append({'path': labels, 'components': visual_types,
                           'excluded_ancestors_or_self': rejected, 'missing_mode': missing})
    for component in obj.get('Components', []):
        if component.get('__type') in ('Sandbox.EnvmapProbe', 'Sandbox.IndirectLightVolume'):
            lighting.append({'path': labels, 'network_modes': [x.get('NetworkMode') for x in chain],
                             'flags': [x.get('Flags', 0) for x in chain],
                             'type': component['__type'], 'mode': component.get('Mode'),
                             'textures': {k: v for k, v in component.items() if k.endswith('Texture')}})
    for child in obj.get('Children', []):
        visit(child, chain)


for obj in scene['GameObjects']:
    visit(obj, [])
cache_checks = []


def texture_paths(value):
    if isinstance(value, dict):
        return {key: item['Path'] if key.endswith('Texture') and isinstance(item, dict)
                and set(item) <= {'Id', 'Path'} and 'Path' in item else texture_paths(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [texture_paths(item) for item in value]
    return value


for relative in ('Sources/Belltower/lighting/reflections.json', 'Sources/Belltower/lighting/indirect.json',
                 'Sources/Belltower/landscape/forest.json'):
    data = json.loads((ROOT / relative).read_text(encoding='utf-8'))
    assert isinstance(data, dict) and '__guid' in data
    installed = objects.get(data['__guid'])
    cache_checks.append({'path': relative, 'present_in_scene': installed is not None,
                         'matches_saved_object': installed == data,
                         'matches_after_texture_reference_normalization': texture_paths(installed) == texture_paths(data)})
report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
          'scope': 'saved scene and regeneration caches only; no live client validation',
          'scene_sha256': hashlib.sha256(source).hexdigest(), 'native_enums': enums,
          'saved_objects': len(objects), 'object_network_modes': dict(mode_counts),
          'objects_without_explicit_network_mode': [{'name': item.get('Name'), 'guid': item['__guid'],
              'components': [c.get('__type') for c in item.get('Components', [])]}
              for item in objects.values() if item.get('NetworkMode') is None],
          'static_component_counts': dict(counts), 'lighting': lighting, 'issues': issues,
          'regeneration_cache_checks': cache_checks,
          'runtime_client_verified': False, 'editor_mutated': False}
assert scene_path.read_bytes() == source
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: report[key] for key in ('saved_objects', 'object_network_modes', 'static_component_counts',
                                              'issues', 'regeneration_cache_checks', 'runtime_client_verified')}))
