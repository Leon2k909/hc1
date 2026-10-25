"""Open, glazed timber casements for the town's usable rectangular windows.

Only render geometry is added: the old opening and collision stay clear. Each
leaf opens past 90 degrees, with separate glass panes and bevelled joinery.
"""
import hashlib
import math

import numpy as np

import building_textures as BT
import belltower_detail as D
import belltower_furniture as F

GLASS = tuple(f'open_window_glass_{i}' for i in range(3))
MATERIALS = {paint: f'materials/belltower/church-windows-v1/church_window_glass_{i}.vmat'
             for i, paint in enumerate(GLASS)}
MATERIALS.update({f'open_window_{paint}': f'materials/buildings/{paint}.vmat'
                  for paint in ('trim_white', 'trim_brown')})


def configure(model):
    model.material_overrides.update(MATERIALS)
    model.grain_paints.update(('open_window_trim_white', 'open_window_trim_brown'))
    model.tile_overrides.update({paint: 1. for paint in GLASS})
    model.tile_overrides.update({f'open_window_{paint}': BT.tile_units(paint)
                                 for paint in ('trim_white', 'trim_brown')})


def build(model, wall, opening, trim, covered=False):
    """Two outward-opening leaves; returns their poses for clearance checks."""
    configure(model)
    trim = f'open_window_{trim}'
    o = opening
    assert o.kind == 'window' and not o.arched
    distance, sign = wall.outer()
    run = np.array((1., 0., 0.) if wall.axis == 'e' else (0., 1., 0.))
    out = np.array((0., sign, 0.) if wall.axis == 'e' else (sign, 0., 0.))
    up = np.array((0., 0., 1.))
    key = f'{wall.axis}:{wall.outward}:{wall.across}:{o.r0}:{o.z0}'.encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:4], 'little')
    width = (o.r1-o.r0-6.4)/2-.25
    height = o.z1-o.z0-6.4
    stile, rail, thickness = 1.7, 1.9, 2.1
    rows = 3 if height >= 80 else 2
    poses = []
    for leaf, (hinge_r, handed) in enumerate(((o.r0+3.2, 1), (o.r1-3.2, -1))):
        # The Bakery/Dairy serving windows sit beneath low canvas canopies.
        # Their leaves fold flat inside, clear of both cloth and shop shelves.
        angle = 178. if covered else 112.+((seed >> (leaf*4)) % 9)
        radians = math.radians(angle)
        swing = -out if covered else out
        along = handed*run*math.cos(radians)+swing*math.sin(radians)
        normal = np.cross(up, along)
        axes = np.array((along, normal, up))
        assert np.linalg.det(axes) > .999
        jamb = -abs(wall.across[1]-wall.across[0]) if covered else 0.
        hinge_depth = jamb-2.2 if covered else 2.2
        hinge = wall.point(hinge_r, distance+sign*hinge_depth, o.z0+3.2)

        def point(u, depth, z):
            return hinge+u*along+depth*normal+z*up

        def block(u0, u1, d0, d1, z0, z1, paint=trim, bevel=.13):
            F.bevel_box(model, point((u0+u1)/2, (d0+d1)/2, (z0+z1)/2), axes,
                        (u1-u0, d1-d0, z1-z0), paint, bevel, seed+leaf)

        # Mortised sash with a small lower drip rail, rather than flat stripes.
        for u0, u1 in ((0., stile), (width-stile, width)):
            block(u0, u1, -thickness/2, thickness/2, 0., height)
        for z0, z1 in ((0., rail+.45), (height-rail, height)):
            block(stile, width-stile, -thickness/2, thickness/2, z0, z1)
        block(-.15, width+.15, -.8, 1.25, .4, 1.15, bevel=.16)
        bottom, top = rail+.45, height-rail
        muntin = 1.05
        for row in range(1, rows):
            z = bottom+(top-bottom)*row/rows
            block(stile, width-stile, -.75, .75, z-muntin/2, z+muntin/2, bevel=.1)

        # Individual glass lights, shallow glazing beads, slightly wavy old glass.
        for row in range(rows):
            z0 = bottom+(top-bottom)*row/rows+(muntin/2 if row else 0.)
            z1 = bottom+(top-bottom)*(row+1)/rows-(muntin/2 if row+1 < rows else 0.)
            for depth in (-.46, .46):
                bead = .32
                for u0, u1 in ((stile, stile+bead), (width-stile-bead, width-stile)):
                    block(u0, u1, depth-.16, depth+.16, z0, z1, bevel=.055)
                for a, b in ((z0, z0+bead), (z1-bead, z1)):
                    block(stile+bead, width-stile-bead, depth-.16, depth+.16, a, b, bevel=.055)
            paint = GLASS[(seed+leaf+row) % len(GLASS)]
            u0, u1 = stile+.2, width-stile-.2
            # A 2x2 grid gives a subtle variation in reflections, without a warp
            # large enough to detach the pane from its surrounding timber bead.
            for x in range(2):
                for z in range(2):
                    corners = []
                    uv = []
                    for a, b in ((x, z), (x+1, z), (x+1, z+1), (x, z+1)):
                        u, v = a/2, b/2
                        wave = .025*math.sin(math.pi*u)*math.sin(math.pi*v)
                        corners.append(point(u0+(u1-u0)*u, wave, z0+(z1-z0)*v))
                        uv.append((u, v))
                    D.outward(model, paint, corners, -normal, uv)

        # Dark iron hinge barrels and an inside latch make the leaves readable
        # close up; no new collision or fixed bars across the opening.
        for z in (8., height-8.):
            D.rod(model, point(.35, 0., z-1.7), point(.35, 0., z+1.7), .36, 'iron_black', sides=8)
            block(0., 3.7, -1.22, -1.06, z-.55, z+.55, 'iron_black', .07)
            # The short jamb plate reaches back into the existing outer frame.
            a = wall.point(hinge_r, distance+sign*(jamb+.5 if covered else -.5), o.z0+3.2+z)
            b = point(.35, 0., z)
            D.rod(model, a, b, .28, 'iron_black', sides=6)
        z = min(height*.48, 35.)
        block(width-3.2, width-2.1, -1.26, -1.08, z-2.1, z+2.1, 'iron_black', .08)
        D.rod(model, point(width-2.65, -1.5, z-1.25), point(width-2.65, -1.5, z+1.25), .19, 'iron_black', sides=8)
        poses.append({'angle': angle, 'width': width, 'height': height,
                      'hinge': hinge.tolist(), 'along': along.tolist(), 'out': swing.tolist(),
                      'covered': covered,
                      'run': run.tolist(), 'handed': handed})
    return poses
