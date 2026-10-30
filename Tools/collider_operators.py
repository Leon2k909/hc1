"""Collider operator furniture. Plan coordinates, inches; staged/native publication only.

The two generated reference images in Sources/Collider/control-room-v1/references
guide the chair construction and the console's separate manufactured parts.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import map_kit as K
from belltower_furniture import face, bevel_box, beam

MATERIAL_DIR = 'materials/collider/control-room-v1'
PAINTS = ('op_fabric', 'op_shell', 'op_worktop', 'op_paint', 'op_alloy', 'op_keys')
TILES = dict(op_fabric=6., op_shell=16., op_worktop=32., op_paint=24., op_alloy=12., op_keys=1.)
UP = np.array((0., 0., 1.))
AXES = np.eye(3)
CALLS = [(side, n, z, z == 256.) for side in (-1, 1)
         for z, positions in ((256., (-55., 95., 245.)), (560., (-220., -70., 80., 230.)))
         for n in positions]
GLYPHS = list(dict.fromkeys(list('1234567890-=QWERTYUIOP[]ASDFGHJKL;\'ZXCVBNM,./') +
    ['ESC', 'TAB', 'CAPS', 'SHIFT', 'CTRL', 'ALT', 'ENTER', 'BKSP', 'SPACE', 'FN', 'UP', 'DN', 'LT', 'RT',
     'INS', 'DEL', 'HOME', 'END', 'PGUP', 'PGDN']))
GLYPH_ROWS = 16


def signed_power(value, power):
    return math.copysign(abs(value) ** power, value) if abs(value) > 1e-12 else 0.


def soft_box(m, centre, size, paint, *, deform=None, uv_axes=None, detail=1, power=.38):
    """Closed padded/molded surface, smooth geometric normals, no flat box silhouette."""
    centre = np.asarray(centre, float)
    half = np.asarray(size, float) / 2
    around, vertical = (32, 14) if detail else (24, 10)

    def sample(theta, phi):
        ring = abs(math.cos(phi)) ** power
        p = half * np.array((ring * signed_power(math.cos(theta), power),
                             ring * signed_power(math.sin(theta), power),
                             signed_power(math.sin(phi), power)))
        return p if deform is None else deform(p.copy())

    def normal(theta, phi):
        h = 1e-4
        a = sample(theta+h, phi)-sample(theta-h, phi)
        b = sample(theta, phi+h)-sample(theta, phi-h)
        return K.normalise(np.cross(a, b))

    rings = []
    for j in range(1, vertical):
        phi = -math.pi/2 + math.pi*j/vertical
        rings.append([(sample(math.tau*i/around, phi), normal(math.tau*i/around, phi))
                      for i in range(around)])

    def emit(items):
        points = [p+centre for p, n in items]
        ns = [n for p, n in items]
        uv = [(p[uv_axes[0]]/TILES[paint], p[uv_axes[1]]/TILES[paint]) for p, n in items] if uv_axes else None
        face(m, paint, points, K.normalise(sum(ns)), uv=uv, normals=ns)

    for bottom, top in zip(rings, rings[1:]):
        for i in range(around):
            k = (i+1) % around
            emit([bottom[i], bottom[k], top[k], top[i]])
    for sign, ring in ((-1, rings[0]), (1, rings[-1])):
        pole = sample(0, sign*math.pi/2)
        # The transformed pole normal is sampled just inside its smooth surface.
        pn = K.normalise(sum(normal(math.tau*i/around, sign*(math.pi/2-.0001)) for i in range(around)))
        for i in range(around):
            emit([(pole, pn), ring[i], ring[(i+1) % around]])


def outline(width, depth, radius, segments=4):
    radius = min(radius, width*.49, depth*.49)
    points = []
    for cx, cy, start in ((width/2-radius, depth/2-radius, 0),
                          (-width/2+radius, depth/2-radius, 90),
                          (-width/2+radius, -depth/2+radius, 180),
                          (width/2-radius, -depth/2+radius, 270)):
        for j in range(segments+1):
            a = math.radians(start+90*j/segments)
            points.append(np.array((cx+radius*math.cos(a), cy+radius*math.sin(a))))
    return points


def round_block(m, centre, size, paint, radius=.5, bevel=.12, axes=AXES, segments=3):
    """Closed solid with rounded plan corners and small actual bevels on both rims."""
    centre, axes = np.asarray(centre), np.asarray(axes)
    width, depth, height = size
    bevel = min(bevel, height*.4, width*.1, depth*.1, radius*.7)
    profiles = [(-height/2, bevel), (-height/2+bevel, 0),
                (height/2-bevel, 0), (height/2, bevel)]
    rings = []
    for z, inset in profiles:
        rings.append([np.array((*p, z)) for p in outline(width-2*inset, depth-2*inset,
                                                       max(.02, radius-inset), segments)])
    count = len(rings[0])
    for bottom, top in zip(rings, rings[1:]):
        for i in range(count):
            points = [bottom[i], bottom[(i+1) % count], top[(i+1) % count], top[i]]
            wn = np.cross(points[1]-points[0], points[2]-points[0])
            face(m, paint, [centre+p@axes for p in points], wn@axes)
    for sign, ring in ((-1, rings[0]), (1, rings[-1])):
        face(m, paint, [centre+p@axes for p in ring], sign*UP@axes)


def turned(m, centre, axis, profile, paint='op_alloy', sides=16):
    """Smooth lathed hardware; caps are explicit and closed."""
    centre, axis = np.asarray(centre), K.normalise(axis)
    u = K.normalise(np.cross(axis, UP if abs(axis[2]) < .9 else (1, 0, 0)))
    v = np.cross(axis, u)
    rim = [u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides) for i in range(sides)]
    for (ra, za), (rb, zb) in zip(profile, profile[1:]):
        slope = K.normalise((zb-za, -(rb-ra), 0))
        for i in range(sides):
            da, db = rim[i], rim[(i+1) % sides]
            points = [centre+ra*da+za*axis, centre+ra*db+za*axis,
                      centre+rb*db+zb*axis, centre+rb*da+zb*axis]
            ns = [da*slope[0]+axis*slope[1], db*slope[0]+axis*slope[1]]
            face(m, paint, points, K.normalise(ns[0]+ns[1]), normals=[ns[0], ns[1], ns[1], ns[0]])
    for sign, (radius, z) in ((-1, profile[0]), (1, profile[-1])):
        face(m, paint, [centre+radius*d+z*axis for d in rim], axis*sign)


def tube(m, a, b, radius, paint='op_alloy', sides=12):
    a, b = np.asarray(a), np.asarray(b)
    turned(m, a, b-a, [(radius, 0), (radius, np.linalg.norm(b-a))], paint, sides)


def button(m, at, normal, radius=.18, paint='op_alloy', sides=8):
    at, normal = np.asarray(at), np.asarray(normal)
    turned(m, at, normal, [(radius*.84, 0), (radius, .035), (radius, .12)], paint, sides)


def transform(m, origin, axes):
    result = K.Model()
    origin, axes = np.asarray(origin), np.asarray(axes)
    for paint, faces in m.polygons.items():
        for index, (points, normal) in enumerate(faces):
            ns = m.polygon_normals.get((paint, index))
            result.polygon(paint, [origin+p@axes for p in points], normal@axes,
                           uv=m.polygon_uvs.get((paint, index)),
                           normals=None if ns is None else [n@axes for n in ns])
    return result


def chair(detail=1):
    m = K.Model()
    # Upholstery has gentle compression and a rolled front edge, not rigid slabs.
    def seat_shape(p):
        p[2] -= .30*math.exp(-(p[0]/7.2)**2-(p[1]/7.5)**2)*max(0., p[2]/1.9)
        p[2] -= p[1]*.025
        return p
    def back_shape(p):
        p[1] += .80*math.exp(-((p[2]+5.5)/4.5)**2)*max(0., p[1]/1.6)
        p[1] -= .115*p[2]
        return p
    soft_box(m, (0, 0, 21.3), (22., 21., 3.8), 'op_fabric', deform=seat_shape,
             uv_axes=(0, 1), detail=detail)
    soft_box(m, (0, -9.4, 36.5), (21.8, 3.2, 26.), 'op_fabric', deform=back_shape,
             uv_axes=(0, 2), detail=detail)
    soft_box(m, (0, -11.35, 36.5), (20.9, 1.1, 25.8), 'op_shell',
             deform=lambda p: p+np.array((0, -.115*p[2], 0)), detail=detail, power=.25)
    soft_box(m, (0, -.2, 19.4), (21.1, 19.4, 1.25), 'op_shell', detail=0, power=.30)
    # Tilt carrier, tension knob, height control and backrest spine.
    round_block(m, (0, -1., 17.3), (11.8, 11., 2.7), 'op_paint', 1.5, .25)
    beam(m, (0, -6.5, 17.9), (0, -11., 30.), (3.2, 1.5), 'op_paint', .22)
    turned(m, (0, 5., 16.8), (0, 1, 0), [(1.15, 0), (1.35, .2), (1.35, 2.), (1.1, 2.3)], 'op_shell', 16)
    beam(m, (-4., 1., 17.7), (-9., 3.3, 17.4), (.45, .35), 'op_paint', .07)
    soft_box(m, (-9.3, 3.4, 17.4), (1.6, 3., .65), 'op_shell', detail=0)
    turned(m, (0, 0, 5.7), UP, [(1.25, 0), (1.25, 12.8)], 'op_alloy', 20)
    turned(m, (0, 0, 4.1), UP, [(1.8, 0), (1.8, 6.8), (1.6, 7.)], 'op_shell', 20)
    turned(m, (0, 0, 3.6), UP, [(2.5, 0), (2.7, .5), (2.1, 2.5)], 'op_alloy', 20)
    for sign in (-1, 1):
        beam(m, (sign*10., -.5, 18.9), (sign*13.6, -.3, 26.6), (1.3, 1.1), 'op_alloy', .18)
        round_block(m, (sign*13.6, -.3, 27.4), (1.5, 2.2, 4.2), 'op_shell', .45, .15)
        soft_box(m, (sign*13.6, .2, 30.2), (3.3, 11.5, 1.65), 'op_shell', detail=0)
        button(m, (sign*14.45, -.1, 27.9), (sign, 0, 0), .32, 'op_paint')
    # Five spokes, swivelling forks and two independently visible wheels per caster.
    for i in range(5):
        angle = math.tau*i/5+.26
        along = np.array((math.cos(angle), math.sin(angle), 0))
        axle = np.array((-along[1], along[0], 0))
        tip = along*14.1+UP*4.2
        beam(m, along*1.3+UP*5.1, tip, (1.7, 1.15), 'op_alloy', .27)
        tube(m, tip-UP*.6, tip+UP*.35, .48, 'op_alloy', 10)
        wheel_c = along*14.55+UP*1.5
        beam(m, tip, wheel_c+UP*.55, (.9, .7), 'op_paint', .10)
        for sign in (-1, 1):
            c = wheel_c+axle*sign*.63
            turned(m, c-axle*.43, axle, [(1.20, 0), (1.5, .16), (1.5, .70), (1.2, .86)],
                   'op_shell', 16 if detail else 12)
            button(m, c+axle*sign*.45, axle*sign, .48, 'op_paint', 10)
    # A restrained upholstered edge welt follows the actual curved cushion shoulder.
    if detail:
        path = []
        phi = .30
        radius = math.cos(phi)**.38
        for i in range(48):
            a = i*math.tau/48
            p = np.array((11.*radius*signed_power(math.cos(a), .38),
                          10.5*radius*signed_power(math.sin(a), .38),
                          1.9*math.sin(phi)**.38))
            path.append(seat_shape(p)+np.array((0, 0, 21.3)))
        for a, b in zip(path, path[1:]+path[:1]):
            tube(m, a, b, .045, 'op_fabric', 6)
    return m


def screen(m, centre, width, height, index=0, detail=1):
    c = np.asarray(centre)
    # This housing is behind the display, with a real front-plane separation.
    axes = np.array(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    round_block(m, c+(0, .85, 0), (width+1.7, height+1.7, 1.7), 'op_shell',
                .8, .14, axes=axes, segments=5 if detail else 3)
    round_block(m, c+(0, 2., 0), (width*.72, height*.72, 1.0), 'op_paint',
                .8, .18, axes=axes)
    rim = outline(width, height, .32, 3)
    points = [c+np.array((x, -.025, y)) for x, y in rim]
    u, v = (index % 2)/2, 1-(index//2+1)/2
    uv = [(u+(x/width+.5)*.5, v+(y/height+.5)*.5) for x, y in rim]
    face(m, 'co_screens', points, (0, -1, 0), uv=uv)
    for x in (-3.9, 3.9):
        for z in (-3.9, 3.9):
            button(m, c+(x, 2.86, z), (0, 1, 0), .18)
    round_block(m, c+(0, 2.6, 0), (9.4, .5, 9.4), 'op_paint', .5, .12)
    if detail:
        for i in range(9):
            m.box(c+(-width*.30+i*1.5, 2.53, height*.26),
                  c+(-width*.30+i*1.5+.55, 2.59, height*.26+2.), 'co_rubber')
    # Tiny actual status lamp in the bezel, not a full emissive strip.
    m.box(c+(width/2-1.3, -.06, -height/2-.50), c+(width/2-.65, -.01, -height/2-.31), 'co_beam')


def key(m, x, y, units, label, axes, origin):
    width, depth = units*.86-.075, .76
    bottom = outline(width, depth, .10, 1)
    top = outline(width-.10, depth-.10, .08, 1)
    centre = np.array((x, y, .48))
    for i in range(len(bottom)):
        j = (i+1) % len(bottom)
        pts = [centre+np.array((*bottom[i], -.13)), centre+np.array((*bottom[j], -.13)),
               centre+np.array((*top[j], .13)), centre+np.array((*top[i], .13))]
        face(m, 'op_shell', [origin+p@axes for p in pts], np.cross(pts[1]-pts[0], pts[2]-pts[0])@axes)
    face(m, 'op_shell', [origin+(centre+np.array((*p, -.13)))@axes for p in bottom], -UP@axes)
    glyph = GLYPHS.index(label)
    uv = [((glyph % 8+(p[0]/max(width-.10, .1)+.5))/8,
           1-(glyph//8+1-(p[1]/(depth-.10)+.5))/GLYPH_ROWS) for p in top]
    face(m, 'op_keys', [origin+(centre+np.array((*p, .13)))@axes for p in top], UP@axes, uv=uv)


def keyboard(m, detail=1):
    origin = np.array((-1.8, 13., 35.15))
    axes = np.array(((1., 0, 0), (0, math.cos(.07), math.sin(.07)), (0, -math.sin(.07), math.cos(.07))))
    round_block(m, origin, (19.5, 6.8, .75), 'op_shell', .5, .12, axes=axes)
    rows = [list(zip('1234567890-=', [1]*12))+[('BKSP', 2)],
            [('TAB', 1.5)]+[(s, 1) for s in 'QWERTYUIOP[]']+[('FN', .5)],
            [('CAPS', 1.75)]+[(s, 1) for s in "ASDFGHJKL;'"]+[('ENTER', 1.25)],
            [('SHIFT', 2.25)]+[(s, 1) for s in 'ZXCVBNM,./']+[('SHIFT', 1.75)],
            [('CTRL', 1.5), ('ALT', 1.5), ('SPACE', 7.), ('ALT', 1.5), ('CTRL', 2.5)]]
    for row, keys in enumerate(rows):
        x = -8.8
        for label, units in keys:
            key(m, x+units*.86/2, (2-row)*.93, units, label, axes, origin)
            x += units*.86
    for row, labels in enumerate((('INS', 'HOME', 'PGUP'), ('DEL', 'END', 'PGDN'))):
        for col, label in enumerate(labels):
            key(m, 6.0+col*.93, (2-row)*.93, 1, label, axes, origin)
    for label, x, y in (('LT', 6.0, -2.25), ('DN', 6.93, -2.25), ('RT', 7.86, -2.25), ('UP', 6.93, -1.25)):
        key(m, x, y, 1, label, axes, origin)
    # Separate mouse and thin mat. The body has actual volume and a wheel.
    round_block(m, (14.4, 13., 34.63), (8.0, 9.4, .13), 'co_rubber', .65, .025)
    soft_box(m, (14.4, 13.3, 35.35), (2.65, 4.8, 1.42), 'op_shell', detail=0, power=.70)
    tube(m, (14.4, 14.25, 35.88), (14.4, 14.85, 35.88), .25, 'op_paint', 12)


def pedestal(m, x, detail):
    # Folded cabinet shell. The vent is a real opening in its service-door face.
    round_block(m, (x, 37., 3.), (16.2, 47., 5.), 'op_paint', .65, .25)
    for xx in (x-7.1, x+7.1):
        round_block(m, (xx, 37., 18.3), (1.3, 43.2, 29.), 'op_paint', .32, .10)
    round_block(m, (x, 58.1, 18.3), (14.5, 1.25, 29.), 'op_paint', .4, .12)
    round_block(m, (x, 37., 32.1), (15.5, 44., 1.25), 'op_paint', .45, .16)
    # Dark cavity is set back behind the cut slots, with frame/support strips.
    round_block(m, (x, 16.9, 17.9), (13.8, .55, 27.4), 'co_rubber', .3, .07)
    for a, b in ((5., 11.8), (18.5, 31.2)):
        round_block(m, (x, 15.7, (a+b)/2), (13.7, .7, b-a), 'op_paint', .25, .06)
    for xx in (x-6.45, x+6.45):
        round_block(m, (xx, 15.7, 15.15), (.8, .7, 6.8), 'op_paint', .12, .04)
    for z in np.linspace(12., 18.3, 7):
        round_block(m, (x, 15.7, z), (12.5, .7, .52), 'op_paint', .12, .04, segments=1)
    # Attached pull handle, screws and protective shoes.
    for xx in (x-2.7, x+2.7):
        tube(m, (xx, 15.4, 25.3), (xx, 14.3, 25.3), .22, 'op_alloy', 8)
    tube(m, (x-2.7, 14.3, 25.3), (x+2.7, 14.3, 25.3), .24, 'op_alloy', 12)
    if detail:
        for xx in (x-5.8, x+5.8):
            for zz in (6.4, 29.8):
                button(m, (xx, 15.30, zz), (0, -1, 0), .17)
    for yy in (17., 57.):
        round_block(m, (x, yy, .48), (12., 7., .96), 'co_rubber', .7, .14)


def desk(detail=1, index=0):
    m = K.Model()
    # Rounded slab, resilient front edging, supporting rails and service pedestals.
    round_block(m, (0, 32., 33.6), (118., 64., 1.8), 'op_worktop', 2.3, .28, segments=5)
    round_block(m, (0, 1.0, 33.4), (114.5, 2., 1.8), 'op_shell', .9, .25, segments=5)
    for x in (-49.2, 49.2):
        pedestal(m, x, detail)
    for y in (17., 55.):
        round_block(m, (0, y, 30.8), (101., 2.6, 2.8), 'op_paint', .5, .15)
    # Covered cable tray below the rear edge; small cables remain beneath the worktop.
    round_block(m, (0, 56.3, 27.5), (81., 6.4, 4.7), 'op_paint', .5, .14)
    for x in (-9., 20.):
        turned(m, (x, 49.8, 34.47), UP, [(1.05, 0), (1.05, .13), (.95, .2)], 'op_shell', 18)
    turned(m, (0, 48.8, 34.5), UP, [(3.1, 0), (3.1, .35), (2.8, .55)], 'op_alloy', 20)
    tube(m, (0, 48.8, 35.0), (0, 48.8, 42.8), .82, 'op_paint', 16)
    tube(m, (0, 48.8, 42.8), (0, 47.8, 50.8), .95, 'op_alloy', 16)
    tube(m, (0, 47.8, 50.8), (0, 44.9, 51.5), .83, 'op_paint', 16)
    for z in (42.8, 50.8):
        turned(m, (-1.25, 48.5 if z<45 else 47.8, z), (1, 0, 0),
               [(1.35, 0), (1.35, 2.5)], 'op_shell', 16)
    screen(m, (0, 43., 51.5), 48., 27., index, detail)
    keyboard(m, detail)
    # A restrained industrial control pod keeps the wide operator surface useful.
    pod_axes = np.array(((1, 0, 0), (0, math.cos(.14), math.sin(.14)), (0, -math.sin(.14), math.cos(.14))))
    pc = np.array((-35., 16., 35.9))
    round_block(m, pc, (16., 12.5, 2.6), 'op_paint', .9, .2, axes=pod_axes)
    for x in (-4.3, 0, 4.3):
        turned(m, pc+np.array((x, 1.8, 1.36))@pod_axes, UP@pod_axes,
               [(1., 0), (1.1, .25), (.95, 1.1)], 'op_shell', 14)
    for x in (-4., 0, 4.):
        round_block(m, pc+np.array((x, -3., 1.48))@pod_axes, (2.3, 1.7, .4),
                    'op_shell', .22, .06, axes=pod_axes)
    return m


def configure(m):
    for p in PAINTS:
        m.material_overrides[p] = f'{MATERIAL_DIR}/{p}.vmat'
        m.tile_overrides[p] = TILES[p]
    return m


def control_desk(m, side, n, z, collide=True):
    """Replace one authored operator station; surrounding room geometry is untouched."""
    detail = int(collide)
    frame = np.array(((0., -side, 0), (side, 0., 0), (0., 0., 1.)))
    origin = np.array((side*1810., n, z))
    index = int((n+200)//100) % 4
    m.extend(transform(desk(detail, index), origin, frame))
    angle = math.radians((-4., 4., 0.)[int(round((n+55)/150)) % 3] if collide else 0)
    rotation = np.array(((math.cos(angle), math.sin(angle), 0), (-math.sin(angle), math.cos(angle), 0), (0, 0, 1.)))
    seat = transform(chair(detail), (0, -21., 0), rotation)
    m.extend(transform(seat, origin, frame))
    if collide:
        # Only these twelve furniture-local boxes change; no new room blockers.
        m.collision_box((min(side*1810, side*1874), n-59, z),
                        (max(side*1810, side*1874), n+59, z+34.5), 'metal')
        m.collision_box((min(side*1771, side*1807), n-18, z),
                        (max(side*1771, side*1807), n+18, z+50), 'metal')
    configure(m)


def vmat(name, color, normal=None, rough=None, metal=0.):
    return ('// Tools/collider_operators.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            f'    TextureColor "{color}"\n'
            f'    TextureNormal "{normal or "materials/default/default_normal.tga"}"\n'
            f'    TextureRoughness "{rough or "[0.58 0.58 0.58 0]"}"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
            '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n}\n')


def materials(out):
    """Original mathematical PBR surfaces at physical scales, not image edits."""
    import ares_materials as AM
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = 1024
    rng = np.random.default_rng(27341)
    yy, xx = np.mgrid[:n, :n]
    x, y = xx/n, yy/n
    fine = rng.normal(0, 1, (n, n))
    # Interlaced upholstery threads, about 0.047 inches apart on a six-inch tile.
    threads = 128
    sx, sy = np.sin(math.tau*x*threads), np.sin(math.tau*y*threads)
    over = (np.floor(x*threads)+np.floor(y*threads)) % 2
    weave = np.where(over == 0, .68*sx+.20*sy, .20*sx+.68*sy)
    yarn = .35*np.sin(math.tau*(x+y)*threads*2)
    fabric = np.array((55., 57., 58.))[None, None, :]*(1+.11*weave[..., None]+.018*fine[..., None])
    maps = dict(op_fabric=(fabric, .0045*weave+.0007*yarn,
                          np.clip(.83+.035*weave+.008*fine, .72, .94), 0.))
    import scipy.ndimage as ndi
    broad = ndi.gaussian_filter(fine, 28, mode='wrap')
    broad /= max(float(broad.std()), 1e-9)
    for name, base, rough, height, metal in (
        ('op_shell', (47., 51., 54.), .48, .00055, 0.),
        ('op_worktop', (139., 142., 139.), .57, .0007, 0.),
        ('op_paint', (52., 58., 61.), .46, .0005, 0.),
        ('op_alloy', (160., 166., 169.), .32, .00016, .88),
    ):
        variation = .010*fine+.009*broad
        if name == 'op_alloy':
            variation += .012*np.sin(math.tau*y*145)
        color = np.array(base)[None, None, :]*(1+variation[..., None])
        maps[name] = (color, height*fine, np.clip(rough+.014*fine+.018*broad, .2, .9), metal)
    for name, (color, height, rough, metal) in maps.items():
        prefix = name.removeprefix('op_')
        Image.fromarray(np.clip(color, 0, 255).astype(np.uint8)).save(out/(prefix+'_color.png'))
        # AM.normals produces the GL convention already used by Collider's scan materials.
        normal = AM.normals(height, (n/TILES[name], n/TILES[name]))
        AM.BX.save_normal(out/(prefix+'_normal.png'), normal)
        AM.BX.save_grey(out/(prefix+'_rough.png'), rough)
        path = f'{MATERIAL_DIR}/{prefix}'
        (out/(name+'.vmat')).write_text(vmat(name, path+'_color.png', path+'_normal.png', path+'_rough.png', metal))
    assert len(GLYPHS) <= 8*GLYPH_ROWS
    atlas = Image.new('RGB', (1024, 128*GLYPH_ROWS), (48, 52, 55))
    draw = ImageDraw.Draw(atlas)
    fontpath = Path('C:/Windows/Fonts/arial.ttf')
    for i, label in enumerate(GLYPHS):
        size = 40 if len(label) == 1 else 19 if len(label) > 3 else 25
        font = ImageFont.truetype(str(fontpath), size)
        cx, cy = (i % 8)*128+64, (i//8)*128+64
        draw.text((cx, cy), label if label != 'SPACE' else '', font=font, anchor='mm', fill=(172, 179, 181))
    atlas.save(out/'key_legends.png')
    (out/'op_keys.vmat').write_text(vmat('op_keys', f'{MATERIAL_DIR}/key_legends.png'))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials', type=Path, required=True)
    materials(parser.parse_args().materials)
