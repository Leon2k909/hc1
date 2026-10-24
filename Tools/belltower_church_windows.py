"""Three recessed arched windows on the church's square-facing facade.

Visual construction only. The existing opening dimensions, masonry collision
and two-inch glass collision slabs are retained by belltower_map.dress.
"""
import math
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_furniture as F
import belltower_architecture as A

STONE = 'church_window_stone'
REVEAL = 'church_window_reveal'
FRAME = 'church_window_frame'
LEAD = 'church_window_lead'
GLASS = tuple('church_window_glass_'+str(i) for i in range(3))
MATERIALS = {
    STONE: 'materials/belltower/well-v1/well_cut_stone.vmat',
    REVEAL: 'materials/belltower/well-v1/well_damp_stone.vmat',
    FRAME: 'materials/belltower/wood_planks_dark.vmat',
    LEAD: 'materials/buildings/iron_black.vmat',
    **{p: 'materials/belltower/church-windows-v1/'+p+'.vmat' for p in GLASS},
}


def glass_materials():
    result = {}
    for name, tint, rough in zip(GLASS, ((.80, .88, .91), (.83, .89, .90), (.78, .86, .90)), (.20, .23, .21)):
        colour = ' '.join(f'{x:.3f}' for x in tint)
        result[name] = ('// Belltower church facade: translucent, gently wavy old glazing\n"Layer0"\n{\n'
            '    shader "shaders/cerroblanco_glass.shader"\n    F_GLASS_QUALITY "2"\n    F_RENDER_BACKFACES "1"\n'
            '    g_flCoatingReflection "0.16"\n'
            '    g_bFogEnabled "1"\n    g_flBlurAmount "0.018"\n    g_flRefractionStrength "1.004"\n'
            '    AlbedoAbsorption "0.60"\n    g_flTintColor "[1 1 1 0]"\n'
            f'    TextureColor "[{colour} 0]"\n'
            '    TextureNormal "materials/default/default_normal.tga"\n'
            f'    TextureRoughness "[{rough} {rough} {rough} 0]"\n'
            '    TextureMetalness "[0 0 0 0]"\n    TextureAmbientOcclusion "[1 1 1 0]"\n'
            '    F_DO_NOT_CAST_SHADOWS "1"\n}\n')
    return result


def configure(model):
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({STONE: 40., REVEAL: 40., FRAME: 72., LEAD: 32., **{p: 48. for p in GLASS}})
    model.grain_paints.add(FRAME)


def frame(wall):
    d, sign = wall.outer()
    out = np.array((0., sign, 0.)) if wall.axis == 'e' else np.array((sign, 0., 0.))
    return lambda r, depth, z: wall.point(r, d+sign*depth, z), out


def block(model, wall, r0, r1, d0, d1, z0, z1, paint, bevel=.15):
    d, sign = wall.outer()
    lo, hi = map(np.asarray, wall.lo_hi(r0, r1, d+sign*d0, d+sign*d1, z0, z1))
    F.bevel_box(model, (lo+hi)/2, np.eye(3), hi-lo, paint, bevel)


def arch_band(model, P, rc, spring, profile, paint, pieces, joint=0.):
    for i in range(pieces):
        a0 = i*math.pi/pieces+joint/2
        a1 = (i+1)*math.pi/pieces-joint/2
        rings = [[P(rc+r*math.cos(a), depth, spring+r*math.sin(a)) for r, depth in profile] for a in (a0, a1)]
        centre = np.mean(rings, axis=(0, 1))
        for j in range(len(profile)):
            k = (j+1) % len(profile)
            pts = [rings[0][j], rings[1][j], rings[1][k], rings[0][k]]
            D.outward(model, paint, pts, np.mean(pts, axis=0)-centre)
        for ring in rings:
            D.outward(model, paint, ring, np.mean(ring, axis=0)-centre)


def clip(polygon, axis, value, greater):
    result = []
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        inside_a = (a[axis] >= value) if greater else (a[axis] <= value)
        inside_b = (b[axis] >= value) if greater else (b[axis] <= value)
        if inside_a: result.append(a)
        if inside_a != inside_b:
            t = (value-a[axis])/(b[axis]-a[axis])
            result.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
    return result


