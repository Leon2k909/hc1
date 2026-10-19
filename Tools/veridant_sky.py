"""
Veridant's sky: the picture's sunset over the sea after rain. A panorama written with belltower_sky's EXR writer and
wrapping, its colours taken from the reference picture (2026-10-15).

    python Tools/veridant_sky.py [--out <dir>] [--width 8192] [--preview <png>] [--seed 7]

- The sun stands 3.4 degrees over the sea, 23.4 degrees north of west (veridant_map's SUN_PITCH, SUN_YAW), right of
  the headland's point as the courtyard sees it. It's a bright disc with a gold glow round it that whitens towards it,
  as the picture's is.
- The clear sky's colours are the picture's, sampled from it and taken back through the game's ACES tonemap at the
  map's exposure (belltower_sky.undisplay): warm peach and gold low towards the sun, a blue-grey higher up, and on the
  far side a dusky pink band over a blue-grey horizon (the Belt of Venus).
- An altocumulus layer 4.2 km up: rows of small cloudlets (a mackerel sky, cellular noise stretched across the wind),
  thinned and thickened in patches tens of kilometres across. Seen in perspective they're big overhead and small and
  crowded towards the horizon, as in the picture. The low sun lights their undersides: gold towards it, salmon and
  pink across the sky, mauve behind; thick middles stay blue-grey. Far ones fade into the horizon's haze.
- Under the horizon it's the far sea (the map's sea ends a kilometre and a half out): slate grey with the sun's
  glitter path under the sun.
- Writes Assets/materials/veridant/sky/veridant_sky.exr and veridant_sky.vmat.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import belltower_sky as BS  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/veridant/sky"
RESOURCE_DIR = "materials/veridant/sky"
NAME = "veridant_sky"

SUN_PITCH, SUN_YAW = 3.4, -113.4     # veridant_map's: 3.4 degrees up, 23.4 degrees north of west
# The map's tonemap holds its exposure at 2.2, and the engine's exposure runs at about twice belltower_sky's
# design scale: in a capture at a fixed exposure of 4.0 this sky showed the colours it was sampled for (2026-10-15).
# So it's baked for 1.1, and what isn't keyed (the sun's glow and disc, the glitter) is scaled to match.
EXPOSURE = 1.1
RADIANCE = BS.DESIGN_EXPOSURE / EXPOSURE
# The engine's ACES came out a little warmer than belltower_sky's display: a touch cooler here (linear).
BALANCE = np.array( ( 0.86, 1.0, 1.12 ), np.float32 )

# The clear sky's displayed colours (sRGB) by degrees above the horizon: towards the sun and away from it.
SUN_SIDE = ( ( -1.0, ( 120, 104, 104 ) ), ( 0.0, ( 240, 184, 128 ) ), ( 1.5, ( 236, 176, 124 ) ), ( 4.0, ( 214, 160, 126 ) ),
             ( 7.0, ( 168, 140, 134 ) ), ( 10.0, ( 124, 118, 128 ) ), ( 14.0, ( 100, 102, 118 ) ), ( 20.0, ( 90, 96, 114 ) ),
             ( 40.0, ( 82, 92, 114 ) ), ( 90.0, ( 78, 90, 116 ) ) )
AWAY_SIDE = ( ( -1.0, ( 74, 74, 86 ) ), ( 0.0, ( 120, 112, 130 ) ), ( 2.5, ( 150, 124, 140 ) ), ( 6.0, ( 140, 122, 142 ) ),
              ( 12.0, ( 108, 108, 132 ) ), ( 25.0, ( 90, 98, 122 ) ), ( 50.0, ( 82, 92, 118 ) ), ( 90.0, ( 78, 90, 116 ) ) )
# Clouds' displayed colours: lit by the low sun, by degrees from the sun; and their shaded middles.
CLOUD_LIT = ( ( 0.0, ( 255, 226, 178 ) ), ( 6.0, ( 252, 210, 162 ) ), ( 14.0, ( 238, 184, 146 ) ), ( 24.0, ( 212, 162, 146 ) ),
              ( 40.0, ( 180, 150, 152 ) ), ( 70.0, ( 162, 146, 156 ) ), ( 120.0, ( 152, 140, 156 ) ), ( 180.0, ( 148, 136, 154 ) ) )
CLOUD_SHADE = ( ( 0.0, ( 118, 92, 86 ) ), ( 15.0, ( 92, 82, 86 ) ), ( 40.0, ( 74, 74, 86 ) ), ( 180.0, ( 70, 72, 86 ) ) )
SEA_FAR = ( ( -90.0, ( 34, 38, 46 ) ), ( -6.0, ( 48, 50, 58 ) ), ( -1.5, ( 70, 66, 74 ) ), ( -0.2, ( 112, 98, 102 ) ),
            ( 0.0, ( 150, 120, 112 ) ) )

CLOUD_HEIGHT = 4200.0       # metres
CELL = 640.0                # the cloudlets' spacing (metres) across the wind; along it CELL * STRETCH
STRETCH = 1.7
CELL_TILE = 26000.0         # the cell field repeats this often (metres); the coverage field doesn't for 400 km
COVER_TILE = 400000.0
WIND = math.radians( 35.0 ) # the rows run across this heading (from x towards y)
HAZE_DISTANCE = 150000.0    # metres for the haze to swallow 63% of a cloud
SLAB = ( 3500.0, 5000.0 )   # the layer's base and top (metres)
SLAB_STEPS = 6
SIGMA = 1.6                 # extinction per kilometre of path through a cloudlet


def sun_direction():
    BS.SUN_PITCH, BS.SUN_YAW = SUN_PITCH, SUN_YAW
    return BS.sun_direction()


def keyed( keys, x ):
    """ Linear colours for x from displayed-colour keys, interpolated in log space (ratios), as belltower_sky does. """
    xs = np.array( [ k for k, _ in keys ] )
    logs = np.log( np.array( [ BS.undisplay( np.array( c, float ), EXPOSURE ) for _, c in keys ] ) )
    return np.exp( np.stack( [ np.interp( x, xs, logs[:, c] ) for c in range( 3 ) ], -1 ) ).astype( np.float32 )


def periodic_fbm( rng, n, octaves, base, persistence=0.55 ):
    """ Tileable value noise on n x n, roughly -1..1, from upsampled periodic random grids. """
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


def worley( rng, n, spacing_px, stretch ):
    """ Distance (pixels, in the unstretched frame) to the nearest jittered cell centre on a tileable n x n grid whose
    cells are spacing_px across and stretch times that along. Cells are jittered points, a few dropped. """
    nx = max( 2, int( round( n / spacing_px ) ) )
    ny = max( 2, int( round( n / ( spacing_px * stretch ) ) ) )
    gx, gy = np.meshgrid( np.arange( nx ), np.arange( ny ), indexing="ij" )
    px = ( gx + 0.5 + rng.uniform( -0.42, 0.42, gx.shape ) ) * n / nx
    py = ( gy + 0.5 + rng.uniform( -0.42, 0.42, gy.shape ) ) * n / ny
    keep = rng.random( gx.shape ) > 0.08
    pts = np.stack( [ px[keep], py[keep] ], -1 )
    # Copies round the tile so the distances wrap.
    copies = np.concatenate( [ pts + np.array( ( dx * n, dy * n ) ) for dx in ( -1, 0, 1 ) for dy in ( -1, 0, 1 ) ] )
    scale = np.array( ( 1.0, 1.0 / stretch ) )
    tree = cKDTree( copies * scale )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 )
    q = np.stack( [ xx.ravel(), yy.ravel() ], -1 ) * scale
    dist, _ = tree.query( q, k=2 )
    f1 = dist[:, 0].reshape( n, n ).astype( np.float32 )
    f2 = dist[:, 1].reshape( n, n ).astype( np.float32 )
    return f1, f2


class CloudFields:
    def __init__( self, seed ):
        rng = np.random.default_rng( seed )
        n = 2048
        self.n = n
        self.cell_m = CELL_TILE / n
        f1, f2 = worley( rng, n, CELL / self.cell_m, STRETCH )
        spacing = CELL / self.cell_m
        # A cloudlet: dense in its middle, thinning out to its edge, separated from its neighbours by a gap.
        puff = np.clip( 1.0 - f1 / ( spacing * 0.62 ), 0, 1 ) ** 1.3
        edge = np.clip( ( f2 - f1 ) / ( spacing * 0.35 ), 0, 1 )
        wobble = periodic_fbm( rng, n, 6, 32 )
        self.cells = np.clip( puff * ( 0.55 + 0.45 * edge ) * ( 1.0 + 0.35 * wobble ), 0, 1.4 ).astype( np.float32 )
        self.cells_mean = float( self.cells.mean() )
        # Blurred copies for far clouds, so the horizon's crowded cloudlets average out instead of aliasing.
        self.blurred = [ self.cells ]
        for sigma in ( 2, 4, 8, 16, 32 ):
            self.blurred.append( ndimage.gaussian_filter( self.cells, sigma, mode="wrap" ) )
        self.detail = periodic_fbm( rng, n, 7, 16 )
        # Clumps a few kilometres across that the cloudlets gather into, with ragged edges.
        self.clumps = periodic_fbm( rng, n, 8, 5, 0.58 )
        self.cover_m = COVER_TILE / 1024
        self.cover = periodic_fbm( rng, 1024, 6, 6, 0.6 )
        self.thin = periodic_fbm( rng, 1024, 5, 12, 0.6 )

    def sample( self, table, xm, ym, metres ):
        u = ( xm / metres ) % table.shape[1]
        v = ( ym / metres ) % table.shape[0]
        return ndimage.map_coordinates( table, [ v.ravel(), u.ravel() ], order=1, mode="grid-wrap" ).reshape( xm.shape )

    def density( self, xm, ym, footprint ):
        """ Cloud density at plane points ( metres ), with the pixel's footprint on the plane (metres) picking how much
        of the cloudlets' detail survives. """
        c, s = math.cos( WIND ), math.sin( WIND )
        u, v = c * xm + s * ym, -s * xm + c * ym
        # Warp the cells so the cloudlets run together into clumps and broken rows rather than a honeycomb.
        wx = self.sample( self.detail, u * 0.37 + 5000.0, v * 0.37, self.cell_m )
        wy = self.sample( self.detail, v * 0.37 - 7000.0, u * 0.37 + 3000.0, self.cell_m )
        uw, vw = u + wx * CELL * 0.55, v + wy * CELL * 0.55
        cover = self.sample( self.cover, xm, ym, self.cover_m )
        thin = self.sample( self.thin, xm, ym, self.cover_m )
        amount = smoothstep( -1.9, 0.35, cover + 0.45 * thin )
        level = np.clip( np.log2( np.maximum( footprint / ( self.cell_m * 1.5 ), 1.0 ) ), 0, len( self.blurred ) - 1 )
        lo = np.floor( level ).astype( int )
        cells = np.zeros_like( xm )
        for k in range( len( self.blurred ) ):
            sel = ( lo == k ) | ( lo + 1 == k )
            if not sel.any():
                continue
            w = np.where( lo == k, 1.0 - ( level - lo ), level - lo )
            cells[sel] += w[sel] * self.sample( self.blurred[k], uw[sel], vw[sel], self.cell_m )
        clumps = self.sample( self.clumps, u * 0.9 + 1234.0, v * 0.9, self.cell_m )
        shape = smoothstep( -0.9, 0.85, clumps + 1.6 * ( amount - 0.45 ) )
        detail = self.sample( self.detail, uw * 2.3, vw * 2.3, self.cell_m )
        keep = np.clip( 1.0 - footprint / 3000.0, 0, 1 )
        d = shape * ( 0.35 + 1.0 * cells ) * 1.3 * ( 1.0 + 0.3 * detail * keep )
        return np.clip( d, 0, 2.5 ).astype( np.float32 )


