"""Offline sewn cargo-sack candidate, confined to existing cover bounds.

The canonical map writer and all live resources stay untouched. The current
generated jute images are reused with finer, continuous cloth UVs. Preview a
small sample first; --stage replaces only lt_jute faces in saved OBJ copies.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import zlib

import numpy as np

import map_kit as K
import lowtide_sacks as OLD

REVISION = 'sewn-filled-sacks-v1'
TILE = 5.25  # 13.3 cm field: the source contains roughly 45 woven yarns.
PAINT = 'lt_jute'
RINGS = np.array([-1, -.96, -.89, -.80, -.66, -.48, -.24, 0,
                   .24, .48, .66, .80, .89, .96, 1.])
SIDES = 40


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed_for(lo):
    return zlib.crc32(np.round(lo, 3).astype('<f8').tobytes())


def tube(model, points, radius, sides=4):
    """Small sewn hems/cords; geometric threads remain a separate closed shell."""
    points = np.asarray(points, float)
    along = np.diff(points, axis=0)
    along = np.vstack((along[0], along[:-1] + along[1:], along[-1]))
    along /= np.linalg.norm(along, axis=1, keepdims=True)
    # Each seam is nearly straight; transport this fixed reference continuously.
    reference = np.array((0., 0., 1.))
    a = np.cross(along, reference)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    b = np.cross(along, a)
    angles = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    normal = a[:, None, :] * np.cos(angles)[None, :, None] + b[:, None, :] * np.sin(angles)[None, :, None]
    vertices = points[:, None, :] + normal * radius
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    for row in range(len(points)-1):
        for j in range(sides):
            k = (j+1) % sides
            ids = ((row, j), (row, k), (row+1, k), (row+1, j))
            pts = [vertices[r, q] for r, q in ids]
            ns = [normal[r, q] for r, q in ids]
            uv = [(j/sides, distance[row]/TILE), ((j+1)/sides, distance[row]/TILE),
                  ((j+1)/sides, distance[row+1]/TILE), (j/sides, distance[row+1]/TILE)]
            # Use actual outward normals; local basis orientation is arbitrary.
            if np.dot(np.cross(pts[1]-pts[0], pts[2]-pts[0]), np.mean(ns, axis=0)) < 0:
                pts, ns, uv = pts[::-1], ns[::-1], uv[::-1]
            model.polygon(PAINT, pts, uv=uv, normals=ns)
    for row, direction in ((0, -along[0]), (-1, along[-1])):
        pts = list(vertices[row])
        if np.dot(np.cross(pts[1]-pts[0], pts[2]-pts[0]), direction) < 0: pts.reverse()
        model.polygon(PAINT, pts, direction,
                      uv=[(float(p@a[row])/TILE, float(p@b[row])/TILE) for p in pts])


def sack(model, lo, size, *, seed=None):
    """Filled cloth with pinched end closures, seam gathers and broad contact faces.

    Plan-local X is across the sack, Y along it. End closures share the body
    boundary; the side hem and sewn mouth are embedded into that surface.
    Every vertex, including hems, stays in the original axis-aligned cover box.
    """
    lo, size = np.asarray(lo, float), np.asarray(size, float)
    seed = seed_for(lo) if seed is None else seed
    phase = seed % 1021 / 1021 * 2 * math.pi
    width, length, height = min(size[:2]), max(size[:2]), size[2]
    theta = np.linspace(0, 2*math.pi, SIDES, endpoint=False)
    cosine, sine = np.cos(theta), np.sin(theta)
    across = np.sign(cosine) * abs(cosine)**.72
    vertical = np.sign(sine) * abs(sine)**.40
    vertices = []
    uvs = []
    shift = np.array(((seed & 255)/255, ((seed >> 8) & 255)/255))
    for t in RINGS:
        end = abs(t)
        # The flat-filled centre compresses onto neighbouring sacks. Only the
        # final fifth collapses into the folded, sewn mouth and bottom closure.
        fullness = .055 + .945 * (1 - end**8)**.53
        waist = .83 + .165 * (1 - end**3) + .018*np.sin(t*4.5+phase)*np.sin(math.pi*end)
        corner_gather = np.exp(-((end-.84)/.15)**2)
        radial = .09*np.sin(theta*3 + phase + t*2.7) * corner_gather * (1-end)
        x = across*width*.5*waist + radial*cosine + .22*np.sin(t*2.5+phase)*np.sin(math.pi*end)
        # End fabric draws back at the corners, so the mouth isn't a hard bar.
        y = np.full(SIDES, t*length*.5) - t*(abs(across)**6)*.50*(1-end)
        y += .11*np.sin(theta*2 + phase)*np.sin(math.pi*t)
        wrinkle = .43*np.sin(theta*5 + phase + t*3.2)*corner_gather*abs(sine)**.5*min((1-end)*6, 1)
        broad = .18*np.sin(t*4.1 + phase)*np.cos(theta*2)*np.sin(math.pi*end)
        z = height*.5 + vertical*height*.5*fullness + wrinkle + broad
        ring = np.column_stack((x, y, z))
        vertices.append(ring)
        edge = np.linalg.norm(np.roll(ring, -1, axis=0)-ring, axis=1)
        perimeter = np.r_[0., np.cumsum(edge)]
        uvs.append(np.column_stack((perimeter/TILE + shift[0], np.full(SIDES+1, (t+1)*length*.5/TILE + shift[1]))))
    vertices = np.asarray(vertices)
    # Explicitly fit the body with room for the sewn cord, preserving the exact
    # cover footprint and making touching stacks independent of deformation.
    lower, upper = vertices.min(axis=(0, 1)), vertices.max(axis=(0, 1))
    desired_lo = np.array((-width*.5+.12, -length*.5+.12, .02))
    desired_hi = np.array((width*.5-.12, length*.5-.12, height-.02))
    vertices = (vertices-lower)/(upper-lower)*(desired_hi-desired_lo) + desired_lo
    points = list(vertices.reshape(-1, 3))
    faces, coords = [], []
    for row in range(len(RINGS)-1):
        for j in range(SIDES):
            k = (j+1) % SIDES
            ids = (row*SIDES+j, (row+1)*SIDES+j, (row+1)*SIDES+k, row*SIDES+k)
            tex = (uvs[row][j], uvs[row+1][j], uvs[row+1][j+1], uvs[row][j+1])
            for ii in ((0, 1, 2), (0, 2, 3)):
                faces.append(tuple(ids[q] for q in ii))
                coords.append(tuple(tex[q] for q in ii))
    for row, reverse in ((0, False), (len(RINGS)-1, True)):
        centre = len(points)
        points.append(vertices[row].mean(axis=0))
        for j in range(SIDES):
            ids = (centre, row*SIDES+j, row*SIDES+(j+1) % SIDES)
            if reverse: ids = ids[::-1]
            faces.append(ids)
            coords.append([(points[k][0]/TILE+shift[0], points[k][2]/TILE+shift[1]) for k in ids])
    points = np.asarray(points)
    normals = np.zeros_like(points)
    for ids in faces:
        p = points[list(ids)]
        cross = np.cross(p[1]-p[0], p[2]-p[0])
        assert np.linalg.norm(cross) > 1e-8
        for index in ids: normals[index] += cross
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    local = K.Model()
    for ids, tex in zip(faces, coords):
        local.polygon(PAINT, [points[i] for i in ids], uv=tex, normals=[normals[i] for i in ids])
    # One side is a stitched longitudinal seam, the other is the fabric fold.
    tube(local, vertices[:, 0, :] + np.array((.025, 0, 0)), .055)
    # The closed mouth follows the actual curved end cap; cord is pressed into
    # the fabric. Its slight zigzag reads as stitching only in close views.
    end_ring = vertices[0]
    across_samples = np.linspace(-.76, .76, 43)*width*.5
    seam = []
    y0 = desired_lo[1]
    for index, x in enumerate(across_samples):
        y = y0 - .035
        z = end_ring[:, 2].mean() + (.027 if index % 2 else -.027)
        seam.append((x, y, z))
    tube(local, seam, .045, sides=3)
    # Rotate the long axis into the saved orientation, retaining handedness.
    if size[0] > size[1]:
        basis = np.array(((0., 1., 0.), (-1., 0., 0.), (0., 0., 1.)))
    else:
        basis = np.eye(3)
    origin = lo + np.array((size[0]*.5, size[1]*.5, 0.))
    for paint, polygons in local.polygons.items():
        for index, (pts, normal) in enumerate(polygons):
            world = [basis@p+origin for p in pts]
            assert np.all(np.asarray(world) >= lo-1e-6) and np.all(np.asarray(world) <= lo+size+1e-6)
            ns = local.polygon_normals.get((paint, index))
            model.polygon(paint, world, basis@normal, uv=local.polygon_uvs.get((paint, index)),
                          normals=[basis@n for n in ns] if ns is not None else None)
    model.tile_overrides[PAINT] = TILE
    return dict(body_triangles=len(faces), total_triangles=local.triangle_count(), seed=int(seed))


def saved_sacks(text):
    positions, faces = [], []
    material = None
    for line in text.splitlines():
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:])
            positions.append((-x, z, y))
        elif line.startswith('usemtl '): material = line[7:]
        elif line.startswith('f ') and material == PAINT: faces.append(line)
    assert faces and len(faces) % 120 == 0, 'Expected current 120-triangle sacks'
    rows = []
    for start in range(0, len(faces), 120):
        ids = {int(part.split('/')[0])-1 for face in faces[start:start+120] for part in face.split()[1:]}
        pts = np.asarray([positions[i] for i in ids])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        assert len(np.unique(pts, axis=0)) == 62
        assert np.allclose(sorted(hi-lo), (11, 21, 33), atol=.002), (lo, hi)
        rows.append(dict(lo=lo.tolist(), size=(hi-lo).tolist()))
    return rows


def replace(text, addition):
    counts = Counter()
    kept, removed, material = [], 0, None
    for line in text.splitlines():
        token = line.split(' ', 1)[0]
        if token in ('v', 'vt', 'vn'): counts[token] += 1
        if token == 'usemtl': material = line[7:]
        if token == 'f' and material == PAINT:
            removed += 1
        else: kept.append(line)
    appended = []
    for line in addition.splitlines():
        if line.startswith(('v ', 'vt ', 'vn ', 'usemtl ')): appended.append(line)
        elif line.startswith('f '):
            refs = ['/'.join(str(int(v)+counts[k]) for v, k in zip(p.split('/'), ('v', 'vt', 'vn'))) for p in line.split()[1:]]
            appended.append('f '+' '.join(refs))
    return '\n'.join(kept + [f'# {REVISION}'] + appended) + '\n', removed


def stage(out):
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve()), 'Offline outputs only'
    out.mkdir(parents=True, exist_ok=True)
    protected = {p.relative_to(K.ROOT).as_posix(): sha(p)
                 for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide')
                 for p in (K.ROOT/folder).rglob('*') if p.is_file() and not p.name.endswith('_c')}
    manifest = dict(revision=REVISION, production_changed=False, collision_changed=False,
                    materials_changed=False, new_material_slots=0, sources={}, protected=protected,
                    models={}, changes={}, layout={})
    for name in OLD.MODEL_NAMES:
        live = K.ASSETS/f'models/maps/lowtide/{name}.obj'
        data = live.read_bytes()
        text = data.decode()
        rows = saved_sacks(text)
        new = K.Model()
        counts = [sack(new, row['lo'], row['size'])['total_triangles'] for row in rows]
        component = out/f'{name}-sacks.obj'
        K.write_obj(component, new, name)
        revised, removed = replace(text, component.read_text())
        target = out/'stage/models/maps/lowtide'/live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(revised.encode())
        before = out/'before'/live.name
        before.parent.mkdir(exist_ok=True)
        if before.exists(): assert before.read_bytes() == data
        else: before.write_bytes(data)
        assert removed == len(rows)*120
        manifest['layout'][name] = rows
        manifest['models'][name] = dict(sacks=len(rows), old_triangles=removed,
                                       new_triangles=sum(counts), component_sha256=sha(component))
        manifest['changes'][live.relative_to(K.ASSETS).as_posix()] = dict(before=sha(live), after=sha(target))
        print(f'Staged {name}: {len(rows)} sacks', flush=True)
    manifest['delta_triangles'] = sum(m['new_triangles']-m['old_triangles'] for m in manifest['models'].values())
    paths = [Path(__file__), Path(K.__file__), Path(OLD.__file__), OLD.SOURCE, OLD.MATERIAL,
             *OLD.TEXTURES.glob('*.png')]
    manifest['sources'] = {p.relative_to(K.ROOT).as_posix(): sha(p) for p in paths}
    assert all(sha(K.ROOT/p) == h for p, h in protected.items())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(models=manifest['models'], delta_triangles=manifest['delta_triangles']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
