"""Check frame joins, clear panes, export reproducibility and live-file safety."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'Tools'))
import numpy as np
import map_kit as K
import lowtide_map as L
import lowtide_window_construction as W

OUT = Path(__file__).resolve().parent


def triangles(model):
    return np.array([(points[0], points[k], points[k+1])
                     for faces in model.polygons.values() for points, normal in faces
                     for k in range(1, len(points)-1)])


def ray(tris, origin, direction):
    # Two-sided geometry intersection: validate coverage independently of the
    # smooth shading normals. Winding and normal orientation have separate checks.
    edges1, edges2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    h = np.cross(direction, edges2)
    determinant = np.einsum('ij,ij->i', edges1, h)
    valid = np.abs(determinant) > 1e-9
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
    s = origin - tris[:, 0]
    u = inverse * np.einsum('ij,ij->i', s, h)
    q = np.cross(s, edges1)
    v = inverse * (q @ direction)
    t = inverse * np.einsum('ij,ij->i', edges2, q)
    valid &= (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1+1e-7) & (t >= 0)
    return t[valid].min() if valid.any() else None


def coverage():
    shapes = ((40, 80), (44, 86), (44, 100), (48, 100))
    checked = dict(opaque_rays=0, clear_pane_rays=0, exterior_rays=0, orientations=0)
    for width, height in shapes:
        for axis, outward in (('e', '-n'), ('e', '+n'), ('n', '-e'), ('n', '+e')):
            for low in (True, False):
                z0 = 64 if low else 382
                wall = K.Wall(axis, (-58, 58), (0, 20), (0, 1000), outward)
                opening = K.Opening(-width/2, width/2, z0, z0+height, 'glass_arch')
                model = K.Model()
                W.frame(model, L, wall, opening, L.EAST)
                W.validate_model(model)
                tris = triangles(model)
                out = L.wall_out(wall)[2]
                def cast(r, z):
                    return ray(tris, W.local_point(wall, r, z, 20), -out)
                opaque = []
                for t in np.linspace(.02, np.pi-.02, 61):
                    opaque.append(((opening.radius-1)*np.cos(t), opening.spring+(opening.radius-1)*np.sin(t)))
                if low:
                    for z in np.linspace(z0+5, opening.spring-3, 11):
                        opaque += [(opening.r0+1, z), (opening.r1-1, z)]
                    opaque += [(r, z0+1) for r in np.linspace(opening.r0+4, opening.r1-4, 11)]
                    for r in (-width/6, width/6):
                        end = opening.spring + np.sqrt((opening.radius-2.6)**2-r*r)
                        opaque += [(r, z) for z in np.linspace(z0+3, end, 21)]
                        levels = list(np.arange(z0+22, opening.spring-4, 20)) + [opening.spring]
                        for z in levels:
                            # Rays across each junction include the ends of the
                            # horizontal shoulder and the bevelled corner zones.
                            opaque += [(r+dx, z+dz) for dx in (-.74, -.60, -.48, -.30, 0, .30, .48, .60, .74)
                                       for dz in (-.74, -.48, 0, .48, .74)]
                for r, z in opaque:
                    hit = cast(r, z)
                    assert hit is not None and 23.7 <= hit <= 26.2, (width, height, axis, outward, low, r, z, hit)
                checked['opaque_rays'] += len(opaque)
                for r in (-width/3, 0, width/3):
                    for z in (z0+12, z0+32, z0+52):
                        assert cast(r, z) is None, (width, height, r, z, 'pane blocked')
                        checked['clear_pane_rays'] += 1
                for r in (opening.r0-.2, opening.r1+.2):
                    for z in np.linspace(z0-1, opening.z1+1, 15):
                        assert cast(r, z) is None, (width, height, r, z, 'outside opening')
                        checked['exterior_rays'] += 1
                checked['orientations'] += 1
    return checked


manifest = json.loads((OUT / 'manifest.json').read_text())
assert manifest['generator_sha256'] == W.sha(Path(W.__file__))
assert all(W.sha(ROOT / p) == digest for p, digest in manifest['protected'].items())
assert all(W.sha(OUT / 'stage' / p) == hashes['after'] for p, hashes in manifest['changes'].items())
records = json.loads((OUT / 'layout.json').read_text())['models']
_, east = W.geometry(records['lowtide_east'], L)
_, backdrop = W.geometry(records['lowtide_backdrop'], L)
models = {'lowtide_east': east, 'lowtide_west': east.mirrored(L.WEST_PAINTS), 'lowtide_backdrop': backdrop}
reproduced = OUT / 'reproduction'
reproduced.mkdir(exist_ok=True)
for name, model in models.items():
    L.configure(model)
    K.write_obj(reproduced / f'{name}-new.obj', model, name)
    assert (reproduced / f'{name}-new.obj').read_bytes() == (OUT / f'{name}-new.obj').read_bytes(), name
report = dict(status='offline_checks_passed_native_review_pending',
              revision=W.REVISION, coverage=coverage(), canonical_reproductions=len(models),
              protected_files_unchanged=len(manifest['protected']),
              staged_meshes=len(manifest['changes']), delta_triangles=manifest['delta_triangles'],
              production_changed=False, native_compile=False, native_visual_review=False,
              gameplay_performance_measured=False,
              visual_review=['cpu-oblique-before.png / cpu-oblique-candidate.png',
                             'cpu-head-before.png / cpu-head-candidate.png',
                             'cpu-joint-before.png / cpu-joint-candidate.png'])
(OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
