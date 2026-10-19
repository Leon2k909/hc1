"""
Cerro Blanco's landscape, for Tools/cerroblanco_map.py: the white hill falling away round the museum's walls, drawn
only (no collision). It replaced a 500-inch grid of flat-shaded quads with 260 oaks on it.

- The ground keeps the old backdrop's lie (cerroblanco_map.terrain_z: level with the play at its edge, gentle to the
  north so only sky shows over the galleries' roofs from the courtyard, falling to the valley in the south and west,
  the sierra rising 2200 beyond 9000), and gets its detail on top, more of it the further out it is: rolling ground,
  gullies, the limestone outcrops the hill is named for, ridges and then the sierra's crests.
- A tensor grid (no cracks): 100 inches apart within 3000 of the play, 350 out to 14000, 1600 out to 46000, shaded
  smooth by the heightfield's own normals.
- One material over all of it, cbf_land (shaders/cerroblanco_land.shader, whose source is in Sources/CerroBlanco): the
  terrain's own drawn dry meadow, meadow, dirt and limestone (materials/terrain) at their real scale, blended by their
  own heights through a painted splat, land_splat.png. The ground used to be one paint per quad, which showed as
  stair-stepped patches from the air and along the hillsides.
- The splat spans the same grid, its texels spaced like the grid's lines, about five to a cell: 21-22 inches by the
  play, 73-77 out to 14000 and 334-354 beyond. texel_plan() gives each column's and row's plan position (the shader's
  MapAxis() turned round), and splat() evaluates height(), its slope and the noises the height is made of there, and
  paints soft versions of the rules the quads had:
  - rock on the steep ground, on the outcrops (the height's own rock noise) and up on the sierra, and partly on the
    middling slopes, as scree;
  - bare earth in patches on the gentle ground;
  - green meadow in the hollows and the gullies, where the water collects;
  - dry meadow elsewhere.
  It's band-limited to footprint(), which grows smoothly with the distance (so nothing jumps where the spacing does):
  the noises' octaves finer than it fade out (fbm()), and the slope is taken over about twice it. Every edge is broken
  by noise, and the paint's own noises are turned, so nothing lines up with the grid. Its alpha is the land's broad
  light and dark, a little darker under the woods.
- Oaks where the woodland noise says, near enough to be the cloud models (scene props, as the old backdrop's were),
  and further out thousands of crowns and scrub clumps (veridant_backdrop.blob) in two greens.

build( C ) returns ( the ground, the woods (drawn with no shadows: past a couple of thousand inches a crown's shadow is
lost in the cascades' texels), the oaks as scene props ). write_materials( root, C ) writes the splat, the land's vmat
and its shader, and the crowns' flat paints. --preview <dir> paints the splat and writes views of it.
"""
import argparse
import io
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import map_kit as K
from map_kit import Model
import veridant_backdrop as VB

RESOURCE = "materials/cerroblanco/fitout"
SHADER = "shaders/cerroblanco_land.shader"
SHADER_SOURCE = Path( __file__ ).resolve().parents[1] / "Sources/CerroBlanco/shaders/cerroblanco_land.shader"
SPLAT = "land_splat.png"
SPLAT_SIZE = 1024
# The grid's zones: how far out from the play's rectangle each spacing reaches, and the spacings (the shader's
# g_vZones and g_vSpacing).
ZONES = ( 3000.0, 14000.0, 46000.0 )
SPACING = ( 100.0, 350.0, 1600.0 )
# The land's layers: ( the shader's name, terrain material, tint ), tinted to the hill's light limestone and dry grass.
# The rock is the terrain's limestone: its scree's dark chips on brown earth read as speckle over whole hillsides.
LAYERS = (
    ( "Dry", "meadow_dry", ( 1.06, 1.0, 0.92 ) ),
    ( "Green", "meadow", ( 0.95, 1.0, 0.92 ) ),
    ( "Dirt", "dirt", ( 1.08, 1.0, 0.92 ) ),
    ( "Rock", "rock", ( 1.3, 1.28, 1.22 ) ),
)
# The land's settings (the shader's defaults, written out so the vmat says what it draws).
LAND = {
    "g_flTile": "150",
    "g_flFarTile": "1180",
    "g_vFarFade": "[1800 9000]",
    "g_flBlendDepth": "0.16",
    "g_flHeightScale": "0.55",
    "g_flMacro": "0.5",
    "g_vNormalStrength": "[1 0.35]",
    "g_vRoughness": "[0.93 0.9 0.9 0.8]",
}
# The crowns and the scrub, flat: ( colour, metalness, roughness ).
FLAT = {
    "cbf_canopy": ( ( 50, 62, 40 ), 0.0, 0.92 ),
    "cbf_canopy_dry": ( ( 92, 94, 64 ), 0.0, 0.92 ),
    "cbf_canopy_dark": ( ( 34, 46, 32 ), 0.0, 0.92 ),
}
OAKS = ( "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl", "models/sbox_props/trees/oak/tree_oak_dry_medium_a.vmdl",
         "models/sbox_props/trees/oak/tree_oak_small_a.vmdl" )
