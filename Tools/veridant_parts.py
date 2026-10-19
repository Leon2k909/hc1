"""
Veridant's pieces: what Tools/veridant_map.py builds the resort from, on map_kit's Model (plan coordinates: e east,
n north, z up, inches), with Tools/riverdale_parts.py's shapes (cards, rods, lathes, tubes) under them and
Tools/veridant_materials.py's vr_ paints on them.

- Stone stairs are solid steps (a honed limestone tread over a travertine riser) with a warm LED strip tucked under
  every nosing, as the picture's grand stair has, drawn over one wedge hull: the slope the navmesh walks.
- Balustrades are frameless glass (a steel shoe and a slim cap rail) or black steel bars; each run adds a player clip
  (CLIPS) the scene builds, so nobody walks off a terrace and bullets pass.
- Trees are built from crossed alpha-tested cards on the vr_foliage atlas over trunks of tapered tubes: olives in
  planters, the stone pine's flat umbrella crown, date palms' arching fronds.
- Lettering, the banner, the flag and the lounge's paintings are quads on the vr_letters_* / vr_print atlases, sized
  by their region's shape.
- Light fixtures (wall washers, step lights, uplights, lanterns, downlights) draw a housing and a lit lens and add a
  point light to LIGHTS, which the scene builds.
"""
import math

import numpy as np

import map_kit as K
import riverdale_parts as P
import veridant_materials as VM
from riverdale_parts import v, unit, card, box, obox, rod, UP

STONE, METAL, WOOD, PLASTIC, FABRIC = "default", "metal", "wood", "plastic", "fabric"

# riverdale_parts' shapes, for the map script.
cylinder, lathe, quad, pipe = P.cylinder, P.lathe, P.quad, P.pipe

CLIPS = P.CLIPS       # ( name, centre (plan), yaw degrees, ( length, thickness, height ) )
LIGHTS = P.LIGHTS     # ( name, position (plan), "r,g,b,1", radius, shadows )

# Lamp colours: warm 2700 K LEDs, brighter than white so they hold their own against the sunset at the scene's
# exposure (s&box's point lights read far dimmer than a renderer's).
# The lamps' light: dimmer than the fixtures look, so the light pools stay pools and the stone between them falls
# into the dusk, as in the picture (2026-10-15: at 1.75 the pylon and the grand stair read twice the picture's brightness).
WARM = "0.98,0.62,0.32,1"
WARM_SOFT = "0.70,0.44,0.23,1"
WARM_ROOM = "1.10,0.76,0.45,1"
RED = "1.6,0.10,0.06,1"


def reset():
    P.reset()


# ---------------------------------------------------------------------------------------------------------------------
# Atlas quads

def atlas_uvs( table, size, name, flip=False ):
    corners = ( ( 1, 0 ), ( 0, 0 ), ( 0, 1 ), ( 1, 1 ) ) if flip else ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) )
    return [ VM.atlas_uv( table, size, name, s, t ) for s, t in corners ]


def sheet( m, paint, table, size, name, centre, right, up, h, w=None, off=0.0, both=False, flip=False ):
    """ A picture from an atlas on a quad h tall (w wide, else by its region's shape), facing cross( right, up ). """
    right, up = unit( right ), unit( up )
    w = w if w is not None else h * VM.aspect( table, name )
    out = np.cross( right, up )
    c = v( *centre ) + out * off
    pts = [ c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2 ]
    m.polygon( paint, pts, normal=out, both_sides=both, uv=atlas_uvs( table, size, name, flip ) )


def letters( m, name, centre, right, h, tone="dark", off=0.3, up=UP ):
    """ Cut lettering or the mark (VM.LETTERS), h tall, on the face whose right is right. """
    sheet( m, f"vr_letters_{tone}", VM.LETTERS, VM.LETTER_ATLAS, name, centre, right, up, h, off=off )


def picture( m, name, centre, right, h, w=None, off=0.3, up=UP, both=False ):
    """ A printed thing from VM.PRINTS: the banner, the flag, a painting, a sign. """
    sheet( m, "vr_print", VM.PRINTS, VM.PRINT_ATLAS, name, centre, right, up, h, w, off, both )


def leaves( m, name, centre, right, up, h, w=None, flip=False ):
    """ A foliage card (VM.FOLIAGE), seen from both sides. """
    sheet( m, "vr_foliage", VM.FOLIAGE, VM.FOLIAGE_ATLAS, name, centre, right, up, h, w, 0.0, True, flip )


def frame_vectors( out ):
    """ right and up for a quad facing out (plan vector; level unless out is nearly vertical). """
    out = unit( out )
    right = np.cross( UP, out )
    if np.linalg.norm( right ) < 1e-6:
        right = v( 1, 0, 0 )
    right = unit( right )
    return right, np.cross( out, right )


# ---------------------------------------------------------------------------------------------------------------------
# Tubes, trunks

