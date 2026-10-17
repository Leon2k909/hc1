"""
Riverdale's yard dressing: the ground level of the outdoor play spaces (the east and west yards, the hall's apron, the
courts, the north lane and the spawn strips) dressed as a working plant's yard just after rain. Tools/riverdale_map.py
adds its two models through extra_models(). Neither collides: nothing here stops players, bots or bullets, and the
existing collision (riverdale_map's boxes and hulls, riverdale_parts.CLIPS) is unchanged.

- riverdale_yard_ground ("Yard Ground Detail", casts no shadows): what lies on the slab, each layer a fraction of an
  inch over the last (Z_*): tyre marks and stains, damp bands along the walls' feet, puddles (a wet rim round glassy
  water), painted markings, drains and covers, and the hall's south footway with its kerb.
- riverdale_yard_props ("Yard Props", casts shadows): small clutter kept to walls, corners and the sides of cover:
  drums, pallets, an IBC tote, cable reels, cones, sand bins, spill kits, hose reels, hydrants, a safety shower and
  signs on posts.

    python Tools/riverdale_yard.py --check [--plan <dir>] [--stage <dir>]

--check builds the whole map (riverdale_map.build()) and reports any prop that overlaps the collision, stands within 24
of a spawn or objective spot or 120 of a bomb site's centre, or isn't tucked against something, and any puddle that
overlaps a painted line or a drain. --plan also draws each area from above with the collision, the spots and this
dressing, for placing things. --stage writes only these two models (configured as riverdale_map configures them) under
a folder laid out as Assets, which is quicker than the whole map while placing things.

The ground-aligned materials (rv_yd_wet, rv_yd_puddle, rv_yd_stain and the rv_yd_paint_* paints) are drawn from the
ground's own maps (riverdale_materials' rv_yard surface, at its size and tile), so they show the same slab joints, marks
and grain as the ground under them, and its ambient occlusion when it has one.
Their polygons' UVs are the ones the compiled ground shows at each point (GroundUV): map_kit's world UVs at the ground's
corners rounded to half floats (ModelDoc keeps TEXCOORD as R16G16_FLOAT), interpolated across its triangles. Each
group's UVs are moved by whole tiles towards 0, where half floats are finest. So a puddle's rim, a worn line's chips
and a stain's halo meet the ground without a seam. If the ground (riverdale_map.ground(), its rv_yard paint or its
model name) changes, these follow it; if rv_yard is replaced by another material, they need redrawing from it.

Plan coordinates: e east, n north, z up, inches. The yards, courts and spawn strips are dressed for the west side and
mirrored (e -> -e) for the east, with their own shapes (every outline is seeded by side). Lettering and pictograms are
built for the side they're on, so they read the right way round.

Materials (riverdale_materials.load_extras merges them): EXTRA_SURFACES for the textured ones, EXTRA_PAINTS for the
flat ones, all named rv_yd_ so they can't clash with another module's. Every name and marking is the map's own: the
signs are generic safety signs, the covers carry Riverdale Nuclear's name.
"""
import math
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402
import map_kit as K  # noqa: E402
import riverdale_materials as RM  # noqa: E402
import riverdale_parts as P  # noqa: E402
from riverdale_parts import v, card, UP  # noqa: E402

lin, smoothstep = BM.lin, BM.smoothstep


def mix( a, b, t ):
    """ a to b by t, a picture's t ( h, w ) spread over colours. """
    a, b, t = np.asarray( a, np.float32 ), np.asarray( b, np.float32 ), np.asarray( t, np.float32 )
    if t.ndim == 2 and ( a.ndim in ( 1, 3 ) or b.ndim in ( 1, 3 ) ):
        t = t[..., None]
    return a + ( b - a ) * t


# Heights over the slab (z 0) of each layer, lowest first. riverdale_map's own floor lines are at 0.30 and its hazard
# strips at 0.35, so the paint here sits over them.
Z_TYRE_OUT, Z_TYRE_IN = 0.14, 0.19
Z_STAIN_HALO, Z_STAIN_CORE = 0.17, 0.23
Z_RIM, Z_WATER = 0.29, 0.37
Z_PAINT = 0.45
Z_FOOT = 0.6                      # the footway's flags; its kerb stands 1.8
Z_COVER = 0.62                    # manhole covers and gully grates, in frames up to 0.75

YARD_TILE = RM.TILES.get( "rv_yard", 768.0 )
SIGN_ATLAS = ( 2048, 2048 )
CAST_ATLAS = ( 1024, 1024 )
FONT = RM.FONT


# ---------------------------------------------------------------------------------------------------------------------
# Materials

def _yard_maps():
    """ rv_yard's own maps (riverdale_materials' rv_yard surface), drawn once: the ground-aligned materials start from
    them. Its surface function may return the four maps or a dict of them, whose ambient occlusion is passed on. """
    if "yard" not in _CACHE:
        result = RM.SURFACES["rv_yard"]() if "rv_yard" in RM.SURFACES else RM.yard()
        if isinstance( result, dict ):
            c, r, h, ppi = result["colour"], result["rough"], result["height"], result["ppi"]
            _CACHE["ao"] = result.get( "ao" )
        else:
            c, r, h, ppi = result[:4]
        c = np.asarray( c, np.float32 )
        if c.max() > 1.5:
            c = c / 255.0
        _CACHE["yard"] = ( c, np.asarray( r, np.float32 ), np.asarray( h, np.float32 ), float( ppi ) )
    return _CACHE["yard"]


def _result( colour, rough, height, ppi ):
    """ An aligned surface's maps: the four, or a dict with the ground's ambient occlusion when it has one. """
    out = ( colour.astype( np.float32 ), np.clip( rough, 0.0, 1.0 ).astype( np.float32 ), height.astype( np.float32 ), ppi )
    ao = _CACHE.get( "ao" )
    if ao is None:
        return out
    ao = np.asarray( ao, np.float32 )
    while ao.shape[0] > colour.shape[0]:
        ao = _half( ao )
    return dict( colour=out[0], rough=out[1], height=out[2], ppi=ppi, ao=ao )


_CACHE = {}


def _half( a ):
    h, w = a.shape[:2]
    return a.reshape( h // 2, 2, w // 2, 2, *a.shape[2:] ).mean( axis=( 1, 3 ) ).astype( np.float32 )


def _aligned( full=False ):
    """ The ground's colour, roughness, height and pixels per inch: at its own size, or halved when that's over 2048
    (as fine as a stain or a worn line needs). """
    c, r, h, ppi = _yard_maps()
    if full or c.shape[0] <= 2048:
        return c, r, h, ppi
    return _half( c ), _half( r ), _half( h ), ppi / 2


def _noise( seed, n, ppi ):
    rng = np.random.default_rng( seed )

    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( n, n ), ( ppi, ppi ), beta, longest, shortest )
    return nz


def wet_yard():
    """ The slab where water has just drained off it: darker, deeper in colour, glossy, its pores half full. """
    c, r, h, ppi = _aligned( full=True )
    nz = _noise( 7101, c.shape[0], ppi )
    col = c * ( 0.6 * ( 1.0 + 0.06 * nz( 2.2, 40, 3 ) ) )[..., None]
    grey = col.mean( -1, keepdims=True )
    col = grey + ( col - grey ) * 1.3
    rough = np.clip( 0.10 + 0.10 * smoothstep( -1.0, 1.5, nz( 2.0, 16, 1 ) ) + 0.3 * ( r - 0.4 ), 0.04, 0.3 )
    return _result( col, rough, h * 0.8, ppi )


def puddle_water():
    """ Standing water: the slab seen through it, dark, a little silt, a mirror's roughness with a faint dust film, and
    a flat surface (the joints under it are full) with the slightest ripple. """
    c, r, h, ppi = _aligned()
    nz = _noise( 7102, c.shape[0], ppi )
    col = c * 0.3 * np.array( ( 0.92, 0.96, 1.04 ), np.float32 )
    col = mix( col, lin( ( 40, 36, 30 ) ) * 0.5, smoothstep( 0.6, 2.0, nz( 2.0, 24, 2 ) ) * 0.25 )
    rough = 0.022 + 0.03 * smoothstep( 1.4, 2.4, nz( 1.8, 10, 1 ) )
    height = 0.004 * nz( 2.0, 10, 1.5 )
    return _result( col, rough, height, ppi )


def stained_yard():
    """ The slab darkened by what's soaked into it, a little brown: the soft edge round an oil stain, a rust run or a
    tyre mark. """
    c, r, h, ppi = _aligned()
    nz = _noise( 7103, c.shape[0], ppi )
    tone = 0.74 + 0.08 * nz( 2.0, 20, 2 )
    col = c * tone[..., None] * np.array( ( 1.0, 0.94, 0.85 ), np.float32 )
    return _result( col, np.clip( r * 0.85 - 0.03, 0.05, 1.0 ), h, ppi )


def worn_paint( colour, seed, coverage=0.95 ):
    """ Road paint on the slab: whole along most of its length, but worn through in patches where wheels run (islands
    of paint left in them) and flaked off in chips an inch or two across, which show the slab's own concrete (the same
    pixels as the ground's). The concrete's grain shows faintly through the paint, which is grimed and glossy wet. """
    def draw():
        c, r, h, ppi = _aligned()
        nz = _noise( seed, c.shape[0], ppi )
        worn = smoothstep( -0.1, 1.1, nz( 1.8, 40, 3 ) )
        islands = smoothstep( -0.25, 0.35, nz( 1.4, 5, 0.6 ) )
        flakes = smoothstep( 1.75, 2.15, nz( 1.5, 5, 0.6 ) )
        alpha = ( ( 1.0 - worn ) * ( 1.0 - flakes ) + worn * 0.85 * islands * ( 1.0 - flakes ) ) * coverage
        grain = ( c.mean( -1 ) / max( float( c.mean() ), 1e-4 ) ) ** 0.35
        paint = lin( colour ) * ( grain * ( 1.0 + 0.04 * nz( 2.4, 12, 0.5 ) ) )[..., None]
        grime = smoothstep( 0.0, 2.0, nz( 2.2, 20, 2 ) )
        paint = mix( paint, paint * lin( ( 150, 140, 120 ) ) * 2.0, grime * 0.35 )
        col = mix( c, paint, alpha )
        rough = mix( r, 0.3 + 0.06 * nz( 2.0, 8, 1 ), alpha )
        return _result( col, np.clip( rough, 0.05, 1 ), h + 0.015 * alpha, ppi )
    return draw


def oil():
    """ An oil stain's core: near-black, mottled, glossier where it's freshest. """
    nz, x, z, ppi = RM.field( np.random.default_rng( 7111 ), 1024, 48.0 )
    col = lin( ( 30, 28, 25 ) ) * ( 1.0 + 0.3 * nz( 2.2, 16, 1 ) )[..., None]
    col = mix( col, lin( ( 14, 13, 12 ) ), smoothstep( 0.8, 2.0, nz( 1.8, 5, 0.4 ) ) * 0.8 )
    rough = 0.14 + 0.14 * smoothstep( -1.0, 1.5, nz( 2.0, 8, 0.5 ) )
    return np.clip( col, 0, 1 ).astype( np.float32 ), rough.astype( np.float32 ), ( 0.004 * nz( 1.0, 1, 0.1 ) ).astype( np.float32 ), ppi


def rust_stain():
    """ Rust washed out of steel onto wet concrete: orange-brown in streaks and blotches over darkened grey. """
    nz, x, z, ppi = RM.field( np.random.default_rng( 7112 ), 1024, 48.0 )
    base = lin( ( 70, 68, 64 ) ) * ( 1.0 + 0.08 * nz( 2.0, 12, 0.5 ) )[..., None]
    rust = mix( BM.RUST_STAIN, BM.RUST_DARK, smoothstep( 0.5, 2.0, nz( 1.6, 4, 0.3 ) ) )
    amount = smoothstep( -0.8, 1.2, 0.8 * nz( 2.2, 14, 1.5 ) + 0.3 * nz( 1.4, 2, 0.4 ) )
    col = mix( base, rust * 0.75, amount * 0.85 )
    rough = 0.55 + 0.15 * amount
    return np.clip( col, 0, 1 ).astype( np.float32 ), rough.astype( np.float32 ), ( 0.006 * nz( 1.2, 2, 0.1 ) ).astype( np.float32 ), ppi


def tyre():
    """ Rubber left on the slab, for the middle of a tyre mark: u across the mark (0..1), v along it (48 in a tile).
    Tread blocks show faintly where the rubber is thick, and it thins towards the mark's edges. """
    n = 1024
    rng = np.random.default_rng( 7113 )
    across = ( np.arange( n, dtype=np.float32 ) + 0.5 ) / n
    along = 48.0 - ( np.arange( n, dtype=np.float32 ) + 0.5 ) / n * 48.0
    a, s = np.meshgrid( across, along )
    smear = BM.noise( rng, ( n, n ), ( n / 6.0, n / 48.0 ), 2.0, 30, 1.0 )
    block = ( ( s + 0.9 * np.abs( ( a * 6.0 ) % 2.0 - 1.0 ) ) % 1.6 ) < 0.75
    edge = smoothstep( 0.0, 0.3, np.minimum( a, 1.0 - a ) )
    amount = np.clip( ( 0.55 + 0.35 * smoothstep( -1.0, 1.5, smear ) ) * edge * ( 0.85 + 0.15 * block ), 0, 1 )
    col = mix( lin( ( 70, 68, 64 ) ) * np.ones( ( n, n, 1 ), np.float32 ), lin( ( 22, 22, 22 ) ), amount )
    rough = 0.42 - 0.12 * amount
    return col.astype( np.float32 ), rough.astype( np.float32 ), ( 0.01 * amount * block ).astype( np.float32 ), n / 48.0


def flags():
    """ The hall's footway: 24 in precast concrete flags (four by four to a tile), each its own shade, with sanded
    joints, chipped corners and a damp sheen. """
    rng = np.random.default_rng( 7114 )
    nz, x, z, ppi = RM.field( rng, 2048, 96.0 )
    flag = 24.0
    i, j = ( x // flag ).astype( int ) % 4, ( z // flag ).astype( int ) % 4
    tone = rng.normal( 0, 0.05, ( 4, 4 ) ).astype( np.float32 )[i, j]
    tilt = rng.normal( 0, 0.03, ( 4, 4, 2 ) ).astype( np.float32 )
    col = lin( ( 146, 143, 136 ) ) * ( 1.0 + tone + 0.05 * nz( 2.2, 20, 2 ) + 0.05 * nz( 0.6, 0.5, 0.08 ) )[..., None]
    fx, fz = x % flag, z % flag
    joint = np.minimum( np.minimum( fx, flag - fx ), np.minimum( fz, flag - fz ) )
    groove = smoothstep( 0.24, 0.1, joint )
    corner = smoothstep( 2.0, 0.6, np.maximum( np.minimum( fx, flag - fx ), np.minimum( fz, flag - fz ) ) )
    chip = corner * smoothstep( -0.2, 0.8, nz( 1.4, 3, 0.2 ) )
    col = mix( col, lin( ( 34, 33, 31 ) ), groove * 0.9 )
    col = mix( col, col * 0.7, chip )
    damp = 0.62 + 0.08 * nz( 2.4, 60, 6 )
    col = col * damp[..., None]
    rough = np.clip( 0.4 + 0.1 * nz( 2.0, 10, 1 ) - 0.12 * smoothstep( 1.0, 2.0, nz( 2.4, 40, 4 ) ), 0.12, 0.9 )
    height = -0.2 * groove - 0.15 * chip + tilt[i, j, 0] * ( fx - flag / 2 ) / flag + tilt[i, j, 1] * ( fz - flag / 2 ) / flag \
        + 0.01 * nz( 0.6, 0.5, 0.08 )
    return np.clip( col, 0, 1 ).astype( np.float32 ), rough.astype( np.float32 ), height.astype( np.float32 ), ppi


def pallet_wood():
    """ Weathered, wet pine boards: grey-brown with the grain along v (the props' paint runs a board's length that way),
    knots, nail heads and darker end grain. """
    rng = np.random.default_rng( 7115 )
    nz, x, z, ppi = RM.field( rng, 1024, 48.0 )
    n = x.shape[0]
    grain = ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 28.0, 0.9 ), mode="wrap" )
    grain /= grain.std() + 1e-6
    base = mix( lin( ( 126, 110, 88 ) ), lin( ( 112, 108, 100 ) ), 0.35 * smoothstep( -0.8, 1.0, nz( 2.2, 10, 3 ) ) )
    col = base * ( 1.0 + 0.12 * grain + 0.06 * nz( 2.0, 8, 2 ) + 0.03 * nz( 0.8, 0.6, 0.1 ) )[..., None]
    knots = np.zeros( ( n, n ), np.float32 )
    for _ in range( 10 ):
        cx, cz = rng.uniform( 0, 48 ), rng.uniform( 0, 48 )
        dx = np.minimum( np.abs( x - cx ), 48 - np.abs( x - cx ) )
        dz = np.minimum( np.abs( z - cz ), 48 - np.abs( z - cz ) )
        knots = np.maximum( knots, smoothstep( 0.9, 0.3, np.sqrt( ( dx / 0.7 ) ** 2 + ( dz / 1.4 ) ** 2 ) ) )
    col = mix( col, lin( ( 60, 44, 30 ) ), knots * 0.8 )
    col = col * 0.72
    rough = 0.68 + 0.1 * nz( 2.0, 8, 1 )
    height = 0.02 * grain - 0.03 * knots
    return np.clip( col, 0, 1 ).astype( np.float32 ), rough.astype( np.float32 ), height.astype( np.float32 ), ppi


