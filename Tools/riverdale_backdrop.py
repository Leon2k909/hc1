"""
Riverdale's backdrop, for Tools/riverdale_map.py: what's seen round the plant, drawn only (no collision).

- The containment domes: UNIT 1 east of the play area at (4400, -1150), UNIT 2 west (mirrored). Each is a 2200 in (56 m)
  post-tensioned concrete cylinder under a shallow dome, in its own weathered concrete (rv_bd_dome): jump-form lifts
  every 5 ft, faint panel joints, rain runs hanging from the ring beam and down the dome, a grimy splash zone at its
  foot. Round it:
  - the ring beam at the spring line, proud of the wall, and three tendon buttresses 120 degrees apart, up the full
    height;
  - on the face towards the yard the logo and the name, the red UNIT banner, the equipment hatch (a steel door in its
    bolted ring) and the pipes and cable trays running up the wall on their brackets;
  - a personnel airlock reached by an open steel stair tower that climbs to the ring beam's walkway;
  - red aircraft warning lights round the ring beam and on the crown;
  - a vent stack with platforms, its caged ladder and warning lights, a duct from the auxiliary buildings to its foot;
  - auxiliary buildings round its foot, towards the play area (near model, shadowed).
- Four natural draught cooling towers, 113-119 m tall, far off to the north-east and north-west, where the east yard's
  and the west yard's views find them over the annexes: each a hyperboloid shell (rv_bd_tower: lift lines, dark rain
  runs hanging from the lip, grime near the foot) with a thickened stiffening ring at the lip, on a ring of raking
  columns crossing as X braces over the air inlet, the dark fill seen through it, the basin's wall round it, and
  warning lights on the lip.
- A tower crane east of the plant, left of the near cooling tower from the east yard: a lattice mast and jib, the
  counter-jib with its walkway and ballast, the tower head's pendant ties, the cab, the trolley and hook block.
- Office and service blocks round the plant's edge: window bands with mullions, parapets, roof plant, ducts and flues.
- The land (rv_bd_land): a heightfield (HEIGHTFIELD) eroded by rain droplets, forested hills round the site and snowy
  mountains beyond, drawn as two polar meshes (fine angular steps where the ridgelines are) and painted by one
  log-polar texture round the whole ring, so every texel is about as wide as it is long and the near hills get finer
  texels than the far peaks: meadow by the plant, conifer forest up to a ragged tree line, scree and grey rock on the
  steep faces with its strata, snow above a snow line that drops on north-facing slopes and in gullies and leaves the
  steep rock bare. Its normal map carries what the mesh can't: crowns, strata, gullies.
- Conifers on the hills (rv_bd_conifer_a/b/c): layered star-shaped tiers with drooping tips, each tier's edge cut by
  the needle texture's alpha into sprigs, in three tints, leaning a little, set in stands with clearings and ragged
  edges by the land's forest mask, densest just past the plant's cleared perimeter. Near ones have more tiers.
Returns two models (far: no shadows, the domes and towers; near: shadows, the crane and blocks); extra_models() adds
the land (in two halves, east and west, to keep each file small) and the trees (near and far).
EXTRA_SURFACES and EXTRA_PAINTS are this module's materials (riverdale_materials writes them).
"""
import functools
import math

import numba
import numpy as np
from scipy import ndimage

import map_kit as K
import riverdale_parts as P
from riverdale_parts import v, card, box, UP

DOME_R, DOME_WALL, DOME_RISE = 1100.0, 1400.0, 760.0
DOME_E, DOME_N = 4400.0, -1150.0                 # UNIT 1 (UNIT 2 at -DOME_E): over the yard's end, clear of B1
TOWERS = ( ( 10300.0, 4160.0, 4700.0 ), ( 14240.0, 2150.0, 4500.0 ) )     # east; the west ones are mirrored
CRANE = ( 4000.0, 1000.0 )                    # left of the near cooling tower from the east yard
CLEAR = ( -2800.0, 2800.0, -2900.0, 2500.0 )     # no trees or hills in the plant
SITE = 6000.0                                 # the plant's gravel ground: a square this far each way (ground())

# The domes' and towers' textures: inches across and up one picture.
DOME_TEX = ( 1024.0, 2048.0 )
TOWER_TEX = ( 2350.0, 4700.0 )

# The land: a heightfield (inches) over a square FIELD_EXT each way, and its texture round the ring: LAND_W texels round,
# LAND_H out, from LAND_R0 out to LAND_R1, each row LAND_STEP further in log radius than the last, so texels are square.
FIELD_N, FIELD_EXT = 2048, 86000.0
FIELD_PX = 2 * FIELD_EXT / FIELD_N
LAND_W, LAND_H = 4096, 2048
LAND_R0 = 3600.0
LAND_STEP = 2 * math.pi / LAND_W
LAND_R1 = LAND_R0 * math.exp( LAND_H * LAND_STEP )
LAND_REF = 40.0                               # inches a texel the normal map's heights are scaled to (see land())
# The meshes: ( inner radius, outer radius, angular steps, radial steps ).
NEAR_RING = ( 3600.0, 22000.0, 480, 34 )
FAR_RING = ( 22000.0, 82000.0, 1200, 70 )

# Trees: how many to try for, and inside what radius they get the near trees' extra tiers.
TREE_TRIES = 26000
PEAKS, DROPS = 46, 700000                   # the mountains' massifs, and the rain droplets that erode them
TREE_NEAR = 11000.0


def fbm( rng, size, octaves=6, base=4 ):
    """ Periodic-ish value noise on size x size, -1..1-ish, from octaves of upsampled random grids. """
    out = np.zeros( ( size, size ), np.float32 )
    amp, total = 1.0, 0.0
    cells = base
    for _ in range( octaves ):
        grid = rng.standard_normal( ( cells + 3, cells + 3 ) ).astype( np.float32 )
        up = ndimage.zoom( grid, ( size + 3 * size / cells ) / ( cells + 3 ), order=3 )
        out += amp * up[:size, :size]
        total += amp
        amp *= 0.5
        cells *= 2
    return out / total


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers

def srgb_lin( rgb ):
    c = np.asarray( rgb, np.float32 ) / 255.0
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 ).astype( np.float32 )


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def mix( a, b, t ):
    t = np.asarray( t, np.float32 )
    if t.ndim >= 1 and np.ndim( a ) == t.ndim + 1:
        t = t[..., None]
    elif np.ndim( b ) == t.ndim + 1 and t.ndim >= 1:
        t = t[..., None]
    return a + ( b - a ) * t


def noise( rng, shape, beta, longest, shortest=1.0, stretch=( 1.0, 1.0 ) ):
    """ Periodic fractal noise (unit deviation) on a picture of shape ( rows, cols ), wavelengths from longest to shortest
    pixels; stretch ( across, down ) makes features that many times longer that way. """
    h, w = shape
    white = rng.standard_normal( ( h, w ) ).astype( np.float32 )
    fy = np.fft.fftfreq( h )[:, None] * stretch[1]
    fx = np.fft.rfftfreq( w )[None, :] * stretch[0]
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    fmin = 1.0 / longest
    amp = f ** ( -beta / 2.0 ) * np.clip( ( f - fmin * 0.5 ) / ( fmin * 0.5 ), 0, 1 ) * np.clip( 2.0 - f * shortest, 0, 1 )
    amp[0, 0] = 0.0
    out = np.fft.irfft2( np.fft.rfft2( white ) * amp, s=( h, w ) ).astype( np.float32 )
    return ( out - out.mean() ) / ( out.std() + 1e-6 )


def runs_down( sources, length_px ):
    """ Stains running down a picture from sources (1 where a run starts), fading over length_px rows. Not wrapped. """
    from scipy import signal
    a = math.exp( -1.0 / max( 1.0, length_px ) )
    return signal.lfilter( [ 1.0 - a ], [ 1.0, -a ], sources, axis=0 ).astype( np.float32 )


def quad_uv( m, paint, pts, uvs, normals=None ):
    """ A polygon with its own UVs (and normals), wound as given. """
    m.polygon( paint, [ np.asarray( p, float ) for p in pts ], uv=uvs, normals=normals )


def lathe_uv( m, paint, c, profile, sides, u_tiles, vs, inward=False, a0=0.0, arc=2 * math.pi ):
    """ A round thing turned about the vertical through c, with UVs: u round it (u_tiles pictures over the arc), v given
    per profile point. Smooth normals from the profile. inward faces it inwards (a tower's inside). """
    c = v( c[0], c[1], 0.0 )
    n = len( profile )
    seg = []
    for j in range( n - 1 ):
        ( r0, z0 ), ( r1, z1 ) = profile[j], profile[j + 1]
        seg.append( P.unit( v( z1 - z0, r0 - r1, 0 ) )[:2] )
    pn = []
    for j in range( n ):
        a = seg[max( 0, j - 1 )]
        b = seg[min( n - 2, j )]
        s = a + b
        pn.append( s / max( np.linalg.norm( s ), 1e-9 ) )
    steps = sides
    dirs = [ v( math.cos( a0 + arc * k / steps ), math.sin( a0 + arc * k / steps ), 0.0 ) for k in range( steps + 1 ) ]
    for j in range( n - 1 ):
        ( r0, z0 ), ( r1, z1 ) = profile[j], profile[j + 1]
        if r0 < 1e-6 and r1 < 1e-6:
            continue
        for k in range( steps ):
            d0, d1 = dirs[k], dirs[k + 1]
            pts = [ c + d0 * r0 + UP * z0, c + d1 * r0 + UP * z0, c + d1 * r1 + UP * z1, c + d0 * r1 + UP * z1 ]
            uv = [ ( k / steps * u_tiles, vs[j] ), ( ( k + 1 ) / steps * u_tiles, vs[j] ), ( ( k + 1 ) / steps * u_tiles, vs[j + 1] ),
                   ( k / steps * u_tiles, vs[j + 1] ) ]
            nr = [ d0 * pn[j][0] + UP * pn[j][1], d1 * pn[j][0] + UP * pn[j][1], d1 * pn[j + 1][0] + UP * pn[j + 1][1],
                   d0 * pn[j + 1][0] + UP * pn[j + 1][1] ]
            if r1 < 1e-6:
                pts, uv, nr = pts[:3], uv[:3], nr[:3]
            elif r0 < 1e-6:
                pts, uv, nr = pts[1:], uv[1:], nr[1:]
            if inward:
                pts, uv, nr = pts[::-1], uv[::-1], [ -x for x in nr[::-1] ]
            m.polygon( paint, pts, uv=uv, normals=nr )


def uv_box( m, paint, centre, axes, size, uv_of, skip=( "-z", ) ):
    """ An oriented box whose faces take their UVs from uv_of( point, face normal ). Faces in skip aren't drawn. """
    centre = np.asarray( centre, float )
    ax = [ P.unit( a ) for a in axes ]
    h = np.asarray( size, float ) / 2

    def corner( sx, sy, sz ):
        return centre + ax[0] * sx * h[0] + ax[1] * sy * h[1] + ax[2] * sz * h[2]

    faces = {
        "+x": ( [ corner( 1, -1, -1 ), corner( 1, 1, -1 ), corner( 1, 1, 1 ), corner( 1, -1, 1 ) ], ax[0] ),
        "-x": ( [ corner( -1, 1, -1 ), corner( -1, -1, -1 ), corner( -1, -1, 1 ), corner( -1, 1, 1 ) ], -ax[0] ),
        "+y": ( [ corner( 1, 1, -1 ), corner( -1, 1, -1 ), corner( -1, 1, 1 ), corner( 1, 1, 1 ) ], ax[1] ),
        "-y": ( [ corner( -1, -1, -1 ), corner( 1, -1, -1 ), corner( 1, -1, 1 ), corner( -1, -1, 1 ) ], -ax[1] ),
        "+z": ( [ corner( -1, -1, 1 ), corner( 1, -1, 1 ), corner( 1, 1, 1 ), corner( -1, 1, 1 ) ], ax[2] ),
        "-z": ( [ corner( -1, 1, -1 ), corner( 1, 1, -1 ), corner( 1, -1, -1 ), corner( -1, -1, -1 ) ], -ax[2] ),
    }
    for face, ( pts, nrm ) in faces.items():
        if face in skip:
            continue
        m.polygon( paint, pts, normal=nrm, uv=[ uv_of( p, nrm ) for p in pts ] )


