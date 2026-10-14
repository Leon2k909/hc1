"""Architectural contact/rain/lime masks for Lowtide's four low sheds.

Layout is read from the actual block/facade/window generator in memory. This
module writes a 2048px numerical mask, never model, collision or scene files.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

import map_kit as K
from lowtide_brick import metadata
from lowtide_facade import smooth_noise

CELL, PAD, HEIGHT = 512, 8, 512.0
RESOURCE = 'materials/lowtide/masonry/shed_wear.png'
FACES = ('-e', '+e', '-n', '+n')


def material_inputs(strength=.9):
    return f'    TextureShedWear "{RESOURCE}"\n    g_flShedWear "{strength:.3f}"\n'


def layout(L):
    records = []
    selected = None
    old_facade, old_window, old_speicher = L.facade, L.window, L.speicher
    def collect_facade(model, wall, style, eaves, bays, **kw):
        nonlocal selected
        depth, _, _ = L.wall_out(wall)
        selected = None
        for building, bounds in enumerate((L.QUAY_SHED, L.YARD_SHED)):
            e0, e1, n0, n1 = bounds
            if wall.axis == 'n' and depth in (e0, e1) and n0 <= wall.run[0] <= wall.run[1] <= n1:
                face = 0 if depth == e0 else 1
            elif wall.axis == 'e' and depth in (n0, n1) and e0 <= wall.run[0] <= wall.run[1] <= e1:
                face = 2 if depth == n0 else 3
            else:
                continue
            selected = {'building': building, 'face': face, 'bounds': list(bounds),
                        'eaves': eaves, 'run': list(wall.run), 'windows': []}
            records.append(selected)
            old_facade(model, wall, style, eaves, bays, **kw)
            selected = None
            return
        # Other closed blocks are irrelevant to this mask.
    def collect_window(model, wall, opening, style, pane=None, glass=None):
        if selected is not None:
            selected['windows'].append({'r0': opening.r0, 'r1': opening.r1,
                                        'sill': opening.z0-4.4, 'head': opening.z1})
    try:
        L.facade, L.window = collect_facade, collect_window
        L.speicher = lambda *args, **kwargs: None
        L.half()
    finally:
        L.facade, L.window, L.speicher = old_facade, old_window, old_speicher
    assert len(records) == 8
    assert {(r['building'], r['face']) for r in records} == {(b, f) for b in range(2) for f in range(4)}
    return records


def elevation(record, side):
    rng = np.random.default_rng(78093 + record['building']*1709 + record['face']*139 + side*719)
    size = CELL-2*PAD
    e0, e1, n0, n1 = record['bounds']
    run = (n0, n1) if record['face'] < 2 else (e0, e1)
    x = np.linspace(*run, size)[None, :]
    z = np.linspace(HEIGHT, 0, size)[:, None]
    fine = smooth_noise(rng, (size, size), (16, 125))
    patches = smooth_noise(rng, (size, size), (19, 13))
    mask = np.zeros((size, size, 3), dtype=np.float32)
    def deposit(top, span, depth=35, amount=.5):
        drop = top-z
        under = (drop >= 0)
        fade = np.maximum(1-np.maximum(drop, 0)/depth, 0)**1.6 * under
        contact = np.exp(-np.maximum(drop, 0)/2.6)*under*span
        rain = span*fade*(.2+.8*fine)*(.35+.65*patches)*amount
        mask[..., 0] = np.maximum(mask[..., 0], contact*.62)
        mask[..., 1] = np.maximum(mask[..., 1], rain)
        mask[..., 2] = np.maximum(mask[..., 2], rain*np.clip((patches-.65)*2.5, 0, 1)*.32)
    for opening in record['windows']:
        lo, hi = opening['r0']-4.35, opening['r1']+4.35
        span = np.clip((x-lo+2)/4, 0, 1)*np.clip((hi+2-x)/4, 0, 1)
        edges = np.maximum(np.exp(-((x-lo-3)/5.0)**2), np.exp(-((x-hi+3)/5.0)**2))
        deposit(opening['sill'], span*(.24+edges*.76), rng.uniform(28, 58), .78)
    eaves = record['eaves']
    deposit(eaves-22, np.ones_like(x), 38, .65)
    # The projecting corbels repeat at their real sixteen-inch spacing.
    for centre in np.arange(record['run'][0]+10, record['run'][1]-6, 16):
        deposit(eaves-36, np.exp(-((x-centre)/3.3)**2), 15, .32)
    deposit(eaves+40, np.ones_like(x), 20, .38)
    if record['face'] >= 2:
        for pipe in (e0+14, e1-16):
            near = np.exp(-np.abs(x-pipe)/6.5)*(z<eaves+40)
            mask[..., 0] = np.maximum(mask[..., 0], near*.20)
            mask[..., 1] = np.maximum(mask[..., 1], near*(.24+.3*patches)*(.35+.65*fine))
    # Irregular splash dirt at the foundation; never a solid level stripe.
    damp = np.clip(1-z/(23+patches*27), 0, 1)*(.4+.6*patches)
    mask[..., 1] = np.maximum(mask[..., 1], damp*.60)
    mask[..., 0] = np.maximum(mask[..., 0], np.exp(-z/3)*.30)
    return np.pad(np.rint(np.clip(mask, 0, 1)*255).astype(np.uint8),
                  ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')


def bake(L, report_dir=None):
    # These tight exterior bounds are mirrored in the shader mapping.
    assert tuple(L.QUAY_SHED) == (1300, 1950, -1050, -600)
    assert tuple(L.YARD_SHED) == (300, 620, -980, -700)
    records = layout(L)
    rows = []
    for building in range(2):
        for side in range(2):
            rows.append(np.concatenate([elevation(next(r for r in records if
                r['building']==building and r['face']==face), side) for face in range(4)], axis=1))
    atlas = np.concatenate(rows, axis=0)
    path=K.ASSETS/RESOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(atlas).save(path)
    metadata(path)
    folder=Path(report_dir) if report_dir else K.ROOT/'output/lowtide/quality-pass'
    folder.mkdir(parents=True, exist_ok=True)
    report={'meaning':['ambient contact','rain and splash deposits','lime'], 'size':[2048,2048],
            'cell':CELL,'padding':PAD,'height':HEIGHT,'faces':FACES,'records':records,
            'window_count':sum(len(r['windows']) for r in records)*2}
    (folder/'shed-weathering-layout.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    import lowtide_map as L
    print(json.dumps(bake(L)))
