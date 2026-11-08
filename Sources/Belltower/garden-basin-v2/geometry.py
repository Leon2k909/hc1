from pathlib import Path
from collections import Counter
import importlib.util,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_detail as D,belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('lantern',ROOT/'Sources/Belltower/wall-lantern-v2/build.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2';STAGE=OUT/'stage';RES='models/maps/belltower/sack-pile-v2';MODEL=STAGE/'Assets'/RES
HOOK=(-1100.,-1365.,-48.)
MAPS={'planter_cut_stone':'materials/belltower/well-v1/well_cut_stone.vmat','basin_water':'materials/belltower/well-v1/well_water.vmat','basin_depth':'materials/belltower/well-v1/well_depth.vmat'}
import belltower_planters as Stone

def build(lod):
    m=K.Model();rng=np.random.default_rng(512);sides=(16,16,12)[lod]
    for course,(low,high) in enumerate(((0,10),(10,20),(20,32))):
        for k in range(sides):
            mid=math.tau*(k+.5*(course%2))/sides;half=math.pi/sides-.003
            radial=np.array((math.cos(mid),math.sin(mid),0));along=np.array((-math.sin(mid),math.cos(mid),0))
            ro=32. if course==2 else 31.5;ri=22.1
            footprint=list(reversed([(-ro*math.sin(half),ro*math.cos(half)),(ro*math.sin(half),ro*math.cos(half)),(ri*math.sin(half),ri*math.cos(half)),(-ri*math.sin(half),ri*math.cos(half))]))
            footprint=np.asarray(footprint);offset=footprint.mean(axis=0);footprint-=offset
            centre=along*offset[0]+radial*offset[1]+(0,0,(low+high)/2)
            Stone.chipped_stone(m,centre,(along,radial,(0,0,1)),footprint,high-low-.08,rng,coping=course==2)
    # Keep the existing water height, with the map's quiet well-water shader.
    m.cylinder((0,0),21.9,6.8,7.,{'top':'basin_water'},sides=(64,40,24)[lod])
    m.cylinder((0,0),22.,.5,.7,{'top':'basin_depth'},sides=(48,32,16)[lod])
    D.configure(m);m.material_overrides.update(MAPS)
    m.tile_overrides.update({p:64. for p in MAPS})
    return m

