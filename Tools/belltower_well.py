"""The garden well's worn masonry and quiet water, inside the existing cover.

Only visible geometry is authored here. The caller keeps the original ring's
collision, frame and roof. Existing photographed textures remain unchanged.
"""
import math
from pathlib import Path
import numpy as np

import belltower_furniture as F
from belltower_planters import PATCHES, TILE
from map_kit import normalise

RESOURCE = 'materials/belltower/well-v1'
STONE, DAMP, MORTAR, WATER, DEPTH = (
    'well_cut_stone', 'well_damp_stone', 'well_mortar', 'well_water', 'well_depth')


def material_definitions():
    root = Path(__file__).resolve().parents[1]
    source = (root/'Assets/materials/belltower/planters-v1/cut_stone.vmat').read_text()
    result = {}
    for paint,tint,normal,roughness in (
        (STONE,'[1.04 1.01 .93]',.42,.72), (DAMP,'[.40 .46 .39]',.42,.50),
        (MORTAR,'[.30 .29 .25]',.20,.96), (DEPTH,'[.035 .05 .04]',0.,.98)):
        text = source.replace('// Tools/belltower_stage_planters.py;', '// Tools/belltower_well.py;')
        text = text.replace('[1.12 1.09 1.01]',tint).replace('"0.42"',f'"{normal}"').replace('"0.72"',f'"{roughness}"')
        result[paint] = text
    result[WATER] = ('"Layer0"\n{\n    shader "shaders/belltower_well_water_v2.shader"\n'
        '    TextureNormalA "materials/belltower/fountain_water_normal.png"\n'
        '    TextureNormalB "materials/belltower/fountain_water_normal.png"\n'
        '    g_vWaterColor "[.003 .008 .006]"\n'
        '    g_flWaterOpacity "0.78"\n    g_flFlowSpeed "0.006"\n'
        '    g_flRippleStrength "0.24"\n    g_flWaterRoughness "0.035"\n}\n')
    return result