def render( width=8192, seed=7, rows=None ):
    h = width // 2
    sun = sun_direction()
    sun_az = math.atan2( sun[1], sun[0] )
    fields = CloudFields( seed )
    out = np.zeros( ( h, width, 3 ), np.float32 )
    pixel = 2 * math.pi / width
    rng = np.random.default_rng( seed + 1 )
    sparkle = rng.random( ( h, width ) ).astype( np.float32 )
    for r0 in range( 0, h, 128 ):
        rr = np.arange( r0, min( h, r0 + 128 ) )
        d = BS.panorama_directions( width, h, rr ).astype( np.float32 )
        el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
        az = np.arctan2( d[..., 1], d[..., 0] )
        daz = np.degrees( np.abs( ( az - sun_az + math.pi ) % ( 2 * math.pi ) - math.pi ) )
        ang = np.degrees( np.arccos( np.clip( d @ sun, -1, 1 ) ) )
        towards = ( ( 1.0 + np.cos( np.radians( daz ) ) ) * 0.5 ) ** 2.2
        sky = keyed( SUN_SIDE, el ) * towards[..., None] + keyed( AWAY_SIDE, el ) * ( 1 - towards[..., None] )
        # The sun's glow: wide and gold, narrower and whiter towards it.
        glow = ( 5.0 * np.exp( -ang / 0.7 ) + 2.0 * np.exp( -ang / 1.8 ) + 0.55 * np.exp( -ang / 6.0 ) + 0.16 * np.exp( -ang / 22.0 ) )
        glow_col = np.array( ( 1.0, 0.62, 0.30 ), np.float32 )
        sky += ( RADIANCE * glow[..., None] * glow_col * ( 0.4 + 0.6 * np.exp( -np.maximum( el, 0 ) / 18.0 ) )[..., None] ).astype( np.float32 )
        # Clouds on the plane.
        up = d[..., 2]
        above = up > 0.0015
        cloud = np.zeros( el.shape, np.float32 )
        if above.any():
            upc = np.maximum( up, 0.0015 )
            t = CLOUD_HEIGHT / upc
            xm, ym = d[..., 0] * t, d[..., 1] * t
            footprint = t * pixel / np.maximum( up, 0.02 )
            # How much sunlight reaches each point through the layer: the low sun's light runs nearly level, so it's
            # the cloud between the point and the sun along the plane that shades it (taken at the layer's middle).
            sx, sy = sun[0], sun[1]
            norm = math.hypot( sx, sy )
            sx, sy = sx / norm, sy / norm
            depth = np.zeros( el.shape, np.float32 )
            for step, weight in ( ( 160.0, 0.5 ), ( 380.0, 0.45 ), ( 720.0, 0.4 ), ( 1250.0, 0.35 ) ):
                probe = np.zeros( el.shape, np.float32 )
                probe[above] = fields.density( xm[above] + sx * step, ym[above] + sy * step, footprint[above] )
                depth += weight * probe
            light = np.exp( -1.1 * depth )
            lit = keyed( CLOUD_LIT, ang )
            shade = keyed( CLOUD_SHADE, ang )
            fade = 0.65 + 0.35 * np.exp( -np.maximum( el - 4.0, 0 ) / 16.0 )
            # March through the layer's thickness: a cloudlet with more in it reaches higher and lower, round in
            # section, so the clouds have bodies, crowd together towards the horizon and hide the sky behind.
            trans = np.ones( el.shape, np.float32 )
            colour = np.zeros( el.shape + ( 3, ), np.float32 )
            for k in range( SLAB_STEPS ):
                sk = ( k + 0.5 ) / SLAB_STEPS
                hk = SLAB[0] + sk * ( SLAB[1] - SLAB[0] )
                tk = hk / upc
                dk = np.zeros( el.shape, np.float32 )
                dk[above] = fields.density( d[..., 0][above] * tk[above], d[..., 1][above] * tk[above], ( tk * pixel / np.maximum( up, 0.02 ) )[above] )
                prof = 1.05 * abs( 2 * sk - 1 ) ** 1.5
                inside = smoothstep( prof, prof + 0.4, dk )
                seg = ( SLAB[1] - SLAB[0] ) / SLAB_STEPS / upc / 1000.0
                a_k = 1.0 - np.exp( -SIGMA * inside * seg )
                thin = 1.0 - smoothstep( 0.0, 1.4, dk )
                # The low sun lights the clouds' undersides: lower in the layer, more of it.
                amount = np.clip( light * ( 0.3 + 0.7 * thin ) * ( 1.25 - 0.6 * sk ), 0, 1 ) * fade
                c_k = shade * ( 1 - amount[..., None] ) + lit * amount[..., None]
                c_k *= ( 1.0 + 1.6 * np.exp( -ang / 7.0 ) * thin * light )[..., None]
                colour += ( trans * a_k )[..., None] * c_k
                trans *= 1.0 - a_k
            alpha = 1.0 - trans
            colour /= np.maximum( alpha, 1e-5 )[..., None]
            haze = np.exp( -t / HAZE_DISTANCE ) * smoothstep( 0.0015, 0.012, up )
            alpha *= haze
            alpha[~above] = 0.0
            cloud = alpha
            sky = sky * ( 1 - alpha[..., None] ) + colour * alpha[..., None]
        # Under the horizon: the far sea, and the glitter path under the sun.
        below = el < 0
        if below.any():
            sea = keyed( SEA_FAR, el )
            path = np.exp( -daz / 2.2 ) * np.exp( -np.abs( el ) / 3.0 )
            glint = path * ( 0.25 + 1.8 * ( sparkle[rr] > 0.9 ) )
            sea = sea + ( RADIANCE * glint[..., None] * np.array( ( 2.6, 1.7, 0.95 ), np.float32 ) )
            blend = smoothstep( 0.0, -0.15, el )
            sky = sky * ( 1 - blend[..., None] ) + sea * blend[..., None]
        # The sun's disc.
        disc = smoothstep( 0.34, 0.26, ang )
        sky = sky * ( 1 - disc[..., None] ) + RADIANCE * np.array( ( 60.0, 50.0, 34.0 ), np.float32 ) * disc[..., None]
        out[rr] = sky * BALANCE
        del cloud
    return out


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def vmat_text():
    return ( "// Tools/veridant_sky.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/sky.shader"\n'
             '    F_TEXTURE_FORMAT2 "6"\n'
             '    g_flBrightnessExposureBias "0"\n'
             '    g_flRenderOnlyExposureBias "0"\n'
             f'    SkyTexture "{RESOURCE_DIR}/{NAME}.exr"\n'
             "}\n" )