def tube( m, pts, radii, paint, sides=8, cap=False, smooth=True ):
    """ A round tube along the polyline pts with a radius per point, parallel-transported frames. """
    pts = [ v( *p ) for p in pts ]
    if len( pts ) < 2:
        return
    tangents = []
    for k in range( len( pts ) ):
        a, b = pts[max( 0, k - 1 )], pts[min( len( pts ) - 1, k + 1 )]
        tangents.append( unit( b - a ) )
    u, _ = P.perp( tangents[0] )
    rings = []
    for p, t, r in zip( pts, tangents, radii ):
        u = unit( u - np.dot( u, t ) * t )
        if np.linalg.norm( u ) < 1e-6:
            u, _ = P.perp( t )
        w = np.cross( t, u )
        dirs = [ u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
        rings.append( ( p, dirs, r ) )
    for ( pa, da, ra ), ( pb, db, rb ) in zip( rings, rings[1:] ):
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            quad = [ pa + da[k] * ra, pa + da[k1] * ra, pb + db[k1] * rb, pb + db[k] * rb ]
            card( m, paint, quad, da[k] + da[k1] + db[k] + db[k1], normals=[ da[k], da[k1], db[k1], db[k] ] if smooth else None )
    if cap:
        p, d, r = rings[-1]
        card( m, paint, [ p + x * r for x in d ], tangents[-1] )


def bent( a, b, bend, steps=4, rng=None, wobble=0.0 ):
    """ Points from a to b, bowed sideways by bend (a plan vector at the middle), with an optional wobble. """
    a, b = v( *a ), v( *b )
    out = []
    for s in range( steps + 1 ):
        f = s / steps
        p = a + ( b - a ) * f + v( *bend ) * math.sin( math.pi * f )
        if rng is not None and 0 < s < steps:
            p = p + rng.normal( 0, wobble, 3 )
        out.append( p )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Stairs, balustrades

def stone_stair( m, foot, head, width, z0, z1, tread="vr_stone_light", riser="vr_stone", side="vr_stone", led=True,
                 sides=( True, True ), surface=STONE, going=11.0, name="stair" ):
    """ A straight flight of solid stone steps from foot (plan: the bottom nosing's middle) to head (the top nosing's
    middle), width across. Each tread overhangs its riser by an inch with a warm LED strip under the nosing. One wedge
    hull carries walking. sides: which ends of the steps are drawn (False where they butt a wall). Returns the riser. """
    foot, head = v( foot[0], foot[1], 0 ), v( head[0], head[1], 0 )
    along = head - foot
    run = float( np.linalg.norm( along ) )
    d = along / run
    s = np.cross( UP, d ) * ( width / 2 )
    steps = max( 2, int( round( ( z1 - z0 ) / 7.4 ) ) )
    rise, go = ( z1 - z0 ) / steps, run / steps
    for i in range( steps ):
        p = foot + d * ( go * i )
        q = p + d * go
        zt = z0 + rise * ( i + 1 )
        lip = d * 1.0
        # The tread: a slab 1.5 thick whose front overhangs the riser by an inch.
        card( m, tread, [ p - lip - s + UP * zt, q - s + UP * zt, q + s + UP * zt, p - lip + s + UP * zt ], UP )
        card( m, tread, [ p - lip - s + UP * ( zt - 1.5 ), p - lip + s + UP * ( zt - 1.5 ), p - lip + s + UP * zt, p - lip - s + UP * zt ], -d )
        card( m, tread, [ p - lip - s + UP * ( zt - 1.5 ), p - s + UP * ( zt - 1.5 ), p + s + UP * ( zt - 1.5 ), p - lip + s + UP * ( zt - 1.5 ) ], -UP )
        # The riser, set back under the nosing, and the LED strip along its top.
        card( m, riser, [ p - s + UP * ( zt - rise ), p + s + UP * ( zt - rise ), p + s + UP * ( zt - 1.5 ), p - s + UP * ( zt - 1.5 ) ], -d )
        if led:
            card( m, "vr_led", [ p - s * 0.98 - d * 0.05 + UP * ( zt - 2.6 ), p + s * 0.98 - d * 0.05 + UP * ( zt - 2.6 ),
                                 p + s * 0.98 - d * 0.05 + UP * ( zt - 1.6 ), p - s * 0.98 - d * 0.05 + UP * ( zt - 1.6 ) ], -d )
        for sgn, want in zip( ( -1, 1 ), sides ):
            if want:
                o = s * sgn
                card( m, side, [ p + o + UP * z0, q + o + UP * z0, q + o + UP * zt, p + o + UP * zt ], o )
    lo = [ foot - s - d * 2 + UP * z0, foot + s - d * 2 + UP * z0, head - s + UP * z0, head + s + UP * z0 ]
    hi = [ head - s + d * 1 + UP * z1, head + s + d * 1 + UP * z1, foot - s - d * 2 + UP * ( z0 + 0.5 ), foot + s - d * 2 + UP * ( z0 + 0.5 ) ]
    m.hull( lo + hi + [ head - s + d + UP * z0, head + s + d + UP * z0 ], surface )
    return rise


def clip( name, a, b, z0, z1, thick=4.0 ):
    P.clip( name, a, b, z0, z1, thick )


def glass_rail( m, pts, z, height=42.0, clip_to=72.0, name="glass rail", panel=48.0, slope=None, cap=True ):
    """ A frameless glass balustrade along plan pts at floor height z (or a z per point): a steel shoe, toughened glass
    panels with a small gap between them, a slim steel cap rail. Drawn only, with a player clip (none if clip_to is
    None). """
    pts = [ v( p[0], p[1], 0.0 ) for p in pts ]
    zs = slope if slope is not None else [ z ] * len( pts )
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        za, zb = zs[k], zs[k + 1]
        dvec = b - a
        L = float( np.linalg.norm( dvec ) )
        if L < 1:
            continue
        d = dvec / L
        side = np.cross( UP, d )
        # The shoe: a low steel channel.
        for sg in ( -1, 1 ):
            o = side * 1.6 * sg
            card( m, "vr_steel", [ a + o + UP * za, b + o + UP * zb, b + o + UP * ( zb + 4 ), a + o + UP * ( za + 4 ) ], o )
        card( m, "vr_steel", [ a - side * 1.6 + UP * ( za + 4 ), b - side * 1.6 + UP * ( zb + 4 ), b + side * 1.6 + UP * ( zb + 4 ),
                               a + side * 1.6 + UP * ( za + 4 ) ], UP )
        count = max( 1, int( round( L / panel ) ) )
        for i in range( count ):
            f0, f1 = i / count, ( i + 1 ) / count
            p0 = a + dvec * f0 + d * 0.4
            p1 = a + dvec * f1 - d * 0.4
            z_0 = za + ( zb - za ) * f0
            z_1 = za + ( zb - za ) * f1
            for sg in ( -1, 1 ):
                o = side * 0.3 * sg
                card( m, "vr_glass_clear", [ p0 + o + UP * ( z_0 + 3 ), p1 + o + UP * ( z_1 + 3 ), p1 + o + UP * ( z_1 + height - 1.5 ),
                                             p0 + o + UP * ( z_0 + height - 1.5 ) ], o )
        if cap:
            rod( m, a + UP * ( za + height - 0.6 ), b + UP * ( zb + height - 0.6 ), 1.0, "vr_steel", 6 )
        if clip_to is not None:
            clip( name, a, b, min( za, zb ), max( za, zb ) + clip_to )


def steel_rail( m, pts, z, height=42.0, clip_to=72.0, name="steel rail", bars=11.0, slope=None, style="bars" ):
    """ A black steel balustrade. style "bars": square posts every 48, a flat top rail, a bottom rail and flat bars
    between them. "rails": the picture's light one, round posts every 54 with a round top rail and a middle rail.
    "tube": a heavy frame of 3 in square tube, posts every 72, a top rail and a kick rail. """
    if style != "bars":
        return _rail( m, pts, z, height, clip_to, name, slope, style )
    pts = [ v( p[0], p[1], 0.0 ) for p in pts ]
    zs = slope if slope is not None else [ z ] * len( pts )
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        za, zb = zs[k], zs[k + 1]
        dvec = b - a
        L = float( np.linalg.norm( dvec ) )
        if L < 1:
            continue
        d = dvec / L
        side = np.cross( UP, d )
        A, B = a + UP * za, b + UP * zb
        m.beam( A + UP * ( height - 0.8 ), B + UP * ( height - 0.8 ), ( 2.4, 1.6 ), "vr_steel" )
        m.beam( A + UP * 4, B + UP * 4, ( 1.4, 1.2 ), "vr_steel" )
        posts = max( 1, int( math.ceil( L / 48.0 ) ) )
        for i in range( posts + 1 ):
            f = i / posts
            p = a + dvec * f
            zp = za + ( zb - za ) * f
            obox( m, p + UP * ( zp + height / 2 ), d, ( 2.0, 2.0, height ), "vr_steel" )
        count = int( L / bars )
        for i in range( 1, count ):
            f = i / count
            p = a + dvec * f
            zp = za + ( zb - za ) * f
            obox( m, p + UP * ( zp + 4 + ( height - 5.6 ) / 2 ), d, ( 0.5, 1.0, height - 5.6 ), "vr_steel" )
        if clip_to is not None:
            clip( name, a, b, min( za, zb ), max( za, zb ) + clip_to )


def _rail( m, pts, z, height, clip_to, name, slope, style ):
    pts = [ v( p[0], p[1], 0.0 ) for p in pts ]
    zs = slope if slope is not None else [ z ] * len( pts )
    heavy = style == "tube"
    spacing = 72.0 if heavy else 54.0
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        za, zb = zs[k], zs[k + 1]
        dvec = b - a
        L = float( np.linalg.norm( dvec ) )
        if L < 1:
            continue
        d = dvec / L
        A, B = a + UP * za, b + UP * zb
        if heavy:
            m.beam( A + UP * ( height - 1.5 ), B + UP * ( height - 1.5 ), ( 3.0, 3.0 ), "vr_steel" )
            m.beam( A + UP * 7, B + UP * 7, ( 2.0, 2.0 ), "vr_steel" )
        else:
            rod( m, A + UP * ( height - 0.8 ), B + UP * ( height - 0.8 ), 0.85, "vr_steel", 6 )
            rod( m, A + UP * ( height * 0.52 ), B + UP * ( height * 0.52 ), 0.45, "vr_steel", 5 )
        posts = max( 1, int( math.ceil( L / spacing ) ) )
        for i in range( posts + 1 ):
            f = i / posts
            p = a + dvec * f
            zp = za + ( zb - za ) * f
            if heavy:
                obox( m, p + UP * ( zp + height / 2 ), d, ( 3.0, 3.0, height ), "vr_steel" )
            else:
                rod( m, p + UP * zp, p + UP * ( zp + height - 0.8 ), 0.7, "vr_steel", 6 )
        if clip_to is not None:
            clip( name, a, b, min( za, zb ), max( za, zb ) + clip_to )


def tarp_over( m, a, b, top, out, drop_out=30.0, drop_in=12.0, folds=4, seed=0, rail=1.6 ):
    """ A canvas tarp thrown over a rail from a to b (plan) whose top is at top: over the rail and hanging drop_out
    down its out side and drop_in down its near side. The cloth hangs in vertical folds that deepen towards the hem,
    the hem uneven and the ends dropping lower, shaded smooth. Drawn only. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    out = unit( v( out[0], out[1], 0 ) )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    cols = max( 12, int( L / 2.2 ) )
    us = np.linspace( 0.0, 1.0, cols + 1 )
    # Folds: three wavelengths at random phases; the hem's own wave; the ends sag.
    waves = [ ( rng.uniform( 7, 11 ), rng.uniform( 0, 6.3 ), 1.0 ), ( rng.uniform( 14, 22 ), rng.uniform( 0, 6.3 ), 0.8 ),
              ( rng.uniform( 3.5, 5.5 ), rng.uniform( 0, 6.3 ), 0.35 ) ]

    def fold( u ):
        x = u * L
        return sum( w * math.sin( 2 * math.pi * x / lam + ph ) for lam, ph, w in waves ) / 2.15

    def hang( u, drop ):
        end = max( 0.0, 1.0 - min( u, 1 - u ) * L / 18.0 )
        return drop * ( 0.86 + 0.14 * math.sin( u * L / 13.0 + 1.3 ) + 0.18 * end )

    # Across the rail: from the near hem up to the top, round the rail, down to the out hem. s: offset along out.
    rows = 14
    grid = []
    for u in us:
        p = a + d * ( L * u )
        f = fold( u )
        col = []
        hi_in, hi_out = hang( u, drop_in ), hang( u, drop_out )
        for k in range( rows + 1 ):
            t = k / rows
            if t < 0.36:
                g = t / 0.36                          # 0 at the near hem, 1 at the rail's near edge
                depth = ( 1.0 - g ) ** 1.2
                s_ = -( rail + 0.9 + depth * 1.6 + f * 1.8 * depth )
                zz = top - hi_in * ( 1.0 - g ) ** 1.05
            elif t < 0.64:
                g = ( t - 0.36 ) / 0.28                # round the rail
                ang = math.pi * ( 1.0 - g )
                s_ = math.cos( ang ) * ( rail + 0.9 )
                zz = top - rail * 0.4 + math.sin( ang ) * ( rail * 0.4 + 1.0 ) + f * 0.15
            else:
                g = ( t - 0.64 ) / 0.36                # 0 at the rail's out edge, 1 at the out hem
                depth = g ** 1.1
                s_ = rail + 0.9 + depth * 2.4 + f * 2.6 * depth
                zz = top - hi_out * g ** 1.02
            col.append( p + out * s_ + UP * zz )
        grid.append( col )
    G = np.array( grid )
    tu = np.gradient( G, axis=0 )
    tv = np.gradient( G, axis=1 )
    nrm = np.cross( tv, tu )
    # Face away from the rail on both sides: the cloth's outer surface.
    for i in range( G.shape[0] ):
        for k in range( G.shape[1] ):
            centre = a + d * ( L * us[i] ) + UP * ( top - rail * 0.4 )
            if np.dot( nrm[i, k], G[i, k] - centre ) < 0:
                nrm[i, k] = -nrm[i, k]
    nrm = nrm / np.maximum( np.linalg.norm( nrm, axis=-1, keepdims=True ), 1e-9 )
    for i in range( G.shape[0] - 1 ):
        for k in range( G.shape[1] - 1 ):
            quad = [ G[i, k], G[i + 1, k], G[i + 1, k + 1], G[i, k + 1] ]
            ns = [ nrm[i, k], nrm[i + 1, k], nrm[i + 1, k + 1], nrm[i, k + 1] ]
            towards = sum( ns )
            card( m, "vr_tarp", quad, towards, normals=ns )
            card( m, "vr_tarp", quad, -towards, normals=[ -n for n in ns ] )


def _old_tarp_over( m, a, b, top, out, drop_out=30.0, drop_in=12.0, folds=4, seed=0 ):
    """ A canvas tarp thrown over a rail from a to b (plan) whose top is at top: it hangs drop_out down the out side
    and drop_in down the near side, in folds. Drawn only. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    out = unit( v( out[0], out[1], 0 ) )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    n = max( 6, folds * 4 )
    rows = []
    for i in range( n + 1 ):
        f = i / n
        wave = math.sin( f * folds * math.pi * 2 + rng.uniform( 0, 0.3 ) ) * 2.2
        hang = 1.0 - 0.35 * abs( math.sin( f * math.pi ) ) * rng.uniform( 0.6, 1.0 )
        p = a + d * ( L * f )
        rows.append( [ p - out * ( 2.5 + wave * 0.4 ) + UP * ( top - drop_in * hang ), p - out * 1.6 + UP * ( top + 0.8 ),
                       p + out * 1.6 + UP * ( top + 0.8 ), p + out * ( 3.0 + wave ) + UP * ( top - drop_out * hang ),
                       p + out * ( 5.0 + wave * 1.4 ) + UP * ( top - drop_out * hang - 6 ) ] )
    for r0, r1 in zip( rows, rows[1:] ):
        for k in range( len( r0 ) - 1 ):
            m.polygon( "vr_tarp", [ r0[k], r1[k], r1[k + 1], r0[k + 1] ], both_sides=True )


# ---------------------------------------------------------------------------------------------------------------------
# Lights

def led( m, a, b, out, h=0.8, paint="vr_led" ):
    """ A self-lit LED strip from a to b (plan points with z), h tall, facing out. """
    a, b = v( *a ), v( *b )
    out = unit( out )
    d = unit( b - a )
    up = unit( np.cross( out, d ) )
    if up[2] < 0 or ( abs( up[2] ) < 1e-6 and np.dot( up, v( 0, 0, 1 ) ) < 0 ):
        up = -up
    card( m, paint, [ a - up * h / 2, b - up * h / 2, b + up * h / 2, a + up * h / 2 ], out )


def wall_washer( m, name, at, out, radius=260, light=True, size=( 9.0, 4.5 ), colour=WARM, rise=10.0, shadows=False ):
    """ A small recessed light in a wall facing out (its lens a lit slot), washing light along the floor or up the
    wall: the picture's lit rectangles at the foot of every wall. at is the lens's middle. """
    out = unit( v( out[0], out[1], 0 ) )
    right = np.cross( UP, out )
    c = v( *at ) + out * 0.25
    w, h = size
    P.quad( m, "vr_dark", c, right, UP, w + 2.0, h + 2.0, off=0.0 )
    P.quad( m, "vr_lamp", c + out * 0.1, right, UP, w, h, off=0.0 )
    if light:
        LIGHTS.append( ( name, tuple( c + out * 16 + UP * rise ), colour, radius, shadows ) )


def step_light( m, name, at, out, light=True, radius=120 ):
    wall_washer( m, name, at, out, radius, light, size=( 7.0, 2.8 ), colour=WARM_SOFT, rise=-4 )


def downlight( m, name, at, radius=300, light=True, colour=WARM_ROOM, shadows=False ):
    """ A downlight set in a ceiling at at (its face): a lit disc, a light under it. """
    c = v( *at )
    P.cylinder( m, ( c[0], c[1] ), 4.2, c[2] - 0.4, c[2], "vr_dark", 12, bottom="vr_dark" )
    card( m, "vr_lamp", [ c + v( 3.2 * math.cos( a ), 3.2 * math.sin( a ), -0.45 ) for a in np.linspace( 0, 2 * math.pi, 12, endpoint=False ) ], -UP )
    if light:
        LIGHTS.append( ( name, tuple( c - UP * 22 ), colour, radius, shadows ) )


def uplight( m, name, at, radius=220, colour=WARM, light=True ):
    """ A ground uplight: a lit disc in the floor or a planter's soil, its light just over it. """
    c = v( *at )
    card( m, "vr_lamp", [ c + v( 2.6 * math.cos( a ), 2.6 * math.sin( a ), 0.25 ) for a in np.linspace( 0, 2 * math.pi, 10, endpoint=False ) ], UP )
    if light:
        LIGHTS.append( ( name, tuple( c + UP * 24 ), colour, radius, False ) )


def lantern_post( m, name, base, h=132.0, light=True, radius=420 ):
    """ A promenade lamp post: a black steel column, a box lantern with lit glass. """
    b = v( *base )
    P.cylinder( m, ( b[0], b[1] ), 4.5, b[2], b[2] + 10, "vr_steel", 10, top="vr_steel", surface=METAL )
    P.cylinder( m, ( b[0], b[1] ), 2.2, b[2] + 10, b[2] + h - 16, "vr_steel", 8, surface=METAL )
    top = b + UP * ( h - 16 )
    box( m, top[0] - 6, top[0] + 6, top[1] - 6, top[1] + 6, top[2], top[2] + 2, "vr_steel" )
    for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ):
        box( m, top[0] + sx * 5.2 - 0.6, top[0] + sx * 5.2 + 0.6, top[1] + sy * 5.2 - 0.6, top[1] + sy * 5.2 + 0.6, top[2] + 2, top[2] + 14, "vr_steel" )
    box( m, top[0] - 4.6, top[0] + 4.6, top[1] - 4.6, top[1] + 4.6, top[2] + 2, top[2] + 14, "vr_lamp" )
    P.lathe( m, top, [ ( 7.5, top[2] + 14 ), ( 6.0, top[2] + 16 ), ( 0.5, top[2] + 19 ), ( 0.0, top[2] + 19.5 ) ], "vr_steel", 4 )
    if light:
        LIGHTS.append( ( name, tuple( top + UP * 8 ), WARM, radius, False ) )


