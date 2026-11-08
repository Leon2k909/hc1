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
HOOK=(-459.,-405.,0.)
MAPS={'ashlar_grey':'materials/belltower/planters-v1/cut_stone.vmat'}

def build(lod):
    m=K.Model();L.BLACK='ashlar_grey'
    # Stone base, shallow entasis, neck and stepped cornice share rounded edges.
    L.square_profile(m,[(9.,0),(9.3,.5),(9.3,2.5),(8.9,3.2),(8.9,5.5),(8.4,6.5),(8.4,12),(8.1,52),(8.4,56),(8.8,57),(8.8,60),(9.5,61),(10.,63),(11.,64),(11.,66),(10.5,67),(8.8,68)],lod)
    # Turned stone finial replaces the lumpy low-resolution ball.
    first=len(m.polygons['ashlar_grey'])
    D.lathe(m,(0,0),0,[(4.8,68),(4.8,68.7),(3.6,69.5),(2.8,70.2),(4.8,71.2),(6.3,72.5),(7.,74.2),(6.8,76.2),(5.6,78.6),(3.8,80.5),(1.5,82),(.35,82.3)],'ashlar_grey',sides=(48,32,16)[lod],caps=(True,True))
    # Keep the carved finial inside one photographed stone, away from mortar.
    for i in range(first,len(m.polygons['ashlar_grey'])):
        points,_=m.polygons['ashlar_grey'][i]
        if np.ptp([p[2] for p in points])<1e-6:
            uv=[(.3035+p[0]*.019,.896+p[1]*.0105) for p in points]
        else:
            angles=np.array([math.atan2(p[1],p[0])%math.tau/math.tau for p in points])
            if np.ptp(angles)>.5:angles[angles<.5]+=1
            uv=[(.153+.301*a,.81+.17*(p[2]-68)/14.3) for a,p in zip(angles,points)]
        m.polygon_uvs[('ashlar_grey',i)]=uv
    # Recessed-looking bevelled panels on all four sides of the dressed shaft.
    for k in range(4):
        a=k*math.pi/2;normal=np.array((math.cos(a),math.sin(a),0));side=np.cross((0,0,1),normal)
        F.bevel_box(m,normal*8.42+(0,0,33),(side,normal,np.array((0,0,1))),(11.8,.22,33.),'ashlar_grey',bevel=.09)
    D.configure(m);m.material_overrides.update(MAPS);return m

