"""Visible Belltower details; all additions are outside gameplay collision.

Photographed height data gives the terracotta roof its silhouette and shadows.
All relief and joinery remain separate from the existing gameplay collision.
"""
import math
import zlib
import numpy as np
import belltower_furniture as Furniture
from functools import lru_cache
from pathlib import Path
from map_kit import Model, normalise


def wall_moulding(model, wall, r0, r1, z0, profile, paint):
    """Extrude a stone profile along a wall; close returns without a concave fan.

    Profile points are (outward depth, height), ordered from bottom to top.
    Horizontal steps create the lips and shadow gaps. Each return is split into
    monotone strips so projecting cornices have no overlapping cap triangles.
    """
    # Street plaques stand only an inch off the wall. Record the actual stone
    # envelope so their placement can clear projecting window hoods and sills.
    wall.plaque_obstacles = list(getattr(wall, 'plaque_obstacles', ())) + [
        (r0, r1, z0+profile[0][1], z0+profile[-1][1])]
    d, sign = wall.outer()
    axis = np.array((1.,0.,0.)) if wall.axis == 'e' else np.array((0.,1.,0.))
    out = np.array((0.,sign,0.)) if wall.axis == 'e' else np.array((sign,0.,0.))
    up = np.array((0.,0.,1.))
    back = min(p[0] for p in profile)

    def at(r, depth, z):
        return wall.point(r,d+sign*depth,z0+z)

    for (da,za),(db,zb) in zip(profile,profile[1:]):
        assert zb >= za, 'Moulding heights must be monotone'
        normal = out*(zb-za)+up*(da-db)
        if np.linalg.norm(normal) < 1e-9:
            continue
        Furniture.face(model,paint,[at(r0,da,za),at(r1,da,za),at(r1,db,zb),at(r0,db,zb)],normal)
        if zb > za:
            for r,toward in ((r0,-axis),(r1,axis)):
                points=[at(r,back,za),at(r,da,za),at(r,db,zb),at(r,back,zb)]
                # At either profile tip the strip can be triangular.
                clean=[]
                for point in points:
                    if not clean or np.linalg.norm(point-clean[-1])>1e-8:
                        clean.append(point)
                if len(clean)>2 and np.linalg.norm(clean[0]-clean[-1])<1e-8:
                    clean.pop()
                if len(clean)>=3:
                    Furniture.face(model,paint,clean,toward)
    Furniture.face(model,paint,[at(r0,back,profile[0][1]),at(r0,back,profile[-1][1]),
        at(r1,back,profile[-1][1]),at(r1,back,profile[0][1])],-out)


def window_sill(model, wall, opening, paint):
    """Sloped stone weathering, a rounded nose and an underside drip recess."""
    # Keep every point in the former sill's bounds, including its highest edge.
    profile=((-0.5,0),(1.8,0),(1.8,.35),(2.45,.35),(2.7,.65),
             (2.7,1.75),(3.0,2.0),(3.0,3.05),(2.65,3.35),(-0.5,4.0))
    wall_moulding(model,wall,opening.r0-3,opening.r1+3,opening.z0-4,profile,paint)


def window_surround(model, wall, opening, paint, variant=0, hood=True):
    """Eased jambs and three related lintel profiles, consistent per house."""
    d, sign=wall.outer()
    band=5.0
    for r0,r1,z0,z1 in ((opening.r0-band,opening.r0,opening.z0,opening.z1+band),
                       (opening.r1,opening.r1+band,opening.z0,opening.z1+band),
                       (opening.r0,opening.r1,opening.z1,opening.z1+band)):
        lo,hi=map(np.asarray,wall.lo_hi(r0,r1,d,d+sign*1.5,z0,z1))
        Furniture.bevel_box(model,(lo+hi)/2,np.eye(3),hi-lo,paint,.22)
    if not hood:
        return
    profiles=(
        ((-.2,0),(1.3,0),(1.3,1),(2.8,1.8),(3.0,2.1),(3.0,3.5),(-.2,4.5)),
        ((-.2,0),(.9,0),(.9,1.3),(1.7,1.3),(2.8,3.2),(3.8,3.2),(4.0,3.4),(4.0,4.6),(-.2,5.5)),
        ((-.2,0),(1.1,0),(1.1,1),(1.6,1.4),(2.2,1.6),(2.9,2.3),(3.1,3.1),(4.4,3.1),(4.4,4.9),(-.2,5.8)),
    )
    wall_moulding(model,wall,opening.r0-band-2,opening.r1+band+2,opening.z1+band,
                  profiles[variant%len(profiles)],paint)


