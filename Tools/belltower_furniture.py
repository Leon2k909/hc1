"""Visible joinery for Belltower. All gameplay collision stays in belltower_map.

Individual boards select seam-free strips of the unchanged one-metre Poly Haven
brown_planks_03 scan. UVs follow the timber, including curved wheel felloes.
"""
import itertools
import math
import numpy as np

WOOD = "furniture_wood"
DARK = "furniture_wood_dark"
IRON = "iron_black"
TILE = 1000 / 25.4
# Original scan's nine boards, inset from the photographed joints.
STRIPS = ((.012, .108), (.132, .226), (.248, .335), (.36, .442),
          (.471, .552), (.58, .647), (.676, .753), (.786, .873), (.903, .981))


def face(model, paint, points, normal, uv=None, normals=None):
    points = [np.asarray(p, float) for p in points]
    if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), normal) < 0:
        points.reverse()
        if uv is not None:
            uv = list(reversed(uv))
        if normals is not None:
            normals = list(reversed(normals))
    model.polygon(paint, points, uv=uv, normals=normals)


def seed_at(p, extra=0):
    return (int(round(np.dot(p.o, (17, 23, 31)))) + extra * 101) & 0xffffffff


def bevel_box(model, centre, axes, size, paint=WOOD, bevel=.12, seed=0):
    """Closed chamfered timber/metal block: six flats, twelve edges, eight corners."""
    centre, axes, size = np.asarray(centre, float), np.asarray(axes, float), np.asarray(size, float)
    half = size / 2
    bevel = min(bevel, min(half) * .45)
    inner = half - bevel
    grain = int(np.argmax(size))
    u0, u1 = STRIPS[seed % len(STRIPS)]
    v0 = ((seed * .61803398875) % 1)

    def emit(points, normal):
        # A separate projection for each face keeps grain parallel to the board.
        dominant = int(np.argmax(np.abs(normal)))
        cross = max((k for k in range(3) if k != grain and k != dominant),
                    key=lambda k: size[k], default=(grain+1) % 3)
        along = grain if dominant != grain else max((k for k in range(3) if k != grain), key=lambda k: size[k])
        if along == cross:
            cross = next(k for k in range(3) if k not in (along, dominant))
        uv = [(u0 + (q[cross]/size[cross]+.5)*(u1-u0), q[along]/TILE+v0) for q in points] if paint in (WOOD, DARK) else None
        face(model, paint, [centre + q @ axes for q in points], normal @ axes, uv)

    for axis in range(3):
        b, c = (axis+1) % 3, (axis+2) % 3
        for sign in (-1, 1):
            normal = np.zeros(3); normal[axis] = sign
            points = []
            for sb, sc in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                q = np.zeros(3); q[axis] = sign*half[axis]; q[b] = sb*inner[b]; q[c] = sc*inner[c]
                points.append(q)
            emit(points, normal)
    for a, b in itertools.combinations(range(3), 2):
        c = 3-a-b
        for sa, sb in itertools.product((-1, 1), repeat=2):
            points = []
            for main, end in ((a, -1), (a, 1), (b, 1), (b, -1)):
                q = np.zeros(3); q[a] = sa*(half[a] if main == a else inner[a]); q[b] = sb*(half[b] if main == b else inner[b]); q[c] = end*inner[c]
                points.append(q)
            normal = np.zeros(3); normal[a] = sa; normal[b] = sb
            emit(points, normal)
    for signs in itertools.product((-1, 1), repeat=3):
        signs = np.asarray(signs)
        points = []
        for a in range(3):
            q = signs*inner; q[a] = signs[a]*half[a]; points.append(q)
        emit(points, signs)


def box(model, p, lo, hi, paint=WOOD, bevel=.12, seed=0):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    bevel_box(model, p.at((lo+hi)/2), (p.x, p.y, p.z), hi-lo, paint, bevel, seed_at(p, seed))


def beam(model, a, b, size, paint=WOOD, bevel=.15, seed=0, up=(0, 0, 1)):
    a, b, up = np.asarray(a, float), np.asarray(b, float), np.asarray(up, float)
    axis = b-a; length = np.linalg.norm(axis); axis /= length
    if abs(np.dot(axis, up)) > .98:
        up = np.array((0, 1., 0))
    side = np.cross(up, axis); side /= np.linalg.norm(side)
    normal = np.cross(axis, side)
    bevel_box(model, (a+b)/2, (axis, side, normal), (length, *size), paint, bevel, seed)


