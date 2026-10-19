"""Check new visible details in all wall orientations, including mirrored halves."""
import json
import platform
import sys
from pathlib import Path
platform._wmi=None
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import numpy as np
import map_kit as K
import belltower_architecture as A

checks=[]
def inspect(model,name):
    faces=0
    for paint,polygons in model.polygons.items():
        for points,normal in polygons:
            points=np.asarray(points)
            assert np.isfinite(points).all() and np.isfinite(normal).all(),name
            for i in range(1,len(points)-1):
                cross=np.cross(points[i]-points[0],points[i+1]-points[0])
                assert np.linalg.norm(cross)>1e-8,(name,'degenerate triangle')
                assert np.dot(cross,normal)>1e-8,(name,'inverted winding')
            faces+=1
    assert faces>0,name
    checks.append(dict(name=name,faces=faces))

for axis,outward in (('e','+n'),('e','-n'),('n','+e'),('n','-e')):
    wall=K.Wall(axis,(-100,100),(-6,6),(0,300),outward)
    opening=wall.add(0,42,150,222,'glass')
    model=K.Model()
    A.window_sill(model,wall,opening,'ashlar')
    for variant in range(3):
        A.window_surround(model,wall,opening,'ashlar',variant)
        A.cornice(model,wall,-100,100,260,'ashlar',variant)
    assert not model.boxes and not model.hulls
    inspect(model,'mouldings '+outward)
    inspect(model.mirrored(),'mirrored mouldings '+outward)
    d,sign=wall.outer()
    depth_axis=1 if axis=='e' else 0
    for left in (True,False):
        r0,r1=(-44,-23) if left else (23,44)
        for angle in (12,25,42):
            leaf=K.Model()
            A.shutter(leaf,wall,r0,r1,150,222,2.2,'shutter_green',
                      angle=-angle if left else angle,hinge=r1 if left else r0)
            vertices=np.array([v for faces in leaf.polygons.values() for ps,n in faces for v in ps])
            outward_depth=(vertices[:,depth_axis]-d)*sign
            assert outward_depth.min()>=2.2-1e-8,'Leaf entered its wall'
            assert outward_depth.max()<=18,'Leaf exceeds upper-floor clearance'
            assert vertices[:,2].min()>=150 and vertices[:,2].max()<=222
            assert not leaf.boxes and not leaf.hulls
            inspect(leaf,f'shutter {outward} {left=} {angle=}')

for lo,hi in (((-250,-12,28),(0,12,32)),((-12,-250,28),(12,0,32)),((-10,-10,0),(10,10,4))):
    model,baseline=K.Model(),K.Model()
    baseline.box(lo,hi,'ashlar_grey','stone')
    A.coping(model,lo,hi,'ashlar_grey','stone')
    assert len(model.boxes)==1 and not model.hulls
    for actual,expected in zip(model.boxes[0][:3],baseline.boxes[0][:3]):
        assert np.array_equal(actual,expected),'Coping collision changed'
    assert model.boxes[0][3]==baseline.boxes[0][3]
    vertices=np.array([v for faces in model.polygons.values() for ps,n in faces for v in ps])
    assert np.all(vertices>=np.array(lo)-1e-8) and np.all(vertices<=np.array(hi)+1e-8)
    inspect(model,f'coping {lo} {hi}')

result=dict(checks=len(checks),orientation_and_winding_checks=checks,
    upper_shutters_outside_walls=True,coping_visuals_inside_original_bounds=True,
    coping_collision_unchanged=True,new_mouldings_have_no_collision=True)
path=ROOT/'output/belltower/quality/facades-v1-geometry-checks.json'
path.write_text(json.dumps(result,indent=2)+'\n')
print(f'{len(checks)} geometry cases passed: winding, finite vertices, shutter clearances and coping collision/bounds.')