# ---------------------------------------------------------------------------------------------------------------------
# Trees and plants

def random_frame( rng, out, tilt=0.6 ):
    out = unit( out + rng.normal( 0, tilt, 3 ) * v( 1, 1, 0.5 ) )
    right, up = frame_vectors( out )
    roll = rng.normal( 0, 0.35 )
    r2 = right * math.cos( roll ) + up * math.sin( roll )
    u2 = np.cross( out, r2 )
    return r2, u2


def olive( m, base, h=150.0, seed=0, spread=1.0, cards=22, leaf_scale=1.0 ):
    """ An olive: two or three twisting grey stems from the base, limbs fanning out, a loose silver-green crown of
    crossed leaf cards. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    b = v( *base )
    crown = b + UP * ( h * 0.66 )
    stems = int( rng.integers( 2, 4 ) )
    for k in range( stems ):
        ang = 2 * math.pi * k / stems + rng.uniform( -0.5, 0.5 )
        lean = v( math.cos( ang ), math.sin( ang ), 0 ) * ( h * rng.uniform( 0.08, 0.16 ) * spread )
        top = b + lean + UP * ( h * rng.uniform( 0.42, 0.55 ) )
        pts = bent( b + lean * 0.1, top, lean * 0.2 + v( *rng.normal( 0, h * 0.03, 2 ), 0 ), 4, rng, h * 0.012 )
        r0 = h * rng.uniform( 0.035, 0.05 )
        tube( m, pts, [ r0 * ( 1.0 - 0.45 * i / 4 ) for i in range( 5 ) ], "vr_bark", 7 )
        for j in range( int( rng.integers( 2, 4 ) ) ):
            a2 = ang + rng.uniform( -1.0, 1.0 )
            reach = v( math.cos( a2 ), math.sin( a2 ), 0 ) * ( h * rng.uniform( 0.15, 0.32 ) * spread )
            tip = top + reach + UP * ( h * rng.uniform( 0.12, 0.28 ) )
            tube( m, bent( top, tip, UP * ( h * 0.04 ), 3 ), [ r0 * 0.5, r0 * 0.38, r0 * 0.26, r0 * 0.15 ], "vr_bark", 5 )
    radii = v( h * 0.42 * spread, h * 0.42 * spread, h * 0.26 )
    for i in range( cards ):
        dirn = unit( rng.normal( 0, 1, 3 ) * v( 1, 1, 0.7 ) + UP * 0.25 )
        c = crown + dirn * radii * rng.uniform( 0.25, 0.95 )
        size = h * rng.uniform( 0.38, 0.56 ) * ( 0.85 + 0.3 * spread ) / 1.15 * leaf_scale
        right, up = random_frame( rng, v( dirn[0], dirn[1], 0 ) if np.linalg.norm( dirn[:2] ) > 0.2 else v( 1, 0, 0 ), 0.7 )
        leaves( m, "olive", c, right, up, size )


def planter( m, lo, hi, z0, top, paint="vr_stone", coping="vr_stone_dark", soil=True, surface=STONE, sides=None ):
    """ A stone planter box from lo to hi (plan e, n), z0 up to top, a coping, soil 4 under its rim. sides: faces to
    skip (against a wall). """
    e0, n0 = lo
    e1, n1 = hi
    paints = { "default": paint, "+z": None, "-z": None }
    for f in sides or ():
        paints[f] = None
    t = 6.0
    for a, b, c, d in ( ( e0, e1, n0, n0 + t ), ( e0, e1, n1 - t, n1 ), ( e0, e0 + t, n0 + t, n1 - t ), ( e1 - t, e1, n0 + t, n1 - t ) ):
        box( m, a, b, c, d, z0, top, paints )
    # The coping round the rim, proud by an inch.
    for a, b, c, d in ( ( e0 - 1, e1 + 1, n0 - 1, n0 + t ), ( e0 - 1, e1 + 1, n1 - t, n1 + 1 ), ( e0 - 1, e0 + t, n0 + t, n1 - t ),
                        ( e1 - t, e1 + 1, n0 + t, n1 - t ) ):
        box( m, a, b, c, d, top, top + 2.5, { "default": coping, "-z": coping } )
    if soil:
        box( m, e0 + t, e1 - t, n0 + t, n1 - t, z0, top - 4, { "default": None, "+z": "vr_soil" } )
    m.collision_box( ( e0, n0, z0 ), ( e1, n1, top + 2.5 ), surface )


def shrubs( m, lo, hi, z, seed=0, kind="shrub", h=26.0, count=None ):
    """ A bed of low plants: crossed cards over an area (plan lo..hi) at floor z. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    e0, n0 = lo
    e1, n1 = hi
    count = count or max( 2, int( ( e1 - e0 ) * ( n1 - n0 ) / 900 ) )
    for _ in range( count ):
        c = v( rng.uniform( e0 + 4, e1 - 4 ), rng.uniform( n0 + 4, n1 - 4 ), z + h * 0.45 )
        hh = h * rng.uniform( 0.7, 1.2 )
        for k in range( 2 ):
            ang = rng.uniform( 0, math.pi ) + k * math.pi / 2
            right = v( math.cos( ang ), math.sin( ang ), 0 )
            leaves( m, kind, c, right, UP, hh, hh * VM.aspect( VM.FOLIAGE, kind ) )