def turned(model, centre, axis, u, profile, paint, segments=20, caps=True, seed=0):
    """Lathed hardware about an arbitrary axis; profile is (radius, axial offset)."""
    centre, axis, u = np.asarray(centre, float), np.asarray(axis, float), np.asarray(u, float)
    v = np.cross(axis, u)
    rim = [u*math.cos(k*math.tau/segments)+v*math.sin(k*math.tau/segments) for k in range(segments)]
    u0, u1 = STRIPS[seed % len(STRIPS)]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        slope = np.array((z1-z0, -(r1-r0))); slope /= np.linalg.norm(slope)
        for k in range(segments):
            d0, d1 = rim[k], rim[(k+1) % segments]
            n0, n1 = d0*slope[0]+axis*slope[1], d1*slope[0]+axis*slope[1]
            points = [centre+d0*r0+axis*z0, centre+d1*r0+axis*z0,
                      centre+d1*r1+axis*z1, centre+d0*r1+axis*z1]
            uv = [(u0+(u1-u0)*k/segments, z0/TILE), (u0+(u1-u0)*(k+1)/segments, z0/TILE),
                  (u0+(u1-u0)*(k+1)/segments, z1/TILE), (u0+(u1-u0)*k/segments, z1/TILE)] if paint in (WOOD, DARK) else None
            face(model, paint, points, n0+n1, uv, [n0, n1, n1, n0])
    if caps:
        for (radius, offset), sign in ((profile[0], -1), (profile[-1], 1)):
            face(model, paint, [centre+d*radius+axis*offset for d in rim], sign*axis)


def bolt(model, point, normal, radius=.30, washer=True):
    normal = np.asarray(normal, float); normal /= np.linalg.norm(normal)
    u = np.cross(normal, (0, 0, 1) if abs(normal[2]) < .9 else (0, 1, 0)); u /= np.linalg.norm(u)
    if washer:
        turned(model, point, normal, u, [(radius*1.55, 0), (radius*1.55, .08)], IRON, segments=12)
    turned(model, point, normal, u, [(radius, .07), (radius, .25), (radius*.78, .31)], IRON, segments=6)


def wheel(model, p, side):
    centre = p.at((-6, side*38, 24))
    # Six jointed felloes, with wood grain following the arc instead of radiating.
    count, subdivisions = 6, 8
    for segment in range(count):
        u0, u1 = STRIPS[(segment+seed_at(p)) % len(STRIPS)]
        start, end = segment*math.tau/count+.003, (segment+1)*math.tau/count-.003
        def at(angle, radius, offset):
            return centre+(p.x*math.cos(angle)+p.z*math.sin(angle))*radius+p.y*offset
        for k in range(subdivisions):
            a, b = start+(end-start)*k/subdivisions, start+(end-start)*(k+1)/subdivisions
            mid = (a+b)/2
            radial = p.x*math.cos(mid)+p.z*math.sin(mid)
            for offset in (-2.45, 2.45):
                points = [at(a,19.8,offset), at(b,19.8,offset), at(b,23.5,offset), at(a,23.5,offset)]
                uv = [(u0,a*21.7/TILE), (u0,b*21.7/TILE), (u1,b*21.7/TILE), (u1,a*21.7/TILE)]
                face(model, WOOD, points, p.y*offset, uv)
            face(model, DARK, [at(a,19.8,-2.45), at(b,19.8,-2.45), at(b,19.8,2.45), at(a,19.8,2.45)], -radial,
                 [(u0,a*21.7/TILE),(u0,b*21.7/TILE),(u1,b*21.7/TILE),(u1,a*21.7/TILE)])
        for angle, direction in ((start,-1), (end,1)):
            tangent = (-p.x*math.sin(angle)+p.z*math.cos(angle))*direction
            face(model, DARK, [at(angle,19.8,-2.45), at(angle,23.5,-2.45), at(angle,23.5,2.45), at(angle,19.8,2.45)], tangent)
    # Rounded tyre edges, restrained iron bands, hub collars and the axle nut.
    turned(model, centre, p.y, p.x, [(23.45,-2.6),(23.72,-2.85),(24,-2.55),(24,2.55),(23.72,2.85),(23.45,2.6)], IRON, 48, False)
    for k in range(12):
        angle = (k+.5)*math.tau/12
        radial = p.x*math.cos(angle)+p.z*math.sin(angle)
        beam(model, centre+radial*3.4, centre+radial*20.4, (1.65,2.2), WOOD, .20, seed_at(p,k+40), up=p.y)
    turned(model, centre, p.y, p.x, [(3.25,-5),(4.2,-3.1),(4.2,3.1),(3.25,5)], DARK, 24, True, seed_at(p))
    for offset in (-4.0, 4.0):
        turned(model, centre+p.y*offset, p.y, p.x, [(3.72,-.45),(3.85,-.25),(3.85,.25),(3.72,.45)], IRON, 24)
    bolt(model, centre+p.y*(side*5.1), p.y*side, .9)


