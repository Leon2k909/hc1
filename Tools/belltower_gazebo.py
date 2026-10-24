"""A curved standing-seam copper roof for Belltower's two garden gazebos."""
import math
import numpy as np
import belltower_furniture as F

COPPER = 'gazebo_copper'
SEAM = 'gazebo_copper_seam'
RESOURCE = 'materials/belltower/gazebo-v1'


def materials():
    result = {}
    for paint, colour, tint, metal, rough in (
        (COPPER, 'copper', '[.24 .38 .30 1]', .08, 1.),
        (SEAM, 'copper_brown', '[.35 .42 .33 1]', .35, 1.),
    ):
        result[paint] = '\n'.join((
            '// Tools/belltower_gazebo.py; original source texture pixels.',
            '"Layer0"', '{', '    shader "shaders/complex.shader"',
            '    F_SPECULAR "1"', f'    g_flMetalness "{metal}"',
            f'    g_flRoughnessScaleFactor "{rough}"',
            f'    TextureColor "materials/buildings/{colour}_color.png"',
            '    TextureNormal "materials/default/default_normal.tga"',
            '    TextureRoughness "materials/buildings/copper_rough.png"',
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
            f'    g_vColorTint "{tint}"', '    g_flModelTintAmount "1"', '}', ''))
    return result


def build(model, centre=(-500, -1130), z=-48):
    """Retain the original radius/roof height and the six existing post positions.

    The patinated surface supplies colour; seams, drip edge, framing and roof
    curvature are actual geometry. No collision or scene instances are added.
    """
    model.material_overrides.update({p: f'{RESOURCE}/{p}.vmat' for p in (COPPER, SEAM)})
    model.tile_overrides.update({COPPER: 64., SEAM: 64.})
    centre = np.asarray((*centre, z), float)
    radius, rim, rise = 72., 96., 54.
    ring_steps = np.linspace(.025, 1., 13)
    up = np.array((0., 0., 1.))

    def radial(a):
        return np.array((math.cos(a), math.sin(a), 0.))

    def point(a0, a1, s, t):
        r = (1-s)*radial(a0) + s*radial(a1)
        return centre + r*(radius*t) + up*(rim + rise*(1-t)**1.25)

    def normal(a0, a1, s, t):
        ds = radius*t*(radial(a1)-radial(a0))
        dt = radius*((1-s)*radial(a0)+s*radial(a1)) - up*(1.25*rise*(1-t)**.25)
        n = np.cross(ds, dt)
        if n[2] < 0:
            n = -n
        return n/np.linalg.norm(n)

    for side in range(6):
        a0, a1 = side*math.tau/6, (side+1)*math.tau/6
        # Three tapered sheets per roof face. UVs sample within the old texture's
        # painted seam bays; geometry now supplies the standing seams.
        for panel in range(3):
            for t0, t1 in zip(ring_steps, ring_steps[1:]):
                for k in range(3):
                    s0, s1 = (panel+k/3)/3, (panel+(k+1)/3)/3
                    st = ((s0,t0),(s1,t0),(s1,t1),(s0,t1))
                    pts = [point(a0,a1,s,t) for s,t in st]
                    normals = [normal(a0,a1,s,t) for s,t in st]
                    uv = [(.055 + .14*(s*3-panel) + ((side+panel)%4)*.25,
                           t*1.42 + ((side*13+panel*7)%19)/19) for s,t in st]
                    F.face(model,COPPER,pts,up,uv,normals)
                    # A dark thin deck closes the underside and gives the eave
                    # an actual thickness rather than a double-sided plane.
                    F.face(model,F.DARK,[p-up*.65 for p in pts],-up,
                           [(s*1.125,t*1.42) for s,t in st],[-n for n in normals])
        # Rolled standing seams along hips and between adjacent copper sheets.
        for s in (0., 1/3, 2/3):
            sections=[]
            for t in ring_steps:
                n=normal(a0,a1,s,t)
                tangent=point(a0,a1,s,min(1,t+.001))-point(a0,a1,s,max(.024,t-.001))
                across=np.cross(n,tangent);across/=np.linalg.norm(across)
                p=point(a0,a1,s,t)
                sections.append([p+across*x+n*h for x,h in ((-.24,.04),(-.10,.65),(.10,.65),(.24,.04))])
            for first,last in zip(sections,sections[1:]):
                for k in range(3):
                    quad=[first[k],last[k],last[k+1],first[k+1]]
                    n=np.cross(quad[1]-quad[0],quad[2]-quad[0])
                    F.face(model,SEAM,quad,n)
        # Copper drip fascia and rounded lower lip along the hexagonal eave.
        p0,p1=point(a0,a1,0,1),point(a0,a1,1,1)
        out=radial((a0+a1)/2)
        F.face(model,SEAM,[p0,p1,p1-up*3.2,p0-up*3.2],out)
        F.face(model,SEAM,[p0-out*.28,p1-out*.28,p1-out*.28-up*3.2,p0-out*.28-up*3.2],-out)
        F.beam(model,p0-up*3.1,p1-up*3.1,(.48,.48),SEAM,.18,up=up)
        # The old cone floated over the posts. A fitted header ring and curved
        # rafters now transfer the roof to the original six iron columns.
        a=centre+radial(a0)*56+up*97.6
        b=centre+radial(a1)*56+up*97.6
        F.beam(model,a,b,(2.0,3.8),'iron_green',.16,up=up)
        for ta,tb in zip(ring_steps,ring_steps[1:]):
            model.beam(point(a0,a1,0,ta)-up*1.8,point(a0,a1,0,tb)-up*1.8,
                       (1.1,2.4),'iron_green',up=up)
        for direction in (a1,a0-math.tau/6):
            along=(radial(direction)-radial(a0))
            along=along/np.linalg.norm(along)
            foot=centre+radial(a0)*56+up*83
            top=centre+radial(a0)*56+along*12+up*96
            F.beam(model,foot,top,(.75,.75),'iron_green',.14,up=up)
    # Small spun cap and finial close the apex without a sharp mathematical point.
    cap_z=z+rim+rise
    F.turned(model,(*centre[:2],cap_z-5),up,(1,0,0),
             [(3.6,0.),(3.6,.8),(2.7,2.2),(1.2,4.5),(.7,5.2)],SEAM,18,True)
    F.beam(model,(*centre[:2],cap_z),(*centre[:2],cap_z+4.8),(.8,.8),SEAM,.25,up=(1,0,0))
    return model.triangle_count()
