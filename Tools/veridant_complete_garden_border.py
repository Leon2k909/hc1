"""Extend the existing limestone along exposed gravel boundaries."""
from pathlib import Path
import numpy as np
from shapely import constrained_delaunay_triangles, orient_polygons
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

folder = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant/gravel_relief_trial'

def surfaces(filename, material):
    vertices, polygons = [], []
    active = False
    for line in (folder / filename).read_text().splitlines():
        if line.startswith('v '):
            y, z, x = map(float, line.split()[1:4])
            vertices.append((x, y))
        elif line.startswith('usemtl '):
            active = line.split()[1] == material
        elif active and line.startswith('f '):
            polygon = Polygon([vertices[int(v.split('/')[0])-1] for v in line.split()[1:]])
            if polygon.is_valid and polygon.area > .001:
                polygons.append(polygon)
    return unary_union(polygons)

path = unary_union([surfaces('../veridant_ground.obj', 'vr_gravel'),
                    surfaces('gravel_edged_trimmed_closed.obj', 'vr_gravel')]).buffer(.06).buffer(-.06).simplify(.25)
existing = unary_union([surfaces('gravel_edged_trimmed_closed.obj', 'vr_stone_light'),
                        surfaces('garden_path_border_closed.obj', 'vr_stone_light')])
garden = box(-1351, -1901, -699, 721)
border = path.boundary.intersection(garden).difference(existing.buffer(.02))
pavilion = box(-1180.05, -320.05, -939.95, -119.95)
footprint = orient_polygons(border.buffer(1.4, cap_style='square', join_style='mitre').difference(existing).difference(pavilion))
name = 'garden_border_pavilion_clear'
out = [f'mtllib {name}.mtl', 'usemtl vr_stone_light']
vertex_count = 0

def emit(points):
    global vertex_count
    corners = np.array([(y, z, x) for x, y, z in points])
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    length = np.linalg.norm(normal)
    if length < 1e-8:
        return
    normal /= length
    axes = [axis for axis in range(3) if axis != np.argmax(abs(normal))]
    for corner in corners:
        out.extend(['v '+' '.join(map(str,corner)), 'vt '+' '.join(map(str,corner[axes]/32)), 'vn '+' '.join(map(str,normal))])
    out.append('f ' + ' '.join(f'{i}/{i}/{i}' for i in range(vertex_count+1, vertex_count+len(points)+1)))
    vertex_count += len(points)

for triangle in orient_polygons(constrained_delaunay_triangles(footprint)).geoms:
    emit([(x, y, 3.2) for x, y in list(triangle.exterior.coords)[:-1]])
for polygon in getattr(footprint, 'geoms', [footprint]):
    for ring in [polygon.exterior, *polygon.interiors]:
        for a, b in zip(ring.coords, list(ring.coords)[1:]):
            emit([(*a, -.1), (*b, -.1), (*b, 3.2), (*a, 3.2)])
(folder/f'{name}.obj').write_text('\n'.join(out))
(folder/f'{name}.mtl').write_text('newmtl vr_stone_light\nKd 0.7 0.7 0.7\n')
(folder/f'{name}.vmdl').write_text((folder/'garden_path_border_closed.vmdl').read_text().replace('garden_path_border_closed.obj',f'{name}.obj'))
print('Border vertices:', vertex_count)