def preview( rgb, path, yaw=90.0, pitch=-9.6, fov=74.0, size=( 1536, 1024 ) ):
    """ The panorama as the map's hero view sees it (looking west from the east terrace), displayed as a match would. """
    from PIL import Image
    d = BS.view_directions( yaw, pitch, fov, size )
    u, v = BS.panorama_uv( d )
    h, w = rgb.shape[:2]
    cols = np.clip( u * w - 0.5, 0, w - 1 )
    rows = np.clip( v * h - 0.5, 0, h - 1 )
    img = np.stack( [ ndimage.map_coordinates( rgb[..., c], [ rows.ravel(), cols.ravel() ], order=1 ).reshape( rows.shape ) for c in range( 3 ) ], -1 )
    Image.fromarray( BS.display( img / BALANCE, EXPOSURE ) ).save( path )
    print( f"wrote {path}" )


def main():
    ap = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    ap.add_argument( "--out" )
    ap.add_argument( "--width", type=int, default=8192 )
    ap.add_argument( "--seed", type=int, default=7 )
    ap.add_argument( "--preview" )
    ap.add_argument( "--no-write", action="store_true" )
    args = ap.parse_args()
    rgb = render( args.width, args.seed )
    if not args.no_write:
        out = Path( args.out ) if args.out else OUT_DIR
        out.mkdir( parents=True, exist_ok=True )
        BS.write_exr( out / f"{NAME}.exr", rgb )
        ( out / f"{NAME}.vmat" ).write_text( vmat_text(), encoding="utf-8", newline="\n" )
        print( f"wrote {out / f'{NAME}.exr'}" )
    if args.preview:
        preview( rgb, args.preview )


if __name__ == "__main__":
    main()