def stone_pine( m, base, h=560.0, crown_r=230.0, seed=0, lean=( 0.0, 0.0 ) ):
    """ An Italian stone pine: a tall bare trunk with reddish plates, forking near the top into limbs, under the
    species' flat umbrella crown: needle-tuft cards laid nearly level in a broad disc, with standing ones round its
    rim for the silhouette and a dark underside. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    b = v( *base )
    fork = b + v( lean[0], lean[1], 0 ) + UP * ( h * 0.62 )
    tube( m, bent( b, fork, v( lean[0] * 0.3, lean[1] * 0.3, 0 ) + v( *rng.normal( 0, 8, 2 ), 0 ), 5, rng, 2.0 ),
          [ 11.0, 9.6, 8.6, 7.8, 7.0, 6.4 ], "vr_bark", 9 )
    crown = b + v( lean[0] * 1.2, lean[1] * 1.2, 0 ) + UP * ( h * 0.84 )
    limbs = []
    for k in range( 5 ):
        ang = 2 * math.pi * k / 5 + rng.uniform( -0.3, 0.3 )
        tip = crown + v( math.cos( ang ), math.sin( ang ), 0 ) * ( crown_r * rng.uniform( 0.45, 0.7 ) ) - UP * ( h * 0.04 )
        tube( m, bent( fork, tip, UP * ( h * 0.05 ), 3 ), [ 5.5, 4.4, 3.4, 2.4 ], "vr_bark", 6 )
        limbs.append( tip )
    # The underside: a dark ragged disc.
    ring = [ crown + v( math.cos( a ), math.sin( a ), 0 ) * ( crown_r * ( 0.82 + 0.1 * math.sin( 3 * a + seed ) ) ) - UP * ( h * 0.03 )
             for a in np.linspace( 0, 2 * math.pi, 18, endpoint=False ) ]
    card( m, "vr_pine_dark", ring[::-1], -UP )
    card( m, "vr_pine_dark", ring, UP )
    for i in range( 54 ):
        r = crown_r * math.sqrt( rng.uniform( 0.0, 1.0 ) )
        a = rng.uniform( 0, 2 * math.pi )
        c = crown + v( math.cos( a ) * r, math.sin( a ) * r, rng.uniform( -0.02, 0.06 ) * h )
        w = crown_r * rng.uniform( 0.7, 1.1 )
        yaw = rng.uniform( 0, 2 * math.pi )
        right = v( math.cos( yaw ), math.sin( yaw ), 0 )
        tilt = rng.uniform( 0.15, 0.55 )
        side = np.cross( UP, right )
        up = unit( side * math.cos( tilt ) + UP * math.sin( tilt ) )
        leaves( m, "pine", c, right, up, w * 0.5, w )
    for i in range( 22 ):
        a = 2 * math.pi * i / 22 + rng.uniform( -0.1, 0.1 )
        c = crown + v( math.cos( a ), math.sin( a ), 0 ) * ( crown_r * rng.uniform( 0.8, 1.02 ) ) + UP * ( h * rng.uniform( -0.01, 0.05 ) )
        right = v( -math.sin( a ), math.cos( a ), 0 )
        w = crown_r * rng.uniform( 0.6, 0.9 )
        leaves( m, "pine", c, right, UP, w * 0.42, w )


def palm( m, base, h=380.0, seed=0, lean=( 0.0, 0.0 ), fronds=20, frond=150.0 ):
    """ Date palm with tapered, individually curved fronds rather than three wide paddle cards. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    b = v( *base )
    top = b + v( lean[0], lean[1], 0 ) + UP * h
    pts = bent( b, top, v( lean[0] * 0.25, lean[1] * 0.25, 0 ), 6 )
    tube( m, pts, [ 13.0, 11.5, 10.8, 10.2, 9.8, 9.6, 10.6 ], "vr_palm_bark", 10 )
    P.lathe( m, top, [ ( 10.6, top[2] ), ( 13.0, top[2] + 10 ), ( 8.0, top[2] + 22 ), ( 0.0, top[2] + 26 ) ], "vr_olive_mass", 8 )
    for i in range( fronds ):
        ang = 2 * math.pi * i / fronds + rng.uniform( -0.15, 0.15 )
        dirn = v( math.cos( ang ), math.sin( ang ), 0 )
        rise = rng.uniform( -0.24, 0.65 )
        L = frond * rng.uniform( 0.8, 1.15 )
        start = top + UP * 16 + dirn * 6
        # A continuous spline-like arc: slight lift by the crown, long downturned
        # tips, and a different elevation for each leaf. Each strip maps only its
        # own region of the frond atlas; no texture is stretched over the whole arc.
        segments = 7
        points = []
        for k in range( segments + 1 ):
            t = k / segments
            radial = L * ( 0.96 * t + 0.04 * math.sin( math.pi * t ) )
            z = L * ( 0.22 * math.sin( math.pi * t ) + rise * 0.22 * t - 0.36 * t * t )
            points.append( start + dirn * radial + UP * z )
        across = unit( np.cross( UP, dirn ) )
        twist = rng.uniform( -0.15, 0.15 )
        for k in range( segments ):
            t0, t1 = k / segments, ( k + 1 ) / segments
            a, c = points[k], points[k + 1]
            width0 = max( 1.8, 26.0 * math.sin( math.pi * ( 0.04 + 0.92 * t0 ) ) ** 0.78 )
            width1 = max( 1.8, 26.0 * math.sin( math.pi * ( 0.04 + 0.92 * t1 ) ) ** 0.78 )
            side0 = unit( across + UP * ( twist + 0.16 * t0 ) )
            side1 = unit( across + UP * ( twist + 0.16 * t1 ) )
            quad = [ a - side0 * width0, c - side1 * width1,
                     c + side1 * width1, a + side0 * width0 ]
            uv = [ VM.atlas_uv( VM.FOLIAGE, VM.FOLIAGE_ATLAS, "palm", t0, 0 ),
                   VM.atlas_uv( VM.FOLIAGE, VM.FOLIAGE_ATLAS, "palm", t1, 0 ),
                   VM.atlas_uv( VM.FOLIAGE, VM.FOLIAGE_ATLAS, "palm", t1, 1 ),
                   VM.atlas_uv( VM.FOLIAGE, VM.FOLIAGE_ATLAS, "palm", t0, 1 ) ]
            m.polygon( "vr_foliage", quad, both_sides=True, uv=uv )


