from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
prefix=(ROOT/'Sources/Belltower/market-cross-v2/geometry.py').read_text().split('def build(lod):')[0]
prefix=prefix[:prefix.index('HOOK=')]+"HOOK=(0.,-1225.,-48.)\nMAPS={F.WOOD:'materials/belltower/furniture_wood.vmat',F.DARK:'materials/belltower/furniture_wood_dark.vmat','iron_black':'materials/buildings/iron_black.vmat','canvas_plain':'materials/buildings/canvas_plain.vmat','endgrain':'materials/gunsmith_range/bench_oak_endgrain.vmat'}\n\n"
body='''def build(lod):
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
    D.configure(m);m.material_overrides.update(MAPS);return m

'''
(HERE/'geometry.py').write_text(prefix+body)
s=(ROOT/'Sources/Belltower/market-cross-v2/build.py').read_text()
a=s.index('old=K.Model()');b=s.index('remaining=Counter',a)
s=s[:a]+'''old=K.Model();e,n=B.GARDEN_WELL;z=B.GARDEN_Z
for se in (-1,1):old.box((e+se*38-4,n-4,z+34),(e+se*38+4,n+4,z+116),'planks_dark')
old.beam((e-44,n,z+106),(e+44,n,z+106),(6,6),'planks_dark')
B.axle(old,(e,n,z+96),(1,0,0),6,50,{'side':'planks','end':'planks_dark'})
'''+s[b:]
s=s.replace('market-cross-v2','well-frame-v2').replace('market_cross','well_frame')
s=s.replace("if not ref.endswith('_ashlar.obj'):continue","if not re.search(r'_(planks|planks_dark)\\.obj$',ref):continue")
s=s.replace("ROOT/'Assets/materials/belltower/ashlar.vmat'","*[ROOT/'Assets'/v for v in MAPS.values()]")
s=s.replace('new Vector3(1275,0,0)','new Vector3(-1225,0,-48)').replace('new Vector3(1360,-60,250)','new Vector3(-1130,-90,100)')
s=s.replace('position=(1390,-100,245),target=(1275,0,230),fov=36','position=(-1100,-130,70),target=(-1225,0,30),fov=48')
(HERE/'build.py').write_text(s)
