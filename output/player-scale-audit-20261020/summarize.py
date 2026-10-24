"""Record scale measurements and source references without changing game assets."""
from pathlib import Path
import ast
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar(node, constants):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name): return constants[node.id]
    if isinstance(node, ast.UnaryOp):
        value = scalar(node.operand, constants)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        a, b = scalar(node.left, constants), scalar(node.right, constants)
        if isinstance(node.op, ast.Add): return a+b
        if isinstance(node.op, ast.Sub): return a-b
        if isinstance(node.op, ast.Mult): return a*b
        if isinstance(node.op, ast.Div): return a/b
    raise ValueError(type(node).__name__)


map_scales = []
for path in sorted((ROOT/'Assets/scenes/maps').rglob('*.scene')):
    try: source = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, UnicodeError): continue
    todo = [(node, (1., 1., 1.)) for node in source.get('GameObjects', [])]
    models = []
    while todo:
        node, parent = todo.pop()
        scale = tuple(float(s) for s in node.get('Scale', '1,1,1').split(','))
        world = tuple(a*b for a, b in zip(scale, parent))
        for component in node.get('Components', []):
            if not component.get('__type', '').endswith('ModelRenderer'): continue
            model = component.get('Model')
            resource = model.get('Path', '') if isinstance(model, dict) else model or ''
            if 'models/maps/' in resource:
                models.append({'name': node.get('Name'), 'model': resource, 'world_scale': world})
        todo.extend((child, world) for child in node.get('Children', []))
    if models:
        map_scales.append({'scene': path.relative_to(ROOT).as_posix(), 'sha256': sha(path),
                           'map_renderers': len(models), 'non_unit_scale': [m for m in models if any(abs(s-1)>1e-6 for s in m['world_scale'])]})

