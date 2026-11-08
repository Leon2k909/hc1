"""Prototype-inspired limestone support for the paired bronze lions."""
from math import cos, pi, sin
import numpy as np
import veridant_fountain_reference_top as mount


PROFILE = [
    (48.25,10.0,9.3), (48.6,10.2,9.55), (49.35,10.2,9.55),
    (49.75,9.8,9.2), (50.4,9.8,9.2), (50.8,9.2,8.65),
    (51.4,8.95,8.4), (53,8.3,8.12), (55,7.65,7.87),
    (57.5,7.02,7.64), (60,6.61,7.48), (62.5,6.38,7.38),
    (65,6.34,7.34), (67.5,6.45,7.38), (70,6.72,7.49),
    (72.5,7.16,7.68), (75,7.77,7.95), (76.5,8.2,8.18),
    (76.9,8.4,8.34), (77.25,8.83,8.72), (77.65,8.97,8.87),
    (78.0,9.46,9.28), (78.32,9.55,9.38), (78.6,10.1,9.8),
    (79.02,10.44,10.08), (79.49,10.5,10.14), (79.88,10.31,9.96),
    (80.17,9.94,9.62), (80.24,9.59,9.32),
]


def leaves(side):
    def stem(z):
        return .36*sin((z-51)*.29)

    yield mount.carving(side, lambda t: (stem(51.4+24*t),51.4+24*t),
                        lambda t,u: (.26-.12*t, .42*(1-u*u)**.8-.035), length=48)

    for start, direction, reach, rise in [
        (52.0,-1,3.15,6.7), (54.5,1,3.32,7.0), (57.1,-1,3.5,7.6),
        (60.5,1,3.48,8.2), (63.3,-1,3.6,8.4), (66.6,1,3.53,8.3),
        (69.1,-1,2.9,7.4), (70.3,0,0,6.4),
    ]:
        def line(t):
            return stem(start) + direction*reach*sin(t*2.15)**1.3, start+rise*t

        def blade(t,u):
            envelope = sin(pi*t)**.87
            lobes = .82 + .18*cos(t*10*pi-.6)
            width = .045 + 1.16*envelope*lobes
            crown = 1-u*u
            lift = envelope*(.85*crown**1.25 + .29*crown**7 + .12*sin(t*14)*crown)
            return width, lift-.045

        yield mount.carving(side, line, blade, length=42, columns=18)

    for direction in (-1,1):
        for fraction, thickness, rise in [(.80,.36,.50),(.69,.13,.23)]:
            def line(t):
                z = 51.1+25.8*t
                width = np.interp(z, mount.PIER_HEIGHTS, mount.PIER_WIDTHS)
                return direction*fraction*width,z

            yield mount.carving(side,line,lambda t,u: (thickness,rise*(1-u*u)**.66-.035),
                                length=60,columns=10)


def build():
    mount.PIER = PROFILE
    mount.PIER_EXPONENT = 3.8
    mount.PIER_HEIGHTS,mount.PIER_WIDTHS,mount.PIER_DEPTHS = np.array(PROFILE).T
    assets = [(f'limestone_{i}',mount.STONE,mesh,uv,1)
              for i,(mesh,uv) in enumerate(mount.moulding(PROFILE,exponent=mount.PIER_EXPONENT,sides=160))]
    for side in (-1,1):
        assets.extend((f'acanthus_{side}_{i}',mount.STONE,mesh,uv,1)
                      for i,(mesh,uv) in enumerate(leaves(side)))
    return assets