def cornice(model, wall, r0, r1, z0, paint, variant=0):
    """Twelve-inch eaves mouldings, inside the original roof clearance."""
    profiles=(
        ((0,0),(1.3,0),(1.3,2),(3.0,2),(4.5,5),(4.5,6),(6.7,6),(7,6.3),(7,10.8),(6.6,11.3),(0,12)),
        ((0,0),(2,0),(2,3),(3.2,3),(3.2,5),(5.2,5),(5.2,7),(7,7),(7,10.8),(6.6,11.2),(0,12)),
        ((0,0),(1,0),(1,1.8),(2.2,2.3),(3.1,3.1),(3.8,4.4),(4.1,5.6),(6.7,5.6),(7,6),(7,10.8),(6.6,11.3),(0,12)),
    )
    wall_moulding(model,wall,r0,r1,z0,profiles[variant%len(profiles)],paint)


def coping(model, lo, hi, paint, surface):
    """Jointed coping stones within one unchanged gameplay collision box."""
    lo,hi=np.asarray(lo,float),np.asarray(hi,float)
    model.box(lo,hi,None,surface)
    along=int(np.argmax((hi-lo)[:2]))
    length=hi[along]-lo[along]
    count=max(1,round(length/30))
    seed=zlib.crc32(np.round(np.r_[lo,hi],3).tobytes())
    rng=np.random.default_rng(seed)
    weights=rng.uniform(.82,1.18,count)
    bounds=np.r_[0,np.cumsum(weights)/sum(weights)*length]+lo[along]
    # A shallow continuous bedding course closes the visible mortar joints.
    bed=hi.copy(); bed[2]=lo[2]+.28
    model.box(lo,bed,paint)
    for index,(a,b) in enumerate(zip(bounds,bounds[1:])):
        left,right=lo.copy(),hi.copy()
        left[along]=a+(.12 if index else 0)
        right[along]=b-(.12 if index<count-1 else 0)
        left[2]+=.18
        right[2]-=rng.uniform(0,.12)
        Furniture.bevel_box(model,(left+right)/2,np.eye(3),right-left,paint,.3)


def stone_pier(model, lo, hi, surface):
    """Dress the exposed vertical edges without changing the collision box."""
    e0,n0,z0 = lo
    e1,n1,z1 = hi
    bevel = 1.25
    outline = [(e0+bevel,n0),(e1-bevel,n0),(e1,n0+bevel),(e1,n1-bevel),
               (e1-bevel,n1),(e0+bevel,n1),(e0,n1-bevel),(e0,n0+bevel)]
    model.box(lo,hi,None,surface)
    model.prism(outline,z0,z1,{"side":"ashlar"})


@lru_cache(maxsize=1)
def roof_height():
    from PIL import Image
    source = Path(__file__).resolve().parents[1] / "Assets/materials/belltower/scans/clay_roof_tiles_displacement_4k.png"
    # Read the original height map as model data; never resample or rewrite it.
    with Image.open(source) as image:
        return np.asarray(image,dtype=np.float32) / 65535