def cart(model, p):
    # Cross bearers, two longitudinal rails and a bed of separate boards.
    for y in (-23, 23):
        box(model,p,(-60,y-2,25),(60,y+2,29),DARK,.2,10+y)
    for x in (-48,-6,44):
        box(model,p,(x-2.2,-32,26.3),(x+2.2,32,29.5),DARK,.15,20+x)
    for k in range(10):
        x0 = -60+k*12
        box(model,p,(x0+.12,-32,29.5),(x0+11.88,32,32),WOOD,.16,k)
    for side in (-1,1):
        for row in range(3):
            za, zb = 32.3+row*5.2, 37.15+row*5.2
            y = side*31.1
            box(model,p,(-60,y-.9,za),(60,y+.9,zb),WOOD,.14,30+row+side)
            x = side*59.1
            box(model,p,(x-.9,-30.1,za),(x+.9,30.1,zb),WOOD,.14,35+row+side)
        # Outside battens and iron corner straps. Rivets actually project.
        for x in (-56,-29,27,56):
            y = side*33.0
            box(model,p,(x-1.65,y-.8,28.5),(x+1.65,y+.8,48),DARK,.13,60+x)
            for zz in (33.8,44.8):
                bolt(model,p.at((x,y+side*.83,zz)),p.y*side)
        for x in (-59.55,59.55):
            box(model,p,(x-.35,side*32-.85,30),(x+.35,side*32+.85,48),IRON,.06)
        wheel(model,p,side)
        a, b = p.at((48,side*22,27)), p.at((140,side*22,4))
        beam(model,a,b,(3.5,3.5),DARK,.32,seed_at(p,80+side))
        # Collars at the shaft joint and rounded grip rather than a sharp end.
        for xx in (54,68):
            zz = 27-(xx-48)*23/92
            box(model,p,(xx-1.5,side*22-1.95,zz-1.95),(xx+1.5,side*22+1.95,zz+1.95),IRON,.1)
        bolt(model,p.at((54,side*24.05,25.5)),p.y*side,.45)
    beam(model,p.at((-6,-38,24)),p.at((-6,38,24)),(2.4,2.4),IRON,.1)


def bench_arm(model, p, x, grip_seed):
    """One swept iron arm and its wooden grip, independent of the leg frame."""
    profile = [(-6.5,17),(-7.5,22),(-5.8,25.2),(-2.5,26.2),(5.5,26.2),(9.8,29.2)]
    for a,b in zip(profile,profile[1:]):
        beam(model,p.at((x,*a)),p.at((x,*b)),(1.1,1.1),IRON,.2)
    box(model,p,(x-1.1,-4.5,25.8),(x+1.1,5.5,27.1),DARK,.3,grip_seed)


def bench_back_support(model, p, x):
    """Raked rear strap with a seat-clearing offset at its welded foot."""
    rake = math.radians(8)

    def rear_y(z):
        # Back board half-depth + strap half-depth + a 1 mm contact clearance.
        return 7.4+(z-18)*math.tan(rake)+(0.7+0.7+0.04)/math.cos(rake)

    start = (rear_y(19.0), 19.0)
    # The lower bracket stays behind the last seat board, then meets the strap.
    profile = [(9.62,15.4), (9.62,18.2), start, (rear_y(32.8),32.8)]
    centres = [p.at((x,*q)) for q in profile]
    directions = [b-a for a,b in zip(centres,centres[1:])]
    directions = [q/np.linalg.norm(q) for q in directions]
    normals = [np.cross(q,p.x) for q in directions]
    offsets = [normals[0]]
    for a,b in zip(normals,normals[1:]):
        offsets.append((a+b)/(1+np.dot(a,b)))
    offsets.append(normals[-1])
    # A single closed casting, with mitred bends and two eased exposed edges.
    # Six corners keep this three-segment support at the old upright's 44 tris.
    section = ((-.65,-.7),(.65,-.7),(.65,.54),(.49,.7),(-.49,.7),(-.65,.54))
    rings = [[c+p.x*u+normal*v for u,v in section] for c,normal in zip(centres,offsets)]
    for j,(a,b) in enumerate(zip(rings,rings[1:])):
        for k in range(len(section)):
            n = (k+1)%len(section)
            edge = a[n]-a[k]
            face(model,IRON,[a[k],a[n],b[n],b[k]],np.cross(edge,directions[j]))
    face(model,IRON,rings[0],-directions[0])
    face(model,IRON,rings[-1],directions[-1])


