"""Constructed town gates; visible detail only, with the original collision in belltower_map.

The fourteen oak boards use seam-free strips of the original Poly Haven scan.
Both faces have working hinge straps; the town face has hanging rings and a bolt.
"""
import math
import numpy as np
import belltower_furniture as F
from map_kit import normalise

IRON = "belltower_gate_iron"
IRON_PATH = "materials/belltower/gate/forged_iron.vmat"
FRONT, BACK = -2334.0, -2345.8
SPRING, RADIUS = 120.0, 74.4


def inset_polygon(points, distance):
    """Intersect inward-offset edges of a convex CCW cross section."""
    points = np.asarray(points, float)
    result = []
    for k, point in enumerate(points):
        a = normalise(point - points[k-1])
        b = normalise(points[(k+1) % len(points)] - point)
        na, nb = np.array((-a[1], a[0])), np.array((-b[1], b[0]))
        matrix = np.array((na, nb))
        result.append(point + np.linalg.solve(matrix, np.full(2, distance)))
    return result


def section(model, outline, back, front, paint, bevel=.16, seed=0, grain=True):
    """Closed, front-and-back bevelled extrusion in the gate's (n,z) plane."""
    outline = np.asarray(outline, float)
    area = sum(np.cross(outline[(k+1) % len(outline)]-p,
                        outline[(k+2) % len(outline)]-outline[(k+1) % len(outline)])
               for k, p in enumerate(outline))
    assert area > 0
    inner = inset_polygon(outline, bevel)
    r0, r1 = min(outline[:,0]), max(outline[:,0])
    u0, u1 = F.STRIPS[seed % len(F.STRIPS)]
    v0 = (seed * .61803398875) % 1

    def emit(points, normal):
        uv = [(u0+(p[1]-r0)/(r1-r0)*(u1-u0), p[2]/F.TILE+v0) for p in points] if grain else None
        F.face(model, paint, points, normal, uv)

    for depth, sign in ((front,1), (back,-1)):
        emit([(depth,*p) for p in inner], (sign,0,0))
        for k, a in enumerate(outline):
            j = (k+1) % len(outline)
            edge = outline[j]-a
            normal = normalise((sign, edge[1], -edge[0]))
            emit([(depth-sign*bevel,*a), (depth-sign*bevel,*outline[j]),
                  (depth,*inner[j]), (depth,*inner[k])], normal)
    for k, a in enumerate(outline):
        b = outline[(k+1) % len(outline)]
        emit([(back+bevel,*a), (back+bevel,*b),
              (front-bevel,*b), (front-bevel,*a)], (0,b[1]-a[1],a[0]-b[0]))


def ring(model, centre, radius=3.65, tube=.58):
    """A freely hanging round-section iron ring, with smooth geometric normals."""
    centre = np.asarray(centre, float)
    out, along, up = np.eye(3)
    for i in range(28):
        for j in range(8):
            points, normals = [], []
            for di,dj in ((0,0),(1,0),(1,1),(0,1)):
                a, b = (i+di)*math.tau/28, (j+dj)*math.tau/8
                radial = along*math.cos(a)+up*math.sin(a)
                normal = radial*math.cos(b)+out*math.sin(b)
                points.append(centre+radial*radius+normal*tube)
                normals.append(normal)
            F.face(model, IRON, points, sum(normals), normals=normals)


def curved_lining(model, start, end, seed):
    """One scarfed timber length; continuous grain and no false cross joints."""
    profile=((-2330,74.82),(-2330,79.48),(-2330.22,79.7),(-2345.78,79.7),
             (-2346,79.48),(-2346,74.82),(-2345.78,74.6),(-2330.22,74.6))
    u0,u1=F.STRIPS[seed%len(F.STRIPS)]
    def point(depth,radius,angle):
        return np.array((depth,radius*math.cos(angle),SPRING+radius*math.sin(angle)))
    for step in range(8):
        a,b=start+(end-start)*step/8,start+(end-start)*(step+1)/8
        for k,(d0,r0) in enumerate(profile):
            d1,r1=profile[(k+1)%len(profile)]
            n0=normalise((r1-r0,-(d1-d0)*math.cos(a),-(d1-d0)*math.sin(a)))
            n1=normalise((r1-r0,-(d1-d0)*math.cos(b),-(d1-d0)*math.sin(b)))
            points=[point(d0,r0,a),point(d0,r0,b),point(d1,r1,b),point(d1,r1,a)]
            uv=[(u0+(r-74.6)/5.1*(u1-u0),t*77/F.TILE+seed*.217)
                for r,t in ((r0,a),(r0,b),(r1,b),(r1,a))]
            F.face(model,F.DARK,points,n0+n1,uv,[n0,n1,n1,n0])
    for angle,sign in ((start,-1),(end,1)):
        F.face(model,F.DARK,[point(d,r,angle) for d,r in profile],
               (0,-math.sin(angle)*sign,math.cos(angle)*sign))


