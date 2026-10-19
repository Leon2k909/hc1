"""Record the inspected offline firewood comparison, without accepting live assets."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'output/belltower/quality/firewood-v1-studio'
hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
relative = lambda path: path.relative_to(ROOT).as_posix()
trial = json.loads((FOLDER / 'trial.json').read_text(encoding='utf-8'))
checks = json.loads((FOLDER / 'geometry-checks.json').read_text(encoding='utf-8'))
assert checks['passed'] and checks['trial_sha256'] == hash_file(FOLDER / 'trial.json')
for path, expected in trial['source_sha256'].items():
    assert hash_file(ROOT / path) == expected, path
captures = {}
for name in ('firewood-before', 'firewood-after'):
    record = json.loads((FOLDER / f'{name}-render.json').read_text(encoding='utf-8'))
    assert record['model_sha256'] == hash_file(FOLDER / f'{name}.obj')
    assert record['image_sha256'] == hash_file(FOLDER / f'{name}.png')
    captures[name] = record
for key in ('preview_source_sha256', 'camera_position', 'camera_rotation', 'lens', 'size',
            'review_bounds', 'view_transform', 'exposure', 'samples'):
    assert captures['firewood-before'][key] == captures['firewood-after'][key], key
report = {
    'checked_utc': datetime.now(timezone.utc).isoformat(),
    'state': 'offline construction comparison reviewed; not integrated or natively accepted',
    'generator': 'Tools/belltower_firewood_trial.py',
    'trial_sha256': hash_file(FOLDER / 'trial.json'),
    'source_sha256': trial['source_sha256'],
    'images': {name: {'path': relative(FOLDER / f'{name}.png'), 'sha256': record['image_sha256']}
               for name, record in captures.items()},
    'same_camera_and_studio_lighting': True,
    'generated_assets': [
        {'source': f'Sources/Belltower/generated/firewood-{name}-v1.png',
         'prompt_and_provenance': f'Sources/Belltower/generated/firewood-{name}-v1.json',
         'generator': 'built-in image_gen',
         'prompt': json.loads((ROOT / f'Sources/Belltower/generated/firewood-{name}-v1.json').read_text(encoding='utf-8'))['prompt']}
        for name in ('cuts', 'bark', 'split')],
    'review': [
        'Rounded irregular bark silhouettes replace the repeated seven-sided extrusions.',
        'The cut faces show annual rings and drying cracks, with four source variants and varied rotations.',
        'Broad split faces now use raw lengthwise fibres instead of furniture board strips.',
        'The comparison uses fixed framing and exposure -1.2; these are Blender renders, not engine captures.'
    ],
    'geometry': {'logs': 34, 'split_logs': 27, 'triangles_before': 1768, 'triangles_after': 8024,
                 'added_triangles_per_pile': 6256, 'checked_placements': 2, 'closed_surface': True,
                 'within_existing_prop_bounds': True, 'collision_authored': False},
    'production_garden_generator_unchanged': checks['production_generator_unchanged'],
    'live_assets_written': False,
    'remaining': [
        'Finish and review garden v3 before changing its pinned generator or source manifest.',
        'Integrate the candidate into staged whole-map models and native materials, then verify collision and gameplay checks.',
        'The generated albedos currently have no matching surface normal maps.',
        'Compare appearance and runtime cost in the native editor before any acceptance.'
    ]
}
(FOLDER / 'offline-review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
source_record = ROOT / 'Sources/Belltower/gardens/firewood-trial-v1.json'
source_record.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'review': relative(source_record), 'same_camera': True, 'native_accepted': False}))