def wall_uv( tex ):
    """ UVs for a vertical-ish face in a picture tex ( across, up ) inches: across along the face, up its height. """
    def f( p, nrm ):
        side = P.unit( np.cross( UP, nrm ) ) if abs( nrm[2] ) < 0.9 else v( 1, 0, 0 )
        return ( float( np.dot( p, side ) ) / tex[0], float( p[2] ) / tex[1] )
    return f


def rod4( m, a, b, r, paint ):
    """ A thin four-sided member: lattices far off, where an eight-sided rod would be wasted. """
    P.rod( m, a, b, r, paint, 4 )


# ---------------------------------------------------------------------------------------------------------------------
# Materials: concrete for the domes and towers, the land's texture, conifer needles

def dome_concrete( seed=301 ):
    """ The containment's concrete, one picture DOME_TEX across and up (1 px an inch, bottom row the foot of the wall):
    jump-form lifts every 60 in, each a little different in tone with a thin joint and a row of grouted tie holes; faint
    panel joints every 96 in; rain runs hanging from under the ring beam (1400 in up) and running down the dome above
    it; efflorescence under some joints; a grimy splash zone at the foot. """
    w, h = int( DOME_TEX[0] ), int( DOME_TEX[1] )
    rng = np.random.default_rng( seed )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    x, z = xx, h - 0.5 - yy
    cure, mid, grit = noise( rng, ( h, w ), 2.8, 400, 20 ), noise( rng, ( h, w ), 2.0, 40, 2 ), noise( rng, ( h, w ), 0.6, 2, 1 )
    base = srgb_lin( ( 150, 150, 145 ) )
    colour = base[None, None, :] * ( 1.0 + 0.045 * cure + 0.03 * mid + 0.035 * grit )[..., None]
    colour *= ( 1.0 + 0.025 * noise( rng, ( h, w ), 3.0, 600, 60 )[..., None] * np.array( [ 0.7, 0.2, -0.8 ], np.float32 ) )
    lift = 60.0
    li = np.floor( z / lift ).astype( int )
    tone = rng.normal( 0, 0.03, 64 ).astype( np.float32 )
    colour *= ( 1.0 + tone[li % 64] )[..., None]
    lz = z % lift
    joint = np.exp( -( np.minimum( lz, lift - lz ) / 0.9 ) ** 2 )
    colour *= ( 1.0 - 0.16 * joint )[..., None]
    panel = 96.0
    px_ = np.minimum( x % panel, panel - x % panel )
    colour *= ( 1.0 - 0.06 * np.exp( -( px_ / 0.8 ) ** 2 ) )[..., None]
    # Tie holes: a row in each lift, every 24 in, grouted darker.
    hx, hz = ( x + 12.0 ) % 24.0 - 12.0, ( z % lift ) - lift * 0.5
    holes = smoothstep( 1.6, 1.0, np.sqrt( hx * hx + hz * hz ) )
    colour = mix( colour, colour * 0.72, holes * 0.8 )
    height = 0.04 * mid + 0.02 * grit - 0.15 * holes + 0.08 * joint
    # Rain runs: from the drip line under the ring beam, and scattered over the dome above it, long and patchy.
    src = np.zeros( ( h, w ), np.float32 )
    drip = int( h - 1400 )
    src[drip - 2:drip + 2] = ( rng.random( w ) ** 3 ).astype( np.float32 )[None, :] * 1.4
    cap = ( rng.random( ( h, w ) ) < 0.0006 ) & ( z > 1420 )
    src[cap] = rng.uniform( 0.3, 1.0, int( cap.sum() ) )
    lifts = ( np.abs( lz - 0.5 ) < 0.6 ) & ( rng.random( ( h, w ) ) < 0.01 )
    src[lifts] = np.maximum( src[lifts], 0.35 )
    src = ndimage.gaussian_filter( src, ( 0.6, 1.6 ) )
    fingers = smoothstep( -0.8, 1.2, noise( rng, ( h, w ), 2.0, 200, 3, ( 1.0, 0.1 ) ) )
    runs = np.clip( runs_down( src, 420.0 ) * 5.0 + runs_down( src, 90.0 ) * 3.0, 0, 1 ) * fingers
    colour = mix( colour, colour * srgb_lin( ( 150, 146, 136 ) ) * 3.2, runs * 0.55 )
    # Salts below some lift joints, and a damp grimy foot.
    salts = smoothstep( 1.3, 2.4, noise( rng, ( h, w ), 2.2, 80, 6 ) ) * runs_down( joint * ( rng.random( ( h, w ) ) < 0.2 ), 30 ) * 4
    colour = mix( colour, srgb_lin( ( 200, 200, 194 ) ), np.clip( salts, 0, 1 ) * 0.35 )
    foot = smoothstep( 90.0, 0.0, z + 25 * noise( rng, ( h, w ), 2.0, 120, 8 ) )
    colour = mix( colour, colour * srgb_lin( ( 120, 122, 104 ) ) * 3.0, foot * 0.75 )
    rough = np.clip( 0.86 + 0.04 * mid - 0.12 * runs + 0.05 * salts - 0.1 * foot, 0.4, 1.0 )
    return colour, rough.astype( np.float32 ), height.astype( np.float32 ), 1.0


def tower_concrete( seed=311 ):
    """ A cooling tower's shell, one picture TOWER_TEX across and up (the whole shell from its foot to the lip): slipform
    lifts every 50 in, broad patches a little lighter or darker, dark rain runs and algae hanging from the lip down to
    mid-height, streaks from the lifts, and grime near the foot from the basin's spray. """
    w, h = 1024, 2048
    ppi = h / TOWER_TEX[1]
    rng = np.random.default_rng( seed )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    z = ( h - 0.5 - yy ) / ppi
    frac = z / TOWER_TEX[1]
    cure, mid, grit = noise( rng, ( h, w ), 2.8, 500, 20 ), noise( rng, ( h, w ), 2.0, 60, 2 ), noise( rng, ( h, w ), 0.6, 2, 1 )
    base = srgb_lin( ( 168, 166, 160 ) )
    colour = base[None, None, :] * ( 1.0 + 0.06 * cure + 0.03 * mid + 0.03 * grit )[..., None]
    lift = 50.0 * ppi
    lz = ( h - 0.5 - yy ) % lift
    joint = np.exp( -( np.minimum( lz, lift - lz ) / 0.7 ) ** 2 )
    colour *= ( 1.0 - 0.1 * joint )[..., None]
    tone = rng.normal( 0, 0.025, 128 ).astype( np.float32 )
    colour *= ( 1.0 + tone[np.floor( ( h - 0.5 - yy ) / lift ).astype( int ) % 128] )[..., None]
    patches = smoothstep( 0.8, 1.6, noise( rng, ( h, w ), 2.6, 300, 30 ) )
    colour = mix( colour, colour * 1.08, patches * 0.6 )
    # Runs from the lip: dense at the top, a long dark fringe down to mid-height; finer runs from the lifts.
    src = np.zeros( ( h, w ), np.float32 )
    src[:6] = ( 0.4 + 0.6 * rng.random( w ) ** 1.5 ).astype( np.float32 )[None, :]
    lifts = ( lz < 1.2 ) & ( rng.random( ( h, w ) ) < 0.004 )
    src[lifts] = rng.uniform( 0.2, 0.7, int( lifts.sum() ) )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.2 ) )
    fingers = smoothstep( -0.9, 1.0, noise( rng, ( h, w ), 2.0, 160, 3, ( 1.0, 0.08 ) ) )
    runs = np.clip( runs_down( src, 900 * ppi ) * 2.2 + runs_down( src, 160 * ppi ) * 2.0, 0, 1 ) * fingers
    top = smoothstep( 0.55, 1.0, frac ) * ( 0.6 + 0.4 * fingers )
    stain = np.clip( runs * 0.75 + top * 0.45, 0, 1 )
    colour = mix( colour, colour * srgb_lin( ( 128, 132, 118 ) ) * 2.4, stain * 0.8 )
    foot = smoothstep( 0.08, 0.0, frac + 0.02 * noise( rng, ( h, w ), 2.0, 200, 6 ) )
    colour = mix( colour, colour * srgb_lin( ( 120, 120, 110 ) ) * 2.8, foot * 0.6 )
    rough = np.clip( 0.84 + 0.05 * mid - 0.15 * stain, 0.4, 1 )
    height = 0.05 * mid + 0.06 * joint
    return colour, rough.astype( np.float32 ), height.astype( np.float32 ), ppi


CONIFER_TINTS = { "a": ( ( 40, 60, 44 ), ( 70, 92, 58 ) ), "b": ( ( 50, 64, 38 ), ( 86, 100, 56 ) ),
                  "c": ( ( 32, 48, 38 ), ( 58, 78, 54 ) ) }


