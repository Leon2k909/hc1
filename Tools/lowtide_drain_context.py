"""Inspect drainage junctions against saved architecture, without the editor.

Clips exact saved triangles to a small review volume. Neutral architectural
colours make intersections visible; these are construction views, not native
lighting or material acceptance. Input OBJ pixels and all live files are read-only.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import ImageDraw

import map_kit as K
import lowtide_drain_construction as D
import lowtide_drain_review as REVIEW
import lowtide_window_software as R
from lowtide_sack_preview import shadow_map

BASE = K.ROOT/'output/lowtide/quality-pass/drain-construction'
CASES = {
    'shed': dict(origin=(1314., -1050., 276.), out=(0., -1., 0.), architecture='lowtide_east'),
    'warehouse': dict(origin=(1000., 207., 942.), out=(1., 0., 0.), architecture='lowtide_east'),
}
VIEWS = {
    'oblique': dict(eye=(.9, 1.5, .60), target=(0., .08, -.16), scale=1.65, size=(1100, 1000)),
    'side': dict(eye=(1.2, .5, .13), target=(0., .08, -.16), scale=1.50, size=(1100, 1000)),
}


def clip(points, lo, hi):
    for axis in range(3):
        for edge, sign in ((lo[axis], 1), (hi[axis], -1)):
            result = []
            for a, b in zip(points, np.roll(points, -1, axis=0)):
                av, bv = sign*(a[axis]-edge), sign*(b[axis]-edge)
                if av >= -1e-9: result.append(a)
                if (av < -1e-9) != (bv < -1e-9):
                    result.append(a+(b-a)*av/(av-bv))
            points = np.asarray(result)
            if len(points) < 3: return []
    return [np.array((points[0], points[i], points[i+1])) for i in range(1, len(points)-1)
            if np.linalg.norm(np.cross(points[i, :3]-points[0, :3], points[i+1, :3]-points[0, :3])) > 1e-8]


def extract(path, cases):
    positions, uvs, normals = [], [], []
    outputs = {name:([], []) for name in cases}
    axes = {}
    for name, case in cases.items():
        out = np.asarray(case['out'])
        axes[name] = np.column_stack((np.cross(out, (0, 0, 1)), out, (0, 0, 1)))
    paint = None
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith(('v ', 'vn ')):
                values = line.split()
                x, y, z = map(float, values[1:])
                (positions if values[0] == 'v' else normals).append((-x, z, y))
            elif line.startswith('vt '): uvs.append(tuple(map(float, line.split()[1:])))
            elif line.startswith('usemtl '): paint = line.split()[1]
            elif line.startswith('f '):
                refs = [tuple(int(v)-1 for v in token.split('/')) for token in line.split()[1:]]
                p = np.asarray([positions[i] for i, _, _ in refs])
                for name, case in cases.items():
                    local = (p-np.asarray(case['origin']))@axes[name]
                    lo, hi = np.array((-25., -13., -42.)), np.array((25., 20., 20.))
                    if np.any(local.max(axis=0) < lo) or np.any(local.min(axis=0) > hi): continue
                    attrs = np.column_stack((local, [uvs[i] for _, i, _ in refs],
                                             np.asarray([normals[i] for _, _, i in refs])@axes[name]))
                    clipped = clip(attrs, lo, hi)
                    outputs[name][0].extend(clipped)
                    outputs[name][1].extend([paint]*len(clipped))
    return outputs


def main(out, candidate):
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve())
    out.mkdir(parents=True, exist_ok=True)
    R.SUN = K.normalise((-.5, .8, 1.))
    architecture = K.ASSETS/'models/maps/lowtide/lowtide_east.obj'
    structures = extract(architecture, CASES)
    source_paths = {'architecture':architecture, 'before':K.ASSETS/'models/maps/lowtide/lowtide_finish.obj',
                    'candidate':Path(candidate).resolve()}
    metal = REVIEW.materials(BASE, True)
    for label in ('before', 'candidate'):
        fittings = extract(source_paths[label], CASES)
        for name in CASES:
            triangles = np.asarray(structures[name][0]+fittings[name][0])
            paints = structures[name][1]+fittings[name][1]
            mats = dict(metal)
            for paint in set(paints)-set(mats):
                color = (.12, .16, .20) if 'slate' in paint else (.32, .21, .15) if 'brick' in paint else (.25, .27, .26)
                mats[paint] = dict(texture=np.asarray([[color]], np.float32), scale=np.ones(2), rough=.8)
            for view, spec in VIEWS.items():
                result = R.render(triangles, paints, mats, shadow_map(triangles), spec)
                draw = ImageDraw.Draw(result)
                draw.rectangle((0, result.height-30, result.width, result.height), fill=(20, 23, 26))
                draw.text((10, result.height-22), f'OFFLINE {name.upper()} | {label.upper()} | exact saved geometry, clipped review volume | neutral wall/roof materials', fill=(230, 230, 225))
                result.save(out/f'{name}-{view}-{label}.png')
                print(f'Rendered {name} {view} {label}', flush=True)
    record = dict(native_capture=False, source_files={p.relative_to(K.ROOT).as_posix():D.sha(p) for p in source_paths.values()},
                  reviewer_sha256=D.sha(__file__), renderer_sha256=D.sha(R.__file__),
                  shadow_adapter_sha256=D.sha(K.ROOT/'Tools/lowtide_sack_preview.py'),
                  metal_inputs={p.relative_to(K.ROOT).as_posix():D.sha(p) for p in (
                      K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png',
                      BASE/'stage/materials/lowtide/finish/lt_drain_iron.vmat',
                      BASE/'stage/materials/lowtide/finish/lt_drain_edge.vmat')},
                  cases=CASES, views=VIEWS, previews={p.name:D.sha(p) for p in out.glob('*.png')},
                  materials='Both versions share the staged metal mapping correction to isolate geometry changes.',
                  limitations='Clipped construction context with neutral architecture; does not validate native lighting or material appearance.')
    (out/'provenance.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=BASE/'stage/models/maps/lowtide/lowtide_finish.obj')
    args = parser.parse_args()
    main(args.output, args.candidate)
