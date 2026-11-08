"""Cast bronze urn sized to the Veridant fountain's limestone capital."""
from pathlib import Path
import math
import numpy as np
import map_kit as K
import veridant_parts as P
from riverdale_parts import lathe

resource = 'models/props/shared/veridant_fountain_urn'
bronze = 'vr_urn_bronze'
model = K.Model()
model.material_overrides[bronze] = 'materials/veridant/fountain_reference_bronze.vmat'
model.tile_overrides[bronze] = 24
profile = [(0,0), (5.5,0), (5.7,.35), (5.7,.8), (5.2,1.15),
           (4.5,1.35), (4.5,1.7), (3.4,2.1), (2.9,2.8), (2.8,3.8),
           (3.1,4.5), (4.1,5.2), (5.1,6.2), (6,7.4), (6.65,8.8),
           (7,10.2), (7.05,11.4), (6.8,12.5), (6.25,13.5),
           (5.4,14.4), (4.65,15.2), (4.5,16.1), (4.7,16.8),
           (5.6,17.15), (5.9,17.55), (5.9,18), (5.6,18.3),
           (4.95,18.5), (4.55,19.1), (3.8,19.7), (2.9,20.2),
           (1.8,20.6), (1.15,21), (1.05,21.5), (1.5,21.9),
           (1.65,22.5), (1.5,23.1), (1.05,23.7), (.48,24.2), (0,24.4)]
lathe(model, (0,0), profile, bronze, sides=96)

# Tapered relief ribs follow the lower curve of the vessel.
for i in range(18):
    angle = i * math.tau / 18
    radial = P.v(math.cos(angle), math.sin(angle), 0)
    points = [radial*r + P.UP*z for r,z in profile[10:17]]
    P.tube(model, points, [.06,.18,.29,.33,.27,.16,.04], bronze, 10, cap=True)

def bezier(points, steps=24):
    a,b,c,d = map(np.array, points)
    return [(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
            for t in np.linspace(0,1,steps)]

for sign in (-1,1):
    path = bezier([(sign*5.5,0,15.5),(sign*13,0,19.6),
                   (sign*12.8,0,10.6),(sign*6.6,0,9.3)])
    P.tube(model, path, [.62+.16*math.sin(math.pi*i/(len(path)-1)) for i in range(len(path))],
           bronze, 14, cap=True)
    curl = bezier([(sign*6.7,0,9.3),(sign*9.1,0,10.0),
                   (sign*9.6,0,12.2),(sign*8.1,0,12.3)], 16)
    P.tube(model, curl, [.51-.36*i/(len(curl)-1) for i in range(len(curl))], bronze, 12, cap=True)

K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource, resource, 'urn', model)