def build(model, centre=(0., -1225.), z=-48.):
    model.material_overrides.update({p: f'{RESOURCE}/{p}.vmat'
                                    for p in (STONE, DAMP, MORTAR, WATER, DEPTH)})
    model.tile_overrides.update({p: (72. if p == WATER else TILE)
                                 for p in (STONE, DAMP, MORTAR, WATER, DEPTH)})
    origin = np.array((*centre, z), float)
    up = np.array((0., 0., 1.))
    rng = np.random.default_rng(620104)

    def at(radius, angle, height):
        return origin + (radius * math.cos(angle), radius * math.sin(angle), height)

    # Recessed mortar closes every real joint, including the inner shaft.
    for i in range(64):
        a, b = i * math.tau / 64, (i + 1) * math.tau / 64
        for radius, sign in ((39.15, 1), (31.7, -1)):
            normal = np.array((math.cos((a+b)/2), math.sin((a+b)/2), 0.)) * sign
            F.face(model, MORTAR, [at(radius,a,0), at(radius,b,0),
                                 at(radius,b,27.9), at(radius,a,27.9)], normal)

    def stone(index, course, count, inner, outer, low, high, offset):
        width = math.tau / count
        mid = offset + (index + .5) * width
        a = offset + index * width + .085 / ((inner+outer)/2)
        b = offset + (index+1) * width - .085 / ((inner+outer)/2)
        bevel = rng.uniform(.25, .40) if course == 3 else rng.uniform(.16, .27)
        # An eight-sided radial profile gives the top, underside and both arrises
        # actual thickness and bevels. Four arc segments per stone soften the hole.
        profile = ((outer-bevel,low,bevel),(outer,low+bevel,0),
                   (outer,high-bevel,0),(outer-bevel,high,bevel),
                   (inner+bevel,high,bevel),(inner,high-bevel,0),
                   (inner,low+bevel,0),(inner+bevel,low,bevel))
        phase = rng.uniform(0, math.tau)
        chip_at = rng.uniform(.15,.85)
        chip = rng.uniform(.12,.40) if course == 3 else rng.uniform(.04,.16)
        def point(k, t):
            radius, height, end_bevel = profile[k]
            angle = a + (b-a)*t + (1-2*t)*end_bevel/((inner+outer)/2)
            if k in (2,3,4,5):
                wear = .035*(1+math.sin(t*5+phase)) + chip*math.exp(-((t-chip_at)/.12)**2)
                height -= wear * (1 if k in (3,4) else .45)
            return at(radius,angle,height)
        points = [point(k,t) for k in range(8) for t in np.linspace(0,1,5)]
        along = np.array((-math.sin(mid),math.cos(mid),0.))
        radial = np.array((math.cos(mid),math.sin(mid),0.))
        axes = np.array((along,radial,up))
        coordinates = np.array([(p-origin) @ axes.T for p in points])
        centre_uv = (coordinates.min(axis=0)+coordinates.max(axis=0))/2
        span = np.ptp(coordinates,axis=0)
        available = [r for r in PATCHES if (r[2]-r[0])*TILE > max(span[0],span[1])+.03
                     and (r[3]-r[1])*TILE > max(span[1],span[2])+.03]
        if not available:
            raise ValueError(('Stone exceeds seam-free scan patch', span))
        patch = available[int(rng.integers(len(available)))]
        uc, vc = (patch[0]+patch[2])/2, 1-(patch[1]+patch[3])/2
        def face(p, normal, paint=STONE, normals=None):
            local_normal = normal @ axes.T
            dominant = int(np.argmax(np.abs(local_normal)))
            u,v = (1,2) if dominant == 0 else ((0,2) if dominant == 1 else (0,1))
            uv = []
            for vertex in p:
                local = (vertex-origin) @ axes.T-centre_uv
                uv.append((uc+local[u]/TILE, vc+local[v]/TILE))
            assert all(patch[0] <= x <= patch[2] and 1-patch[3] <= y <= 1-patch[1] for x,y in uv)
            F.face(model,paint,p,normal,uv,normals)
        for k,(pa,pb) in enumerate(zip(profile,profile[1:]+profile[:1])):
            dr,dz = pb[0]-pa[0],pb[1]-pa[1]
            for ta,tb in zip(np.linspace(0,1,5)[:-1],np.linspace(0,1,5)[1:]):
                aa,bb = a+(b-a)*ta,a+(b-a)*tb
                na = normalise((math.cos(aa)*dz,math.sin(aa)*dz,-dr))
                nb = normalise((math.cos(bb)*dz,math.sin(bb)*dz,-dr))
                q = [point(k,ta),point(k,tb),point((k+1)%8,tb),point((k+1)%8,ta)]
                paint = DAMP if course == 0 and k in (4,5,6) else STONE
                face(q,normalise(na+nb),paint,[na,nb,nb,na])
        for t,sign in ((0.,-1),(1.,1)):
            angle = a+(b-a)*t
            face([point(k,t) for k in range(8)],
                 np.array((-math.sin(angle),math.cos(angle),0.))*sign)

    # Staggered courses, with the coping projecting past both wall faces.
    for course,(count,inner,outer,low,high,offset) in enumerate((
        (16,31.3,39.85,.12,9.25,0.),
        (16,31.3,39.95,9.43,18.60,math.pi/16),
        (16,31.3,39.85,18.78,28.00,0.),
        (12,29.6,42.,28.18,34.,math.pi/24))):
        for index in range(count):
            stone(index,course,count,inner,outer,low,high,offset)

    # The garden surface remains at z0: a dark bed hides it under quiet water.
    # Keeping both disks above that surface avoids exposing grass in the shaft.
    for paint,height in ((DEPTH,1.0),(WATER,4.0)):
        for index in range(64):
            a,b = index*math.tau/64,(index+1)*math.tau/64
            q = [origin+up*height,at(31.65,a,height),at(31.65,b,height)]
            F.face(model,paint,q,up,[(p[0]/72,p[1]/72) for p in q])
