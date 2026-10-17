"""
Riverdale's sky: a golden sunrise after rain over the plant's mountains, the sun low in the east-north-east. A panorama
written with Belltower's sky code (Tools/belltower_sky.py: its atmosphere, wrapping, tonemap and EXR writer), with the
clouds painted on as thin layers rather than ray-marched heaps (those read as cartoon puffs, as Orion's did).

    python Tools/riverdale_sky.py [--out <dir>] [--width 8192] [--seed 7] [--preview <dir>] [--no-write]

- The sun is riverdale_map's (SUN_PITCH, SUN_YAW): 16 degrees up, 33 degrees north of east, so the east yard looks
  towards it past the cooling towers and the west yard away from it.
- The clear sky's colours are keyed by degrees above the horizon, towards the sun (SUN_SIDE) and away from it
  (AWAY_SIDE), blended round by azimuth: peach and cream at the horizon on the sun's side, paler and cooler across from
  it, a clean blue overhead. They're colours as a match shows them at EXPOSURE (belltower_sky's design scale), taken
  back through the game's ACES tonemap. Over that, a glow round the sun (GLOW) whitens and warms the sky towards it, and
  a thin haze band sits on the horizon (HAZE_BAND), behind the mountains.
- Two cloud layers, each a texture on a plane over a round earth, so they're big overhead and crowd and flatten towards
  the horizon as real ones do:
  - altocumulus 4.0-4.4 km up: patches of small cloudlets in broken rows (cellular noise stretched across the wind,
    warped), thinned and thickened in patches tens of kilometres across;
  - cirrus 8.5 km up: long fibrous strands drawn out along the wind, in a few wide sheets.
  The low sun lights them from below: gold and cream towards it, peach and pink across the sky, a soft lavender-grey in
  their thick middles and away from it (CLOUD_LIT, CLOUD_SHADE). Thin edges towards the sun glow (forward scattering).
  Far ones fade into the horizon's haze, and their detail is filtered by each texel's footprint on the layer, so the
  crowded rows near the horizon blur together instead of aliasing. Nothing crosses the sun's disc.
- Under the horizon, which the mountains hide, it's the light the ground throws up (GROUND): the sky is also what the
  map's surfaces reflect and are lit by (SkyBox2D's SkyIndirectLighting).
- --preview writes the panorama and views from the map's yards, displayed both at EXPOSURE and at SHOWN, the exposure
  the offscreen captures showed the old sky at (2026-10-15: about 0.75 on belltower_sky's scale).
- Writes riverdale_sky.exr and riverdale_sky.vmat to Assets/materials/riverdale/sky (or --out).
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverdale/sky"
RESOURCE_DIR = "materials/riverdale/sky"
NAME = "riverdale_sky"

SUN_PITCH, SUN_YAW = 16.0, 123.0      # riverdale_map's
LIGHT = np.array( ( 2.30, 1.62, 1.05 ), np.float32 )     # riverdale_map's sun LightColor
# The sky is baked to show its keyed colours at this exposure (belltower_sky's design scale). The old sky was baked
# for 2.0 and the offscreen captures showed it at about 0.75 (SHOWN): its blue came out navy and its clouds stark.
EXPOSURE = 1.0
SHOWN = 0.75
RADIANCE = 2.0 / EXPOSURE            # what isn't keyed (the glow, the disc) is scaled to match
# The clouds are keyed for a lower exposure than the sky: sunlit cloud is brighter than the blue round it, and at the
# exposure a match shows they still read as lit, gold and cream rather than salmon.
CLOUD_EXPOSURE = 0.85

# The clear sky's displayed colours (sRGB) by degrees above the horizon: towards the sun and away from it.
SUN_SIDE = ( ( -1.0, ( 168, 150, 132 ) ), ( 0.0, ( 246, 210, 166 ) ), ( 2.0, ( 244, 212, 172 ) ), ( 5.0, ( 236, 212, 182 ) ),
             ( 9.0, ( 214, 206, 198 ) ), ( 14.0, ( 186, 196, 210 ) ), ( 22.0, ( 152, 178, 212 ) ), ( 35.0, ( 120, 156, 206 ) ),
             ( 55.0, ( 98, 140, 200 ) ), ( 90.0, ( 86, 128, 194 ) ) )
AWAY_SIDE = ( ( -1.0, ( 150, 146, 144 ) ), ( 0.0, ( 222, 210, 204 ) ), ( 2.5, ( 214, 208, 208 ) ), ( 6.0, ( 196, 200, 212 ) ),
              ( 12.0, ( 168, 186, 212 ) ), ( 22.0, ( 136, 166, 208 ) ), ( 40.0, ( 108, 146, 202 ) ), ( 65.0, ( 92, 134, 198 ) ),
              ( 90.0, ( 86, 128, 194 ) ) )
# The glow round the sun: ( e-folding angle in degrees, brightness, colour ), linear, before RADIANCE. Wide and gold,
# narrower and whiter towards the disc; dimmer high above the horizon, where there's less haze to light.
GLOW = ( ( 0.6, 4.0, ( 1.0, 0.94, 0.84 ) ), ( 2.2, 1.6, ( 1.0, 0.86, 0.66 ) ), ( 7.0, 0.55, ( 1.0, 0.80, 0.56 ) ),
         ( 24.0, 0.16, ( 1.0, 0.76, 0.52 ) ) )
# A haze band on the horizon, behind the mountains: ( degrees thick, how far towards white-cream, colour ).
HAZE_BAND = ( 3.5, 0.35, ( 240, 222, 204 ) )
GROUND = np.array( ( 0.20, 0.18, 0.15 ), np.float32 )   # as the old sky had it (linear radiance)

# Clouds' displayed colours: lit by the low sun from below, by degrees from the sun; and their shaded middles.
CLOUD_LIT = ( ( 0.0, ( 255, 236, 196 ) ), ( 8.0, ( 255, 226, 176 ) ), ( 20.0, ( 255, 218, 168 ) ), ( 38.0, ( 250, 212, 174 ) ),
              ( 65.0, ( 244, 214, 190 ) ), ( 110.0, ( 238, 220, 208 ) ), ( 180.0, ( 234, 224, 218 ) ) )
CLOUD_SHADE = ( ( 0.0, ( 146, 124, 112 ) ), ( 20.0, ( 150, 132, 126 ) ), ( 60.0, ( 150, 144, 152 ) ), ( 180.0, ( 152, 156, 174 ) ) )
CIRRUS_LIT = ( ( 0.0, ( 255, 242, 214 ) ), ( 12.0, ( 255, 232, 194 ) ), ( 35.0, ( 252, 224, 192 ) ), ( 80.0, ( 240, 226, 214 ) ),
               ( 180.0, ( 230, 230, 234 ) ) )

# Altocumulus: the layer's slab (metres), the cloudlets' spacing across the wind and how much longer they are along it.
ALTO = ( 4000.0, 4380.0 )
ALTO_STEPS = 4
CELL = 400.0
STRETCH = 1.6
CELL_TILE = 24000.0         # the cell field repeats this often (metres); the coverage field every COVER_TILE
COVER_TILE = 60000.0
ALTO_COVER = 0.8           # more or less of the sky under altocumulus
SIGMA = 3.2                 # extinction per kilometre of path through a cloudlet
# Cirrus: its height, the strands' tile and how much longer than wide they're drawn out.
CIRRUS_HEIGHT = 8500.0
CIRRUS_TILE = 90000.0
CIRRUS_STRETCH = 7.0
CIRRUS_OPACITY = 0.42
WIND = math.radians( 62.0 ) # the strands run along this heading (from x, north, towards y, west); the rows across it
HAZE_DISTANCE = 100000.0    # metres for the haze to swallow 63% of a cloud
SUN_CLEAR = 5.0             # degrees round the sun kept clear of thick cloud

# Views for --preview: ( name, plan eye, plan target, horizontal fov ), riverdale_map's and the captures'.
VIEWS = ( ( "yard_reference", ( 560, -1010, 170 ), ( 2000, -880, 300 ), 84 ),
          ( "west_yard", ( -560, -1010, 170 ), ( -2000, -880, 300 ), 84 ),
          ( "court", ( 1380, 300, 70 ), ( 1400, 2000, 300 ), 80 ),
          ( "north_lane", ( -1900, 2250, 70 ), ( 1000, 2200, 60 ), 75 ),
          ( "towards_sun", ( 0, 0, 0 ), ( 1680, 1090, 900 ), 90 ),
          ( "south", ( 0, 0, 0 ), ( 0, -2000, 600 ), 90 ),
          ( "up", ( 0, 0, 0 ), ( 300, 200, 2000 ), 100 ) )


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def sun_direction():
    import belltower_sky as BS
    BS.SUN_PITCH, BS.SUN_YAW = SUN_PITCH, SUN_YAW
    return BS.sun_direction().astype( np.float32 )


def keyed( keys, x, exposure=EXPOSURE ):
    """ Linear colours for x from displayed-colour keys, interpolated in log space (ratios), as belltower_sky does. """
    import belltower_sky as BS
    xs = np.array( [ k for k, _ in keys ] )
    logs = np.log( np.array( [ BS.undisplay( np.array( c, float ), exposure ) for _, c in keys ] ) )
    return np.exp( np.stack( [ np.interp( x, xs, logs[:, c] ) for c in range( 3 ) ], -1 ) ).astype( np.float32 )


# ---------------------------------------------------------------------------------------------------------------------
# Tileable fields

def periodic_fbm( rng, n, octaves, base, persistence=0.55 ):
    """ Tileable value noise on n x n, about unit deviation, from upsampled periodic random grids. """
    out = np.zeros( ( n, n ), np.float32 )
    amp, total, cells = 1.0, 0.0, base
    for _ in range( octaves ):
        grid = rng.standard_normal( ( cells, cells ) ).astype( np.float32 )
        up = ndimage.zoom( grid, n / cells, order=3, mode="grid-wrap", grid_mode=True )
        out += amp * up[:n, :n]
        total += amp
        amp *= persistence
        cells *= 2
        if cells > n // 2:
            break
    out /= total
    return out / ( out.std() + 1e-6 )


def spectral( rng, n, beta, longest, shortest, stretch=1.0 ):
    """ Tileable fractal noise, unit deviation, with wavelengths from longest to shortest texels across x, and features
    stretch times longer along x than across it. """
    white = rng.standard_normal( ( n, n ) ).astype( np.float32 )
    spectrum = np.fft.rfft2( white )
    fy = ( np.fft.fftfreq( n ) )[:, None]
    fx = ( np.fft.rfftfreq( n ) )[None, :] * stretch
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    fmin = 1.0 / longest
    amp = f ** ( -beta / 2.0 ) * np.clip( ( f - fmin * 0.5 ) / ( fmin * 0.5 ), 0.0, 1.0 ) * np.clip( 2.0 - f * shortest, 0.0, 1.0 )
    amp[0, 0] = 0.0
    out = np.fft.irfft2( spectrum * amp, s=( n, n ) ).astype( np.float32 )
    return ( out - out.mean() ) / ( out.std() + 1e-6 )


def worley( rng, n, spacing_px, stretch ):
    """ Distances (texels, in the unstretched frame) to the nearest and next jittered cell centres on a tileable n x n
    grid whose cells are spacing_px across and stretch times that along x. A few cells are dropped. """
    nx = max( 2, int( round( n / ( spacing_px * stretch ) ) ) )
    ny = max( 2, int( round( n / spacing_px ) ) )
    gx, gy = np.meshgrid( np.arange( nx ), np.arange( ny ), indexing="ij" )
    px = ( gx + 0.5 + rng.uniform( -0.42, 0.42, gx.shape ) ) * n / nx
    py = ( gy + 0.5 + rng.uniform( -0.42, 0.42, gy.shape ) ) * n / ny
    keep = rng.random( gx.shape ) > 0.1
    pts = np.stack( [ px[keep], py[keep] ], -1 )
    copies = np.concatenate( [ pts + np.array( ( dx * n, dy * n ) ) for dx in ( -1, 0, 1 ) for dy in ( -1, 0, 1 ) ] )
    scale = np.array( ( 1.0 / stretch, 1.0 ) )
    tree = cKDTree( copies * scale )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 )
    dist, _ = tree.query( np.stack( [ xx.ravel(), yy.ravel() ], -1 ) * scale, k=2, workers=-1 )
    return dist[:, 0].reshape( n, n ).astype( np.float32 ), dist[:, 1].reshape( n, n ).astype( np.float32 )


def sample( table, u, v ):
    """ A tileable table at texel coordinates ( u across, v down ), bilinear, wrapping. """
    return ndimage.map_coordinates( table, [ ( v % table.shape[0] ).ravel(), ( u % table.shape[1] ).ravel() ], order=1,
                                    mode="grid-wrap" ).reshape( u.shape ).astype( np.float32 )


def filtered( levels, texel, u, v, footprint ):
    """ Sample a stack of ever blurrier copies ( 0: sharp, then sigma 2, 4, ... texels ) by the footprint (metres) of
    the pixel on the layer against the table's texel (metres), so detail finer than a pixel averages out. """
    level = np.clip( np.log2( np.maximum( footprint / ( texel * 1.5 ), 1.0 ) ), 0, len( levels ) - 1 )
    lo = np.floor( level ).astype( int )
    out = np.zeros( u.shape, np.float32 )
    for k in range( len( levels ) ):
        sel = ( lo == k ) | ( lo + 1 == k )
        if not sel.any():
            continue
        w = np.where( lo == k, 1.0 - ( level - lo ), level - lo )
        out[sel] += w[sel] * sample( levels[k], u[sel], v[sel] )
    return out