# The draws veridant_backdrop.blob took from the rng for each old crown: its turn, three for each of its five sides and
# two for its apex. build() still takes them, so the oaks after it stay where they were.
BLOB_DRAWS = 18


def axis( lo, hi ):
    """ Grid lines along one axis: fine near the play, coarse far out. """
    near, mid, far = ZONES
    fine, middle, coarse = SPACING
    inner = np.arange( lo - near, hi + near + 1.0, fine )
    mid_lo = np.arange( lo - mid, lo - near, middle )
    mid_hi = np.arange( hi + near + middle, hi + mid + 1.0, middle )
    far_lo = np.arange( lo - far, lo - mid, coarse )
    far_hi = np.arange( hi + mid + coarse, hi + far + 1.0, coarse )
    return np.unique( np.concatenate( [ far_lo, mid_lo, inner, mid_hi, far_hi, [ lo, hi ] ] ) )


def height( E, N, C ):
    """ The ground's height: the old backdrop's lie, and its detail, growing with the distance from the play. """
    rect = ( C.PLAY[0], C.PLAY[1], C.PLAY[2], C.PLAY[3] )
    d = VB.rect_distance( E, N, rect )
    base = C.terrain_z( E, N )
    near = VB.smoothstep01( 250.0, 2600.0, d )
    hills = 150.0 * VB.vfbm( E, N, 1800.0, 4, 1101 ) + 55.0 * VB.vfbm( E, N, 520.0, 3, 1102 )
    gullies = -120.0 * np.maximum( 0.0, VB.vfbm( E, N, 1100.0, 3, 1103 ) ) * VB.smoothstep01( 900.0, 3200.0, d )
    rock = VB.vfbm( E, N, 760.0, 3, 1104 )
    outcrops = 70.0 * np.clip( ( rock - 0.32 ) * 3.0, 0.0, 1.0 ) ** 1.5
    ridges = 480.0 * VB.vridged( E, N, 4600.0, 4, 1105 ) * VB.smoothstep01( 2600.0, 9000.0, d )
    sierra = ( 1700.0 * VB.vridged( E, N, 11000.0, 5, 1106 ) + 650.0 * VB.vfbm( E, N, 3600.0, 3, 1107 ) ) * \
        VB.smoothstep01( 9000.0, 22000.0, d )
    return base + near * ( hills + gullies + outcrops ) + ridges + sierra


# ---------------------------------------------------------------------------------------------------------------------
# The splat

def zone_knots( lo, hi ):
    """ Where each spacing starts and ends along an axis, from the land's far edge to the other, and the spacings. """
    near, mid, far = ZONES
    fine, middle, coarse = SPACING
    knots = np.array( [ lo - far, lo - mid, lo - near, hi + near, hi + mid, hi + far ] )
    return knots, np.array( [ coarse, middle, fine, middle, coarse ] )


def map_axis( x, lo, hi, size=SPLAT_SIZE ):
    """ The shader's MapAxis(): how far along the splat (0 to 1) a plan coordinate is, the grid's cells counted from
    the land's far edge, with the texels' centres at both ends. """
    knots, steps = zone_knots( lo, hi )
    x = np.asarray( x, float )
    cells = sum( ( np.clip( x, knots[k], knots[k + 1] ) - knots[k] ) / steps[k] for k in range( 5 ) )
    total = float( np.sum( np.diff( knots ) / steps ) )
    return ( cells / total ) * ( size - 1 ) / size + 0.5 / size


