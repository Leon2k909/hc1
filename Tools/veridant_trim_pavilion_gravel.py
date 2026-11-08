"""Clip gravel triangles against the pavilion footprint, keeping their UVs."""
from pathlib import Path
import numpy as np
from shapely import constrained_delaunay_triangles, orient_polygons
from shapely.geometry import Polygon, box

root = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant'
source = 'courtyard-drains-v1/ground_without_drains.obj'
destination = root/'pavilion-junction'
name = 'ground_clear_of_pavilion'
pavilion = box(-1180, -320, -940, -120)
vertices, uv, output = [], [], []
new_vertices, new_uv, replacements = [], [], []
material = ''
removed_area = 0
for line in (root/source).read_text().splitlines():
    if line.startswith('v '):
        vertices.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith('vt '):
        uv.append(tuple(map(float, line.split()[1:3])))
    elif line.startswith('usemtl '):
        material = line.split()[1]
    elif line.startswith('f ') and material == 'vr_gravel':
        refs = [tuple(int(i)-1 for i in ref.split('/')) for ref in line.split()[1:]]
        points = np.array([vertices[i] for i, _, _ in refs])
        poly = Polygon(points[:, [2,0]])
        area = poly.intersection(pavilion).area
        if area > 1e-5:
            if len(refs) != 3:
                raise ValueError('Expected triangulated gravel')
            removed_area += area
            basis = np.column_stack((points[:,2], points[:,0], np.ones(3)))
            attributes = np.column_stack((points[:,1], [uv[j] for _, j, _ in refs]))
            affine = np.linalg.solve(basis, attributes)
            triangles = orient_polygons(constrained_delaunay_triangles(poly.difference(pavilion)), exterior_cw=not poly.exterior.is_ccw)
            for triangle in triangles.geoms:
                first = len(new_vertices)
                for x,y in list(triangle.exterior.coords)[:-1]:
                    z,u,v = np.array([x,y,1]) @ affine
                    new_vertices.append((y,z,x))
                    new_uv.append((u,v))
                replacements.append((first, refs[0][2]+1))
            continue
    output.append(line)

if removed_area < 100:
    raise RuntimeError(f'Expected gravel underneath the pavilion, removed {removed_area:.1f} square units')
output.extend('v '+' '.join(map(str,p)) for p in new_vertices)
output.extend('vt '+' '.join(map(str,p)) for p in new_uv)
output.append('usemtl vr_gravel')
for first, normal in replacements:
    output.append('f '+' '.join(f'{len(vertices)+i+1}/{len(uv)+i+1}/{normal}' for i in range(first,first+3)))
for line in output[:10]:
    if line.startswith('mtllib '):
        material_file = line.split(maxsplit=1)[1]
        old_mtl = (root/source).with_name(material_file)
        if old_mtl.exists():
            (destination/material_file).write_bytes(old_mtl.read_bytes())
(destination/f'{name}.obj').write_text('\n'.join(output)+'\n')
(destination/f'{name}.vmdl').write_text((root/'veridant_ground.vmdl').read_text().replace(source, f'pavilion-junction/{name}.obj'))
print(f'Clipped {removed_area:.1f} square units of gravel under the pavilion')