def ivy( m, at, right, w, h, seed=0, off=1.2 ):
    """ Ivy hanging down a wall face from its top edge at at (the top middle), w wide and h down, in strands. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    right = unit( right )
    out = np.cross( right, UP )
    top = v( *at )
    count = max( 1, int( w / 26 ) )
    for i in range( count ):
        f = ( i + 0.5 ) / count - 0.5
        hh = h * rng.uniform( 0.45, 1.0 )
        ww = hh * 0.5
        c = top + right * ( f * w + rng.normal( 0, 4 ) ) - UP * ( hh / 2 ) + out * ( off + rng.uniform( 0, 2.5 ) )
        sheet( m, "vr_foliage", VM.FOLIAGE, VM.FOLIAGE_ATLAS, "ivy" if i % 2 else "ivy_2", c, right, UP, hh, ww, 0.0, True )


def bougainvillea( m, at, right, w, h, seed=0, off=2.0 ):
    rng = np.random.default_rng( abs( int( seed ) ) )
    right = unit( right )
    out = np.cross( right, UP )
    count = max( 1, int( w / 30 ) )
    for i in range( count ):
        f = ( i + 0.5 ) / count - 0.5
        s = h * rng.uniform( 0.6, 1.0 )
        c = v( *at ) + right * ( f * w ) - UP * ( s / 2 ) + out * ( off + rng.uniform( 0, 4 ) )
        sheet( m, "vr_foliage", VM.FOLIAGE, VM.FOLIAGE_ATLAS, "flowers", c, right, UP, s, s, 0.0, True )


# ---------------------------------------------------------------------------------------------------------------------
# Things

def hard_case( m, c, size, along=( 1, 0 ), paint="vr_case_black", z0=0.0, surface=PLASTIC, seed=0 ):
    """ A moulded military hard case: a body with chamfered corners, a lid seam with a groove, a bevelled lid with
    ribs across it, recessed latches and folding handles, and stacking feet. size ( L, W, H ). """
    along = unit( v( along[0], along[1], 0 ) )
    side = np.cross( UP, along )
    L, W, H = size
    base = v( c[0], c[1], z0 )
    seam = H * 0.68
    ch = 1.6

    def ring( inset ):
        hl, hw = L / 2 - inset, W / 2 - inset
        pts = [ ( -hl + ch, -hw ), ( hl - ch, -hw ), ( hl, -hw + ch ), ( hl, hw - ch ), ( hl - ch, hw ), ( -hl + ch, hw ), ( -hl, hw - ch ),
                ( -hl, -hw + ch ) ]
        return [ base + along * x + side * y for x, y in pts ]

    def band( r0, r1, z_a, z_b ):
        for k in range( len( r0 ) ):
            a0, b0 = r0[k], r0[( k + 1 ) % len( r0 )]
            a1, b1 = r1[k], r1[( k + 1 ) % len( r1 )]
            mid = ( a0 + b0 ) / 2 - base
            card( m, paint, [ a0 + UP * z_a, b0 + UP * z_a, b1 + UP * z_b, a1 + UP * z_b ], v( mid[0], mid[1], 0 ) + UP * ( 0.0 if r0 is r1 else 0.8 ) )

    outer, groove, top = ring( 0.0 ), ring( 0.45 ), ring( 0.9 )
    band( outer, outer, 0.6, seam - 0.7 )
    band( groove, groove, seam - 0.7, seam + 0.7 )
    band( outer, outer, seam + 0.7, H - 0.9 )
    band( outer, top, H - 0.9, H )
    card( m, paint, [ p + UP * H for p in top ], UP )
    for f in ( -0.3, 0.0, 0.3 ):
        obox( m, base + along * ( L * f ) + UP * ( H + 0.35 ), along, ( 2.2, W - 6, 0.7 ), paint )
    for sgn in ( -1, 1 ):
        p = base + side * ( W / 2 + 0.15 ) * sgn
        for f in ( -0.32, 0.32 ):
            obox( m, p + along * ( L * f ) + UP * seam + side * 0.4 * sgn, along, ( 3.4, 0.9, 4.2 ), "vr_dark" )
        h_ = p + side * 0.9 * sgn + UP * ( seam - 5.5 )
        rod( m, h_ - along * 4.5, h_ + along * 4.5, 0.55, "vr_dark", 6 )
    for sgn in ( -1, 1 ):
        p = base + along * ( L / 2 + 0.2 ) * sgn + UP * ( H * 0.5 )
        rod( m, p - side * 3.5, p + side * 3.5, 0.55, "vr_dark", 6 )
    for sa in ( -1, 1 ):
        for sb in ( -1, 1 ):
            obox( m, base + along * ( L / 2 - 4 ) * sa + side * ( W / 2 - 4 ) * sb + UP * 0.3, along, ( 4.0, 4.0, 0.6 ), "vr_black" )
    if surface:
        m.oriented_box( base + UP * ( H / 2 ), ( along, side, UP ), ( L, W, H ), {}, surface )


def case_stack( m, c, along, paint="vr_case_black", sizes=( ( 46, 28, 24 ), ( 40, 26, 20 ) ), seed=0, z0=0.0 ):
    """ Cases stacked, each a little askew. Returns the stack's height. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    along = unit( v( along[0], along[1], 0 ) )
    z = z0
    for i, ( L, W, H ) in enumerate( sizes ):
        yaw = rng.normal( 0, 0.05 )
        a = v( along[0] * math.cos( yaw ) - along[1] * math.sin( yaw ), along[0] * math.sin( yaw ) + along[1] * math.cos( yaw ), 0 )
        off = rng.normal( 0, 1.2, 2 )
        hard_case( m, ( c[0] + off[0], c[1] + off[1] ), ( L, W, H ), a, paint, z, seed=seed + i )
        z += H
    return z


