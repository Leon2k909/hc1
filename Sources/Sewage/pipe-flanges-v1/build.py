"""Stage additive, render-only bolted joints for the three west-wall utility pipes."""
from pathlib import Path
import sys, json, math
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/sewage/pipe-flanges-v1'
STAGE = OUT / 'stage/Assets/models/maps/sewage/pipe-flanges-v1'
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K

model = K.Model()
model.material_overrides.update(
    flange='materials/sewage/crane-blocks-v1/steel.vmat',
    bolt='materials/sewage/crane-blocks-v1/steel.vmat',
    gasket='materials/sewage/crane-blocks-v1/dark.vmat',
)
model.tile_overrides.update(flange=48, bolt=24, gasket=48)

def ring(center, inner, outer, start, end, paint, sides=48, bevel=.45):
    center = np.asarray(center, float)
    # Ring axis is plan north (engine X); a closed bevelled annular profile.
    profile = [(inner,start),(outer-bevel,start),(outer,start+bevel),
               (outer,end-bevel),(outer-bevel,end),(inner,end)]
    for j, (r0,t0) in enumerate(profile):
        r1,t1 = profile[(j+1)%len(profile)]
        for i in range(sides):
            a,b = 2*math.pi*i/sides, 2*math.pi*(i+1)/sides
            def p(r,t,h): return center + (r*math.cos(h),t,r*math.sin(h))
            points = [p(r0,t0,a),p(r0,t0,b),p(r1,t1,b),p(r1,t1,a)]
            desired = np.array(((t1-t0)*math.cos((a+b)/2),r0-r1,(t1-t0)*math.sin((a+b)/2)))
            cross = np.cross(points[1]-points[0],points[2]-points[0])
            if np.dot(cross,desired)<0: points.reverse()
            model.polygon(paint, points)

def bolt(center, radius, start, end, paint, sides=6):
    # Almost-zero bore is hidden inside the flange; ring supplies closed visible ends.
    ring(center, .05, radius, start, end, paint, sides, min(.25,(end-start)/4))

placements = []
for z in (282,325,375):
    for north in np.linspace(-960+1940*.12,-960+1940*.88,10)[:2]:
        center=np.array((-942,north,z))
        ring(center,13.8,21.0,-6.1,-.85,'flange')
        ring(center,13.8,21.0,.85,6.1,'flange')
        ring(center,17.15,19.4,-.85,.85,'gasket',bevel=.15)
        for theta in np.linspace(0,2*math.pi,8,endpoint=False):
            q=center+np.array((17.4*math.cos(theta),0,17.4*math.sin(theta)))
            bolt(q,1.1,-8.6,8.6,'bolt',8)
            for sign in (-1,1):
                lo,hi=sorted((sign*6.12,sign*6.85))
                ring(q,.95,2.7,lo,hi,'bolt',sides=12,bevel=.1)
                lo,hi=sorted((sign*6.85,sign*9.0))
                bolt(q,2.2,lo,hi,'bolt')
        placements.append(K.to_world(center).tolist())

triangles=K.write_model(STAGE,'models/maps/sewage/pipe-flanges-v1','flanges',model)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'plan.json').write_text(json.dumps(dict(joints=len(placements),triangles=triangles,placements=placements),indent=2))
print(dict(joints=len(placements),triangles=triangles))
