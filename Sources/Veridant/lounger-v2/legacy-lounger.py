"""Original published lounger, retained only for exact baked-face replacement."""
import math
import numpy as np
from riverdale_parts import v, unit, obox, UP
WOOD = "wood"


def lounger(m, c, facing, z0=0.0, surface=WOOD):
    f = unit(v(facing[0], facing[1], 0))
    s = np.cross(UP, f)
    b = v(c[0], c[1], z0)
    for sg in (-1, 1):
        obox(m, b + s * 11 * sg + UP * 6, f, (74, 2, 4), "vr_timber_dark")
        for sa in (-1, 1):
            obox(m, b + s * 11 * sg + f * 33 * sa + UP * 2, f, (3, 2, 4), "vr_timber_dark")
    obox(m, b + f * 8 + UP * 9.5, f, (52, 24, 3), "vr_mattress")
    back = b - f * 28 + UP * 18
    m.oriented_box(back, (unit(f * math.cos(0.9) + UP * math.sin(0.9)), s,
                          np.cross(unit(f * math.cos(0.9) + UP * math.sin(0.9)), s)), (26, 24, 3), "vr_mattress")
    m.oriented_box(b + UP * 8, (f, s, UP), (76, 26, 16), {}, surface)