def axis_plan( t, lo, hi ):
    """ map_axis() turned round: the plan coordinate t of the way along the grid's cells (0 to 1, texel centre to texel
    centre). """
    knots, steps = zone_knots( lo, hi )
    edges = np.concatenate( [ [ 0.0 ], np.cumsum( np.diff( knots ) / steps ) ] )
    cells = np.asarray( t, float ) * edges[-1]
    k = np.clip( np.searchsorted( edges, cells, side="right" ) - 1, 0, 4 )
    return knots[k] + ( cells - edges[k] ) * steps[k]


def texel_plan( C, size=SPLAT_SIZE ):
    """ Each column's plan east and each row's plan north: columns run east, rows south (v = 1 - MapAxis( n )). """
    t = np.arange( size ) / ( size - 1 )
    return axis_plan( t, C.PLAY[0], C.PLAY[1] ), axis_plan( 1.0 - t, C.PLAY[2], C.PLAY[3] )


def texel_sizes( lo, hi, size=SPLAT_SIZE ):
    """ How many inches a texel covers along an axis in each spacing's zone (fine, middle, coarse). """
    knots, steps = zone_knots( lo, hi )
    total = float( np.sum( np.diff( knots ) / steps ) )
    return tuple( s * total / ( size - 1 ) for s in SPACING )


def footprint( d ):
    """ The splat's texel at d inches from the play, smoothly: never smaller than the larger of a texel's two sides
    there (21-22 inches by the play, 73-77 past 3000, 334-354 past 14000), and with no jump where they do. """
    return 24.0 + 0.025 * d


def fbm( E, N, scale, octaves, seed, F ):
    """ veridant_backdrop.vfbm (the same noise, octave for octave), with each octave fading out as it nears the splat's
    footprint F, so the splat doesn't alias it far out. """
    total, amp, norm = np.zeros( np.shape( E ) ), 1.0, 0.0
    for o in range( octaves ):
        fade = VB.smoothstep01( 1.5 * F, 4.0 * F, scale / 2 ** o )
        total = total + amp * fade * VB.vnoise( E, N, scale / 2 ** o, seed + 7 * o, turn=0.61 * o )
        norm += amp
        amp *= 0.5
    return total / norm


def breakup( E, N, F, seed ):
    """ Noise (about -1..1) to break the edges up: octaves from 2400 inches down to 75, each fading out as it nears the
    footprint F there, so it never aliases in the splat. Its lattices are turned, so nothing in it lines up with the
    grid. """
    total, norm = np.zeros( np.shape( E ) ), 0.0
    for o in range( 6 ):
        scale = 2400.0 / 2 ** o
        amp = 0.65 ** o
        fade = VB.smoothstep01( 1.5 * F, 4.0 * F, scale )
        total = total + amp * fade * VB.vnoise( E, N, scale, seed + 5 * o, turn=0.37 + 0.71 * o )
        norm += amp
    return total / norm * 1.7


def smooth_gradient( f, E, N, sigma, samples=6 ):
    """ The gradient ( d/de, d/dn ) of f( E, N ), each through a Gaussian's derivative sigma wide (sampled out to two
    sigma), so a crease in f gives a gradual change of slope, not the kinks a plain difference would put either side of
    it. Exact for a plane. """
    t = ( np.arange( samples ) + 0.5 ) / samples * 2.0
    w = t * np.exp( -0.5 * t * t )
    ge, gn = np.zeros( np.shape( E ) ), np.zeros( np.shape( E ) )
    norm = 0.0
    for tk, wk in zip( t, w ):
        tau = tk * sigma
        ge = ge + wk * ( f( E + tau, N ) - f( E - tau, N ) )
        gn = gn + wk * ( f( E, N + tau ) - f( E, N - tau ) )
        norm = norm + wk * 2.0 * tau
    return ge / norm, gn / norm


def turned( E, N, angle=0.53, warp=260.0 ):
    """ Plan points turned by angle and warped up to about warp inches (by noise 3000 across), for the paint's own
    noises. """
    c, s = math.cos( angle ), math.sin( angle )
    we = warp * VB.vnoise( E, N, 3000.0, 1611, turn=0.41 )
    wn = warp * VB.vnoise( E, N, 3000.0, 1612, turn=1.27 )
    return ( E + we ) * c - ( N + wn ) * s, ( E + we ) * s + ( N + wn ) * c


def soft( x, a, b, widen ):
    """ smoothstep from a to b, both moved out by widen (a field's change over the footprint). """
    return VB.smoothstep01( a - widen, b + widen, x )


