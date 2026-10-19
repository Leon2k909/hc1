"""Visible Belltower details; all additions are outside gameplay collision.

Photographed height data gives the terracotta roof its silhouette and shadows.
All relief and joinery remain separate from the existing gameplay collision.
"""
import math
import numpy as np
from functools import lru_cache
from pathlib import Path
from map_kit import normalise


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


def shutter(model, wall, r0, r1, z0, z1, depth, paint):
    """Timber stiles, rails, tilted louvres, and iron hinge straps."""
    d, sign = wall.outer()
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