def roof_surface(model, low, high, across, length):
    """A 3.5-inch mesh grid following the scanned tile heights, with matching UVs.

    The scan's normal map supplies fine surface normals, so vertices retain the
    roof plane's tangent frame instead of applying the same curvature twice.
    """
    low,high = np.asarray(low),np.asarray(high)
    distance = np.linalg.norm(high-low)
    along,across = normalise(high-low),normalise(across)
    up = normalise(np.cross(across,along))
    if up[2] < 0:
        across,up = -across,-up
    nx,ny = math.ceil(length/3.5),math.ceil(distance/3.5)
    xs,ys = np.linspace(-length*.5,length*.5,nx+1),np.linspace(0,distance,ny+1)
    xx,yy = np.meshgrid(xs,ys)
    tile = 4000/25.4
    uvx,uvy = xx/tile + low[0]*.0027, yy/tile + low[1]*.0031
    source = roof_height()
    h,w = source.shape
    u,v = np.mod(uvx,1)*w,np.mod(-uvy,1)*h
    ix,iy = np.floor(u).astype(int),np.floor(v).astype(int)
    tx,ty = u-ix,v-iy
    sample = ((1-tx)*(1-ty)*source[iy%h,ix%w] + tx*(1-ty)*source[iy%h,(ix+1)%w]
              + (1-tx)*ty*source[(iy+1)%h,ix%w] + tx*ty*source[(iy+1)%h,(ix+1)%w])
    points = low + xx[...,None]*across + yy[...,None]*along + (.15+3.0*sample[...,None])*up
    for row in range(ny):
        for col in range(nx):
            indices = ((row,col),(row,col+1),(row+1,col+1),(row+1,col))
            model.polygon("roof_tiles",[points[y,x] for y,x in indices],normal=up,
                          uv=[(uvx[y,x],uvy[y,x]) for y,x in indices])
    # The exposed clay edges close onto the timber substrate; no floating sheet.
    def substrate(point):
        return point - up*(np.dot(point-low,up)+.15)
    for a,b in zip(points[0,:-1],points[0,1:]):
        model.polygon("roof_clay_0",[substrate(a),substrate(b),b,a])
    for edge in (points[:,0],points[:,-1]):
        for a,b in zip(edge[:-1],edge[1:]):
            model.polygon("roof_clay_0",[a,b,substrate(b),substrate(a)],both_sides=True)


def clay_shell(model, origin, across, along, up, width, length, rise, variant):
    """A tapered half-round roof tile, with a thick open mouth and smooth normals."""
    paint = f"roof_clay_{variant % 3}"
    angles = np.linspace(0, math.pi, 7)
    origin = np.asarray(origin, float)
    across, along, up = map(np.asarray, (across, along, up))

    def point(t, a, inner=False):
        taper = 1 - .12 * t
        r = width * .5 * taper - (.38 if inner else 0)
        h = rise * taper - (.38 if inner else 0)
        return origin + along * (t * length) + across * (math.cos(a) * r) + up * (math.sin(a) * h + .4 * t)

    for a, b in zip(angles, angles[1:]):
        vertices = [point(0,a),point(1,a),point(1,b),point(0,b)]
        normals = [normalise(across * math.cos(q) / (width*.5) + up * math.sin(q) / rise) for q in (a,a,b,b)]
        face = np.cross(vertices[1]-vertices[0], vertices[2]-vertices[0])
        if np.dot(face, sum(normals)) < 0:
            vertices.reverse(); normals.reverse()
        model.polygon(paint, vertices, normals=normals)
        # Only the lower mouth is exposed; the next tile covers the far end.
        rim = [point(0,a),point(0,b),point(0,b,True),point(0,a,True)]
        if np.dot(np.cross(rim[1]-rim[0],rim[2]-rim[0]),-along) < 0:
            rim.reverse()
        model.polygon(paint, rim)


def roof_eaves(model, low, high, across, length):
    along = normalise(np.asarray(high)-low)
    across = normalise(across)
    up = normalise(np.cross(across, along))
    if up[2] < 0:
        across = -across
        up = -up
    count = max(1, round(length/8.5))
    step = length/count
    # Three overlapping courses produce the visible edge and a natural lip.
    for column in range(count):
        for row in range(3):
            start = np.asarray(low) + across*((column+.5)*step-length*.5) + along*(row*13-1.0) + up*.25
            clay_shell(model,start,across,along,up,min(7.3,step*.86),15.2,2.2,(column*17+row*11)%3)


