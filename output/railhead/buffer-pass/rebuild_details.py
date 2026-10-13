import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'Tools'))
import railhead_map as R

glass = R.Model()
for name, model in (
    ('railhead_dress_east', R.dress_side(1)),
    ('railhead_dress_west', R.dress_side(-1)),
    ('railhead_dress_centre', R.dress_centre()),
):
    glass.extend(R.split_paints(model, R.GLASS_PAINTS))
    R.configure(model)
    count = R.K.write_model(R.OUT_DIR, R.RESOURCE_DIR, name, model)
    print(name + ': ' + str(count) + ' triangles', flush=True)
R.configure(glass)
R.K.write_model(R.OUT_DIR, R.RESOURCE_DIR, 'railhead_dress_glass', glass)

# Preserve all other scene content while bringing in the new local reflection probes.
scene = json.loads(R.SCENE_FILE.read_text())
group = next(item for item in scene['GameObjects'] if item['Name'] == 'Reflection Probes')
names = {item['Name'] for item in group['Children']}
for record in R.PROBES:
    if record[0].startswith('Track Ends') and 'Probe ' + record[0] not in names:
        group['Children'].append(R.probe_object(*record))
R.SCENE_FILE.write_text(json.dumps(scene, indent=2), encoding='utf-8')
print('Updated track-end reflection probes', flush=True)
