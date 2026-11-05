"""Stage one substantial cast pedestal/rolled-steel table rebuild for native review."""
from pathlib import Path
from collections import Counter
import importlib.util,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_detail as D
import belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chair_geometry',ROOT/'Sources/Belltower/bistro-chair-v2/build.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
OUT=Path(tempfile.gettempdir())/'belltower-bistro-table-v2';STAGE=OUT/'stage'
RES='models/maps/belltower/bistro-table-v2';MODEL=STAGE/'Assets'/RES
CENTRE=(-600.,-170.);GREEN='iron_green';BLACK='iron_black'
Z=np.array((0.,0,1));X=np.array((1.,0,0))

def cast_leg(m,d,lod):
    """A continuous tapered, oval-section casting with a rounded toe."""
    p=C.curve([(1.1,0,8.0),(2.4,0,6.9),(4.4,0,3.35),(7.5,0,1.7),(10.8,0,1.25)],(16,10,5)[lod])
    side=np.cross(Z,d);rings=[];ns=[];n=(12,8,6)[lod]
    for i,c in enumerate(p):
        t=K.normalise(p[min(i+1,len(p)-1)]-p[max(i-1,0)])
        t=d*t[0]+Z*t[2];up=K.normalise(np.cross(t,side))
        amount=i/(len(p)-1);width=.7-.22*amount;thick=.82-.42*amount
        centre=d*c[0]+Z*c[2]
        ring=[];norm=[]
        for a in np.arange(n)*math.tau/n:
            ring.append(centre+side*math.cos(a)*width+up*math.sin(a)*thick)
            norm.append(K.normalise(side*math.cos(a)/width+up*math.sin(a)/thick))
        rings.append(ring);ns.append(norm)
    for i in range(len(p)-1):
        for k in range(n):
            q=(k+1)%n;ids=((i,k),(i,q),(i+1,q),(i+1,k))
            D.outward(m,BLACK,[rings[a][b] for a,b in ids],sum(ns[a][b] for a,b in ids),normals=[ns[a][b] for a,b in ids])
    D.outward(m,BLACK,rings[-1],d)
    # A separate broad leveling foot meets the cobbles, with no floating ends.
    D.lathe(m,d[:2]*10.8,0,[(.75,.08),(.92,.18),(.92,.38),(.75,.55),(.48,1.1)],BLACK,sides=n,caps=(True,True))

def build(lod):
    m=K.Model();n=(64,40,20)[lod];sides=(24,16,10)[lod]
    # One closed sheet shell, with an umbrella aperture and rolled outer seam.
    profile=[(13.5,28.4),(13.75,28.5),(13.8,28.8),(13.72,29.05),(13.5,29.2),(13.2,29.15),(13.,29.),(1.18,29.),(1.18,28.55),(13.2,28.55),(13.5,28.4)]
    D.lathe(m,(0,0),0,profile,GREEN,sides=n)
    # Dark rubber/iron grommet surrounds the unchanged parasol pole.
    D.lathe(m,(0,0),0,[(1.2,28.72),(1.45,28.83),(1.5,29.03),(1.4,29.12),(1.04,29.12),(1.04,28.72),(1.2,28.72)],BLACK,sides=sides)
    # Cast central column with shaped hub, upper bell and rolled collars.
    D.lathe(m,(0,0),0,[(1.7,3.4),(2.,4.1),(2.,5.3),(1.65,6.1),(1.35,7.5),(1.15,9.),(.98,21.8),(1.13,23.),(1.5,24.1),(1.8,24.5),(1.8,25.),(1.5,25.4)],BLACK,sides=sides,caps=(True,True))
    for h,r in ((7.5,1.4),(22.9,1.2)):
        D.lathe(m,(0,0),0,[(r,h-.25),(r+.18,h-.1),(r+.18,h+.15),(r,h+.3)],BLACK,sides=sides)
    for k in range(4):
        a=math.pi/4+k*math.pi/2;d=np.array((math.cos(a),math.sin(a),0))
        cast_leg(m,d,lod)
        # Curved pedestal arms support a real underside mounting ring.
        points=C.curve([(1.4,0,24.5),(3.,0,25.),(5.,0,27.3),(8.5,0,28.2)],(9,6,3)[lod])
        C.tube(m,[d*p[0]+Z*p[2] for p in points],.42,BLACK,sides=(10,8,6)[lod])
        if lod<2:
            q=d*8.5+Z*28.3
            F.turned(m,q,-Z,d,[(.40,0),(.40,.09),(.27,.16),(.27,.31)],BLACK,segments=6)
    D.lathe(m,(0,0),0,[(8.6,28.18),(8.6,28.52),(7.9,28.52),(7.9,28.18),(8.6,28.18)],BLACK,sides=(48,32,16)[lod])
    D.configure(m);m.material_overrides.update({GREEN:'materials/buildings/iron_green.vmat',BLACK:'materials/buildings/iron_black.vmat'})
    return m

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'table_lod{i}.obj',build(i),f'table_lod{i}') for i in range(3)]
    text=C.modeldoc().replace('bistro-chair-v2','bistro-table-v2').replace('chair_lod','table_lod')
    (MODEL/'bistro_table.vmdl').write_text(text)
    print(json.dumps({'lods':lods,'accepted_resource_staged':True,'review_wrappers_recreated':False}))

if __name__=='__main__':main()