def weights( E, N, C ):
    """ The splat at plan points: ( green, dirt, rock, broad light and dark ), each 0 to 1, green + dirt + rock <= 1. """
    rect = ( C.PLAY[0], C.PLAY[1], C.PLAY[2], C.PLAY[3] )
    d = VB.rect_distance( E, N, rect )
    F = footprint( d )
    # The height and slope over about twice the footprint (as coarse as the grid's own normals far out), so they don't
    # alias in the splat. Each axis's slope is the mean of the rises either side, so a ridge's crest or a gully's floor
    # keeps its flanks' slope rather than cancelling out to level. terrain_z's own slope is smoothed over 400 inches and
    # more (smooth_gradient()): it has creases (where it eases in from the play's edge, at 600 and 1500 out, and along
    # n = 0, where its rise changes), which the paint would draw as straight lines.
    h = np.minimum( 60.0 + 0.05 * d, 800.0 )
    pe, pn = np.stack( [ E, E + h, E - h, E, E ] ), np.stack( [ N, N, N, N + h, N - h ] )
    zz = height( pe, pn, C )
    z = zz[0]
    detail = zz - C.terrain_z( pe, pn )
    ge, gn = smooth_gradient( C.terrain_z, E, N, 200.0 + 0.025 * d )
    slope_e = ( np.abs( detail[1] - detail[0] + ge * h ) + np.abs( detail[0] - detail[2] + ge * h ) ) / ( 2.0 * h )
    slope_n = ( np.abs( detail[3] - detail[0] + gn * h ) + np.abs( detail[0] - detail[4] + gn * h ) ) / ( 2.0 * h )
    slope = np.hypot( slope_e, slope_n )
    near = VB.smoothstep01( 250.0, 2600.0, d )
    b = breakup( E, N, F, 1501 )
    # The paint's own noises are turned and warped, so nothing in them lines up with the grid.
    TE, TN = turned( E, N )
    s = slope + 0.13 * b
    # Rock: steep ground, the outcrops, the sierra's tops, and stony on the middling slopes (the old scree).
    steep = VB.smoothstep01( 0.55, 1.0, s )
    middling = VB.smoothstep01( 0.3, 0.62, s )
    r = fbm( E, N, 760.0, 3, 1104, F ) + 0.07 * b
    wr = 0.35 * F / 760.0
    outcrop = soft( r, 0.32, 0.47, wr ) * VB.smoothstep01( 0.04, 0.2, s ) * near
    stony = soft( r, 0.2, 0.34, wr ) * VB.smoothstep01( 0.02, 0.12, s ) * near
    # Up on the sierra mostly rock, with dry grass still on the gentler tops.
    high = soft( z + 300.0 * b, 3000.0, 3700.0, 0.6 * F ) * ( 0.6 + 0.4 * VB.smoothstep01( 0.12, 0.42, s ) )
    rock = 1.0 - ( 1.0 - steep ) * ( 1.0 - outcrop ) * ( 1.0 - high ) * ( 1.0 - 0.5 * middling ) * ( 1.0 - 0.4 * stony )
    # Bare earth: patches on the gentle ground, and some between the stones.
    dd = fbm( TE, TN, 900.0, 3, 1202, F ) + 0.1 * b
    gentle = 1.0 - VB.smoothstep01( 0.28, 0.45, s )
    patch = soft( dd, 0.36, 0.56, 0.35 * F / 900.0 ) * gentle
    dirt = 1.0 - ( 1.0 - 0.85 * patch ) * ( 1.0 - 0.3 * middling * ( 1.0 - steep ) )
    # Greener in the hollows of the rolling ground and in the gullies (the height's own noises), where the water
    # collects. Not from the slope's bend: terrain_z's creases (where it eases in from the play's edge) would draw it
    # as straight lines.
    rolling = fbm( E, N, 1800.0, 4, 1101, F ) + 0.37 * fbm( E, N, 520.0, 3, 1102, F )
    hollow = np.clip( -2.0 * rolling, 0.0, 1.0 ) * near
    gully = np.clip( fbm( E, N, 1100.0, 3, 1103, F ), 0.0, 1.0 ) * VB.smoothstep01( 900.0, 3200.0, d )
    g = fbm( TE, TN, 2400.0, 3, 1201, F ) + 0.3 * gully + 0.25 * hollow + 0.1 * b
    green = 0.9 * soft( g, 0.05, 0.32, 0.35 * F / 2400.0 ) * ( 1.0 - VB.smoothstep01( 0.32, 0.5, s ) )
    B = rock
    G = dirt * ( 1.0 - B )
    R = green * ( 1.0 - B - G )
    # Broad light and dark, past 3000 inches across, a little darker under the woods and in the hollows.
    woods = fbm( E, N, 2200.0, 3, 1301, F )
    wooded = VB.smoothstep01( -0.15, 0.2, woods ) * VB.smoothstep01( 600.0, 1400.0, d ) * \
        ( 1.0 - VB.smoothstep01( 0.6, 0.85, slope ) ) * ( 1.0 - VB.smoothstep01( 3000.0, 3300.0, z ) )
    A = 0.54 + 0.13 * VB.vfbm( TE, TN, 9000.0, 3, 1401 ) + 0.05 * VB.vnoise( E, N, 3400.0, 1402, turn=0.9 ) - \
        0.08 * wooded - 0.04 * hollow
    return R, G, B, np.clip( A, 0.15, 0.85 )