def conifer( kind, seed=401 ):
    """ One branch tier's needles for the trees' star-shaped tiers, 512 px square: u across one branch (its axis at u 0,
    the gap between branches at u 0.5), v from the tip (v 0) to the trunk (v 1). Sprigs of needles fan out along the
    branch, lit at their new growth; between the branches it's dark. The tier's edge in UV runs from the tip (0, 0) to
    the gap (0.5, 0.3): the alpha cuts it into sprigs just inside that line, so the tiers' outlines are ragged. """
    from PIL import Image, ImageDraw
    n, ss = 512, 2
    rng = np.random.default_rng( seed + ord( kind ) )
    big = n * ss
    mass = Image.new( "L", ( big, big ), 0 )
    lit = Image.new( "L", ( big, big ), 0 )
    dm, dl = ImageDraw.Draw( mass ), ImageDraw.Draw( lit )

    # Sprigs along each branch (copies at u -1, 0, 1 so they wrap): a stem and needles either side, pointing out.
    for copy in ( -1.0, 0.0, 1.0 ):
        for _ in range( 520 ):
            t = rng.random() ** 0.8                      # along the branch from the tip
            vv = 0.02 + t * 0.98
            spread = 0.04 + 0.4 * t                     # the branch's sprigs fan wider towards the trunk
            u0 = copy + rng.normal( 0, spread * 0.45 )
            length = rng.uniform( 0.05, 0.12 )
            ang = rng.uniform( -0.9, 0.9 ) + ( -0.6 if u0 < copy else 0.6 )
            u1, v1 = u0 + math.sin( ang ) * length * 0.6, vv - math.cos( ang ) * length
            width = int( rng.uniform( 3, 7 ) * ss )
            a_, b_ = ( u0 * big, ( 1 - vv ) * big ), ( u1 * big, ( 1 - v1 ) * big )
            dm.line( [ a_, b_ ], fill=255, width=width )
            if vv < 0.45 and rng.random() < 0.7:
                dl.line( [ a_, b_ ], fill=int( rng.uniform( 120, 255 ) ), width=max( 2, width // 2 ) )
    # The canvas wraps across u: fold the copies drawn past its edges back in.
    mass_a = np.asarray( mass, np.float32 ) / 255.0
    lit_a = np.asarray( lit, np.float32 ) / 255.0
    small = lambda a: a.reshape( n, ss, n, ss ).mean( ( 1, 3 ) )
    mass_a, lit_a = small( mass_a ), small( lit_a )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 )
    u = ( xx + 0.5 ) / n
    vv = 1.0 - ( yy + 0.5 ) / n
    du = np.minimum( u, 1.0 - u )                    # 0 on the branch's axis, 0.5 in the gap
    inner = smoothstep( 0.25, 0.7, vv )              # towards the trunk the tier is solid needles
    edge = 0.6 * du                                  # the tier's outline in UV
    body = np.clip( mass_a * 1.6, 0, 1 )
    alpha = np.clip( np.maximum( body, inner ), 0, 1 ) * smoothstep( edge - 0.005, edge + 0.03, vv )
    alpha = smoothstep( 0.35, 0.65, alpha )
    dark, light = srgb_lin( CONIFER_TINTS[kind][0] ), srgb_lin( CONIFER_TINTS[kind][1] )
    shade = np.clip( 0.35 + 0.65 * ( 1 - du * 1.6 ) * ( 1 - 0.5 * inner ), 0, 1 )
    colour = dark[None, None, :] * ( 0.55 + 0.6 * shade )[..., None]
    colour = mix( colour, light[None, None, :], np.clip( lit_a * 0.9, 0, 1 ) )
    colour *= ( 1.0 + 0.12 * noise( rng, ( n, n ), 1.5, 40, 2 ) )[..., None]
    height = ndimage.gaussian_filter( body, 2.0, mode="wrap" ) * 1.2 - inner * 0.3
    rough = np.full( ( n, n ), 0.82, np.float32 ) - 0.1 * lit_a
    return dict( colour=colour.astype( np.float32 ), rough=rough.astype( np.float32 ), height=height.astype( np.float32 ),
                 ppi=8.0, alpha=alpha.astype( np.float32 ), backfaces=True )


# ---------------------------------------------------------------------------------------------------------------------
# The land's heightfield

@numba.njit( cache=True )
def _erode( h, drops, seed, radius ):
    """ Hydraulic erosion by rain droplets (after Hans Beyer's and Sebastian Lague's): each runs downhill with a little
    inertia, picks up sediment while it's fast and the slope is steep, drops it where it slows. h is in cell units. """
    np.random.seed( seed )
    n = h.shape[0]
    inertia, capacity, min_slope, erode, deposit, evaporate, gravity = 0.06, 5.0, 0.01, 0.35, 0.3, 0.015, 4.0
    # The brush: cells within radius, weighted by closeness.
    offs = []
    for dy in range( -radius, radius + 1 ):
        for dx in range( -radius, radius + 1 ):
            d = math.sqrt( dx * dx + dy * dy )
            if d <= radius:
                offs.append( ( dy, dx, radius - d + 0.5 ) )
    total = 0.0
    for o in offs:
        total += o[2]
    for _ in range( drops ):
        x = np.random.random() * ( n - 3 ) + 1
        y = np.random.random() * ( n - 3 ) + 1
        dx, dy, speed, water, sediment = 0.0, 0.0, 1.0, 1.0, 0.0
        for _step in range( 80 ):
            ix, iy = int( x ), int( y )
            fx, fy = x - ix, y - iy
            h00, h10, h01, h11 = h[iy, ix], h[iy, ix + 1], h[iy + 1, ix], h[iy + 1, ix + 1]
            gx = ( h10 - h00 ) * ( 1 - fy ) + ( h11 - h01 ) * fy
            gy = ( h01 - h00 ) * ( 1 - fx ) + ( h11 - h10 ) * fx
            here = h00 * ( 1 - fx ) * ( 1 - fy ) + h10 * fx * ( 1 - fy ) + h01 * ( 1 - fx ) * fy + h11 * fx * fy
            dx = dx * inertia - gx * ( 1 - inertia )
            dy = dy * inertia - gy * ( 1 - inertia )
            length = math.sqrt( dx * dx + dy * dy )
            if length < 1e-9:
                break
            dx /= length
            dy /= length
            nx, ny = x + dx, y + dy
            if nx < 1 or ny < 1 or nx >= n - 2 or ny >= n - 2:
                break
            jx, jy = int( nx ), int( ny )
            gx2, gy2 = nx - jx, ny - jy
            there = ( h[jy, jx] * ( 1 - gx2 ) * ( 1 - gy2 ) + h[jy, jx + 1] * gx2 * ( 1 - gy2 ) + h[jy + 1, jx] * ( 1 - gx2 ) * gy2 +
                      h[jy + 1, jx + 1] * gx2 * gy2 )
            dh = there - here
            cap = max( -dh, min_slope ) * speed * water * capacity
            if sediment > cap or dh > 0:
                amount = min( dh, sediment ) if dh > 0 else ( sediment - cap ) * deposit
                sediment -= amount
                h[iy, ix] += amount * ( 1 - fx ) * ( 1 - fy )
                h[iy, ix + 1] += amount * fx * ( 1 - fy )
                h[iy + 1, ix] += amount * ( 1 - fx ) * fy
                h[iy + 1, ix + 1] += amount * fx * fy
            else:
                amount = min( ( cap - sediment ) * erode, -dh )
                for o in offs:
                    cy, cx = iy + o[0], ix + o[1]
                    if cy < 0 or cx < 0 or cy >= n or cx >= n:
                        continue
                    take = amount * o[2] / total
                    if h[cy, cx] < take:
                        take = max( h[cy, cx], 0.0 )
                    h[cy, cx] -= take
                    sediment += take
            speed = math.sqrt( max( speed * speed - dh * gravity, 0.0 ) )
            water *= 1 - evaporate
            x, y = nx, ny


def _octave( rng, n, cells ):
    """ Periodic cubic value noise on n x n with cells across, unit deviation. """
    grid = rng.standard_normal( ( cells, cells ) ).astype( np.float32 )
    up = ndimage.zoom( grid, n / cells, order=3, mode="grid-wrap", grid_mode=True )[:n, :n]
    return ( up - up.mean() ) / ( up.std() + 1e-6 )


@functools.lru_cache( maxsize=1 )
def heightfield():
    """ The land round the plant, inches over a FIELD_N square FIELD_EXT each way (rows north, columns east):
    - rolling hills from the plant out to about 25000 in;
    - a ring of mountains beyond: PEAKS massifs, each a cone with spurs (its outline swells and shrinks round it, so
      ridges run down from the summit), some drawn out into short ranges, their bases warped, rising to about a sixth of
      their distance, overlapping into ridges with saddles between;
    - detail on them that fades where the slope it has already gathered is steep (Quilez's eroded fbm), so valleys stay
      smooth and the ridges rough;
    - then rain: droplets carve gullies down the faces and drop fans at their feet (_erode), on a field half as fine;
    - the plant's square and the cooling towers' yards flattened, the land falling to meet them.
    Returns a dict of the fields the texture and the meshes sample. """
    rng = np.random.default_rng( 2031 )
    n = FIELD_N // 2
    px = 2 * FIELD_EXT / n
    c = -FIELD_EXT + ( np.arange( n ) + 0.5 ) * px
    E, N = np.meshgrid( c, c )
    R = np.hypot( E, N )
    wx, wy = _octave( rng, n, 10 ) * 2500, _octave( rng, n, 10 ) * 2500
    macro = np.zeros( ( n, n ), np.float32 )
    for _ in range( PEAKS ):
        a, r = rng.uniform( 0, 2 * math.pi ), rng.uniform( 25000, 80000 )
        hp = 0.19 * r * rng.uniform( 0.55, 1.1 )
        r0 = hp * rng.uniform( 2.2, 3.4 )
        turn, el = rng.uniform( 0, math.pi ), rng.uniform( 1.0, 2.2 )
        de, dn = E + wx - r * math.sin( a ), N + wy - r * math.cos( a )
        u = de * math.cos( turn ) + dn * math.sin( turn )
        w = -de * math.sin( turn ) + dn * math.cos( turn )
        th = np.arctan2( w, u )
        spur = 1 + 0.2 * np.cos( 3 * th + rng.uniform( 0, 6.3 ) ) + 0.12 * np.cos( 5 * th + rng.uniform( 0, 6.3 ) ) +             0.06 * np.cos( 9 * th + rng.uniform( 0, 6.3 ) )
        d = np.sqrt( ( u / el ) ** 2 + ( w * el * 0.8 ) ** 2 ) / ( r0 * spur )
        cone = ( hp * np.clip( 1 - d, 0, None ) ** 1.5 ).astype( np.float32 )
        macro = np.maximum( macro, cone ) + 0.25 * np.minimum( macro, cone )
    macro *= np.clip( ( R - 20000 ) / 8000, 0, 1 ).astype( np.float32 )
    hills = ( 150 + 2300 * smoothstep( 5000, 26000, R ) ) * ( 0.55 + 0.32 * ( 0.55 * _octave( rng, n, 14 ) + 0.3 * _octave( rng, n, 30 ) +
                                                                          0.15 * _octave( rng, n, 64 ) ) )
    detail = np.zeros( ( n, n ), np.float32 )
    dx, dy = np.zeros( ( n, n ), np.float32 ), np.zeros( ( n, n ), np.float32 )
    amp = 1.0
    for cells in ( 12, 24, 48, 96, 192 ):
        o = _octave( rng, n, cells )
        gy, gx = np.gradient( o )
        dx += gx * cells / 24 * amp
        dy += gy * cells / 24 * amp
        detail += amp * o / ( 1 + 0.6 * ( dx * dx + dy * dy ) )
        amp *= 0.5
    H = hills + macro * np.clip( 0.85 + 0.18 * detail, 0.45, 1.3 ) + 700 * smoothstep( 20000, 40000, R ) * detail
    # Rain, in cell units so the droplets' slopes are dimensionless.
    cells_h = ( H / px ).astype( np.float64 )
    _erode( cells_h, DROPS, 7, 2 )
    H = ndimage.zoom( ( cells_h * px ).astype( np.float32 ), FIELD_N / n, order=3 )
    # Finer grain than the erosion's field, more where it's steep.
    n = FIELD_N
    c = -FIELD_EXT + ( np.arange( n ) + 0.5 ) * FIELD_PX
    E, N = np.meshgrid( c, c )
    gy, gx = np.gradient( H, FIELD_PX )
    H = H + ( 18 + 30 * np.clip( np.hypot( gx, gy ), 0, 1.2 ) ) * _octave( rng, n, 384 ) * smoothstep( 15000, 30000, np.hypot( E, N ) )
    # The plant's square and the towers' yards, flattened; the rest falls to meet them.
    out = np.maximum( np.abs( E ), np.abs( N ) ) - SITE
    H = -45.0 + ( H + 45.0 ) * smoothstep( 0.0, 3600.0, out )
    for te, tn, th in TOWERS:
        for sx in ( -1, 1 ):
            d = np.hypot( E - sx * te, N - tn ) - ( th * 0.36 + 700 )
            H = -15.0 + ( H + 15.0 ) * smoothstep( 0.0, 2600.0, d )
    H = H.astype( np.float32 )
    gy, gx = np.gradient( H, FIELD_PX )
    blur1, blur3 = ndimage.gaussian_filter( H, 1.5 ), ndimage.gaussian_filter( H, 3.5 )
    sgy, sgx = np.gradient( ndimage.gaussian_filter( H, 2.5 ), FIELD_PX )
    curv = ndimage.laplace( ndimage.gaussian_filter( H, 2.0 ) ) / FIELD_PX
    curv_wide = ndimage.laplace( ndimage.gaussian_filter( H, 6.0 ) ) / FIELD_PX
    return dict( H=H, gx=gx.astype( np.float32 ), gy=gy.astype( np.float32 ), sgx=sgx.astype( np.float32 ), sgy=sgy.astype( np.float32 ),
                 blur1=blur1, blur3=blur3,
                 curv=curv.astype( np.float32 ), curv_wide=curv_wide.astype( np.float32 ) )


def field_at( name, e, n, order=1 ):
    """ A heightfield's field at plan points (arrays), bilinear. """
    f = heightfield()[name]
    rows = ( np.asarray( n, np.float64 ) + FIELD_EXT ) / FIELD_PX - 0.5
    cols = ( np.asarray( e, np.float64 ) + FIELD_EXT ) / FIELD_PX - 0.5
    shape = np.shape( rows )
    return ndimage.map_coordinates( f, [ np.ravel( rows ), np.ravel( cols ) ], order=order, mode="nearest" ).reshape( shape )


@functools.lru_cache( maxsize=1 )
def detail_tiles():
    """ Tileable noise for the land's texture, sampled at world coordinates: TILE inches across each. """
    rng = np.random.default_rng( 77 )
    n = 1024
    out = {}
    for name, beta, longest, shortest in ( ( "large", 2.6, 512, 6 ), ( "mid", 2.2, 256, 3 ), ( "fine", 1.8, 128, 1.5 ),
                                           ( "grain", 1.0, 32, 1.0 ) ):
        out[name] = noise( rng, ( n, n ), beta, longest, shortest )
    # Crowns of trees seen from above, about 220 in apart in a 20000 in tile: a cell's middle 1, its edge 0.
    from scipy.spatial import cKDTree
    pts = rng.random( ( 9000, 2 ) ) * n
    copies = np.concatenate( [ pts + np.array( ( dx * n, dy * n ) ) for dx in ( -1, 0, 1 ) for dy in ( -1, 0, 1 ) ] )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 )
    d, _ = cKDTree( copies ).query( np.stack( [ xx.ravel(), yy.ravel() ], -1 ), k=2, workers=-1 )
    f1, f2 = d[:, 0].reshape( n, n ), d[:, 1].reshape( n, n )
    out["crowns"] = np.clip( 1.0 - f1 / ( 0.5 * ( f1 + f2 ) + 1e-6 ), 0, 1 ).astype( np.float32 )
    return out