def build(model, wall, o):
    configure(model)
    P, out = frame(wall)
    rc, radius, spring = (o.r0+o.r1)/2, o.radius, o.spring
    width = o.r1-o.r0
    # Individually eased jamb blocks and matching radial voussoirs.
    band = 5.2
    count = max(3, round((spring-o.z0)/22))
    levels = np.linspace(o.z0, spring, count+1)
    for j, (z0, z1) in enumerate(zip(levels[:-1], levels[1:])):
        for sign in (-1, 1):
            a, b = sorted((rc+sign*(radius-.8), rc+sign*(radius+band)))
            block(model, wall, a, b, -.9, 1.65+(j % 3)*.06, z0+.06, z1-.06, STONE, .24)
    profile = [(radius-.8, -.9), (radius-.8, 1.10), (radius-.35, 1.75),
               (radius+4.7, 1.75), (radius+band, 1.15), (radius+band, -.9)]
    arch_band(model, P, rc, spring, profile, STONE, 17 if width > 40 else 11, .003)
    # Splayed reveals carry the opening back 12 inches, to the actual frame.
    for sign in (-1, 1):
        pts = [P(rc+sign*(radius-.8), -.8, o.z0), P(rc+sign*(radius-.8), -.8, spring),
               P(rc+sign*(radius-2.5), -12.2, spring), P(rc+sign*(radius-2.5), -12.2, o.z0)]
        D.outward(model, REVEAL, pts, -sign*(P(rc+1, 0, 0)-P(rc, 0, 0)))
    # Continuous curved soffit; each strip faces into the glazed opening.
    for j in range(32):
        a, b = j*math.pi/32, (j+1)*math.pi/32
        points = [P(rc+r*math.cos(angle), depth, spring+r*math.sin(angle))
                  for r, depth, angle in [(radius-.8, -.8, a), (radius-.8, -.8, b),
                                          (radius-2.5, -12.2, b), (radius-2.5, -12.2, a)]]
        inward = -(math.cos((a+b)/2)*(P(rc+1, 0, 0)-P(rc, 0, 0))+np.array((0., 0., math.sin((a+b)/2))))
        D.outward(model, REVEAL, points, inward)
    sill = [(-13., 0), (5.5, 0), (6., .45), (6., 1.7), (5.6, 2.1), (-13., 4.)]
    A.wall_moulding(model, wall, o.r0-6, o.r1+6, o.z0-4, sill, STONE)
    # Recessed timber sash, including the previously missing curved head.
    bar = 2.5 if width > 40 else 1.65
    r = radius-2.6
    zbase = o.z0+1.2
    for sign in (-1, 1):
        a, b = sorted((rc+sign*r, rc+sign*(r-bar)))
        block(model, wall, a, b, -13.6, -10.4, zbase, spring, FRAME, .18)
    block(model, wall, rc-r, rc+r, -13.6, -10.4, zbase, zbase+bar, FRAME, .18)
    arch_band(model, P, rc, spring, [(r-bar, -13.6), (r-bar, -10.7), (r-bar+.3, -10.4),
              (r-.3, -10.4), (r, -10.7), (r, -13.6)], FRAME, 32)
    clear = r-bar
    # Individual panes and genuine room visibility replace the opaque black sheet.
    outline = [(rc-clear, zbase+bar), (rc+clear, zbase+bar)] + [
        (rc+clear*math.cos(t), spring+clear*math.sin(t)) for t in np.linspace(0, math.pi, 33)]
    body_rows = 3 if width > 40 else 4
    levels = list(np.linspace(zbase+bar, spring, body_rows+1))+[spring+clear+.1]
    centre_bar = 1.35 if width > 40 else .85
    for row, (z0, z1) in enumerate(zip(levels[:-1], levels[1:])):
        for col, (x0, x1) in enumerate(((rc-clear, rc-centre_bar/2), (rc+centre_bar/2, rc+clear))):
            panel = outline[:]
            for axis, value, greater in ((0, x0+.1, True), (0, x1-.1, False), (1, z0+.12, True), (1, z1-.12, False)):
                if panel: panel = clip(panel, axis, value, greater)
            if len(panel) < 3: continue
            paint = GLASS[(row+col+round(rc)) % len(GLASS)]
            def depth(x, z):
                return -12.0+.045*math.sin((x-rc)*.17+row)*math.sin(z*.12+col)
            points = [P(x, depth(x, z), z) for x, z in panel]
            D.outward(model, paint, points, out, uv=[((x-rc)/48, (z-o.z0)/48) for x, z in panel])
    block(model, wall, rc-centre_bar/2, rc+centre_bar/2, -12.15, -10.9,
          zbase+bar, spring+clear-.4, FRAME, .12)
    for z in levels[1:-1]:
        block(model, wall, rc-clear, rc+clear, -12.05, -11.1, z-.40, z+.40, LEAD, .10)
    # One fine fanlight spoke each side of the central stem, clipped to the arch.
    for a in (math.pi/3, 2*math.pi/3):
        D.rod(model, P(rc, -11.35, spring), P(rc+clear*math.cos(a), -11.35, spring+clear*math.sin(a)), .30, LEAD, sides=8)


def front_band(model, wall):
    """Leave the large arch visible where it intersects the old eaves band."""
    for r0, r1 in ((wall.run[0], -42), (42, wall.run[1])):
        d, sign = wall.outer()
        lo, hi = wall.lo_hi(r0, r1, d, d+sign*8, 275, 287)
        model.box(lo, hi, 'ashlar_grey')


def front_wall():
    wall = K.Wall('e', (-170., 170.), (-420., -400.), (0., 300.), '+n')
    for rc, width, z0, z1 in ((0, 70, 190, 290), (-110, 30, 110, 230), (110, 30, 110, 230)):
        wall.add(rc, width, z0, z1, 'glass_arch')
    return wall
