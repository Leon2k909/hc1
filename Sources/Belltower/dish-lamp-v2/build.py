from pathlib import Path
from collections import Counter
import importlib.util,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_detail as D,belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('lantern',ROOT/'Sources/Belltower/wall-lantern-v2/build.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
OUT=Path(tempfile.gettempdir())/'belltower-dish-lamp-v2';STAGE=OUT/'stage';RES='models/maps/belltower/dish-lamp-v2';MODEL=STAGE/'Assets'/RES
e,n0,n1,z=B.CABLES[0];HOOK=(e,(n0+n1)/2,z-12)
MAPS={p:L.MAPS[p] for p in ('iron_black','lamp_reflector','lamp_bulb','door_brass')}

def shell(m,profile,paint,n,inside=False):
    # Smooth tangent normals follow the pressed profile; the inner liner is a separate shell.
    for i,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
        normals=[]
        for j in (i,i+1):
            ra,za=profile[max(0,j-1)];rb,zb=profile[min(len(profile)-1,j+1)]
            normals.append(K.normalise(np.array((zb-za,-(rb-ra)))))
        for k in range(n):
            a,b=k*math.tau/n,(k+1)*math.tau/n;da=np.array((math.cos(a),math.sin(a),0));db=np.array((math.cos(b),math.sin(b),0))
            points=[da*r0+(0,0,z0),db*r0+(0,0,z0),db*r1+(0,0,z1),da*r1+(0,0,z1)]
            ns=[da*normals[0][0]+(0,0,normals[0][1]),db*normals[0][0]+(0,0,normals[0][1]),db*normals[1][0]+(0,0,normals[1][1]),da*normals[1][0]+(0,0,normals[1][1])]
            D.outward(m,paint,points,sum(ns),normals=ns)

def build(lod):
    m=K.Model();n=(64,40,20)[lod];small=(24,16,10)[lod]
    # Traverse the outer shell upwards, then the underside downwards.
    outer=[(9.,-9.7),(9.08,-9.5),(8.95,-9.28),(8.6,-9.15),(8.15,-8.9),(7.4,-8.45),(6.5,-7.8),(5.6,-7.),(4.8,-6.25),(4.15,-5.65),(3.6,-5.22),(3.1,-5.),(2.3,-4.9),(1.2,-4.9)]
    if lod==2:outer=outer[::2]+[outer[-1]]
    shell(m,outer,'iron_black',n)
    inner=[(r-.12,z-.13) for r,z in reversed(outer)]
    shell(m,inner,'lamp_reflector',n)
    # Closed rolled enamel rim, not a single sharp polygon edge.
    D.lathe(m,(0,0),0,[(8.9,-9.86),(9.12,-9.8),(9.22,-9.6),(9.18,-9.4),(9.,-9.29)],'iron_black',sides=n)
    D.lathe(m,(0,0),0,[(.28,-4.9),(.36,-4.7),(.36,-.8),(.5,-.65),(.5,-.35),(.3,-.2)],'iron_black',sides=small,caps=(True,True))
    # Cable clamp, neck and compression collars.
    F.bevel_box(m,(0,0,-.1),(L.X,L.Y,L.Z),(1.4,1.,.65),'iron_black',bevel=.15)
    for h in (-1.,-4.6):
        D.lathe(m,(0,0),0,[(.4,h-.1),(.6,h),(.6,h+.18),(.4,h+.28)],'door_brass',sides=small)
    D.lathe(m,(0,0),0,[(.8,-7.15),(1.,-6.95),(1.05,-6.7),(.8,-6.4),(.8,-5.5),(1.2,-5.3),(1.2,-5.05)],'lamp_reflector',sides=small,caps=(True,True))
    D.lathe(m,(0,0),0,[(.65,-7.7),(.7,-7.5),(.7,-7.1),(.6,-6.95)],'door_brass',sides=small,caps=(True,True))
    D.lathe(m,(0,0),0,[(.3,-10.4),(.8,-10.2),(1.25,-9.8),(1.5,-9.2),(1.5,-8.7),(1.25,-8.2),(.8,-7.8),(.6,-7.6)],'lamp_bulb',sides=small,caps=(True,True))
    D.configure(m);m.material_overrides.update(MAPS);return m

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}') for i in range(3)]
    L.RES=RES;L.MAPS=MAPS
    (MODEL/'wall_lantern.vmdl').write_text(L.modeldoc())
    print(json.dumps({'accepted_staged':True,'lods':lods}))
if __name__=='__main__':main()
