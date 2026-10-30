"""Veridant chair entry point and retained wicker material authoring.

The current upholstered walnut chair is built by veridant_chair_soft.
Render geometry only: retains existing collision and table clearances.
Local x faces the table, y is across the seat, z is inches above the floor.
"""
import math

import numpy as np

from riverdale_parts import card, unit, v


def rounded_outline(x0, x1, y0, y1, radius, steps=8):
    points = []
    for cx, cy, start in ((x1-radius, y1-radius, 0),
                          (x0+radius, y1-radius, 90),
                          (x0+radius, y0+radius, 180),
                          (x1-radius, y0+radius, 270)):
        for k in range(steps+1):
            a = math.radians(start + 90*k/steps)
            points.append(np.array((cx+radius*math.cos(a), cy+radius*math.sin(a))))
    return points


def _tube(model, points, radii, paint, sides=12, closed=False):
    """Smooth tapered tubing, including a continuous frame around a panel."""
    points = [np.asarray(p, float) for p in points]
    if np.isscalar(radii):
        radii = [radii]*len(points)
    tangents = []
    for i in range(len(points)):
        a = points[(i-1) % len(points)] if closed else points[max(0, i-1)]
        b = points[(i+1) % len(points)] if closed else points[min(len(points)-1, i+1)]
        tangents.append(unit(b-a))
    basis = unit(np.cross(tangents[0], (0, 0, 1)))
    if np.linalg.norm(basis) < .5:
        basis = v(1, 0, 0)
    rings = []
    for p, tangent, radius in zip(points, tangents, radii):
        basis = unit(basis - tangent*np.dot(basis, tangent))
        other = np.cross(tangent, basis)
        normals = [basis*math.cos(2*math.pi*k/sides) + other*math.sin(2*math.pi*k/sides)
                   for k in range(sides)]
        rings.append((p, radius, normals))
    for i in range(len(points) if closed else len(points)-1):
        pa, ra, na = rings[i]
        pb, rb, nb = rings[(i+1) % len(points)]
        for k in range(sides):
            j = (k+1) % sides
            card(model, paint, [pa+na[k]*ra, pa+na[j]*ra, pb+nb[j]*rb, pb+nb[k]*rb],
                 na[k]+na[j]+nb[k]+nb[j], normals=[na[k], na[j], nb[j], nb[k]])
    if not closed:
        for index, sign in ((0, -1), (-1, 1)):
            p, radius, normals = rings[index]
            card(model, paint, [p+n*radius for n in normals], tangents[index]*sign)


def _panel(model, outline, position, normal, front, thickness, paint):
    """A closed thin shell; author the weave in panel coordinates, not world axes."""
    centre = np.mean(outline, axis=0)
    for side in (1, -1):
        def point(uv):
            return position(*uv) + normal(*uv)*(thickness*.5*side)

        centre_point = point(centre)
        previous = None
        for scale in (.25, .5, .75, 1.):
            ring_uv = [centre + (uv-centre)*scale for uv in outline]
            ring = [point(uv) for uv in ring_uv]
            for i in range(len(outline)):
                j = (i+1) % len(outline)
                if previous is None:
                    coords = [centre, ring_uv[i], ring_uv[j]]
                    vertices = [centre_point, ring[i], ring[j]]
                else:
                    previous_ring, previous_uv = previous
                    coords = [previous_uv[i], ring_uv[i], ring_uv[j], previous_uv[j]]
                    vertices = [previous_ring[i], ring[i], ring[j], previous_ring[j]]
                normals = [normal(*uv)*side for uv in coords]
                card(model, paint, vertices, front*side,
                     uv=[tuple(uv/4.) for uv in coords], normals=normals)
            previous = ring, ring_uv
    for i, uv in enumerate(outline):
        other = outline[(i+1) % len(outline)]
        pa, pb = position(*uv), position(*other)
        na, nb = normal(*uv)*thickness*.5, normal(*other)*thickness*.5
        direction = (pa+pb)*.5-position(*centre)
        card(model, paint, [pa-na, pb-nb, pb+nb, pa+na], direction,
             uv=[tuple(uv/4.), tuple(other/4.), tuple(other/4.), tuple(uv/4.)])