def roof_ridge(model, start, end):
    start, end = np.asarray(start), np.asarray(end)
    along = normalise(end-start)
    up = np.array((0.,0.,1.))
    across = normalise(np.cross(along,up))
    count = max(1, math.ceil(np.linalg.norm(end-start)/14.0))
    step = np.linalg.norm(end-start)/count
    for k in range(count):
        clay_shell(model,start+along*k*step,across,along,up,11.5,step+1.2,4.4,k)


def shutter(model, wall, r0, r1, z0, z1, depth, paint, angle=0.0, hinge=None):
    """Timber stiles, rails, tilted louvres, and iron hinge straps."""
    d, sign = wall.outer()
    if angle:
        # Rotate an upper-storey leaf around its actual hinge. This uses a
        # rigid transform, retaining outward winding on every wall direction.
        part=Model()
        shutter(part,wall,r0,r1,z0,z1,depth,paint)
        axis=np.array((1.,0.,0.)) if wall.axis=='e' else np.array((0.,1.,0.))
        out=np.array((0.,sign,0.)) if wall.axis=='e' else np.array((sign,0.,0.))
        turn=math.radians(angle)*np.cross(axis,out)[2]
        c,s=math.cos(turn),math.sin(turn)
        rotation=np.array(((c,-s,0),(s,c,0),(0,0,1)))
        pivot=wall.point(r0 if hinge is None else hinge,d+sign*depth,z0)
        for material,faces in part.polygons.items():
            for points,normal in faces:
                model.polygon(material,[(p-pivot)@rotation.T+pivot for p in points],normal=normal@rotation.T)
        return
    def box(a,b,c,e,f,g,material):
        lo,hi = wall.lo_hi(a,b,d+sign*c,d+sign*e,f,g)
        model.box(lo,hi,material)
    rail = 1.5
    box(r0,r0+rail,depth,depth+1.5,z0,z1,paint)
    box(r1-rail,r1,depth,depth+1.5,z0,z1,paint)
    for z in (z0,(z0+z1)*.5-rail*.5,z1-rail):
        box(r0+rail,r1-rail,depth,depth+1.5,z,z+rail,paint)
    axis = np.array((1.,0.,0.)) if wall.axis == "e" else np.array((0.,1.,0.))
    out = np.array((0.,sign,0.)) if wall.axis == "e" else np.array((sign,0.,0.))
    tilt = math.radians(28)
    slope = np.array((0.,0.,math.cos(tilt))) + out*math.sin(tilt)
    normal = normalise(np.cross(axis,slope))
    for bottom,top in ((z0+rail,(z0+z1)*.5-rail*.5),((z0+z1)*.5+rail*.5,z1-rail)):
        count = max(1,round((top-bottom)/2.6))
        step = (top-bottom)/count
        for k in range(count):
            centre = wall.point((r0+r1)*.5,d+sign*(depth+.8),bottom+(k+.5)*step)
            model.oriented_box(centre,(axis,slope,normal),(r1-r0-2*rail,step+0.15,.42),paint)
    for z in (z0+8,z1-8):
        box(r0+.25,r1-.25,depth+1.5,depth+1.75,z,z+.65,"iron_black")


