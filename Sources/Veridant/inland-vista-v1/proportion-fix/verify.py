"""Audit exported proportions, ground topology, native compiles and side views."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parent
PARENT = ROOT / 'output/veridant/inland-vista-v1'
RUN = PARENT / 'proportion-fix'
STAGE = RUN / 'stage-v17'
sys.path.insert(0, str(ROOT / 'Tools'))
import veridant_inland_vista as vista
from veridant_vista_ground import coast_data
from veridant_backdrop import PLAY_RECT

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((STAGE / 'manifest.json').read_text(encoding='utf-8'))
published = {}
geometry_only = '--geometry-only' in sys.argv
for relative in manifest['files']:
    if not geometry_only:
        assert sha(ROOT / relative) == sha(STAGE / relative), relative
    published[relative] = sha(ROOT / relative)
assert sha(ROOT / 'Assets/materials/veridant/vista/inland-v1.png') == sha(SOURCE / 'wide-v3.png')

def obj(path):
    vertices, coords, faces, paint = [], [], [], None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            x, z, n = map(float, line.split()[1:])
            vertices.append((-x, n, z))
        elif line.startswith('vt '):
            coords.append(list(map(float, line.split()[1:])))
        elif line.startswith('usemtl '):
            paint = line.split()[1]
        elif line.startswith('f '):
            indices = [[int(value)-1 for value in part.split('/')] for part in line.split()[1:]]
            faces.append((paint, [part[0] for part in indices], [part[1] for part in indices]))
    return np.array(vertices), np.array(coords), faces

vertices, uv, faces = obj(STAGE / 'inland-card.obj')
scales, base = [], []
for paint, ids, ids_uv in faces:
    points = vertices[ids]
    if paint == 'vr_inland_vista':
        pixels = uv[ids_uv] * np.array(vista.IMAGE_META['size'])
        for a, b in ((0,1), (1,2), (2,0)):
            scales.append(float(np.linalg.norm(points[b]-points[a]) / np.linalg.norm(pixels[b]-pixels[a])))
    elif paint == 'vr_lawn':
        base.append(points)
scales = np.array(scales)
aspect_ratio = float(scales.max() / scales.min())
assert aspect_ratio < 1.005, aspect_ratio
assert vista.BOTTOM + (vista.IMAGE_RECT[3]-vista.IMAGE_META['minimum_foot_row']) * vista.PIXEL_SCALE <= -500

base = np.array(base)
normals = np.cross(base[:,1]-base[:,0], base[:,2]-base[:,0])
assert np.all(np.abs(normals[:,2]) > .00001)
slopes = np.linalg.norm(normals[:,:2], axis=1) / np.abs(normals[:,2])
max_ground_uv_stretch = float(np.sqrt(1 + slopes.max() ** 2))
assert max_ground_uv_stretch < 1.1, max_ground_uv_stretch

# Merge quantization-level differences, then inspect every triangle boundary.
xy = base[:,:,:2].reshape(-1,2)
parent = np.arange(len(xy))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
for a, b in cKDTree(xy).query_pairs(.01):
    parent[find(a)] = find(b)
ids = np.array([find(i) for i in range(len(xy))]).reshape(-1,3)
edges = Counter(tuple(sorted((int(triangle[a]),int(triangle[b]))))
                for triangle in ids for a,b in ((0,1),(1,2),(2,0)))
assert all(count <= 2 for count in edges.values())
coast = coast_data()
coast_e = lambda n: np.interp(n, coast[:,1], coast[:,0])
outer_normals = np.array([(math.cos(a),math.sin(a)) for a in (np.arange(144)+.5)*2*math.pi/144])
apothem = (vista.RADIUS+80)*math.cos(math.pi/144)
unmatched = []
boundary_count = 0
for (a,b), count in edges.items():
    if count == 2:
        continue
    boundary_count += 1
    points = xy[[a,b]]
    middle = points.mean(axis=0)
    on_coast = abs(middle[0]-coast_e(middle[1])) < .03
    x0,x1,y0,y1 = PLAY_RECT
    on_play = any(np.all(np.abs(points[:,0]-x)<.02) and np.all((points[:,1]>=y0-.02)&(points[:,1]<=y1+.02)) for x in (x0,x1))
    on_play |= any(np.all(np.abs(points[:,1]-y)<.02) and np.all((points[:,0]>=x0-.02)&(points[:,0]<=x1+.02)) for y in (y0,y1))
    on_outer = np.min(np.max(np.abs((points-vista.CENTRE) @ outer_normals.T - apothem),axis=0)) < .03
    if not (on_coast or on_play or on_outer):
        unmatched.append(points.tolist())
assert not unmatched, unmatched[:8]
if geometry_only:
    print(json.dumps({'pixel_scale_ratio':aspect_ratio, 'max_ground_uv_stretch':max_ground_uv_stretch,
                      'boundary_edges_checked':boundary_count, 'unmatched_edges':len(unmatched)},indent=2))
    raise SystemExit(0)

def native(folder, tool):
    result = json.loads((PARENT / folder / (tool+'.json')).read_text(encoding='utf-8'))
    assert not result.get('isError'), folder
    return json.loads(next(block['text'] for block in result['content'] if block['type']=='text'))
compiles = {name:native(folder,'asset_compile') for name,folder in
            [('material','proportion-fix/compile-material-v14'),('land','proportion-fix/compile-land-v17'),('props','compile-props-v8')]}
assert all(result['Success'] for result in compiles.values())
capture = native('proportion-fix/native-after-v17','run_csharp')
assert capture['SourceUnchanged'] and not capture['ErrorModels'] and len(capture['Written']) == 12
for name in capture['Written']:
    assert (RUN/'after-v17'/(name+'.png')).stat().st_size > 10000
imported = native('proportion-fix/native-import-v17','run_csharp')
assert all(imported[k] for k in ('SourceUnchanged','PlayStateUnchanged','SceneFileUnchanged'))

bay_counts, totals = {}, {}
for name in ('veridant_backdrop','veridant_backdrop_props'):
    relative = f'Assets/models/maps/veridant/{name}.obj'
    original = (PARENT/'before-assets'/relative).read_bytes().splitlines()
    current = (ROOT/relative).read_bytes().splitlines()
    for prefix in (b'v ',b'vt ',b'vn '):
        before = [line for line in original if line.startswith(prefix)]
        after = [line for line in current if line.startswith(prefix)]
        assert after[:len(before)] == before
    def bay(lines):
        paint, result = '', []
        for line in lines:
            if line.startswith(b'usemtl '): paint = line.split()[1].decode()
            elif line.startswith(b'f ') and paint in vista.BAY: result.append((paint,line))
        return result
    assert bay(original) == bay(current)
    bay_counts[name] = len(bay(current))
    totals[name] = sum(line.startswith(b'f ') for line in current)
    assert totals[name] == manifest['geometry'][name]['after_triangles']
    assert '"Physics' not in (ROOT/relative).with_suffix('.vmdl').read_text()
assert totals['veridant_backdrop_props'] == 20

report = {'success':True,'old_horizontal_vertical_ratio':1.9323288147,
          'new_exported_pixel_scale_ratio':aspect_ratio,'max_ground_uv_stretch':max_ground_uv_stretch,
          'ground_boundary_edges_checked':boundary_count,'unmatched_ground_edges':0,
          'image_triangles':sum(paint=='vr_inland_vista' for paint,_,_ in faces),
          'new_ground_triangles':len(faces)-288,'total_backdrop_triangles':sum(totals.values()),
          'original_backdrop_triangles':164312,'reduction_percent':round(100*(1-sum(totals.values())/164312),2),
          'bay_cards_unchanged':bay_counts,'no_physics':True,'native_compiles':compiles,'capture':capture,
          'fps_benchmarked':False,'published_sha256':published,
          'selected_source':vista.IMAGE_META['source'],'prompt':'Sources/Veridant/inland-vista-v1/proportion-fix/generation.json'}
for destination in (RUN/'verification.json',PARENT/'verification.json',SOURCE.parent/'installed.json'):
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ('success','new_exported_pixel_scale_ratio','max_ground_uv_stretch',
                 'ground_boundary_edges_checked','unmatched_ground_edges','total_backdrop_triangles','reduction_percent')},indent=2))