def splat( C, size=SPLAT_SIZE, rows=32, workers=None ):
    """ The splat as an RGBA uint8 array ( size, size, 4 ): row 0 is the north edge, column 0 the west. """
    for lo, hi in ( ( C.PLAY[0], C.PLAY[1] ), ( C.PLAY[2], C.PLAY[3] ) ):
        sizes = texel_sizes( lo, hi, size )
        for d, t in zip( ( 0.0, ZONES[0], ZONES[1] ), sizes ):
            assert footprint( d ) >= t, f"the footprint ({footprint( d ):.0f}) is under a texel ({t:.0f}) at {d:.0f}"
    es, ns = texel_plan( C, size )
    out = np.zeros( ( size, size, 4 ), np.uint8 )

    def band( y0 ):
        E, N = np.meshgrid( es, ns[y0:y0 + rows] )
        out[y0:y0 + rows] = np.clip( np.rint( np.stack( weights( E, N, C ), -1 ) * 255.0 ), 0, 255 ).astype( np.uint8 )

    with ThreadPoolExecutor( max_workers=workers or min( 8, os.cpu_count() or 4 ) ) as pool:
        list( pool.map( band, range( 0, size, rows ) ) )
    return out


def save_png( image, path ):
    """ Writes a PNG through a temporary file, renamed over the old one with retries (the editor can hold it), and
    only if it changed, so a re-run doesn't make the editor compile it again. """
    buffer = io.BytesIO()
    image.save( buffer, format="PNG", optimize=True )
    data = buffer.getvalue()
    write_bytes( path, data )


def write_bytes( path, data ):
    path = Path( path )
    if path.exists() and path.read_bytes() == data:
        return
    temp = path.with_name( f".{path.name}.tmp" )
    temp.write_bytes( data )
    for attempt in range( 40 ):
        try:
            os.replace( temp, path )
            return
        except OSError:
            if attempt == 39:
                raise
            time.sleep( 0.25 )


# ---------------------------------------------------------------------------------------------------------------------
# The ground and the woods