TILE = { "large": 60000.0, "mid": 14000.0, "fine": 3000.0, "grain": 600.0, "crowns": 20000.0 }


def tile_at( name, e, n ):
    t = detail_tiles()[name]
    k = t.shape[0] / TILE[name]
    return ndimage.map_coordinates( t, [ ( np.ravel( n ) * k ) % t.shape[0], ( np.ravel( e ) * k ) % t.shape[1] ], order=1,
                                    mode="grid-wrap" ).reshape( np.shape( e ) )


def classify( e, n ):
    """ What covers the land at plan points: weights ( meadow, forest, alpine, rock, scree, snow ) summing to 1, and the
    fields they came from. """
    z = field_at( "H", e, n )
    gx, gy = field_at( "sgx", e, n ), field_at( "sgy", e, n )     # the slope a few texels across, not the grain's
    slope = np.hypot( gx, gy )
    curv = field_at( "curv", e, n ) + 0.6 * field_at( "curv_wide", e, n )
    large, mid, fine = tile_at( "large", e, n ), tile_at( "mid", e, n ), tile_at( "fine", e, n )
    r = np.hypot( e, n )
    north = np.clip( -gy / np.maximum( slope, 1e-3 ), -1, 1 ) * smoothstep( 0.1, 0.5, slope )     # faces north
    treeline = 6200 + 1300 * large + 500 * mid
    snowline = 8300 + 1100 * large + 600 * mid - 1500 * north - 1400 * np.clip( curv * 2.5, -0.8, 1 )
    steep = smoothstep( 0.8, 1.25, slope + 0.12 * mid + 0.06 * fine )
    snow = smoothstep( snowline - 300, snowline + 500, z ) * ( 1 - smoothstep( 1.0, 1.55, slope + 0.15 * fine - 0.25 * np.clip( curv * 2, -1, 1 ) ) )
    high = smoothstep( treeline - 300, treeline + 600, z + 400 * fine )
    # Forest: below the tree line on slopes it can hold, in stands with clearings, kept off the plant's cleared ground.
    stands = smoothstep( -0.35, 0.35, mid + 0.7 * large + 0.35 * fine + 0.3 )
    perimeter = smoothstep( SITE + 500, SITE + 1400, np.maximum( np.abs( e ), np.abs( n ) ) + 300 * fine )
    forest = ( 1 - high ) * ( 1 - smoothstep( 0.75, 1.1, slope ) ) * stands * perimeter
    rock = np.clip( steep + high * smoothstep( -0.2, 0.4, -curv * 1.5 + 0.4 * mid ) * 0.8, 0, 1 )
    scree = high * ( 1 - steep ) * smoothstep( 0.3, 0.7, slope + 0.2 * fine ) * smoothstep( -0.1, 0.4, curv * 1.5 + 0.3 * mid )
    w_snow = snow
    w_rock = ( 1 - w_snow ) * rock
    w_scree = ( 1 - w_snow ) * ( 1 - w_rock ) * np.clip( scree, 0, 1 )
    rest = ( 1 - w_snow ) * ( 1 - w_rock ) * ( 1 - w_scree )
    w_forest = rest * forest
    w_alpine = ( rest - w_forest ) * high
    w_meadow = rest - w_forest - w_alpine
    return dict( meadow=w_meadow, forest=w_forest, alpine=w_alpine, rock=w_rock, scree=w_scree, snow=w_snow,
                 z=z, slope=slope, curv=curv, r=r, mid=mid, fine=fine, large=large )


def land():
    """ The land's texture: LAND_W x LAND_H texels in log-polar rows (row 0 the outer edge, LAND_R1; the last the inner
    one, LAND_R0), column 0 due north and on clockwise. Colour from classify()'s cover, each with its own detail; the
    normal map's heights are what the mesh doesn't carry (the field less its blur at the mesh's spacing, crowns,
    strata, grain), scaled to LAND_REF inches a texel (a texel is LAND_STEP times its radius across), so riverdale_materials'
    one pixels-per-inch gives each row its own true slopes. """
    W, H = LAND_W, LAND_H
    colour = np.zeros( ( H, W, 3 ), np.float32 )
    rough = np.zeros( ( H, W ), np.float32 )
    height = np.zeros( ( H, W ), np.float32 )
    ao = np.zeros( ( H, W ), np.float32 )
    a = 2 * math.pi * ( np.arange( W ) + 0.5 ) / W
    pal = { k: srgb_lin( c ) for k, c in dict(
        meadow=( 82, 92, 54 ), meadow_dry=( 112, 108, 70 ), meadow_wet=( 60, 72, 44 ), forest=( 30, 44, 32 ),
        forest_top=( 50, 68, 44 ), forest_gap=( 16, 22, 18 ), alpine=( 118, 110, 78 ), alpine_dark=( 86, 84, 66 ),
        rock=( 136, 132, 126 ), rock_dark=( 92, 88, 84 ), rock_warm=( 140, 126, 108 ), lichen=( 118, 116, 98 ),
        scree=( 146, 140, 132 ), snow=( 236, 238, 242 ), snow_dirty=( 196, 196, 194 ) ).items() }
    for r0 in range( 0, H, 128 ):
        rows = np.arange( r0, min( H, r0 + 128 ) )
        vv = 1.0 - ( rows + 0.5 ) / H
        R = LAND_R0 * np.exp( vv * H * LAND_STEP )
        RR, AA = np.meshgrid( R, a, indexing="ij" )
        e, n = RR * np.sin( AA ), RR * np.cos( AA )
        c = classify( e, n )
        grain = tile_at( "grain", e, n )
        crowns = tile_at( "crowns", e, n )
        fine, mid = c["fine"], c["mid"]
        z = c["z"]
        # Meadow: wet grass after the rain, drier patches, darker hollows.
        meadow = mix( pal["meadow"], pal["meadow_dry"], smoothstep( 0.2, 1.4, mid + 0.4 * fine )[..., None] )
        meadow = mix( meadow, pal["meadow_wet"], smoothstep( 0.0, 0.3, c["curv"] )[..., None] * 0.6 )
        meadow = meadow * ( 1 + 0.1 * grain )[..., None]
        # Forest: crowns lit on top, dark gaps between them.
        crown = smoothstep( 0.15, 0.75, crowns )
        forest = mix( pal["forest_gap"], mix( pal["forest"], pal["forest_top"], smoothstep( 0.5, 1.0, crowns )[..., None] ), crown[..., None] )
        forest = forest * ( 1 + 0.12 * mid )[..., None]
        # Rock: strata running level, warmer and darker bands, lichen on the gentler parts.
        strata = np.sin( z / 140.0 + 2.4 * mid + 0.8 * fine )
        rock = mix( pal["rock"], pal["rock_dark"], smoothstep( 0.4, 0.95, strata )[..., None] * 0.7 )
        rock = mix( rock, pal["rock_warm"], smoothstep( 0.6, 1.6, fine )[..., None] * 0.5 )
        rock = mix( rock, pal["lichen"], ( smoothstep( 0.8, 0.5, c["slope"] ) * smoothstep( 0.4, 1.2, mid ) )[..., None] * 0.5 )
        rock = rock * ( 1 + 0.06 * grain + 0.06 * fine )[..., None]
        rock = mix( rock, pal["rock_dark"], smoothstep( 0.1, 0.6, c["curv"] )[..., None] * 0.5 )      # dark in the gullies
        alpine = mix( pal["alpine"], pal["alpine_dark"], smoothstep( -0.5, 0.8, fine )[..., None] ) * ( 1 + 0.08 * grain )[..., None]
        scree = pal["scree"][None, None, :] * ( 1 + 0.18 * grain + 0.06 * fine )[..., None]
        snow = mix( pal["snow"], pal["snow_dirty"], ( smoothstep( 0.3, 0.0, c["snow"] ) * 0.8 + smoothstep( 0.8, 1.6, fine ) * 0.15 )[..., None] )
        out = ( meadow * c["meadow"][..., None] + forest * c["forest"][..., None] + alpine * c["alpine"][..., None] +
                rock * c["rock"][..., None] + scree * c["scree"][..., None] + snow * c["snow"][..., None] )
        colour[rows] = out
        rough[rows] = ( 0.86 * c["meadow"] + 0.9 * c["forest"] + 0.85 * c["alpine"] + 0.78 * c["rock"] + 0.82 * c["scree"] +
                        0.5 * c["snow"] )
        # Heights for the normal map: the field less its blur at the mesh's spacing, and each cover's own relief.
        blur = np.where( RR < NEAR_RING[1], field_at( "blur1", e, n ), field_at( "blur3", e, n ) )
        relief = ( z - blur ) * 0.8
        relief += c["forest"] * crowns * 160.0
        relief += c["rock"] * ( 30.0 * smoothstep( 0.2, 0.9, strata ) + 25.0 * fine + 8.0 * grain )
        relief += ( c["scree"] + c["alpine"] ) * 10.0 * grain + c["meadow"] * 3.0 * grain + c["snow"] * 6.0 * fine
        texel = RR * LAND_STEP
        height[rows] = relief * ( LAND_REF / texel )
        ao[rows] = np.clip( 1.0 - c["forest"] * ( 1 - crown ) * 0.55 - c["rock"] * smoothstep( 0.3, 0.95, strata ) * 0.25, 0.3, 1 )
    return dict( colour=colour, rough=rough, height=height, ppi=1.0 / LAND_REF, ao=ao )


