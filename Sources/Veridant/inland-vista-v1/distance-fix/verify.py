"""Audit the installed distant atlas, terrain topology and native render results."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PARENT = ROOT / 'output/veridant/inland-vista-v1'
RUN = PARENT / 'distance-fix'
STAGE = RUN / 'stage-v26'
sys.path.insert(0,str(ROOT / 'Tools'))
import veridant_inland_vista as vista
from veridant_vista_ground import coast_data,GROUND_RADIUS
from veridant_backdrop import PLAY_RECT

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((STAGE / 'manifest.json').read_text())
geometry_only = '--geometry-only' in sys.argv

def obj(path):
    vertices, uv, faces, paint = [], [], [], None
    for line in path.read_text(encoding='utf-8').splitlines():
        words = line.split()
        if not words: continue
        if words[0]=='v':
            x,z,n = map(float,words[1:]); vertices.append((-x,n,z))
        elif words[0]=='vt': uv.append(list(map(float,words[1:])))
        elif words[0]=='usemtl': paint=words[1]
        elif words[0]=='f':
            indices = [[int(i)-1 for i in word.split('/')] for word in words[1:]]
            faces.append((paint,[i[0] for i in indices],[i[1] for i in indices]))
    return np.array(vertices),np.array(uv),faces

vertices,uv,faces = obj(STAGE / 'inland-card.obj')
assert np.isfinite(vertices).all() and np.isfinite(uv).all()
scales,ground = {paint:[] for paint in vista.PAINTS},[]
counts = Counter()
for paint,ids,ids_uv in faces:
    counts[paint] += 1
    points = vertices[ids]
    if paint in scales:
        pixels = uv[ids_uv]*vista.IMAGE_META['size']
        for a,b in ((0,1),(1,2),(2,0)):
            scales[paint].append(float(np.linalg.norm(points[b]-points[a])/np.linalg.norm(pixels[b]-pixels[a])))
    elif paint=='vr_inland_scrub': ground.append(points)
ratios = {paint:max(values)/min(values) for paint,values in scales.items()}
assert max(ratios.values()) < 1.005,ratios
assert all(counts[paint]==96 for paint in vista.PAINTS)
assert counts['vr_inland_brush']==720
ground = np.array(ground)
normals = np.cross(ground[:,1]-ground[:,0],ground[:,2]-ground[:,0])
assert (np.abs(normals[:,2]) > .00001).all()
slope = np.linalg.norm(normals[:,:2],axis=1)/np.abs(normals[:,2])
# The coast has rocky grades; reject vertical folds while allowing those slopes.
assert slope.max()<math.tan(math.radians(55)), float(slope.max())

# Merge exporter precision, then reject any unsealed internal terrain edge.
xy = ground[:,:,:2].reshape(-1,2)
parent = np.arange(len(xy))
def find(i):
    while parent[i]!=i:
        parent[i]=parent[parent[i]]; i=parent[i]
    return i
for a,b in cKDTree(xy).query_pairs(.01): parent[find(a)]=find(b)
ids = np.array([find(i) for i in range(len(xy))]).reshape(-1,3)
edges = Counter(tuple(sorted((int(t[a]),int(t[b])))) for t in ids for a,b in ((0,1),(1,2),(2,0)))
assert max(edges.values())==2
coast = coast_data()
outer_normals = np.array([(math.cos(a),math.sin(a)) for a in (np.arange(144)+.5)*2*math.pi/144])
apothem = (GROUND_RADIUS+80)*math.cos(math.pi/144)
unmatched,boundaries = [],0
for (a,b),count in edges.items():
    if count==2: continue
    boundaries+=1
    points=xy[[a,b]]; middle=points.mean(axis=0)
    on_coast=abs(middle[0]-np.interp(middle[1],coast[:,1],coast[:,0]))<.04
    x0,x1,y0,y1=PLAY_RECT
    on_play=any(np.all(np.abs(points[:,0]-x)<.02) and np.all((points[:,1]>=y0-.02)&(points[:,1]<=y1+.02)) for x in (x0,x1))
    on_play|=any(np.all(np.abs(points[:,1]-y)<.02) and np.all((points[:,0]>=x0-.02)&(points[:,0]<=x1+.02)) for y in (y0,y1))
    on_outer=np.min(np.max(np.abs((points-vista.CENTRE)@outer_normals.T-apothem),axis=0))<.04
    if not (on_coast or on_play or on_outer): unmatched.append(points.tolist())
assert not unmatched,unmatched[:5]
report={'success':True,'per_sector_pixel_scale_ratio':ratios,'max_ground_slope':float(slope.max()),
        'ground_boundary_edges_checked':boundaries,'unmatched_ground_edges':0,'added_triangles_by_material':dict(counts),
        'atlas_size':vista.IMAGE_META['size'],'radius':vista.RADIUS,'ground_radius':GROUND_RADIUS,'mainland_arc':[vista.START,vista.END],
        'fps_benchmarked':False}
for index in range(3):
    start,end,scale,bottom=vista.panel_mapping(index)
    rect=vista.IMAGE_META['panels'][index]['uv_rect_px']
    assert bottom+(rect[3]-vista.IMAGE_META['panels'][index]['minimum_foot_row'])*scale <= 500.01
    for angle in np.linspace(start,end,49):
        position=vista.CENTRE+vista.RADIUS*np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle))])
        assert position[0]-np.interp(position[1],coast[:,1],coast[:,0])>=299.9
if geometry_only:
    print(json.dumps(report,indent=2)); raise SystemExit(0)

for relative in manifest['files']: assert sha(ROOT/relative)==sha(STAGE/relative),relative
assert sha(ROOT/'Assets/materials/veridant/vista/inland-v1.png')==sha(ROOT/vista.IMAGE_META['source'])

def native(folder,tool):
    raw=json.loads((RUN/folder/(tool+'.json')).read_text())
    assert not raw.get('isError'),folder
    return json.loads(next(b['text'] for b in raw['content'] if b['type']=='text'))

compiles={}
for name in ('vr_inland_vista','vr_inland_vista_b','vr_inland_vista_c','vr_inland_scrub','vr_inland_brush','model'):
    revision='v26' if name=='model' or name in vista.PAINTS else 'v24'
    compiles[name]=native('compile-'+name+'-'+revision,'asset_compile')
    assert compiles[name]['Success'],name
shaders=native('compile-horizon','run_csharp')
shaders+=native('compile-ground-v3','run_csharp')
assert len(shaders)==2 and all(s['Success'] for s in shaders)
capture=native('native-after-v26','run_csharp')
assert capture['SourceUnchanged'] and not capture['ErrorModels'] and len(capture['Written'])==13
for name in capture['Written']: assert (RUN/'after-v26'/(name+'.png')).stat().st_size>10000
imported=native('native-import-v26','run_csharp')
assert all(imported[k] for k in ('SourceUnchanged','PlayStateUnchanged','SceneFileUnchanged'))
totals,bay_counts={},{}
for name in ('veridant_backdrop','veridant_backdrop_props'):
    relative=f'Assets/models/maps/veridant/{name}.obj'
    original=(PARENT/'before-assets'/relative).read_bytes().splitlines()
    current=(ROOT/relative).read_bytes().splitlines()
    for prefix in (b'v ',b'vt ',b'vn '):
        before=[line for line in original if line.startswith(prefix)]
        after=[line for line in current if line.startswith(prefix)]
        assert after[:len(before)]==before
    def bay(lines):
        paint,result='',[]
        for line in lines:
            if line.startswith(b'usemtl '): paint=line.split()[1].decode()
            elif line.startswith(b'f ') and paint in vista.BAY: result.append((paint,line))
        return result
    assert bay(original)==bay(current)
    bay_counts[name]=len(bay(current))
    totals[name]=sum(line.startswith(b'f ') for line in current)
    assert totals[name]==manifest['geometry'][name]['after_triangles']
    assert '"Physics' not in (ROOT/relative).with_suffix('.vmdl').read_text()
assert totals['veridant_backdrop_props']==20
report.update({'total_backdrop_triangles':sum(totals.values()),'original_backdrop_triangles':164312,
    'reduction_percent':round(100*(1-sum(totals.values())/164312),2),'no_physics':True,'bay_cards_unchanged':bay_counts,
    'native_compiles':compiles,'native_shaders':shaders,'capture':capture,'source_scene_preserved':True,
    'published_sha256':{relative:sha(ROOT/relative) for relative in manifest['files']},
    'selected_source':vista.IMAGE_META['source'],'scrub_source':vista.BRUSH_META['source'],
    'prompt_set':'Sources/Veridant/inland-vista-v1/distance-fix/prompts.json'})
for destination in (RUN/'verification.json',PARENT/'verification.json',HERE.parent/'installed.json'):
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('success','total_backdrop_triangles','reduction_percent','unmatched_ground_edges')},indent=2))
