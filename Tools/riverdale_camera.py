"""Reactor hall CCTV candidate: a serviceable weatherproof camera, in inches."""
import math
import numpy as np
import riverdale_parts as P
import riverdale_hall as H

UP = P.UP
PAINT = 'rv_cam_paint'
SEAL = 'rv_cam_seal'
METAL = 'rv_cam_metal'
GLASS = 'rv_cam_glass'
INNER = 'rv_cam_inner'
LABEL = 'rv_cam_label'
MATERIALS = (PAINT, SEAL, METAL, GLASS, INNER, LABEL)

def camera(d, fine, face, s, z, target):
    """Fits the original wall anchors and aiming direction; purely visual, no collision."""
    at = face.p(s, z, 0)
    end = face.p(s, z, 10)
    x, y, zz = H.axes_along(H.unit(P.v(*target) - end), UP)
    centre = end - UP * 3.2 + x * 2.5
    axes = (x, y, zz)
    for model in (d, fine):
        for paint in MATERIALS:
            model.tile_overrides[paint] = 7.0
            model.material_overrides[paint] = f'materials/riverdale/cctv_v2/{paint}.vmat'

    def box(c, size, paint=PAINT, bevel=.12, frame=axes):
        P.bevel_box(d, c, frame, size, paint, bevel)

    def screw(c, axis, radius=.13):
        P.lathe_axis(d, c, axis, [(radius, -.03), (radius, .055), (radius*.72, .085), (0, .085)], METAL, 8)
        a, b = P.perp(axis)
        P.quad(d, SEAL, c + axis*.088, a, b, radius*1.1, radius*.19)

    # Gasket, cast wall flange and four captive stainless fixings.
    wall_axes = (face.out, face.a, UP)
    box(at + face.out*.12, (.24, 4.55, 5.9), SEAL, .10, wall_axes)
    box(at + face.out*.45, (.52, 4.3, 5.65), PAINT, .24, wall_axes)
    for sy in (-1, 1):
        for sz in (-1, 1):
            screw(at + face.out*.73 + face.a*sy*1.56 + UP*sz*2.05, face.out, .19)

    # A cast arm with a downward elbow, a tilt hinge, and a strain-relieved cable.
    P.tube(d, [at + face.out*.65, at + face.out*3.2,
               end - face.out*1.1, end - UP*1.05], .58, PAINT, 12, bend_radius=1.15)
    box(end - UP*1.4, (2.45, 1.8, .62), PAINT, .15)
    hinge = centre - x*1.7 + zz*2.0
    P.lathe_axis(d, hinge-y*1.28, y, [(0, 0), (.72, 0), (.82, .12), (.82, 2.44), (.72, 2.56), (0, 2.56)], PAINT, 20)
    screw(hinge+y*1.30, y, .36)
    screw(hinge-y*1.30, -y, .36)
    P.tube(d, [at + face.out*.8 - UP*1.0,
               at + face.out*3.0 - UP*2.2,
               end - x*4.8 - UP*3.8,
               centre-x*5.20-zz*.75], .18, SEAL, 8, bend_radius=.8)
    P.lathe_axis(d, centre-x*5.35-zz*.75, -x,
                 [(.28, 0), (.34, .15), (.34, .40), (.23, .52)], SEAL, 10)

    # Extruded housing, rear service lid and continuous dark lid seal.
    box(centre-x*.1, (9.5, 4.2, 4.05), PAINT, .32)
    box(centre-x*4.57, (.15, 4.23, 4.08), SEAL, .24)
    box(centre-x*4.86, (.50, 4.2, 4.05), PAINT, .28)
    for sy in (-1, 1):
        for sz in (-1, 1):
            screw(centre-x*5.12 + y*sy*1.35 + zz*sz*1.28, -x)

    # Front gasket and inset lens face. The glass is recessed behind machined rings.
    box(centre+x*4.65, (.30, 4.15, 4.0), SEAL, .28)
    box(centre+x*4.86, (.30, 4.12, 3.97), PAINT, .28)
    box(centre+x*5.025, (.10, 3.56, 3.40), INNER, .26)
    lens = centre+x*5.08+zz*.12
    P.lathe_axis(d, lens, x,
                 [(1.36, 0), (1.42, .10), (1.42, .30), (1.29, .42),
                  (1.04, .42), (.97, .32), (.97, .08)], SEAL, 32)
    P.lathe_axis(d, lens, x, [(1.27, .37), (1.28, .43), (1.19, .48), (1.13, .48)], METAL, 32)
    P.lathe_axis(d, lens, x, [(1.12, .26), (1.12, .34), (.85, .34), (.82, .16)], INNER, 32)
    P.lathe_axis(d, lens, x, [(.82, .17), (.58, .20), (.30, .235), (0, .245)], GLASS, 32)
    for sy in (-1, 1):
        for sz in (-1, 1):
            screw(centre+x*5.09+y*sy*1.40+zz*sz*1.27, x, .10)
    # Two unlit sensor windows below the lens, not emissive lights.
    for sy in (-1, 1):
        point = centre+x*5.09+y*sy*.55-zz*1.35
        P.lathe_axis(d, point, x, [(.16, 0), (.16, .045), (0, .045)], GLASS, 12)

    # Folded sheet-metal sunshield: soft leading edge and two turned-down side lips.
    shield = centre + zz*2.40+x*.58
    box(shield, (12.3, 5.42, .17), PAINT, .075)
    for sy in (-1, 1):
        box(shield+y*sy*2.65-zz*.31, (12.18, .14, .62), PAINT, .06)
    for xx in (-3.6, 2.5):
        box(centre+x*xx+zz*2.13, (.5, 2.8, .35), SEAL, .06)
        screw(shield+x*xx+zz*.095, zz, .14)

    # Discreet side identification plate and a single cast alignment mark.
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for sy in (-1, 1):
        side = centre+y*sy*2.108-x*1.1-zz*.22
        P.quad(d, LABEL, side, -x*sy, zz, 2.45, .83, uv)
    return centre
