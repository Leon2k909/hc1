"""Check real prop bounds, collision and mesh winding before building town meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys

platform._wmi=None
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'Tools'))
import numpy as np
import belltower_map as B
import belltower_gardens as G
from map_kit import Model

old=runpy.run_path(str(ROOT/'output/belltower/quality/garden-v1-before/source/belltower_map.py'))
records=[]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
options=parser.parse_args()
surface_checks=[]


def check_cladding_planes(name, model, walls):
    """Find overlapping timber faces on the visible cladding/trim planes."""
    planes={}
    for paint in (G.F.WOOD,G.F.DARK):
        for points,normal in model.polygons.get(paint,[]):
            points=np.asarray(points)
            axis=int(np.argmax(np.abs(normal)))
            if axis==2 or abs(abs(normal[axis])-1)>1e-7:
                continue
            sign=int(np.sign(normal[axis]))
            distance=sign*(points[0,axis]-walls[axis][sign>0])
            if not -.4<=distance<=.01:
                continue
            key=(axis,int(np.sign(normal[axis])),round(float(points[0,axis]),5))
            axes=[a for a in range(3) if a!=axis]
            lo,hi=points[:,axes].min(axis=0),points[:,axes].max(axis=0)
            for other_paint,other_lo,other_hi in planes.get(key,[]):
                if paint==other_paint:
                    continue
                overlap=np.minimum(hi,other_hi)-np.maximum(lo,other_lo)
                assert not np.all(overlap>.05),(name,'coplanar cladding and trim',key,overlap)
            planes.setdefault(key,[]).append((paint,lo,hi))
    surface_checks.append(name)

def collision(model):
    return [(np.asarray(c).tolist(),np.asarray(a).tolist(),np.asarray(s).tolist(),m) for c,a,s,m in model.boxes]

def basin_intrusions(model):
    """Detect geometry in the usable central part of the open wheelbarrow basin.

    The tapered side walls bound this empty space; x is restricted to the flat
    centre, away from the rounded end corners. Inspect vertices and face centres
    so a long chassis tube crossing it is caught even when its endpoints are out.
    """
    intrusions=[]
    for paint,polygons in model.polygons.items():
        for points,_ in polygons:
            points=np.asarray(points)
            samples=np.vstack((points,points.mean(axis=0)))
            for x,y,z in samples:
                if abs(x)>=12 or not 13.42<z<25.68:
                    continue
                interior_half_width=8.2+4.7*(z-13.4)/12.3
                if abs(y)<interior_half_width-.03:
                    intrusions.append({'material':paint,'point':[float(x),float(y),float(z)]})
    return intrusions

def check(name,model,lo=None,hi=None):
    triangles=0
    for paint,polygons in model.polygons.items():
        for points,normal in polygons:
            points=np.asarray(points)
            assert np.isfinite(points).all() and np.isfinite(normal).all(), name
            for i in range(1,len(points)-1):
                cross=np.cross(points[i]-points[0],points[i+1]-points[0])
                assert np.linalg.norm(cross)>1e-7,(name,paint,'degenerate')
                assert np.dot(cross,normal)>0,(name,paint,'winding')
                triangles+=1
    actual_lo,actual_hi=model.bounds()
    if lo is not None:
        assert np.all(actual_lo>=np.asarray(lo)-1e-5),(name,'lower bounds',actual_lo,lo)
    if hi is not None:
        assert np.all(actual_hi<=np.asarray(hi)+1e-5),(name,'upper bounds',actual_hi,hi)
    records.append({'name':name,'triangles':triangles,'bounds':[actual_lo.tolist(),actual_hi.tolist()],
                    'collision_boxes':len(model.boxes),'collision_hulls':len(model.hulls)})

for name,args in [
    ('large-west',(-1840,-1720,-1440,-1340,-48,'+n',False)),
    ('large-east',(-420,-300,-1440,-1360,-48,'+n',False)),
    ('small-terrace',(-1440,-1380,-1090,-1030,-48,'+e',True)),
]:
    e0,e1,n0,n1,z,door,small=args
    previous,current=Model(),Model()
    before_rng,after_rng=np.random.default_rng(2024),np.random.default_rng(2024)
    old['shed'](previous,e0,e1,n0,n1,z,door,before_rng,small)
    B.shed(current,e0,e1,n0,n1,z,door,after_rng,small)
    assert collision(current)==collision(previous),name
    assert before_rng.bit_generator.state==after_rng.bit_generator.state,name
    lo,hi=previous.bounds()
    check(name,current,lo,hi)
    check_cladding_planes(name,current,((e0,e1),(n0,n1)))
    check(name+'-mirrored',current.mirrored(),(-hi[0],lo[1],lo[2]),(-lo[0],hi[1],hi[2]))

for e in (-1700,-1640):
    model=Model()
    G.compost_bin(model,e,e+50,-1080,-1030,-48)
    check('compost-'+str(e),model,(e,-1080,-48),(e+50,-1030,-12))
    assert not model.boxes and not model.hulls
model=Model()
G.woodpile(model,-1840,-1740,-1170,-1140,-48)
check('firewood',model,(-1840,-1170,-48),(-1740,-1140,-8))
assert not model.boxes and not model.hulls
model=Model()
G.wheelbarrow(model,B.Place((0,0,0)))
check('wheelbarrow',model,(-50,-15,0),(35,15,32))
check('wheelbarrow-mirrored',model.mirrored(),(-35,-15,0),(50,15,32))
assert not model.boxes and not model.hulls

basin_check=None
if options.revision=='garden-v3':
    archived=ROOT/'output/belltower/quality/garden-v3-before/source/belltower_gardens.py'
    assert hashlib.sha256(archived.read_bytes()).hexdigest()=='97ecf15e63aeabee3ce49d03b7abb3fabcc2821699701c7c89732380da2d802f'
    old_wheelbarrow=runpy.run_path(str(archived))['wheelbarrow']
    previous_wheelbarrow=Model()
    old_wheelbarrow(previous_wheelbarrow,B.Place((0,0,0)))
    old_intrusions=basin_intrusions(previous_wheelbarrow)
    new_intrusions=basin_intrusions(model)
    assert old_intrusions, 'Regression check must detect the accepted v2 chassis intrusion'
    assert not new_intrusions,new_intrusions[:3]
    basin_check={'v2_intruding_samples':len(old_intrusions),'v3_intruding_samples':0,
                 'example_v2':old_intrusions[0],'archived_v2_sha256':hashlib.sha256(archived.read_bytes()).hexdigest()}

# Garden generation must preserve the shared random sequence (tree placements,
# flower placements and the rest of the map depend on its exact state).
a,b=Model(),Model()
ra,rb=np.random.default_rng(2024),np.random.default_rng(2024)
old['gardens'](a,ra)
B.gardens(b,rb)
assert collision(a)==collision(b)
assert len(a.hulls)==len(b.hulls)
for (pa,sa),(pb,sb) in zip(a.hulls,b.hulls):
    assert sa==sb and np.array_equal(pa,pb)
assert ra.bit_generator.state==rb.bit_generator.state
assert a.props==b.props
result={'checks':len(records),'results':records,'garden_collision_preserved':True,
        'cladding_trim_separation':surface_checks,
        'wheelbarrow_basin_clearance':basin_check,
        'shared_random_sequence_preserved':True,'scene_props_preserved':True,
        'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('Tools/belltower_gardens.py'),Path('Tools/belltower_map.py')]}}
out=ROOT/'output/belltower/quality'/f'{options.revision}-geometry-checks.json'
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
