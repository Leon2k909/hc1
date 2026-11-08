"""
Riverside's sleeper retaining walls (rs_ties) from a real timber scan, replacing riverside_materials.ties()'s numpy paint.

    python Tools/riverside_sleepers.py [--size 4096] [--out <dir>]

The user (2026-11-07) said the walls' texture "looks bad": the procedural one was 11 px/in with pale cloudy blotches,
machine-straight courses and no real grain. Nothing in the project fitted as it was (Railhead's rw_sleeper is concrete,
its rw_sleeper_wood is procedural too, the scanned planks are boards in a deck), so this lays real wood out as a wall:

- The wood is Belltower's photographed weathered oak boards, brown_planks_03 (4K diffuse, GL normal, roughness, AO).
  Each of its nine boards is found from the gaps in the scan and straightened, then used as one sleeper's face, so
  every sleeper is a different photographed board. Its normal map is integrated to height (Frankot-Chellappa, as
  Sources/Belltower/props/headstone-v2/scan_stone.py does), so the wall's own shapes can be added to it.
- A 96 in tile (riverside_materials' TILES["rs_ties"]) of 12 courses, 8 in apart: 7.5 in faces with eased arrises and
  dark, soil-filled joints that wander a little, as stacked ties never sit dead straight. Each course has one butt
  joint, staggered from the courses either side. Each sleeper is flipped and started at random along its board.
- Tone is per sleeper: the board's own broad blotches are flattened, then each is lighter or darker, and some keep the
  dark brown of creosote that hasn't weathered out. Growth is sparse and sits in the joints only.
- 4096 px for 96 in is 43 px/in, the density the project's scan-built surfaces use. Colour, normal (GL), roughness and
  AO go to materials/riverside/rs_ties_v2_*.png; the old rs_ties_* maps are kept. rs_ties.vmat points at the new maps.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path( __file__ ).resolve().parents[1]
SCAN = ROOT / "Assets/materials/belltower/scans/brown_planks_03"
RESOURCE_DIR = "materials/riverside"
TILE = 96.0           # inches, as riverside_materials.TILES["rs_ties"]
COURSE = 8.0          # inches between courses
FACE = 7.5            # a sleeper's visible face; the rest of the course is joint
ARRIS = 0.55          # inches of rounded edge along a sleeper's top and bottom
END_ARRIS = 0.35      # and at its ends
SCAN_PPI = 52.0       # the scan's boards are about 8.7 in wide across 460 px
RELIEF = 2.4          # the scan's grain relief, deepened for big, checked timbers
SEED = 2611
Image.MAX_IMAGE_PIXELS = None


def srgb_to_linear( c ):
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def linear_to_srgb( c ):
    c = np.clip( c, 0, 1 )
    return np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 )


def grey( path ):
    a = np.asarray( Image.open( path ) ).astype( np.float32 )
    if a.ndim == 3:
        a = a[..., 0]
    return a / ( 65535.0 if a.max() > 255 else 255.0 )


def integrate( nx, ny ):
    """ Height in pixels from a normal map's slopes (Frankot-Chellappa). Rows run down the image, GL normals' y up it. """
    h, w = nx.shape
    u, v = np.meshgrid( np.fft.fftfreq( w ) * 2 * np.pi, np.fft.fftfreq( h ) * 2 * np.pi )
    denom = u * u + v * v
    denom[0, 0] = 1.0
    out = np.fft.ifft2( ( -1j * u * np.fft.fft2( -nx ) - 1j * v * np.fft.fft2( ny ) ) / denom ).real
    return out.astype( np.float32 )


def periodic_noise( rng, n, period, terms=6, falloff=1.4 ):
    """ Smooth noise over n samples that repeats every `period` of them (so the tile tiles). """
    t = np.arange( n ) / period * 2 * np.pi
    out = np.zeros( n, np.float32 )
    for k in range( 1, terms + 1 ):
        out += rng.normal( 0, 1 ) / k ** falloff * np.sin( k * t + rng.uniform( 0, 2 * np.pi ) )
    return out / ( np.abs( out ).max() + 1e-6 )


def noise2d( rng, n, sigma ):
    a = ndi.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), sigma, mode="wrap" )
    return a / ( a.std() + 1e-6 )


def load_scan():
    srgb = np.asarray( Image.open( f"{SCAN}_diffuse_4k.png" ).convert( "RGB" ) ).astype( np.float32 ) / 255.0
    linear = srgb_to_linear( srgb ).astype( np.float32 )
    # Each board has broad blotches of its own; flatten everything broader than ~2 in, the wall lays its own tone over it.
    log = np.log( linear + 0.01 )
    broad = ndi.gaussian_filter( log, ( 100, 100, 0 ), mode="wrap" )
    linear = ( np.exp( log - broad + broad.reshape( -1, 3 ).mean( 0 ) ) - 0.01 ).astype( np.float32 )
    normal = np.asarray( Image.open( f"{SCAN}_nor_gl_4k.png" ).convert( "RGB" ) ).astype( np.float32 ) / 255.0 * 2 - 1
    sx = normal[..., 0] / np.maximum( normal[..., 2], 0.25 )
    sy = normal[..., 1] / np.maximum( normal[..., 2], 0.25 )
    height = integrate( sx, sy )
    height = ( height - ndi.gaussian_filter( height, 120, mode="wrap" ) ) / SCAN_PPI  # inches
    rough = grey( f"{SCAN}_rough_4k.png" )
    ao = grey( f"{SCAN}_ao_4k.png" )
    return linear, height.astype( np.float32 ), rough.astype( np.float32 ), ao.astype( np.float32 )


def find_boards( linear ):
    """ The boards run down the scan. Their gaps are its darkest columns; each gap is followed down the image in bands
    (the boards aren't dead straight), giving every board's left and right edge per row. """
    lum = linear @ np.array( ( 0.2126, 0.7152, 0.0722 ), np.float32 )
    h, w = lum.shape
    col = ndi.uniform_filter1d( lum.mean( 0 ), 15, mode="wrap" )
    gaps = []
    for x in np.argsort( col ):
        if all( min( abs( x - g ), w - abs( x - g ) ) > 300 for g in gaps ):
            gaps.append( int( x ) )
        if len( gaps ) == 9:
            break
    gaps.sort()
    bands = 16
    rows = ( np.arange( bands ) + 0.5 ) * h / bands
    tracks = []
    for g in gaps:
        xs = []
        for b in range( bands ):
            strip = lum[int( b * h / bands ):int( ( b + 1 ) * h / bands )].mean( 0 )
            window = [ ( g + d ) % w for d in range( -60, 61 ) ]
            xs.append( g + ( int( np.argmin( strip[window] ) ) - 60 ) )
        xs = ndi.uniform_filter1d( np.array( xs, np.float32 ), 3, mode="wrap" )
        tracks.append( np.interp( np.arange( h ), rows, xs, period=h ) )
    boards = []
    for i, left in enumerate( tracks ):
        right = tracks[( i + 1 ) % len( tracks )]
        right = np.where( right < left, right + w, right )
        boards.append( ( left + 28, right - 28 ) )  # stay clear of the gap and the board's own worn edge
    return boards


def sample( channels, rows, cols ):
    """ Bilinear samples of each (H, W) channel at fractional rows/cols, wrapping. """
    coords = np.array( [ rows.ravel(), cols.ravel() ] )
    return [ ndi.map_coordinates( c, coords, order=1, mode="grid-wrap" ).reshape( rows.shape ) for c in channels ]


def build( size=4096 ):
    rng = np.random.default_rng( SEED )
    linear, height, rough, ao = load_scan()
    boards = find_boards( linear )
    sh = linear.shape[0]
    ppi = size / TILE
    courses = int( round( TILE / COURSE ) )
    x = np.arange( size, dtype=np.float32 )
    y = np.arange( size, dtype=np.float32 )

    out_col = np.zeros( ( size, size, 3 ), np.float32 )
    out_h = np.zeros( ( size, size ), np.float32 )
    out_r = np.zeros( ( size, size ), np.float32 )
    out_ao = np.zeros( ( size, size ), np.float32 )
    joint = np.ones( ( size, size ), np.float32 )  # 1 in the joints, 0 on wood

    # Each sleeper's top and bottom edges wander on their own (up to ~0.25 in, repeating across the tile), so the joints
    # between courses close up in places and open to about an inch in others, as stacked ties do.
    butts = []
    creosote = srgb_to_linear( np.array( ( 44, 33, 25 ), np.float32 ) / 255 )
    last_board = None
    for c in range( courses ):
        top = c * COURSE * ppi + ( 0.12 + 0.13 * periodic_noise( rng, size, size ) ) * ppi           # per column
        bottom = c * COURSE * ppi + ( FACE + 0.1 * periodic_noise( rng, size, size ) ) * ppi
        bottom = np.minimum( bottom, ( c + 1 ) * COURSE * ppi - 0.03 * ppi )
        # One butt joint per course, at least 18 in from the course below's.
        while True:
            butt = rng.uniform( 0, size )
            if not butts or min( abs( butt - butts[-1] ), size - abs( butt - butts[-1] ) ) > 18 * ppi:
                break
        butts.append( butt )
        board = rng.choice( [ b for b in range( len( boards ) ) if b != last_board ] )
        last_board = board
        left, right = boards[board]
        flip_u = rng.random() < 0.5
        flip_v = rng.random() < 0.5
        start = rng.uniform( 0, sh )
        y0 = int( np.floor( top.min() ) ) - 2
        y1 = int( np.ceil( bottom.max() ) ) + 2
        yy = np.arange( y0, y1, dtype=np.float32 )[:, None]
        t = ( yy - top[None, :] ) / ( bottom - top )[None, :]        # 0..1 across the face
        inside = ( t >= 0 ) & ( t <= 1 )
        # The butt joint is sawn a little off square, and its gap is 0.1-0.35 in.
        lean = rng.uniform( -0.25, 0.25 ) * ppi
        along = ( x[None, :] - butt - lean * ( yy - top.mean() ) / ( FACE * ppi ) ) % size  # px from the butt joint
        butt_gap = rng.uniform( 0.1, 0.35 )
        src_row = ( start + ( -along if flip_u else along ) * ( sh / size ) ) % sh
        src_row = np.broadcast_to( src_row, t.shape )
        tv = 1 - t if flip_v else t
        lr = np.interp( src_row.ravel(), np.arange( sh ), left ).reshape( t.shape )
        rr = np.interp( src_row.ravel(), np.arange( sh ), right ).reshape( t.shape )
        src_col = lr + np.clip( tv, 0, 1 ) * ( rr - lr )
        red, green, blue, h_c, r_c, ao_c = sample( [ linear[..., 0], linear[..., 1], linear[..., 2], height, rough, ao ],
                                                   src_row, src_col )
        wood = np.stack( ( red, green, blue ), -1 )

        # This sleeper's own tone: lighter or darker, a little warmer (cool shifts read blue), and about half keep
        # creosote that hasn't weathered out, patchy along their length.
        bright = float( np.clip( rng.normal( 1.0, 0.17 ), 0.66, 1.35 ) )
        warm = float( np.clip( rng.normal( 0.02, 0.035 ), -0.015, 0.08 ) )
        tar = float( rng.uniform( 0.35, 0.8 ) if rng.random() < 0.5 else rng.uniform( 0.0, 0.12 ) )
        patch = np.clip( 0.6 + 0.5 * periodic_noise( rng, size, size / 2, terms=6 ), 0, 1 )[None, :]
        wood = wood * bright * np.array( ( 1 + warm, 1, 1 - warm ), np.float32 )
        wood = wood + ( creosote - wood ) * ( tar * patch )[..., None]

        # Eased arrises: the face curves away over ARRIS at top and bottom, END_ARRIS at the butt joints.
        d_edge = np.minimum( t, 1 - t ) * ( bottom - top )[None, :] / ppi  # inches from the nearer long edge
        d_end = np.minimum( along, size - along ) / ppi
        ease = np.clip( 1 - d_edge / ARRIS, 0, 1 )
        ease_end = np.clip( 1 - d_end / END_ARRIS, 0, 1 )
        drop = ARRIS * ( 1 - np.sqrt( np.clip( 1 - ease ** 2, 0, 1 ) ) ) + END_ARRIS * ( 1 - np.sqrt( np.clip( 1 - ease_end ** 2, 0, 1 ) ) )
        shade = 1 - 0.35 * np.maximum( ease, ease_end ) ** 1.5
        # End grain soaks up dirt: darker and warmer for a couple of inches from each butt.
        ends = np.clip( 1 - d_end / 2.5, 0, 1 ) ** 2
        # End splits: one to three checks running in from each butt along the grain, a few inches long.
        split = np.zeros( t.shape, np.float32 )
        for end_side in ( 0, 1 ):
            for _ in range( rng.integers( 1, 4 ) ):
                at, reach = rng.uniform( 0.2, 0.8 ), rng.uniform( 1.5, 5.0 )
                d_in = ( along if end_side == 0 else size - along ) / ppi
                width = 0.05 * np.clip( 1 - d_in / reach, 0, 1 )
                split = np.maximum( split, np.clip( 1 - np.abs( t - at ) * ( bottom - top )[None, :] / ppi / np.maximum( width, 1e-3 ), 0, 1 ) * ( d_in < reach ) )
        wood = wood * ( 1 - 0.28 * ends )[..., None] * shade[..., None] * ( 1 - 0.8 * split )[..., None]
        face_h = h_c * RELIEF - drop - 0.25 * split
        rows = np.arange( y0, y1 ) % size
        # The butt joint itself is a thin dark gap.
        sel = np.nonzero( inside & ( d_end >= butt_gap / 2 ) )
        rr_, cc_ = rows[sel[0]], sel[1]
        out_col[rr_, cc_] = wood[sel]
        out_h[rr_, cc_] = face_h[sel]
        out_r[rr_, cc_] = r_c[sel]
        out_ao[rr_, cc_] = ( ao_c * shade )[sel]
        joint[rr_, cc_] = 0.0

    # Joints: packed dark soil sunk 1.2 in behind the faces, rough and in shadow, browner in places.
    j = joint > 0.5
    grit = noise2d( rng, size, 1.5 )
    loam = np.clip( 0.5 + 0.5 * noise2d( rng, size, 1.5 * ppi ), 0, 1 )
    soil_col = ( np.array( ( 0.016, 0.013, 0.010 ), np.float32 ) * ( 1 - loam[..., None] )
                 + np.array( ( 0.034, 0.024, 0.015 ), np.float32 ) * loam[..., None] ) * ( 1 + 0.1 * grit )[..., None]
    out_col[j] = soil_col[j]
    out_h[j] = -1.2 + 0.02 * grit[j]
    out_r[j] = 0.95
    out_ao[j] = 0.3
    # Sparse growth, only in the joints and the arrises beside them, sinking in.
    near = ndi.gaussian_filter( joint, 0.35 * ppi, mode="wrap" )
    growth = np.clip( ( noise2d( rng, size, 2.2 * ppi ) - 1.6 ) * 2.0, 0, 1 ) * np.clip( near * 2.2, 0, 1 )
    moss = srgb_to_linear( np.array( ( 54, 62, 32 ), np.float32 ) / 255 )
    out_col = out_col + ( moss * 0.8 - out_col ) * ( growth * 0.6 )[..., None]
    out_r = np.clip( out_r * ( 1 - 0.15 * growth ) + 0.05 * growth, 0.3, 1 )
    print( f"growth covers {np.mean( growth > 0.2 ) * 100:.1f}% of the tile" )

    # Height to a GL normal: slopes in inches per inch, rows run down the image.
    hx = ( np.roll( out_h, -1, 1 ) - np.roll( out_h, 1, 1 ) ) * 0.5 * ppi
    hy = ( np.roll( out_h, -1, 0 ) - np.roll( out_h, 1, 0 ) ) * 0.5 * ppi
    n = np.stack( ( -hx, hy, np.ones_like( hx ) ), -1 )
    n /= np.linalg.norm( n, axis=-1, keepdims=True )
    return linear_to_srgb( out_col ), n, out_r, np.clip( out_ao, 0, 1 )


def vmat_text( prefix ):
    return f"""// Tools/riverside_sleepers.py: sleeper retaining walls from a real timber scan (old maps: rs_ties_*.jpg, kept)
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "{prefix}_color.png"
    TextureNormal "{prefix}_normal.png"
    TextureRoughness "{prefix}_rough.png"
    TextureAmbientOcclusion "{prefix}_ao.png"
    g_flAmbientOcclusionDirectDiffuse "0.300"
    g_vColorTint "[1.000000 1.000000 1.000000 1.000000]"
    g_flModelTintAmount "1.0"
}}
"""


def write( out=None, size=4096 ):
    out = Path( out or ROOT / "Assets" / RESOURCE_DIR )
    colour, normal, rough, ao = build( size )
    u8 = lambda a: np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 )
    Image.fromarray( u8( colour ), "RGB" ).save( out / "rs_ties_v2_color.png", optimize=True )
    Image.fromarray( u8( normal * 0.5 + 0.5 ), "RGB" ).save( out / "rs_ties_v2_normal.png", optimize=True )
    half = ( size // 2, size // 2 )  # roughness and AO hold no fine detail worth the memory
    Image.fromarray( u8( rough ), "L" ).resize( half, Image.Resampling.LANCZOS ).save( out / "rs_ties_v2_rough.png", optimize=True )
    Image.fromarray( u8( ao ), "L" ).resize( half, Image.Resampling.LANCZOS ).save( out / "rs_ties_v2_ao.png", optimize=True )
    ( out / "rs_ties.vmat" ).write_text( vmat_text( f"{RESOURCE_DIR}/rs_ties_v2" ), encoding="utf-8", newline="\n" )
    print( f"wrote rs_ties ({size} px, {size / TILE:.1f} px/in) to {out}" )
    return colour


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--size", type=int, default=4096 )
    parser.add_argument( "--out", help="write here instead of Assets/materials/riverside (for a preview)" )
    args = parser.parse_args()
    if args.out:
        Path( args.out ).mkdir( parents=True, exist_ok=True )
    write( args.out, args.size )


if __name__ == "__main__":
    main()
