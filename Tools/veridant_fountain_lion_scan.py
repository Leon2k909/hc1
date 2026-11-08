"""Fit the CC BY Arkhangelskoye lion scan to Veridant's upper basin.

Usage: python Tools/veridant_fountain_lion_scan.py source.glb
Requires numpy, trimesh and fast-simplification.
"""
from pathlib import Path
import sys

import fast_simplification
import numpy as np
import trimesh

root = Path(__file__).resolve().parents[1]
folder = root / 'Assets/models/props/shared/veridant_fountain_lion_scan'
folder.mkdir(parents=True, exist_ok=True)

scan = trimesh.load_scene(sys.argv[1]).to_mesh()
scan.merge_vertices(merge_tex=True, merge_norm=True)
# The scan is Y-up, with the longitudinal axis angled in the XZ plane.
horizontal = scan.vertices[:, [0, 2]]
ahead = np.array([.24512238, .96949214])
across = np.array([-.96949214, .24512238])
depth = horizontal @ ahead
width = horizontal @ across
points = np.column_stack(((width + .015) * 24 - 4.4, (depth + .92) * 20.4,
                          57.8 + (scan.vertices[:, 1] - .285) * 29.4))
mesh = trimesh.Trimesh(points, scan.faces, process=False)
# Trim the capture's base and ground fringe. The installed bronze plinth seats the sculpture.
mesh = mesh.slice_plane([0, 0, 57.8], [0, 0, 1])
mesh.remove_unreferenced_vertices()
vertices, faces = fast_simplification.simplify(
    np.ascontiguousarray(mesh.vertices), np.ascontiguousarray(mesh.faces), target_count=38000)
mesh = trimesh.Trimesh(vertices, faces, process=True)
mesh = max(mesh.split(only_watertight=False), key=lambda part: len(part.faces))

with (folder / 'sculpture.obj').open('w', encoding='utf-8') as obj:
    obj.write('mtllib sculpture.mtl\no reclining_lions\nusemtl lion_bronze\n')
    for index, sign in enumerate((1, -1)):
        forward = np.array((.6, -.8, 0)) * sign
        side = np.array((-.8, -.6, 0)) * sign
        basis = np.column_stack((side, forward, (0, 0, 1)))
        for x, y, z in mesh.vertices @ basis.T:
            obj.write(f'v {y:.5f} {z:.5f} {x:.5f}\n')
        for x, y, z in mesh.vertices:
            obj.write(f'vt {(x + y * .31) / 32 + .5:.5f} {z / 32 + .25:.5f}\n')
        for x, y, z in mesh.vertex_normals @ basis.T:
            obj.write(f'vn {y:.5f} {z:.5f} {x:.5f}\n')
        for face in mesh.faces + index * len(mesh.vertices) + 1:
            obj.write('f ' + ' '.join(f'{i}/{i}/{i}' for i in face) + '\n')

(folder / 'sculpture.mtl').write_text('newmtl lion_bronze\nKd 0.4 0.28 0.16\n', encoding='utf-8')
template = root / 'Assets/models/props/shared/veridant_fountain_sculpture_v4/sculpture.vmdl'
model = template.read_text(encoding='utf-8-sig')
(folder / 'sculpture.vmdl').write_text(model.replace('veridant_fountain_sculpture_v4', folder.name), encoding='utf-8')
print(f'{len(mesh.faces):,} triangles per lion; local bounds {mesh.bounds.tolist()}')
