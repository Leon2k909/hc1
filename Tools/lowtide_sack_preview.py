"""Offline matched construction views; no engine rendering or albedo editing."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import map_kit as K
import lowtide_sacks as OLD
import lowtide_sack_construction as S
import lowtide_window_software as R

OUT = K.ROOT/'output/lowtide/quality-pass/sack-construction/preview'
VIEWS = {
    'single': dict(eye=(1.1, -1.5, .95), target=(0., 0., .12), scale=.90, size=(1050, 850)),
    'mouth': dict(eye=(.35, -1.5, .45), target=(0., -.37, .13), scale=.45, size=(1050, 760)),
    'stack': dict(eye=(1.55, -2.1, 1.25), target=(.275, .432, .28), scale=1.75, size=(1100, 900)),
}


def shadow_map(triangles):
    """Align depth texel centres with the review renderer's integer receivers.

    Its plane correction evaluates a shadow sample at (index / (size-1)).
    rasterise() evaluates at index+.5, so translate the raster geometry by .5.
    Without this, shallow surfaces can acquire whole-triangle self shadows.
    This adapter changes no legacy renderer or other candidate evidence.
    """
    points = triangles[..., :3]
    right = K.normalise(np.cross(R.SUN, (0, 0, 1)))
    up = np.cross(R.SUN, right)
    flat = points.reshape(-1, 3)
    projected = np.column_stack((flat@right, flat@up))
    minimum = projected.min(axis=0)-2
    span = projected.max(axis=0)-minimum+2
    size = 2048
    screen = ((projected-minimum)/span*(size-1)+.5).reshape(-1, 3, 2)
    depth = np.full((size, size), -1e8, np.float32)
    dummy = np.zeros((size, size, 3), np.float32)
    R.PV.rasterise(dummy, depth, screen, points@R.SUN, np.zeros((len(points), 3)))
    return depth, right, up, minimum, span


def model(label, stacked=False):
    m = K.Model()
    m.box((-50, -55, -1.5), (75, 85, -.02), 'review_ground')
    m.tile_overrides['review_ground'] = 64.
    build = S.sack if label == 'candidate' else OLD.sack
    for layer in range(2 if stacked else 1):
        for i in range(2 if stacked else 1):
            for j in range(2 if stacked else 1):
                lo = (-10.5 + i*22 + layer*.65, -16.5 + j*34, layer*11)
                build(m, lo, (21, 33, 11))
    return m


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = OLD.TEXTURES/'lt_jute_color.png'
    rgb = np.asarray(Image.open(source).convert('RGB'), np.float32)/255
    linear = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    mats = {S.PAINT: dict(texture=linear, scale=np.ones(2), rough=.95),
            'review_ground': dict(texture=np.array([[[.16, .17, .18]]], np.float32), scale=np.ones(2), rough=.8)}
    exports = {}
    for label in ('before', 'candidate'):
        for kind, stacked in (('single', False), ('stack', True)):
            path = out/f'{kind}-{label}.obj'
            K.write_obj(path, model(label, stacked), 'sack-review')
            exports[path.name] = S.sha(path)
            triangles, paints = R.read_obj(path)
            shadows = shadow_map(triangles)
            names = ('stack',) if stacked else ('single', 'mouth')
            for name in names:
                image = R.render(triangles, paints, mats, shadows, VIEWS[name])
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, image.height-25, image.width, image.height), fill=(20, 22, 23))
                draw.text((10, image.height-19), f'OFFLINE CONSTRUCTION | {label.upper()} | original jute pixels | matched CPU lighting, no engine GI or fibre normals', fill=(225, 225, 220))
                image.save(out/f'{name}-{label}.png')
                print(f'Rendered {name} {label}', flush=True)
    provenance = dict(kind='Matched CPU construction views', native_engine_capture=False,
        generator_sha256=S.sha(S.__file__), reviewer_sha256=S.sha(__file__), renderer_sha256=S.sha(R.__file__),
        source_colour_sha256=S.sha(source), source_colour_pixels_preserved=True,
        shadow_sampling='Geometry shifted half a pixel to match the receiver plane texel-centre convention',
        exported_meshes=exports, views=VIEWS,
        previews={p.name:S.sha(p) for p in sorted(out.glob('*.png'))},
        limitations=['No engine GI, fibre normal mapping, texture mip/compression or temporal rendering',
                     'Isolated sack examples; integration and gameplay cost remain unverified'])
    (out/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    main(parser.parse_args().output)