def bench(model, p, length):
    half = length/2
    # Five eased seat boards with daylight between them; three raked back slats.
    for k in range(5):
        y = -9+k*3.6
        box(model,p,(-half,y+.18,16.2),(half,y+3.42,18),WOOD,.20,k+100)
    rake = math.radians(8)
    axes = (p.x, p.y*math.cos(rake)-p.z*math.sin(rake), p.y*math.sin(rake)+p.z*math.cos(rake))
    for k in range(3):
        z = 21.1+k*5.1
        c = p.at((0,7.4+(z-18)*math.tan(rake),z))
        bevel_box(model,c,axes,(length,1.4,4.5),WOOD,.22,seed_at(p,k+110))
    for x in (-half+6,half-6):
        # Cast-iron front/rear feet, braced seat carrier and a raked back upright.
        for y in (-7,7):
            box(model,p,(x-2.0,y-2,0),(x+2.0,y+2,.8),IRON,.18)
            beam(model,p.at((x,y,1)),p.at((x,y*.58,15.7)),(1.4,1.4),IRON,.24)
        beam(model,p.at((x,-8,15.4)),p.at((x,9.5,15.4)),(1.7,1.4),IRON,.22)
        bench_back_support(model, p, x)
        beam(model,p.at((x,-6,5)),p.at((x,6,14)),(1.0,1.0),IRON,.15)
        # The grip's outer edge meets the slat ends; the leg frame stays inset.
        arm_x = math.copysign(half-1.1, x)
        bench_arm(model, p, arm_x, 140+int(x))
        for k in range(5):
            bolt(model,p.at((x,-7.2+k*3.6,18.03)),p.z,.23,False)
        for k in range(3):
            z=21.1+k*5.1
            bolt(model,p.at((x,6.65+(z-18)*math.tan(rake),z)),-axes[1],.25,False)
    beam(model,p.at((-half+6,4,9)),p.at((half-6,4,9)),(1.2,1.2),IRON,.16)


def crate(model,p,size):
    # Separate module keeps shipping-crate wear out of the shared furniture primitives.
    import belltower_crates
    belltower_crates.build(model,p,size)


def sack(model, p, centre, size=(28,22,14), seed=0):
    """A stuffed cloth sack with rounded corners, shallow folds and a sewn edge."""
    centre, half = np.asarray(centre,float), np.asarray(size,float)/2
    def local_point(lat,lon):
        c,s=math.cos(lon),math.sin(lon)
        around=np.array((math.copysign(abs(c)**.65,c),math.copysign(abs(s)**.65,s),0))
        radial=max(0,math.cos(lat))**.65
        fold=1+.025*math.sin(7*lon+seed)*radial**4
        q=around*radial*fold
        q[2]=math.copysign(abs(math.sin(lat))**.7,math.sin(lat))
        return q*half
    def vertex(lat,lon):
        q=local_point(lat,lon)
        if abs(abs(lat)-math.pi/2)<.0001:
            n=np.array((0,0,math.copysign(1,lat)))
        else:
            dlat=local_point(lat+.001,lon)-local_point(lat-.001,lon)
            dlon=local_point(lat,lon+.001)-local_point(lat,lon-.001)
            n=np.cross(dlon,dlat); n/=np.linalg.norm(n)
        return p.at(centre+q), p.x*n[0]+p.y*n[1]+p.z*n[2]
    rings,segments=10,32
    for i in range(rings):
        a,b=-math.pi/2+i*math.pi/rings,-math.pi/2+(i+1)*math.pi/rings
        for k in range(segments):
            angles=[(a,k),(a,k+1),(b,k+1),(b,k)]
            if i==0: angles=angles[1:]
            elif i==rings-1: angles=angles[:3]
            pairs=[vertex(lat,j*math.tau/segments) for lat,j in angles]
            face(model,"canvas_plain",[q[0] for q in pairs],sum(q[1] for q in pairs),
                 [(j/segments*2,lat/math.pi+seed*.13) for lat,j in angles],[q[1] for q in pairs])
    # The seam is a thin rolled cloth ridge around the bag's long edge.
    rim=[p.at(centre+local_point(0,k*math.tau/segments)*1.003) for k in range(segments)]
    for a,b in zip(rim,rim[1:]+rim[:1]):
        model.beam(a,b,(.13,.13),"canvas_plain")
