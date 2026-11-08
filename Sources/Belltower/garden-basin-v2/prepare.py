from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/gate-pier-v2/geometry.py').read_text().split('def build(lod):')[0]
s=s[:s.index('HOOK=')]+"HOOK=(-1100.,-1365.,-48.)\nMAPS={'planter_cut_stone':'materials/belltower/well-v1/well_cut_stone.vmat','basin_water':'materials/belltower/well-v1/well_water.vmat','basin_depth':'materials/belltower/well-v1/well_depth.vmat'}\nimport belltower_planters as Stone\n\n"
s+='''def build(lod):
    m=K.Model();rng=np.random.default_rng(512);sides=(16,16,12)[lod]
    for course,(low,high) in enumerate(((0,10),(10,20),(20,32))):
        for k in range(sides):
            mid=math.tau*(k+.5*(course%2))/sides;half=math.pi/sides-.003
            radial=np.array((math.cos(mid),math.sin(mid),0));along=np.array((-math.sin(mid),math.cos(mid),0))
            ro=32. if course==2 else 31.5;ri=22.1
            footprint=list(reversed([(-ro*math.sin(half),ro*math.cos(half)),(ro*math.sin(half),ro*math.cos(half)),(ri*math.sin(half),ri*math.cos(half)),(-ri*math.sin(half),ri*math.cos(half))]))
            Stone.chipped_stone(m,(0,0,(low+high)/2),(along,radial,(0,0,1)),footprint,high-low-.08,rng,coping=course==2)
    # Keep the existing water height, with the map's quiet well-water shader.
    m.cylinder((0,0),21.9,6.8,7.,{'top':'basin_water'},sides=(64,40,24)[lod])
    m.cylinder((0,0),22.,.5,.7,{'top':'basin_depth'},sides=(48,32,16)[lod])
    D.configure(m);m.material_overrides.update(MAPS)
    m.tile_overrides.update({p:64. for p in MAPS})
    return m

'''
(HERE/'geometry.py').write_text(s)
# Adapt the preserved review staging source from the previous pier candidate.
s=(ROOT/'Sources/Belltower/gate-pier-v2/build.py').read_text().replace('gate-pier-v2','garden-basin-v2').replace('gate_pier','garden_basin')
s=s.replace('old=K.Model();B.pier(old,(-459,-405),0,64)',"old=K.Model();B.ring(old,(-1100,-1365),22,32,-48,-16,10,{'outside':'rubble','inside':'rubble','top':'ashlar_grey'});old.cylinder((-1100,-1365),22,-42,-41,{'top':'water'},sides=10,turn=math.pi/10)")
s=s.replace("r'_(ashlar|ashlar_grey)\\.obj$'","r'_(rubble|ashlar_grey|water)\\.obj$'")
s=s.replace('new Vector3(-405,459,0)','new Vector3(-1365,1100,-48)').replace('new Vector3(-335,400,100)','new Vector3(-1270,990,80)')
s=s.replace('position=(-335,375,80),target=(-405,459,44),fov=48','position=(-1275,1000,35),target=(-1365,1100,-28),fov=40')
(HERE/'build.py').write_text(s)
