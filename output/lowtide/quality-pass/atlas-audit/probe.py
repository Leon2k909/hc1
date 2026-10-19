"""Read-only inventory of exact repeated image borders; never edits source pixels."""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / 'Assets'
OUT = Path(__file__).parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapped_uvs(mesh, paints):
    uvs = []
    faces = {paint: [] for paint in paints}
    paint = None
    with mesh.open() as stream:
        for line in stream:
            values = line.split()
            if not values:
                continue
            if values[0] == 'vt':
                uvs.append(tuple(map(float, values[1:3])))
            elif values[0] == 'usemtl':
                paint = values[1]
            elif values[0] == 'f' and paint in faces:
                face = np.asarray([uvs[int(v.split('/')[1])-1] for v in values[1:]])
                for i in range(1, len(face)-1):
                    faces[paint].append(face[[0, i, i+1]])
    return {paint: np.asarray(triangles) for paint, triangles in faces.items()}


def check_meshes():
    checks = []
    cases = [
        ('fleet', {'lt_bridge_deck': (1254/2048, 1254/2048)}),
        ('backdrop', {'lt_shipyard_panorama': (2172/4096, 680/1024),
                      'lt_shipyard_peripheral': (2172/4096, 650/1024)}),
        ('finish', {'lt_drain_iron': (1254/2048, 1254/2048),
                    'lt_drain_edge': (1254/2048, 1254/2048)}),
    ]
    for name, paints in cases:
        mesh = ASSETS / f'models/maps/lowtide/lowtide_{name}.obj'
        for paint, uv in mapped_uvs(mesh, paints).items():
            assert len(uv), paint
            # Source OBJ has upward V; the native importer flips it.
            samples = np.concatenate((uv.reshape(-1, 2), uv.mean(axis=1)))
            samples[:, 1] = 1-samples[:, 1]
            raw_bounds = [samples.min(axis=0).tolist(), samples.max(axis=0).tolist()]
            repeat = paint.startswith('lt_drain_')
            if repeat:
                samples %= 1
            limit = np.asarray(paints[paint])
            outside = np.any((samples < -0.000006) | (samples > limit+0.000006), axis=1)
            checks.append(dict(mesh=mesh.relative_to(ROOT).as_posix(), sha256=sha(mesh),
                               paint=paint, triangles=len(uv), importer_uv_bounds=raw_bounds,
                               uv_limit=limit.tolist(), samples=len(samples),
                               padding_samples=int(outside.sum()), wraps=repeat,
                               classification='known_pending_drain_fix' if repeat else 'explicit_bounded_uvs'))
            if not repeat:
                assert not outside.any(), (paint, checks[-1])
    return checks


def main():
    materials = []
    textures = {}
    for path in sorted((ASSETS / 'materials/lowtide').rglob('*.vmat')):
        props = dict(re.findall(r'^\s*(\w+)\s+"([^"\n]*)"', path.read_text(), re.M))
        color = props.get('TextureColor', '')
        material = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
                        shader=props.get('shader'), texture=color,
                        regions={k:v for k,v in props.items() if 'Region' in k},
                        scales={k:v for k,v in props.items() if 'Scale' in k or 'Tile' in k})
        materials.append(material)
        texture = ASSETS / color
        if not texture.is_file() or texture.suffix.lower() != '.png' or color in textures:
            continue
        with Image.open(texture) as image:
            a = np.asarray(image.convert('RGBA'))
        changed_x = np.flatnonzero(np.any(a[:, 1:] != a[:, :-1], axis=(0, 2)))
        changed_y = np.flatnonzero(np.any(a[1:] != a[:-1], axis=(1, 2)))
        valid_w = int(changed_x[-1]) + 2 if len(changed_x) else 1
        valid_h = int(changed_y[-1]) + 2 if len(changed_y) else 1
        textures[color] = dict(sha256=sha(texture), size=[a.shape[1], a.shape[0]],
                               last_varied_extent=[valid_w, valid_h],
                               right_repeat=a.shape[1]-valid_w,
                               bottom_repeat=a.shape[0]-valid_h)
    mesh_checks = check_meshes()
    report = dict(materials=materials, textures=textures, mesh_checks=mesh_checks,
                  limitation='Repeated borders flag candidates only; mesh UV and shader checks are required.')
    (OUT / 'inventory.json').write_text(json.dumps(report, indent=2)+'\n')
    for color, info in textures.items():
        if info['right_repeat'] < 8 and info['bottom_repeat'] < 8:
            continue
        print(color, info['size'], 'varied', info['last_varied_extent'])
        for material in materials:
            if material['texture'] == color:
                print(' ', Path(material['path']).name, material['shader'], material['regions'])
    print('TOTAL', len(materials), 'materials;', len(textures), 'unique PNG inputs')
    for check in mesh_checks:
        print(check['paint'], check['triangles'], 'triangles;', check['padding_samples'],
              '/', check['samples'], 'padding samples;', check['classification'])


if __name__ == '__main__':
    main()