EXTRA_SURFACES = {
    "rv_bd_dome": ( DOME_TEX[0], 0.0, dome_concrete ),
    "rv_bd_tower": ( TOWER_TEX[0], 0.0, tower_concrete ),
    "rv_bd_land": ( 1024.0, 0.0, land ),
    "rv_bd_conifer_a": ( 64.0, 0.0, lambda: conifer( "a" ) ),
    "rv_bd_conifer_b": ( 64.0, 0.0, lambda: conifer( "b" ) ),
    "rv_bd_conifer_c": ( 64.0, 0.0, lambda: conifer( "c" ) ),
}
EXTRA_PAINTS = {
    "rv_bd_bark": ( ( 56, 46, 40 ), 0.0, 0.9, 0 ),
    "rv_bd_fill": ( ( 30, 34, 34 ), 0.0, 0.95, 0 ),            # a tower's fill packs and rain zone, seen through the inlet
    "rv_bd_membrane": ( ( 74, 76, 78 ), 0.0, 0.7, 0 ),          # flat roofs' membrane
    "rv_bd_glass": ( ( 40, 52, 64 ), 0.4, 0.06, 0 ),           # office windows, reflecting the sky
    "rv_bd_mullion": ( ( 92, 96, 100 ), 0.6, 0.4, 0 ),
    "rv_bd_water": ( ( 30, 36, 38 ), 0.0, 0.05, 0 ),           # a cooling tower's basin
}
# Mean colours for riverdale_map's flat previews, which take a textured paint's colour from its picture in Assets.
PREVIEW_COLOURS = { "rv_bd_dome": ( 0.56, 0.56, 0.54 ), "rv_bd_tower": ( 0.58, 0.58, 0.55 ), "rv_bd_land": ( 0.30, 0.34, 0.26 ),
                    "rv_bd_conifer_a": ( 0.16, 0.24, 0.17 ), "rv_bd_conifer_b": ( 0.20, 0.25, 0.15 ),
                    "rv_bd_conifer_c": ( 0.13, 0.19, 0.15 ) }


# ---------------------------------------------------------------------------------------------------------------------
# Containment domes

def dome_uv( c ):
    """ UVs on the dome's wall picture for flat faces near the wall: u along the face, v up (DOME_TEX). """
    return wall_uv( DOME_TEX )


def stair_tower( m, base, out, z1, width=120.0, depth=110.0, flight=120.0 ):
    """ An open steel stair tower against a wall: four columns, a landing every flight, flights zig-zagging between them
    with hand rails, and cross bracing on its outer face. base is the foot of its outer face's middle, out away from the
    wall. """
    out = P.unit( ( out[0], out[1], 0.0 ) )
    right = np.cross( UP, out )
    base = v( *base )
    corners = [ base + right * ( width / 2 ) * sr + out * dd for sr in ( -1, 1 ) for dd in ( 0.0, -depth ) ]
    for p in corners:
        P.obox( m, p + UP * ( z1 / 2 ), right, ( 8, 8, z1 ), "rv_steel" )
    levels = np.arange( flight, z1 + 1, flight )
    for k, z in enumerate( levels ):
        mid = base - out * ( depth / 2 ) + UP * z
        P.obox( m, mid, right, ( width, depth, 4 ), { "default": "rv_steel", "+z": "rv_grating" } )
        P.railing( m, [ base + right * ( -width / 2 ) + UP * 0, base + right * ( width / 2 ) ], z, height=42, post_every=60,
                   kick=True )
        # The flight up to here, alternating sides.
        side = 1 if k % 2 == 0 else -1
        a = base - out * ( depth * 0.25 ) + right * ( -width / 2 + 12 ) * side + UP * ( z - flight )
        b = base - out * ( depth * 0.75 ) + right * ( width / 2 - 12 ) * side + UP * z
        m.beam( a, b, ( 3, 36 ), "rv_steel" )
        rod4( m, a + UP * 36 + out * 18, b + UP * 36 + out * 18, 1.0, "rv_yellow" )
    for z0, z1_ in zip( np.concatenate( [ [ 0.0 ], levels[:-1] ] ), levels ):
        a, b = corners[0] + UP * z0, corners[2] + UP * z1_
        rod4( m, a, b, 1.5, "rv_steel" )
        rod4( m, corners[2] + UP * z0, corners[0] + UP * z1_, 1.5, "rv_steel" )


def dome( m, sx, near ):
    """ One unit's containment building (sx 1 east UNIT 1, -1 west UNIT 2). """
    c = v( sx * DOME_E, DOME_N, 0 )
    unit = "unit1" if sx > 0 else "unit2"
    sides = 96
    u_round = round( 2 * math.pi * DOME_R / DOME_TEX[0] )
    W, TH = DOME_WALL, DOME_TEX[1]
    # The wall, the ring beam at the spring line and the dome over it, one picture round them (v by height: the dome's
    # arc squeezed into what's left of the picture over the wall).
    lathe_uv( m, "rv_bd_dome", c, [ ( DOME_R, 0.0 ), ( DOME_R, W - 64 ) ], sides, u_round, [ 0.0, ( W - 64 ) / TH ] )
    ring = [ ( DOME_R, W - 64 ), ( DOME_R + 26, W - 58 ), ( DOME_R + 30, W - 52 ), ( DOME_R + 30, W + 18 ), ( DOME_R + 22, W + 28 ),
             ( DOME_R - 1.5, W + 46 ) ]
    lathe_uv( m, "rv_bd_dome", c, ring, sides, u_round, [ ( W - 64 + k * 22 ) / TH for k in range( len( ring ) ) ] )
    steps = 18
    cap = []
    for k in range( steps + 1 ):
        t = math.pi / 2 * ( 0.035 + 0.965 * k / steps )
        cap.append( ( DOME_R * math.cos( t ) - 1.5 * math.cos( t ), W + DOME_RISE * math.sin( t ) ) )
    cap[-1] = ( 0.0, W + DOME_RISE )
    arc = [ 0.0 ]
    for ( r0, z0 ), ( r1, z1 ) in zip( cap, cap[1:] ):
        arc.append( arc[-1] + math.hypot( r1 - r0, z1 - z0 ) )
    v0 = ( W + 46 ) / TH
    lathe_uv( m, "rv_bd_dome", c, cap, sides, u_round, [ v0 + ( 0.995 - v0 ) * s / arc[-1] for s in arc ] )
    # The crown: a vent cap with warning lights on a short mast.
    P.cylinder( m, c, 70, W + DOME_RISE - 6, W + DOME_RISE + 30, "rv_plinth", 16, top="rv_steel" )
    P.cylinder( m, c, 6, W + DOME_RISE + 30, W + DOME_RISE + 150, "rv_steel", 6 )
    for k in range( 3 ):
        d = v( math.cos( k * 2.1 ), math.sin( k * 2.1 ), 0 )
        P.beacon( m, f"crown beacon {sx} {k}", c + d * 8 + UP * ( W + DOME_RISE + 150 ), light=False )
    # The ring beam's walkway: a railing round its top, warning lights on it.
    P.railing( m, [ ( c[0] + ( DOME_R + 27 ) * math.cos( a ), c[1] + ( DOME_R + 27 ) * math.sin( a ) )
                    for a in np.linspace( 0, 2 * math.pi, 49 ) ], W + 18, height=40, post_every=140, kick=False, posts=True )
    for k in range( 12 ):
        a = 2 * math.pi * ( k + 0.5 ) / 12
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.beacon( m, f"dome beacon {sx} {k}", c + d * ( DOME_R + 31 ) + UP * ( W + 18 ), light=False )
    to_yard = P.unit( v( 600 * sx - c[0], -1010 - c[1], 0 ) )
    base_a = math.atan2( to_yard[1], to_yard[0] )
    hand = 1 if sx > 0 else -1

    def at( da, r ):
        a = base_a + da * hand
        d = v( math.cos( a ), math.sin( a ), 0 )
        return d, c + d * r

    # Three tendon buttresses 120 degrees apart, away from the yard's face, up to the ring beam.
    for da in ( math.radians( 62 ), math.radians( 182 ), math.radians( 302 ) ):
        d, p = at( da, DOME_R + 13 )
        right = np.cross( UP, d )
        uv_box( m, "rv_bd_dome", p + UP * ( ( W - 58 ) / 2 ), ( right, d, UP ), ( 86, 30, W - 58 ), wall_uv( DOME_TEX ),
                skip=( "-z", "-y" ) )
        uv_box( m, "rv_bd_dome", p + d * 4 + UP * 18, ( right, d, UP ), ( 110, 46, 36 ), wall_uv( DOME_TEX ), skip=( "-z", "-y" ) )
    # The face towards the yard: the logo and the name, and the red banner to their right as the yard sees it.
    for name, da, z, h, kind in ( ( "logo", 0.0, 1150.0, 300.0, "dark" ), ( "wordmark", 0.0, 920.0, 150.0, "dark" ) ):
        a = base_a + da
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.letters( m, name, c + d * ( DOME_R + 0.6 ) + UP * z, np.cross( UP, d ), h, kind )
    a = base_a + math.radians( 17 )
    d = v( math.cos( a ), math.sin( a ), 0 )
    P.plate( m, unit, c + d * ( DOME_R + 1.0 ) + UP * 1010, np.cross( UP, d ), 420 )
    # Pipes up the side on their saddles, and two cable trays beside them on brackets.
    for k, ( da, r ) in enumerate( ( ( 0.42, 14.0 ), ( 0.46, 10.0 ), ( 0.5, 10.0 ), ( -0.45, 12.0 ) ) ):
        d, p = at( da, DOME_R + 24 + r )
        P.pipe( m, [ p + UP * 0, p + UP * ( W - 80 ) ], r, "rv_pipe", 10, caps=False, flanges=() )
        for z in np.arange( 160, W - 80, 180 ):
            P.obox( m, c + d * ( DOME_R + 12 ) + UP * z, np.cross( UP, d ), ( r * 1.6, 24, 6 ), "rv_steel" )
    for da in ( 0.36, -0.39 ):
        d, p = at( da, DOME_R + 10 )
        right = np.cross( UP, d )
        P.obox( m, p + d * 8 + UP * ( W / 2 - 20 ), right, ( 24, 2, W - 120 ), "rv_galv" )
        for sg in ( -1, 1 ):
            P.obox( m, p + d * 11 + right * 12 * sg + UP * ( W / 2 - 20 ), right, ( 1.5, 6, W - 120 ), "rv_galv" )
        for z in np.arange( 120, W - 100, 96 ):
            P.obox( m, p + d * 4 + UP * z, right, ( 32, 8, 3 ), "rv_steel" )
    # The equipment hatch: a steel door in its bolted ring, with its rails and a canopy over it.
    d, p = at( 0.22, DOME_R )
    right = np.cross( UP, d )
    hc = p + UP * 660                          # over the auxiliary buildings' roofs, as the yard sees it
    for r_, depth, paint in ( ( 168, 10, "rv_steel" ), ( 150, 22, "rv_steel" ), ( 132, 16, "rv_door" ) ):
        P.rod( m, hc - d * 4, hc + d * depth, r_, paint, 28, caps=True )
    for k in range( 24 ):
        a = 2 * math.pi * k / 24
        q = hc + d * 11 + ( right * math.cos( a ) + UP * math.sin( a ) ) * 159
        P.obox( m, q, right, ( 4, 4, 4 ), "rv_dark" )
    for sg in ( -1, 1 ):
        P.obox( m, hc + right * 60 * sg + d * 26, right, ( 10, 6, 200 ), "rv_steel" )
    P.obox( m, hc + d * 40 + UP * 190, right, ( 380, 80, 8 ), "rv_steel" )
    # The personnel airlock, 520 in up, reached by an open stair tower that climbs on to the ring beam's walkway.
    d, p = at( -0.62, DOME_R )
    right = np.cross( UP, d )
    lock = p + UP * 520
    P.rod( m, lock - d * 4, lock + d * 96, 62, "rv_steel", 20, caps=False )
    P.rod( m, lock + d * 96, lock + d * 104, 72, "rv_steel", 20, caps=True )
    P.obox( m, lock + d * 106 - UP * 6, right, ( 56, 2, 84 ), "rv_door" )
    platform = lock + d * 160 - UP * 60
    P.obox( m, platform, right, ( 220, 120, 4 ), { "default": "rv_steel", "+z": "rv_grating" } )
    P.railing( m, [ platform + d * 60 + right * -110, platform + d * 60 + right * 110 ], platform[2] + 2, height=42, kick=True )
    stair_tower( m, p + d * 340 + right * 0, d, W + 18, width=130, depth=120, flight=128 )
    # The vent stack beside it, with its platforms, caged ladder and warning lights, and the duct to its foot.
    sc = c + v( 0, 1, 0 ) * ( DOME_R + 700 ) + v( sx, 0, 0 ) * 500
    stack = [ ( 140, 0 ), ( 136, 400 ), ( 124, 2400 ), ( 122, 2560 ), ( 124, 2600 ) ]
    lathe_uv( m, "rv_bd_dome", sc, stack, 24, 1, [ 0.0, 0.18, 0.62, 0.68, 0.69 ] )
    P.cylinder( m, sc, 110, 2600, 2620, "rv_dark", 24, top="rv_black" )
    for z in ( 800.0, 1600.0, 2380.0 ):
        rr = np.interp( z, [ s[1] for s in stack ], [ s[0] for s in stack ] )
        P.cylinder( m, sc, rr + 40, z, z + 6, "rv_steel", 24, top="rv_grating", bottom="rv_steel" )
        P.railing( m, [ ( sc[0] + ( rr + 38 ) * math.cos( a ), sc[1] + ( rr + 38 ) * math.sin( a ) ) for a in np.linspace( 0, 2 * math.pi, 17 ) ],
                   z + 6, height=40, post_every=90, kick=False )
    ld = P.unit( v( -sx, -1, 0 ) )
    lr = np.cross( UP, ld )
    for sg in ( -1, 1 ):
        rod4( m, sc + ld * 150 + lr * 10 * sg, sc + ld * 128 + lr * 10 * sg + UP * 2600, 1.2, "rv_steel" )
    for z in np.arange( 200, 2560, 60 ):
        rr = np.interp( z, [ s[1] for s in stack ], [ s[0] for s in stack ] )
        for k in range( 5 ):
            a0, a1 = math.pi * k / 5, math.pi * ( k + 1 ) / 5
            q0 = sc + ld * ( rr + 10 + 16 * math.sin( a0 ) ) + lr * ( -16 * math.cos( a0 ) ) + UP * z
            q1 = sc + ld * ( rr + 10 + 16 * math.sin( a1 ) ) + lr * ( -16 * math.cos( a1 ) ) + UP * z
            rod4( m, q0, q1, 0.6, "rv_steel" )
    for k in range( 4 ):
        P.beacon( m, f"stack beacon {sx} {k}", sc + v( math.cos( k * math.pi / 2 ), math.sin( k * math.pi / 2 ), 0 ) * 120 + UP * 2620, light=False )
        P.beacon( m, f"stack mid beacon {sx} {k}", sc + v( math.cos( k * math.pi / 2 + 0.7 ), math.sin( k * math.pi / 2 + 0.7 ), 0 ) * 150 + UP * 1606, light=False )
    fx = sx * ( DOME_E - DOME_R - 420 )
    duct_a, duct_b = v( fx, DOME_N + 900, 360 ), v( sc[0] - sx * 140, sc[1], 360 )
    near.beam( duct_a, v( duct_b[0], duct_a[1], 360 ), ( 70, 60 ), "rv_galv" )
    near.beam( v( duct_b[0], duct_a[1], 360 ), duct_b, ( 70, 60 ), "rv_galv" )
    for t in np.linspace( 0.08, 0.92, 6 ):
        q = duct_a + ( v( duct_b[0], duct_a[1], 360 ) - duct_a ) * t
        P.obox( near, q - UP * 180, v( 1, 0, 0 ), ( 8, 8, 330 ), "rv_steel" )
    # Auxiliary buildings round its foot, towards the play area: blocks with window bands, roof plant, a door and lamps.
    rng = np.random.default_rng( 11 if sx > 0 else 12 )
    for n0, n1, h in ( ( DOME_N - 900, DOME_N - 200, 420 ), ( DOME_N - 200, DOME_N + 500, 520 ), ( DOME_N + 500, DOME_N + 1300, 380 ) ):
        a_, b_ = sorted( ( fx - sx * 260, fx + sx * 260 ) )
        office( near, a_, b_, n0, n1, h, rng, faces=( "-e" if sx > 0 else "+e", ), plant=True )
        out = v( -sx, 0, 0 )
        right = np.cross( UP, out )
        face = fx - sx * 260
        P.door( near, ( face, ( n0 + n1 ) / 2, 0 ), right, 110, 130 )
        P.wall_light( near, f"Aux lamp {sx} {n0}", ( face, ( n0 + n1 ) / 2, 160 ), out, "warm", 1, light=False )
        P.louvre( near, ( face, ( n0 + n1 ) / 2 + 200, h - 120 ), right, 160, 100 )
    # A pipe bridge from the plant's boundary out to the auxiliary buildings, above the spawn's roofs.
    for nn in ( DOME_N + 700, DOME_N + 760 ):
        P.truss( near, ( sx * 2600, nn, 470 ), ( fx - sx * 260, nn, 470 ), 50, "rv_steel", panel=80 )
    for k, r in enumerate( ( 14.0, 10.0, 8.0 ) ):
        P.pipe( near, [ ( sx * 2600, DOME_N + 712 + k * 22, 520 + r ), ( fx - sx * 260, DOME_N + 712 + k * 22, 520 + r ) ], r, "rv_pipe", 10, caps=False )