def build( C, seed=27 ):
    es = axis( C.PLAY[0], C.PLAY[1] )
    ns = axis( C.PLAY[2], C.PLAY[3] )
    E, N = np.meshgrid( es, ns, indexing="ij" )
    Z = height( E, N, C )
    dz_de, dz_dn = np.gradient( Z, es, ns, edge_order=1 )
    normals = np.stack( [ -dz_de, -dz_dn, np.ones_like( Z ) ], -1 )
    normals /= np.linalg.norm( normals, axis=-1, keepdims=True )
    rect = ( C.PLAY[0], C.PLAY[1], C.PLAY[2], C.PLAY[3] )
    # One paint: the land's shader blends its materials by the splat, so the quads need no paints of their own.
    m = Model()
    quads = 0
    for i in range( len( es ) - 1 ):
        for j in range( len( ns ) - 1 ):
            me, mn = ( es[i] + es[i + 1] ) / 2, ( ns[j] + ns[j + 1] ) / 2
            if C.PLAY[0] <= me <= C.PLAY[1] and C.PLAY[2] <= mn <= C.PLAY[3]:
                continue
            idx = ( ( i, j ), ( i + 1, j ), ( i + 1, j + 1 ), ( i, j + 1 ) )
            pts = [ ( es[a], ns[b], Z[a, b] ) for a, b in idx ]
            nrm = [ normals[a, b] for a, b in idx ]
            m.polygon( "cbf_land", pts, normal=sum( nrm ), normals=nrm )
            quads += 1
    # The woods were crowns and scrub clumps (veridant_backdrop.blob) placed here; they're cerroblanco_trees.py's cards
    # now. The old placing still runs, drawing nothing, so the shared rng reaches the oaks below as it did and they stay
    # where they were: each crown took its place's draws here and blob()'s 18 (BLOB_DRAWS).
    rng = np.random.default_rng( seed )
    wood_noise = lambda e, n: VB.vfbm( np.array( [ e ] ), np.array( [ n ] ), 2200.0, 3, 1301 )[0]
    clumps = 0
    props = []
    tries = 0
    while clumps < 5200 and tries < 60000:
        tries += 1
        a = rng.uniform( 0, 2 * math.pi )
        dist = 900.0 + ( rng.random() ** 1.7 ) * 21000.0
        cx, cy = ( C.PLAY[0] + C.PLAY[1] ) / 2, ( C.PLAY[2] + C.PLAY[3] ) / 2
        e = cx + math.cos( a ) * ( dist + ( C.PLAY[1] - C.PLAY[0] ) / 2 )
        n = cy + math.sin( a ) * ( dist + ( C.PLAY[3] - C.PLAY[2] ) / 2 )
        d = float( VB.rect_distance( np.array( e ), np.array( n ), rect ) )
        if d < 700:
            continue
        w = wood_noise( e, n )
        if w < -0.1 + 0.2 * rng.random():
            continue
        z = float( height( np.array( [ e ] ), np.array( [ n ] ), C )[0] )
        # The slope here, from the heights a little each way.
        zz = height( np.array( [ e + 80, e - 80, e, e ] ), np.array( [ n, n, n + 80, n - 80 ] ), C )
        if math.hypot( zz[0] - zz[1], zz[2] - zz[3] ) / 160.0 > 0.75 or z > 3200:
            continue
        rng.uniform( 110, 260 )
        rng.uniform( 0.7, 1.1 )
        rng.choice( 3, p=( 0.5, 0.3, 0.2 ) )
        rng.random( BLOB_DRAWS )
        clumps += 1
    # The oaks near the walls are the cloud models, standing in groves.
    tries = 0
    while len( props ) < 300 and tries < 20000:
        tries += 1
        e = rng.uniform( C.PLAY[0] - 5500, C.PLAY[1] + 5500 )
        n = rng.uniform( C.PLAY[2] - 5500, C.PLAY[3] + 5500 )
        d = float( VB.rect_distance( np.array( e ), np.array( n ), rect ) )
        if not 450 < d < 5200:
            continue
        if wood_noise( e, n ) < 0.05 + 0.25 * rng.random():
            continue
        z = float( height( np.array( [ e ] ), np.array( [ n ] ), C )[0] )
        zz = height( np.array( [ e + 60, e - 60, e, e ] ), np.array( [ n, n, n + 60, n - 60 ] ), C )
        if math.hypot( zz[0] - zz[1], zz[2] - zz[3] ) / 120.0 > 0.6:
            continue
        path = OAKS[int( rng.choice( 3, p=( 0.55, 0.3, 0.15 ) ) )]
        s = float( rng.uniform( 0.95, 1.35 ) )
        props.append( { "path": path, "position": ( e, n, z - 8 ), "yaw": float( rng.uniform( 0, 360 ) ), "scale": ( s, s, s ),
                        "name": "Backdrop Tree" } )
    # The woods: cerroblanco_trees.py's cards, kept off the oaks.
    import cerroblanco_trees as T
    woods = T.build( C, height, seed, avoid=[ p["position"] for p in props ] )
    for paint in m.polygons:
        if paint.startswith( "cbf_" ):
            m.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            m.tile_overrides[paint] = float( LAND["g_flTile"] ) if paint == "cbf_land" else 64.0
    print( f"landscape: {quads} ground quads, {len( props )} oaks" )
    return m, woods, props


# ---------------------------------------------------------------------------------------------------------------------
# Materials

