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
HOOK=(0.,-1225.,-48.)
MAPS={F.WOOD:'materials/belltower/furniture_wood.vmat',F.DARK:'materials/belltower/furniture_wood_dark.vmat','iron_black':'materials/buildings/iron_black.vmat','canvas_plain':'materials/buildings/canvas_plain.vmat','endgrain':'materials/gunsmith_range/bench_oak_endgrain.vmat'}

def build(lod):
    m=K.Model();X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1));p=B.Place((0,0,0),0)
    for sign in (-1,1):
        x=sign*38
        F.bevel_box(m,(x,0,75),(X,Y,Z),(8,8,82),F.DARK,bevel=.3,seed=3)
        F.beam(m,(x,0,89),(sign*22,0,106),(3.8,3.8),F.DARK,bevel=.2,seed=4)
        # Bearing blocks and steel straps fitted around the posts.
        F.bevel_box(m,(x,0,96),(X,Y,Z),(9.2,9.2,7),F.WOOD,bevel=.3,seed=7)
        for z in (39,94,98):
            F.bevel_box(m,(x,-4.15,z),(X,Y,Z),(8.4,.35,1.4),'iron_black',bevel=.08)
        if lod<2:
            for z in (39,94,98,105):F.bolt(m,(x,-4.4,z),-Y,.32)
        F.turned(m,(x,0,96),X,Y,[(2.,-5),(2.7,-4.9),(2.7,-4.3),(2.,-4.1)],'iron_black',segments=(20,12,8)[lod])
    F.beam(m,(-44,0,106),(44,0,106),(6,6),F.DARK,bevel=.25,seed=6)
    D.rod(m,(-46,0,96),(46,0,96),1.4,'iron_black',sides=(20,12,8)[lod])
    F.turned(m,(0,0,96),X,Y,[(5.6,-25),(6.,-24.6),(6.,24.6),(5.6,25)],F.WOOD,segments=(48,32,16)[lod])
    for x,sign in ((-25.02,-1),(25.02,1)):
        n=(40,24,12)[lod];angles=np.arange(n)*math.tau/n
        D.outward(m,'endgrain',[(x,5.6*math.cos(a),96+5.6*math.sin(a)) for a in angles],X*sign,uv=[(.5+.45*math.cos(a),.5+.45*math.sin(a)) for a in angles])
        F.turned(m,(x,0,96),X,Y,[(6.1,-.28),(6.5,-.15),(6.5,.15),(6.1,.28)],'iron_black',segments=(32,20,12)[lod])
    # Rope lays across the windlass and descends freely inside the well opening.
    count=(216,144,72)[lod];points=[]
    for t in np.linspace(0,1,count):
        a=t*math.tau*9
        points.append((-15+t*30,6.25*math.cos(a),96+6.25*math.sin(a)))
    L.C.tube(m,points,.27,'canvas_plain',sides=(8,6,4)[lod])
    L.C.tube(m,[(15,6.25,96),(15,6.4,92),(15,6.5,65),(15.2,6.3,18)],.27,'canvas_plain',sides=(8,6,4)[lod])
    F.beam(m,(46,0,96),(46,0,82),(1.2,2.),'iron_black',bevel=.2)
    F.turned(m,(46,0,82),X,Y,[(1.,0),(1.35,.5),(1.35,7.5),(1.,8)],F.WOOD,segments=(20,12,8)[lod])
    D.configure(m);m.material_overrides.update(MAPS);m.tile_overrides['endgrain']=12.;return m

