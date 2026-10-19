"""Matched CPU construction views of the exact staged loading-door geometry.

The live albedo and atlas coordinates are read directly. Normal mapping, engine
GI and performance are not reproduced; these are offline geometry previews.
"""
import json
import re

import numpy as np
from PIL import Image

import map_kit as K
import lowtide_map as L
import lowtide_door_construction as D
import lowtide_window_construction as W
import lowtide_window_software as R

OUT = K.ROOT/'output/lowtide/quality-pass/door-construction/preview'
VIEWS = {
    'whole': dict(eye=(3.8, -8., 3.4), target=(0., 0., 2.15), scale=5.15, size=(1100, 1100)),
    'hinge': dict(eye=(-.15, -3.4, 1.4), target=(-1.18, .1, .45), scale=1.35, size=(1100, 900)),
    'handles': dict(eye=(1.2, -3.4, 1.75), target=(0., .12, 1.05), scale=.85, size=(1100, 1000)),
}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    wall = K.Wall('e', (-82, 82), (0, 20), (0, 198), '-n')
    opening = wall.add(0, 120, 0, 170, 'shut')
    common = K.Model()
    wall.build(common, 'brick', None, 'brick', None, None)
    L.courses(common, wall, L.EAST, ())
    L.leaves_shut(common, wall, opening, L.EAST)
    candidate = K.Model()
    for paint, items in common.polygons.items():
        if paint in (L.EAST.door, D.IRON): continue
        for i, (points, normal) in enumerate(items):
            candidate.polygon(paint, points, normal, uv=common.polygon_uvs.get((paint, i)))
    D.leaf_geometry(candidate, L, wall, opening, L.EAST, D.mapping())
    W.validate_model(candidate)
    for label, model in (('before', common), ('candidate', candidate)):
        L.configure(model)
        K.write_obj(OUT/f'{label}.obj', model, 'lowtide_east')
    inputs = {}
    for paint in common.polygons:
        resource = common.material_overrides.get(paint, K.BT.material_path(paint))
        text = (K.ASSETS/resource).read_text()
        inputs[paint] = dict(resource=resource, inputs=dict(re.findall(r'^\s*(\w+)\s+"([^"\r\n]*)"', text, re.M)))
    (OUT/'materials.json').write_text(json.dumps(inputs, indent=2)+'\n')
    return inputs


def materials(inputs):
    old_out = R.OUT
    try:
        R.OUT = OUT
        result = R.materials()
    finally:
        R.OUT = old_out
    for paint, data in inputs.items():
        if 'g_vDoorRegion' in data['inputs']:
            result[paint]['region'] = R.number_array(data['inputs']['g_vDoorRegion'], [0, 0, 1, 1])
            result[paint]['scale'] = R.number_array(data['inputs']['g_vDoorScale'], [1, 1])
            result[paint]['rough'] = .84
    return result


def main():
    inputs = prepare()
    mats = materials(inputs)
    for label in ('before', 'candidate'):
        triangles, paints = R.read_obj(OUT/f'{label}.obj')
        shadows = R.shadow_map(triangles)
        for name, spec in VIEWS.items():
            R.render(triangles, paints, mats, shadows, spec).save(OUT/f'cpu-{name}-{label}.png')
            print(f'Rendered {label} {name}', flush=True)
    # The west-side material uses the same photographed board atlas layout.
    red_path = K.ASSETS/'materials/lowtide/lt_door_red_color.png'
    rgb = np.asarray(Image.open(red_path).convert('RGB'), np.float32)/255
    mats[L.EAST.door]['texture'] = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    R.render(triangles, paints, mats, shadows, VIEWS['whole']).save(OUT/'cpu-whole-red-candidate.png')
    provenance = dict(kind='Offline CPU construction rendering', native_engine_capture=False,
                      image_generation=False, geometry='Exact before/candidate OBJ exports',
                      geometry_generator_sha256=D.sha(D.__file__), renderer_sha256=D.sha(R.__file__),
                      exported_meshes={name: D.sha(OUT/f'{name}.obj') for name in ('before', 'candidate')},
                      textures='Current unmodified production albedo with the door shader atlas mapping and OBJ V flip',
                      lighting='Matched directional shadow maps and approximate diffuse/specular response',
                      limitations=['No engine normal mapping, GI, material weathering or runtime performance validation'],
                      views=VIEWS)
    (OUT/'cpu-provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