def build(model):
    first = model.triangle_count()
    model.material_overrides[IRON] = IRON_PATH
    model.tile_overrides[IRON] = 48.0
    # Slightly varied board widths, but no false joints from tiling the full scan.
    weights = np.array((1.03,.95,1.06,.98,.94,1.04,1.0))
    bounds = np.r_[.05, .05+np.cumsum(weights)/sum(weights)*(RADIUS-.05)]
    for side in (-1,1):
        for k,(a,b) in enumerate(zip(bounds,bounds[1:])):
            left, right = sorted((side*(a+.10), side*(b-.10)))
            # Samples follow the actual arch, including the shoulders.
            top = [(r,SPRING+math.sqrt(RADIUS**2-r*r)) for r in np.linspace(right,left,5)]
            bottom = 1.0 + ((k*13+side)%5)*.06
            outline = [(left,bottom),(right,bottom),*top]
            variation = ((k*17+side*3)%7-3)*.055
            section(model,outline,BACK,FRONT+variation,
                    F.DARK if k%4 else F.WOOD,.22,seed=k+side*19+80)

    # Rebated back boards and an overlapping meeting joint close the visible
    # cracks. The front seams retain depth without revealing the bright exterior.
    for side in (-1,1):
        left,right=sorted((side*.08,side*74.3))
        top=[(r,SPRING+math.sqrt(74.3**2-r*r)) for r in np.linspace(right,left,25)]
        section(model,[(left,.9),(right,.9),*top],BACK+.3,BACK+1.7,F.DARK,.04,seed=130+side)
    F.bevel_box(model,(FRONT-4.6,0,97.5),np.eye(3),(1.8,2.0,193.3),F.DARK,.12,136)

    # A real timber lining sits ahead of the leaves, with mortised jamb feet.
    for side in (-1,1):
        F.bevel_box(model,(-2338,side*77.1,60),np.eye(3),(16.0,5.2,120),F.DARK,.30,40+side)
        F.bevel_box(model,(-2338,side*77.1,5),np.eye(3),(17,5.6,9.5),IRON,.15)
    # Six scarfed lengths in the curved lining, instead of one unbroken ribbon.
    for length in range(6):
        start, end = length*math.pi/6+.0015, (length+1)*math.pi/6-.0015
        curved_lining(model,start,end,60+length)

    # Projecting stone jambs and individual wedge-shaped arch stones at the reveal.
    for side in (-1,1):
        for row in range(5):
            F.bevel_box(model,(-2300,side*85,12+row*24),np.eye(3),
                        (5.5,9.6,23.7),"ashlar",.25,120+row)
    for k in range(19):
        a,b=k*math.pi/19+.002,(k+1)*math.pi/19-.002
        outline=[(r*math.cos(t),SPRING+r*math.sin(t))
                 for r,t in ((80,a),(90,a),(90,b),(80,b))]
        section(model,outline,-2303.5,-2296.7 if k==9 else -2297.4,
                "ashlar",.18,k,grain=False)

    out = np.array((1.,0.,0.))
    # Each strap ends before the centre seam: the two leaves can actually open.
    for face_sign, depth in ((1,FRONT+.6),(-1,BACK-.6)):
        face_out = out*face_sign
        for side in (-1,1):
            for z in (34.,98.,132.):
                outline=[(4,z),(8,z-1.25),(67,z-2.6),(72,z-2.6),
                         (72,z+2.6),(67,z+2.6),(8,z+1.25)]
                if side < 0: outline=[(-r,h) for r,h in reversed(outline)]
                lo,hi=sorted((depth-face_sign*.5,depth+face_sign*.55))
                section(model,outline,lo,hi,IRON,.12,grain=False)
                # Rounded hinge barrel, knuckles and the projecting pintle head.
                F.turned(model,(depth,side*72,z-5.3),(0,0,1),(1,0,0),
                         [(1.25,0),(1.4,.4),(1.4,3.2),(1.18,3.35),(1.18,6.7),
                          (1.4,6.85),(1.4,10.2),(1.25,10.6)],IRON,12)
                F.turned(model,(depth,side*72,z+5.3),(0,0,1),(1,0,0),
                         [(1.6,0),(1.6,.4),(.95,1.05),(.25,1.25)],IRON,12)
                F.bevel_box(model,(depth,side*74.5,z),np.eye(3),(2.5,4.0,2.7),IRON,.16)
                for r in (13,31,49,66):
                    # Reuse the established bolt builder, then assign its iron
                    # faces to the gate material without touching shared assets.
                    bolt_part=type(model)()
                    F.bolt(bolt_part,(depth+face_sign*.56,side*r,z),face_out,.48)
                    for faces in bolt_part.polygons.values():
                        for points,normal in faces: model.polygon(IRON,points,normal)
            # Bottom weather shoe has its own edge and fasteners.
            F.bevel_box(model,(depth,side*38.5,7.3),np.eye(3),(1.1,67,7.0),IRON,.14)
            # Rear diagonal compression brace connects hinge foot to free stile.
            if face_sign < 0:
                F.beam(model,(BACK-1.8,side*66,40),(BACK-1.8,side*9,92),
                       (4.7,2.6),F.DARK,.22,154+side,up=(1,0,0))

    # Hanging ring pulls and raised escutcheons on the town side.
    for side in (-1,1):
        F.bevel_box(model,(FRONT+.8,side*10,80.5),np.eye(3),(.85,5.2,13),IRON,.16)
        F.turned(model,(FRONT+1.25,side*10,84.8),(1,0,0),(0,1,0),
                 [(1.25,0),(1.25,.35),(.65,.7),(.65,2.1)],IRON,16)
        ring(model,(FRONT+3.1,side*10,81.0))
    # Sliding bolt, two keeper brackets and a turned hand grip.
    F.turned(model,(FRONT+2.3,-13,111),(0,1,0),(1,0,0),
             [(.68,0),(.68,26)],IRON,12)
    for r in (-10,6):
        F.bevel_box(model,(FRONT+2.3,r,111),np.eye(3),(3.4,2.8,4.2),IRON,.16)
    F.turned(model,(FRONT+2.8,-5,111),(1,0,0),(0,1,0),
             [(.75,0),(.75,2.3),(1.1,2.5),(1.1,3.5),(.65,4)],IRON,12)
    return model.triangle_count()-first
