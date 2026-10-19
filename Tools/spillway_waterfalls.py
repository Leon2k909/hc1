"""Spillway's visual torrents and the basin below them; stage before native import."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import numpy as np
import map_kit as K
import riverdale_parts as P

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output/spillway/waterfall-pass'
STAGE = OUT / 'stage/models/maps/spillway'
BASIN_END = 4600
CENTRES = (-4300, -3200, -2100, -1000)
Z_BREAKS = np.array((-350, 0, 400, 1000, 1750, 2400, 2900, 3300), float)
E_BREAKS = np.linspace(-7600, 7600, 23)


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def carve_basin(e, n, height):
    """Lower only the visual terrain inside the existing spillway tailrace."""
    weight = smooth(-6200, -5400, e) * (1-smooth(-400, 200, e))
    weight *= smooth(1900, 2300, n) * (1-smooth(4400, 4800, n))
    return np.minimum(height, height*(1-weight)-420*weight)


def face_n(e, z):
    # Match the saved dam's faceted surface, including expansion buttresses.
    # Using the analytic curve instead lets the coarser concrete cut through it.
    z_values = 3520 + 1150*np.clip((Z_BREAKS+350)/3650, 0, 1)**.72
    return float(np.interp(z, Z_BREAKS, z_values) + np.interp(e, E_BREAKS, .000010*E_BREAKS**2))


def point(centre, u, z, seed):
    progress = max(0.0, min(1.0, (3020-z)/3310))
    width = 355*(1+.30*progress**1.4)
    edge = (math.sin(z*.017+seed)*8 + math.sin(z*.043+seed*3)*3)*abs(u)**3
    e = centre + u*(width+edge)
    swell = math.sin(u*9+z*.013+seed)*7 + math.sin(u*19-z*.022+seed*2)*3
    n = face_n(e, z) - 105 - progress*18 - swell
    return np.array((e, n+400, (z+245)*.78-245))


def build():
    model = K.Model()
    rows = np.unique(np.r_[np.linspace(-290, 3020, 81), Z_BREAKS[(Z_BREAKS > -290) & (Z_BREAKS < 3020)]])
    columns = np.linspace(-1, 1, 9)
    for seed, centre in enumerate(CENTRES):
        for z0, z1 in zip(rows[:-1], rows[1:]):
            for u0, u1 in zip(columns[:-1], columns[1:]):
                coords = ((u0, z0), (u1, z0), (u1, z1), (u0, z1))
                points = [point(centre, u, z, seed) for u, z in coords]
                normals = []
                for u, z in coords:
                    du = point(centre, u+.001, z, seed)-point(centre, u-.001, z, seed)
                    dz = point(centre, u, z+1, seed)-point(centre, u, z-1, seed)
                    normal = P.unit(np.cross(du, dz))
                    if normal[1] > 0: normal = -normal
                    normals.append(normal)
                uv = [((u+1)*.5, (3020-z)/700) for u, z in coords]
                P.card(model, 'sw_fall', points, (0, -1, .2), uv=uv, normals=normals)
        foot = point(centre, 0, -245, seed)[1]
        P.quad(model, 'sw_foam', (centre, foot-380, -241), (1,0,0), (0,1,0), 1280, 1220,
               uv=[(0,0),(1,0),(1,1),(0,1)])
        # Small overlapping volumes of spray, with distinct silhouettes and depth.
        for offset, ahead, z, width, height, angle in ((0,80,230,1500,1600,0), (-230,145,160,1100,1230,-.22), (245,170,100,1150,1050,.19)):
            P.quad(model, 'sw_mist', (centre+offset, foot-ahead, z), (math.cos(angle),math.sin(angle),0), (0,0,1), width, height,
                   uv=[(0,0),(1,0),(1,1),(0,1)])
    for paint in model.polygons:
        model.tile_overrides[paint] = 128
    return model


def baseline(name):
    relative = Path('models/maps/spillway') / name
    saved = OUT / 'before-assets' / relative
    if not saved.exists():
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'Assets' / relative, saved)
    return saved


def carve_obj(source, target):
    lines = source.read_text().splitlines()
    vertex_lines = [i for i,l in enumerate(lines) if l.startswith('v ')]
    normal_lines = [i for i,l in enumerate(lines) if l.startswith('vn ')]
    vertices = np.array([list(map(float, lines[i].split()[1:4])) for i in vertex_lines])
    original = vertices.copy()
    vertices[:,1] = np.round(carve_basin(-vertices[:,0], vertices[:,2], vertices[:,1]), 3)
    changed = np.abs(vertices[:,1]-original[:,1]) > .0005
    vertices[~changed] = original[~changed]
    for i in np.flatnonzero(changed):
        lines[vertex_lines[i]] = 'v '+' '.join(f'{v:.3f}' for v in vertices[i])
    # Smooth the edited bank normals. UVs, faces, all other vertices and normals stay intact.
    faces = []
    for line in lines:
        if line.startswith('f '):
            corners = [p.split('/') for p in line.split()[1:]]
            faces.append((np.array([int(p[0])-1 for p in corners]), [int(p[2])-1 for p in corners]))
    affected = set()
    sums = {}
    for indices, normals in faces:
        if changed[indices].any():
            affected.update(tuple(vertices[i]) for i in indices)
    for indices, normals in faces:
        p = vertices[indices]
        normal = np.cross(p[1]-p[0], p[2]-p[0])
        for i in indices:
            key = tuple(vertices[i])
            if key in affected: sums[key] = sums.get(key, np.zeros(3))+normal
    revised = set()
    for indices, normals in faces:
        for i, ni in zip(indices, normals):
            key = tuple(vertices[i])
            if key in affected:
                normal = P.unit(sums[key])
                lines[normal_lines[ni]] = 'vn '+' '.join(f'{v:.3f}' for v in normal)
                revised.add(ni)
    target.write_text('\n'.join(lines)+'\n')
    assert np.array_equal(vertices[~changed], original[~changed])
    return {'lowered_vertices':int(changed.sum()), 'revised_normals':len(revised), 'other_vertex_positions_unchanged':True}


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    for name in ('spillway_falls.obj', 'spillway_falls.mtl', 'spillway_falls.vmdl', 'spillway_mountains.obj', 'spillway_mountains.vmdl', 'spillway_river.obj', 'spillway_river.vmdl'):
        baseline(name)
    triangles = K.write_obj(STAGE/'spillway_falls.obj', build(), 'spillway_falls')
    mountains = carve_obj(baseline('spillway_mountains.obj'), STAGE/'spillway_mountains.obj')
    # The old river stopped before the actual dam toes; extend only that back basin.
    lines = baseline('spillway_river.obj').read_text().splitlines()
    extended = 0
    for i,line in enumerate(lines):
        if not line.startswith('v '): continue
        x,y,z = map(float, line.split()[1:4])
        if abs(z-4000)<.01 and abs(y+245)<.01 and abs(x)>7000:
            lines[i] = f'v {x:.3f} {y:.3f} {BASIN_END:.3f}'
            extended += 1
    assert extended >= 2
    (STAGE/'spillway_river.obj').write_text('\n'.join(lines)+'\n')
    for name in ('spillway_falls.vmdl', 'spillway_mountains.vmdl', 'spillway_river.vmdl'):
        shutil.copy2(baseline(name), STAGE/name)
    protected = [ROOT/'Assets/scenes/maps/spillway/spillway.scene', *sorted((ROOT/'Assets/models/maps/spillway').glob('*hulls*.obj'))]
    result = {'waterfall_triangles':triangles, 'basin':mountains, 'extended_river_vertices':extended,
              'protected':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}}
    (OUT/'geometry.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    stage()