# ---------------------------------------------------------------------------------------------------------------------
# Cooling towers

def tower_profile( h ):
    """ The shell's ( radius, height ) from the lintel up: a hyperboloid narrowing to a throat at 78% of its height, then
    flaring a little to the lip. """
    r_base, r_throat, r_top = h * 0.36, h * 0.215, h * 0.235
    z0, z_throat = h * 0.075, h * 0.78
    prof = []
    for t in np.linspace( 0, 1, 34 ):
        z = z0 + ( h - z0 ) * t
        if z <= z_throat:
            s = ( z_throat - z ) / ( z_throat - z0 )
            r = r_throat * math.sqrt( 1 + ( ( r_base / r_throat ) ** 2 - 1 ) * s * s )
        else:
            s = ( z - z_throat ) / ( h - z_throat )
            r = r_throat * math.sqrt( 1 + ( ( r_top / r_throat ) ** 2 - 1 ) * s * s )
        prof.append( ( r, z ) )
    return prof


def cooling_tower( m, e, n, h ):
    """ A natural draught cooling tower: the hyperboloid shell (rv_bd_tower) with its lintel ring and the stiffening ring
    at its lip, the inside of its top, the raking columns crossing over the air inlet, the dark fill behind them, the
    basin's wall, and warning lights on the lip. """
    prof = tower_profile( h )
    sides = 72
    arc = [ 0.0 ]
    for ( r0, z0 ), ( r1, z1 ) in zip( prof, prof[1:] ):
        arc.append( arc[-1] + math.hypot( r1 - r0, z1 - z0 ) )
    rot = ( e * 0.37 + n * 0.11 ) % 1.0          # each tower's picture turned a little differently
    lathe_uv( m, "rv_bd_tower", ( e, n ), prof, sides, 5.0, [ 0.004 + 0.99 * s / arc[-1] for s in arc ], a0=rot * 2 * math.pi )
    r_top, z_top = prof[-1]
    r_base, z0 = prof[0]
    # The lip's stiffening ring: out, up and over, and back down inside.
    lip = [ ( r_top, z_top ), ( r_top + 22, z_top + 4 ), ( r_top + 24, z_top + 46 ), ( r_top + 6, z_top + 58 ), ( r_top - 14, z_top + 58 ) ]
    lathe_uv( m, "rv_bd_tower", ( e, n ), lip, sides, 5.0, [ 0.995, 0.996, 0.997, 0.998, 0.999 ], a0=rot * 2 * math.pi )
    # The inside of the top, seen over the lip from above: darker, wetter.
    inside = [ ( r - 14, z ) for r, z in prof[-9:] ] + [ ( r_top - 14, z_top + 58 ) ]
    lathe_uv( m, "rv_bd_tower", ( e, n ), inside, sides, 5.0, [ 0.7 + 0.03 * k for k in range( len( inside ) ) ], inward=True )
    # The lintel ring where the shell sits on its columns.
    lathe_uv( m, "rv_bd_tower", ( e, n ), [ ( r_base - 18, z0 - 30 ), ( r_base + 14, z0 - 30 ), ( r_base + 14, z0 + 10 ), ( r_base, z0 + 18 ) ],
              sides, 5.0, [ 0.0, 0.001, 0.003, 0.004 ] )
    # Raking columns: pairs from each point on the lintel, out and down to either side, crossing their neighbours' as
    # X braces.
    pairs = 44
    for k in range( pairs ):
        a0 = 2 * math.pi * k / pairs
        top = v( e + ( r_base - 2 ) * math.cos( a0 ), n + ( r_base - 2 ) * math.sin( a0 ), z0 - 30 )
        for s in ( -1, 1 ):
            a1 = a0 + s * 2 * math.pi / pairs * 1.0
            foot = v( e + ( r_base + 30 ) * math.cos( a1 ), n + ( r_base + 30 ) * math.sin( a1 ), 0 )
            P.rod( m, top, foot, 16, "rv_plinth", 5 )
        P.cylinder( m, ( e + ( r_base + 30 ) * math.cos( a0 + math.pi / pairs ), n + ( r_base + 30 ) * math.sin( a0 + math.pi / pairs ) ),
                    26, 0, 22, "rv_plinth", 6, top="rv_plinth" )
    # The fill packs and the rain zone behind the columns: dark, under the shell.
    P.cylinder( m, ( e, n ), r_base - 70, 0, z0 + 40, "rv_bd_fill", 48 )
    # The basin: its wall (outside, top, inside) and the water between it and the columns.
    P.lathe( m, ( e, n ), [ ( r_base + 150, -20 ), ( r_base + 150, 54 ), ( r_base + 140, 54 ), ( r_base + 140, 20 ) ], "rv_plinth", 64 )
    P.lathe( m, ( e, n ), [ ( r_base + 140, 20 ), ( r_base - 70, 20 ) ], "rv_bd_water", 64 )
    for k in range( 6 ):
        a = 2 * math.pi * ( k + 0.25 ) / 6
        P.beacon( m, f"tower beacon {e:.0f} {k}", ( e + ( r_top + 26 ) * math.cos( a ), n + ( r_top + 26 ) * math.sin( a ), z_top + 58 ), light=False )


# ---------------------------------------------------------------------------------------------------------------------
# Terrain: forested hills and snowy mountains

def land_uv( r, a ):
    """ The land's texture coordinates at radius r and angle a (clockwise from north, not wrapped: a full turn is u 1). """
    return ( a / ( 2 * math.pi ), math.log( max( r, LAND_R0 ) / LAND_R0 ) / ( LAND_H * LAND_STEP ) )