def boulder( m, c, r, seed=0, squash=0.62, paint="vr_rock", surface=STONE, sink=0.18 ):
    """ A weathered boulder: an icosphere subdivided twice, pushed in and out by noise, flattened underneath, sunk a
    little into what it sits on. Shaded smooth, collides as its hull. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    t = ( 1 + 5 ** 0.5 ) / 2
    verts = [ unit( p ) for p in ( ( -1, t, 0 ), ( 1, t, 0 ), ( -1, -t, 0 ), ( 1, -t, 0 ), ( 0, -1, t ), ( 0, 1, t ), ( 0, -1, -t ),
                                   ( 0, 1, -t ), ( t, 0, -1 ), ( t, 0, 1 ), ( -t, 0, -1 ), ( -t, 0, 1 ) ) ]
    faces = [ ( 0, 11, 5 ), ( 0, 5, 1 ), ( 0, 1, 7 ), ( 0, 7, 10 ), ( 0, 10, 11 ), ( 1, 5, 9 ), ( 5, 11, 4 ), ( 11, 10, 2 ), ( 10, 7, 6 ),
              ( 7, 1, 8 ), ( 3, 9, 4 ), ( 3, 4, 2 ), ( 3, 2, 6 ), ( 3, 6, 8 ), ( 3, 8, 9 ), ( 4, 9, 5 ), ( 2, 4, 11 ), ( 6, 2, 10 ),
              ( 8, 6, 7 ), ( 9, 8, 1 ) ]
    for _ in range( 2 ):
        cache = {}
        new = []

        def mid( i, j ):
            key = ( min( i, j ), max( i, j ) )
            if key not in cache:
                verts.append( unit( ( verts[i] + verts[j] ) / 2 ) )
                cache[key] = len( verts ) - 1
            return cache[key]
        for a, b, cc in faces:
            ab, bc, ca = mid( a, b ), mid( b, cc ), mid( cc, a )
            new += [ ( a, ab, ca ), ( b, bc, ab ), ( cc, ca, bc ), ( ab, bc, ca ) ]
        faces = new
    lumps = [ ( unit( rng.normal( 0, 1, 3 ) ), rng.uniform( -0.18, 0.2 ) ) for _ in range( 9 ) ]
    centre = v( *c )
    pts = []
    for p in verts:
        k = 1.0 + sum( amt * max( 0.0, float( np.dot( p, d ) ) ) ** 3 for d, amt in lumps )
        q = p * k * v( 1.0, 0.86, squash )
        pts.append( centre + q * r - UP * ( r * squash * sink ) )
    pts = [ v( p[0], p[1], max( p[2], c[2] - 0.5 ) ) for p in pts ]
    normals = [ unit( p - centre ) for p in pts ]
    for a, b, cc in faces:
        tri = [ pts[a], pts[b], pts[cc] ]
        nrm = np.cross( tri[1] - tri[0], tri[2] - tri[0] )
        if np.linalg.norm( nrm ) < 1e-9:
            continue
        m.polygon( paint, tri, normals=[ normals[a], normals[b], normals[cc] ] )
    if surface:
        m.hull( pts, surface )


def umbrella_closed( m, base, h=110.0, paint="vr_umbrella", z0=0.0 ):
    """ A furled market umbrella on its weighted base: the pole, the canopy wrapped round its ribs (widest a third of
    the way down from the top, tapering to the runner), a finial. """
    b = v( base[0], base[1], z0 )
    P.cylinder( m, ( b[0], b[1] ), 11, z0, z0 + 3, "vr_steel", 14, top="vr_steel", surface=METAL )
    P.cylinder( m, ( b[0], b[1] ), 1.2, z0 + 3, z0 + h, "vr_steel", 8 )
    top = z0 + h
    # The canopy, top to bottom: ( radius, z ). Its eight panels hang in pleats between the ribs, the rib tips poking
    # out at the bottom.
    profile = [ ( 0.9, top ), ( 2.0, top - 4 ), ( 4.2, top - 14 ), ( 6.8, top - 28 ), ( 9.2, top - 44 ), ( 10.8, top - 58 ),
                ( 11.2, top - 68 ), ( 10.0, top - 76 ), ( 7.6, top - 81 ), ( 2.0, top - 83 ) ]
    sides = 48
    ring = []
    for r_, zz in profile:
        pts = []
        for j in range( sides ):
            ang = 2 * math.pi * j / sides
            pleat = abs( math.sin( 4 * ang + 0.35 * ( top - zz ) / 80.0 ) ) ** 0.7
            rr = r_ * ( 0.80 + 0.22 * pleat )
            pts.append( v( b[0] + math.cos( ang ) * rr, b[1] + math.sin( ang ) * rr, zz ) )
        ring.append( pts )
    for k in range( len( ring ) - 1 ):
        for j in range( sides ):
            j1 = ( j + 1 ) % sides
            quad = [ ring[k][j], ring[k][j1], ring[k + 1][j1], ring[k + 1][j] ]
            centre = v( b[0], b[1], ( ring[k][j][2] + ring[k + 1][j][2] ) / 2 )
            ns = [ unit( q - v( b[0], b[1], q[2] ) + UP * 0.25 ) for q in quad ]
            card( m, paint, quad, ( quad[0] + quad[2] ) / 2 - centre, normals=ns )
    # The rib tips at the bottom, and the tie.
    for k in range( 8 ):
        ang = 2 * math.pi * k / 8 + math.pi / 8
        d = v( math.cos( ang ), math.sin( ang ), 0 )
        rod( m, b + d * 9.0 + UP * ( h - 79 ), b + d * 10.5 + UP * ( h - 84 ), 0.35, "vr_steel", 4 )
    P.cylinder( m, ( b[0], b[1] ), 10.4, top - 52, top - 50, "vr_umbrella_tie", 16 )
    P.cylinder( m, ( b[0], b[1] ), 0.9, top, top + 5, "vr_steel", 6, top="vr_steel" )
    P.lathe( m, b, [ ( 1.6, top + 5 ), ( 1.8, top + 7 ), ( 0.0, top + 10 ) ], "vr_steel", 8 )
    m.collision_box( ( b[0] - 9, b[1] - 9, z0 ), ( b[0] + 9, b[1] + 9, z0 + 3 ), METAL )


def flag( m, base, h=210.0, name="flag", z0=0.0, along=( 0, 1 ), size=( 44.0, 66.0 ), seed=0 ):
    """ A flagpole with the resort's flag flying from it in a light breeze: the cloth as four bowed strips. """
    rng = np.random.default_rng( abs( int( seed ) ) )
    b = v( base[0], base[1], z0 )
    P.cylinder( m, ( b[0], b[1] ), 6, z0, z0 + 6, "vr_stone_dark", 10, top="vr_stone_dark", surface=STONE )
    P.cylinder( m, ( b[0], b[1] ), 1.6, z0 + 6, z0 + h, "vr_mast", 8, surface=METAL )
    P.lathe( m, b, [ ( 2.4, z0 + h ), ( 2.4, z0 + h + 2 ), ( 0.0, z0 + h + 4 ) ], "vr_brass", 8 )
    fh, fw = size
    d = unit( v( along[0], along[1], 0 ) )
    out = np.cross( UP, d )
    top = z0 + h - 4
    cols = 5
    prev = None
    for i in range( cols + 1 ):
        f = i / cols
        wave = math.sin( f * math.pi * 1.6 + 0.4 ) * 3.5 * f
        sag = 3.0 * f * f
        p = v( b[0], b[1], 0.0 ) + d * ( fw * f + 2 ) + out * wave
        col = ( p + UP * ( top - fh - sag ), p + UP * ( top - sag * 0.5 ) )
        if prev is not None:
            s0, s1 = ( i - 1 ) / cols, f
            uv = [ VM.atlas_uv( VM.PRINTS, VM.PRINT_ATLAS, name, s0, 0 ), VM.atlas_uv( VM.PRINTS, VM.PRINT_ATLAS, name, s1, 0 ),
                   VM.atlas_uv( VM.PRINTS, VM.PRINT_ATLAS, name, s1, 1 ), VM.atlas_uv( VM.PRINTS, VM.PRINT_ATLAS, name, s0, 1 ) ]
            m.polygon( "vr_print", [ prev[0], col[0], col[1], prev[1] ], both_sides=True, uv=uv )
        prev = col