def drum_paint( seed, colour ):
    def draw():
        return RM.painted( seed, colour, chips=0.55, tile=48.0, rough=0.4, grime=0.65, bare=( 70, 62, 54 ) )
    return draw


# The cast atlas: four 512 px quadrants of cast iron (x, y, w, h in pixels).
CAST = { "round": ( 0, 0, 512, 512 ), "square": ( 512, 0, 512, 512 ), "gully": ( 0, 512, 512, 512 ),
         "trench": ( 512, 512, 512, 512 ) }


def _font( px ):
    return ImageFont.truetype( str( FONT ), max( 6, int( px ) ) )


def cast_atlas():
    """ Cast iron in four quadrants, each a whole piece (mapped by explicit UVs): a round manhole cover with a raised
    chequer, Riverdale Nuclear's name round its rim and two lifting keyholes; a square double-sealed cover in diamond
    plate; a gully grate's bars; a slotted trench grate. Worn bright on the high points, rust and silt in the low, the
    holes black. """
    W, H = CAST_ATLAS
    relief = Image.new( "L", ( W, H ), 0 )          # 0 the frame's level ... 255 raised
    holes = Image.new( "L", ( W, H ), 0 )
    d, dh = ImageDraw.Draw( relief ), ImageDraw.Draw( holes )
    # Round cover.
    cx, cy, R = 256, 256, 250
    d.ellipse( ( cx - R, cy - R, cx + R, cy + R ), fill=120 )
    dh.ellipse( ( cx - R, cy - R, cx + R, cy + R ), outline=255, width=3 )
    for gy in range( cy - 168, cy + 169, 24 ):
        for gx in range( cx - 168, cx + 169, 24 ):
            if ( gx - cx ) ** 2 + ( gy - cy ) ** 2 < 165 ** 2:
                d.rectangle( ( gx - 8, gy - 8, gx + 8, gy + 8 ), fill=230 )
    d.ellipse( ( cx - 236, cy - 236, cx + 236, cy + 236 ), outline=200, width=6 )
    d.ellipse( ( cx - 182, cy - 182, cx + 182, cy + 182 ), outline=200, width=5 )
    text = "RIVERDALE NUCLEAR • SURFACE WATER • "
    font = _font( 30 )
    step = 360.0 / len( text )
    for k, ch in enumerate( text ):
        tile = Image.new( "L", ( 40, 40 ), 0 )
        ImageDraw.Draw( tile ).text( ( 20, 20 ), ch, font=font, fill=230, anchor="mm" )
        a = -90.0 + k * step
        tile = tile.rotate( -a - 90.0, resample=Image.BICUBIC )
        px = cx + 209 * math.cos( math.radians( a ) ) - 20
        py = cy + 209 * math.sin( math.radians( a ) ) - 20
        relief.paste( 230, ( int( px ), int( py ) ), tile )
    for sgn in ( -1, 1 ):
        dh.rectangle( ( cx + sgn * 120 - 18, cy - 6, cx + sgn * 120 + 18, cy + 6 ), fill=255 )
    d.polygon( [ ( cx, cy - 46 ), ( cx + 44, cy + 32 ), ( cx - 44, cy + 32 ) ], fill=240 )
    # Square cover: two leaves in diamond plate, a border and keyholes.
    ox = 512
    d.rectangle( ( ox + 8, 8, ox + 503, 503 ), fill=130 )
    for leaf in ( ( ox + 22, 22, ox + 252, 489 ), ( ox + 259, 22, ox + 489, 489 ) ):
        d.rectangle( leaf, fill=150 )
        x0, y0, x1, y1 = leaf
        for k, gy in enumerate( range( y0 + 10, y1 - 6, 18 ) ):
            for gx in range( x0 + 10 + ( 9 if k % 2 else 0 ), x1 - 6, 18 ):
                if k % 2 == ( ( gx - x0 ) // 18 ) % 2:
                    d.line( ( gx - 5, gy - 5, gx + 5, gy + 5 ), fill=235, width=4 )
                else:
                    d.line( ( gx - 5, gy + 5, gx + 5, gy - 5 ), fill=235, width=4 )
        dh.rectangle( ( ( x0 + x1 ) // 2 - 14, y0 + 30, ( x0 + x1 ) // 2 + 14, y0 + 40 ), fill=255 )
        dh.rectangle( ( ( x0 + x1 ) // 2 - 14, y1 - 40, ( x0 + x1 ) // 2 + 14, y1 - 30 ), fill=255 )
    dh.line( ( ox + 255, 22, ox + 255, 489 ), fill=255, width=4 )
    # Gully grate: a frame and bars.
    oy = 512
    d.rectangle( ( 10, oy + 10, 501, oy + 501 ), fill=150 )
    for k in range( 9 ):
        x0 = 44 + k * 48
        dh.rectangle( ( x0, oy + 52, x0 + 26, oy + 460 ), fill=255 )
    d.rectangle( ( 30, oy + 246, 481, oy + 266 ), fill=210 )
    dh.rectangle( ( 30, oy + 246, 481, oy + 266 ), fill=0 )
    # Trench grate: its length up the picture, slots across it.
    for k in range( 16 ):
        y0 = oy + 18 + k * 30
        dh.rounded_rectangle( ( ox + 96, y0, ox + 416, y0 + 14 ), radius=7, fill=255 )
    d.rectangle( ( ox + 4, oy + 4, ox + 507, oy + 507 ), outline=200, width=10 )
    rel = ndimage.gaussian_filter( np.asarray( relief, np.float32 ) / 255.0, 1.2 )
    hole = ndimage.gaussian_filter( np.asarray( holes, np.float32 ) / 255.0, 0.8 )
    rng = np.random.default_rng( 7116 )
    ppi = W / 30.0
    grit = BM.noise( rng, ( H, W ), ( ppi, ppi ), 1.6, 3, 0.1 )
    blot = BM.noise( rng, ( H, W ), ( ppi, ppi ), 2.2, 12, 0.5 )
    iron = lin( ( 54, 52, 49 ) ) * ( 1.0 + 0.08 * grit + 0.06 * blot )[..., None]
    worn = smoothstep( 0.55, 0.85, rel ) * smoothstep( -0.8, 0.6, blot )
    low = smoothstep( 0.45, 0.2, rel )
    col = mix( iron, lin( ( 96, 94, 90 ) ), worn * 0.7 )
    col = mix( col, lin( ( 74, 52, 36 ) ) * 0.8, low * smoothstep( -0.3, 1.2, grit ) * 0.6 )
    col = mix( col, lin( ( 6, 6, 6 ) ), hole )
    rough = np.clip( 0.42 - 0.18 * worn + 0.2 * low * 0.5 + 0.45 * hole, 0.12, 1.0 )
    height = 0.14 * rel - 0.4 * hole + 0.004 * grit
    return np.clip( col, 0, 1 ).astype( np.float32 ), rough.astype( np.float32 ), height.astype( np.float32 ), ppi


# The signs atlas: name -> ( x, y, w, h ) in pixels.
SIGNS = {
    "speed10": ( 0, 0, 512, 512 ), "pedestrians": ( 512, 0, 512, 640 ), "forklift": ( 1024, 0, 512, 640 ),
    "no_smoking": ( 1536, 0, 512, 640 ), "ppe": ( 0, 640, 768, 512 ), "assembly": ( 768, 640, 768, 512 ),
    "high_voltage": ( 1536, 640, 512, 640 ), "eyewash": ( 0, 1152, 512, 512 ), "spill_kit": ( 512, 1280, 768, 256 ),
    "sand": ( 1280, 1280, 512, 256 ), "hose_reel": ( 1792, 1280, 256, 256 ), "ghs_flame": ( 512, 1536, 256, 256 ),
    "ghs_warn": ( 768, 1536, 256, 256 ), "ibc_label": ( 1024, 1536, 512, 256 ), "hydrant": ( 1536, 1536, 256, 256 ),
    "fire_route": ( 0, 1664, 1024, 384 ), "drum_label": ( 1024, 1792, 512, 256 ),
}


def _text( d, box, lines, fill, align="center", track=0.04, pad=0.08 ):
    RM.text_block( d, box, lines, fill=fill, align=align, track=track, pad=pad )


def _person( d, cx, cy, h, fill, walking=True ):
    """ A standing or walking figure h tall, its middle at cx, cy. """
    u = h / 10.0
    d.ellipse( ( cx - 0.9 * u, cy - 5 * u, cx + 0.9 * u, cy - 3.2 * u ), fill=fill )
    d.polygon( [ ( cx - 0.9 * u, cy - 3.0 * u ), ( cx + 0.9 * u, cy - 3.0 * u ), ( cx + 0.8 * u, cy + 0.6 * u ),
                 ( cx - 0.8 * u, cy + 0.6 * u ) ], fill=fill )
    if walking:
        d.line( ( cx - 0.3 * u, cy + 0.4 * u, cx - 1.6 * u, cy + 5 * u ), fill=fill, width=int( 0.9 * u ) )
        d.line( ( cx + 0.3 * u, cy + 0.4 * u, cx + 1.8 * u, cy + 2.6 * u, cx + 1.4 * u, cy + 5 * u ), fill=fill, width=int( 0.9 * u ) )
        d.line( ( cx - 0.6 * u, cy - 2.6 * u, cx - 1.9 * u, cy - 0.4 * u ), fill=fill, width=int( 0.7 * u ) )
        d.line( ( cx + 0.6 * u, cy - 2.6 * u, cx + 1.9 * u, cy - 0.8 * u ), fill=fill, width=int( 0.7 * u ) )
    else:
        for sgn in ( -1, 1 ):
            d.line( ( cx + sgn * 0.4 * u, cy + 0.4 * u, cx + sgn * 0.6 * u, cy + 5 * u ), fill=fill, width=int( 0.9 * u ) )
            d.line( ( cx + sgn * 0.8 * u, cy - 2.6 * u, cx + sgn * 1.3 * u, cy + 0.2 * u ), fill=fill, width=int( 0.7 * u ) )


def _triangle_sign( d, x, y, w, h, fill_bg=( 236, 186, 26 ), border=( 18, 18, 18 ) ):
    """ An ISO warning triangle in the top of a box; returns its inner centre and size. """
    s = min( w * 0.9, h * 0.62 / 0.866 )
    cx, top = x + w / 2, y + h * 0.04
    base = top + s * 0.866
    d.polygon( [ ( cx, top ), ( cx + s / 2, base ), ( cx - s / 2, base ) ], fill=border )
    k = s * 0.13
    d.polygon( [ ( cx, top + k * 1.6 ), ( cx + s / 2 - k * 1.4, base - k * 0.8 ), ( cx - s / 2 + k * 1.4, base - k * 0.8 ) ], fill=fill_bg )
    return cx, top + s * 0.866 * 0.62, s


def signs_atlas():
    """ The yard's printed signs and labels, drawn as generic safety signs (no maker, operator brand or real logo but
    Riverdale Nuclear's own), weathered a little. """
    W, H = SIGN_ATLAS
    img = Image.new( "RGB", ( W, H ), ( 60, 60, 60 ) )
    d = ImageDraw.Draw( img )
    white, black, red, yellow = ( 236, 236, 230 ), ( 18, 18, 18 ), ( 196, 28, 24 ), ( 236, 186, 26 )
    blue, green = ( 24, 84, 168 ), ( 18, 128, 70 )

    def box( name ):
        return SIGNS[name]

    # Speed limit: a red ring round 10.
    x, y, w, h = box( "speed10" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 70, 72, 74 ) )
    d.ellipse( ( x + 8, y + 8, x + w - 8, y + h - 8 ), fill=red )
    d.ellipse( ( x + 70, y + 70, x + w - 70, y + h - 70 ), fill=white )
    _text( d, ( x + 100, y + 120, w - 200, h - 240 ), [ "10" ], black, track=0.0, pad=0.02 )
    # Warning triangles with a text panel under them.
    for name, words in ( ( "pedestrians", [ "PEDESTRIAN", "CROSSING" ] ), ( "forklift", [ "FORK LIFT", "TRUCKS OPERATING" ] ),
                         ( "high_voltage", [ "DANGER", "HIGH VOLTAGE" ] ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=white )
        cx, cy, s = _triangle_sign( d, x, y, w, h )
        if name == "pedestrians":
            _person( d, cx, cy + s * 0.04, s * 0.42, black )
        elif name == "forklift":
            u = s * 0.05
            d.rectangle( ( cx - 4 * u, cy - 1 * u, cx + 2 * u, cy + 3 * u ), fill=black )
            d.rectangle( ( cx + 3 * u, cy - 6 * u, cx + 4 * u, cy + 3.5 * u ), fill=black )
            d.rectangle( ( cx + 4 * u, cy + 3 * u, cx + 7.5 * u, cy + 3.8 * u ), fill=black )
            d.line( ( cx - 3 * u, cy - 1 * u, cx - 3 * u, cy - 5 * u, cx + 2 * u, cy - 5 * u ), fill=black, width=int( 0.8 * u ) )
            for wx in ( cx - 2.5 * u, cx + 1.5 * u ):
                d.ellipse( ( wx - 1.4 * u, cy + 2.6 * u, wx + 1.4 * u, cy + 5.4 * u ), fill=black )
            d.ellipse( ( cx - 1.8 * u, cy - 4.3 * u, cx - 0.2 * u, cy - 2.7 * u ), fill=black )
        else:
            u = s * 0.05
            d.polygon( [ ( cx + 1 * u, cy - 6 * u ), ( cx - 2.6 * u, cy + 0.6 * u ), ( cx + 0.2 * u, cy + 0.6 * u ),
                         ( cx - 1.2 * u, cy + 6 * u ), ( cx + 2.8 * u, cy - 1.2 * u ), ( cx, cy - 1.2 * u ), ( cx + 2 * u, cy - 6 * u ) ], fill=black )
        panel = ( x + w * 0.04, y + h * 0.66, w * 0.92, h * 0.3 )
        d.rectangle( ( panel[0], panel[1], panel[0] + panel[2], panel[1] + panel[3] ), fill=yellow if name != "high_voltage" else white )
        _text( d, panel, words, black )
    # No smoking: a red slashed ring over a cigarette.
    x, y, w, h = box( "no_smoking" )
    d.rectangle( ( x, y, x + w, y + h ), fill=white )
    cx, cy, r = x + w / 2, y + h * 0.36, w * 0.38
    d.rectangle( ( cx - r * 0.7, cy - r * 0.08, cx + r * 0.5, cy + r * 0.1 ), fill=black )
    d.rectangle( ( cx + r * 0.52, cy - r * 0.08, cx + r * 0.68, cy + r * 0.1 ), fill=black )
    d.ellipse( ( cx - r, cy - r, cx + r, cy + r ), outline=red, width=int( r * 0.16 ) )
    d.line( ( cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7 ), fill=red, width=int( r * 0.16 ) )
    _text( d, ( x + w * 0.04, y + h * 0.72, w * 0.92, h * 0.24 ), [ "NO SMOKING", "NO NAKED FLAMES" ], black )
    # Personal protective equipment: three blue mandatory circles.
    x, y, w, h = box( "ppe" )
    d.rectangle( ( x, y, x + w, y + h ), fill=white )
    for k in range( 3 ):
        cx, cy, r = x + w * ( 0.2 + 0.3 * k ), y + h * 0.32, h * 0.22
        d.ellipse( ( cx - r, cy - r, cx + r, cy + r ), fill=blue )
        u = r * 0.12
        if k == 0:
            d.pieslice( ( cx - 5 * u, cy - 4 * u, cx + 5 * u, cy + 5 * u ), 180, 360, fill=white )
            d.rectangle( ( cx - 6.5 * u, cy + 0.6 * u, cx + 6.5 * u, cy + 1.8 * u ), fill=white )
        elif k == 1:
            d.polygon( [ ( cx - 4 * u, cy - 5 * u ), ( cx - 1.5 * u, cy - 5 * u ), ( cx, cy - 2 * u ), ( cx + 1.5 * u, cy - 5 * u ),
                         ( cx + 4 * u, cy - 5 * u ), ( cx + 4 * u, cy + 5 * u ), ( cx - 4 * u, cy + 5 * u ) ], fill=white )
            d.rectangle( ( cx - 4 * u, cy + 1 * u, cx + 4 * u, cy + 2 * u ), fill=blue )
        else:
            d.polygon( [ ( cx - 2 * u, cy - 5 * u ), ( cx + 1 * u, cy - 5 * u ), ( cx + 1 * u, cy + 1 * u ), ( cx + 5 * u, cy + 2 * u ),
                         ( cx + 5 * u, cy + 4.5 * u ), ( cx - 2 * u, cy + 4.5 * u ) ], fill=white )
    _text( d, ( x + w * 0.04, y + h * 0.6, w * 0.92, h * 0.36 ), [ "SAFETY HELMETS, HI-VIS AND", "SAFETY BOOTS MUST BE WORN" ], blue )
    # Assembly point: four arrows into a group, on green.
    x, y, w, h = box( "assembly" )
    d.rectangle( ( x, y, x + w, y + h ), fill=green )
    cx, cy, s = x + w * 0.25, y + h * 0.5, h * 0.36
    d.rectangle( ( cx - s, cy - s, cx + s, cy + s ), outline=white, width=int( s * 0.06 ) )
    for k in range( 3 ):
        _person( d, cx + ( k - 1 ) * s * 0.3, cy + s * 0.08, s * 0.55, white, walking=False )
    for ax, ay in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ):
        tip = ( cx + ax * s * 0.62, cy + ay * s * 0.62 )
        tail = ( cx + ax * s * 0.92, cy + ay * s * 0.92 )
        d.line( ( *tail, *tip ), fill=white, width=int( s * 0.08 ) )
        d.polygon( [ tip, ( tip[0] + ax * s * 0.16, tip[1] ), ( tip[0], tip[1] + ay * s * 0.16 ) ], fill=white )
    _text( d, ( x + w * 0.48, y + h * 0.18, w * 0.5, h * 0.64 ), [ "FIRE", "ASSEMBLY", "POINT", "B" ], white, align="left" )
    # Emergency shower and eyewash.
    x, y, w, h = box( "eyewash" )
    d.rectangle( ( x, y, x + w, y + h ), fill=green )
    cx, cy = x + w / 2, y + h * 0.36
    d.ellipse( ( cx - 60, cy - 70, cx + 60, cy + 50 ), fill=white )
    d.ellipse( ( cx - 35, cy - 30, cx - 10, cy - 15 ), fill=green )
    d.ellipse( ( cx + 10, cy - 30, cx + 35, cy - 15 ), fill=green )
    for k in range( 3 ):
        d.arc( ( cx - 120 + k * 10, cy - 150 + k * 20, cx + 120 - k * 10, cy + 90 - k * 20 ), 200, 340, fill=white, width=10 )
    _text( d, ( x + w * 0.04, y + h * 0.66, w * 0.92, h * 0.3 ), [ "EMERGENCY SHOWER", "AND EYE WASH" ], white )
    # Labels: the spill kit, the sand bin, the hose reel, the hydrant.
    for name, words, bg, fg in ( ( "spill_kit", [ "SPILL KIT" ], white, black ), ( "sand", [ "SAND" ], yellow, black ),
                                 ( "hose_reel", [ "HOSE", "REEL" ], red, white ), ( "hydrant", [ "FIRE", "HYDRANT" ], red, white ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=bg )
        d.rectangle( ( x + 6, y + 6, x + w - 6, y + h - 6 ), outline=fg, width=4 )
        _text( d, ( x, y, w, h ), words, fg, pad=0.14 )
    # Hazard diamonds for drums and the tote.
    for name, kind in ( ( "ghs_flame", "flame" ), ( "ghs_warn", "warn" ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=white )
        cx, cy, r = x + w / 2, y + h / 2, w * 0.46
        d.polygon( [ ( cx, cy - r ), ( cx + r, cy ), ( cx, cy + r ), ( cx - r, cy ) ], fill=red )
        r2 = r * 0.84
        d.polygon( [ ( cx, cy - r2 ), ( cx + r2, cy ), ( cx, cy + r2 ), ( cx - r2, cy ) ], fill=white )
        if kind == "flame":
            d.polygon( [ ( cx - 30, cy + 40 ), ( cx - 36, cy ), ( cx - 12, cy - 30 ), ( cx - 4, cy - 64 ), ( cx + 16, cy - 20 ),
                         ( cx + 32, cy - 38 ), ( cx + 36, cy + 10 ), ( cx + 28, cy + 40 ) ], fill=black )
            d.rectangle( ( cx - 40, cy + 44, cx + 40, cy + 52 ), fill=black )
        else:
            d.rectangle( ( cx - 9, cy - 56, cx + 9, cy + 18 ), fill=black )
            d.rectangle( ( cx - 9, cy + 30, cx + 9, cy + 48 ), fill=black )
    for name, lines in ( ( "ibc_label", [ "BORIC ACID SOLUTION", "4% W/W  -  1000 L", "UN 3264  CORROSIVE" ] ),
                         ( "drum_label", [ "LUBRICATING OIL", "205 L", "RN STORES 4471" ] ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=white )
        d.rectangle( ( x, y, x + w, y + h * 0.22 ), fill=( 30, 60, 120 ) )
        _text( d, ( x, y + h * 0.26, w, h * 0.7 ), lines, black, align="left" )
    # Fire route: a red board with white lettering.
    x, y, w, h = box( "fire_route" )
    d.rectangle( ( x, y, x + w, y + h ), fill=red )
    d.rectangle( ( x + 10, y + 10, x + w - 10, y + h - 10 ), outline=white, width=6 )
    _text( d, ( x, y, w, h ), [ "FIRE ACCESS ROUTE", "KEEP CLEAR AT ALL TIMES" ], white, pad=0.1 )
    c = np.asarray( img, np.float32 )
    rng = np.random.default_rng( 7117 )
    ppi = W / 48.0
    dirt = smoothstep( 0.2, 2.4, BM.noise( rng, ( H, W ), ( ppi, ppi ), 2.2, 10, 0.2 ) )
    streak = smoothstep( 0.6, 2.0, BM.noise( rng, ( H, W ), ( ppi * 6, ppi * 0.4 ), 2.0, 12, 0.3 ) )
    c = c * ( 1.0 - 0.16 * dirt[..., None] - 0.1 * streak[..., None] )
    colour = RM.T.srgb_to_linear( c ).astype( np.float32 )
    rough = 0.36 + 0.24 * dirt
    return colour, rough.astype( np.float32 ), np.zeros( ( H, W ), np.float32 ), ppi


# Flat paints: colour (sRGB), metalness, roughness, glow.
EXTRA_PAINTS = {
    "rv_yd_cone": ( ( 226, 86, 22 ), 0.0, 0.5, 0 ),
    "rv_yd_reflective": ( ( 232, 232, 228 ), 0.0, 0.26, 0 ),
    "rv_yd_bin": ( ( 220, 172, 28 ), 0.0, 0.55, 0 ),
    "rv_yd_ibc": ( ( 222, 220, 206 ), 0.0, 0.42, 0 ),
    "rv_yd_red": ( ( 160, 28, 22 ), 0.2, 0.42, 0 ),
    "rv_yd_hose": ( ( 120, 26, 22 ), 0.0, 0.55, 0 ),
}

# Textured surfaces: ( tile inches, metalness, draw ).
EXTRA_SURFACES = {
    "rv_yd_wet": ( YARD_TILE, 0.0, wet_yard ),
    "rv_yd_puddle": ( YARD_TILE, 0.0, puddle_water ),
    "rv_yd_stain": ( YARD_TILE, 0.0, stained_yard ),
    "rv_yd_paint_yellow": ( YARD_TILE, 0.0, worn_paint( ( 200, 156, 40 ), 7121 ) ),
    "rv_yd_paint_white": ( YARD_TILE, 0.0, worn_paint( ( 200, 200, 192 ), 7122 ) ),
    "rv_yd_paint_black": ( YARD_TILE, 0.0, worn_paint( ( 28, 28, 28 ), 7123, coverage=0.9 ) ),
    "rv_yd_paint_green": ( YARD_TILE, 0.0, worn_paint( ( 36, 122, 68 ), 7124 ) ),
    "rv_yd_oil": ( 48.0, 0.0, oil ),
    "rv_yd_rust": ( 48.0, 0.0, rust_stain ),
    "rv_yd_tyre": ( 48.0, 0.0, tyre ),
    "rv_yd_flags": ( 96.0, 0.0, flags ),
    "rv_yd_cast": ( 48.0, 0.35, cast_atlas ),
    "rv_yd_pallet": ( 48.0, 0.0, pallet_wood ),
    "rv_yd_drum_blue": ( 48.0, 0.0, drum_paint( 7131, ( 32, 70, 138 ) ) ),
    "rv_yd_drum_red": ( 48.0, 0.0, drum_paint( 7132, ( 150, 46, 30 ) ) ),
    "rv_yd_drum_grey": ( 48.0, 0.0, drum_paint( 7133, ( 92, 96, 100 ) ) ),
    "rv_yd_drum_green": ( 48.0, 0.0, drum_paint( 7134, ( 58, 84, 56 ) ) ),
    "rv_yd_signs": ( 48.0, 0.0, signs_atlas ),
}
ALIGNED = { "rv_yd_wet", "rv_yd_puddle", "rv_yd_stain", "rv_yd_paint_yellow", "rv_yd_paint_white", "rv_yd_paint_black", "rv_yd_paint_green" }


# ---------------------------------------------------------------------------------------------------------------------
# Footprints, for --check: ( category, name, ( e0, e1, n0, n1 ), top )

NOTES = []


def note( category, name, pts, top=0.0 ):
    pts = np.asarray( [ np.asarray( p, float )[:2] for p in pts ] )
    NOTES.append( ( category, name, ( float( pts[:, 0].min() ), float( pts[:, 0].max() ), float( pts[:, 1].min() ),
                                      float( pts[:, 1].max() ) ), float( top ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Plan geometry

def unit2( d ):
    d = np.asarray( d, float )[:2]
    return d / np.linalg.norm( d )


def left( d ):
    """ d turned a quarter counter-clockwise (seen from above). """
    return np.array( ( -d[1], d[0] ) )


def signed_area( pts ):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float( np.dot( x, np.roll( y, -1 ) ) - np.dot( y, np.roll( x, -1 ) ) )


def seed_of( *key ):
    return zlib.crc32( "/".join( str( k ) for k in key ).encode() )


def triangulate( pts ):
    """ Ear clipping of a simple polygon (counter-clockwise): index triples, counter-clockwise. """
    n = len( pts )
    if n < 3:
        return []
    idx = list( range( n ) )
    out = []
    i = stall = 0
    while len( idx ) > 3:
        m = len( idx )
        if stall > m:
            out += [ ( idx[0], idx[k], idx[k + 1] ) for k in range( 1, m - 1 ) ]
            return out
        a, b, c = idx[( i - 1 ) % m], idx[i % m], idx[( i + 1 ) % m]
        pa, pb, pc = pts[a], pts[b], pts[c]
        ear = ( pb[0] - pa[0] ) * ( pc[1] - pa[1] ) - ( pb[1] - pa[1] ) * ( pc[0] - pa[0] ) > 1e-9
        if ear:
            rest = np.array( [ j for j in idx if j not in ( a, b, c ) ], int )
            if len( rest ):
                q = pts[rest]

                def side( p0, p1 ):
                    return ( p1[0] - p0[0] ) * ( q[:, 1] - p0[1] ) - ( p1[1] - p0[1] ) * ( q[:, 0] - p0[0] )
                inside = ( side( pa, pb ) > -1e-9 ) & ( side( pb, pc ) > -1e-9 ) & ( side( pc, pa ) > -1e-9 )
                ear = not inside.any()
        if ear:
            out.append( ( a, b, c ) )
            del idx[i % m]
            stall = 0
        else:
            i += 1
            stall += 1
    out.append( tuple( idx ) )
    return out


def clip_rect( poly, e0, e1, n0, n1 ):
    """ A convex polygon clipped to an upright rectangle (Sutherland-Hodgman). """
    pts = [ np.asarray( p, float ) for p in poly ]
    for axis, value, keep in ( ( 0, e0, 1 ), ( 0, e1, -1 ), ( 1, n0, 1 ), ( 1, n1, -1 ) ):
        out = []
        for k in range( len( pts ) ):
            a, b = pts[k], pts[( k + 1 ) % len( pts )]
            ina, inb = ( a[axis] - value ) * keep >= 0, ( b[axis] - value ) * keep >= 0
            if ina:
                out.append( a )
            if ina != inb:
                t = ( value - a[axis] ) / ( b[axis] - a[axis] )
                out.append( a + ( b - a ) * t )
        pts = out
        if not pts:
            return []
    return pts


class GroundUV:
    """ The UVs the compiled ground shows at a plan point: map_kit's world UVs at the corners of riverdale_map.ground()'s
    rv_yard faces (written to 5 decimals, then rounded to half floats by ModelDoc), interpolated across the triangles
    map_kit fans them into. Off the ground's faces, the unrounded world UVs. """

    def __init__( self ):
        import riverdale_map as RD
        self.tile = RM.TILES.get( "rv_yard", 768.0 )
        self.offset = K.uv_offset( "riverdale_ground" )
        self.tris = []
        for points, normal in RD.ground().polygons.get( "rv_yard", [] ):
            if normal[2] < 0.99:
                continue
            wn = K.to_world( normal )
            uv = np.array( [ K.face_uv( K.to_world( p ), wn, "rv_yard", self.offset, self.tile ) for p in points ] )
            uv = np.round( uv, 5 ).astype( np.float16 ).astype( float )
            pts = np.asarray( points, float )[:, :2]
            for k in range( 1, len( points ) - 1 ):
                self.tris.append( ( pts[[ 0, k, k + 1 ]], uv[[ 0, k, k + 1 ]] ) )

    def __call__( self, pts ):
        pts = np.asarray( pts, float )[:, :2]
        out = np.full( ( len( pts ), 2 ), np.nan )
        for tri, uv in self.tris:
            a, b, c = tri
            v0, v1, rel = b - a, c - a, pts - a
            det = v0[0] * v1[1] - v0[1] * v1[0]
            l1 = ( rel[:, 0] * v1[1] - rel[:, 1] * v1[0] ) / det
            l2 = ( v0[0] * rel[:, 1] - v0[1] * rel[:, 0] ) / det
            l0 = 1.0 - l1 - l2
            hit = ( l0 > -1e-7 ) & ( l1 > -1e-7 ) & ( l2 > -1e-7 ) & np.isnan( out[:, 0] )
            out[hit] = l0[hit, None] * uv[0] + l1[hit, None] * uv[1] + l2[hit, None] * uv[2]
        miss = np.isnan( out[:, 0] )
        if miss.any():
            out[miss] = np.column_stack( ( pts[miss, 0] / self.tile + self.offset[0], pts[miss, 1] / self.tile + self.offset[1] ) )
        return out


_GROUND_UV = []


def ground_uv( pts ):
    if not _GROUND_UV:
        _GROUND_UV.append( GroundUV() )
    return _GROUND_UV[0]( pts )


def flat( m, paint, pts, z, uv=None ):
    """ A level polygon at height z over plan points (either winding; drawn counter-clockwise from above), triangulated.
    An ALIGNED paint's UVs are the ground's at each point; else uv as given, or the paint's world UVs. Every polygon's
    UVs are moved by whole tiles towards 0, where half floats are finest. """
    pts = np.asarray( [ np.asarray( p, float )[:2] for p in pts ] )
    if len( pts ) < 3 or abs( signed_area( pts ) ) < 1e-3:
        return
    if uv is not None:
        uv = np.asarray( uv, float )
    if signed_area( pts ) < 0:
        pts = pts[::-1]
        uv = uv[::-1] if uv is not None else None
    if paint in ALIGNED:
        uv = ground_uv( pts )
    elif uv is None:
        uv = pts / RM.TILES.get( paint, 64.0 )
    uv = uv - np.floor( uv.mean( axis=0 ) + 0.5 )
    tris = [ ( 0, k, k + 1 ) for k in range( 1, len( pts ) - 1 ) ] if len( pts ) <= 4 else triangulate( pts )
    for a, b, c in tris:
        m.polygon( paint, [ ( *pts[a], z ), ( *pts[b], z ), ( *pts[c], z ) ], normal=UP,
                   uv=[ tuple( uv[a] ), tuple( uv[b] ), tuple( uv[c] ) ] )


def rect_pts( centre, along, length, width ):
    a = unit2( along )
    s = left( a )
    c = np.asarray( centre, float )[:2]
    return [ c - a * length / 2 - s * width / 2, c + a * length / 2 - s * width / 2, c + a * length / 2 + s * width / 2,
             c - a * length / 2 + s * width / 2 ]


def strip( m, paint, a, b, width, z=Z_PAINT, piece=192.0 ):
    """ A straight band from a to b, width across, in pieces no longer than piece. """
    a, b = np.asarray( a, float )[:2], np.asarray( b, float )[:2]
    L = float( np.linalg.norm( b - a ) )
    count = max( 1, int( math.ceil( L / piece ) ) )
    d = ( b - a ) / L
    for k in range( count ):
        p0, p1 = a + d * L * k / count, a + d * L * ( k + 1 ) / count
        flat( m, paint, rect_pts( ( p0 + p1 ) / 2, d, L / count, width ), z )


def band( m, paint, e0, e1, n0, n1, z=Z_PAINT ):
    """ An upright rectangle of paint, split along its length. """
    if e1 - e0 >= n1 - n0:
        strip( m, paint, ( e0, ( n0 + n1 ) / 2 ), ( e1, ( n0 + n1 ) / 2 ), n1 - n0, z )
    else:
        strip( m, paint, ( ( e0 + e1 ) / 2, n0 ), ( ( e0 + e1 ) / 2, n1 ), e1 - e0, z )


# ---------------------------------------------------------------------------------------------------------------------
# Organic outlines: puddles, stains, rust runs

def blob_outlines( seed, centre, along, length, width, levels, lobes=3, rough=0.3, grid=1.5, min_area=10.0, keep=5 ):
    """ Outlines round a centre, as water or a stain spreads: a few soft lobes along `along` (length by width) summed,
    roughened by noise near them, cut at each level (higher is smaller, 0.5 near the length and width). Returns
    { level: [ plan polygons ( n, 2 ), counter-clockwise ] }, the largest first; dry islands are filled. """
    from skimage import measure
    rng = np.random.default_rng( seed )
    a = unit2( along )
    s = left( a )
    c = np.asarray( centre, float )[:2]
    span = max( length - width, 0.0 )
    mx, my = length / 2 + width, width / 2 + width
    xs = np.arange( -mx, mx + grid, grid )
    ys = np.arange( -my, my + grid, grid )
    X, Y = np.meshgrid( xs, ys )
    f = np.zeros_like( X )
    for k in range( lobes ):
        cx = ( -0.5 + ( k + 0.5 ) / lobes ) * span + rng.normal( 0, span * 0.06 + 0.5 )
        cy = rng.normal( 0, width * 0.1 )
        sx = 0.6 * ( span / lobes * 0.85 + width * 0.55 ) * rng.uniform( 0.85, 1.15 )
        sy = 0.6 * width * rng.uniform( 0.85, 1.1 )
        f += rng.uniform( 0.75, 1.0 ) * np.exp( -( ( X - cx ) / sx ) ** 2 - ( ( Y - cy ) / sy ) ** 2 )
    f /= max( f.max(), 1e-6 )
    n1 = ndimage.gaussian_filter( rng.standard_normal( X.shape ), max( 1.0, min( width * 0.18, 9.0 ) / grid ) )
    n2 = ndimage.gaussian_filter( rng.standard_normal( X.shape ), max( 0.8, 1.6 / grid ) )
    n1 /= n1.std() + 1e-9
    n2 /= n2.std() + 1e-9
    f = f + rough * ( 0.2 * n1 + 0.07 * n2 ) * smoothstep( 0.02, 0.35, f )
    f[[ 0, -1 ], :] = -1.0
    f[:, [ 0, -1 ]] = -1.0
    out = {}
    for level in levels:
        inside = f > level
        holes = ndimage.binary_fill_holes( inside ) & ~inside
        g = np.where( holes, level + 0.02, f )
        polys = []
        for contour in measure.find_contours( g, level ):
            if len( contour ) < 4 or np.abs( contour[0] - contour[-1] ).max() > 1e-6:
                continue
            local = np.column_stack( ( xs[0] + contour[:, 1] * grid, ys[0] + contour[:, 0] * grid ) )
            local = measure.approximate_polygon( local, tolerance=0.3 )[:-1]
            if len( local ) < 3:
                continue
            plan = c + local[:, :1] * a + local[:, 1:] * s
            area = signed_area( plan )
            if abs( area ) < min_area:
                continue
            if area < 0:
                plan = plan[::-1]
            polys.append( plan )
        polys.sort( key=lambda p: -abs( signed_area( p ) ) )
        out[level] = polys[:keep]
    return out


def puddle( m, name, centre, along, length, width, lobes=3, rough=0.3, z=0.0 ):
    """ Standing water: a glassy pool (rv_yd_puddle) in a wet rim (rv_yd_wet), both on the ground's own texture. """
    shapes = blob_outlines( seed_of( "puddle", name ), centre, along, length, width, ( 0.28, 0.5 ), lobes, rough )
    for poly in shapes[0.28]:
        flat( m, "rv_yd_wet", poly, z + Z_RIM )
    for poly in shapes[0.5]:
        flat( m, "rv_yd_puddle", poly, z + Z_WATER )
    if shapes[0.28]:
        note( "puddle", name, np.vstack( shapes[0.28] ) )


def wet_edge( m, name, a, b, out, depth=( 3.0, 14.0 ), step=8.0, piece=240.0 ):
    """ The damp band along a wall's foot, where rain runs off the wall and splashes: the wall's side straight (a hair
    off its face), the other wandering between depth[0] and depth[1] inches out. rv_yd_wet at the puddle rims' height,
    so where the two meet they're the same surface. """
    rng = np.random.default_rng( seed_of( "wet", name ) )
    a, b = np.asarray( a, float )[:2], np.asarray( b, float )[:2]
    o = unit2( out )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    count = max( 2, int( L / step ) + 1 )
    t = np.linspace( 0.0, L, count )
    knots = max( 3, int( L / 60.0 ) )
    wander = np.interp( t, np.linspace( 0, L, knots ), rng.uniform( 0, 1, knots ) )
    fine = np.interp( t, np.linspace( 0, L, max( 3, int( L / 14.0 ) ) ), rng.normal( 0, 0.12, max( 3, int( L / 14.0 ) ) ) )
    reach = depth[0] + ( depth[1] - depth[0] ) * np.clip( wander + fine, 0, 1 )
    reach[0] = reach[-1] = 0.5
    per = max( 2, int( piece / step ) )
    for k0 in range( 0, count - 1, per ):
        k1 = min( count - 1, k0 + per )
        wall = [ a + d * t[k] + o * 0.3 for k in range( k0, k1 + 1 ) ]
        edge = [ a + d * t[k] + o * ( 0.3 + reach[k] ) for k in range( k1, k0 - 1, -1 ) ]
        flat( m, "rv_yd_wet", wall + edge, Z_RIM )
    note( "wet", name, [ a, b, a + o * depth[1], b + o * depth[1] ] )


def oil_stain( m, name, centre, along, length, width, lobes=2, core=0.55 ):
    """ An oil stain: a dark core (rv_yd_oil) in a soaked halo (rv_yd_stain). """
    shapes = blob_outlines( seed_of( "oil", name ), centre, along, length, width, ( 0.22, core ), lobes, 0.45 )
    for poly in shapes[0.22]:
        flat( m, "rv_yd_stain", poly, Z_STAIN_HALO )
    for poly in shapes[core]:
        flat( m, "rv_yd_oil", poly, Z_STAIN_CORE )
    if shapes[0.22]:
        note( "stain", name, np.vstack( shapes[0.22] ) )


def rust_run( m, name, start, direction, length, width ):
    """ Rust washed out from a steel foot: a streak from start along direction, orange-brown in a darkened halo. """
    d = unit2( direction )
    centre = np.asarray( start, float )[:2] + d * ( length * 0.4 )
    shapes = blob_outlines( seed_of( "rust", name ), centre, d, length, width, ( 0.25, 0.5 ), 3, 0.5, grid=1.0 )
    for poly in shapes[0.25]:
        flat( m, "rv_yd_stain", poly, Z_STAIN_HALO )
    for poly in shapes[0.5]:
        flat( m, "rv_yd_rust", poly, Z_STAIN_CORE )
    if shapes[0.25]:
        note( "stain", name, np.vstack( shapes[0.25] ) )


def rust_ring( m, name, centre, r ):
    """ A rust stain round a column's or a post's foot, longer on one side. """
    rng = np.random.default_rng( seed_of( "ring", name ) )
    a = rng.uniform( 0, 2 * math.pi )
    d = np.array( ( math.cos( a ), math.sin( a ) ) )
    rust_run( m, name, np.asarray( centre, float )[:2] - d * r * 0.6, d, r * rng.uniform( 2.4, 3.6 ), r * rng.uniform( 1.6, 2.2 ) )


def _spline( points, step=10.0 ):
    """ A Catmull-Rom curve through points, sampled about every step inches. """
    p = [ np.asarray( q, float )[:2] for q in points ]
    p = [ p[0] * 2 - p[1] ] + p + [ p[-1] * 2 - p[-2] ]
    out = []
    for k in range( 1, len( p ) - 2 ):
        p0, p1, p2, p3 = p[k - 1], p[k], p[k + 1], p[k + 2]
        count = max( 2, int( np.linalg.norm( p2 - p1 ) / step ) )
        for i in range( count ):
            t = i / count
            out.append( 0.5 * ( 2 * p1 + ( -p0 + p2 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                                + ( -p0 + 3 * p1 - 3 * p2 + p3 ) * t ** 3 ) )
    out.append( p[-2] )
    return np.array( out )


def tyre_marks( m, name, points, track=38.0, width=6.5 ):
    """ A vehicle's two wheel tracks along a curve through points: rubber (rv_yd_tyre) down each track's middle in a darker
    smear (rv_yd_stain), fading in and out at the ends and broken where the tyre barely touched. """
    rng = np.random.default_rng( seed_of( "tyre", name ) )
    path = _spline( points )
    dist = np.concatenate( ( [ 0.0 ], np.cumsum( np.linalg.norm( np.diff( path, axis=0 ), axis=1 ) ) ) )
    total = dist[-1]
    tang = np.gradient( path, axis=0 )
    tang /= np.linalg.norm( tang, axis=1, keepdims=True )
    lefts = np.column_stack( ( -tang[:, 1], tang[:, 0] ) )
    t = dist / total
    fade = np.clip( np.minimum( t / 0.2, ( 1 - t ) / 0.2 ), 0, 1 )
    knots = max( 4, int( total / 40 ) )
    for side in ( -0.5, 0.5 ):
        wob = np.interp( dist, np.linspace( 0, total, 12 ), rng.normal( 0, 1.0, 12 ) )
        breakup = np.interp( dist, np.linspace( 0, total, knots ), rng.uniform( 0.2, 1.0, knots ) )
        w = width * fade * np.clip( breakup * 1.4, 0, 1 )
        centre = path + lefts * ( track * side + wob )[:, None]
        for k in range( len( path ) - 1 ):
            if w[k] < 1.0 and w[k + 1] < 1.0:
                continue
            for paint, share, z in ( ( "rv_yd_stain", 1.0, Z_TYRE_OUT ), ( "rv_yd_tyre", 0.55, Z_TYRE_IN ) ):
                h0, h1 = w[k] * share / 2, w[k + 1] * share / 2
                q = [ centre[k] - lefts[k] * h0, centre[k + 1] - lefts[k + 1] * h1, centre[k + 1] + lefts[k + 1] * h1,
                      centre[k] + lefts[k] * h0 ]
                uv = None
                if paint == "rv_yd_tyre":
                    v0, v1 = dist[k] / 48.0, dist[k + 1] / 48.0
                    uv = [ ( 0.02, v0 ), ( 0.02, v1 ), ( 0.98, v1 ), ( 0.98, v0 ) ]
                flat( m, paint, q, z, uv )
    note( "stain", name, path )


# ---------------------------------------------------------------------------------------------------------------------
# Painted markings: lines, hatched boxes, arrows, lettering and pictograms (geometry in worn, ground-aligned paint)

def hatch( m, name, e0, e1, n0, n1, paint="rv_yd_paint_yellow", second=None, border=4.0, stripe=5.0, gap=14.0, angle=45.0,
           z=Z_PAINT ):
    """ A hatched box: a border line and diagonal stripes inside (with second, alternate stripes of it and no gaps:
    hazard hatching). """
    band( m, paint, e0, e1, n0, n0 + border, z )
    band( m, paint, e0, e1, n1 - border, n1, z )
    band( m, paint, e0, e0 + border, n0 + border, n1 - border, z )
    band( m, paint, e1 - border, e1, n0 + border, n1 - border, z )
    i0, i1, j0, j1 = e0 + border, e1 - border, n0 + border, n1 - border
    a = math.radians( angle )
    d = np.array( ( math.cos( a ), math.sin( a ) ) )
    nv = left( d )
    corners = np.array( [ ( i0, j0 ), ( i1, j0 ), ( i1, j1 ), ( i0, j1 ) ] )
    proj = corners @ nv
    reach = float( np.linalg.norm( corners[2] - corners[0] ) ) + 10
    mid = corners.mean( axis=0 )
    step = stripe if second is not None else stripe + gap
    t = proj.min() - step
    k = 0
    while t < proj.max():
        base = mid + nv * ( t - float( mid @ nv ) )
        quad = [ base - d * reach, base + d * reach, base + d * reach + nv * stripe, base - d * reach + nv * stripe ]
        piece = clip_rect( quad, i0, i1, j0, j1 )
        if len( piece ) >= 3:
            flat( m, paint if second is None or k % 2 == 0 else second, piece, z )
        t += step
        k += 1
    note( "paint", name, [ ( e0, n0 ), ( e1, n1 ) ] )


def arrow( m, name, centre, direction, length=84.0, width=10.0, paint="rv_yd_paint_white", z=Z_PAINT ):
    """ A painted direction arrow: a shaft and a head, length along direction. """
    d = unit2( direction )
    s = left( d )
    c = np.asarray( centre, float )[:2]
    head, hw = length * 0.36, width * 1.9
    local = [ ( -length / 2, -width / 2 ), ( length / 2 - head, -width / 2 ), ( length / 2 - head, -hw ), ( length / 2, 0.0 ),
              ( length / 2 - head, hw ), ( length / 2 - head, width / 2 ), ( -length / 2, width / 2 ) ]
    pts = [ c + d * x + s * y for x, y in local ]
    flat( m, paint, pts, z )
    note( "paint", name, pts )


def _mask_rects( mask ):
    """ A boolean picture (rows top down) as rectangles ( r0, r1, c0, c1 ): runs along rows, merged down while they
    match. """
    rects, active = [], {}
    for r in range( mask.shape[0] + 1 ):
        runs = []
        if r < mask.shape[0]:
            row = np.concatenate( ( [ False ], mask[r], [ False ] ) )
            edges = np.flatnonzero( row[1:] != row[:-1] )
            runs = [ ( int( edges[k] ), int( edges[k + 1] ) ) for k in range( 0, len( edges ), 2 ) ]
        nxt = {}
        for run in runs:
            nxt[run] = active.pop( run ) if run in active else r
        for run, r0 in active.items():
            rects.append( ( r0, r, run[0], run[1] ) )
        active = nxt
    return rects


def _crop( a ):
    rows, cols = np.flatnonzero( a.any( 1 ) ), np.flatnonzero( a.any( 0 ) )
    return a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def text_mask( text, px=48 ):
    """ Lettering as a boolean picture, its capitals px tall, cropped to the ink. """
    font = ImageFont.truetype( str( FONT ), int( px / 0.69 ) )
    x0, y0, x1, y1 = font.getbbox( text )
    img = Image.new( "L", ( x1 - x0 + 4, y1 - y0 + 4 ), 0 )
    ImageDraw.Draw( img ).text( ( 2 - x0, 2 - y0 ), text, font=font, fill=255 )
    return _crop( np.asarray( img ) > 127 )


def person_mask( px=96 ):
    """ A walkway's walking figure, as a boolean picture px tall. """
    img = Image.new( "L", ( px, px ), 0 )
    _person( ImageDraw.Draw( img ), px / 2, px / 2, px * 0.95, 255 )
    return _crop( np.asarray( img ) > 127 )


def floor_glyphs( m, name, mask, centre, up, height, paint="rv_yd_paint_white", stretch=1.0, z=Z_PAINT ):
    """ A picture painted on the ground, read by someone facing up: height inches along up, its width to scale over
    stretch (road lettering is drawn long, to read right from a low eye). Returns its width. """
    u = unit2( up )
    r = np.array( ( u[1], -u[0] ) )
    rows, cols = mask.shape
    sy = height / rows
    sx = sy / stretch
    W = cols * sx
    c = np.asarray( centre, float )[:2]
    for r0, r1, c0, c1 in _mask_rects( mask ):
        x0, x1 = -W / 2 + c0 * sx, -W / 2 + c1 * sx
        y1, y0 = height / 2 - r0 * sy, height / 2 - r1 * sy
        flat( m, paint, [ c + r * x0 + u * y0, c + r * x1 + u * y0, c + r * x1 + u * y1, c + r * x0 + u * y1 ], z )
    note( "paint", name, [ c + r * x + u * y for x in ( -W / 2, W / 2 ) for y in ( -height / 2, height / 2 ) ] )
    return W


def floor_text( m, name, text, centre, up, height, paint="rv_yd_paint_white", stretch=2.2, z=Z_PAINT ):
    return floor_glyphs( m, name, text_mask( text ), centre, up, height, paint, stretch, z )


def walkway_figure( m, name, centre, up, height=34.0, paint="rv_yd_paint_yellow", z=Z_PAINT ):
    floor_glyphs( m, name, person_mask(), centre, up, height, paint, 1.0, z )


def zebra( m, name, centre, across, length, width, bar=20.0, gap=18.0, paint="rv_yd_paint_white" ):
    """ A crossing's bars: `length` across the lane (along `across`), each bar `width` long the lane's way. """
    a = unit2( across )
    c = np.asarray( centre, float )[:2]
    count = int( ( length + gap ) // ( bar + gap ) )
    start = -( count * bar + ( count - 1 ) * gap ) / 2
    for k in range( count ):
        mid = c + a * ( start + k * ( bar + gap ) + bar / 2 )
        flat( m, paint, rect_pts( mid, a, bar, width ), Z_PAINT )
    note( "paint", name, rect_pts( c, a, length, width ) )


# ---------------------------------------------------------------------------------------------------------------------
# Drains, covers and the footway

def _cast_uv( name, s, t, inset=3 ):
    x, y, w, h = CAST[name]
    x, y, w, h = x + inset, y + inset, w - 2 * inset, h - 2 * inset
    return ( ( x + s * w ) / CAST_ATLAS[0], 1.0 - ( y + ( 1.0 - t ) * h ) / CAST_ATLAS[1] )


def _frame( m, centre, along, length, width, rim=1.5, top=0.75, paint="rv_dark" ):
    """ A metal frame round an opening flush in the slab: four bars rim wide, top high. """
    a = unit2( along )
    s = left( a )
    c = np.asarray( centre, float )[:2]
    for sgn in ( -1, 1 ):
        P.obox( m, ( *( c + s * sgn * ( width / 2 + rim / 2 ) ), top / 2 ), a, ( length + 2 * rim, rim, top ), paint )
        P.obox( m, ( *( c + a * sgn * ( length / 2 + rim / 2 ) ), top / 2 ), a, ( rim, width, top ), paint )


def trench( m, name, a, b, width=10.0, piece=20.0 ):
    """ A trench drain: a galvanised frame flush with the slab and slotted cast grates in pieces about piece long. """
    a, b = np.asarray( a, float )[:2], np.asarray( b, float )[:2]
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    s = left( d )
    _frame( m, ( a + b ) / 2, d, L, width, 1.2, 0.75, "rv_zinc" )
    count = max( 1, int( round( L / piece ) ) )
    uv = [ _cast_uv( "trench", 0.0, 0.0 ), _cast_uv( "trench", 0.0, 1.0 ), _cast_uv( "trench", 1.0, 1.0 ), _cast_uv( "trench", 1.0, 0.0 ) ]
    for k in range( count ):
        p0, p1 = a + d * L * k / count, a + d * L * ( k + 1 ) / count
        flat( m, "rv_yd_cast", [ p0 - s * width / 2, p1 - s * width / 2, p1 + s * width / 2, p0 + s * width / 2 ], Z_COVER, uv )
        if k < count - 1:
            flat( m, "rv_dark", [ p1 - s * width / 2 - d * 0.2, p1 - s * width / 2 + d * 0.2, p1 + s * width / 2 + d * 0.2,
                                  p1 + s * width / 2 - d * 0.2 ], Z_COVER + 0.03 )
    note( "drain", name, [ a - s * width, b + s * width ] )


def gully( m, name, centre, size=18.0, turn=0.0 ):
    """ A square gully grate in its frame. """
    d = np.array( ( math.cos( math.radians( turn ) ), math.sin( math.radians( turn ) ) ) )
    _frame( m, centre, d, size, size )
    pts = rect_pts( centre, d, size, size )
    flat( m, "rv_yd_cast", pts, Z_COVER, [ _cast_uv( "gully", s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ] )
    note( "drain", name, pts )


def manhole( m, name, centre, kind="round", size=30.0, turn=0.0 ):
    """ A manhole cover in its frame: round (size across) or a square double cover (size by 1.4 size). """
    c = np.asarray( centre, float )[:2]
    t = math.radians( turn )
    if kind == "round":
        r, sides = size / 2, 28
        ang = [ t + 2 * math.pi * k / sides for k in range( sides ) ]
        disc = [ c + r * np.array( ( math.cos( x ), math.sin( x ) ) ) for x in ang ]
        uv = [ _cast_uv( "round", 0.5 + 0.5 * math.cos( x - t ), 0.5 + 0.5 * math.sin( x - t ), inset=6 ) for x in ang ]
        flat( m, "rv_yd_cast", disc, Z_COVER, uv )
        outer = [ c + ( r + 2.5 ) * np.array( ( math.cos( x ), math.sin( x ) ) ) for x in ang ]
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            flat( m, "rv_dark", [ disc[k], outer[k], outer[k1], disc[k1] ], 0.75 )
            card( m, "rv_dark", [ ( *outer[k], 0.0 ), ( *outer[k1], 0.0 ), ( *outer[k1], 0.75 ), ( *outer[k], 0.75 ) ],
                  v( *( ( outer[k] + outer[k1] ) / 2 - c ), 0 ) )
        note( "drain", name, outer )
    else:
        d = np.array( ( math.cos( t ), math.sin( t ) ) )
        _frame( m, c, d, size * 1.4, size, rim=2.0 )
        pts = rect_pts( c, d, size * 1.4, size )
        flat( m, "rv_yd_cast", pts, Z_COVER, [ _cast_uv( "square", s, q ) for s, q in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ] )
        note( "drain", name, pts )


def footway( m, name, e0, e1, n0, n1, kerb="-n", piece=36.0 ):
    """ A footway of precast flags a little over the slab (Z_FOOT), with precast kerbs (1.8 tall, chamfered on the road
    side, piece long) along its south ('-n') or north ('+n') edge, outside it. """
    P.box( m, e0, e1, n0, n1, 0.0, Z_FOOT, { "default": "rv_yd_flags", "-z": None } )
    edge, out = ( n0, -1.0 ) if kerb == "-n" else ( n1, 1.0 )
    # The kerb's section: q out from the footway's edge, z up; from the road face's foot over the top to the flags.
    sec = [ ( 6.0, 0.0 ), ( 6.0, 1.0 ), ( 5.2, 1.8 ), ( 0.0, 1.8 ), ( 0.0, Z_FOOT ) ]
    middle = np.array( ( 3.0, 0.9 ) )
    count = max( 1, int( round( ( e1 - e0 ) / piece ) ) )
    for k in range( count ):
        a, b = e0 + ( e1 - e0 ) * k / count + 0.12, e0 + ( e1 - e0 ) * ( k + 1 ) / count - 0.12
        for j in range( len( sec ) - 1 ):
            ( qa, za ), ( qb, zb ) = sec[j], sec[j + 1]
            nq, nz = zb - za, -( qb - qa )
            if np.dot( ( nq, nz ), ( ( qa + qb ) / 2 - middle[0], ( za + zb ) / 2 - middle[1] ) ) < 0:
                nq, nz = -nq, -nz
            face = [ ( a, edge + out * qa, za ), ( b, edge + out * qa, za ), ( b, edge + out * qb, zb ), ( a, edge + out * qb, zb ) ]
            card( m, "rv_yd_flags", face, v( 0, out * nq, nz ) )
        cap = [ ( edge + out * q, z ) for q, z in sec ] + [ ( edge, 0.0 ) ]
        card( m, "rv_yd_flags", [ ( a, y, z ) for y, z in cap ], v( -1, 0, 0 ) )
        card( m, "rv_yd_flags", [ ( b, y, z ) for y, z in cap ], v( 1, 0, 0 ) )
    note( "drain", name, [ ( e0, min( n0, edge + out * 6 ) ), ( e1, max( n1, edge + out * 6 ) ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# Clutter (drawn only)

def turned( m, base, axis, profile, paints, sides=16, phase=0.0 ):
    """ A round thing turned about axis through base: profile [ ( radius, distance along axis ) ], paints one or one per
    band (None leaves a band out), shaded smooth. """
    base, axis = np.asarray( base, float ), P.unit( axis )
    u, w = P.perp( axis )
    dirs = [ u * math.cos( phase + 2 * math.pi * k / sides ) + w * math.sin( phase + 2 * math.pi * k / sides ) for k in range( sides ) ]
    for j in range( len( profile ) - 1 ):
        paint = paints[j] if isinstance( paints, ( list, tuple ) ) else paints
        ( r0, t0 ), ( r1, t1 ) = profile[j], profile[j + 1]
        slope = np.array( ( t1 - t0, r0 - r1 ), float )
        if paint is None or np.linalg.norm( slope ) < 1e-9 or ( r0 < 1e-6 and r1 < 1e-6 ):
            continue
        slope /= np.linalg.norm( slope )
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ base + dirs[k] * r0 + axis * t0, base + dirs[k1] * r0 + axis * t0, base + dirs[k1] * r1 + axis * t1,
                    base + dirs[k] * r1 + axis * t1 ]
            nrm = [ dirs[i] * slope[0] + axis * slope[1] for i in ( k, k1, k1, k ) ]
            if r0 < 1e-6:
                pts, nrm = pts[1:], nrm[1:]
            elif r1 < 1e-6:
                pts, nrm = pts[:3], nrm[:3]
            card( m, paint, pts, sum( nrm ), normals=nrm )


def _sign_uv( name ):
    x, y, w, h = SIGNS[name]
    W, H = SIGN_ATLAS
    return [ ( ( x + s * w ) / W, 1.0 - ( y + ( 1.0 - t ) * h ) / H ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]


def _sign_aspect( name ):
    x, y, w, h = SIGNS[name]
    return w / h


def printed( m, name, centre, facing, h, up=UP, back=None, off=0.05 ):
    """ A sign or label from the yard's atlas, h tall, facing out (a plan or 3D vector), on its own plate. """
    f = P.unit( v( *facing ) if len( facing ) == 3 else v( facing[0], facing[1], 0 ) )
    right = P.unit( np.cross( up, f ) )
    w = h * _sign_aspect( name )
    P.quad( m, "rv_yd_signs", centre, right, up, w, h, _sign_uv( name ), off )
    if back:
        P.quad( m, back, v( *centre ) - f * 0.12, -right, up, w, h )
    return w


DRUM_R, DRUM_H = 11.25, 34.5
DRUM_PROFILE = [ ( DRUM_R - 0.4, 0.0 ), ( DRUM_R + 0.2, 0.25 ), ( DRUM_R + 0.25, 1.3 ), ( DRUM_R, 1.6 ), ( DRUM_R, 11.0 ),
                 ( DRUM_R + 0.4, 11.3 ), ( DRUM_R + 0.4, 12.1 ), ( DRUM_R, 12.4 ), ( DRUM_R, 22.1 ), ( DRUM_R + 0.4, 22.4 ),
                 ( DRUM_R + 0.4, 23.2 ), ( DRUM_R, 23.5 ), ( DRUM_R, 32.9 ), ( DRUM_R + 0.25, 33.2 ), ( DRUM_R + 0.25, 34.5 ),
                 ( DRUM_R - 0.5, 34.5 ), ( DRUM_R - 0.6, 34.0 ), ( 0.0, 34.0 ) ]


def drum( m, name, c, paint="rv_yd_drum_blue", z0=0.0, facing=( 1, 0 ), label="drum_label", lying=None ):
    """ A 205 l steel drum: rolling hoops, chimes, a lid with two bungs, a label. lying: lay it down along that plan
    direction. """
    if lying is None:
        axis, base = UP, v( c[0], c[1], z0 )
    else:
        d = unit2( lying )
        axis, base = v( d[0], d[1], 0 ), v( c[0] - d[0] * DRUM_H / 2, c[1] - d[1] * DRUM_H / 2, z0 + DRUM_R + 0.4 )
    turned( m, base, axis, DRUM_PROFILE, paint, 16, phase=seed_of( name ) % 7 * 0.1 )
    u, w = P.perp( axis )
    for k, r in enumerate( ( 7.0, 7.5 ) ):
        a = 1.3 + k * 2.4
        at = base + axis * 34.0 + ( u * math.cos( a ) + w * math.sin( a ) ) * r
        turned( m, at, axis, [ ( 1.25, 0.0 ), ( 1.25, 0.45 ), ( 0.0, 0.45 ) ], "rv_dark", 8 )
    if label and lying is None:
        f = unit2( facing )
        printed( m, "drum_label", base + v( f[0], f[1], 0 ) * ( DRUM_R + 0.45 ) + UP * 17.5, f, 4.6 )
    top = z0 + ( DRUM_H if lying is None else 2 * DRUM_R + 0.8 )
    if lying is None:
        note( "prop", name, [ ( c[0] - DRUM_R, c[1] - DRUM_R ), ( c[0] + DRUM_R, c[1] + DRUM_R ) ], top )
    else:
        note( "prop", name, [ base[:2], ( base + axis * DRUM_H )[:2], base[:2] + left( d ) * DRUM_R, base[:2] - left( d ) * DRUM_R ], top )


def pallet( m, name, c, along, z0=0.0, L=47.2, W=31.5, record=True ):
    """ A wooden pallet, its boards as a four-way one's: bottom boards, nine blocks, cross boards, the top deck.
    Returns its top. """
    a = unit2( along )
    s = left( a )
    c = np.asarray( c, float )[:2]

    def board( x, y, z, lx, wy, h ):
        p = c + a * x + s * y
        P.obox( m, ( p[0], p[1], z0 + z + h / 2 ), a, ( lx, wy, h ), "rv_yd_pallet" )

    for y in ( -W / 2 + 2.83, 0.0, W / 2 - 2.83 ):
        board( 0, y, 0.0, L, 5.67, 0.87 )
        for x in ( -L / 2 + 2.83, 0.0, L / 2 - 2.83 ):
            board( x, y, 0.87, 5.67, 3.94, 3.07 )
    for x in ( -L / 2 + 2.83, 0.0, L / 2 - 2.83 ):
        board( x, 0, 3.94, 5.67, W, 0.87 )
    widths = ( 5.67, 3.94, 5.67, 3.94, 5.67 )
    for k, y in enumerate( np.linspace( -W / 2 + 2.83, W / 2 - 2.83, 5 ) ):
        board( 0, y, 4.81, L, widths[k], 0.87 )
    if record:
        note( "prop", name, rect_pts( c, a, L, W ), z0 + 5.68 )
    return z0 + 5.68


def pallet_stack( m, name, c, along, count ):
    """ Empty pallets stacked, each a little askew. """
    rng = np.random.default_rng( seed_of( "stack", name ) )
    a = unit2( along )
    z = 0.0
    for k in range( count ):
        turn = rng.normal( 0, 0.035 )
        ak = np.array( ( a[0] * math.cos( turn ) - a[1] * math.sin( turn ), a[0] * math.sin( turn ) + a[1] * math.cos( turn ) ) )
        z = pallet( m, f"{name} {k}", np.asarray( c, float )[:2] + rng.normal( 0, 0.8, 2 ), ak, z, record=False )
    note( "prop", name, rect_pts( c, a, 48.5, 33.0 ), z )


def spill_pallet( m, name, c, along, drums=( "rv_yd_drum_blue", ) * 4, facing=( 1, 0 ) ):
    """ A bunded spill pallet (a yellow sump with a grating over it) with drums standing on it, two by two. """
    a = unit2( along )
    s = left( a )
    c = np.asarray( c, float )[:2]
    P.obox( m, ( c[0], c[1], 5.0 ), a, ( 52.0, 52.0, 10.0 ), { "default": "rv_yd_bin", "+z": None, "-z": None } )
    for sg in ( -1, 1 ):
        P.obox( m, ( *( c + a * sg * 25.0 ), 10.5 ), a, ( 2.0, 52.0, 1.0 ), "rv_yd_bin" )
        P.obox( m, ( *( c + s * sg * 25.0 ), 10.5 ), a, ( 48.0, 2.0, 1.0 ), "rv_yd_bin" )
    P.quad( m, "rv_black", v( c[0], c[1], 8.0 ), v( a[0], a[1], 0 ), v( s[0], s[1], 0 ), 48.0, 48.0 )
    P.quad( m, "rv_grating", v( c[0], c[1], 10.2 ), v( a[0], a[1], 0 ), v( s[0], s[1], 0 ), 48.0, 48.0 )
    k = 0
    for x in ( -11.8, 11.8 ):
        for y in ( -11.8, 11.8 ):
            if k < len( drums ) and drums[k]:
                drum( m, f"{name} drum {k}", c + a * x + s * y, drums[k], 10.2, facing, label="drum_label" if k % 2 == 0 else None )
            k += 1
    note( "prop", name, rect_pts( c, a, 52.0, 52.0 ), 10.2 + DRUM_H )


def cone( m, name, c, z0=0.0, tipped=None ):
    """ A traffic cone on its square rubber base, two reflective bands; tipped: lying with its tip that way. """
    paints = [ "rv_yd_cone", "rv_yd_reflective", "rv_yd_cone", "rv_yd_reflective", "rv_yd_cone", "rv_yd_cone" ]
    profile = [ ( 6.0, 0.0 ), ( 4.48, 8.7 ), ( 3.78, 12.7 ), ( 3.25, 15.7 ), ( 2.73, 18.7 ), ( 1.33, 26.7 ), ( 0.0, 26.7 ) ]
    c = np.asarray( c, float )[:2]
    if tipped is None:
        P.obox( m, ( c[0], c[1], z0 + 0.65 ), ( 1, 0.2 ), ( 14.0, 14.0, 1.3 ), "rv_rubber" )
        turned( m, v( c[0], c[1], z0 + 1.3 ), UP, profile, paints, 14 )
        note( "prop", name, [ c - 7, c + 7 ], 28.0 )
        return
    d = unit2( tipped )
    tilt = math.atan2( 7.0 - 1.0, 27.0 )
    axis = P.unit( v( d[0] * math.cos( tilt ), d[1] * math.cos( tilt ), -math.sin( tilt ) ) )
    side = v( -d[1], d[0], 0 )
    base = v( c[0], c[1], 7.0 )
    m.oriented_box( base - axis * 0.65, ( axis, side, np.cross( axis, side ) ), ( 1.3, 14.0, 14.0 ), "rv_rubber" )
    turned( m, base, axis, profile, paints, 14 )
    note( "prop", name, [ c - 7, c + d * 28 + 7 ], 14.0 )


def ibc( m, name, c, along, label=True ):
    """ An IBC tote: a 1000 l plastic tank in a galvanised tube cage on a steel pallet, a fill cap and a drain valve. """
    a = unit2( along )
    s = left( a )
    c = np.asarray( c, float )[:2]
    L, W = 47.2, 39.4
    P.obox( m, ( c[0], c[1], 2.9 ), a, ( L, W, 5.8 ), "rv_zinc" )
    P.obox( m, ( c[0], c[1], 27.0 ), a, ( L - 3.6, W - 3.6, 42.0 ), "rv_yd_ibc" )
    turned( m, v( c[0], c[1], 48.0 ), UP, [ ( 7.0, 0.0 ), ( 7.0, 1.6 ), ( 0.0, 1.6 ) ], "rv_yd_ibc", 14 )
    front = c + a * ( L / 2 - 1.8 )
    valve = [ ( 2.2, 0.0 ), ( 2.2, 4.0 ), ( 3.0, 4.0 ), ( 3.0, 6.0 ), ( 0.0, 6.0 ) ]
    turned( m, v( front[0], front[1], 9.0 ), v( a[0], a[1], 0 ), valve, "rv_dark", 10 )
    hx, hy = L / 2 + 0.2, W / 2 + 0.2
    for x in np.linspace( -hx, hx, 7 ):
        for sg in ( -1, 1 ):
            p = c + a * x + s * sg * hy
            P.rod( m, ( p[0], p[1], 5.8 ), ( p[0], p[1], 49.5 ), 0.42, "rv_zinc", 6 )
    for y in np.linspace( -hy, hy, 6 )[1:-1]:
        for sg in ( -1, 1 ):
            p = c + a * sg * hx + s * y
            P.rod( m, ( p[0], p[1], 5.8 ), ( p[0], p[1], 49.5 ), 0.42, "rv_zinc", 6 )
    corners = [ c + a * x + s * y for x, y in ( ( -hx, -hy ), ( hx, -hy ), ( hx, hy ), ( -hx, hy ) ) ]
    for z in ( 6.2, 17.5, 29.0, 40.5, 49.5 ):
        for k in range( 4 ):
            p, q = corners[k], corners[( k + 1 ) % 4]
            P.rod( m, ( p[0], p[1], z ), ( q[0], q[1], z ), 0.42, "rv_zinc", 6 )
    if label:
        printed( m, "ibc_label", v( *( c + a * ( L / 2 - 1.75 ) ), 33.0 ), a, 8.0 )
        printed( m, "ghs_warn", v( *( c + a * ( L / 2 - 1.75 ) - s * 12.0 ), 33.0 ), a, 7.0 )
    note( "prop", name, rect_pts( c, a, L + 1, W + 1 ), 51.0 )


def cable_reel( m, name, c, axis, R=20.0, width=26.0, wound=15.0 ):
    """ A wooden cable drum on its rim: two flanges round a barrel of black cable. """
    d = unit2( axis )
    ax = v( d[0], d[1], 0 )
    base = v( c[0], c[1], R ) - ax * ( width / 2 + 1.4 )
    profile = [ ( 0.0, 0.0 ), ( R, 0.0 ), ( R, 1.4 ), ( wound, 1.4 ), ( wound, 1.4 + width ), ( R, 1.4 + width ), ( R, 2.8 + width ),
                ( 0.0, 2.8 + width ) ]
    turned( m, base, ax, profile, [ "rv_yd_pallet", "rv_yd_pallet", "rv_yd_pallet", "rv_black", "rv_yd_pallet", "rv_yd_pallet", "rv_yd_pallet" ], 20 )
    hub = base + ax * ( width / 2 + 1.4 )
    for sg in ( -1, 1 ):
        turned( m, hub + ax * sg * ( width / 2 + 1.4 ), ax * sg, [ ( 3.0, 0.0 ), ( 3.0, 0.5 ), ( 0.0, 0.5 ) ], "rv_zinc", 10 )
    tail = hub + v( 0, 0, wound - 1.0 ) + ax * 4.0
    P.pipe( m, [ tuple( tail ), tuple( tail + v( 0, 0, 2.0 ) + v( d[1], -d[0], 0 ) * 8.0 ),
                 tuple( v( tail[0], tail[1], 1.0 ) + v( d[1], -d[0], 0 ) * 22.0 ),
                 tuple( v( tail[0], tail[1], 1.0 ) + v( d[1], -d[0], 0 ) * 40.0 + ax * 6.0 ) ], 0.9, "rv_black", 6, caps=True )
    note( "prop", name, [ c - d * ( width / 2 + 2.8 ) - left( d ) * R, c + d * ( width / 2 + 2.8 ) + left( d ) * R ], 2 * R )


def sand_bin( m, name, c, facing ):
    """ A yellow sand bin with a sloping lid, its label to the front. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    right = np.cross( UP, fv )
    c = np.asarray( c, float )[:2]
    P.obox( m, ( c[0], c[1], 12.5 ), right[:2], ( 34.0, 22.0, 25.0 ), "rv_yd_bin" )
    t = math.atan2( 4.0, 24.0 )
    back = -fv
    y = P.unit( back * math.cos( t ) + UP * math.sin( t ) )
    m.oriented_box( v( c[0], c[1], 27.6 ), ( right, y, np.cross( right, y ) ), ( 36.0, 25.0, 1.2 ), "rv_yd_bin" )
    printed( m, "sand", v( c[0], c[1], 14.0 ) + fv * 11.05, f, 7.5 )
    P.obox( m, ( *( c + f * 11.6 ), 25.0 ), right[:2], ( 8.0, 1.2, 1.6 ), "rv_black" )
    note( "prop", name, rect_pts( c, right[:2], 36.0, 26.0 ), 30.0 )


def spill_kit( m, name, c, facing ):
    """ A yellow wheelie bin spill kit: a tapered body, an overhanging lid, wheels and a handle at the back, a label. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    r = np.cross( UP, fv )
    c = v( c[0], c[1], 0 )
    lo = [ ( -10.0, -11.0 ), ( 10.0, -11.0 ), ( 10.0, 11.0 ), ( -10.0, 11.0 ) ]
    hi = [ ( -11.5, -14.5 ), ( 11.5, -14.5 ), ( 11.5, 13.0 ), ( -11.5, 13.0 ) ]

    def p( x, y, z ):
        return c + r * x + fv * y + UP * z
    for k in range( 4 ):
        k1 = ( k + 1 ) % 4
        quad = [ p( *lo[k], 3.0 ), p( *lo[k1], 3.0 ), p( *hi[k1], 38.0 ), p( *hi[k], 38.0 ) ]
        mid = sum( quad ) / 4
        card( m, "rv_yd_bin", quad, mid - ( c + UP * 20.0 ) )
    card( m, "rv_yd_bin", [ p( *q, 3.0 ) for q in lo ], -UP )
    m.oriented_box( p( 0, -0.5, 39.0 ), ( r, fv, UP ), ( 24.5, 31.0, 1.6 ), "rv_yd_bin" )
    for sg in ( -1, 1 ):
        turned( m, p( sg * 9.0, -12.5, 4.0 ), r * sg, [ ( 0.0, 0.0 ), ( 4.0, 0.0 ), ( 4.0, 2.2 ), ( 0.0, 2.2 ) ], "rv_black", 12 )
    P.rod( m, p( -11.5, -15.5, 37.0 ), p( 11.5, -15.5, 37.0 ), 0.6, "rv_black", 6 )
    # The label on the front face, which leans out 3.5 over its 35 height.
    lean = math.atan2( 2.0, 35.0 )
    up = P.unit( UP * math.cos( lean ) + fv * math.sin( lean ) )
    printed( m, "spill_kit", p( 0, 12.1, 26.0 ), np.cross( r, up ), 6.0, up=up )
    note( "prop", name, [ p( -12, -16, 0 )[:2], p( 12, 14, 0 )[:2] ], 40.6 )


def hose_reel( m, name, c, facing ):
    """ A fire hose reel on a galvanised post: a red drum of red hose facing out, its nozzle hanging, a sign above. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    c = v( c[0], c[1], 0 )
    P.obox( m, ( c[0], c[1], 0.3 ), f, ( 10.0, 10.0, 0.6 ), "rv_zinc" )
    P.obox( m, ( c[0], c[1], 33.0 ), f, ( 2.5, 2.5, 66.0 ), "rv_zinc" )
    hub = c + UP * 42.0 + fv * 3.0
    profile = [ ( 0.0, 0.0 ), ( 12.5, 0.0 ), ( 12.5, 0.6 ), ( 10.5, 0.6 ), ( 10.5, 4.6 ), ( 12.5, 4.6 ), ( 12.5, 5.2 ), ( 3.0, 5.2 ),
                ( 3.0, 6.2 ), ( 0.0, 6.2 ) ]
    turned( m, hub, fv, profile, [ "rv_yd_red", "rv_yd_red", "rv_yd_red", "rv_yd_hose", "rv_yd_red", "rv_yd_red",
                                   "rv_yd_red", "rv_zinc", "rv_zinc" ], 18 )
    right = np.cross( UP, fv )
    start = hub + fv * 2.6 + right * 10.5 - UP * 3.0
    P.pipe( m, [ tuple( start ), tuple( start + right * 2.0 - UP * 6.0 ), tuple( start + right * 1.0 - UP * 16.0 ) ], 0.75,
            "rv_yd_hose", 6, caps=False )
    tip = start + right * 1.0 - UP * 16.0
    turned( m, tip, -UP, [ ( 0.9, 0.0 ), ( 1.1, 3.0 ), ( 0.6, 5.0 ), ( 0.0, 5.0 ) ], "rv_black", 8 )
    printed( m, "hose_reel", c + UP * 62.0 + fv * 1.4, f, 8.0, back="rv_zinc" )
    note( "prop", name, [ ( c - right * 13 - fv * 2 )[:2], ( c + right * 13 + fv * 10 )[:2] ], 66.0 )


def hydrant( m, name, c, facing ):
    """ A pillar fire hydrant: a red barrel with two outlets and their caps, a domed top and its operating nut. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    base = v( c[0], c[1], 0 )
    turned( m, base, UP, [ ( 6.0, 0.0 ), ( 6.0, 1.4 ), ( 4.4, 2.0 ), ( 4.4, 22.0 ), ( 5.0, 22.5 ), ( 5.0, 24.2 ), ( 3.8, 26.6 ),
                           ( 1.6, 28.4 ), ( 0.0, 28.6 ) ], "rv_yd_red", 16 )
    turned( m, base + UP * 28.4, UP, [ ( 1.3, 0.0 ), ( 1.3, 1.6 ), ( 0.0, 1.6 ) ], "rv_dark", 5 )
    right = np.cross( UP, fv )
    for d in ( right, -right, fv ):
        turned( m, base + UP * 17.0 + d * 4.0, d, [ ( 1.8, 0.0 ), ( 1.8, 2.6 ), ( 2.2, 2.6 ), ( 2.2, 3.6 ), ( 0.0, 3.6 ) ],
                [ "rv_yd_red", "rv_yd_red", "rv_dark", "rv_dark" ], 10 )
    note( "prop", name, [ ( c[0] - 8, c[1] - 8 ), ( c[0] + 8, c[1] + 8 ) ], 30.0 )


def safety_shower( m, name, c, facing ):
    """ An emergency shower and eye wash: a yellow standpipe on a base plate, the shower head on an arm with its pull
    rod, the eye wash bowl at waist height, its green sign on top. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    right = np.cross( UP, fv )
    base = v( c[0], c[1], 0 )
    P.obox( m, ( c[0], c[1], 0.4 ), f, ( 14.0, 14.0, 0.8 ), "rv_yellow" )
    P.rod( m, base, base + UP * 88.0, 1.2, "rv_yellow", 10 )
    P.pipe( m, [ tuple( base + UP * 86.0 ), tuple( base + UP * 86.0 + fv * 22.0 ) ], 1.0, "rv_yellow", 8 )
    head = base + UP * 85.0 + fv * 22.0
    turned( m, head, -UP, [ ( 1.0, 0.0 ), ( 5.5, 3.0 ), ( 5.5, 3.6 ), ( 0.0, 3.6 ) ], "rv_yellow", 16 )
    P.rod( m, head - fv * 8.0, head - fv * 8.0 - UP * 22.0, 0.3, "rv_zinc", 5 )
    grip = head - fv * 8.0 - UP * 22.0
    corners = ( grip - UP * 5 + right * 3, grip - UP * 5 - right * 3 )
    for a, b in ( ( grip, corners[0] ), ( grip, corners[1] ), corners ):
        P.rod( m, a, b, 0.35, "rv_zinc", 5 )
    P.pipe( m, [ tuple( base + UP * 34.0 ), tuple( base + UP * 34.0 + fv * 12.0 ) ], 0.8, "rv_yellow", 8 )
    turned( m, base + UP * 34.0 + fv * 12.0, UP, [ ( 0.8, 0.0 ), ( 5.0, 1.2 ), ( 6.2, 3.8 ), ( 5.8, 4.0 ), ( 4.0, 2.0 ), ( 0.0, 2.0 ) ],
            "rv_yellow", 16 )
    P.obox( m, ( *( c + f * 4.0 ), 30.0 ), right[:2], ( 1.0, 6.0, 4.0 ), "rv_yellow" )
    printed( m, "eyewash", base + UP * 97.0 + fv * 1.6, f, 13.0, back="rv_zinc" )
    note( "prop", name, [ ( base - right * 8 - fv * 8 )[:2], ( base + right * 8 + fv * 28 )[:2] ], 104.0 )


def sign_post( m, name, base, facing, sign, h, top=84.0 ):
    """ A sign on a galvanised post, its top at top, facing out; its back plain. """
    f = unit2( facing )
    fv = v( f[0], f[1], 0 )
    b = v( base[0], base[1], 0 )
    P.rod( m, b, b + UP * ( top + 1.0 ), 1.2, "rv_zinc", 8 )
    turned( m, b + UP * ( top + 1.0 ), UP, [ ( 1.3, 0.0 ), ( 0.0, 0.4 ) ], "rv_zinc", 8 )
    w = printed( m, sign, b + fv * 1.5 + UP * ( top - h / 2 ), f, h, back="rv_zinc" )
    right = np.cross( UP, fv )
    for z in ( top - h * 0.18, top - h * 0.82 ):
        P.obox( m, ( *( base + f * 0.5 ), z ), right[:2], ( 3.4, 2.6, 1.0 ), "rv_zinc" )
    note( "prop", name, [ ( b - right * w / 2 )[:2], ( b + right * w / 2 + fv * 2 )[:2] ], top + 1.4 )


# ---------------------------------------------------------------------------------------------------------------------
# Where it all goes

# riverdale_map's own floor lines (west coordinates; yard_side mirrors them): the walkway's edge along the annex, the
# lane's double centre line (cut here for the crossing), the line by the grey container, and the annex opening's
# hazard strip. They're painted over in worn paint; if riverdale_map moves them, move these too.
YARD_LINES = ( ( -1700, -480, -668, -664 ), ( -1300, -772, -1210, -1206 ), ( -1300, -772, -1226, -1222 ),
               ( -676, -560, -1210, -1206 ), ( -676, -560, -1226, -1222 ), ( -870, -866, -1700, -1240 ) )
MIDDLE_LINE = ( -520, 520, -1206, -1202 )
HAZARD_STRIP = ( -1450, -1170, -660, -636 )


def side( g, p, sx ):
    """ One side's yard, annex front, court and spawn strip, built in west coordinates and mirrored for the east (sx 1),
    every outline seeded by side. """
    f = -sx
    tag = "west" if f > 0 else "east"

    def at( e, n ):
        return ( f * e, n )

    def D( x, y ):
        return ( f * x, y )

    def ee( e0, e1 ):
        return tuple( sorted( ( f * e0, f * e1 ) ) )

    def name( text ):
        return f"{tag} {text}"

    def pick( west, east ):
        """ A west-coordinate value that differs by side: the turbine hall's pilasters aren't mirrored. """
        return west if f > 0 else east

    # Worn paint over riverdale_map's lines; its hazard strip repainted in yellow and black.
    for e0, e1, n0, n1 in YARD_LINES:
        a, b = ee( e0, e1 )
        band( g, "rv_yd_paint_yellow", a - 0.15, b + 0.15, n0 - 0.15, n1 + 0.15 )
    a, b = ee( HAZARD_STRIP[0], HAZARD_STRIP[1] )
    hatch( g, name( "annex opening" ), a - 0.15, b + 0.15, HAZARD_STRIP[2] - 0.15, HAZARD_STRIP[3] + 0.15, "rv_yd_paint_yellow",
           "rv_yd_paint_black", border=0.0, stripe=6.0 )

    # The yard: the lane's crossing, its stop lines, SLOW and an arrow; hatched loading bays; walkway figures.
    zebra( g, name( "crossing" ), at( -724, -1216 ), ( 0, 1 ), 192, 72, bar=24, gap=18 )
    band( g, "rv_yd_paint_white", *ee( -800, -788 ), -1312, -1232 )
    band( g, "rv_yd_paint_white", *ee( -676, -664 ), -1200, -1120 )
    floor_text( g, name( "slow" ), "SLOW", at( -1000, -1272 ), D( 1, 0 ), 44 )
    arrow( g, name( "lane arrow" ), at( -1230, -1268 ), D( 1, 0 ) )
    hatch( g, name( "turbine bay" ), *ee( -1284, -1180 ), -1652, -1458, "rv_yd_paint_yellow", "rv_yd_paint_black", stripe=6.0 )
    hatch( g, name( "annex bay" ), *ee( -642, -538 ), -1652, -1468, "rv_yd_paint_yellow", "rv_yd_paint_black", stripe=6.0 )
    hatch( g, name( "annex north door" ), *ee( -1462, -1318 ), 244, 306, stripe=4.0, gap=12.0 )
    hatch( g, name( "annex west door" ), *ee( -1764, -1704 ), -276, -124, stripe=4.0, gap=12.0 )
    hatch( g, name( "spawn wing door" ), *ee( -1876, -1826 ), -805, -725, stripe=4.0, gap=12.0 )
    walkway_figure( g, name( "walkway a" ), at( -1610, -642 ), D( 1, 0 ) )
    walkway_figure( g, name( "walkway b" ), at( -800, -642 ), D( 1, 0 ) )
    # The muster point round the spawns: a green box, its name painted inside.
    x0, x1 = ee( -2244, -1796 )
    for e0, e1, n0, n1 in ( ( x0, x1, -560, -555 ), ( x0, x1, 535, 540 ), ( x0, x0 + 5, -555, 535 ), ( x1 - 5, x1, -555, 535 ) ):
        band( g, "rv_yd_paint_green", e0, e1, n0, n1 )
    floor_text( g, name( "assembly" ), "ASSEMBLY POINT", at( -1815, -10 ), D( -1, 0 ), 16, "rv_yd_paint_green", stretch=1.6 )

    # Drains and covers.
    trench( g, name( "annex opening" ), at( -1440, -629 ), at( -1180, -629 ) )
    trench( g, name( "turbine bay" ), at( -1291, -1640 ), at( -1291, -1470 ) )
    trench( g, name( "annex bay" ), at( -529, -1640 ), at( -529, -1480 ) )
    gully( g, name( "fore gully" ), at( -845, -872 ), 16, turn=8 * f )
    gully( g, name( "wall gully" ), at( -975, -1735 ), 16 )
    gully( g, name( "b gully" ), at( -1160, -1452 ), 16, turn=15 * f )
    gully( g, name( "court gully" ), at( -1545, 1205 ), 16 )
    gully( g, name( "spawn gully" ), at( -2205, 1000 ), 16 )
    gully( g, name( "apron gully" ), at( -650, -320 ), 16 )
    manhole( g, name( "yard cover" ), at( -1220, -1045 ), "round", 30, turn=20 * f )
    manhole( g, name( "lane cover" ), at( -520, -995 ), "round", 30, turn=-35 * f )
    manhole( g, name( "court cover" ), at( -1450, 1460 ), "square", 24 )
    manhole( g, name( "spawn cover" ), at( -1830, 1100 ), "square", 24, turn=90 )
    manhole( g, name( "spawn south cover" ), at( -1880, -1380 ), "round", 30, turn=50 * f )

    # Damp bands along the walls' feet: the turbine hall, its block, the annex, the hall's court side, the spawn
    # buildings and the boundary.
    for k, ( p0, p1, out ) in enumerate( (
            ( ( -2286, -1750 ), ( -1700, -1750 ), ( 0, 1 ) ), ( ( -1300, -1750 ), ( -520, -1750 ), ( 0, 1 ) ),
            ( ( -1700, -1250 ), ( -1300, -1250 ), ( 0, 1 ) ), ( ( -1300, -1750 ), ( -1300, -1250 ), ( 1, 0 ) ),
            ( ( -1700, -1750 ), ( -1700, -1250 ), ( -1, 0 ) ), ( ( -520, -1750 ), ( -520, -1240 ), ( -1, 0 ) ),
            ( ( -1700, -620 ), ( -1040, -620 ), ( 0, -1 ) ), ( ( -1700, -620 ), ( -1700, 240 ), ( -1, 0 ) ),
            ( ( -1700, 240 ), ( -1040, 240 ), ( 0, 1 ) ), ( ( -1040, -620 ), ( -1040, -300 ), ( 1, 0 ) ),
            ( ( -1040, 240 ), ( -1040, 2040 ), ( -1, 0 ) ), ( ( -2300, -1750 ), ( -2300, 2447 ), ( 1, 0 ) ),
            ( ( -2060, -1160 ), ( -2060, -840 ), ( 1, 0 ) ), ( ( -1880, -840 ), ( -1880, -690 ), ( 1, 0 ) ),
            ( ( -2300, -690 ), ( -1880, -690 ), ( 0, 1 ) ), ( ( -2300, -1160 ), ( -2060, -1160 ), ( 0, -1 ) ) ) ):
        wet_edge( g, name( f"wet edge {k}" ), at( *p0 ), at( *p1 ), D( *out ) )

    # Puddles: by the gullies, along the walls and the containers, in the forklift's ruts, in the slab's dips.
    puddle( g, name( "yard fore" ), at( -770, -862 ), D( 1, 0.12 ), 175, 62 )
    puddle( g, name( "yard near" ), at( -690, -985 ), D( 1, -0.1 ), 110, 46 )
    puddle( g, name( "rut a" ), at( -1355, -765 ), D( 0.15, 1 ), 90, 14, lobes=2, rough=0.4 )
    puddle( g, name( "rut b" ), at( -1316, -752 ), D( 0.12, 1 ), 70, 12, lobes=2, rough=0.4 )
    puddle( g, name( "container" ), at( -1000, -1112 ), D( 1, 0 ), 150, 26 )
    puddle( g, name( "wall" ), at( -925, -1727 ), D( 1, 0 ), 105, 24 )
    puddle( g, name( "b site" ), at( -1120, -1420 ), D( 0.6, 0.8 ), 95, 48 )
    puddle( g, name( "container south" ), at( -690, -1690 ), D( 1, 0 ), 70, 22 )
    puddle( g, name( "middle" ), at( -430, -1226 ), D( 1, 0 ), 70, 14, lobes=2 )
    puddle( g, name( "apron kerb" ), at( -575, -318 ), D( 1, 0 ), 170, 30 )
    puddle( g, name( "apron" ), at( -300, -642 ), D( 1, 0.1 ), 120, 34 )
    puddle( g, name( "court a" ), at( -1520, 1250 ), D( 0.3, 1 ), 140, 58 )
    puddle( g, name( "court fence" ), at( -1290, 520 ), D( 1, 0 ), 80, 36 )
    puddle( g, name( "court tanks" ), at( -1195, 1420 ), D( 0, 1 ), 70, 36 )
    puddle( g, name( "court north" ), at( -1400, 1880 ), D( 1, 0.2 ), 90, 50 )
    puddle( g, name( "spawn a" ), at( -2180, 950 ), D( 0, 1 ), 120, 46 )
    puddle( g, name( "spawn b" ), at( -1960, 1620 ), D( 0.8, 0.6 ), 90, 56 )
    puddle( g, name( "spawn south" ), at( -2150, -1240 ), D( 1, 0.2 ), 80, 46 )
    puddle( g, name( "spawn mid" ), at( -1950, -640 ), D( 1, 0 ), 110, 36 )
    puddle( g, name( "spawn c" ), at( -2100, 560 ), D( 1, 0 ), 110, 40 )

    # Stains: oil where machines stand and drip, rust round steel feet and from the containers' corners, tyre marks.
    oil_stain( g, name( "forklift" ), at( -1548, -770 ), D( 1, 0.1 ), 120, 70 )
    oil_stain( g, name( "container end" ), at( -862, -1172 ), D( 0, 1 ), 36, 22 )
    oil_stain( g, name( "lane drip a" ), at( -1150, -1262 ), D( 1, 0 ), 40, 18 )
    oil_stain( g, name( "lane drip b" ), at( -950, -1282 ), D( 1, 0.2 ), 34, 16 )
    oil_stain( g, name( "bay drip" ), at( -1140, -1560 ), D( 0, 1 ), 60, 30 )
    oil_stain( g, name( "yard spot" ), at( -1440, -1010 ), D( 1, 0.5 ), 50, 26 )
    for k, ( e, n ) in enumerate( ( ( -1240, -1700 ), ( -620, -1700 ) ) ):
        rust_ring( g, name( f"mast {k}" ), at( e, n ), 6.0 )
    for k, ( e, n, dx, dy ) in enumerate( ( ( -1120, -1229, -0.3, -1 ), ( -880, -1229, 0.3, -1 ), ( -1120, -1131, -0.2, 1 ),
                                            ( -880, -1131, 0.2, 1 ), ( -809, -1640, -0.2, -1 ), ( -711, -1640, 0.2, -1 ),
                                            ( -1609, -1200, -0.2, -1 ), ( -1511, -1200, 0.2, -1 ) ) ):
        rust_run( g, name( f"container rust {k}" ), at( e, n ), D( dx, dy ), 26, 10 )
    for k, ( e, n ) in enumerate( ( ( -1880, -1270 ), ( -2040, -1270 ), ( -1880, -1160 ) ) ):
        rust_ring( g, name( f"gantry {k}" ), at( e, n ), 7.0 )
    for k, ( e, n ) in enumerate( ( ( -1640, 980 ), ( -1360, 980 ), ( -1080, 980 ), ( -1640, 1700 ), ( -1360, 1700 ), ( -1080, 1700 ) ) ):
        rust_ring( g, name( f"court column {k}" ), at( e, n ), 6.0 )
    tyre_marks( g, name( "forklift" ), [ at( -1305, -660 ), at( -1320, -740 ), at( -1380, -800 ), at( -1480, -815 ), at( -1570, -790 ) ], 34, 5.5 )
    tyre_marks( g, name( "bay truck" ), [ at( -880, -1300 ), at( -1020, -1345 ), at( -1150, -1440 ), at( -1225, -1555 ) ], 68, 8.0 )
    tyre_marks( g, name( "lane" ), [ at( -1290, -1262 ), at( -1050, -1275 ), at( -820, -1268 ), at( -600, -1255 ) ], 66, 7.0 )

    # Clutter along the walls and in the corners.
    spill_pallet( p, name( "wall drums" ), at( pick( -1030, -1066 ), -1724 ), D( 1, 0 ),
                  ( "rv_yd_drum_blue", "rv_yd_drum_blue", "rv_yd_drum_grey", None ), D( 0, 1 ) )
    sand_bin( p, name( "sand" ), at( -562, -1736 ), D( 0, 1 ) )
    spill_kit( p, name( "spill kit" ), at( -1283, -1718 ), D( 1, 0 ) )
    pallet_stack( p, name( "container pallets" ), at( -832, -1562 ), D( 0, 1 ), 6 )
    cone( p, name( "cone a" ), at( -1222, -800 ) )
    cone( p, name( "cone b" ), at( -1082, -818 ), tipped=D( 0.7, -0.7 ) )
    hose_reel( p, name( "annex hose" ), at( -1718, -318 ), D( -1, 0 ) )
    sign_post( p, name( "annex ppe" ), at( -1712, -112 ), D( -1, 0 ), "ppe", 16, 80 )
    spill_pallet( p, name( "annex drums" ), at( -1728, 160 ), D( 0, 1 ),
                  ( "rv_yd_drum_grey", "rv_yd_drum_red", "rv_yd_drum_grey", "rv_yd_drum_grey" ), D( -1, 0 ) )
    sign_post( p, name( "annex no smoking" ), at( -1708, 205 ), D( -1, 0 ), "no_smoking", 14, 78 )
    sign_post( p, name( "forklifts" ), at( -1712, -632 ), D( -1, 0 ), "forklift", 16, 82 )
    sign_post( p, name( "yard speed" ), at( -1712, -1262 ), D( -1, 0 ), "speed10", 20, 84 )
    sign_post( p, name( "crossing" ), at( -660, -1104 ), D( 1, 0 ), "pedestrians", 16, 84 )
    cable_reel( p, name( "hut reel" ), at( -2265, -1580 ), D( 0, 1 ) )
    cone( p, name( "hut cone a" ), at( -2060, -1510 ) )
    cone( p, name( "hut cone b" ), at( -2085, -1512 ) )
    sign_post( p, name( "hut speed" ), at( -2182, -1392 ), D( 0, 1 ), "speed10", 18, 80 )
    for k, ( e, n, paint ) in enumerate( ( ( -2276, 846, "rv_yd_drum_red" ), ( -2276, 870, "rv_yd_drum_grey" ), ( -2253, 858, "rv_yd_drum_red" ) ) ):
        drum( p, name( f"spawn drum {k}" ), at( e, n ), paint, facing=D( 1, 0 ), label="drum_label" if k == 2 else None )
    pallet_stack( p, name( "spawn pallets" ), at( -2269, 1421 ), D( 0, 1 ), 5 )
    ibc( p, name( "spawn ibc" ), at( -2271, 2045 ), D( 1, 0 ) )
    sign_post( p, name( "spawn no smoking" ), at( -2282, 2002 ), D( 1, 0 ), "no_smoking", 14, 78 )
    cable_reel( p, name( "spawn reel" ), at( -2262, 2372 ), D( 0, 1 ) )
    sign_post( p, name( "assembly" ), at( -2283, 30 ), D( 1, 0 ), "assembly", 22, 88 )
    hydrant( p, name( "court hydrant" ), at( -1688, 262 ), D( 1, 0 ) )
    z = pallet( p, name( "court pallet" ), at( -1063, 1150 ), D( 0, 1 ) )
    for k, n in enumerate( ( 1138.5, 1161.5 ) ):
        drum( p, name( f"court drum {k}" ), at( -1063, n ), "rv_yd_drum_green", z0=z, facing=D( 1, 0 ), label="drum_label" if k == 0 else None )
    safety_shower( p, name( "shower" ), at( -1056, 1640 ), D( -1, 0 ) )
    spill_kit( p, name( "court kit" ), at( -1555, 700 ), D( 1, 0 ) )
    sand_bin( p, name( "court sand" ), at( -1250, 258 ), D( 0, 1 ) )
    printed( p, "high_voltage", v( f * -1420, 558.6, 24.0 ), D( 0, -1 ), 14.0, back="rv_zinc" )
    printed( p, "high_voltage", v( f * -1521.4, 640.0, 24.0 ), D( -1, 0 ), 14.0, back="rv_zinc" )
    pallet_stack( p, name( "court stack" ), at( -1066, 1995 ), D( 0, 1 ), 4 )
    for k, e in enumerate( ( -1018, -994 ) ):
        drum( p, name( f"apron drum {k}" ), at( e, -269 ), "rv_yd_drum_blue", z0=Z_FOOT, facing=D( 1, 0 ), label="drum_label" if k == 1 else None )
    sand_bin( p, name( "turbine sand" ), at( -462, -1226 ), D( 0, 1 ) )
    sign_post( p, name( "turbine ppe" ), at( -500, -1232 ), D( 0, 1 ), "ppe", 14, 76 )


def middle( g, p ):
    """ The hall's apron and the turbine annex's front: the footway and its kerb along the hall, the south door's drain
    and hatched box, the middle lane's arrows, the generators' oil. """
    for k, ( p0, p1, out ) in enumerate( ( ( ( -520, -1240 ), ( 520, -1240 ), ( 0, 1 ) ), ( ( -160, -1040 ), ( 160, -1040 ), ( 0, -1 ) ),
                                           ( ( -420, -700 ), ( 420, -700 ), ( 0, 1 ) ) ) ):
        wet_edge( g, f"middle wet edge {k}", p0, p1, out )
    footway( g, "hall footway west", -1040, -112, -300, -240 )
    footway( g, "hall footway east", 112, 1040, -300, -240 )
    trench( g, "hall south door", ( -112, -251 ), ( 112, -251 ) )
    hatch( g, "hall south door", -112, 112, -330, -262, stripe=4.0, gap=12.0 )
    band( g, "rv_yd_paint_yellow", MIDDLE_LINE[0] - 0.15, MIDDLE_LINE[1] + 0.15, MIDDLE_LINE[2] - 0.15, MIDDLE_LINE[3] + 0.15 )
    arrow( g, "middle arrow east", ( -260, -1223 ), ( 1, 0 ), 72, 8 )
    arrow( g, "middle arrow west", ( 260, -1184 ), ( -1, 0 ), 72, 8 )
    manhole( g, "apron cover", ( 0, -385 ), "square", 24, turn=90 )
    puddle( g, "turbine door", ( 30, -1224 ), ( 1, 0 ), 90, 18, lobes=2 )
    for e in ( -225, 225 ):
        oil_stain( g, f"generator {e}", ( e, -1115 ), ( 1, 0 ), 240, 150, lobes=3, core=0.62 )


def north_lane( g, p ):
    """ The lane between the hall and the perimeter wall: puddles along the wall and in the lane, the hall's north doors'
    drains and hatched boxes, a walkway under the pipe rack, FIRE ROUTE, covers, the generator's oil, tyre marks and
    clutter along the wall. """
    for k, ( c, d, L, W ) in enumerate( ( ( ( -1450, 2400 ), ( 1, 0 ), 200, 40 ), ( ( -820, 2275 ), ( 1, 0.05 ), 220, 80 ),
                                         ( ( -120, 2165 ), ( 1, 0 ), 160, 36 ), ( ( 380, 2330 ), ( 1, -0.1 ), 150, 60 ),
                                         ( ( 1150, 2410 ), ( 1, 0 ), 180, 34 ), ( ( 1500, 2200 ), ( 0.8, 0.6 ), 100, 60 ),
                                         ( ( -2120, 2400 ), ( 1, 0 ), 120, 40 ), ( ( 2080, 2390 ), ( 1, -0.2 ), 110, 44 ) ) ):
        puddle( g, f"lane {k}", c, d, L, W )
    for sg in ( -1, 1 ):
        trench( g, f"lane door {sg}", ( sg * 480, 2051 ), ( sg * 340, 2051 ) )
        hatch( g, f"lane door {sg}", *sorted( ( sg * 490, sg * 330 ) ), 2058, 2128, stripe=4.0, gap=12.0 )
        walkway_figure( g, f"lane walkway {sg}", ( sg * 680, 2120 ), ( -sg, 0 ) )
        floor_text( g, f"fire route {sg}", "FIRE ROUTE", ( sg * 1350, 2300 ), ( -sg, 0 ), 40, "rv_yd_paint_yellow", stretch=2.0 )
        hose_reel( p, f"lane hose {sg}", ( sg * 750, 2200 ), ( 0, 1 ) )
        sign_post( p, f"lane speed {sg}", ( sg * 1690, 2436 ), ( sg, 0 ), "speed10", 18, 80 )
    walkway_figure( g, "lane walkway mid", ( 0, 2120 ), ( 1, 0 ) )
    wet_edge( g, "lane wet edge hall", ( -1040, 2040 ), ( 1040, 2040 ), ( 0, 1 ) )
    wet_edge( g, "lane wet edge wall", ( -2300, 2447 ), ( 2300, 2447 ), ( 0, -1 ), depth=( 4.0, 18.0 ) )
    band( g, "rv_yd_paint_yellow", -1000, 1000, 2203, 2207 )
    manhole( g, "lane cover a", ( -300, 2335 ), "square", 24 )
    manhole( g, "lane cover b", ( 560, 2140 ), "round", 30, turn=30 )
    manhole( g, "lane cover c", ( 1300, 2280 ), "round", 30, turn=-70 )
    for k, c in enumerate( ( ( -1350, 2425 ), ( -720, 2270 ), ( 450, 2330 ), ( 1225, 2425 ) ) ):
        gully( g, f"lane gully {k}", c, 16, turn=6 * k )
    oil_stain( g, "lane generator", ( 0, 2255 ), ( 1, 0 ), 330, 120, lobes=4, core=0.6 )
    oil_stain( g, "lane drip a", ( -500, 2300 ), ( 1, 0.3 ), 36, 18 )
    oil_stain( g, "lane drip b", ( 900, 2290 ), ( 1, -0.2 ), 44, 20 )
    for k, e in enumerate( ( -1000, -500, 250, 750, 1000 ) ):
        rust_ring( g, f"lane column {k}", ( e, 2190 ), 6.0 )
    for k, e in enumerate( ( -750, 0, 500 ) ):
        rust_ring( g, f"lane hall column {k}", ( e, 2050 ), 6.0 )
    tyre_marks( g, "lane trucks", [ ( -1650, 2310 ), ( -900, 2330 ), ( -200, 2345 ), ( 600, 2335 ), ( 1500, 2300 ) ], 66, 7.0 )
    for k, ( e, n ) in enumerate( ( ( -1662, 2426 ), ( -1638, 2428 ) ) ):
        drum( p, f"lane drum {k}", ( e, n ), "rv_yd_drum_blue", facing=( 0, -1 ), label="drum_label" if k == 0 else None )
    drum( p, "lane drum lying", ( -1600, 2425 ), "rv_yd_drum_grey", lying=( 1, 0.15 ) )
    pallet_stack( p, "lane pallets", ( -980, 2427 ), ( 1, 0 ), 6 )
    hydrant( p, "lane hydrant west", ( -380, 2436 ), ( 0, -1 ) )
    hydrant( p, "lane hydrant east", ( 1450, 2436 ), ( 0, -1 ) )
    ibc( p, "lane ibc", ( 880, 2424 ), ( 1, 0 ) )
    sign_post( p, "lane no smoking", ( 918, 2440 ), ( 0, -1 ), "no_smoking", 14, 76 )
    for k, e in enumerate( ( 1480, 1504 ) ):
        drum( p, f"lane drum east {k}", ( e, 2427 ), "rv_yd_drum_red" if k else "rv_yd_drum_grey", facing=( 0, -1 ), label=None )
    for k, ( e, n ) in enumerate( ( ( 300, 2433 ), ( 330, 2434 ) ) ):
        cone( p, f"lane cone {k}", ( e, n ) )
    cone( p, "lane cone tipped", ( 362, 2428 ), tipped=( 1, -0.4 ) )
    cable_reel( p, "lane reel", ( 60, 2420 ), ( 1, 0 ) )
    sign_post( p, "fire route board", ( -1200, 2440 ), ( 0, -1 ), "fire_route", 14, 78 )


# ---------------------------------------------------------------------------------------------------------------------
# The models

def extra_models():
    """ riverdale_map.build()'s hook: the ground detail and the props, neither colliding. """
    NOTES.clear()
    ground, props = K.Model(), K.Model()
    props.grain_paints.add( "rv_yd_pallet" )
    for sx in ( -1, 1 ):
        side( ground, props, sx )
    middle( ground, props )
    north_lane( ground, props )
    return [ ( "riverdale_yard_ground", "Yard Ground Detail", False, False, ground ),
             ( "riverdale_yard_props", "Yard Props", False, True, props ) ]


# ---------------------------------------------------------------------------------------------------------------------
# --check and --plan

def _gap( a, b ):
    """ The plan distance between two rectangles ( e0, e1, n0, n1 ) (0 where they overlap). """
    de = max( a[0] - b[1], b[0] - a[1], 0.0 )
    dn = max( a[2] - b[3], b[2] - a[3], 0.0 )
    return math.hypot( de, dn )


def _overlap( a, b ):
    return max( 0.0, min( a[1], b[1] ) - max( a[0], b[0] ) ) * max( 0.0, min( a[3], b[3] ) - max( a[2], b[2] ) )


def check( plan_dir=None ):
    import railhead_map as R
    import riverdale_map as RD
    models = RD.build()
    solid = [ models[n] for n, _, collide, _ in RD.scene_models() if collide and n in models ]
    boxes = [ ( lo, hi ) for lo, hi in R.collision_aabbs( solid ) if hi[2] > 0.5 and lo[2] < 90 ]
    rects = [ ( float( lo[0] ), float( hi[0] ), float( lo[1] ), float( hi[1] ), float( lo[2] ), float( hi[2] ) ) for lo, hi in boxes ]
    # Railings' player clips count as something to stand against (not as collision a prop mustn't touch).
    against = list( rects )
    for _, centre, yaw, ( L, thick, H ) in P.CLIPS:
        a = math.radians( yaw )
        he = abs( math.cos( a ) ) * L / 2 + abs( math.sin( a ) ) * thick / 2
        hn = abs( math.sin( a ) ) * L / 2 + abs( math.cos( a ) ) * thick / 2
        if centre[2] - H / 2 < 30:
            against.append( ( centre[0] - he, centre[0] + he, centre[1] - hn, centre[1] + hn, centre[2] - H / 2, centre[2] + H / 2 ) )
    spots = [ ( label, p ) for label, p in RD.all_spots() if p[2] < 10 ]
    lines = []
    for model in models.values():
        for paint in ( "rv_line_yellow", "rv_hazard" ):
            for pts, normal in model.polygons.get( paint, [] ):
                q = np.asarray( pts )
                if q[:, 2].max() < 1 and normal[2] > 0.9:
                    lines.append( ( q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max() ) )
    problems = 0
    for category, label, r, top in NOTES:
        if category == "prop":
            for e0, e1, n0, n1, z0, z1 in rects:
                if z0 < top and _overlap( r, ( e0, e1, n0, n1 ) ) > 4.0 and ( e1 - e0 ) * ( n1 - n0 ) < 4e6:
                    print( f"  {label}: overlaps collision {e0:.0f}..{e1:.0f}, {n0:.0f}..{n1:.0f}, z {z0:.0f}..{z1:.0f}" )
                    problems += 1
                    break
            for spot, ( e, n, z ) in spots:
                if _gap( r, ( e - 16, e + 16, n - 16, n + 16 ) ) < 24:
                    print( f"  {label}: within 24 of {spot}" )
                    problems += 1
            for site in RD.BOMB_SITES:
                ce, cn = ( site[2] + site[3] ) / 2, ( site[4] + site[5] ) / 2
                if _gap( r, ( ce, ce, cn, cn ) ) < 120:
                    print( f"  {label}: within 120 of {site[1]}'s centre" )
                    problems += 1
            walls = min( r[0] - RD.PLAY[0], RD.PLAY[1] - r[1], r[2] - RD.PLAY[2], RD.PLAY[3] - r[3] )
            near = min( [ _gap( r, x[:4] ) for x in against if x[4] < 60 ] + [ walls ]
                        + [ _gap( r, r2 ) for c2, l2, r2, _ in NOTES if c2 == "prop" and l2 != label and not l2.startswith( label ) ] )
            if near > 30 and "sign" not in label and "crossing" not in label and "speed" not in label:
                print( f"  {label}: stands {near:.0f} from anything (not tucked)" )
                problems += 1
        if category == "puddle":
            for other_category, other, r2, _ in NOTES:
                if other_category in ( "paint", "drain" ) and _overlap( r, r2 ) > 0 and "gully" not in other and "footway" not in other:
                    print( f"  {label}: overlaps {other_category} {other}" )
                    problems += 1
            for line in lines:
                if _overlap( r, line ) > 0:
                    print( f"  {label}: overlaps a riverdale_map line at {line[0]:.0f}..{line[1]:.0f}, {line[2]:.0f}..{line[3]:.0f}" )
                    problems += 1
    counts = { name: model.triangle_count() for name, model in models.items() if name.startswith( "riverdale_yard" ) }
    print( f"  {problems} placement problem(s); {', '.join( f'{k}: {v} triangles' for k, v in counts.items() )}" )
    if plan_dir:
        plan( Path( plan_dir ), rects, spots, lines )
    return problems


AREAS = { "west_yard": ( -2300, -200, -1760, -200 ), "east_yard": ( 200, 2300, -1760, -200 ), "middle": ( -1100, 1100, -1760, -200 ),
          "west_court": ( -2300, -1000, 200, 2460 ), "east_court": ( 1000, 2300, 200, 2460 ), "north_lane": ( -2300, 2300, 1950, 2460 ) }
COLOURS = { "prop": ( 80, 200, 255 ), "puddle": ( 40, 90, 255 ), "wet": ( 30, 60, 160 ), "stain": ( 150, 90, 50 ),
            "paint": ( 250, 230, 60 ), "drain": ( 200, 200, 200 ) }


def plan( out, rects, spots, lines ):
    """ Each area from above at half an inch a pixel: collision orange (tall) and amber (low), riverdale_map's lines,
    the spots green, the bomb sites red, and this dressing's footprints by kind. """
    import riverdale_map as RD
    out.mkdir( parents=True, exist_ok=True )
    for area, ( e0, e1, n0, n1 ) in AREAS.items():
        s = 0.5 if area != "north_lane" else 0.3
        img = Image.new( "RGB", ( int( ( e1 - e0 ) * s ), int( ( n1 - n0 ) * s ) ), ( 36, 40, 36 ) )
        d = ImageDraw.Draw( img )

        def X( e ):
            return ( e - e0 ) * s

        def Y( n ):
            return ( n1 - n ) * s
        for g in range( int( e0 // 100 ) * 100, int( e1 ) + 1, 100 ):
            d.line( ( X( g ), 0, X( g ), img.height ), fill=( 60, 64, 60 ) if g % 500 else ( 100, 100, 100 ) )
        for g in range( int( n0 // 100 ) * 100, int( n1 ) + 1, 100 ):
            d.line( ( 0, Y( g ), img.width, Y( g ) ), fill=( 60, 64, 60 ) if g % 500 else ( 100, 100, 100 ) )
        for a, b, c, dd, z0, z1 in rects:
            d.rectangle( ( X( a ), Y( dd ), X( b ), Y( c ) ), outline=( 200, 90, 40 ) if z1 > 60 else ( 220, 170, 60 ) )
        for a, b, c, dd in lines:
            d.rectangle( ( X( a ), Y( dd ), X( b ), Y( c ) ), fill=( 160, 140, 40 ) )
        for category, label, ( a, b, c, dd ), top in NOTES:
            d.rectangle( ( X( a ), Y( dd ), X( b ), Y( c ) ), outline=COLOURS[category], width=2 if category == "prop" else 1 )
        for label, ( e, n, z ) in spots:
            d.rectangle( ( X( e - 16 ), Y( n + 16 ), X( e + 16 ), Y( n - 16 ) ), outline=( 60, 255, 60 ) )
        for site in RD.BOMB_SITES:
            d.rectangle( ( X( site[2] ), Y( site[5] ), X( site[3] ), Y( site[4] ) ), outline=( 255, 0, 0 ), width=2 )
        for g in range( int( e0 // 500 ) * 500, int( e1 ) + 1, 500 ):
            for h in range( int( n0 // 500 ) * 500, int( n1 ) + 1, 500 ):
                d.text( ( X( g ) + 2, Y( h ) + 2 ), f"{g},{h}", fill=( 200, 200, 255 ) )
        img.save( out / f"plan_{area}.png" )
        print( f"wrote {out / f'plan_{area}.png'}" )


def main():
    import argparse
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--check", action="store_true", help="build the map and check the dressing's placements" )
    parser.add_argument( "--plan", metavar="DIR", help="with --check, also draw each area from above into DIR" )
    parser.add_argument( "--stage", metavar="DIR", help="write only this module's two models under DIR, laid out as Assets "
                                                        "(quicker than riverdale_map.py --stage while placing things)" )
    args = parser.parse_args()
    if args.stage:
        import riverdale_map as RD
        import riverdale_yard
        out = Path( args.stage ).resolve() / RD.RESOURCE_DIR
        for name, _, _, _, model in riverdale_yard.extra_models():
            RD.configure( model )
            print( f"{name}: {K.write_model( out, RD.RESOURCE_DIR, name, model )} triangles" )
    if args.check or args.plan:
        # riverdale_map loads this module by name for its models: check through that copy, which holds their NOTES.
        import riverdale_yard
        riverdale_yard.check( args.plan )
    if not ( args.check or args.plan or args.stage ):
        parser.print_help()


if __name__ == "__main__":
    main()