def street_door(model, wall, r0, r1, z0, z1, paint):
    """Two framed leaves with recessed mouldings and projecting ironmongery.

    UVs retain the existing 48 x 94-inch door atlas. Its panel boundaries,
    grain directions and worn hardware positions match the actual joinery.
    Everything is visual and stays inside the existing closed opening.
    """
    d, sign = wall.outer()
    right_sign = 1 if wall.outward in ("-n", "+e") else -1
    right = np.array((right_sign, 0., 0.)) if wall.axis == "e" else np.array((0., right_sign, 0.))
    out = np.array((0., sign, 0.)) if wall.axis == "e" else np.array((sign, 0., 0.))
    up = np.array((0., 0., 1.))
    sx, sz = (r1-r0)/48, (z1-z0)/94
    front = -5.25

    def point(x, z, depth=front):
        r = r0+x*sx if right_sign > 0 else r1-x*sx
        return wall.point(r, d+sign*depth, z0+z*sz)

    def face(points):
        Furniture.face(model, paint, [point(*p) for p in points], out,
                       [(p[0]/48, p[1]/94) for p in points])

    def rectangle(x0, x1, y0, y1, depth=front):
        face([(x0,y0,depth),(x1,y0,depth),(x1,y1,depth),(x0,y1,depth)])

    def ring(x0, x1, y0, y1, inset, depth):
        return [(x0+inset,y0+inset,depth),(x1-inset,y0+inset,depth),
                (x1-inset,y1-inset,depth),(x0+inset,y1-inset,depth)]

    for leaf in (0,24):
        left, right_edge = leaf+.09, leaf+24-.09
        # Stiles and rails stay distinct: the atlas carries the right grain.
        rectangle(left,leaf+4,.12,93.88)
        rectangle(leaf+20,right_edge,.12,93.88)
        for low, high in ((.12,9),(36,44),(89,93.88)):
            rectangle(leaf+4,leaf+20,low,high)
        # Eased outer edges and the shadow gap at the meeting stiles.
        inner = ring(left,right_edge,.12,93.88,0,front)
        outer = ring(left,right_edge,.12,93.88,-.08,front-.18)
        for k in range(4):
            face([outer[k],outer[(k+1)%4],inner[(k+1)%4],inner[k]])
        for low, high in ((9,36),(44,89)):
            # Quirk, round bead and broad field bevel; all above the backing.
            profile = ((0,0),(.25,-.58),(.48,-.58),(.64,-.40),(.8,-.24),
                       (.98,-.26),(1.17,-.42),(1.38,-.55),(3.2,-.08))
            rings = [ring(leaf+4,leaf+20,low,high,inset,front+depth)
                     for inset,depth in profile]
            for a,b in zip(rings,rings[1:]):
                for k in range(4):
                    face([a[k],a[(k+1)%4],b[(k+1)%4],b[k]])
            face(rings[-1])

    metal = "door_brass"
    # A turned rose, stem and round knob cover the old painted hardware.
    Furniture.turned(model,point(26,40),out,right,
        [(1.29,0),(1.29,.12),(1.1,.23),(.36,.35),(.36,.65),
         (.86,.80),(1.08,1.15),(1.02,1.63),(.76,1.98),(.30,2.16),(.07,2.18)],metal,24)
    Furniture.turned(model,point(26,36),out,right,
        [(.57,.01),(.57,.10),(.46,.16)],metal,20)
    # Dark keyhole on the raised escutcheon.
    Furniture.turned(model,point(26,36.12,front+.17),out,right,
        [(.12,0),(.12,.015)],"iron_black",12)
    Furniture.bevel_box(model,point(26,35.88,front+.18),(right,out,up),(.15,.025,.32),"iron_black",.01)

    # Letter plate: a real slot bordered by four small bevelled brass strips.
    def hardware_box(x0,x1,y0,y1,depth=.16,thickness=.20):
        Furniture.bevel_box(model,point((x0+x1)/2,(y0+y1)/2,front+depth),
            (right,out,up),((x1-x0)*sx,thickness,(y1-y0)*sz),metal,.07)
    hardware_box(14.5,20.5,39.2,39.7)
    hardware_box(14.5,20.5,40.3,40.8)
    hardware_box(14.5,15,39.7,40.3)
    hardware_box(20,20.5,39.7,40.3)
    for x in (14.75,20.25):
        Furniture.turned(model,point(x,40,front+.29),out,right,
            [(.105,0),(.105,.06),(.075,.085)],metal,12)
        Furniture.bevel_box(model,point(x,40,front+.38),(right,out,up),(.12,.01,.025),"iron_black",.004)

    # Hinge knuckles catch a highlight at each leaf's outer edge.
    for x in (.6,47.4):
        for z in (18,76):
            Furniture.turned(model,point(x,z,front+.12),up,right,
                [(.30,-2),(.40,-1.82),(.40,1.82),(.30,2)],"iron_black",16)