def blurred_stack( table, steps=6 ):
    return [ table ] + [ ndimage.gaussian_filter( table, 2 ** k, mode="wrap" ) for k in range( 1, steps ) ]


class Altocumulus:
    """ Cloudlets in broken rows across the wind, gathered into patches. """

    def __init__( self, seed ):
        rng = np.random.default_rng( seed )
        n = 2048
        self.texel = CELL_TILE / n
        spacing = CELL / self.texel
        f1, f2 = worley( rng, n, spacing, 1.0 / STRETCH )
        puff = np.clip( 1.0 - f1 / ( spacing * 0.6 ), 0, 1 ) ** 1.25
        gap = np.clip( ( f2 - f1 ) / ( spacing * 0.32 ), 0, 1 )
        wobble = periodic_fbm( rng, n, 6, 32 )
        cells = np.clip( puff * ( 0.5 + 0.5 * gap ) * ( 1.0 + 0.35 * wobble ), 0, 1.4 ).astype( np.float32 )
        self.cells = blurred_stack( cells )
        self.spacing = spacing
        self.detail = periodic_fbm( rng, n, 7, 16 )
        self.warp = periodic_fbm( rng, n, 4, 8 )
        # Clumps two or three cells across that the cloudlets merge into, with frayed edges.
        self.mass = blurred_stack( periodic_fbm( rng, n, 6, n // int( spacing * 2.6 ), 0.55 ) )
        self.fray = blurred_stack( periodic_fbm( rng, n, 6, n // int( spacing * 0.7 ), 0.6 ) )
        self.rows = periodic_fbm( rng, n, 6, 6, 0.6 )
        self.cover_texel = COVER_TILE / 1024
        self.cover = periodic_fbm( rng, 1024, 6, 5, 0.6 )
        self.thin = periodic_fbm( rng, 1024, 5, 14, 0.6 )

    def density( self, x, y, footprint ):
        """ Density at plane points ( metres, world x north and y west ) for pixels footprint metres across. """
        c, s = math.cos( WIND ), math.sin( WIND )
        a, b = ( c * x + s * y ) / self.texel, ( -s * x + c * y ) / self.texel     # along the wind, across it (texels)
        # A broad warp, a few cells across, so the rows bend and break instead of running ruler-straight.
        wx = sample( self.warp, a * 0.25 + 900.0, b * 0.25 )
        wy = sample( self.warp, b * 0.25 - 700.0, a * 0.25 + 300.0 )
        aw, bw = a + wx * 1.1 * self.spacing, b + wy * 1.1 * self.spacing
        cover = sample( self.cover, x / self.cover_texel, y / self.cover_texel )
        thin = sample( self.thin, x / self.cover_texel + 300.0, y / self.cover_texel )
        amount = smoothstep( -0.7, 0.7, cover + 0.4 * thin + ALTO_COVER )
        cells = filtered( self.cells, self.texel, aw, bw, footprint )
        rows = sample( self.rows, a * 0.6 + 1234.0, b * 1.4 )
        shape = smoothstep( -0.5, 0.5, 0.5 * rows + 3.0 * ( amount - 0.5 ) )
        detail = sample( self.detail, aw * 2.3, bw * 2.3 )
        keep = np.clip( 1.0 - footprint / 2500.0, 0, 1 )
        mass = filtered( self.mass, self.texel, aw, bw, footprint )
        fray = filtered( self.fray, self.texel, aw * 1.7, bw * 1.7, footprint )
        # Cloudlets merged into clumps, clear sky between them, their edges frayed, thinned where the patch thins.
        body = 0.55 * cells + 0.5 * ( 0.5 + 0.3 * mass ) - 0.42 + 0.14 * fray + 0.08 * detail * keep
        d = np.clip( body, 0, None ) * 2.6 * ( 0.35 + 0.65 * shape ) * smoothstep( 0.05, 0.4, shape )
        return np.clip( d, 0, 2.5 ).astype( np.float32 )


class Cirrus:
    """ Strands drawn out along the wind, in a few wide sheets. """

    def __init__( self, seed ):
        rng = np.random.default_rng( seed )
        n = 2048
        self.texel = CIRRUS_TILE / n
        fibres = spectral( rng, n, 2.2, 700, 10.0, CIRRUS_STRETCH )
        strands = np.clip( 1.0 - np.abs( fibres ) * 0.75, 0, 1 ) ** 1.8
        soft = spectral( rng, n, 2.6, 900, 14, CIRRUS_STRETCH * 0.6 )
        body = np.clip( 0.55 * strands + 0.45 * smoothstep( -0.2, 1.6, soft ), 0, 1 ).astype( np.float32 )
        self.body = blurred_stack( body )
        self.warp = periodic_fbm( rng, n, 5, 6 )
        self.cover = periodic_fbm( rng, 1024, 5, 4, 0.55 )

    def density( self, x, y, footprint ):
        c, s = math.cos( WIND ), math.sin( WIND )
        a, b = ( c * x + s * y ) / self.texel, ( -s * x + c * y ) / self.texel
        bend = sample( self.warp, a * 0.25, b * 0.25 )
        bw = b + bend * 40.0
        aw = a + sample( self.warp, b * 0.25 + 500.0, a * 0.25 ) * 25.0
        body = filtered( self.body, self.texel, aw, bw, footprint )
        sheets = smoothstep( 0.45, 1.5, sample( self.cover, x / ( CIRRUS_TILE * 4 / 1024 ), y / ( CIRRUS_TILE * 4 / 1024 ) ) )
        return ( body * sheets ).astype( np.float32 )


# ---------------------------------------------------------------------------------------------------------------------
# The panorama

def layer_points( d, height, up ):
    """ Where the rays d cross a layer this high over a round earth: distance (metres) and plane x, y. """
    earth = 6371e3
    t = -earth * up + np.sqrt( ( earth * up ) ** 2 + 2 * earth * height + height * height )
    return t, d[..., 0] * t, d[..., 1] * t, ( t + earth * up ) / ( earth + height )


def render( width=8192, seed=7, rows=None ):
    import belltower_sky as BS
    h = width // 2
    sun = sun_direction()
    sun_az = math.atan2( sun[1], sun[0] )
    flat = math.hypot( sun[0], sun[1] )
    sx, sy = sun[0] / flat, sun[1] / flat
    alto, cirrus = Altocumulus( seed ), Cirrus( seed + 11 )
    BS.SKY_KEYS = SUN_SIDE
    BS.SUN_HALO = 0.35
    base = BS.clear_sky_base( 1024, 512, sun )       # the atmosphere's own brightening towards the sun
    lum = base @ BS.LUMA
    variation = lum / np.maximum( lum.mean( 1, keepdims=True ), 1e-9 )
    out = np.zeros( ( h, width, 3 ), np.float32 )
    stats = [ 0.0, 0.0 ]
    pixel = 2 * math.pi / width
    band_r, band_mix, band_col = HAZE_BAND
    band_lin = keyed( ( ( 0.0, band_col ), ( 1.0, band_col ) ), np.zeros( 1 ) )[0]
    for r0 in range( 0, h, 128 ):
        rr = np.arange( r0, min( h, r0 + 128 ) )
        if rows is not None and not np.isin( rr, rows ).any():
            continue
        d = BS.panorama_directions( width, h, rr ).astype( np.float32 )
        el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
        az = np.arctan2( d[..., 1], d[..., 0] )
        daz = np.degrees( np.abs( ( az - sun_az + math.pi ) % ( 2 * math.pi ) - math.pi ) )
        ang = np.degrees( np.arccos( np.clip( d @ sun, -1, 1 ) ) )
        towards = ( ( 1.0 + np.cos( np.radians( daz ) ) ) * 0.5 ) ** 1.6
        sky = keyed( SUN_SIDE, el ) * towards[..., None] + keyed( AWAY_SIDE, el ) * ( 1 - towards[..., None] )
        u, v = BS.panorama_uv( d )
        vary = ndimage.map_coordinates( variation, [ np.clip( v * 512 - 0.5, 0, 511 ).ravel(), ( u * 1024 - 0.5 ).ravel() ],
                                        order=1, mode="grid-wrap" ).reshape( el.shape )
        sky *= ( 0.75 + 0.25 * vary )[..., None]
        band = np.exp( -np.maximum( el, 0 ) / band_r ) * band_mix * ( 0.6 + 0.4 * towards )
        sky = sky * ( 1 - band[..., None] ) + band_lin * band[..., None]
        lift = ( 0.35 + 0.65 * np.exp( -np.maximum( el, 0 ) / 20.0 ) )[..., None]
        for radius, strength, colour in GLOW:
            sky += RADIANCE * strength * np.exp( -ang / radius )[..., None] * np.array( colour, np.float32 ) * lift
        up = d[..., 2]
        above = up > 0.0015
        if above.any():
            upc = np.maximum( up, 0.0015 )
            clear = smoothstep( SUN_CLEAR * 0.6, SUN_CLEAR * 1.6, ang )
            near = np.exp( -ang / 9.0 )
            # Cirrus: one thin sheet, high up. Its ice scatters forward, so the strands round the sun glow.
            t, x, y, mu = layer_points( d, CIRRUS_HEIGHT, upc )
            foot = t * pixel / np.maximum( mu, 0.02 )
            dc = np.zeros( el.shape, np.float32 )
            dc[above] = cirrus.density( x[above], y[above], foot[above] )
            path = 1.0 / np.maximum( mu, 0.12 )
            a_c = ( 1.0 - np.exp( -dc * CIRRUS_OPACITY * path ) ) * ( 0.35 + 0.65 * clear )
            a_c *= np.exp( -t / ( HAZE_DISTANCE * 1.4 ) ) * smoothstep( 0.0015, 0.01, up )
            c_c = keyed( CIRRUS_LIT, ang, CLOUD_EXPOSURE ) * ( 1.0 + 1.3 * near * ( 1.0 - 0.5 * dc ) )[..., None]
            sky = sky * ( 1 - a_c[..., None] ) + c_c * a_c[..., None]
            # Altocumulus: marched through the slab's thickness, so the cloudlets have bodies, overlap towards the
            # horizon and hide the sky behind them. The low sun lights them through the cloud between each point and
            # it, along the layer.
            tm, xm, ym, mum = layer_points( d, ( ALTO[0] + ALTO[1] ) / 2, upc )
            footm = tm * pixel / np.maximum( mum, 0.02 )
            depth = np.zeros( el.shape, np.float32 )
            for step, weight in ( ( 150.0, 0.5 ), ( 360.0, 0.45 ), ( 700.0, 0.4 ), ( 1200.0, 0.3 ) ):
                probe = np.zeros( el.shape, np.float32 )
                probe[above] = alto.density( xm[above] + sx * step, ym[above] + sy * step, footm[above] )
                depth += weight * probe
            light = np.exp( -1.0 * depth )
            lit, shade = keyed( CLOUD_LIT, ang, CLOUD_EXPOSURE ), keyed( CLOUD_SHADE, ang, CLOUD_EXPOSURE )
            trans = np.ones( el.shape, np.float32 )
            colour = np.zeros( el.shape + ( 3, ), np.float32 )
            for k in range( ALTO_STEPS ):
                sk = ( k + 0.5 ) / ALTO_STEPS
                hk = ALTO[0] + sk * ( ALTO[1] - ALTO[0] )
                tk, xk, yk, muk = layer_points( d, hk, upc )
                dk = np.zeros( el.shape, np.float32 )
                dk[above] = alto.density( xk[above], yk[above], ( tk * pixel / np.maximum( muk, 0.02 ) )[above] )
                dk *= 0.3 + 0.7 * clear
                prof = 1.05 * abs( 2 * sk - 1 ) ** 1.5
                inside = smoothstep( prof, prof + 0.4, dk )
                seg = ( ALTO[1] - ALTO[0] ) / ALTO_STEPS / np.maximum( muk, 0.0015 ) / 1000.0
                a_k = 1.0 - np.exp( -SIGMA * inside * seg )
                thin = 1.0 - smoothstep( 0.0, 1.4, dk )
                # Lit from below: lower in the layer, more of it; thin parts towards the sun glow.
                amount = np.clip( light * ( 0.5 + 0.5 * thin ) * ( 1.25 - 0.4 * sk ), 0, 1 )
                c_k = shade * ( 1 - amount[..., None] ) + lit * amount[..., None]
                c_k *= ( 1.0 + 1.4 * near * thin * light )[..., None]
                colour += ( trans * a_k )[..., None] * c_k
                trans *= 1.0 - a_k
            alpha = 1.0 - trans
            colour /= np.maximum( alpha, 1e-5 )[..., None]
            alpha *= np.exp( -tm / HAZE_DISTANCE ) * smoothstep( 0.0015, 0.012, up )
            alpha[~above] = 0.0
            sky = sky * ( 1 - alpha[..., None] ) + colour * alpha[..., None]
            seen = 1.0 - ( 1.0 - alpha ) * ( 1.0 - a_c )
            weight = np.sqrt( np.clip( 1 - up ** 2, 0, 1 ) ) * ( el > 2.0 )
            stats[0] += float( np.sum( weight * ( seen > 0.5 ) ) )
            stats[1] += float( np.sum( weight ) )
        # Under the horizon: the ground's light, blended in over a fraction of a degree.
        blend = smoothstep( 0.0, -0.15, el )
        sky = sky * ( 1 - blend[..., None] ) + GROUND * blend[..., None]
        # The sun's disc, in the scene's light's colour.
        disc = smoothstep( 0.30, 0.24, ang )
        sky = sky * ( 1 - disc[..., None] ) + RADIANCE * 22.0 * LIGHT / LIGHT.max() * disc[..., None]
        out[rr] = sky
    print( f"{stats[0] / max( stats[1], 1e-9 ) * 100:.1f}% of the sky from 2 degrees up is mostly cloud" )
    return out


def vmat_text():
    """ The core skies' material. The sky shader's texture is SkyTexture: under any other key the compiler gives it the
    default texture, with no error. """
    return ( "// Tools/riverdale_sky.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/sky.shader"\n'
             '    F_TEXTURE_FORMAT2 "6"\n'
             '    g_flBrightnessExposureBias "0"\n'
             '    g_flRenderOnlyExposureBias "0"\n'
             f'    SkyTexture "{RESOURCE_DIR}/{NAME}.exr"\n'
             "}\n" )


def view( rgb, eye, target, fov, size=( 1280, 720 ) ):
    """ The panorama seen from a plan eye towards a plan target ( e, n, z ), linear. """
    import belltower_sky as BS
    de, dn, dz = ( np.asarray( target, float ) - np.asarray( eye, float ) )
    yaw = math.degrees( math.atan2( -de, dn ) )      # world: x north, y west
    pitch = math.degrees( math.atan2( dz, math.hypot( de, dn ) ) )
    d = BS.view_directions( yaw, pitch, fov, size )
    u, v = BS.panorama_uv( d )
    h, w = rgb.shape[:2]
    cols, rows = u * w - 0.5, np.clip( v * h - 0.5, 0, h - 1 )
    return np.stack( [ ndimage.map_coordinates( rgb[..., c], [ rows.ravel(), cols.ravel() ], order=1, mode="grid-wrap" )
                       .reshape( rows.shape ) for c in range( 3 ) ], -1 )


def write_previews( rgb, folder ):
    import belltower_sky as BS
    from PIL import Image
    folder.mkdir( parents=True, exist_ok=True )
    small = rgb[::4, ::4] if rgb.shape[1] > 4096 else rgb[::2, ::2]
    Image.fromarray( BS.display( small, SHOWN ) ).save( folder / "panorama.png" )
    for name, eye, target, fov in VIEWS:
        img = view( rgb, eye, target, fov )
        for exposure, tag in ( ( SHOWN, "" ), ( EXPOSURE, "_design" ) ):
            Image.fromarray( BS.display( img, exposure ) ).save( folder / f"{name}{tag}.png" )
        print( f"wrote {folder / name}.png" )


def main():
    import belltower_sky as BS
    ap = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    ap.add_argument( "--out", help="write the EXR and vmat here instead of Assets/materials/riverdale/sky" )
    ap.add_argument( "--width", type=int, default=8192 )
    ap.add_argument( "--seed", type=int, default=7 )
    ap.add_argument( "--preview", help="also write the panorama and views here" )
    ap.add_argument( "--no-write", action="store_true", help="previews only" )
    args = ap.parse_args()
    rgb = render( args.width, args.seed )
    if not args.no_write:
        out = Path( args.out ) if args.out else OUT_DIR
        out.mkdir( parents=True, exist_ok=True )
        BS.write_exr( out / f"{NAME}.exr", rgb )
        path = out / f"{NAME}.vmat"
        if not path.exists() or path.read_text( encoding="utf-8" ) != vmat_text():
            path.write_text( vmat_text(), encoding="utf-8", newline="\n" )
        print( f"wrote {out / f'{NAME}.exr'}" )
    if args.preview:
        write_previews( rgb, Path( args.preview ) )


if __name__ == "__main__":
    main()