def land_vmat( C ):
    """ The land's vmat: the shader, where the splat lies, the four layers' maps and tints. """
    def vec( values ):
        return "[" + " ".join( f"{v:g}" for v in values ) + "]"
    lines = [ "// Tools/cerroblanco_landscape.py", '"Layer0"', "{", f'    shader "{SHADER}"',
              f'    g_vPlay "{vec( C.PLAY )}"', f'    g_vZones "{vec( ZONES )}"', f'    g_vSpacing "{vec( SPACING )}"',
              f'    g_flSplatSize "{SPLAT_SIZE}"' ]
    lines += [ f'    {key} "{value}"' for key, value in LAND.items() ]
    lines.append( f'    Splat "{RESOURCE}/{SPLAT}"' )
    for name, source, tint in LAYERS:
        lines += [ f'    g_vTint{name} "{vec( tint )}"', f'    Color{name} "materials/terrain/{source}_color.png"',
                   f'    Height{name} "materials/terrain/{source}_height.png"',
                   f'    Normal{name} "materials/terrain/{source}_normal.png"' ]
    return "\n".join( lines + [ "}" ] ) + "\n"


def write_materials( root, C=None ):
    """ The land's splat, its vmat and its shader (copied from Sources/CerroBlanco), and the crowns' flat greens, as
    text vmats beside the fit-out's. root is Assets, or a staging folder laid out like it. """
    from PIL import Image
    import railhead_materials as RM
    if C is None:
        import cerroblanco_map as C
    root = Path( root )
    out = root / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    save_png( Image.fromarray( splat( C ), "RGBA" ), out / SPLAT )
    K.write_text( out / "cbf_land.vmat", land_vmat( C ) )
    ( root / SHADER ).parent.mkdir( parents=True, exist_ok=True )
    write_bytes( root / SHADER, SHADER_SOURCE.read_bytes() )
    for name, ( colour, metal, rough ) in FLAT.items():
        text = RM.painted_vmat( name, colour, metal, rough ).replace( "Tools/railhead_materials.py", "Tools/cerroblanco_landscape.py" )
        K.write_text( out / f"{name}.vmat", text )


# ---------------------------------------------------------------------------------------------------------------------
# Previews

def layer_colours():
    """ Each layer's mean colour in linear light, tinted, as the land draws it from afar. """
    from PIL import Image
    colours = []
    for _, source, tint in LAYERS:
        c = np.asarray( Image.open( K.ASSETS / f"materials/terrain/{source}_color.png" ).convert( "RGB" ), float ) / 255.0
        linear = np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )
        colours.append( linear.reshape( -1, 3 ).mean( 0 ) * np.array( tint ) )
    return np.array( colours )


def colour_of( rgba, macro=float( LAND["g_flMacro"] ) ):
    """ The splat as the land's colour (sRGB, 0-255): the layers' mean colours by their weights, times the macro term. """
    w = rgba[..., :3].astype( float ) / 255.0
    a = rgba[..., 3].astype( float ) / 255.0
    weights = np.concatenate( [ np.clip( 1.0 - w.sum( -1, keepdims=True ), 0.0, 1.0 ), w ], -1 )
    linear = weights @ layer_colours()
    linear *= ( 1.0 + ( 0.55 + 0.9 * a - 1.0 ) * macro )[..., None]
    srgb = np.where( linear <= 0.0031308, linear * 12.92, 1.055 * np.clip( linear, 0.0, None ) ** ( 1 / 2.4 ) - 0.055 )
    return np.clip( srgb * 255.0, 0, 255 ).astype( np.uint8 )


def sample( rgba, E, N, C ):
    """ The splat at plan points as the shader samples it: MapAxis(), then bilinear, clamped to the edge. """
    size = rgba.shape[0]
    x = map_axis( E, C.PLAY[0], C.PLAY[1], size ) * size - 0.5
    y = ( 1.0 - map_axis( N, C.PLAY[2], C.PLAY[3], size ) ) * size - 0.5
    x, y = np.clip( x, 0, size - 1 ), np.clip( y, 0, size - 1 )
    x0, y0 = np.minimum( np.floor( x ).astype( int ), size - 2 ), np.minimum( np.floor( y ).astype( int ), size - 2 )
    fx, fy = ( x - x0 )[..., None], ( y - y0 )[..., None]
    t = rgba.astype( float )
    top = t[y0, x0] * ( 1 - fx ) + t[y0, x0 + 1] * fx
    bottom = t[y0 + 1, x0] * ( 1 - fx ) + t[y0 + 1, x0 + 1] * fx
    return top * ( 1 - fy ) + bottom * fy