def ring_mesh( m, r0, r1, na, nr, joint=None, half=None ):
    """ A polar ring of the land from r0 to r1, na steps round and nr out, its radii spaced evenly in log radius. Heights
    from the heightfield, normals from its slope, UVs from land_uv. joint: the coarser ring inside's step count, whose
    outer edge this one's inner edge follows exactly (its extra points on the coarse edges), so there are no cracks.
    half: 'east' or 'west' keeps only that half (by the quads' middle). """
    radii = r0 * np.exp( np.linspace( 0, math.log( r1 / r0 ), nr + 1 ) )
    angles = np.linspace( 0, 2 * math.pi, na + 1 )
    RR, AA = np.meshgrid( radii, angles, indexing="ij" )
    E, N = RR * np.sin( AA ), RR * np.cos( AA )
    Z = field_at( "blur1", E, N )
    if joint is not None:
        # The first ring on the coarser ring's chords.
        coarse = np.linspace( 0, 2 * math.pi, joint + 1 )
        ce, cn = r0 * np.sin( coarse ), r0 * np.cos( coarse )
        cz = field_at( "blur1", ce, cn )
        f = angles / ( 2 * math.pi ) * joint
        i0 = np.minimum( np.floor( f ).astype( int ), joint - 1 )
        t = f - i0
        E[0] = ce[i0] * ( 1 - t ) + ce[i0 + 1] * t
        N[0] = cn[i0] * ( 1 - t ) + cn[i0 + 1] * t
        Z[0] = cz[i0] * ( 1 - t ) + cz[i0 + 1] * t
    gx = ndimage.gaussian_filter( field_at( "gx", E, N ), 0.8 )
    gy = ndimage.gaussian_filter( field_at( "gy", E, N ), 0.8 )
    NR = np.stack( [ -gx, -gy, np.ones_like( gx ) ], -1 )
    NR /= np.linalg.norm( NR, axis=-1, keepdims=True )
    U = AA / ( 2 * math.pi )
    V = np.log( np.maximum( np.hypot( E, N ), LAND_R0 ) / LAND_R0 ) / ( LAND_H * LAND_STEP )
    count = 0
    for i in range( nr ):
        for j in range( na ):
            if half is not None:
                mid = ( angles[j] + angles[j + 1] ) / 2
                if ( half == "east" ) != ( mid < math.pi ):
                    continue
            ids = ( ( i, j ), ( i, j + 1 ), ( i + 1, j + 1 ), ( i + 1, j ) )
            pts = [ ( E[ij], N[ij], Z[ij] ) for ij in ids ]
            m.polygon( "rv_bd_land", pts, uv=[ ( U[ij], V[ij] ) for ij in ids ], normals=[ NR[ij] for ij in ids ] )
            count += 1
    return radii, angles, Z


def terrain( m, rng=None, half=None ):
    """ The land round the site: the near hills and the far mountains (see ring_mesh). Returns the far ring's radii,
    angles and heights (height_at reads them). """
    r0, r1, na, nr = NEAR_RING
    ring_mesh( m, r0, r1, na, nr, half=half )
    f0, f1, fa, fr = FAR_RING
    radii, angles, Z = ring_mesh( m, f0, f1, fa, fr, joint=na, half=half )
    return radii, angles[:-1], Z[:, :-1]


def height_at( radii, angles, H, e, n ):
    r = math.hypot( e, n )
    a = math.atan2( e, n ) % ( 2 * math.pi )
    if r < radii[0]:
        return 0.0
    i = int( np.clip( np.searchsorted( radii, r ) - 1, 0, len( radii ) - 2 ) )
    ti = ( r - radii[i] ) / ( radii[i + 1] - radii[i] )
    da = angles[1] - angles[0]
    j = int( a / da ) % len( angles )
    tj = ( a - j * da ) / da
    j1 = ( j + 1 ) % len( angles )
    h0 = H[i, j] * ( 1 - tj ) + H[i, j1] * tj
    h1 = H[i + 1, j] * ( 1 - tj ) + H[i + 1, j1] * tj
    return h0 * ( 1 - ti ) + h1 * ti


def pine( m, base, h, paint ):
    """ A conifer: a short trunk and three stacked cones (Spillway's backdrop uses it; Riverdale's are conifer()s). """
    e, n, z = base
    P.cylinder( m, ( e, n ), h * 0.025, z, z + h * 0.2, "rv_dark", 5 )
    for k, ( r, z0, z1 ) in enumerate( ( ( 0.30, 0.12, 0.55 ), ( 0.23, 0.38, 0.8 ), ( 0.15, 0.62, 1.0 ) ) ):
        sides = 7
        c = v( e, n, z + h * z0 )
        top = v( e, n, z + h * z1 )
        ring = [ c + v( math.cos( 2 * math.pi * s / sides + k ), math.sin( 2 * math.pi * s / sides + k ), 0 ) * ( r * h ) for s in range( sides ) ]
        for s in range( sides ):
            a, b = ring[s], ring[( s + 1 ) % sides]
            out = ( a + b ) / 2 - c
            nrm = [ P.unit( a - c + UP * ( r * h * 0.6 ) ), P.unit( b - c + UP * ( r * h * 0.6 ) ), UP ]
            card( m, paint, [ a, b, top ], out + UP * ( r * h * 0.5 ), normals=nrm )
        card( m, paint, ring, -UP )


def conifer_tree( m, base, h, rng, paint, tiers=7, branches=7, lean=( 0.0, 0.0 ) ):
    """ A spruce: a trunk and tiers of star-shaped cones, each tier's tips drooping past the next one down, narrowing up
    the tree to a spire. Each tier is one polygon fanned from its apex on the trunk, so it costs one point a triangle.
    UVs per conifer(): tips at whole u, the gaps between at halves, the apex at v 1. """
    base = v( *base )
    lx, ly = lean
    axis = P.unit( v( lx, ly, 1.0 ) )
    trunk_r = h * 0.014
    P.rod( m, base - UP * 20, base + axis * h * 0.3, trunk_r, "rv_bd_bark", 3 )
    turn = rng.uniform( 0, 2 * math.pi )
    for k in range( tiers ):
        t = k / ( tiers - 1 )
        zc = h * ( 0.12 + 0.8 * t ** 0.92 ) * rng.uniform( 0.97, 1.03 )
        R = h * ( 0.27 * ( 1 - t ) ** 0.9 + 0.035 ) * rng.uniform( 0.86, 1.12 )
        apex = base + axis * ( zc + R * ( 0.95 if k < tiers - 1 else 1.6 ) )
        centre = base + axis * zc
        nb = branches if k < tiers - 2 else max( 5, branches - 2 )
        pts, uvs, nrm = [ apex ], [ ( nb * 0.5, 1.0 ) ], [ UP ]
        turn += rng.uniform( 0.4, 1.4 )
        for s in range( 2 * nb + 1 ):
            phi = turn + math.pi * s / nb + ( rng.normal( 0, 0.12 ) if s % 2 == 0 and s < 2 * nb else 0.0 )
            d = v( math.cos( phi ), math.sin( phi ), 0 )
            if s % 2 == 0:
                rr = R * ( rng.uniform( 0.82, 1.15 ) if s < 2 * nb else 1.0 )
                p = centre + d * rr - UP * R * rng.uniform( 0.18, 0.34 )
                nn = P.unit( d * 1.0 + UP * 0.6 )
                uv = ( s * 0.5, 0.0 )
            else:
                p = centre + d * R * 0.5 + UP * R * 0.12
                nn = P.unit( d * 0.55 + UP * 0.85 )
                uv = ( s * 0.5, 0.3 )
            pts.append( p )
            uvs.append( uv )
            nrm.append( nn )
        # The closing tip is the first one again, a turn on in u.
        pts[-1], nrm[-1] = pts[1], nrm[1]
        m.polygon( paint, pts, uv=uvs, normals=nrm )


def forest( m, rng, radii=None, angles=None, H=None, near=None ):
    """ Conifers on the hills, by classify()'s forest cover: densest just past the plant's cleared perimeter, thinning
    into stands and clearings further out; none in the domes', towers' and crane's yards. Near ones (inside TREE_NEAR)
    go into near (if given) with more tiers. Returns how many. """
    count = 0
    tries = TREE_TRIES
    a = rng.uniform( 0, 2 * math.pi, tries )
    r = SITE * 1.02 + ( rng.random( tries ) ** 1.6 ) * ( 23000 - SITE )
    e, n = r * np.sin( a ), r * np.cos( a )
    c = classify( e, n )
    dens = c["forest"] * ( 0.35 + 0.65 * smoothstep( 16000, 7000, r ) )
    keep = rng.random( tries ) < dens
    for k in np.flatnonzero( keep ):
        ek, nk = float( e[k] ), float( n[k] )
        if any( math.hypot( ek - sx * DOME_E, nk - DOME_N ) < DOME_R + 1500 for sx in ( -1, 1 ) ):
            continue
        if any( math.hypot( ek - sx * te, nk - tn ) < th * 0.36 + 900 for te, tn, th in TOWERS for sx in ( -1, 1 ) ):
            continue
        zk = float( c["z"][k] ) - 10
        h = rng.uniform( 520, 1050 ) * ( 0.8 + 0.4 * float( smoothstep( -1, 1, c["mid"][k] ) ) )
        paint = ( "rv_bd_conifer_a", "rv_bd_conifer_b", "rv_bd_conifer_c" )[int( rng.integers( 0, 3 ) )]
        lean = ( rng.normal( 0, 0.03 ), rng.normal( 0, 0.03 ) )
        if r[k] < TREE_NEAR:
            conifer_tree( near if near is not None else m, ( ek, nk, zk ), h, rng, paint, tiers=8, branches=8, lean=lean )
        else:
            conifer_tree( m, ( ek, nk, zk ), h, rng, paint, tiers=5, branches=6, lean=lean )
        count += 1
    return count


def ground( m ):
    """ Flat gravel round the play area out to the plant's square (SITE); the land (terrain) takes over beyond. """
    # A ring round the play area, whose own ground (riverdale_map.ground) runs 400 past its edges: a slab under it
    # would cap the fuel pool, whose water is at -30.
    e0, e1, n0, n1 = -2600, 2600, -2050, 2750
    for a, b, c, d in ( ( -SITE, SITE, -SITE, n0 ), ( -SITE, SITE, n1, SITE ), ( -SITE, e0, n0, n1 ), ( e1, SITE, n0, n1 ) ):
        box( m, a, b, c, d, -30, -24, { "default": None, "+z": "rv_gravel" } )


# ---------------------------------------------------------------------------------------------------------------------
# The tower crane and service blocks

