"""Flat military roof finishes and service details on existing HVAC cover.

All added surfaces are thin flashing, lap seams, grilles and fasteners. The
roof slab and the HVAC enclosure retain their existing collision envelopes.
"""
import math

import numpy as np


MATERIAL = 'materials/forestbase/roof_deck.vmat'


def deck(m, bounds, z, bevel):
    if m.__class__.__name__ == 'CollisionOnlyModel':
        return
    x0, x1, y0, y1 = bounds
    # Flat bituminous rolls, unlike the corrugated panels on the two sheds.
    # Broad welded laps stay about one eighth of an inch above the surface.
    # A narrower, nearly coplanar strip shimmered in native roof views.
    seams = np.arange(x0 + 43, x1 - 12, 40)
    for i, x in enumerate(seams):
        m.box((x - .8, y0 + 5, z + .025),
              (x + .8, y1 - 5, z + .14), 'rubber')
        for y in np.arange(y0 + 120 + (i % 3) * 29, y1 - 12, 144):
            m.box((max(x0 + 5, x - 39.2), y - .7, z + .025),
                  (x - .8, y + .7, z + .13), 'rubber')
    # Folded galvanized coping caps the existing slab, with short cover joints.
    for a, b in [((x0 - 1, y0 - 1, z - 1.5), (x1 + 1, y0 + 3, z + 1.25)),
                 ((x0 - 1, y1 - 3, z - 1.5), (x1 + 1, y1 + 1, z + 1.25)),
                 ((x0 - 1, y0 + 3, z - 1.5), (x0 + 3, y1 - 3, z + 1.25)),
                 ((x1 - 3, y0 + 3, z - 1.5), (x1 + 1, y1 - 3, z + 1.25))]:
        bevel(m, a, b, 'structural_steel', .35)
    for x in np.arange(x0 + 72, x1 - 12, 96):
        for y in (y0 + 1, y1 - 1):
            m.box((x - .8, y - 2.1, z + 1.25),
                  (x + .8, y + 2.1, z + 1.45), 'case_hardware')
    # Small screened drains sit over the existing front downpipe corners.
    for x in (x0 + 15, x1 - 15):
        y = y0 + 15
        m.cylinder((x, y), 5, z + .08, z + .3, 'rubber', sides=16)
        for dx in (-3, -1.5, 0, 1.5, 3):
            half = math.sqrt(25 - dx * dx) * .88
            m.box((x + dx - .25, y - half, z + .3),
                  (x + dx + .25, y + half, z + .55), 'steel')


def hvac_details(m, origin, size, bevel, tube):
    if m.__class__.__name__ == 'CollisionOnlyModel':
        return
    e, n, z = origin
    w, d, h = size
    # Back service doors, folded frame seams and small quarter-turn latches.
    for a, b in ((.08, .48), (.52, .92)):
        left, right = e + w * a, e + w * b
        bevel(m, (left, n + d + .05, z + 8),
              (right, n + d + .35, z + h - 8), 'rubber', .12)
        bevel(m, (left + .7, n + d + .35, z + 8.7),
              (right - .7, n + d + .65, z + h - 8.7), 'equipment_paint', .15)
        for zz in (z + 15, z + h - 15):
            m.box((right - 3, n + d + .65, zz - 1.2),
                  (right - 1.5, n + d + .95, zz + 1.2), 'case_hardware')
        for zz in (z + 16, z + h - 16):
            m.box((left + .4, n + d + .7, zz - 2),
                  (left + 2, n + d + 1, zz + 2), 'steel')
    # Side condenser fins give the broad enclosure a readable mechanical face.
    m.box((e - .2, n + 9, z + 12), (e - .05, n + d - 9, z + h - 12), 'rubber')
    for y in np.arange(n + 11, n + d - 10, 3.5):
        m.box((e - .65, y, z + 13), (e - .25, y + .7, z + h - 13), 'steel')
    # A short attached conduit terminates at the existing service compartment.
    for a, b in [((e + w + .9, n + 39, z + 10), (e + w + .9, n + 39, z + 4)),
                 ((e + w + .9, n + 39, z + 4), (e + w - 8, n + 39, z + 4)),
                 ((e + w - 8, n + 39, z + 4), (e + w - 8, n + 22, z + 4))]:
        tube(m, a, b, .65, 'steel', segments=6)