def banner( m, centre_top, right, h, name="banner", light=True, light_name="Banner light" ):
    """ The hanging banner: a black steel rod with end caps, the printed cloth under it, a slim canopy over it with an
    LED strip washing down its face. centre_top: the rod's middle. """
    right = unit( right )
    out = np.cross( right, UP )
    w = h * VM.aspect( VM.PRINTS, name )
    top = v( *centre_top )
    rod( m, top - right * ( w / 2 + 3 ) + out * 4, top + right * ( w / 2 + 3 ) + out * 4, 1.0, "vr_steel", 8, caps=True )
    picture( m, name, top - UP * ( h / 2 + 1 ) + out * 4, right, h, off=0.0, both=False )
    # A slight hollow behind it so it reads as cloth: its back face.
    P.quad( m, "vr_black", top - UP * ( h / 2 + 1 ) + out * 3.9, -right, UP, w, h )
    # The canopy and its LED, over the banner.
    c = top + UP * 10 + out * 6
    obox( m, c, right, ( w + 16, 12, 3 ), "vr_steel" )
    led( m, c - UP * 1.6 - right * ( w / 2 + 6 ) + out * 2, c - UP * 1.6 + right * ( w / 2 + 6 ) + out * 2, -UP, 2.0 )
    if light:
        LIGHTS.append( ( light_name, tuple( top + out * 22 - UP * 10 ), WARM_SOFT, 220, False ) )


def pylon( m, lo, hi, z0, top, face="+e", name="Pylon" ):
    """ The resort's sign: a travertine monolith with the mark, VERIDANT and RESORT cut into its face, a lit slot at
    its foot. lo, hi: its plan footprint; face: which side the sign faces. """
    e0, n0 = lo
    e1, n1 = hi
    box( m, e0, e1, n0, n1, z0, top - 4, "vr_stone", STONE )
    box( m, e0 - 1, e1 + 1, n0 - 1, n1 + 1, top - 4, top, "vr_stone_dark", STONE )
    box( m, e0 + 1, e1 - 1, n0 + 1, n1 - 1, z0, z0 + 0.5, "vr_stone_dark" )
    outv = { "+e": v( 1, 0, 0 ), "-e": v( -1, 0, 0 ), "+n": v( 0, 1, 0 ), "-n": v( 0, -1, 0 ) }[face]
    right = np.cross( UP, outv )
    fx = { "+e": e1, "-e": e0, "+n": ( e0 + e1 ) / 2, "-n": ( e0 + e1 ) / 2 }[face]
    fy = { "+e": ( n0 + n1 ) / 2, "-e": ( n0 + n1 ) / 2, "+n": n1, "-n": n0 }[face]
    width = abs( np.dot( v( e1 - e0, n1 - n0, 0 ), right ) )
    h = top - z0
    letters( m, "logo", ( fx, fy, z0 + h * 0.66 ), right, width * 0.34, "dark", off=0.25 )
    letters( m, "veridant", ( fx, fy, z0 + h * 0.48 ), right, width * 0.82 / VM.aspect( VM.LETTERS, "veridant" ), "dark", off=0.25 )
    letters( m, "resort", ( fx, fy, z0 + h * 0.405 ), right, width * 0.42 / VM.aspect( VM.LETTERS, "resort" ), "dark", off=0.25 )
    wall_washer( m, f"{name} foot", ( fx, fy, z0 + 9 ), outv, 200, size=( 12.0, 5.0 ), rise=20 )


# ---------------------------------------------------------------------------------------------------------------------
# Furniture

def cafe_table( m, c, z0=0.0, chairs=2, seed=0, surface=METAL ):
    rng = np.random.default_rng( abs( int( seed ) ) )
    b = v( c[0], c[1], z0 )
    P.cylinder( m, ( b[0], b[1] ), 9, z0, z0 + 1, "vr_steel", 12, top="vr_steel" )
    P.cylinder( m, ( b[0], b[1] ), 1.2, z0 + 1, z0 + 28, "vr_steel", 8 )
    P.cylinder( m, ( b[0], b[1] ), 15, z0 + 28, z0 + 29.5, "vr_stone_light", 16, top="vr_stone_light", bottom="vr_steel" )
    m.collision_box( ( b[0] - 12, b[1] - 12, z0 ), ( b[0] + 12, b[1] + 12, z0 + 29.5 ), surface )
    for k in range( chairs ):
        a = 2 * math.pi * k / chairs + rng.uniform( -0.3, 0.3 )
        d = v( math.cos( a ), math.sin( a ), 0 )
        chair( m, b + d * 24, -d, z0 )


