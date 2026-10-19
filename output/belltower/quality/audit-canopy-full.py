"""Record the full-size candidate and inspect its material dependencies."""
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT/'output/belltower/quality/canopy-photo-v2-full'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


manifest_path = STAGE/'native-import.json'
manifest = json.loads(manifest_path.read_text())
for group in ('source_hashes', 'base_inputs'):
    for path, digest in manifest[group].items():
        assert sha(ROOT/path) == digest, path
for item in manifest['files']:
    assert sha(ROOT/item['source']) == item['sha256'], item['source']
accepted = manifest['accepted_manifest']
assert sha(ROOT/accepted['path']) == accepted['sha256']

trial_prefix = 'materials/belltower/vista/canopy-photo-v2/'
base_prefix = 'materials/belltower/vista/'
available = {item['path'] for item in manifest['files']}
references = []
for original, candidate in manifest['material_overrides'].items():
    content = (STAGE/Path(candidate).name).read_text()
    assert content.replace(trial_prefix, base_prefix) == (ROOT/'Assets'/original).read_text()
    references.extend(re.findall(r'"(materials/[^\"]+)"', content))
assert all(path in available or (ROOT/'Assets'/path).is_file() for path in references)

zones = []
for zone in 'abcd':
    name = f'vista_{zone}_color.jpg'
    before = np.asarray(Image.open(ROOT/'Assets/materials/belltower/vista'/name), dtype=np.int16)
    after = np.asarray(Image.open(STAGE/name), dtype=np.int16)
    assert before.shape == after.shape == (4096, 4096, 3)
    difference = np.abs(after-before)
    kind_name = f'vista_{zone}_kind.png'
    kind_before = np.asarray(Image.open(ROOT/'Assets/materials/belltower/vista'/kind_name))
    kind_after = np.asarray(Image.open(STAGE/kind_name))
    normal = f'vista_{zone}_normal.jpg'
    assert sha(STAGE/normal) == sha(ROOT/'Assets/materials/belltower/vista'/normal)
    zones.append({'zone':zone, 'colour_sha256':sha(STAGE/name),
                  'mean_absolute_colour_difference_8bit':float(difference.mean()),
                  'changed_colour_pixel_fraction':float(np.any(difference != 0, axis=2).mean()),
                  'changed_kind_pixel_fraction':float((kind_before != kind_after).mean()),
                  'terrain_normal_unchanged':True})
assert zones[0]['changed_colour_pixel_fraction'] == zones[0]['changed_kind_pixel_fraction'] == 0

report = {
    'checked_utc':datetime.now(timezone.utc).isoformat(),
    'state':'full-resolution offline candidate staged; native compilation and review pending',
    'manifest_sha256':sha(manifest_path), 'zones':zones,
    'material_changes':'Texture references only; all other material text matches the accepted inputs.',
    'resolved_texture_references':len(references), 'trial_assets':len(manifest['files']),
    'published_trial_assets':sum((ROOT/'Assets'/item['path']).exists() for item in manifest['files']),
    'review':[
        'The full-resolution zone C candidate has finer, less circular natural woodland crowns than the accepted texture.',
        'Zone B retains the orchard pattern and adds natural crown detail along woodland edges.',
        'The far zone still shows broad procedural woodland bands and simplified fields. This canopy change does not finish the landscape quality goal.',
        'Zone A is byte-identical to the accepted colour/kind maps. All four terrain normal maps are byte-identical.',
    ],
    'native_sequence':[
        'Run import-canopy-trial.cs.txt through the native editor in a coordinated window.',
        'Compile the separate vista_land.vmat and forest_trees.vmat, then run verify-canopy-trial.cs.txt.',
        'Capture matching saved and --canopy-trial views at valley, west-ridge and terrace, confirming exact material restoration.',
        'Review native quality and performance before changing any accepted landscape input or manifest.',
    ],
    'native_verified':False,
}
(STAGE/'offline-review.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
