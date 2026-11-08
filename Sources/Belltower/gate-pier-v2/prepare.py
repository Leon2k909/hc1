from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/well-frame-v2/geometry.py').read_text().split('def build(lod):')[0]
s=s[:s.index('HOOK=')]+"HOOK=(-459.,-405.,0.)\nMAPS={'ashlar_grey':'materials/belltower/planters-v1/cut_stone.vmat'}\n\n"
s+='''def build(lod):
    m=K.Model();L.BLACK='ashlar_grey'
    # Stone base, shallow entasis, neck and stepped cornice share rounded edges.
    L.square_profile(m,[(9.,0),(9.3,.5),(9.3,2.5),(8.9,3.2),(8.9,5.5),(8.4,6.5),(8.4,12),(8.1,52),(8.4,56),(8.8,57),(8.8,60),(9.5,61),(10.,63),(11.,64),(11.,66),(10.5,67),(8.8,68)],lod)
    # Turned stone finial replaces the lumpy low-resolution ball.
    D.lathe(m,(0,0),0,[(4.8,68),(4.8,68.7),(3.6,69.5),(2.8,70.2),(4.8,71.2),(6.3,72.5),(7.,74.2),(6.8,76.2),(5.6,78.6),(3.8,80.5),(1.5,82),(.35,82.3)],'ashlar_grey',sides=(48,32,16)[lod],caps=(True,True))
    # Recessed-looking bevelled panels on all four sides of the dressed shaft.
    for k in range(4):
        a=k*math.pi/2;normal=np.array((math.cos(a),math.sin(a),0));side=np.cross((0,0,1),normal)
        F.bevel_box(m,normal*8.42+(0,0,33),(side,normal,np.array((0,0,1))),(11.8,.22,33.),'ashlar_grey',bevel=.09)
    D.configure(m);m.material_overrides.update(MAPS);return m

'''
(HERE/'geometry.py').write_text(s)
s=(ROOT/'Sources/Belltower/well-frame-v2/build.py').read_text();a=s.index('old=K.Model()');b=s.index('remaining=Counter',a)
s=s[:a]+"old=K.Model();B.pier(old,(-459,-405),0,64)\n"+s[b:]
s=s.replace('well-frame-v2','gate-pier-v2').replace('well_frame','gate_pier').replace('belltower_centre.vmdl','belltower_west.vmdl')
s=s.replace("r'_(planks|planks_dark)\\.obj$'","r'_(ashlar|ashlar_grey)\\.obj$'")
s=s.replace('new Vector3(-1225,0,-48)','new Vector3(-405,459,0)').replace('new Vector3(-1130,-90,100)','new Vector3(-335,400,100)')
s=s.replace('position=(-1100,-130,70),target=(-1225,0,30),fov=48','position=(-335,375,80),target=(-405,459,44),fov=48')
# The base capture already selects west, so its previous centre substitution must be removed.
s=s.replace("text=text.replace('belltower_west.vmdl','belltower_west.vmdl')", "text=text.replace('belltower_west.vmdl','belltower_west.vmdl')")
(HERE/'build.py').write_text(s)