def _woven_build_into(model, at, facing, z0=0., paint="vr_wicker"):
    f = unit(v(facing[0], facing[1], 0))
    s = np.cross((0, 0, 1), f)
    c = v(at[0], at[1], z0)

    def world(point):
        return c + f*point[0] + s*point[1] + v(0, 0, point[2])

    def direction(point):
        return unit(f*point[0] + s*point[1] + v(0, 0, point[2]))

    def tube(points, radius, material, sides=12, closed=False):
        _tube(model, [world(p) for p in points], radius, material, sides, closed)

    # A shallow seat dish with rounded corners and a separate round bound edge.
    seat = rounded_outline(-7.5, 7.7, -7.65, 7.65, 1.8)
    def seat_z(x, y):
        return 17.45 + .003*x*x + .004*y*y + .018*x
    _panel(model, seat, lambda x,y: world((x,y,seat_z(x,y))),
           lambda x,y: direction((-.006*x-.018,-.008*y,1)), v(0,0,1), .48, paint)
    tube([(x,y,seat_z(x,y)-.10) for x,y in seat], .30, "vr_timber_dark", 12, True)

    # Recline and transverse bow are geometry. The back catches soft highlights
    # rather than presenting the original flat vertical board to the light.
    back = rounded_outline(-7.25, 7.25, 19.3, 33.1, 1.8)
    def back_x(y,z):
        return -7.05-.125*(z-19.3)+.0155*y*y
    _panel(model, back, lambda y,z: world((back_x(y,z),y,z)),
           lambda y,z: direction((1,-.031*y,.125)), f, .48, paint)
    tube([(back_x(y,z),y,z) for y,z in back], .31, "vr_timber_dark", 12, True)

    # Splayed legs and swept rear uprights, with under-seat supports and rubber
    # glides. Feet stay on the original floor instead of floating above it.
    for sign in (-1, 1):
        tube([(7.1,sign*7.1,.32),(6.9,sign*6.95,3.5),(6.55,sign*6.7,9),
              (6.2,sign*6.35,14.9),(5.8,sign*6.15,seat_z(5.8,6.15)-.61)],
             [.27,.30,.34,.38,.39], "vr_steel")
        # Pass behind the seat's rear bound edge before rising behind the back.
        # The old sweep crossed the seat and emerged through the front wicker.
        tube([(-7.65,sign*7.2,.32),(-7.35,sign*6.95,4),(-7.35,sign*6.7,11),
              (-8.25,sign*6.65,16.5),(-8.35,sign*6.65,18.7),
              (-7.55,sign*6.65,20.4),
              (back_x(sign*6.65,25.5)-.82,sign*6.65,25.5),
              (back_x(sign*6.6,30.4)-.82,sign*6.6,30.4)],
             [.28,.31,.36,.40,.40,.39,.35,.31], "vr_steel")
        # Rails meet the seat from below; the back posts have their own short
        # under-seat brackets instead of piercing the seating surface.
        side_rail = [(-6.8,sign*6.4),(-3.4,sign*6.55),(3.8,sign*6.55),(6.2,sign*6.3)]
        tube([(x,y,seat_z(x,y)-.61) for x,y in side_rail], .34, "vr_steel")
        tube([(-8.25,sign*6.65,16.5),(-7.8,sign*6.6,16.8),
              (-6.8,sign*6.4,seat_z(-6.8,6.4)-.61)], .30, "vr_steel")
        tube([(-6.9,sign*6.75,6.5),(-3.5,sign*6.75,6.25),
              (3.4,sign*6.75,6.25),(6.7,sign*6.75,6.5)], .20, "vr_steel")
        for x,y in ((7.1,sign*7.1),(-7.65,sign*7.2)):
            tube([(x,y,0),(x,y,.55)], .33, "vr_black", 12)
        # Rear mounting spacers finish behind the back skin. Their caps are
        # parallel to its surface, leaving the visible front uninterrupted.
        for z in (21.,29.2):
            y = sign*6.65
            centre = world((back_x(y,z),y,z))
            n = direction((1,-.031*y,.125))
            _tube(model,[centre-n*.84,centre-n*.255],.18,"vr_steel",12)
    for x in (-6.5,5.6):
        tube([(x,y,seat_z(x,y)-.54) for y in (-6.2,0,6.2)], .27, "vr_steel")


def build_into(model, at, facing, z0=0., paint="vr_wicker"):
    from veridant_chair_authored import build_into as build_soft
    build_soft(model, at, facing, z0, paint)


def wicker_surface(size=1024):
    """Seamless 4-inch basket weave with strand colour and physical height."""
    y, x = np.mgrid[0:size,0:size].astype(np.float32)/size*20
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    ux, uy = x-ix-.5, y-iy-.5
    warp, weft = np.abs(ux)<.465, np.abs(uy)<.465
    over = (ix+iy) % 2 == 0
    vertical = warp & (~weft | over)
    horizontal = weft & (~warp | ~over)
    occupied = vertical | horizontal
    cross = np.where(vertical, ux, uy)
    along = np.where(vertical, y, x)
    crest = np.sqrt(np.maximum(0, 1-(cross/.48)**2))
    # Different natural reeds, restrained fibre grain, and dark recessed joints.
    reed = np.where(vertical, np.sin(ix*2.11)+np.sin(ix*.53),
                    np.cos(iy*1.73)+np.sin(iy*.71))*.028
    grain = np.sin(cross*310+np.sin(along*1.2)*2)*.008
    grain += np.sin(cross*91+np.sin(along*2.1))*.009
    shade = np.where(occupied, .91+.10*crest+reed+grain, .34)
    colour = np.stack([shade*.235, shade*.153, shade*.084], axis=-1)
    rough = np.where(occupied, .61+reed+grain, .91)
    # Heights are inches, as expected by veridant_materials.write_surface.
    height = np.where(occupied, .026*crest+.002*grain, -.012).astype(np.float32)
    return colour.astype(np.float32), rough.astype(np.float32), height, size/4.