def lattice( m, a, b, size, panel, paint="rv_yellow", chord=3.0, brace=1.4, up=UP ):
    """ A square lattice member from a to b: four chords, and zig-zag braces on each face. """
    a, b = v( *a ), v( *b )
    d = P.unit( b - a )
    side = P.unit( np.cross( up, d ) ) if np.linalg.norm( np.cross( up, d ) ) > 1e-6 else v( 1, 0, 0 )
    upv = np.cross( d, side )
    L = float( np.linalg.norm( b - a ) )
    s = size / 2
    corners = [ side * sx * s + upv * sy * s for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
    for cc in corners:
        rod4( m, a + cc, b + cc, chord, paint )
    count = max( 1, int( round( L / panel ) ) )
    for i in range( count ):
        p0, p1 = a + d * ( L * i / count ), a + d * ( L * ( i + 1 ) / count )
        for f in range( 4 ):
            c0, c1 = corners[f], corners[( f + 1 ) % 4]
            if ( i + f ) % 2:
                rod4( m, p0 + c0, p1 + c1, brace, paint )
            else:
                rod4( m, p0 + c1, p1 + c0, brace, paint )
        rod4( m, p0 + corners[0], p0 + corners[2], brace * 0.8, paint ) if i % 3 == 0 else None


def tower_crane( m ):
    """ A flat-top tower crane: its foundation block, a lattice mast, the slewing unit and cab, the jib (a triangular
    lattice) out to the west-south-west with its trolley and hook block, the counter-jib with its walkway, railings and
    ballast, and the tower head's pendant ties. """
    e, n = CRANE
    h = 2300.0
    box( m, e - 110, e + 110, n - 110, n + 110, -30, 30, { "default": "rv_plinth", "+z": "rv_plinth" } )
    lattice( m, ( e, n, 30 ), ( e, n, h ), 96, 96 )
    # Slewing unit and cab.
    P.cylinder( m, ( e, n ), 62, h, h + 34, "rv_dark", 16, top="rv_yellow" )
    jib = P.unit( v( -1, -0.25, 0 ) )
    side = np.cross( UP, jib )
    cab = v( e, n, h + 34 ) + side * 74 + jib * 30
    P.obox( m, cab + UP * 50, jib, ( 96, 66, 100 ), { "default": "rv_white", "-z": "rv_dark" } )
    P.quad( m, "rv_bd_glass", cab + jib * 48.2 + UP * 62, side, UP, 58, 50 )
    P.quad( m, "rv_bd_glass", cab + side * 33.2 + UP * 62, -jib, UP, 80, 44 )
    # The jib: two bottom chords and a top chord, braced, out 2600 in; its root on the slewing unit.
    root = v( e, n, h + 40 )
    tip = root + jib * 2600
    for sg in ( -1, 1 ):
        rod4( m, root + side * 30 * sg, tip + side * 20 * sg, 3.0, "rv_yellow" )
    top_a, top_b = root + UP * 64, tip + UP * 40
    rod4( m, top_a, top_b, 3.0, "rv_yellow" )
    panels = 26
    for i in range( panels ):
        f0, f1 = i / panels, ( i + 1 ) / panels
        for sg in ( -1, 1 ):
            b0 = root + ( tip - root ) * f0 + side * ( 30 - 10 * f0 ) * sg
            b1 = root + ( tip - root ) * f1 + side * ( 30 - 10 * f1 ) * sg
            t0 = top_a + ( top_b - top_a ) * f0
            t1 = top_a + ( top_b - top_a ) * f1
            rod4( m, b0, t1 if i % 2 == 0 else t0, 1.4, "rv_yellow" )
            rod4( m, t0 if i % 2 == 0 else t1, b1, 1.4, "rv_yellow" )
        rod4( m, root + ( tip - root ) * f1 - side * ( 30 - 10 * f1 ), root + ( tip - root ) * f1 + side * ( 30 - 10 * f1 ), 1.2, "rv_yellow" )
    # Trolley and hook block on its ropes.
    tr = root + jib * 1500
    P.obox( m, tr - UP * 6, jib, ( 60, 70, 18 ), "rv_yellow" )
    for sg in ( -1, 1 ):
        rod4( m, tr - UP * 14 + side * 8 * sg, tr - UP * 880 + side * 8 * sg, 0.5, "rv_dark" )
    hook = tr - UP * 900
    P.obox( m, hook, jib, ( 30, 22, 40 ), "rv_yellow" )
    P.rod( m, hook - UP * 20, hook - UP * 46, 3, "rv_dark", 6 )
    # The counter-jib: a walkway between two chords, railings, the hoist winch and ballast blocks at its end.
    cj = root - jib * 920
    for sg in ( -1, 1 ):
        rod4( m, root + side * 40 * sg, cj + side * 40 * sg, 3.0, "rv_yellow" )
        rod4( m, root + side * 40 * sg + UP * 40, cj + side * 40 * sg + UP * 40, 1.2, "rv_yellow" )
    P.obox( m, ( root + cj ) / 2 - UP * 2, jib, ( 920, 70, 3 ), { "default": "rv_steel", "+z": "rv_grating" } )
    P.obox( m, root - jib * 420 + UP * 22, jib, ( 90, 70, 44 ), "rv_dark" )
    for k in range( 4 ):
        P.obox( m, cj + jib * ( 30 + 44 * k ) - UP * 50, side, ( 120, 40, 120 ), "rv_plinth" )
    # The tower head and its pendants to the jib and counter-jib.
    head = root + UP * 420
    for sg in ( -1, 1 ):
        rod4( m, root + side * 30 * sg, head + side * 6 * sg, 3.0, "rv_yellow" )
    rod4( m, head, root + jib * 1800 + UP * 52, 1.0, "rv_dark" )
    rod4( m, head, cj + UP * 40, 1.0, "rv_dark" )
    P.beacon( m, "crane beacon", head + UP * 4, light=False )
    P.beacon( m, "crane jib beacon", tip + UP * 42, light=False )


def office( m, e0, e1, n0, n1, h, rng, faces=( "-e", "+e", "-n", "+n" ), plant=True ):
    """ A plant office or service block: concrete walls with window bands (recessed glass, mullions, a sill and a head
    band), a parapet with its coping, downpipes, and roof plant: condensers with their fans, a louvred plant room, ducts
    and flues. """
    box( m, e0, e1, n0, n1, 0, h, { "default": "rv_wall", "+z": "rv_bd_membrane" } )
    # The parapet and its coping.
    t = 8
    for a, b, c, d in ( ( e0, e1, n0, n0 + t ), ( e0, e1, n1 - t, n1 ), ( e0, e0 + t, n0, n1 ), ( e1 - t, e1, n0, n1 ) ):
        box( m, a, b, c, d, h, h + 36, "rv_wall" )
        box( m, a - 1.5, b + 1.5, c - 1.5, d + 1.5, h + 36, h + 40, "rv_plinth" )
    # Window bands, a floor every 150 in: glass, mullions and a transom on it, a sill and a head band proud of the wall.
    walls = { "-e": ( v( e0, ( n0 + n1 ) / 2, 0 ), v( 0, -1, 0 ), n1 - n0 ), "+e": ( v( e1, ( n0 + n1 ) / 2, 0 ), v( 0, 1, 0 ), n1 - n0 ),
              "-n": ( v( ( e0 + e1 ) / 2, n0, 0 ), v( 1, 0, 0 ), e1 - e0 ), "+n": ( v( ( e0 + e1 ) / 2, n1, 0 ), v( -1, 0, 0 ), e1 - e0 ) }
    for face in faces:
        centre, right, length = walls[face]
        out = np.cross( right, UP )
        band = length * 0.84
        panes = max( 1, int( band // 60 ) )
        for z in np.arange( 150, h - 70, 150.0 ):
            c = centre + UP * ( z + 30 )
            P.quad( m, "rv_bd_glass", c, right, UP, band, 56, off=0.4 )
            if rng.random() < 0.18:
                P.quad( m, "rv_window_lit", c + right * rng.uniform( -band / 3, band / 3 ), right, UP, band * 0.25, 52, off=0.6 )
            for k in range( panes + 1 ):
                P.quad( m, "rv_bd_mullion", c + right * ( -band / 2 + band * k / panes ), right, UP, 3, 58, off=1.2 )
            P.quad( m, "rv_bd_mullion", c + UP * 8, right, UP, band, 2.5, off=1.2 )
            P.obox( m, c - UP * 31 + out * 2, right, ( band + 8, 4, 3 ), "rv_plinth" )
            P.obox( m, c + UP * 34 + out * 0.5, right, ( band + 4, 1, 10 ), "rv_plinth" )
        for sg in ( -1, 1 ):
            p = centre + right * ( length / 2 - 14 ) * sg + out * 4
            P.rod( m, p, p + UP * ( h + 20 ), 2.5, "rv_steel", 6 )
    if not plant:
        return
    # Roof plant.
    w, d = e1 - e0, n1 - n0
    cx, cy = ( e0 + e1 ) / 2, ( n0 + n1 ) / 2
    room_w, room_d = min( 220, w * 0.35 ), min( 180, d * 0.35 )
    box( m, cx - room_w / 2, cx + room_w / 2, cy - room_d / 2, cy + room_d / 2, h, h + 110, { "default": "rv_wall", "+z": "rv_bd_membrane" } )
    P.louvre( m, ( cx, cy - room_d / 2, h + 60 ), v( 1, 0, 0 ), room_w * 0.6, 60 )
    count = max( 1, int( w // 260 ) )
    for k in range( count ):
        ex = e0 + w * ( k + 0.5 ) / count
        ny = n0 + 50 if k % 2 == 0 else n1 - 90
        P.obox( m, v( ex, ny + 20, h + 24 ), v( 1, 0, 0 ), ( 110, 50, 48 ), "rv_white" )
        for f in ( -1, 1 ):
            P.cylinder( m, ( ex + f * 26, ny + 20 ), 20, h + 48, h + 50, "rv_dark", 12, top="rv_black" )
    for k in range( 2 ):
        fxp = cx + room_w / 2 + 40 + 60 * k
        P.cylinder( m, ( fxp, cy ), 9, h, h + 170 + 30 * k, "rv_zinc", 10 )
        P.cylinder( m, ( fxp, cy ), 13, h + 160 + 30 * k, h + 172 + 30 * k, "rv_zinc", 10, top="rv_dark" )
    m.beam( v( cx - room_w / 2, cy + 20, h + 70 ), v( e0 + 30, cy + 20, h + 70 ), ( 40, 30 ), "rv_galv" )
    P.obox( m, v( e0 + 40, cy + 20, h + 35 ), v( 1, 0, 0 ), ( 8, 8, 70 ), "rv_steel" )


def blocks( m, rng ):
    """ Service and office blocks round the plant's edge, beyond the play area. """
    spots = [ ( -3600, 3200, 900, 600, 520 ), ( 3700, 3300, 700, 500, 600 ), ( -1500, 3300, 1200, 400, 420 ), ( 1600, 3300, 1000, 400, 460 ),
              ( -3400, -3700, 900, 900, 700 ), ( 3500, -3800, 900, 900, 700 ), ( 0, -3600, 2600, 800, 1100 ), ( -4200, 2200, 500, 900, 380 ),
              ( 4200, 2200, 500, 900, 380 ) ]
    for k, ( e, n, w, d, h ) in enumerate( spots ):
        office( m, e - w / 2, e + w / 2, n - d / 2, n + d / 2, h, rng )
    return len( spots )


# ---------------------------------------------------------------------------------------------------------------------

_EXTRA = {}


def build():
    """ The far model (domes, towers) and the near one (crane, blocks, the domes' auxiliary buildings); the land and the
    trees are kept for extra_models(). """
    far, near = K.Model(), K.Model()
    rng = np.random.default_rng( 17 )
    for sx in ( -1, 1 ):
        dome( far, sx, near )
        for e, n, h in TOWERS:
            cooling_tower( far, sx * e, n, h )
    ground( far )
    tower_crane( near )
    blocks( near, rng )
    land_e, land_w = K.Model(), K.Model()
    terrain( land_e, rng, half="east" )
    terrain( land_w, rng, half="west" )
    trees_far, trees_near = K.Model(), K.Model()
    count = forest( trees_far, np.random.default_rng( 23 ), near=trees_near )
    _EXTRA.clear()
    _EXTRA.update( land_e=land_e, land_w=land_w, trees_far=trees_far, trees_near=trees_near )
    try:
        import railhead_preview as PV
        for paint, colour in PREVIEW_COLOURS.items():
            PV._colours.setdefault( paint, np.array( colour ) )
    except ImportError:
        pass
    print( f"backdrop: {count} conifers" )
    return far, near


def extra_models():
    """ The land in two halves and the trees, near and far: drawn only, casting no shadows. """
    if not _EXTRA:
        build()
    return [ ( "riverdale_backdrop_land_east", "Backdrop Land East", False, False, _EXTRA["land_e"] ),
             ( "riverdale_backdrop_land_west", "Backdrop Land West", False, False, _EXTRA["land_w"] ),
             ( "riverdale_backdrop_trees", "Backdrop Trees", False, False, _EXTRA["trees_far"] ),
             ( "riverdale_backdrop_trees_near", "Backdrop Trees Near", False, False, _EXTRA["trees_near"] ) ]
