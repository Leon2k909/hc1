"""Give the garden pavilion a tiled hip roof and timber-framed entrances."""
from pathlib import Path
import numpy as np
import map_kit as K
import veridant_map as V
import veridant_parts as P

resource = 'models/maps/veridant/garden-shelter'
model = K.Model()
model.uv_source_name = 'veridant_dress'
eaves = [V.v(110,-1190,154), V.v(330,-1190,154),
         V.v(330,-930,154), V.v(110,-930,154)]
ridge = [V.v(220,-1090,195), V.v(220,-1030,195)]
roof = [([eaves[0], eaves[1], ridge[0]], (1,0,0)),
        ([eaves[1], eaves[2], ridge[1], ridge[0]], (0,1,0)),
        ([eaves[2], eaves[3], ridge[1]], (1,0,0)),
        ([eaves[3], eaves[0], ridge[0], ridge[1]], (0,1,0))]
for points, along in roof:
    normal = np.cross(points[1]-points[0], points[2]-points[0])
    normal /= np.linalg.norm(normal)
    if normal[2] < 0:
        normal = -normal
    tangent = np.array(along, dtype=float)
    slope = np.cross(normal, tangent)
    uv = [(np.dot(p-points[0], tangent)/42, np.dot(p-points[0], slope)/42) for p in points]
    V.card(model, 'vr_pavilion_tile', points, normal, uv=uv)
for a,b in [(ridge[0],ridge[1]), *((eaves[i], ridge[0 if i<2 else 1]) for i in range(4))]:
    P.tube(model, [a+V.v(0,0,1.4), b+V.v(0,0,1.4)], [2.2,2.2], 'vr_pavilion_tile', 10, cap=True)

V.box(model, 110,330,-1190,-930,148,154,'vr_timber_dark')
for n0,n1 in [(-1182,-1179),(-941,-938)]:
    for e0,e1 in [(168,175),(265,272)]:
        V.box(model,e0,e1,n0,n1,0,113,'vr_stone_light')
    V.box(model,166,274,n0,n1,110,119,'vr_timber_dark')
for e0,e1 in [(118,121),(319,322)]:
    for n in range(-1120,-998,12):
        V.box(model,e0,e1,n,n+2.5,28,119,'vr_timber')
    for z in (28,117):
        V.box(model,e0,e1,-1123,-995,z,z+3,'vr_timber_dark')

V.configure(model)
model.material_overrides['vr_pavilion_tile'] = 'materials/buildings/roof_tiles.vmat'
K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource,
              resource, 'shelter_details', model)
