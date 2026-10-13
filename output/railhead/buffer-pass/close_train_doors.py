from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K
import railhead_map as R
import railhead_props as P
import railhead_train as T

records = []
doorway = T.doorway

def record(car, xs, d0, d1, opened=False):
    records.append((opened, car.p(xs * (P.EMU_W - .5), (d0 + d1) * .5, 80)))
    return doorway(car, xs, d0, d1, opened)

T.doorway = record
out = ROOT / 'Assets/models/maps/railhead'
for side, name in ((1, 'railhead_dress_east'), (-1, 'railhead_dress_west')):
    start = len(records)
    model = R.dress_side(side)
    assert not R.MISSING, R.MISSING
    assert len(records) - start == 16, 'Expected every door on both two-car trains'
    for opened, point in records[start:]:
        assert not opened, 'A train door was generated open'
        def contains(box):
            centre, axes, size, surface = box
            local = np.asarray(axes) @ (point - centre)
            return np.all(abs(local) <= np.asarray(size) * .5 + 1e-5)
        assert any(contains(box) for box in model.boxes), 'Unblocked doorway at {}'.format(point)
    # The saloon glazing is unchanged; keep the existing shared glass model.
    R.split_paints(model, R.GLASS_PAINTS)
    R.configure(model)
    count = K.write_model(out, 'models/maps/railhead', name, model)
    print('{}: rebuilt {} triangles; 16 door pairs closed and blocked'.format(name, count), flush=True)
print('PASS: all 32 door pairs on four trains closed, with solid collision', flush=True)