def chair( m, at, facing, z0=0.0, paint="vr_wicker" ):
    """ A bistro chair: a woven seat and back on four steel legs, facing facing (plan). """
    f = unit( v( facing[0], facing[1], 0 ) )
    s = np.cross( UP, f )
    c = v( at[0], at[1], z0 )
    obox( m, c + UP * 17.5, f, ( 16, 16, 2 ), paint )
    obox( m, c - f * 7.5 + UP * 26, f, ( 1.4, 15, 15 ), paint )
    for sa in ( -1, 1 ):
        for sb in ( -1, 1 ):
            q = c + f * 6.5 * sa + s * 6.5 * sb
            rod( m, q, q + UP * 16.5, 0.45, "vr_steel", 4 )


def sofa( m, c, facing, length=84.0, z0=0.0, surface=FABRIC ):
    """ A low lounge sofa facing facing: a plinth, a deep seat with cushions, a back and arms. """
    f = unit( v( facing[0], facing[1], 0 ) )
    s = np.cross( UP, f )
    b = v( c[0], c[1], z0 )
    obox( m, b + UP * 2, f, ( 34, length - 4, 4 ), "vr_black" )
    obox( m, b + UP * 10, f, ( 36, length, 12 ), "vr_sofa" )
    obox( m, b - f * 14 + UP * 24, f, ( 8, length, 18 ), "vr_sofa" )
    for sg in ( -1, 1 ):
        obox( m, b + s * ( length / 2 - 4 ) * sg + UP * 20, f, ( 36, 8, 8 ), "vr_sofa" )
    for i in range( 3 ):
        q = b + s * ( ( i - 1 ) * ( length - 12 ) / 3 ) - f * 9 + UP * 26
        obox( m, q, f, ( 6, ( length - 16 ) / 3 - 2, 14 ), "vr_cushion" )
    m.oriented_box( b + UP * 15, ( f, s, UP ), ( 36, length, 30 ), {}, surface )


def lounger( m, c, facing, z0=0.0, surface=WOOD ):
    """ A teak sun lounger with a white mattress, its back raised. """
    f = unit( v( facing[0], facing[1], 0 ) )
    s = np.cross( UP, f )
    b = v( c[0], c[1], z0 )
    for sg in ( -1, 1 ):
        obox( m, b + s * 11 * sg + UP * 6, f, ( 74, 2, 4 ), "vr_timber_dark" )
        for sa in ( -1, 1 ):
            obox( m, b + s * 11 * sg + f * 33 * sa + UP * 2, f, ( 3, 2, 4 ), "vr_timber_dark" )
    obox( m, b + f * 8 + UP * 9.5, f, ( 52, 24, 3 ), "vr_mattress" )
    back = b - f * 28 + UP * 18
    m.oriented_box( back, ( unit( f * math.cos( 0.9 ) + UP * math.sin( 0.9 ) ), s,
                            np.cross( unit( f * math.cos( 0.9 ) + UP * math.sin( 0.9 ) ), s ) ), ( 26, 24, 3 ), "vr_mattress" )
    m.oriented_box( b + UP * 8, ( f, s, UP ), ( 76, 26, 16 ), {}, surface )


def bench( m, c, along, length=72.0, z0=0.0 ):
    """ A stone bench with a teak seat. """
    d = unit( v( along[0], along[1], 0 ) )
    s = np.cross( UP, d )
    b = v( c[0], c[1], z0 )
    for sg in ( -1, 1 ):
        obox( m, b + d * ( length / 2 - 8 ) * sg + UP * 8, d, ( 10, 16, 16 ), "vr_stone" )
    for k in range( 4 ):
        obox( m, b + s * ( -6 + 4 * k ) + UP * 17, d, ( length, 3.4, 2 ), "vr_timber" )
    m.oriented_box( b + UP * 9, ( d, s, UP ), ( length, 18, 18 ), {}, STONE )


def bar_counter( m, lo, hi, z0, top=42.0, front="+e", surface=STONE ):
    """ A stone bar counter with a dark top and an LED glow under its overhang. """
    e0, n0 = lo
    e1, n1 = hi
    box( m, e0, e1, n0, n1, z0, z0 + top - 2, "vr_stone", surface )
    box( m, e0 - 2, e1 + 2, n0 - 2, n1 + 2, z0 + top - 2, z0 + top, "vr_dark" )
    outv = { "+e": v( 1, 0, 0 ), "-e": v( -1, 0, 0 ), "+n": v( 0, 1, 0 ), "-n": v( 0, -1, 0 ) }[front]
    if front in ( "+e", "-e" ):
        x = e1 + 0.3 if front == "+e" else e0 - 0.3
        led( m, ( x, n0 + 2, z0 + top - 3 ), ( x, n1 - 2, z0 + top - 3 ), outv, 1.0 )
    else:
        y = n1 + 0.3 if front == "+n" else n0 - 0.3
        led( m, ( e0 + 2, y, z0 + top - 3 ), ( e1 - 2, y, z0 + top - 3 ), outv, 1.0 )


def drain( m, a, b, z=0.0, w=5.0 ):
    """ A linear drain set in the paving from a to b: a steel grate in a slim frame, flush. """
    a, b = v( a[0], a[1], z + 0.06 ), v( b[0], b[1], z + 0.06 )
    d = unit( b - a )
    s = np.cross( UP, d ) * ( w / 2 )
    card( m, "vr_grate", [ a - s, b - s, b + s, a + s ], UP )
    for sg in ( -1, 1 ):
        o = s * sg * 1.18
        card( m, "vr_steel", [ a + s * sg, b + s * sg, b + o, a + o ], UP )


def art( m, name, centre, right, h, frame=1.4 ):
    """ A painting on a wall in a thin dark frame. """
    right = unit( right )
    out = np.cross( right, UP )
    w = h * VM.aspect( VM.PRINTS, name )
    c = v( *centre )
    obox( m, c + out * 0.5, right, ( w + frame * 2, 1.0, h + frame * 2 ), "vr_black" )
    picture( m, name, c + out * 1.02, right, h, off=0.0 )


def counter_shelves( m, lo, hi, z0, face="+e" ):
    """ A back bar: dark shelves with lit bottles drawn as small blocks. """
    e0, n0 = lo
    e1, n1 = hi
    box( m, e0, e1, n0, n1, z0, z0 + 90, "vr_timber_dark" )
    outv = { "+e": v( 1, 0, 0 ), "-e": v( -1, 0, 0 ), "+n": v( 0, 1, 0 ), "-n": v( 0, -1, 0 ) }[face]
    rng = np.random.default_rng( int( abs( e0 * 7 + n0 * 3 ) ) % 1000 )
    for z in ( 40.0, 58.0, 76.0 ):
        if face in ( "+e", "-e" ):
            x = e1 if face == "+e" else e0
            led( m, ( x + outv[0] * 0.2, n0 + 3, z - 0.5 ), ( x + outv[0] * 0.2, n1 - 3, z - 0.5 ), outv, 0.6, "vr_led_soft" )
            n = n0 + 5
            while n < n1 - 5:
                hh = rng.uniform( 7, 12 )
                box( m, x + outv[0] * 0.5 - 1.5, x + outv[0] * 0.5 + 1.5, n, n + 2.6, z, z + hh, "vr_brass" if rng.random() < 0.4 else "vr_yacht_glass" )
                n += rng.uniform( 3.5, 6 )
        else:
            y = n1 if face == "+n" else n0
            led( m, ( e0 + 3, y + outv[1] * 0.2, z - 0.5 ), ( e1 - 3, y + outv[1] * 0.2, z - 0.5 ), outv, 0.6, "vr_led_soft" )
