"""Refined utility leaf: real pressings and recessed pulls, generated paint albedo."""
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as P
import ares_pressure_formed as F

out=Path(__file__).parent/'stage-v2'
out.mkdir(exist_ok=True)
front=K.Model()
profile=F.rounded(-32.5,32.5,-49,49,.45,step=3)
panel=F.rounded(-26,20,-23,41,2.0,step=2)
pull=F.rounded(23,28,-6,8,1.1,step=.8)
F.slab(front,profile,0,-1.75,'paint',.22,holes=[panel,pull])
F.recess(front,panel,-1.75,.55,'paint',.22)
F.recess(front,pull,-1.75,1.2,'rubber',.32)
# Rounded stainless finger pull, genuinely below the surrounding face.
P.tube(front,[(25.5,-.8,-4),(25.5,-1.4,-3),(25.5,-1.4,5),(25.5,-.8,6)],.24,'ar_pd_steel',sides=12,bend_radius=.5)
F.box(front,(25.5,-.63,-4),(1.25,.25,1.25),'steel',.1)
F.box(front,(25.5,-.63,6),(1.25,.25,1.25),'steel',.1)
# A replaceable stainless lower guard, with actual countersunk fasteners.
F.slab(front,F.rounded(-28,28,-44,-31,.7,step=2),-1.76,-2.03,'steel',.10)
for x in (-25.5,25.5):
    for z in (-41.5,-33.5):F.bolt(front,x,z,-2.04,.22)

m=K.Model()
for side in (1,-1):
    for paint,rows in front.polygons.items():
        for index,(pts,normal) in enumerate(rows):
            flip=np.array((1,side,1))
            points=[p*flip for p in pts]
            normals=front.polygon_normals.get((paint,index))
            # Whole-leaf planar paint mapping avoids the previous repeating squares.
            uv=[((p[0]+32.5)/65,(p[2]+49)/98) for p in pts] if paint=='ar_pd_paint' else front.polygon_uvs.get((paint,index))
            P.card(m,paint,points,normal*flip,uv=uv,
                   normals=[n*flip for n in normals] if normals is not None else None)
m.material_overrides.update({
 'ar_pd_paint':'materials/ares/control-room-door-v2/enamel.vmat',
 'ar_pd_steel':'materials/ares/pressure-doors-v3/steel.vmat',
 'ar_pd_rubber':'materials/ares/ar_rubber.vmat',
 'ar_pd_dark':'materials/ares/ar_gunmetal.vmat',
})
for name in m.material_overrides:m.tile_overrides[name]=32
count=K.write_model(out,'models/maps/ares/control-room-door-v2','utility_leaf',m)
print(f'Staged refined leaf: {count} triangles; true panel and pull recesses; no old model')