openings = []
for path in sorted((ROOT/'Tools').glob('*_map.py')):
    if 'belltower_map' not in path.name and path.stem.split('_map')[0].lower() not in {
        Path(m['scene']).parent.name.lower() for m in map_scales}: continue
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try: constants[node.targets[0].id] = scalar(node.value, constants)
            except (KeyError, ValueError, ZeroDivisionError): pass
    for node in ast.walk(tree):
        args = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add' and len(node.args) >= 5:
            args = node.args[:5]
        elif isinstance(node, ast.Tuple) and len(node.elts) == 5:
            args = node.elts
        if args is None or not isinstance(args[4], ast.Constant) or args[4].value not in ('door', 'shop', 'shut', 'arch'): continue
        try:
            width, low, high = (scalar(n, constants) for n in args[1:4])
        except (KeyError, ValueError, ZeroDivisionError): continue
        if high <= low or width <= 0: continue
        openings.append({'source': path.relative_to(ROOT).as_posix(), 'line': node.lineno, 'kind': args[4].value,
                         'width_inches': width, 'height_inches': high-low,
                         'width_metres': width*.0254, 'height_metres': (high-low)*.0254})
    for name, value in constants.items():
        if name in ('DOOR_H', 'UPPER_DOOR_H'):
            line = next(n.lineno for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
            openings.append({'source': path.relative_to(ROOT).as_posix(), 'line': line, 'constant': name,
                             'height_inches': value, 'height_metres': value*.0254})

native = json.loads((OUT/'native-measurements.json').read_text())
samples = json.loads((OUT/'live-fov/measurements.json').read_text())
ads = json.loads((OUT/'live-fov/ads.json').read_text())
ratios = {str(int(s['Requested'])): s['ReferenceTarget']['FractionOfViewportHeight'] for s in samples}
observed = ratios['60']/ratios['85']
expected = math.tan(math.radians(85/2))/math.tan(math.radians(60/2))
assert abs(observed-expected) < .001
assert all(abs(s['Actual']-s['Requested']) < .001 and s['Mode'] == 'FirstPerson' and s['LifeState'] == 'Alive' for s in samples)
assert not any(m['non_unit_scale'] for m in map_scales)
restoration = json.loads((OUT/'live-fov/restoration.json').read_text())
assert all(restoration.values())
images = [{**{k:s[k] for k in ['Requested', 'Actual', 'Image']}, 'sha256': sha(ROOT/s['Image']),
           'bitmap_size': [1280, 720], 'live_viewport_size': s['Screen'],
           'purpose': 'Qualitative framing check; HUD coordinates use the live viewport and are not a centering test.'} for s in samples]
reference_openings = [r for r in openings if r.get('kind') == 'door' or r.get('constant')]
report = {
    'task': 'Whole-game character scale, camera height, FOV and environment proportion audit',
    'canonical_project': str(ROOT),
    'native_models': native['Models'],
    'maps': map_scales,
    'map_count': len(map_scales), 'map_renderers_checked': sum(m['map_renderers'] for m in map_scales),
    'global_map_scale_multiplier_found': False,
    'live_camera_samples': samples,
    'fov_85_to_60_size_ratio': {'native_projection': observed, 'perspective_prediction': expected, 'passed': True},
    'standing_camera_inches': samples[0]['CameraHeight'],
    'animated_eye_mean_inches': sum(b['Height'] for b in samples[0]['EyeBones'] if b['Name'].startswith('eye_'))/2,
    'ads_samples': ads,
    'independent_ads_at_60_shrinks_targets_relative_to_hip': math.tan(math.radians(60/2))/math.tan(math.radians(80/2)),
    'normal_iron_sight_zoom_85_to_80': math.tan(math.radians(85/2))/math.tan(math.radians(80/2)),
    'architectural_reference_openings': reference_openings,
    'all_statically_resolved_openings': openings,
    'architecture_audit_limit': 'Only statically resolved wall apertures/constants; cargo portals, arches and shop fronts must not be treated as ordinary single-person doors.',
    'images': images,
    'findings': [
        'Loaded adult reference meshes are about 1.75 m tall; player and bot roots and bodies are at unit scale.',
        'Live first-person FOV follows the setting exactly at 60, 85 and 120 degrees horizontally.',
        'The live camera is close to the animated combat-pose eye height; bind-pose eye height overstates this gap.',
        'The measured editor game viewport was 1138 by 455 pixels. A smaller displayed game pane can reduce physical on-screen target size relative to full-screen play; internal render resolution alone does not.',
        'Several architectural apertures are deliberately much larger than human dimensions. This changes perceived person-to-building scale.',
        'The first-person weapon shares world FOV; it does not have an independent viewmodel FOV.',
        'Independent ADS ignores hip FOV and can widen a 60-degree hip view to 80-degree iron-sight view. The tested current setting was Affected.',
        'Editor viewport, first-person, third-person/deathcam and Independent ADS use different FOV paths.'
    ],
    'limits': [
        'No specific CoD title, matching-distance screenshot or display size was provided; this is an internal scale/projection audit, not a numerical CoD model-height comparison.',
        'Character vertex measurements are reference-pose geometry, while live eye bones were sampled from the actual animated player.',
        'Map transform checks cover authored map model references, not the physical dimensions of every individual scenery prop.'
    ],
    'gameplay_source_or_assets_changed_by_this_audit': False,
    'temporary_fov_and_god_mode_restoration': restoration,
    'sources': [
        'https://sbox.game/dev/doc/assets/ready-to-use-assets/citizen-characters',
        'https://www.callofduty.com/blog/2020/11/Black-Ops-Cold-War-Controls-and-Settings-PC',
        'https://www.callofduty.com/au/en/blog/2026/08/call-of-duty-modern-warfare-4-next-highlights-multiplayer-gameplay-systems'
    ]
}
(OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'maps': len(map_scales), 'map_renderers': report['map_renderers_checked'],
                  'fov_ratio': observed, 'animated_eye_height': report['animated_eye_mean_inches'],
                  'door_reference_heights_metres': {name: sorted(set(round(r['height_metres'], 3) for r in reference_openings if name in r['source']))
                    for name in ['belltower', 'lowtide', 'ares', 'ridgeback', 'railhead']}}))