def preview( C, out_dir, size=SPLAT_SIZE ):
    """ Paints the splat and writes it and views of it to out_dir: the weights (red green, green dirt, blue rock), the
    alpha, the colour in the splat's own texels, and the colour in plan (as the shader samples it) over the whole land,
    out to 16000 and round the play, with the play's rectangle outlined. Prints each layer's share. """
    from PIL import Image, ImageDraw
    out_dir = Path( out_dir )
    out_dir.mkdir( parents=True, exist_ok=True )
    started = time.time()
    rgba = splat( C, size )
    print( f"splat: {size} x {size} in {time.time() - started:.1f} s" )
    Image.fromarray( rgba, "RGBA" ).save( out_dir / "land_splat.png" )
    Image.fromarray( rgba[..., :3], "RGB" ).save( out_dir / "splat_weights.png" )
    Image.fromarray( rgba[..., 3], "L" ).save( out_dir / "splat_alpha.png" )
    Image.fromarray( colour_of( rgba ), "RGB" ).save( out_dir / "colour_texels.png" )
    # Each layer's share, of the texels and of the land's area.
    es, ns = texel_plan( C, size )
    de, dn = np.gradient( es ), -np.gradient( ns )
    area = dn[:, None] * de[None, :]
    w = rgba[..., :3].astype( float ) / 255.0
    layers = np.concatenate( [ np.clip( 1.0 - w.sum( -1, keepdims=True ), 0, 1 ), w ], -1 )
    E, N = np.meshgrid( es, ns )
    d = VB.rect_distance( E, N, ( C.PLAY[0], C.PLAY[1], C.PLAY[2], C.PLAY[3] ) )
    outside = d > 0
    for label, mask in ( ( "texels", outside ), ( "area", outside ), ( "within 3000", outside & ( d < ZONES[0] ) ),
                         ( "3000-14000", ( d >= ZONES[0] ) & ( d < ZONES[1] ) ), ( "past 14000", d >= ZONES[1] ) ):
        weight = ( area if label != "texels" else np.ones_like( area ) ) * mask
        share = ( layers * weight[..., None] ).sum( ( 0, 1 ) ) / weight.sum()
        print( f"  {label:>12}: " + ", ".join( f"{name} {100 * v:.1f}%" for ( name, _, _ ), v in zip( LAYERS, share ) ) )
    # The colour in plan.
    centre = ( ( C.PLAY[0] + C.PLAY[1] ) / 2, ( C.PLAY[2] + C.PLAY[3] ) / 2 )
    for name, half in ( ( "plan_full", 48000.0 ), ( "plan_16000", 16000.0 ), ( "plan_inner", 6500.0 ),
                        ( "plan_edge", 1600.0 ) ):
        pixels = 1024
        span = np.linspace( -half, half, pixels )
        if name == "plan_edge":
            # The play's south-west corner, where the land meets it.
            ce, cn = C.PLAY[0], C.PLAY[2]
        else:
            ce, cn = centre
        PE, PN = np.meshgrid( ce + span, cn - span )
        image = Image.fromarray( colour_of( np.rint( sample( rgba, PE, PN, C ) ).astype( np.uint8 ) ), "RGB" )
        draw = ImageDraw.Draw( image )
        scale = ( pixels - 1 ) / ( 2 * half )
        to_px = lambda e, n: ( ( e - ce + half ) * scale, ( cn + half - n ) * scale )
        draw.rectangle( [ to_px( C.PLAY[0], C.PLAY[3] ), to_px( C.PLAY[1], C.PLAY[2] ) ], outline=( 255, 40, 40 ) )
        # The zones' knots, as ticks along the edges.
        for lo, hi, along in ( ( C.PLAY[0], C.PLAY[1], "e" ), ( C.PLAY[2], C.PLAY[3], "n" ) ):
            for knot in zone_knots( lo, hi )[0]:
                if along == "e":
                    x = to_px( knot, cn )[0]
                    draw.line( [ ( x, 0 ), ( x, 12 ) ], fill=( 255, 255, 0 ) )
                else:
                    y = to_px( ce, knot )[1]
                    draw.line( [ ( 0, y ), ( 12, y ) ], fill=( 255, 255, 0 ) )
        image.save( out_dir / f"{name}.png" )
    return rgba


def main( argv=None ):
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", type=Path, help="paint the splat and write it and views of it here" )
    args = parser.parse_args( argv )
    if args.preview:
        sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
        import cerroblanco_map
        preview( cerroblanco_map, args.preview )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
