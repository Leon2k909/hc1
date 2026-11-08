"""Align the Operations garden spur to the glazed double door."""
from pathlib import Path
import numpy as np
from shapely import constrained_delaunay_triangles, orient_polygons
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

root = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant'
directory = root / 'operations-garden-approaches-v2'
directory.mkdir(exist_ok=True)
old_spur = box(-820, -20, -700, 40)
door_spur = box(-820, -140, -700, -60)
threshold = box(-700, -140, -684, -60)
stair_spur = box(-820, -600, -700, -520)
old_spur = old_spur.union(box(-820, -620, -700, -560))
door_spur = door_spur.union(stair_spur)
threshold = threshold.union(box(-700, -600, -684, -520))
ground_source = root / 'courtyard-drains-v1/ground_without_drains.obj'
border_source = root / 'gravel_relief_trial/garden_border_open_entrance.obj'
relative = 'models/maps/veridant/operations-garden-approaches-v2'


def read(path):
    lines = path.read_text().splitlines()
    vertices = [tuple(map(float, line.split()[1:4])) for line in lines if line.startswith('v ')]
    return lines, vertices


def triangles(polygon, clockwise=False):
    for face in orient_polygons(constrained_delaunay_triangles(polygon), exterior_cw=clockwise).geoms:
        yield list(face.exterior.coords)[:-1]


def emit(output, points, index, uv=None):
    corners = np.array([(y,z,x) for x,y,z in points])
    normal = np.cross(corners[1]-corners[0], corners[2]-corners[0])
    length = np.linalg.norm(normal)
    if length < 1e-8:
        return index
    normal /= length
    axes = [axis for axis in range(3) if axis != np.argmax(abs(normal))]
    if uv is None:
        uv = corners[:,axes]/32
    for corner, texcoord in zip(corners, uv):
        output.extend(['v '+' '.join(map(str,corner)), 'vt '+' '.join(map(str,texcoord)), 'vn '+' '.join(map(str,normal))])
    offsets = range(len(points))
    output.append('f '+' '.join('/'.join(str(base+i+1) for base in index) for i in offsets))
    return tuple(base+len(points) for base in index)


lines, vertices = read(ground_source)
uvs = [tuple(map(float, line.split()[1:3])) for line in lines if line.startswith('vt ')]
index = (len(vertices),len(uvs),sum(line.startswith('vn ') for line in lines))
ground, cuts = [], []
material = ''
removed = 0
for line in lines:
    if line.startswith('usemtl '):
        material = line.split()[1]
    if line.startswith('f ') and material == 'vr_gravel':
        refs = [tuple(int(i)-1 for i in token.split('/')) for token in line.split()[1:]]
        points = np.array([vertices[i] for i, _, _ in refs])
        polygon = Polygon(points[:,[2,0]])
        overlap = polygon.intersection(old_spur).area
        if overlap > 1e-6:
            removed += overlap
            transform = np.linalg.solve(np.column_stack((points[:,2],points[:,0],np.ones(3))),
                                        np.column_stack((points[:,1],[uvs[j] for _,j,_ in refs])))
            for face in triangles(polygon.difference(old_spur), not polygon.exterior.is_ccw):
                attributes = np.array([(x,y,1) for x,y in face]) @ transform
                cuts.append(([(x,y,z) for (x,y),(z,_,_) in zip(face,attributes)],attributes[:,1:]))
            continue
    ground.append(line)
if abs(removed-old_spur.area) > .01:
    raise RuntimeError(f'Unexpected gravel spur area: {removed}')
ground.append('usemtl vr_gravel')
for points, uv in cuts:
    index = emit(ground,points,index,uv)
for face in triangles(door_spur):
    texcoords = (np.array([(x,y,1) for x,y in face]) @ transform)[:,1:]
    index = emit(ground,[(x,y,.15) for x,y in face],index,texcoords)
ground.append('usemtl vr_floor')
for face in triangles(threshold):
    index = emit(ground,[(x,y,0) for x,y in face],index)

lines, vertices = read(border_source)
tops = []
for line in lines:
    if line.startswith('f '):
        points = [vertices[int(token.split('/')[0])-1] for token in line.split()[1:]]
        if all(abs(z-3.2)<1e-4 for _,z,_ in points):
            tops.append(Polygon([(x,y) for y,_,x in points]))
border = unary_union(tops).difference(box(-821.5,-22,-698,42))
border = border.union(box(-821.4,-22,-818.6,42)).difference(box(-822,-140,-818,-60))
border = border.difference(box(-821.5,-622,-698,-558))
border = border.union(box(-821.4,-622,-818.6,-558)).difference(box(-822,-600,-818,-520))
border = border.union(box(-821.4,-602.8,-700,-600)).union(box(-821.4,-520,-700,-517.2))
border = orient_polygons(border.union(box(-821.4,-142.8,-700,-140)).union(box(-821.4,-60,-700,-57.2)))
edges = ['mtllib edging.mtl','usemtl vr_stone_light']
index = (0,0,0)
for face in triangles(border):
    index = emit(edges,[(x,y,3.2) for x,y in face],index)
for polygon in getattr(border,'geoms',[border]):
    for ring in [polygon.exterior,*polygon.interiors]:
        for a,b in zip(ring.coords,list(ring.coords)[1:]):
            index = emit(edges,[(*a,-.1),(*b,-.1),(*b,3.2),(*a,3.2)],index)

for line in ground[:10]:
    if line.startswith('mtllib '):
        filename = line.split(maxsplit=1)[1]
        if (ground_source.parent/filename).exists():
            (directory/filename).write_bytes((ground_source.parent/filename).read_bytes())
(directory/'ground.obj').write_text('\n'.join(ground)+'\n')
(directory/'edging.obj').write_text('\n'.join(edges)+'\n')
(directory/'edging.mtl').write_text('newmtl vr_stone_light\nKd .7 .7 .7\n')
model = (root/'veridant_ground.vmdl').read_text().replace('models/maps/veridant/courtyard-drains-v1/ground_without_drains.obj',relative+'/ground.obj')
model = model.replace('remaps =\n\t\t\t\t\t\t[','remaps =\n\t\t\t\t\t\t[\n{ from = "vr_floor.vmat" to = "materials/veridant/vr_floor.vmat" },',1)
(directory/'ground.vmdl').write_text(model)
(directory/'edging.vmdl').write_text((root/'gravel_relief_trial/garden_border_open_entrance.vmdl').read_text().replace('models/maps/veridant/gravel_relief_trial/garden_border_open_entrance.obj',relative+'/edging.obj'))
assert border.intersection(door_spur).area < .01
print(f'Relocated {removed:.0f} square inches of gravel to the 80-inch door opening')
